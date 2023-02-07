from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from starlite.types.protocols import IsDataclass

DataclassT = TypeVar("DataclassT", bound=IsDataclass)
PydanticT = TypeVar("PydanticT", bound=BaseModel)
