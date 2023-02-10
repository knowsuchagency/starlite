from typing import TYPE_CHECKING, TypeVar

from pydantic_openapi_schema.utils.utils import OpenAPI310PydanticSchema

from starlite.exceptions import MissingDependencyException
from starlite.plugins.base import OpenAPISchemaPluginProtocol
from starlite.plugins.pydantic import FromPydantic

try:
    from piccolo.table import Table, TableMetaclass
    from piccolo.utils.pydantic import create_pydantic_model
except ImportError as e:
    raise MissingDependencyException("piccolo orm is not installed") from e

if TYPE_CHECKING:
    from typing import Any, Mapping

    from pydantic import BaseModel
    from pydantic_openapi_schema.v3_1_0 import Schema
    from typing_extensions import TypeGuard


PiccoloModelT = TypeVar("PiccoloModelT", bound="Table")


class PiccoloORMPlugin(FromPydantic[Table], OpenAPISchemaPluginProtocol[Table]):
    """Support (de)serialization and OpenAPI generation for Piccolo ORM types."""

    _models_map: "dict[type[Table], type[BaseModel]]" = {}
    _data_models_map: "dict[type[Table], type[BaseModel]]" = {}

    def to_data_container_class(
        self,
        model_class: "type[PiccoloModelT]",
        exclude: "set[str] | None" = None,
        field_mappings: "Mapping[str, str | tuple[str, Any]] | None" = None,
        fields: "dict[str, tuple[Any, Any]] | None" = None,
        localns: "dict[str, Any] | None" = None,
        **kwargs: "Any",
    ) -> "type[BaseModel]":
        """Given a piccolo model_class instance, convert it to a subclass of the piccolo "BaseModel".

        Since incoming request body's cannot and should not include values for
        related fields, pk fields and read only fields in piccolo-orm, we generate two different kinds of pydantic models here:
        - the first is a regular pydantic model, and the other is for the "data" kwarg only, which is further sanitized.

        This function uses memoization to ensure we don't recompute unnecessarily.
        """
        parameter_name = kwargs.get("parameter_name")
        if parameter_name == "data":
            if model_class not in self._data_models_map:
                self._data_models_map[model_class] = create_pydantic_model(
                    table=model_class, model_name=f"{model_class.__name__}RequestBody"
                )
            return self._data_models_map[model_class]
        if model_class not in self._models_map:
            self._models_map[model_class] = create_pydantic_model(
                table=model_class,
                model_name=model_class.__name__,
                nested=True,
                include_default_columns=True,
            )
        return self._models_map[model_class]

    @staticmethod
    def is_plugin_supported_type(value: "Any") -> "TypeGuard[Table]":
        """Given a value of indeterminate type, determine if this value is supported by the plugin."""
        return isinstance(value, (Table, TableMetaclass))

    def from_data_container_instance(
        self, model_class: "type[PiccoloModelT]", data_container_instance: "BaseModel"
    ) -> "PiccoloModelT":
        """Given an instance of a pydantic model created using the plugin's ``to_data_container_class``, return an
        instance of the class from which that pydantic model has been created.

        This class is passed in as the ``model_class`` kwarg.
        """
        return self.from_dict(model_class=model_class, **data_container_instance.dict())

    def to_dict(self, model_instance: "PiccoloModelT") -> "dict[str, Any]":
        """Given an instance of a model supported by the plugin, return a dictionary of serializable values."""
        return model_instance.to_dict()

    def from_dict(self, model_class: "type[PiccoloModelT]", **kwargs: "Any") -> "PiccoloModelT":
        """Given a class supported by this plugin and a dict of values, create an instance of the class."""
        instance = model_class()
        for column in instance.all_columns():
            meta = column._meta
            if meta.name in kwargs:
                setattr(instance, meta.name, kwargs[meta.name])
        return instance

    def to_openapi_schema(self, model_class: "type[PiccoloModelT]") -> "Schema":
        """Given a model class, transform it into an OpenAPI schema class.

        :param model_class: A table class.
        :return: An :class:`OpenAPI <pydantic_openapi_schema.v3_1_0.schema.Schema>` instance.
        """
        return OpenAPI310PydanticSchema(schema_class=self.to_data_container_class(model_class=model_class))
