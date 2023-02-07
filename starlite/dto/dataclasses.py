from __future__ import annotations

from typing import ClassVar

from starlite.plugins.dataclasses import DataclassPlugin

from .types import DataclassT
from .factory import Factory

__all__ = ("DataclassDTOFactory",)


class DataclassDTOFactory(Factory[DataclassT]):
    plugin: ClassVar[DataclassPlugin] = DataclassPlugin()
