"""Static mark options and circular point painting."""

from math import isfinite

from .cartesian import check_keys


def mark_options(spec, name, fields):
    path = f"{spec['type']}.{name}"
    config = spec.get(name, {})
    check_keys(config, {"style", "visible", "state"}, path)
    visible = config.get("visible", True)
    if not isinstance(visible, bool):
        raise ValueError(f"{path}.visible must be boolean")
    style = config.get("style", {})
    check_keys(style, fields, f"{path}.style")
    for key in ("lineWidth", "size"):
        if key in style:
            value = style[key]
            if type(value) not in (int, float) or not isfinite(value) or value < 0:
                raise ValueError(f"{path}.style.{key} must be a nonnegative finite number")
    return visible, style


def draw_points(surface, points, style, *, size=8, stroke="white", width=1, opacity=1):
    for x, y in points:
        surface.circle(x, y, style.get("size", size), style.get("fill", "#1664ff"),
                       style.get("stroke", stroke), style.get("lineWidth", width),
                       style.get("fillOpacity", opacity))
