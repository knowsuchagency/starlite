"""
Examples
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
    assert isinstance(dto.to_model_instance(), Model)
"""
from inspect import isawaitable
from typing import (
    TYPE_CHECKING,
    Any,
    Annotated,
    ClassVar,
    Dict,
    Generic,
    List,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    get_args,
    get_origin,
)

from pydantic import BaseConfig, BaseModel, create_model
from pydantic.fields import SHAPE_SINGLETON, ModelField

from starlite.exceptions import ImproperlyConfiguredException
from starlite.plugins import PluginProtocol
from starlite.utils import is_async_callable

if TYPE_CHECKING:
    from typing import Awaitable


def get_field_type(model_field: ModelField) -> Any:
    """Given a model field instance, return the correct type.

    Args:
        model_field (ModelField): `pydantic.fields.ModelField`

    Returns:
        Type of field.
    """
    outer_type = model_field.outer_type_
    inner_type = model_field.type_
    if "ForwardRef" not in repr(outer_type):
        return outer_type
    if model_field.shape == SHAPE_SINGLETON:
        return inner_type
    # This might be too simplistic
    return List[inner_type]  # type: ignore


T = TypeVar("T")


class DTOConfig(BaseModel):
    exclude: set[str] = set()
    field_mapping: Dict[str, str] = {}


class Factory(BaseModel, Generic[T]):
    """Create :class:`DTO` type.

    Pydantic models, :class:`TypedDict <typing.TypedDict>` and dataclasses are natively supported. Other types supported
    via plugins.
    """

    class Config(BaseConfig):
        orm_mode = True

    _model_type: ClassVar[Any]
    _config: DTOConfig = DTOConfig()
    _reverse_field_mappings: Dict[str, str]
    plugin: ClassVar[PluginProtocol]

    def __class_getitem__(cls, item: Union[TypeVar, Type[T], Annotated[Type[T], DTOConfig]]) -> "Type[Factory[T]]":
        if isinstance(item, TypeVar):
            return cls

        if get_origin(item) is Annotated:
            item, config = get_args(item)
        else:
            config = DTOConfig()

        field_definitions = cls._create_field_definitions(
            cls._config.exclude,
            cls._config.field_mapping,
            cls.plugin.to_pydantic_model_class(item).__fields__,
        )

        reverse_field_mappings = {
            value[0] if not isinstance(value, str) else value: key for key, value in cls._config.field_mapping.items()
        }

        new: "Type[Factory[T]]" = create_model(
            f"{item.__name__}DTO",
            __base__=cls,
            __module__=getattr(item, "__module__", __name__),
            __cls_kwargs__={"model_type": item, "config": config, "reverse_field_mappings": reverse_field_mappings},
            **field_definitions,
        )

        return new

    def __init_subclass__(cls, model_type: type[T] | None = None, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if model_type is not None:
            cls.model_type = model_type

    def to_model_instance(self) -> T:
        values = self.dict()

        for dto_key, original_key in self._reverse_field_mappings.items():
            value = values.pop(dto_key)
            values[original_key] = value

        return self.plugin.from_dict(self._model_type, **values)

    @classmethod
    def _from_value_mapping(cls, mapping: Dict[str, Any]) -> "Factory[T]":
        for dto_key, original_key in cls._config.field_mapping.items():
            value = mapping.pop(original_key)
            mapping[dto_key] = value
        return cls(**mapping)

    @classmethod
    def from_model_instance(cls: "type[Factory[T]]", model_instance: T) -> "Factory[T]":
        result = cls.plugin.to_dict(model_instance=model_instance)
        if isawaitable(result):
            raise ImproperlyConfiguredException(
                f"plugin {type(cls.plugin).__name__} to_dict method is async. "
                f"Use 'DTO.from_model_instance_async instead'",
            )
        return cls._from_value_mapping(result)

    @classmethod
    async def from_model_instance_async(cls, model_instance: T) -> "Factory[T]":
        """Given an instance of the source model, create an instance of the given DTO subclass asynchronously.

        Args:
            model_instance (T): instance of source model.

        Returns:
            Instance of the :class:`DTO` subclass.
        """
        if is_async_callable(cls.plugin.to_dict):
            values = await cast("Awaitable[Dict[str, Any]]", cls.plugin.to_dict(model_instance=model_instance))
            return cls._from_value_mapping(mapping=values)
        return cls.from_model_instance(model_instance=model_instance)

    @classmethod
    def _create_field_definitions(
        cls, exclude: Set[str], field_mapping: Dict[str, Union[str, Tuple[str, Any]]], fields: Dict[str, ModelField]
    ) -> Dict[str, Tuple[Any, Any]]:
        """Populate ``field_definitions``, ignoring fields in ``exclude``, and remapping fields in ``field_mapping``."""
        ret = {}
        for field_name, model_field in fields.items():
            if field_name in exclude:
                continue
            field_type = get_field_type(model_field=model_field)
            if field_name in field_mapping:
                field_name, field_type = cls._remap_field(field_mapping, field_name, field_type)
            ret[field_name] = field_type, model_field.field_info
        return ret

    @staticmethod
    def _remap_field(
        field_mapping: Dict[str, Union[str, Tuple[str, Any]]], field_name: str, field_type: Any
    ) -> Tuple[str, Any]:
        """Return tuple of field name and field type remapped according to entry in ``field_mapping``."""
        mapping = field_mapping[field_name]
        if isinstance(mapping, tuple):
            field_name, field_type = mapping
        else:
            field_name = mapping
        return field_name, field_type
