"""Static correlation symbols and the center glyph at a fixed ripple phase."""

from math import isfinite, radians

from .._deps.vdataset import inline_values
from .._deps.vdataset.correlation import positions
from .cartesian import DYNAMIC, check_keys
from .layout_helpers import field, number, palette_for
from .plot import hidden_label, nonnegative, plot_region
from .point import mark_options


def radius(value, extent):
    if isinstance(value, str) and value.endswith("%"):
        return nonnegative(float(value[:-1]), "correlation radius")*extent/100
    return nonnegative(value, "correlation radius")


def finite(value, path):
    if type(value) not in (int, float) or not isfinite(value):
        raise ValueError(f"{path} must be a finite number")
    return value


def opacity(style, default):
    value = finite(style.get("fillOpacity", default), "correlation fillOpacity")
    if not 0 <= value <= 1:
        raise ValueError("correlation fillOpacity must be between zero and one")
    return value


def layout_nodes(spec, rows, extent, center, bounds):
    values = [number(row, spec.get("valueField")) for row in rows]
    sizes = [number(row, spec["sizeField"]) for row in rows] if "sizeField" in spec else values
    limits = spec.get("sizeRange", [5, 5])
    if not isinstance(limits, (tuple, list)) or len(limits) != 2:
        raise ValueError("correlation.sizeRange requires two diameters")
    limits = [nonnegative(value, "correlation.sizeRange") for value in limits]
    radii = [radius(spec.get("innerRadius", 0), extent), radius(spec.get("outerRadius", extent), extent)]
    angles = [radians(finite(spec.get(key, default), key)) for key, default in (("startAngle",-90), ("endAngle",270))]
    obstacles = []
    for row in rows:
        coords = tuple(row.get(key) for key in ("x", "y", "size"))
        obstacles.append(coords if all(type(v) in (float, int) and isfinite(v) for v in coords) else None)
    return positions(values, sizes, radii, limits, angles, center, bounds, obstacles)


def render_correlation(spec, surface, width, height):
    options = {"type", "data", "width", "height", "padding", "background", "categoryField", "valueField",
               "sizeField", "seriesField", "sizeRange", "centerX", "centerY", "innerRadius", "outerRadius",
               "startAngle", "endAngle", "label", "centerLabel", "nodePoint", "ripplePoint", "centerPoint"}
    check_keys(spec, options | DYNAMIC, "correlation")
    hidden_label(spec, default=True)
    if spec.get("centerLabel", {"visible": False}) != {"visible": False}:
        raise ValueError("correlation.centerLabel currently requires visible=false")
    plot = plot_region(spec, surface, width, height)
    px, py, w, h = plot
    extent = max(w, h)/2
    cx = finite(spec.get("centerX", w/2), "correlation.centerX")
    cy = finite(spec.get("centerY", h/2), "correlation.centerY")
    rows = inline_values(spec.get("data"), "correlation.data")
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError("correlation.data requires records")
    nodes = layout_nodes(spec, rows, extent, (cx, cy), (w, h))
    groups = [field(row, spec["seriesField"]) for row in rows] if "seriesField" in spec else [None]*len(rows)
    keys = dict.fromkeys(groups)
    palette = palette_for(len(keys))
    colors = {key: palette[i % len(palette)] for i, key in enumerate(keys)}
    center_color = palette[(len(keys) if "seriesField" in spec else int(not rows)) % len(palette)]
    common_style = {"fill", "fillOpacity", "size"}
    show_nodes, node_style = mark_options(spec, "nodePoint", common_style)
    show_center, center_style = mark_options(spec, "centerPoint", common_style)
    show_ripple, ripple_style = mark_options(spec, "ripplePoint", common_style | {"ripple"})
    marks = dict(nodePoint=[], ripplePoint=[], centerPoint=[])
    x, y = px+cx, py+cy
    if show_ripple:
        phase = min(1, max(0, finite(ripple_style.get("ripple", 0), "ripplePoint.ripple")))
        base = ripple_style.get("size", extent)
        ripple_opacity = opacity(ripple_style, .2)
        for i in range(3):
            size = base*(1+(i+phase)/2)
            alpha = (3-i-phase)/4
            marks["ripplePoint"].append([x, y, size, alpha])
            surface.circle(x, y, size, ripple_style.get("fill", center_color), None, 0,
                           alpha*ripple_opacity)
    if show_nodes:
        node_opacity = opacity(node_style, 1)
        for (nx, ny, size), group in zip(nodes, groups):
            mark = [px+nx, py+ny, node_style.get("size", size)]
            marks["nodePoint"].append(mark)
            surface.circle(*mark, node_style.get("fill", colors[group]), None, 0, node_opacity)
    if show_center:
        mark = [x, y, center_style.get("size", .2*extent)]
        marks["centerPoint"].append(mark)
        surface.circle(*mark, center_style.get("fill", center_color), None, 0, opacity(center_style, 1))
    return dict(plot=plot, axes=[], labels=[], marks=marks)
