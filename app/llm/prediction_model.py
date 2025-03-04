"""
/**
 * @file: prediction_model.py
 * @description 
 * This module implements a simple prediction model using direct OpenAI API calls,
 * replacing the LangChain-based implementation. It generates ATS predictions for
 * NBA games based on structured and unstructured data.
 * 
 * Key features:
 * - Direct LLM Integration: Uses OpenAI API for predictions without LangChain.
 * - Data-Driven Predictions: Incorporates game stats, news, and injuries.
 * - Simplified Interface: Maintains compatibility with BasePredictionModel.
 * 
 * @dependencies
 * - openai: For direct LLM calls.
 * - app.llm.base_model: For prediction interface and schemas.
 * - app.core.logger: For logging.
 * - os, json: For environment and data handling.
 * 
 * @notes
 * - Requires OPENAI_API_KEY in environment variables.
 * - Confidence calibration is applied to raw LLM outputs.
 * - Error handling retries API calls up to 3 times.
 * - Assumes a basic prompt; refine for production use.
 */
"""

import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential

import openai
from app.llm.base_model import BasePredictionModel, PredictionInput, PredictionResult
from app.core.logger import setup_logger

# Initialize logger
logger = setup_logger("app.llm.prediction_model")

# Load environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment variables")

# Initialize OpenAI client
client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)

class SimplePredictionModel(BasePredictionModel):
    """
    A simple prediction model using direct OpenAI API calls.

    Attributes:
        model_name (str): The OpenAI model to use.
        temperature (float): Sampling temperature for LLM.
        max_tokens (int): Maximum tokens for response.
        agent_id (str): Unique identifier for this model.
    """

    def __init__(
        self,
        model_name: str = "gpt-4",
        temperature: float = 0.3,
        max_tokens: int = 2000,
        agent_id: str = "simple-llm-v1"
    ):
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._agent_id = agent_id
        logger.info(f"Initialized SimplePredictionModel with model {model_name}")

    @property
    def agent_id(self) -> str:
        """Return the unique identifier for this model."""
        return self._agent_id

    def _prepare_prompt(self, input_data: PredictionInput) -> str:
        """
        Prepare the prompt for the LLM with game data.

        Args:
            input_data: Prediction input containing game details.

        Returns:
            str: Formatted prompt string.
        """
        game_date = datetime.fromisoformat(input_data.game_date).strftime("%A, %B %d, %Y at %I:%M %p")
        spread_value = abs(input_data.spread)
        favorite = input_data.home_team if input_data.spread <= 0 else input_data.away_team
        underdog = input_data.away_team if input_data.spread <= 0 else input_data.home_team
        spread_desc = f"{favorite} favored by {spread_value} points"

        home_stats = self._format_stats(input_data.structured_data.get("home_team_stats", []))
        away_stats = self._format_stats(input_data.structured_data.get("away_team_stats", []))
        home_injuries = self._format_injuries(input_data.unstructured_data.get("home_team_injuries", []))
        away_injuries = self._format_injuries(input_data.unstructured_data.get("away_team_injuries", []))
        home_news = self._format_news(input_data.unstructured_data.get("home_team_news", []))
        away_news = self._format_news(input_data.unstructured_data.get("away_team_news", []))

        prompt = f"""
You are an NBA betting expert. Predict which team will cover the spread for this game:
- Game ID: {input_data.game_id}
- Matchup: {input_data.away_team} @ {input_data.home_team}
- Date: {game_date}
- Spread: {spread_desc}

Home Team ({input_data.home_team}) Stats:
{home_stats}

Away Team ({input_data.away_team}) Stats:
{away_stats}

Injuries:
- {input_data.home_team}: {home_injuries}
- {input_data.away_team}: {away_injuries}

News:
- {input_data.home_team}: {home_news}
- {input_data.away_team}: {away_news}

Return a JSON object with:
- "pick": Team and spread (e.g., "Lakers -4")
- "logic": Reasoning paragraph
- "confidence": Float between 0 and 1
"""
        return prompt

    def _format_stats(self, stats: List[Dict[str, Any]]) -> str:
        """Format team statistics into a string."""
        if not stats:
            return "No stats available."
        stat = stats[0]
        return f"Points: {stat.get('pts', 'N/A')}, Rebounds: {stat.get('reb', 'N/A')}, Assists: {stat.get('ast', 'N/A')}"

    def _format_injuries(self, injuries: List[Dict[str, Any]]) -> str:
        """Format injury reports into a string."""
        if not injuries:
            return "No injuries reported."
        return "; ".join(f"{i.get('player', 'Unknown')}: {i.get('status', 'Unknown')}" for i in injuries)

    def _format_news(self, news: List[Dict[str, Any]]) -> str:
        """Format news summaries into a string."""
        if not news:
            return "No recent news."
        return "; ".join(f"{n.get('title', 'Untitled')}: {n.get('summary', 'N/A')}" for n in news[:3])

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def predict(self, input_data: PredictionInput) -> PredictionResult:
        """
        Generate a prediction using the OpenAI API.

        Args:
            input_data: Prediction input data.

        Returns:
            PredictionResult: Generated prediction.

        Raises:
            Exception: If prediction fails after retries.
        """
        logger.info(f"Generating prediction for game {input_data.game_id}")
        prompt = self._prepare_prompt(input_data)

        try:
            response = await client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are an NBA betting expert."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"}
            )
            raw_response = response.choices[0].message.content
            pred_data = json.loads(raw_response)

            confidence = max(0.0, min(1.0, float(pred_data.get("confidence", 0.5))))
            calibrated_confidence = self._calibrate_confidence(confidence)

            return PredictionResult(
                agent_id=self.agent_id,
                game_id=input_data.game_id,
                pick=pred_data.get("pick", ""),
                logic=pred_data.get("logic", ""),
                confidence=calibrated_confidence,
                result="pending",
                metadata={"model": self.model_name, "timestamp": datetime.now().isoformat()}
            )
        except Exception as e:
            logger.error(f"Prediction failed for game {input_data.game_id}: {str(e)}")
            raise

    async def batch_predict(self, inputs: List[PredictionInput]) -> List[PredictionResult]:
        """
        Generate predictions for multiple games.

        Args:
            inputs: List of prediction inputs.

        Returns:
            List[PredictionResult]: List of predictions.
        """
        results = []
        for input_data in inputs:
            try:
                result = await self.predict(input_data)
                results.append(result)
            except Exception as e:
                logger.error(f"Batch predict failed for game {input_data.game_id}: {str(e)}")
        return results

    async def evaluate(self, input_data: PredictionInput, actual_result: str) -> Dict[str, Any]:
        """
        Evaluate prediction accuracy.

        Args:
            input_data: Original prediction input.
            actual_result: Actual game outcome ("win" or "loss").

        Returns:
            Dict[str, Any]: Evaluation metrics.
        """
        prediction = await self.predict(input_data)
        is_correct = actual_result.lower() == "win"
        confidence_error = abs((1.0 if is_correct else 0.0) - prediction.confidence)

        return {
            "game_id": input_data.game_id,
            "prediction": prediction.pick,
            "actual_result": actual_result,
            "is_correct": is_correct,
            "confidence": prediction.confidence,
            "confidence_error": confidence_error
        }

    def _calibrate_confidence(self, raw_confidence: float) -> float:
        """Calibrate raw confidence scores."""
        mean = 0.7
        regression_strength = 0.3
        calibrated = (1 - regression_strength) * raw_confidence + regression_strength * mean
        return max(0.0, min(1.0, calibrated))

def create_prediction_model(
    model_name: str = "gpt-4",
    temperature: float = 0.3,
    agent_id: str = "simple-llm-v1"
) -> SimplePredictionModel:
    """
    Factory function to create a prediction model instance.

    Args:
        model_name: OpenAI model name.
        temperature: Sampling temperature.
        agent_id: Unique identifier.

    Returns:
        SimplePredictionModel: Configured model instance.
    """
    return SimplePredictionModel(model_name=model_name, temperature=temperature, agent_id=agent_id)