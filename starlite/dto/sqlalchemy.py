from __future__ import annotations

from starlite.plugins.sql_alchemy import SQLAlchemyPlugin

from .factory import Factory
from .types import SQLAlchemyT

__all__ = ("SQLAlchemyFactory",)


class SQLAlchemyFactory(Factory[SQLAlchemyT]):
    """A DTO Factory type for dataclasses models."""

    plugin_type = SQLAlchemyPlugin
