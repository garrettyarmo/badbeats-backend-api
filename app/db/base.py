"""
SQLAlchemy Base Definition Module.

This module defines the SQLAlchemy declarative base that all models will inherit from.
It sets up the foundation for the Object-Relational Mapping (ORM) functionality
throughout the application.

The declarative base allows models to be defined as Python classes,
which then map to database tables via SQLAlchemy's ORM.
"""

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import registry

# Create a new SQLAlchemy mapper registry
mapper_registry = registry()

# Create the base class for declarative class definitions
Base = declarative_base(metadata=mapper_registry.metadata)