from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel

from starlite import dto
from starlite.dto.pydantic import PydanticFactory


class MyClass(BaseModel):
    first: int
    second: int


MyClassDTO = PydanticFactory[
    Annotated[
        MyClass,
        dto.Config(
            field_mapping={
                "first": "third",
                "second": ("fourth", float),
            }
        ),
    ]
]
