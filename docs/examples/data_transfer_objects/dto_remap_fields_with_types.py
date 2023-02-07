from __future__ import annotations

from pydantic import BaseModel
from typing_extensions import Annotated

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
