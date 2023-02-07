from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel
from sqlalchemy.orm import DeclarativeMeta

from starlite.types.protocols import IsDataclass

DataclassT = TypeVar("DataclassT", bound=IsDataclass)
PydanticT = TypeVar("PydanticT", bound=BaseModel)
SQLAlchemyT = TypeVar("SQLAlchemyT", bound=DeclarativeMeta)
