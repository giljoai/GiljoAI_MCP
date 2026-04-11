# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Base classes and utility functions for SQLAlchemy models.

This module provides the foundational elements used by all other model modules:
- Base: The declarative base for all models
- Utility functions: generate_uuid, generate_project_alias
"""

from uuid import uuid4

from sqlalchemy.orm import declarative_base


Base = declarative_base()


def generate_uuid() -> str:
    """Generate a string UUID for cross-database compatibility."""
    return str(uuid4())


def generate_project_alias() -> str:
    """
    Generate a unique 6-character alphanumeric project alias.

    Format: A-Z0-9, 6 characters (e.g., "A1B2C3")

    This function is used as a default callable for new Project instances.
    Database-level uniqueness is enforced by the unique index on the alias column.

    Returns:
        str: 6-character alphanumeric alias
    """
    import random
    import string

    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=6))
