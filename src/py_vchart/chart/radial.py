"""Radial axes, radar series and single-value progress indicators."""

from math import cos, pi, sin, tau

from .._deps.vscale import linear, numeric_axis
from .cartesian import AXIS, GRID, check_keys
from .layout_helpers import BLUE, field
from .polar import PolarFrame, SECTOR_OPTIONS


def axis_label(frame, value, angle, radius):
    dx, dy = cos(angle), sin(angle)
    align = "center" if abs(dx) < 1e-8 else ("right" if dx < 0 else "left")
    baseline = "middle" if abs(dy) < 1e-8 else ("bottom" if dy < 0 else "top")
    frame.surface.label(value, *frame.point(angle, radius), align, baseline, line_height=12)


def ring(frame, radius, color):
    ctx = frame.surface.ctx
    ctx.beginPath()
    ctx.arc(*frame.center, radius, 0, tau)
    ctx.strokeStyle = color
    ctx.stroke()


def render_radar(spec, surface, width, height):
    frame = PolarFrame(spec, surface, width, height, {"categoryField", "outerRadius", "area"})
    area = spec.get("area", {})
    check_keys(area, {"visible"}, "radar.area")
    keys = [field(row, spec.get("categoryField")) for row in frame.rows]
    categories = list(dict.fromkeys(keys))
    domain, ticks = numeric_axis(frame.values, {})
    extent = frame.radii(spec, 0, .6)
    frame.axis("angle", categories, frame.angles)
    frame.axis("radius", domain, extent)
    start, end = frame.angles
    angles = {key: start + (end-start) * i / len(categories) for i, key in enumerate(categories)}
    outer = extent[1]
    if categories:
        # Keep neighboring radial grid lines at least one label height apart.
        stride = 1
        if len(ticks) > 1 and linear(ticks[1], domain, extent) - linear(ticks[0], domain, extent) < 16:
            stride = 2
        for tick in ticks[::stride]:
            radius = linear(tick, domain, extent)
            if radius:
                ring(frame, radius, GRID)
        surface.ctx.setLineDash([6, 6])
        for angle in [*angles.values(), start]:
            surface.line(*frame.point(angle, outer), *frame.center, GRID)
        surface.ctx.setLineDash([])
    ring(frame, outer, AXIS)
    for key, angle in angles.items():
        surface.line(*frame.point(angle, outer), *frame.point(angle, outer+4), AXIS)
        axis_label(frame, key, angle, outer+9)
    points = [frame.point(angles[key], linear(value, domain, extent)) for key, value in zip(keys, frame.values)]
    filled = area.get("visible", False)
    if filled:
        surface.polygon(points, BLUE, .2)
    surface.polyline(points + points[:1], BLUE, 2)
    for point in points:
        surface.circle(*point, 8, BLUE, "white", 1)
    frame.marks.update(line=points, point=points, area=[p + frame.center for p in points] if filled else [])
    return frame.scene()


def unit_value(frame):
    if len(frame.values) != 1 or not 0 <= frame.values[0] <= 1:
        raise ValueError("Expected one indicator value in [0, 1]")
    return frame.values[0]


def render_indicator(spec, surface, width, height):
    frame = PolarFrame(spec, surface, width, height, SECTOR_OPTIONS)
    value = unit_value(frame)
    extent = frame.radii(spec, .6, .8)
    frame.axis("angle", [0, 1], frame.angles)
    frame.axis("radius", [field(frame.rows[0], spec.get("categoryField"))], extent)
    start, end = frame.angles
    angle = linear(value, [0, 1], frame.angles)
    gauge = spec["type"] == "gauge"
    color = "#1ac6ff" if gauge else BLUE
    frame.sector("track", *extent, start, end, color, .2)
    frame.sector("progress", *extent, start, angle, color)
    if gauge:
        for i in range(6):
            axis_label(frame, f"{i/5:g}", start + (end-start)*i/5, extent[1]+5)
        draw_pointer(frame, angle + pi/2, color)
    return frame.scene()


def draw_pointer(frame, angle, color):
    from py_skia_canvas import Path2D
    ctx = frame.surface.ctx
    for name, ratio, rotation, fill in [
        ("pinBackground", .06, 0, "#ddd"), ("pointer", .4, angle, color), ("pin", .025, 0, "#888")
    ]:
        size = frame.radius * ratio
        frame.marks[name] = [[*frame.center, size, rotation]]
        if name == "pointer":
            ctx.save()
            ctx.translate(*frame.center)
            ctx.rotate(angle)
            ctx.scale(size, size)
            ctx.fillStyle = fill
            ctx.fill(Path2D(POINTER))
            ctx.restore()
        else:
            frame.surface.circle(*frame.center, 2*size, fill, fill, 0)


# Normalized outline of the default VChart gauge pointer.
POINTER = ("M-.020059 -.978425 C-.018029 -.9888053 -.013378 -1 0 -1 "
           "C.01342 -1 .01812 -.989146 .0201 -.978425 C.02161 -.9702819 .0692 -.459505 .09486 -.184807 "
           "C.10298 -.097849 .1089 -.034548 .11047 -.018339 C.11698 .04908 .07373 .11111 .00002 .11111 "
           "C-.07369 .11111 -.117184 .04991 -.110423 -.018339 C-.103662 -.086591 -.022089 -.9680447 -.020059 -.978425Z")
