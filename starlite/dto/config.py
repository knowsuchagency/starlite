from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any


@dataclass()
class Config:
    """A configuration type for DTO factory models."""

    exclude: set[str] = field(default_factory=set)
    field_mapping: dict[str, str] = field(default_factory=dict)
    fields: dict[str, tuple[Any, Any]] = field(default_factory=dict)
