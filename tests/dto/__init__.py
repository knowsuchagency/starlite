from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from typing_extensions import TypeAlias

ListInt: TypeAlias = "List[int]"


@dataclass
class DC:
    a: float = 1.01
    b: str = "string"
    c: ListInt = field(default_factory=lambda: [0, 1, 2, 3])


@dataclass
class CompositeDC:
    d: DC = field(default_factory=lambda: DC())
