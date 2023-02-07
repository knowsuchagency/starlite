from __future__ import annotations

from typing import Any, List

from pydantic.fields import ModelField, SHAPE_SINGLETON


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


def remap_field(field_mapping: dict[str, str | tuple[str, Any]], field_name: str, field_type: Any) -> tuple[str, Any]:
    """Return tuple of field name and field type remapped according to entry in ``field_mapping``."""
    mapping = field_mapping[field_name]
    if isinstance(mapping, tuple):
        field_name, field_type = mapping
    else:
        field_name = mapping
    return field_name, field_type


def create_field_definitions(
    exclude: set[str], field_mapping: dict[str, str | tuple[str, Any]], fields: dict[str, ModelField]
) -> dict[str, tuple[Any, Any]]:
    """Populate ``field_definitions``, ignoring fields in ``exclude``, and remapping fields in ``field_mapping``."""
    ret = {}
    for field_name, model_field in fields.items():
        if field_name in exclude:
            continue
        field_type = get_field_type(model_field=model_field)
        if field_name in field_mapping:
            field_name, field_type = remap_field(field_mapping, field_name, field_type)
        ret[field_name] = field_type, model_field.field_info
    return ret
