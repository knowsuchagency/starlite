from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from starlite import dto
from tests.dto import CompositeDC

if TYPE_CHECKING:
    from tests.dto.types import CreateDTOType


def test_dto_from_raw_data(create_dto: CreateDTOType, raw_composite: bytes) -> None:
    """Test that given correct raw data we construct expected instance of the model."""
    dto_type = create_dto(dto.Config())
    dto_instance = dto_type.from_buffer(raw_composite, "application/json")
    assert CompositeDC() == dto_instance.to_model()


def test_dto_from_raw_data_validation_error(create_dto: CreateDTOType) -> None:
    """Test incorrect data raises a validation error."""
    raw = b'{"d":{"a":"one-point-oh-one","b":"string","c":[0, 1, 2, 3]}}'
    dto_type = create_dto(dto.Config())
    with pytest.raises(ValidationError):
        dto_type._transfer_type.parse_obj(raw)
