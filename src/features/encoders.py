from collections.abc import Iterable


def fit_category_maps(rows: Iterable[dict[str, str]], columns: list[str]) -> dict[str, dict[str, int]]:
    maps: dict[str, dict[str, int]] = {}
    materialized = list(rows)

    for column in columns:
        values = sorted({row.get(column, "") for row in materialized})
        maps[column] = {value: index for index, value in enumerate(values)}

    return maps


def encode_category(value: str, mapping: dict[str, int]) -> int:
    return mapping.get(value, -1)


def bool_as_int(value: bool) -> int:
    return 1 if value else 0

