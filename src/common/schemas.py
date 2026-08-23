from pathlib import Path
from typing import Any

from src.common.io import read_json


class SchemaValidationError(ValueError):
    """Raised when a JSON object does not match an expected schema."""


def load_schema(path: str | Path) -> dict[str, Any]:
    schema = read_json(path)
    if not isinstance(schema, dict):
        raise SchemaValidationError(f"Schema must be a JSON object: {path}")
    return schema


def validate_with_jsonschema(payload: dict[str, Any], schema: dict[str, Any]) -> None:
    try:
        import jsonschema
    except ImportError as exc:
        validate_with_builtin_schema(payload, schema)
        return

    try:
        jsonschema.Draft202012Validator(schema).validate(payload)
    except jsonschema.ValidationError as exc:
        path = ".".join(str(part) for part in exc.path) or "<root>"
        raise SchemaValidationError(f"{path}: {exc.message}") from exc


def validate_with_builtin_schema(payload: dict[str, Any], schema: dict[str, Any]) -> None:
    """Validate the schema subset used by this project.

    This keeps local development moving when the optional `jsonschema` package is
    not installed. The full dependency can still be added later for broader JSON
    Schema coverage.
    """

    _validate_node(payload, schema, path="<root>")


def _validate_node(value: Any, schema: dict[str, Any], path: str) -> None:
    expected_type = schema.get("type")
    if expected_type is not None and not _matches_type(value, expected_type):
        raise SchemaValidationError(f"{path}: expected {expected_type}")

    if "enum" in schema and value not in schema["enum"]:
        allowed = ", ".join(str(item) for item in schema["enum"])
        raise SchemaValidationError(f"{path}: expected one of {allowed}")

    if isinstance(value, str):
        min_length = schema.get("minLength")
        if min_length is not None and len(value) < min_length:
            raise SchemaValidationError(f"{path}: must be at least {min_length} characters")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            raise SchemaValidationError(f"{path}: must be >= {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            raise SchemaValidationError(f"{path}: must be <= {schema['maximum']}")

    if isinstance(value, list):
        _validate_array(value, schema, path)

    if isinstance(value, dict):
        _validate_object(value, schema, path)


def _validate_array(value: list[Any], schema: dict[str, Any], path: str) -> None:
    min_items = schema.get("minItems")
    if min_items is not None and len(value) < min_items:
        raise SchemaValidationError(f"{path}: must contain at least {min_items} items")

    max_items = schema.get("maxItems")
    if max_items is not None and len(value) > max_items:
        raise SchemaValidationError(f"{path}: must contain at most {max_items} items")

    if schema.get("uniqueItems") and len(value) != len(set(_hashable(item) for item in value)):
        raise SchemaValidationError(f"{path}: items must be unique")

    item_schema = schema.get("items")
    if item_schema:
        for index, item in enumerate(value):
            _validate_node(item, item_schema, path=f"{path}[{index}]")


def _validate_object(value: dict[str, Any], schema: dict[str, Any], path: str) -> None:
    required = schema.get("required", [])
    for field in required:
        if field not in value:
            raise SchemaValidationError(f"{path}: missing required field '{field}'")

    properties = schema.get("properties", {})
    if schema.get("additionalProperties") is False:
        extra = sorted(set(value) - set(properties))
        if extra:
            raise SchemaValidationError(f"{path}: unexpected field '{extra[0]}'")

    for field, field_value in value.items():
        field_schema = properties.get(field)
        if field_schema:
            child_path = field if path == "<root>" else f"{path}.{field}"
            _validate_node(field_value, field_schema, path=child_path)


def _matches_type(value: Any, expected_type: str) -> bool:
    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected_type == "boolean":
        return isinstance(value, bool)
    return True


def _hashable(value: Any) -> Any:
    if isinstance(value, dict):
        return tuple(sorted((key, _hashable(item)) for key, item in value.items()))
    if isinstance(value, list):
        return tuple(_hashable(item) for item in value)
    return value
