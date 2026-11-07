"""Static, single-series scatter charts with circular point marks."""

from math import isfinite

from .cartesian import render_cartesian
from .point import draw_points, mark_options


def draw_scatter(spec, surface, frame, rows):
    visible, style = mark_options(spec, "point", {"fill", "stroke", "lineWidth", "size", "fillOpacity"})
    size = spec.get("size", 8)
    if type(size) not in (int, float) or not isfinite(size) or size < 0:
        raise ValueError("scatter.size must be a nonnegative finite number")
    opacity = style.get("fillOpacity", 0.8)
    if type(opacity) not in (int, float) or not 0 <= opacity <= 1:
        raise ValueError("scatter.point.style.fillOpacity must be between 0 and 1")
    points = [frame.point(key, value) for key, value in rows] if visible else []
    draw_points(surface, points, style, size=size, stroke="#1664ff", width=0, opacity=opacity)
    return {"points": points}


def render_scatter(spec, surface, width, height):
    return render_cartesian(spec, surface, width, height, marks={"size", "point"},
                            draw_series=draw_scatter, allow_numeric_pair=True)
