from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, create_model

from starlite.utils.predicates import is_type_or_instance_of

from . import SerializationPluginProtocol

if TYPE_CHECKING:
    from typing import Any, TypeGuard  # noqa:TC004


class PydanticPlugin(SerializationPluginProtocol[BaseModel, BaseModel]):
    """Plugin for pydantic object models."""

    @staticmethod
    def is_plugin_supported_type(value: Any) -> TypeGuard[BaseModel]:
        """Is ``value`` a type managed by the plugin?

        Args:
            value: anything.

        Returns:
            Boolean indicating if ``value`` is a type or instance of a pydantic.
        """
        return is_type_or_instance_of(value, BaseModel)

    def to_data_container_class(
        self, model_class: type[BaseModel], localns: dict[str, Any] | None = None, **kwargs: Any
    ) -> type[BaseModel]:
        """Produce a pydantic model from ``model_class``.

        Args:
            model_class: the pydantic model type.
            localns: used for forward ref resolution.
            **kwargs: not used in this implementation

        Returns:
            A pydantic model to represent the pydantic model.
        """
        model_class.update_forward_refs(localns=localns)
        return create_model(
            model_class.__name__,
            __config__=None,
            __base__=model_class,
            __module__=model_class.__module__,
            __validators__={},
            __cls_kwargs__={},
        )

    def from_data_container_instance(
        self, model_class: type[BaseModel], data_container_instance: BaseModel
    ) -> BaseModel:
        """Create an instance of the pydantic model type from a pydantic model instance.

        Args:
            model_class: pydantic model type.
            data_container_instance: DTO instance that represents model data.

        Returns:
            Instance of the model type, populated with DTO data.
        """
        return model_class(**data_container_instance.dict())

    def to_dict(self, model_instance: BaseModel) -> dict[str, Any]:
        """Convert ``model_instance`` to a dict representation.

        Args:
            model_instance: a pydantic instance.

        Returns:
            A dict representation of ``model_instance``.
        """
        return model_instance.dict()

    def from_dict(self, model_class: type[BaseModel], **kwargs: Any) -> BaseModel:
        """Create an instance of the model pydantic from ``kwargs``.

        Args:
            model_class: pydantic model type.
            **kwargs: k/v pairs to be set on the instance.

        Returns:
            Instance of model pydantic populated with ``kwargs``.
        """
        return model_class(**kwargs)
