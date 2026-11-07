"""Single, grouped and stacked rectangular bars."""

from .cartesian import check_keys, render_cartesian
from .._deps.vscale import bands
from .layout_helpers import field, fields, frame_scene, make_frame, number, palette_for, records, rect_between


def draw_bars(spec, surface, frame, rows):
    style = spec.get("bar", {})
    check_keys(style, {"style", "state"}, "bar.bar")
    brush = style.get("style", {})
    check_keys(brush, {"fill"}, "bar.bar.style")
    minimum, maximum = frame.domain
    zero = max(minimum, min(maximum, 0))
    bars = []
    for key, value in rows:
        box = rect_between(frame, key, zero, max(minimum, min(maximum, value)))
        bars.append(box)
        surface.rect(box, brush.get("fill", "#1664ff"))
    return {"bars": bars}


def grouped_bars(spec, surface, width, height):
    data = records(spec, {"seriesField", "stack", "bar"})
    horizontal = spec.get("direction") == "horizontal"
    category, value = fields(spec, horizontal)
    group = spec["seriesField"]
    stack = spec.get("stack", False)
    if not stack:
        if not isinstance(category, list) or len(category) != 2 or category[1] != group:
            raise ValueError("Grouped bars require [category, seriesField] on the category axis")
        category = category[0]
    style = spec.get("bar", {})
    check_keys(style, {"style", "state"}, "bar.bar")
    brush = style.get("style", {})
    check_keys(brush, {"fill"}, "bar.bar.style")
    intervals = []
    totals = {}
    for row in data:
        key, series, delta = field(row, category), field(row, group), number(row, value)
        sign_key = (key, delta < 0)
        start = totals.get(sign_key, 0) if stack else 0
        totals[sign_key] = start + delta
        intervals.append((key, series, start, start + delta))
    groups = list(dict.fromkeys(series for _, series, _, _ in intervals))
    frame = make_frame(spec, surface, width, height, [k for k, *_ in intervals],
                       [end for _, _, _, end in intervals], horizontal=horizontal)
    palette = palette_for(len(groups))
    colors = {key: palette[i % len(palette)] for i, key in enumerate(groups)}
    boxes = []
    for key, series, start, end in intervals:
        box = rect_between(frame, key, start, end)
        if not stack:
            offset, breadth = bands(groups, frame.positions[key][1])[series]
            dim = 1 if horizontal else 0
            box[dim] += offset
            box[dim + 2] = box[dim] + breadth
        surface.rect(box, brush.get("fill", colors[series]))
        boxes.append(box)
    return frame_scene(surface, frame) | {"bars": boxes}


def render_bar(spec, surface, width, height):
    if "seriesField" in spec:
        return grouped_bars(spec, surface, width, height)
    return render_cartesian(spec, surface, width, height, marks={"bar"}, draw_series=draw_bars)
