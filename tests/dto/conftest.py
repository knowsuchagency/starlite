from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from typing_extensions import Annotated

from starlite.dto.dataclasses import DataclassFactory
from tests.dto import CompositeDC

if TYPE_CHECKING:
    from typing import Any

    from starlite import dto
    from tests.dto.types import CreateDTOType, DCFactoryType


@pytest.fixture
def raw_composite() -> dict[str, Any]:
    """Raw representation of our composite data model defined in ``tests.dto``"""
    return {
        "d": {
            "a": 1.01,
            "b": "string",
            "c": [0, 1, 2, 3],
        }
    }


@pytest.fixture
def create_dto() -> CreateDTOType:
    """Callable that gives us a ready-to-use DTO factory type."""

    def dto_creator(config: dto.Config) -> type[DCFactoryType]:
        return DataclassFactory[Annotated[CompositeDC, config]]

    return dto_creator
