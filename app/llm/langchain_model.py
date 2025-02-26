"""
@file: langchain_model.py
@description:
Implementation of the BasePredictionModel interface using LangChain and LLMs
to generate sports betting predictions. This module handles the integration with
OpenAI/Groq APIs via LangChain, constructs appropriate prompts with game data,
and processes the LLM responses into structured prediction outputs.

@dependencies:
- langchain: For LLM chaining, prompting, and output parsing
- openai: For API access to GPT models
- app.llm.base_model: For the prediction model interface
- app.services: For data ingestion from external APIs and news sources
- app.core.logger: For logging
- dotenv: For environment variable management
- tenacity: For retry logic
- typing: For type hints

@notes:
- The model supports both OpenAI and Groq as LLM providers
- Structured and unstructured data are incorporated into the prediction process
- Confidence calibration is applied to adjust raw confidence scores
- The implementation follows LangChain's best practices for output parsing
- Extensive error handling and retry logic is implemented
- The prompt engineering incorporates sports betting domain knowledge
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Union, Tuple, cast
from tenacity import retry, stop_after_attempt, wait_exponential
from dotenv import load_dotenv

# LangChain imports
from langchain.schema import HumanMessage, SystemMessage
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.output_parsers import ResponseSchema, StructuredOutputParser
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory

# Application imports
from app.llm.base_model import BasePredictionModel, PredictionInput, PredictionResult
from app.services.ball_dont_lie_api import (
    get_team_by_id, 
    get_game_by_id, 
    get_player_stats,
    get_player_season_averages,
    get_team_stats_averages
)
from app.services.news_ingestion import (
    get_recent_news_for_team,
    get_team_injury_report,
    preprocess_text_for_llm
)
from app.core.logger import logger

# Load environment variables
load_dotenv()

# Constants
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DEFAULT_MODEL = "gpt-4"  # Default model to use
MAX_PROMPT_TOKENS = 16000  # Maximum tokens for input context
MAX_NEWS_ARTICLES = 5  # Maximum number of news articles to include per team
RECENT_GAMES_LIMIT = 5  # Number of recent games to analyze per team


class PredictionError(Exception):
    """Custom exception for prediction-related errors."""
    pass


class LangChainPredictionModel(BasePredictionModel):
    """
    Implementation of a prediction model using LangChain and LLMs.
    
    This model uses LangChain to interface with LLMs (OpenAI or Groq)
    to generate Against The Spread (ATS) predictions for NBA games.
    """
    
    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        provider: str = "openai",
        temperature: float = 0.3,
        max_tokens: int = 2000,
        agent_identifier: str = "langchain-llm-v1"
    ):
        """
        Initialize the LangChain prediction model.
        
        Args:
            model_name: Name of the LLM model to use
            provider: LLM provider ('openai' or 'groq')
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens for generation
            agent_identifier: Unique identifier for this agent
        
        Raises:
            ValueError: If required API keys are missing or provider is invalid
        """
        # Validate API keys
        if provider == "openai" and not OPENAI_API_KEY:
            raise ValueError("OpenAI API key not found in environment variables")
        elif provider == "groq" and not GROQ_API_KEY:
            raise ValueError("Groq API key not found in environment variables")
        elif provider not in ["openai", "groq"]:
            raise ValueError(f"Invalid provider: {provider}. Must be 'openai' or 'groq'")
            
        self._provider = provider
        self._model_name = model_name
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._agent_id = agent_identifier
        
        # Initialize LLM
        self._initialize_llm()
        
        # Initialize output parser for structured predictions
        self._initialize_output_parser()
        
        logger.info(f"Initialized LangChainPredictionModel with {provider} provider and {model_name} model")
    
    @property
    def agent_id(self) -> str:
        """Return the unique identifier for this model."""
        return self._agent_id
    
    def _initialize_llm(self):
        """
        Initialize the Language Model based on the selected provider.
        
        This method sets up the appropriate LLM client based on whether
        we're using OpenAI or Groq as the provider.
        """
        try:
            if self._provider == "openai":
                self._llm = ChatOpenAI(
                    model_name=self._model_name,
                    temperature=self._temperature,
                    max_tokens=self._max_tokens,
                    openai_api_key=OPENAI_API_KEY,
                    verbose=True
                )
            elif self._provider == "groq":
                # Assuming Groq has a compatible interface with OpenAI
                self._llm = ChatOpenAI(
                    model_name=self._model_name,
                    temperature=self._temperature,
                    max_tokens=self._max_tokens,
                    openai_api_key=GROQ_API_KEY,
                    openai_api_base="https://api.groq.com/openai/v1",
                    verbose=True
                )
            logger.info(f"Successfully initialized LLM with {self._provider}")
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {str(e)}")
            raise PredictionError(f"Failed to initialize LLM: {str(e)}")
    
    def _initialize_output_parser(self):
        """
        Initialize the structured output parser for LLM responses.
        
        This parser ensures that the LLM's textual output can be
        converted into a structured format matching our prediction schema.
        """
        # Define the expected response schemas
        response_schemas = [
            ResponseSchema(
                name="pick",
                description="The team and spread prediction, e.g., 'Lakers -4'. Include the team name and the spread number."
            ),
            ResponseSchema(
                name="logic",
                description="A paragraph explaining the reasoning behind the prediction, including key factors that influenced the decision."
            ),
            ResponseSchema(
                name="confidence",
                description="A confidence score from 0.0 to 1.0 (float) representing how confident the model is in this prediction."
            )
        ]
        
        # Create the structured output parser
        self._parser = StructuredOutputParser.from_response_schemas(response_schemas)
        
        # Get the format instructions for the LLM
        self._format_instructions = self._parser.get_format_instructions()
    
    async def _gather_team_data(self, team_id: int, team_name: str) -> Dict[str, Any]:
        """
        Gather comprehensive data about a team for prediction.
        
        Args:
            team_id: The BallDontLie API team ID
            team_name: The team name
            
        Returns:
            Dictionary containing team statistics, recent game results,
            player statistics, news, and injury reports
            
        Raises:
            PredictionError: If data gathering fails
        """
        try:
            # Gather data concurrently for efficiency
            import asyncio
            
            # Define tasks for concurrent execution
            tasks = [
                get_team_stats_averages(team_id),  # Team season stats
                get_recent_news_for_team(team_name, days=7),  # Recent news
                get_team_injury_report(team_name),  # Injury reports
            ]
            
            # Execute tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            team_stats = results[0] if not isinstance(results[0], Exception) else {}
            news_articles = results[1] if not isinstance(results[1], Exception) else []
            injury_reports = results[2] if not isinstance(results[2], Exception) else []
            
            # Limit the number of news articles to avoid token limits
            if len(news_articles) > MAX_NEWS_ARTICLES:
                news_articles = news_articles[:MAX_NEWS_ARTICLES]
            
            return {
                "team_stats": team_stats.get("data", []),
                "news": news_articles,
                "injuries": injury_reports
            }
        
        except Exception as e:
            logger.error(f"Error gathering data for team {team_name}: {str(e)}")
            raise PredictionError(f"Failed to gather team data: {str(e)}")
    
    def _prepare_prediction_prompt(
        self, 
        input_data: PredictionInput, 
        home_team_data: Dict[str, Any],
        away_team_data: Dict[str, Any]
    ) -> str:
        """
        Prepare the prompt for the LLM with all relevant game information.
        
        Args:
            input_data: The prediction input data
            home_team_data: Gathered data for the home team
            away_team_data: Gathered data for the away team
            
        Returns:
            Formatted prompt string for the LLM
        """
        # Format the game date for readability
        game_date = datetime.fromisoformat(input_data.game_date).strftime("%A, %B %d, %Y at %I:%M %p")
        
        # Determine favorite and underdog based on the spread
        spread_value = abs(input_data.spread)
        if input_data.spread > 0:
            # Positive spread means home team is underdog
            favorite = input_data.away_team
            underdog = input_data.home_team
            spread_description = f"{favorite} favored by {spread_value} points"
        else:
            # Negative or zero spread means home team is favorite
            favorite = input_data.home_team
            underdog = input_data.away_team
            spread_description = f"{favorite} favored by {spread_value} points"
        
        # Prepare team stats summaries
        home_stats_summary = self._format_team_stats(home_team_data.get("team_stats", []))
        away_stats_summary = self._format_team_stats(away_team_data.get("team_stats", []))
        
        # Prepare injury report summaries
        home_injuries = self._format_injury_report(home_team_data.get("injuries", []))
        away_injuries = self._format_injury_report(away_team_data.get("injuries", []))
        
        # Prepare news summaries (limited to avoid token limits)
        home_news = self._format_news_summary(home_team_data.get("news", []))
        away_news = self._format_news_summary(away_team_data.get("news", []))
        
        # Build the comprehensive prompt
        prompt = f"""
You are a leading NBA sports betting analyst with expertise in predicting Against The Spread (ATS) outcomes.
Your task is to analyze the following NBA game and make a prediction against the spread.

Game Information:
- Game ID: {input_data.game_id}
- Matchup: {input_data.away_team} @ {input_data.home_team}
- Date: {game_date}
- Current Spread: {spread_description}

{input_data.home_team} (Home Team) Information:
{home_stats_summary}

{input_data.away_team} (Away Team) Information:
{away_stats_summary}

Injury Reports:
{input_data.home_team} Injuries:
{home_injuries}

{input_data.away_team} Injuries:
{away_injuries}

Recent News:
{input_data.home_team} News:
{home_news}

{input_data.away_team} News:
{away_news}

Additional Context:
- Home court advantage is typically worth 2-3 points in the spread.
- Consider recent performance trends, matchup history, and rest advantages.
- Back-to-back games often impact team performance negatively.
- Player injuries can significantly affect team capabilities.

Based on all available information, predict which team will cover the spread.
{self._format_instructions}
"""
        return prompt
    
    def _format_team_stats(self, stats: List[Dict[str, Any]]) -> str:
        """Format team statistics into a readable string."""
        if not stats:
            return "Statistics not available."
        
        # Extract the first stats entry
        team_stats = stats[0] if stats else {}
        
        return f"""
- Win-Loss Record: {team_stats.get('wins', 'N/A')}-{team_stats.get('losses', 'N/A')}
- Points Per Game: {team_stats.get('pts', 'N/A')}
- Field Goal %: {team_stats.get('fg_pct', 'N/A')}
- 3-Point %: {team_stats.get('fg3_pct', 'N/A')}
- Rebounds Per Game: {team_stats.get('reb', 'N/A')}
- Assists Per Game: {team_stats.get('ast', 'N/A')}
- Turnovers Per Game: {team_stats.get('turnover', 'N/A')}
"""
    
    def _format_injury_report(self, injuries: List[Dict[str, Any]]) -> str:
        """Format injury reports into a readable string."""
        if not injuries:
            return "No reported injuries."
        
        injury_lines = []
        for injury in injuries:
            player = injury.get('player', 'Unknown Player')
            status = injury.get('status', 'Unknown Status')
            injury_type = injury.get('injury', 'Unknown Injury')
            injury_lines.append(f"- {player}: {status} ({injury_type})")
        
        return "\n".join(injury_lines)
    
    def _format_news_summary(self, news: List[Dict[str, Any]]) -> str:
        """Format news articles into a condensed summary."""
        if not news:
            return "No recent news."
        
        news_summaries = []
        for article in news[:3]:  # Limit to 3 recent articles to save tokens
            title = article.get('title', 'Untitled')
            summary = article.get('summary', '')
            
            # Truncate long summaries
            if len(summary) > 200:
                summary = summary[:200] + "..."
            
            news_summaries.append(f"- {title}: {summary}")
        
        return "\n".join(news_summaries)
    
    def _calibrate_confidence(self, raw_confidence: float) -> float:
        """
        Calibrate raw confidence scores from the LLM.
        
        LLMs can be overconfident, so this applies a calibration function
        to produce more reliable confidence scores.
        
        Args:
            raw_confidence: Raw confidence score from LLM (0 to 1)
            
        Returns:
            Calibrated confidence score
        """
        # Implement a simple calibration function
        # This can be expanded with more sophisticated calibration based on historical accuracy
        
        # Add a slight regression to the mean (0.7)
        # This reduces extreme confidence values
        mean = 0.7
        regression_strength = 0.3
        
        calibrated = (1 - regression_strength) * raw_confidence + regression_strength * mean
        
        # Ensure the result is still between 0 and 1
        return max(0.0, min(1.0, calibrated))
    
    async def _extract_prediction_from_llm_response(self, llm_response: str) -> Dict[str, Any]:
        """
        Extract structured prediction information from LLM response.
        
        Args:
            llm_response: Raw response text from the LLM
            
        Returns:
            Dictionary containing parsed prediction fields
            
        Raises:
            PredictionError: If parsing fails
        """
        try:
            # Parse the response text using the output parser
            parsed_output = self._parser.parse(llm_response)
            
            # Extract and validate the required fields
            pick = parsed_output.get("pick", "")
            logic = parsed_output.get("logic", "")
            
            # Handle confidence - ensure it's a float between 0 and 1
            try:
                confidence_raw = float(parsed_output.get("confidence", 0.5))
                confidence = max(0.0, min(1.0, confidence_raw))
            except (ValueError, TypeError):
                logger.warning("Could not parse confidence score, using default 0.5")
                confidence = 0.5
            
            # Apply confidence calibration
            calibrated_confidence = self._calibrate_confidence(confidence)
            
            return {
                "pick": pick,
                "logic": logic,
                "confidence": calibrated_confidence
            }
            
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {str(e)}")
            logger.debug(f"Raw LLM response: {llm_response}")
            raise PredictionError(f"Failed to parse LLM response: {str(e)}")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def predict(self, input_data: PredictionInput) -> PredictionResult:
        """
        Generate a prediction for a single game using the LLM.
        
        This method:
        1. Gathers comprehensive data for both teams
        2. Prepares a detailed prompt with all relevant information
        3. Sends the prompt to the LLM
        4. Parses the response into a structured prediction
        
        Args:
            input_data: PredictionInput containing game information
            
        Returns:
            PredictionResult containing the generated prediction
            
        Raises:
            PredictionError: If prediction generation fails
            ValueError: If input data is invalid
        """
        try:
            logger.info(f"Generating prediction for game {input_data.game_id}: {input_data.away_team} @ {input_data.home_team}")
            
            # Gather team data (both structured and unstructured)
            # For simplicity, we're assuming the team IDs are provided in structured_data
            # In a real implementation, you would look up the team IDs from their names
            home_team_id = input_data.structured_data.get("home_team_id", 1)  # Default ID as fallback
            away_team_id = input_data.structured_data.get("away_team_id", 2)  # Default ID as fallback
            
            # Gather data for both teams concurrently
            import asyncio
            home_team_data, away_team_data = await asyncio.gather(
                self._gather_team_data(home_team_id, input_data.home_team),
                self._gather_team_data(away_team_id, input_data.away_team)
            )
            
            # Prepare the prediction prompt with all gathered data
            prompt = self._prepare_prediction_prompt(
                input_data=input_data,
                home_team_data=home_team_data,
                away_team_data=away_team_data
            )
            
            # Log the prompt length for monitoring token usage
            logger.debug(f"Prompt length: {len(prompt)} characters")
            
            # Generate prediction using LLM
            messages = [
                SystemMessage(content="You are a sports betting analyst specialized in NBA predictions against the spread."),
                HumanMessage(content=prompt)
            ]
            
            # Send to LLM and get response
            response = await self._llm.agenerate([messages])
            llm_response = response.generations[0][0].text
            
            # Parse the LLM response
            prediction_data = await self._extract_prediction_from_llm_response(llm_response)
            
            # Create and return the prediction result
            result = PredictionResult(
                agent_id=self.agent_id,
                game_id=input_data.game_id,
                pick=prediction_data["pick"],
                logic=prediction_data["logic"],
                confidence=prediction_data["confidence"],
                result="pending",
                metadata={
                    "model": self._model_name,
                    "provider": self._provider,
                    "generation_time": datetime.now().isoformat()
                }
            )
            
            logger.info(f"Successfully generated prediction for game {input_data.game_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error generating prediction: {str(e)}")
            raise PredictionError(f"Failed to generate prediction: {str(e)}")
    
    async def batch_predict(self, inputs: List[PredictionInput]) -> List[PredictionResult]:
        """
        Generate predictions for multiple games.
        
        This implementation processes each prediction sequentially,
        but could be optimized for batch processing in the future.
        
        Args:
            inputs: List of PredictionInput objects
            
        Returns:
            List of PredictionResult objects
            
        Raises:
            PredictionError: If prediction generation fails
        """
        results = []
        errors = []
        
        for input_data in inputs:
            try:
                prediction = await self.predict(input_data)
                results.append(prediction)
            except Exception as e:
                logger.error(f"Error in batch prediction for game {input_data.game_id}: {str(e)}")
                errors.append(f"Game {input_data.game_id}: {str(e)}")
        
        if errors and not results:
            # All predictions failed
            raise PredictionError(f"All batch predictions failed: {'; '.join(errors)}")
        elif errors:
            # Some predictions failed, but we'll return the successful ones
            logger.warning(f"Some batch predictions failed: {'; '.join(errors)}")
        
        return results
    
    async def evaluate(self, input_data: PredictionInput, actual_result: str) -> Dict[str, Any]:
        """
        Evaluate the model's performance after the actual game result is known.
        
        This can be used for model calibration and continuous improvement.
        
        Args:
            input_data: The original prediction input
            actual_result: The actual outcome (e.g., "win" or "loss" in reference to the pick)
            
        Returns:
            Dictionary with evaluation metrics
            
        Raises:
            ValueError: If input data or actual result is invalid
        """
        # Generate a prediction if we don't already have one
        prediction = await self.predict(input_data)
        
        # Determine if the prediction was correct
        is_correct = actual_result.lower() == "win"
        
        # Calculate confidence calibration metrics
        confidence_error = abs((1.0 if is_correct else 0.0) - prediction.confidence)
        
        # Return evaluation metrics
        return {
            "game_id": input_data.game_id,
            "prediction": prediction.pick,
            "actual_result": actual_result,
            "is_correct": is_correct,
            "confidence": prediction.confidence,
            "confidence_error": confidence_error,
            "evaluation_time": datetime.now().isoformat()
        }


# Factory function to create a prediction model
def create_langchain_prediction_model(
    model_name: str = DEFAULT_MODEL,
    provider: str = "openai",
    temperature: float = 0.3,
    agent_id: str = "langchain-llm-v1"
) -> LangChainPredictionModel:
    """
    Factory function to create and configure a LangChain prediction model.
    
    Args:
        model_name: Name of the LLM model to use
        provider: Provider to use ('openai' or 'groq')
        temperature: Temperature setting for generation
        agent_id: Unique identifier for the agent
        
    Returns:
        Configured LangChainPredictionModel instance
    """
    return LangChainPredictionModel(
        model_name=model_name,
        provider=provider,
        temperature=temperature,
        agent_identifier=agent_id
    )