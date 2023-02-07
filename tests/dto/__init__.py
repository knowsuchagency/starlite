from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DC:
    a: float = 1.01
    b: str = "string"
    c: list[int] = field(default_factory=lambda: [0, 1, 2, 3])


@dataclass
class CompositeDC:
    d: DC = field(default_factory=lambda: DC())
