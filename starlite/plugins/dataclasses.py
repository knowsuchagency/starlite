from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Type, TypeGuard

from pydantic import BaseModel

from starlite.types import IsDataclass
from starlite.utils.model import convert_dataclass_to_model
from starlite.utils.predicates import is_dataclass_class_or_instance

from . import PluginProtocol


class DataclassPlugin(PluginProtocol[IsDataclass]):
    @staticmethod
    def is_plugin_supported_type(value: Any) -> TypeGuard[IsDataclass]:
        return is_dataclass_class_or_instance(value)

    def to_pydantic_model_class(self, model_class: Type[IsDataclass], **kwargs: Any) -> Type[BaseModel]:
        return convert_dataclass_to_model(model_class)

    def from_pydantic_model_instance(
        self, model_class: Type[IsDataclass], pydantic_model_instance: BaseModel
    ) -> IsDataclass:
        return model_class(**pydantic_model_instance.dict())

    def to_dict(self, model_instance: IsDataclass) -> Dict[str, Any]:
        return asdict(model_instance)

    def from_dict(self, model_class: Type[IsDataclass], **kwargs: Any) -> IsDataclass:
        return model_class(**kwargs)
