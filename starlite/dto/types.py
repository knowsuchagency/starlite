from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel
from sqlalchemy.orm import DeclarativeMeta

from starlite.types.protocols import DataclassProtocol

DataclassT = TypeVar("DataclassT", bound=DataclassProtocol)
PydanticT = TypeVar("PydanticT", bound=BaseModel)
SQLAlchemyT = TypeVar("SQLAlchemyT", bound=DeclarativeMeta)
