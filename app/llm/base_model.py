"""
@file: base_model.py
@description:
Defines the abstract base class interface for all prediction models in the BadBeats system.
This module establishes the contract that all predictive models must follow, enabling
a modular, pluggable architecture where different model types (LangChain, ML models, etc.)
can be integrated seamlessly.

@dependencies:
- abc: For abstract base class functionality
- typing: For type hints
- pydantic: For data validation

@notes:
- Each prediction model implementation must inherit from BasePredictionModel
- The predict method must be implemented by all concrete model classes
- Models should handle their own validation and error cases
- The abstract predict method defines the common input/output contract
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field


class PredictionInput(BaseModel):
    """Schema for standardized prediction input data."""
    game_id: int = Field(..., description="Unique identifier for the game")
    home_team: str = Field(..., description="Home team name")
    away_team: str = Field(..., description="Away team name")
    spread: float = Field(..., description="Current point spread (positive means home team is underdog)")
    game_date: str = Field(..., description="Date and time of the game (ISO format)")
    structured_data: Dict[str, Any] = Field(
        default={},
        description="Structured data for the game (team stats, player stats, odds data)"
    )
    unstructured_data: Dict[str, Any] = Field(
        default={},
        description="Unstructured data (news, injury reports, narratives)"
    )


class PredictionResult(BaseModel):
    """Schema for standardized prediction output data."""
    agent_id: str = Field(..., description="Identifier for the model/agent making the prediction")
    game_id: int = Field(..., description="Unique identifier for the game")
    pick: str = Field(..., description="Team and spread, e.g. 'Lakers -4'")
    logic: str = Field(..., description="Explanation of the reasoning behind the prediction")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score from 0 to 1")
    result: str = Field("pending", description="Outcome of the prediction")
    metadata: Dict[str, Any] = Field(default={}, description="Additional model-specific metadata")


class BasePredictionModel(ABC):
    """
    Abstract base class that defines the interface for all prediction models.
    
    Any concrete prediction model implementation must inherit from this class
    and implement the predict method according to the defined contract.
    """
    
    @property
    @abstractmethod
    def agent_id(self) -> str:
        """
        Returns a unique identifier for this prediction model/agent.
        
        Each model implementation should have a unique ID to distinguish
        its predictions from others in the system.
        """
        pass
    
    @abstractmethod
    async def predict(self, input_data: PredictionInput) -> PredictionResult:
        """
        Generate a prediction based on the provided input data.
        
        Args:
            input_data: PredictionInput containing all necessary game information
                       and contextual data needed for making a prediction.
        
        Returns:
            PredictionResult containing the prediction details, including the pick,
            confidence score, and explanation.
            
        Raises:
            ValueError: If the input data is invalid or insufficient
            Exception: If prediction generation fails
        """
        pass
    
    @abstractmethod
    async def batch_predict(self, inputs: List[PredictionInput]) -> List[PredictionResult]:
        """
        Generate predictions for multiple games in batch.
        
        Implementations may optimize batch processing for better performance.
        
        Args:
            inputs: List of PredictionInput objects
            
        Returns:
            List of PredictionResult objects in the same order as the inputs
            
        Raises:
            ValueError: If any input data is invalid
            Exception: If prediction generation fails
        """
        pass
    
    @abstractmethod
    async def evaluate(self, input_data: PredictionInput, actual_result: str) -> Dict[str, Any]:
        """
        Evaluate the model's performance on a specific game after the actual result is known.
        
        This method may be used for model calibration and improvement over time.
        
        Args:
            input_data: The original prediction input
            actual_result: The actual outcome of the game
            
        Returns:
            Dictionary containing evaluation metrics
            
        Raises:
            ValueError: If the input data or actual result is invalid
        """
        pass