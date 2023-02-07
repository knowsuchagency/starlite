from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING

from starlite.types import IsDataclass
from starlite.utils.model import convert_dataclass_to_model
from starlite.utils.predicates import is_dataclass_class_or_instance

from . import PluginProtocol

if TYPE_CHECKING:
    from typing import Any, TypeGuard  # noqa:TC004

    from pydantic import BaseModel


class DataclassPlugin(PluginProtocol[IsDataclass]):
    """Plugin for dataclass object models."""

    @staticmethod
    def is_plugin_supported_type(value: Any) -> TypeGuard[IsDataclass]:
        """Is ``value`` a type managed by the plugin?

        Args:
            value: anything.

        Returns:
            Boolean indicating if ``value`` is a type or instance of a dataclass.
        """
        return is_dataclass_class_or_instance(value)

    def to_pydantic_model_class(self, model_class: type[IsDataclass], **kwargs: Any) -> type[BaseModel]:
        """Produce a pydantic model from ``model_class``.

        Args:
            model_class: the dataclass model type.
            **kwargs: not used in this implementation

        Returns:
            A pydantic model to represent the dataclass model.
        """
        return convert_dataclass_to_model(model_class)

    def from_pydantic_model_instance(
        self, model_class: type[IsDataclass], pydantic_model_instance: BaseModel
    ) -> IsDataclass:
        """Create an instance of the dataclass model type from a pydantic model instance.

        Args:
            model_class: dataclass model type.
            pydantic_model_instance: DTO instance that represents model data.

        Returns:
            Instance of the model type, populated with DTO data.
        """
        return model_class(**pydantic_model_instance.dict())

    def to_dict(self, model_instance: IsDataclass) -> dict[str, Any]:
        """Convert ``model_instance`` to a dict representation.

        Args:
            model_instance: a dataclass instance.

        Returns:
            A dict representation of ``model_instance``.
        """
        return asdict(model_instance)

    def from_dict(self, model_class: type[IsDataclass], **kwargs: Any) -> IsDataclass:
        """Create an instance of the model dataclass from ``kwargs``.

        Args:
            model_class: dataclass model type.
            **kwargs: k/v pairs to be set on the instance.

        Returns:
            Instance of model dataclass populated with ``kwargs``.
        """
        return model_class(**kwargs)
