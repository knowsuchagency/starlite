from __future__ import annotations

from pydantic import BaseModel

from starlite.dto.pydantic import PydanticFactory


class MyClass(BaseModel):
    first: int
    second: int


class MyClassDTO(PydanticFactory[MyClass]):
    third: str
