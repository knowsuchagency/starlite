from __future__ import annotations

from typing import Generic

from starlite.plugins.dataclasses import DataclassPlugin

from .factory import Factory
from .types import DataclassT

__all__ = ("DataclassFactory",)


class DataclassFactory(Factory[DataclassT], Generic[DataclassT]):
    """DTO Factory for dataclass models."""

    plugin_type = DataclassPlugin
