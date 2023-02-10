"""Types for transferring data to and from domain models.

Example:
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

    ModelDTO = DataclassDTO[Model2]

    # to add fields onto a DTO
    class ModelDTO(DataclassDTO[Model]):
        new: int
        fields: str

    dto = ModelDTO.parse_obj({})
    assert dto._model_type is Model
    assert isinstance(dto.to_model(), Model)
"""
from .config import Config
from .factory import Factory

__all__ = (
    "Config",
    "Factory",
)
