import sys
from collections import defaultdict, deque
from collections.abc import Iterable as CollectionsIterable
from dataclasses import is_dataclass
from inspect import isawaitable, isclass
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    DefaultDict,
    Deque,
    Dict,
    FrozenSet,
    Generic,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from typing_extensions import (
    Annotated,
    NotRequired,
    ParamSpec,
    Required,
    TypeGuard,
    get_args,
    get_origin,
    is_typeddict,
)

from starlite.types.builtin_types import NoneType

if sys.version_info >= (3, 10):
    from types import UnionType

    UNION_TYPES = {UnionType, Union}
else:  # pragma: no cover
    UNION_TYPES = {Union}

if TYPE_CHECKING:
    from starlite.types.builtin_types import (
        DataclassClass,
        DataclassClassOrInstance,
        TypedDictClass,
    )

P = ParamSpec("P")
T = TypeVar("T")


def _get_origin(annotation: Any) -> Any:
    origin = get_origin(annotation)
    return origin if origin not in (Annotated, Required, NotRequired) else get_args(annotation)[0]


def is_awaitable(value: Awaitable[T] | T) -> TypeGuard[Awaitable[T]]:
    """A type narrowing version of ``inspect.isawaitable``.

    Args:
        value: value to be checked.

    Returns:
        Boolean indicating whether value is an awaitable object.
    """
    return isawaitable(value)


def is_not_awaitable(value: Awaitable[T] | T) -> TypeGuard[T]:
    """An inverse type narrowing version of ``inspect.isawaitable``.

    Args:
        value: value to be checked.

    Returns:
        Boolean indicating whether value is an awaitable object.
    """
    return isawaitable(value)


def is_class_and_subclass(value: Any, t_type: Type[T]) -> TypeGuard[Type[T]]:
    """Return ``True`` if ``value`` is a ``class`` and is a subtype of ``t_type``.

    See https://github.com/starlite-api/starlite/issues/367

    Args:
        value: The value to check if is class and subclass of ``t_type``.
        t_type: Type used for :func:`issubclass` check of ``value``

    Returns:
        bool
    """
    origin = _get_origin(value)
    if not origin and not isclass(value):
        return False
    try:
        return issubclass(origin or value, t_type)
    except TypeError:  # pragma: no cover
        return False


def is_generic(annotation: Any) -> bool:
    """Given a type annotation determine if the annotation is a generic class.

    Args:
    annotation: A type.

    Returns:
        True if the annotation is a subclass of :data:`Generic <typing.Generic>` otherwise ``False``.
    """
    return is_class_and_subclass(annotation, Generic)  # type: ignore


def is_mapping(annotation: Any) -> "TypeGuard[Mapping[Any, Any]]":
    """Given a type annotation determine if the annotation is a mapping type.

    Args:
    annotation: A type.

    Returns:
        A typeguard determining whether the type can be cast as :class:`Mapping <typing.Mapping>`.
    """
    _type = _get_origin(annotation) or annotation
    return isclass(_type) and issubclass(_type, (dict, defaultdict, DefaultDict, Mapping))


def is_non_string_iterable(annotation: Any) -> "TypeGuard[Iterable[Any]]":
    """Given a type annotation determine if the annotation is an iterable.

    Args:
    annotation: A type.

    Returns:
        A typeguard determining whether the type can be cast as :class:`Iterable <typing.Iterable>` that is not a string.
    """
    origin = _get_origin(annotation)
    if not origin and not isclass(annotation):
        return False
    try:
        return not issubclass(origin or annotation, (str, bytes)) and (
            issubclass(origin or annotation, (Iterable, CollectionsIterable, Dict, dict, Mapping))
            or is_non_string_sequence(annotation)
        )
    except TypeError:  # pragma: no cover
        return False


def is_non_string_sequence(annotation: Any) -> "TypeGuard[Sequence[Any]]":
    """Given a type annotation determine if the annotation is a sequence.

    Args:
    annotation: A type.

    Returns:
        A typeguard determining whether the type can be cast as :class`Sequence <typing.Sequence>` that is not a string.
    """
    origin = _get_origin(annotation)
    if not origin and not isclass(annotation):
        return False
    try:
        return not issubclass(origin or annotation, (str, bytes)) and issubclass(
            origin or annotation,
            (  # type: ignore
                Tuple,
                List,
                Set,
                FrozenSet,
                Deque,
                Sequence,
                list,
                tuple,
                deque,
                set,
                frozenset,
            ),
        )
    except TypeError:  # pragma: no cover
        return False


def is_any(annotation: Any) -> "TypeGuard[Any]":
    """Given a type annotation determine if the annotation is Any.

        Args:
        annotation: A type.

    Returns:
        A typeguard determining whether the type is :data:`Any <typing.Any>`.
    """
    return (
        annotation is Any
        or getattr(annotation, "_name", "") == "typing.Any"
        or (get_origin(annotation) in UNION_TYPES and Any in get_args(annotation))
    )


def is_union(annotation: Any) -> "TypeGuard[Union[Any, Any]]":
    """Given a type annotation determine if the annotation infers an optional union.

    Args:
        annotation: A type.

    Returns:
        A typeguard determining whether the type is :data:`Union typing.Union>`.
    """
    return _get_origin(annotation) in UNION_TYPES


def is_optional_union(annotation: Any) -> "TypeGuard[Union[Any, None]]":
    """Given a type annotation determine if the annotation infers an optional union.

    Args:
        annotation: A type.

    Returns:
        A typeguard determining whether the type is :data:`Union typing.Union>` with a
            None value or :data:`Optional <typing.Optional>` which is equivalent.
    """
    origin = _get_origin(annotation)
    return origin is Optional or (get_origin(annotation) in UNION_TYPES and NoneType in get_args(annotation))


def is_dataclass_class(value: Any) -> "TypeGuard[DataclassClass]":
    """Wrap :func:`is_dataclass <dataclasses.is_dataclass>` in a :data:`typing.TypeGuard`, narrowing to type only, not
        instance.

    Args:
        value: tested to determine if type of :class:`dataclasses.dataclass`.

    Returns:
        ``True`` if ``value`` is a ``dataclass`` type.
    """
    return is_dataclass(value) and isinstance(value, type)


def is_dataclass_class_or_instance(value: Any) -> "TypeGuard[DataclassClassOrInstance]":
    """Wrap :func:`is_dataclass <dataclasses.is_dataclass>` in a :data:`typing.TypeGuard`.

    Args:
        value: tested to determine if instance or type of :class:`dataclasses.dataclass`.

    Returns:
        ``True`` if instance or type of ``dataclass``.
    """
    return is_dataclass(value)


def is_typed_dict(value: Any) -> "TypeGuard[TypedDictClass]":
    """Wrap :func:`typing.is_typeddict` in a :data:`typing.TypeGuard`.

    Args:
        value: tested to determine if instance or type of :class:`typing.TypedDict`.

    Returns:
        ``True`` if instance or type of ``TypedDict``.
    """
    return is_typeddict(value)


def is_type_or_instance_of(value: Any, type_: Type[T]) -> "TypeGuard[Type[T] | T]":
    """Is ``value`` either a type or instance of ``type_``?

    Args:
        value: value to be tested.
        type_: type for test.

    Returns:
        Bool indicating whether ``value`` is either a type of ``type_`` or an instance of ``type_``.
    """
    if is_class_and_subclass(value, t_type=type_):
        return True

    return isinstance(value, type_)
