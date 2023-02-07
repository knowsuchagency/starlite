from __future__ import annotations

from typing import ClassVar

from starlite.plugins.dataclasses import DataclassPlugin

from .factory import Factory
from .types import DataclassT

__all__ = ("DataclassFactory",)


class DataclassFactory(Factory[DataclassT]):
    plugin: ClassVar[DataclassPlugin] = DataclassPlugin()
