from typing import TYPE_CHECKING, TypeVar

import anyio
from pydantic_factories.utils import is_pydantic_model
from pydantic_openapi_schema.utils.utils import OpenAPI310PydanticSchema
from tortoise.fields import ReverseRelation
from tortoise.fields.relational import RelationalField

from starlite.exceptions import MissingDependencyException
from starlite.plugins.base import (
    OpenAPISchemaPluginProtocol,
    SerializationPluginProtocol,
)
from starlite.utils.serialization import decode_json

try:
    from tortoise import Model, ModelMeta  # type: ignore[attr-defined]
    from tortoise.contrib.pydantic import (  # type: ignore[attr-defined]
        PydanticModel,
        pydantic_model_creator,
    )
except ImportError as e:
    raise MissingDependencyException("tortoise-orm is not installed") from e

if TYPE_CHECKING:
    from typing import Any, Mapping

    from pydantic_openapi_schema.v3_1_0 import Schema
    from typing_extensions import TypeGuard

    from starlite.enums import RequestEncodingType


TortoiseModelT = TypeVar("TortoiseModelT", bound="Model")


class TortoiseORMPlugin(SerializationPluginProtocol[Model, PydanticModel], OpenAPISchemaPluginProtocol[Model]):
    """Support (de)serialization and OpenAPI generation for Tortoise ORMtypes."""

    _models_map: "dict[type[Model], type[PydanticModel]]" = {}
    _data_models_map: "dict[type[Model], type[PydanticModel]]" = {}

    @staticmethod
    def container_instance_to_dict(container_instance: "PydanticModel") -> "dict[str, Any]":
        """Convert ``container_instance`` to dict.

        Args
            container_instance: the container instance

        Returns
            dict representation of container instance
        """
        return container_instance.dict()

    @staticmethod
    def parse_container_type_from_raw(
        container_type: "type[PydanticModel]", buffer: bytes, media_type: "RequestEncodingType | str"
    ) -> PydanticModel:
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
        container_type: "type[PydanticModel]",
        buffer: bytes,
        media_type: "RequestEncodingType | str",
    ) -> "list[PydanticModel]":
        """Parse an array of ``container_type`` from raw bytes.

        Args
            container_type: a container model type
            buffer: bytes to be parsed into instance
            media_type: format of the raw data

        Returns
            List of ``container_type`` instances.
        """
        return decode_json(buffer, list[container_type])  # type:ignore[valid-type]

    @staticmethod
    def _create_pydantic_model(model_class: "type[TortoiseModelT]", **kwargs: "Any") -> "type[PydanticModel]":
        """Take a tortoise model_class instance and convert it to a subclass of the tortoise PydanticModel.

        This fixes some issues with the result of the tortoise model creator.
        """
        pydantic_model = pydantic_model_creator(model_class, **kwargs)
        for (
            field_name,
            tortoise_model_field,
        ) in model_class._meta.fields_map.items():
            if field_name in pydantic_model.__fields__:
                if (
                    is_pydantic_model(pydantic_model.__fields__[field_name].type_)
                    and "." in pydantic_model.__fields__[field_name].type_.__name__
                ):
                    sub_model_name = pydantic_model.__fields__[field_name].type_.__name__.split(".")[-2]
                    pydantic_model.__fields__[field_name].type_ = pydantic_model_creator(
                        model_class, name=sub_model_name
                    )
                if not tortoise_model_field.required:
                    pydantic_model.__fields__[field_name].required = False
                if tortoise_model_field.null:
                    pydantic_model.__fields__[field_name].allow_none = True
        return pydantic_model

    def to_data_container_class(
        self,
        model_class: "type[TortoiseModelT]",
        exclude: "set[str] | None" = None,
        field_mappings: "Mapping[str, str | tuple[str, Any]] | None" = None,
        fields: "dict[str, tuple[Any, Any]] | None" = None,
        localns: "dict[str, Any] | None" = None,
        **kwargs: "Any",
    ) -> "type[PydanticModel]":
        """Given a tortoise model_class instance, convert it to a subclass of the tortoise PydanticModel.

        Since incoming request body's cannot and should not include values for
        related fields, pk fields and read only fields in tortoise-orm, we generate two different kinds of pydantic models here:
        - the first is a regular pydantic model, and the other is for the "data" kwarg only, which is further sanitized.

        This function uses memoization to ensure we don't recompute unnecessarily.

        :param model_class: The model class that serves as a basis.
        :param exclude: do not include fields of these names in the model.
        :param field_mappings: to rename, and re-type fields.
        :param fields: additional fields to add to the container model.
        :param localns: additional namespace for forward ref resolution.
        :param kwargs: Any kwargs.
        :return: The generated data container class.
        """
        parameter_name = kwargs.pop("parameter_name", None)
        if parameter_name == "data":
            if model_class not in self._data_models_map:
                fields_to_exclude: "set[str]" = {
                    field_name
                    for field_name, tortoise_model_field in model_class._meta.fields_map.items()
                    if isinstance(tortoise_model_field, (RelationalField, ReverseRelation)) or tortoise_model_field.pk
                }
                fields_to_exclude.update(exclude or set())
                kwargs.update(
                    exclude=tuple(fields_to_exclude), exclude_readonly=True, name=f"{model_class.__name__}RequestBody"
                )
                self._data_models_map[model_class] = self._create_pydantic_model(model_class=model_class, **kwargs)
            return self._data_models_map[model_class]
        if model_class not in self._models_map:
            kwargs.update(name=model_class.__name__)
            self._models_map[model_class] = self._create_pydantic_model(model_class=model_class, **kwargs)
        return self._models_map[model_class]

    @staticmethod
    def is_plugin_supported_type(value: "Any") -> "TypeGuard[Model]":
        """Given a value of indeterminate type, determine if this value is supported by the plugin."""
        return isinstance(value, (Model, ModelMeta))

    def from_data_container_instance(
        self, model_class: "type[TortoiseModelT]", data_container_instance: "PydanticModel"
    ) -> TortoiseModelT:
        """Given an instance of a pydantic model created using the plugin's ``to_data_container_class``, return an
        instance of the class from which that pydantic model has been created.

        This class is passed in as the ``model_class`` kwarg.
        """
        return model_class().update_from_dict(data_container_instance.dict())

    def to_dict(self, model_instance: TortoiseModelT) -> "dict[str, Any]":
        """Given an instance of a model supported by the plugin, return a dictionary of serializable values."""
        pydantic_model_class = self.to_data_container_class(type(model_instance))
        with anyio.start_blocking_portal() as portal:
            data = portal.call(pydantic_model_class.from_tortoise_orm, model_instance)
        return data.dict()

    def from_dict(self, model_class: "type[TortoiseModelT]", **kwargs: "Any") -> TortoiseModelT:  # pragma: no cover
        """Given a class supported by this plugin and a dict of values, create an instance of the class."""
        return model_class().update_from_dict(**kwargs)

    def to_openapi_schema(self, model_class: "type[TortoiseModelT]") -> "Schema":
        """Given a model class, transform it into an OpenAPI schema class.

        :param model_class: A table class.
        :return: An :class:`OpenAPI <pydantic_openapi_schema.v3_1_0.schema.Schema>` instance.
        """
        return OpenAPI310PydanticSchema(schema_class=self.to_data_container_class(model_class=model_class))
