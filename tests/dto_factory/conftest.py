from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any, Dict, Type, TypeGuard, TypeVar

import pytest
from pydantic import BaseModel

from starlite import dto
from starlite.utils.model import convert_dataclass_to_model
from starlite.utils.predicates import is_dataclass_class_or_instance

if TYPE_CHECKING:
    from starlite.plugins import PluginProtocol


class DataclassPlugin(PluginProtocol[dataclass]):
    @staticmethod
    def is_plugin_supported_type(value: Any) -> TypeGuard[dataclass]:
        return is_dataclass_class_or_instance(value)

    def to_pydantic_model_class(self, model_class: Type[dataclass], **kwargs: Any) -> Type[BaseModel]:
        return convert_dataclass_to_model(model_class)

    def from_pydantic_model_instance(
        self, model_class: Type[dataclass], pydantic_model_instance: BaseModel
    ) -> DataclassT:
        return model_class(**pydantic_model_instance.dict())

    def to_dict(self, model_instance: dataclass) -> Dict[str, Any]:
        return asdict(model_instance)

    def from_dict(self, model_class: Type[dataclass], **kwargs: Any) -> dataclass:
        return model_class(**kwargs)


DataclassT = TypeVar("DataclassT", bound=dataclass)


class DataclassDTO(dto.Factory[Type[DataclassT]]):
    plugins = DataclassPlugin


@dataclass()
class Model1:
    a: int
    b: str


@dataclass()
class Model2:
    c: float
    one: Model1


@pytest.fixture()
def dto() -> type[DataclassDTO[Model2]]:
    """A dto instance."""
    return DataclassDTO[Model2]
