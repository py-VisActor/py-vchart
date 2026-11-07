"""Single-series straight lines with optional circular point marks."""

from .cartesian import render_cartesian
from .point import draw_points, mark_options


def draw_line(spec, surface, frame, rows):
    show_line, line = mark_options(spec, "line", {"stroke", "lineWidth"})
    show_points, point = mark_options(spec, "point", {"fill", "stroke", "size", "lineWidth"})
    segments = []
    segment = []
    for category, value in rows:
        if value is None:
            if segment:
                segments.append(segment)
                segment = []
        else:
            segment.append(frame.point(category, value))
    if segment:
        segments.append(segment)

    if show_line:
        for path in segments:
            surface.polyline(path, line.get("stroke", "#1664ff"), line.get("lineWidth", 2))
    points = [p for path in segments for p in path] if show_points else []
    draw_points(surface, points, point)
    return {"segments": segments if show_line else [], "points": points}


def render_line(spec, surface, width, height):
    return render_cartesian(spec, surface, width, height, marks={"line", "point"},
                            draw_series=draw_line, allow_missing=True)
