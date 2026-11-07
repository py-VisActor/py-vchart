"""The single inline data view needed by the first Cartesian series."""

from math import isfinite


def inline_values(data, path):
    views = data if isinstance(data, list) else [data]
    if len(views) != 1 or not isinstance(views[0], dict):
        raise ValueError(f"{path} requires one inline data view")
    view = views[0]
    if set(view) - {"id", "values"} or not isinstance(view.get("values"), list):
        raise ValueError(f"{path}[0] requires inline values")
    return view["values"]


def read_records(data, category_field, value_field, *, path="bar.data", allow_missing=False):
    rows = []
    for i, row in enumerate(inline_values(data, path)):
        if not isinstance(row, dict) or category_field not in row or (value_field not in row and not allow_missing):
            raise ValueError(f"{path}.values[{i}] is missing a required field")
        category, value = row[category_field], row.get(value_field)
        valid_number = type(value) in (int, float) and isfinite(value)
        if type(category) not in (str, int, float) or not (valid_number or (allow_missing and value is None)):
            raise ValueError(f"{path}.values[{i}] requires a scalar category and finite numeric value")
        rows.append((category, value))
    return rows
