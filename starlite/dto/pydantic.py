from __future__ import annotations

from typing import ClassVar

from starlite.plugins.pydantic import PydanticPlugin

from .factory import Factory
from .types import PydanticT

__all__ = ("PydanticFactory",)


class PydanticFactory(Factory[PydanticT]):
    """A DTO Factory type for dataclasses models."""

    plugin: ClassVar[PydanticPlugin] = PydanticPlugin()
