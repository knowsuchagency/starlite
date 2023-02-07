from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Callable, TypeAlias

    from starlite import dto
    from starlite.dto.dataclasses import DataclassFactory
    from tests.dto import CompositeDC

DCFactoryType: TypeAlias = "DataclassFactory[CompositeDC]"
CreateDTOType: TypeAlias = "Callable[[dto.Config], type[DCFactoryType]]"
