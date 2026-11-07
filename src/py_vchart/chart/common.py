"""Single-region combinations with one shared category axis and numeric axis."""

from dataclasses import replace

from .bar import draw_bars
from .cartesian import Axis, axis_options, check_keys, frame_scene, prepare_frame
from .layout_helpers import field, number, palette_for, records
from .line import draw_line


def render_common(spec, surface, width, height):
    data = records(spec, {"series"})
    series = spec.get("series")
    if not isinstance(series, list) or not series:
        raise ValueError("common.series requires a list of Cartesian series")
    horizontal = spec.get("direction") == "horizontal"
    prepared = []
    for i, item in enumerate(series):
        check_keys(item, {"type", "xField", "yField", "bar", "line", "point"}, f"common.series[{i}]")
        kind = item.get("type")
        if kind not in ("bar", "line"):
            raise ValueError("common.series currently supports bar and line")
        cat, val = ("yField", "xField") if horizontal else ("xField", "yField")
        rows = [(field(r, item.get(cat)), number(r, item.get(val))) for r in data]
        prepared.append((item, rows))
    all_rows = [pair for _, rows in prepared for pair in rows]
    options = axis_options(spec, secondary=True)
    cat_side, val_side = ("left", "bottom") if horizontal else ("bottom", "left")
    bindings = [val_side] * len(series)
    dual = any(a["orient"] == "right" for a in spec.get("axes", []))
    if dual and horizontal:
        raise ValueError("common: right axis requires vertical series")
    for side in (val_side, "right"):
        indices = options[side].get("seriesIndex", [])
        if type(indices) is int:
            indices = [indices]
        if not isinstance(indices, list) or any(type(i) is not int or not 0 <= i < len(series) for i in indices):
            raise ValueError(f"common.axes.{side}.seriesIndex requires valid series indices")
        for index in indices:
            bindings[index] = side
    axes = {cat_side: Axis.make(cat_side, "band", [k for k, _ in all_rows], options[cat_side], "common.axes")}
    for side in ([val_side, "right"] if dual else [val_side]):
        domain_values = [v for i, (_, rows) in enumerate(prepared) if bindings[i] == side for _, v in rows]
        axes[side] = Axis.make(side, "linear", domain_values, options[side], "common.axes")
    for side, axis in axes.items():
        if options[side].get("type", axis.kind) != axis.kind:
            raise ValueError(f"common.axes.{side}.type must be {axis.kind}")
    frame = prepare_frame(spec, surface, width, height, axes, horizontal)
    marks = {}
    palette = palette_for(len(series))
    # Unnamed series share the last registered default series color in the common spec.
    color = palette[(len(series)-1) % len(palette)]
    for i, (item, rows) in enumerate(prepared):
        active = frame if bindings[i] == val_side else replace(frame, axes=axes | {val_side: axes[bindings[i]]})
        configured = item.copy()
        for name, channel in ([("bar", "fill")] if item["type"] == "bar" else [("line", "stroke"), ("point", "fill")]):
            mark = item.get(name, {})
            configured[name] = mark | {"style": {channel: color} | mark.get("style", {})}
        if item["type"] == "bar":
            marks[f"{i}.bar"] = draw_bars(configured, surface, active, rows)["bars"]
        else:
            line = draw_line(configured, surface, active, rows)
            marks[f"{i}.line"] = [p for segment in line["segments"] for p in segment]
            marks[f"{i}.point"] = line["points"]
    order = ("bottom", "left", "right") if dual else ("bottom", "left")
    return frame_scene(surface, frame, order) | {"marks": marks}
