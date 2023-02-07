from __future__ import annotations

from typing import TypeVar

from starlite.types.protocols import IsDataclass

DataclassT = TypeVar("DataclassT", bound=IsDataclass)
