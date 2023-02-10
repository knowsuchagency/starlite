from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, Generic, TypeVar

from pydantic import BaseModel, create_model

from starlite.utils.predicates import is_type_or_instance_of
from starlite.utils.serialization import decode_json

from .base import ModelT, SerializationPluginProtocol
from .utils import get_field_type, remap_field

if TYPE_CHECKING:
    from typing import Any, Mapping, TypeGuard

    from starlite.enums import RequestEncodingType


class FromPydantic(ABC, SerializationPluginProtocol[ModelT, BaseModel], Generic[ModelT]):
    """Plugins that use pydantic as transfer type."""

    @staticmethod
    def container_instance_to_dict(container_instance: BaseModel) -> dict[str, Any]:
        """Convert ``container_instance`` to dict.

        Args
            container_instance: the container instance

        Returns
            dict representation of container instance
        """
        return container_instance.dict()

    @staticmethod
    def parse_container_type_from_raw(
        container_type: type[BaseModel],
        buffer: bytes,
        media_type: RequestEncodingType | str,
    ) -> BaseModel:
        """Parse an instance of ``container_type`` from raw bytes.

        Args
            container_type: a container model type
            buffer: bytes to be parsed into instance
            media_type: format of the raw data

        Returns
            Instance of ``container_type``.
        """
        return decode_json(buffer, container_type)

    @staticmethod
    def parse_container_type_array_from_raw(
        container_type: type[BaseModel],
        buffer: bytes,
        media_type: RequestEncodingType | str,
    ) -> list[BaseModel]:
        """Parse an array of ``container_type`` from raw bytes.

        Args
            container_type: a container model type
            buffer: bytes to be parsed into instance
            media_type: format of the raw data

        Returns
            List of ``container_type`` instances.
        """
        return decode_json(buffer, list[container_type])  # type:ignore[valid-type]


PydanticModelT = TypeVar("PydanticModelT", bound=BaseModel)


class PydanticPlugin(FromPydantic[BaseModel]):
    """Plugin for deserializing into pydantic models, that uses pydantic as a transfer type."""

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
        self,
        model_class: type[PydanticModelT],
        exclude: set[str] | None = None,
        field_mappings: Mapping[str, str | tuple[str, Any]] | None = None,
        fields: dict[str, tuple[Any, Any]] | None = None,
        localns: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> type[BaseModel]:
        """Produce a pydantic model from ``model_class``.

        :param model_class: The model class that serves as a basis.
        :param exclude: do not include fields of these names in the model.
        :param field_mappings: to rename, and re-type fields.
        :param fields: additional fields to add to the container model.
        :param kwargs: Any kwargs.
        :param localns: Mapping of names to types for forward ref. resolution.
        :return: The generated data container class.
        """
        model_class.update_forward_refs(localns=localns)
        exclude = exclude or set()
        field_mappings = field_mappings or {}
        fields = fields or {}
        for field_name, model_field in model_class.__fields__.items():
            if field_name in exclude:
                continue
            field_type = get_field_type(model_field=model_field)
            if field_name in field_mappings:
                field_name, field_type = remap_field(field_mappings, field_name, field_type)
            fields[field_name] = field_type, model_field.field_info
        return create_model(
            model_class.__name__,
            __config__=None,
            __base__=None,
            __module__=model_class.__module__,
            __validators__={},
            __cls_kwargs__={},
            **fields,
        )

    def from_data_container_instance(
        self, model_class: type[PydanticModelT], data_container_instance: BaseModel
    ) -> PydanticModelT:
        """Create an instance of the pydantic model type from a pydantic model instance.

        Args:
            model_class: pydantic model type.
            data_container_instance: DTO instance that represents model data.

        Returns:
            Instance of the model type, populated with DTO data.
        """
        return model_class(**data_container_instance.dict())

    def to_dict(self, model_instance: PydanticModelT) -> dict[str, Any]:
        """Convert ``model_instance`` to a dict representation.

        Args:
            model_instance: a pydantic instance.

        Returns:
            A dict representation of ``model_instance``.
        """
        return model_instance.dict()

    def from_dict(self, model_class: type[PydanticModelT], **kwargs: Any) -> PydanticModelT:
        """Create an instance of the model from ``kwargs``.

        Args:
            model_class: pydantic model type.
            **kwargs: k/v pairs to be set on the instance.

        Returns:
            Instance of model pydantic populated with ``kwargs``.
        """
        return model_class.parse_obj(kwargs)
