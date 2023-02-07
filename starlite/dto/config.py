from __future__ import annotations

from dataclasses import dataclass, field


@dataclass()
class Config:
    """A configuration type for DTO factory models."""

    exclude: set[str] = field(default_factory=set)
    field_mapping: dict[str, str] = field(default_factory=dict)
