"""
LLM Package for BadBeats Backend.

This package handles all Large Language Model (LLM) integrations and implementations,
including LangChain pipelines and other ML models for generating betting predictions.

The package provides:
- Base prediction model interface for standardization
- LangChain implementation for generating predictions
- Factory functions for model creation
- Supporting utilities for prompt engineering and data processing
"""

# Export base model classes
from .base_model import BasePredictionModel, PredictionInput, PredictionResult

# Export LangChain model implementation
from .langchain_model import (
    LangChainPredictionModel,
    create_langchain_prediction_model,
    PredictionError
)

# Define package exports
__all__ = [
    # Base interface
    "BasePredictionModel",
    "PredictionInput",
    "PredictionResult",
    
    # Implementation
    "LangChainPredictionModel",
    "create_langchain_prediction_model",
    "PredictionError"
]