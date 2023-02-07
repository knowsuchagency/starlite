from __future__ import annotations

from abc import ABC
from typing import (
    Annotated,
    Any,
    ClassVar,
    Generic,
    TypeVar,
    cast,
    get_args,
    get_origin,
)

from pydantic import BaseConfig, BaseModel, create_model

from starlite.exceptions import ImproperlyConfiguredException
from starlite.plugins import PluginProtocol
from starlite.utils import is_awaitable, is_not_awaitable

from .config import Config as DTOConfig
from .utils import create_field_definitions

T = TypeVar("T")
FactoryT = TypeVar("FactoryT", bound="Factory")


class Factory(BaseModel, ABC, Generic[T]):
    """Create :class:`DTO` type.

    Pydantic models, :class:`TypedDict <typing.TypedDict>` and dataclasses are natively supported. Other types supported
    via plugins.
    """

    class Config(BaseConfig):
        orm_mode = True

    plugin: ClassVar[PluginProtocol]

    _model_type: ClassVar[Any]
    _config = DTOConfig()
    _reverse_field_mappings: ClassVar[dict[str, str]]

    def __class_getitem__(cls, item: TypeVar | type[T]) -> type[Factory[T]]:
        if isinstance(item, TypeVar):
            return cls

        if get_origin(item) is Annotated:
            item, config = get_args(item)
            item = cast("type[T]", item)
            config = cast("DTOConfig", config)
        else:
            config = cls._config

        field_definitions = create_field_definitions(
            config.exclude,
            config.field_mapping,
            cls.plugin.to_pydantic_model_class(item).__fields__,
        )

        reverse_field_mappings = {
            value[0] if not isinstance(value, str) else value: key for key, value in config.field_mapping.items()
        }

        return create_model(
            f"{cls.__name__}[{item.__name__}]",
            __config__=None,
            __base__=cls,
            __module__=str(getattr(item, "__module__", __name__)),
            __validators__={},
            __cls_kwargs__={"model_type": item, "config": config, "reverse_field_mappings": reverse_field_mappings},
            **field_definitions,
        )

    def __init_subclass__(  # pylint: disable=arguments-differ
        cls,
        model_type: type[T] | None = None,
        config: DTOConfig | None = None,
        reverse_field_mappings: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init_subclass__(**kwargs)
        if config is not None:
            cls._config = config
        if model_type is not None:
            cls._model_type = model_type
        if reverse_field_mappings is not None:
            cls._reverse_field_mappings = reverse_field_mappings

    def to_model_instance(self) -> T:
        """Convert self into instance of the model type.

        Returns:
            Instance of model type, populated from ``self``.
        """
        values = self.dict()

        for dto_key, original_key in self._reverse_field_mappings.items():
            value = values.pop(dto_key)
            values[original_key] = value

        return cast("T", self.plugin.from_dict(self._model_type, **values))

    @classmethod
    def _from_value_mapping(cls: type[FactoryT], mapping: dict[str, Any]) -> FactoryT:
        for dto_key, original_key in cls._config.field_mapping.items():
            value = mapping.pop(original_key)
            mapping[dto_key] = value
        return cls(**mapping)

    @classmethod
    def from_model_instance(cls: type[FactoryT], model_instance: T) -> FactoryT:
        """Create an instance of ``dto.Factory`` from an instance of the model.

        Args:
            model_instance: instance of the model

        Returns:
            Instance of ``dto.Factory``
        """
        result = cls.plugin.to_dict(model_instance=model_instance)
        if is_not_awaitable(result):
            return cls._from_value_mapping(result)
        raise ImproperlyConfiguredException(
            f"plugin {type(cls.plugin).__name__} to_dict method is async. "
            f"Use 'DTO.from_model_instance_async instead'",
        )

    @classmethod
    async def from_model_instance_async(cls: type[FactoryT], model_instance: T) -> FactoryT:
        """Given an instance of the source model, create an instance of the given DTO subclass asynchronously.

        Args:
            model_instance (T): instance of source model.

        Returns:
            Instance of the :class:`DTO` subclass.
        """
        maybe_awaitable = cls.plugin.to_dict(model_instance)
        mapping: dict[str, Any]
        if is_awaitable(maybe_awaitable):
            mapping = await maybe_awaitable
        else:
            # else branch of type guard doesn't seem to reverse-narrow the type
            mapping = maybe_awaitable  # type:ignore[assignment]
        return cls._from_value_mapping(mapping)
