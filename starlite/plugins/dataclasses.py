from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING

import pydantic.dataclasses
from pydantic import BaseModel

from starlite.types import DataclassProtocol
from starlite.utils.predicates import is_dataclass_class_or_instance

from .pydantic import FromPydantic

if TYPE_CHECKING:
    from typing import Any, Mapping, TypeGuard  # noqa:TC004


class DataclassPlugin(FromPydantic[DataclassProtocol]):
    """Plugin for dataclass object models."""

    @staticmethod
    def is_plugin_supported_type(value: Any) -> TypeGuard[DataclassProtocol]:
        """Is ``value`` a type managed by the plugin?

        Args:
            value: anything.

        Returns:
            Boolean indicating if ``value`` is a type or instance of a dataclass.
        """
        return is_dataclass_class_or_instance(value)

    def to_data_container_class(
        self,
        model_class: type[DataclassProtocol],
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
        :param localns: additional namespace for forward ref resolution.
        :param kwargs: Any kwargs.
        :return: The generated data container class.
        """

        pydantic_model = pydantic.dataclasses.dataclass(model_class).__pydantic_model__
        pydantic_model.update_forward_refs(localns=localns)
        return pydantic_model

    def from_data_container_instance(
        self, model_class: type[DataclassProtocol], data_container_instance: BaseModel
    ) -> DataclassProtocol:
        """Create an instance of the dataclass model type from a pydantic model instance.

        Args:
            model_class: dataclass model type.
            data_container_instance: DTO instance that represents model data.

        Returns:
            Instance of the model type, populated with DTO data.
        """
        return model_class(**data_container_instance.dict())

    def to_dict(self, model_instance: DataclassProtocol) -> dict[str, Any]:
        """Convert ``model_instance`` to a dict representation.

        Args:
            model_instance: a dataclass instance.

        Returns:
            A dict representation of ``model_instance``.
        """
        return asdict(model_instance)

    def from_dict(self, model_class: type[DataclassProtocol], **kwargs: Any) -> DataclassProtocol:
        """Create an instance of the model dataclass from ``kwargs``.

        Args:
            model_class: dataclass model type.
            **kwargs: k/v pairs to be set on the instance.

        Returns:
            Instance of model dataclass populated with ``kwargs``.
        """
        return model_class(**kwargs)
