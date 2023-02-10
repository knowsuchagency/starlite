from __future__ import annotations

import importlib
import typing
from typing import TYPE_CHECKING, Generic, TypeVar, cast

import typing_extensions
from typing_extensions import Annotated, get_args, get_origin

from starlite.enums import RequestEncodingType
from starlite.exceptions import ImproperlyConfiguredException
from starlite.plugins import SerializationPluginProtocol
from starlite.utils.serialization import encode_json

from .config import Config as DTOConfig

if TYPE_CHECKING:
    from typing import Any

ModelT = TypeVar("ModelT")
FactoryT = TypeVar("FactoryT", bound="Factory")


class Factory(Generic[ModelT]):
    """Create :class:`DTO` type.

    Subclass Factory and define `plugin_type`.

    Type narrow the factory down to a specific model type, that must be compatible with the `plugin_type`.

    Examples
        class DataclassFactory(Factory[ModelT]):
            plugin_type = DataclassPlugin

        @dataclass
        class MyDC:
            ...

        DTO = DataclassFactory[MyDC]
    """

    plugin_type: type[SerializationPluginProtocol]

    _plugin_instance: SerializationPluginProtocol
    _model_type: type[ModelT]
    _transfer_type: Any
    _config: DTOConfig
    _reverse_field_mappings: dict[str, str]

    def __init__(self, transfer_instance: Any) -> None:
        """Create an instance of the factory type.

        Args:
            transfer_instance: instance of the container type that is supported by ``plugin_type``.
        """
        self.transfer_instance = transfer_instance

    def __class_getitem__(cls, item: TypeVar | type[ModelT]) -> type[Factory[ModelT]]:
        if isinstance(item, TypeVar):
            return cls

        if not getattr(cls, "plugin_type", None):
            raise ImproperlyConfiguredException("You must subclass `Factory` and define `plugin_type`.")

        plugin_instance = getattr(cls, "_plugin_instance", cls.plugin_type())
        reverse_field_mappings = getattr(cls, "_reverse_field_mappings", {})

        if get_origin(item) is Annotated:
            item, config = get_args(item)
            item = cast("type[ModelT]", item)
            if not isinstance(config, DTOConfig):
                raise ImproperlyConfiguredException(
                    f"Metadata passed via `Annotated` must be an instance of `dto.Config`, not `{config}`"
                )
            reverse_field_mappings.update(
                {value[0] if not isinstance(value, str) else value: key for key, value in config.field_mapping.items()}
            )
        else:
            config = cls._config if getattr(cls, "_config", None) is not None else DTOConfig()

        cls_kwargs = {
            "_plugin_instance": plugin_instance,
            "_config": config,
            "_reverse_field_mappings": reverse_field_mappings,
        }

        item_module = importlib.import_module(item.__module__)
        cls_kwargs["_transfer_type"] = plugin_instance.to_data_container_class(
            item,
            exclude=config.exclude,
            field_mappings=config.field_mapping,
            fields=config.fields,
            localns={**vars(typing), **vars(typing_extensions), **vars(item_module)},
        )
        cls_kwargs["_model_type"] = item

        return type(f"Factory[{item.__name__}, {cls.plugin_type.__name__}]", (cls,), cls_kwargs)

    def to_model(self) -> ModelT:
        """Convert self into instance of the model type.

        Returns:
            Instance of model type, populated from ``self``.
        """
        values = self._plugin_instance.container_instance_to_dict(self.transfer_instance)

        for dto_key, original_key in self._reverse_field_mappings.items():
            values[original_key] = values.pop(dto_key)

        return self._plugin_instance.from_dict(self._model_type, **values)  # type:ignore[no-any-return]

    @classmethod
    def _apply_field_mappings(cls, mapping: dict[str, Any]) -> dict[str, Any]:
        for dto_key, original_key in cls._config.field_mapping.items():
            mapping[dto_key] = mapping.pop(original_key)
        return mapping

    @classmethod
    def from_model(cls: type[FactoryT], model_instance: ModelT) -> FactoryT:
        """Create an instance of ``dto.Factory`` from an instance of ``ModelT``.

        Args:
            model_instance: instance of the model

        Returns:
            Instance of ``dto.Factory``
        """
        return cls.from_buffer(encode_json(cls._plugin_instance.to_dict(model_instance)), RequestEncodingType.JSON)

    @classmethod
    def from_buffer(cls: type[FactoryT], buffer: bytes, media_type: RequestEncodingType | str) -> FactoryT:
        """Create an instance of the DTO type from raw buffer.

        Args:
            buffer: The raw data extracted from the request
            media_type: Format of the raw data
        """
        return cls(
            transfer_instance=cls._plugin_instance.parse_container_type_from_raw(
                container_type=cls._transfer_type, buffer=buffer, media_type=media_type
            )
        )

    @classmethod
    def array_from_buffer(cls: type[FactoryT], buffer: bytes, media_type: RequestEncodingType | str) -> list[FactoryT]:
        """Create an array of DTO types from raw buffer.

        Args:
            buffer: The raw data extracted from the request
            media_type: Format of the raw data
        """
        return [
            cls(
                transfer_instance=cls._plugin_instance.parse_container_type_array_from_raw(
                    cls._transfer_type, buffer=buffer, media_type=media_type
                )
            )
        ]
