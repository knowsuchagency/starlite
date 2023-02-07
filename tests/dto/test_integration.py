from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from starlite import dto
from tests.dto import CompositeDC

if TYPE_CHECKING:
    from typing import Any

    from tests.dto.types import CreateDTOType


def test_dto_from_raw_data(create_dto: CreateDTOType, raw_composite: dict[str, Any]) -> None:
    """Test that given correct raw data we construct expected instance of the model."""
    dto_type = create_dto(dto.Config())
    dto_instance = dto_type.parse_obj(raw_composite)
    assert CompositeDC() == dto_instance.to_model_instance()


def test_dto_from_raw_data_validation_error(create_dto: CreateDTOType, raw_composite: dict[str, Any]) -> None:
    """Test incorrect data raises a validation error."""
    raw_composite["d"]["a"] = "one-point-oh-one"
    dto_type = create_dto(dto.Config())
    with pytest.raises(ValidationError):
        dto_type.parse_obj(raw_composite)
