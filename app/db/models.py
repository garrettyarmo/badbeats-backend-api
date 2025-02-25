"""
@file: models.py
@description: 
This file defines SQLAlchemy ORM models for the BadBeats Backend API. 
Currently, it includes the Prediction model/table, which stores AI-driven
sports betting picks and associated metadata.

@notes:
- Adheres to project guidelines requiring UUID primary keys and timestamp fields.
- Additional models can be added in the future to handle user data, 
  historical stats, or extended prediction data.

@dependencies:
- SQLAlchemy: for defining ORM models.
- app.db.base: provides the Base class (declarative_base).
- project env (.env) must define DATABASE_URL, among other environment variables.
- python-dotenv or another approach is used to load .env data.

@assumptions:
- The database is PostgreSQL, and the SQLAlchemy dialect is configured 
  for PostgreSQL usage in session.py.
- All migrations will be handled via Alembic.

@limitations:
- The current schema is minimal and only stores predictions. Future 
  enhancements (user or subscription models) will be added as needed.
"""

import uuid
from sqlalchemy import Column, String, Text, Float, DateTime, func, Integer
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base

class Prediction(Base):
    """
    @class Prediction
    @description
    SQLAlchemy model representing an AI-generated sports betting pick. 
    This model stores essential prediction details (spread pick, logic, 
    confidence, etc.) that can be served via API or analyzed for accuracy.

    @attributes:
        id (UUID): Primary key (uuid4).
        agent_id (Integer): Identifies the model/agent making the prediction.
        game_id (Integer): Unique identifier for the game (indexed for fast queries).
        pick (String): The chosen team and spread (e.g., "Lakers -4").
        logic (Text): Detailed explanation of the AI's reasoning.
        confidence (Float): Numerical confidence score (0 to 1).
        result (String): Outcome of the prediction, defaults to "pending".
        created_at (DateTime): Timestamp of creation, defaults to current time.
        updated_at (DateTime): Timestamp of last update, auto-updates on row changes.

    @notes:
    - The `created_at` field is automatically set upon insertion via server_default=func.now().
    - The `updated_at` field is automatically updated when the row is modified.
    - Additional indexes or constraints may be added for performance or data integrity.
    """
    __tablename__ = "predictions"

    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        doc="Primary key using UUID4."
    )
    agent_id = Column(
        Integer,
        nullable=False,
        doc="Identifies the model or agent generating the prediction."
    )
    game_id = Column(
        Integer,
        nullable=False,
        index=True,
        doc="Unique identifier for the game; indexed for faster lookups."
    )
    pick = Column(
        String,
        nullable=False,
        doc="Team and spread (e.g., 'Lakers -4')."
    )
    logic = Column(
        Text,
        nullable=False,
        doc="Detailed reasoning or explanation for the pick."
    )
    confidence = Column(
        Float,
        nullable=False,
        doc="Numerical confidence score ranging from 0.0 to 1.0."
    )
    result = Column(
        String,
        nullable=False,
        default="pending",
        doc="Holds the final outcome of the prediction (e.g., 'win', 'loss', or 'pending')."
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Timestamp of when the record was created."
    )
    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now(),
        doc="Timestamp of the last update to this record."
    )
