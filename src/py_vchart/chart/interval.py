"""Area ribbons and floating columns share their pair of value coordinates."""

from .layout_helpers import BLUE, field, fields, make_frame, number, records, rect_between, result
from .point import draw_points, mark_options


def render_interval(spec, surface, width, height):
    kind = spec["type"]
    area = kind != "rangeColumn"
    simple = kind == "area"
    mark_fields = {"area": {"area", "point"}, "rangeArea": {"area"}, "rangeColumn": {"bar"}}
    rows = records(spec, mark_fields[kind])
    horizontal = spec.get("direction") == "horizontal"
    cat, interval = fields(spec, horizontal)
    if not simple and (not isinstance(interval, list) or len(interval) != 2):
        raise ValueError(f"{kind} requires two ordered value fields")
    keys = [field(r, cat) for r in rows]
    if simple:
        if not isinstance(interval, str):
            raise ValueError("area requires a numeric value field")
        pairs = [(number(r, interval), 0) if r.get(interval) is not None else None for r in rows]
    else:
        pairs = [(number(r, interval[0]), number(r, interval[1])) for r in rows]
    frame = make_frame(spec, surface, width, height, keys,
                       [v for pair in pairs if pair for v in pair], horizontal=horizontal)
    if not area:
        visible, style = mark_options(spec, "bar", {"fill"})
        boxes = [rect_between(frame, k, *pair) for k, pair in zip(keys, pairs)] if visible else []
        for box in boxes:
            surface.rect(box, style.get("fill", BLUE))
        return result(surface, frame, bar=boxes)

    visible, style = mark_options(spec, "area", {"fill", "fillOpacity"})
    spans = []
    path = []
    for key, pair in zip(keys, pairs):
        if pair is None:
            if path:
                spans.append(path)
                path = []
        else:
            path.append([*frame.point(key, pair[0]), *frame.point(key, pair[1])])
    if path:
        spans.append(path)
    for path in spans if visible else []:
        top = [p[:2] for p in path]
        surface.polygon(top + [p[2:] for p in reversed(path)], style.get("fill", BLUE),
                        style.get("fillOpacity", 0.2))
        if simple:
            surface.polyline(top, BLUE, 2)
    marks = {"area": [p for path in spans for p in path] if visible else []}
    if simple:
        show, point = mark_options(spec, "point", {"size", "fill", "stroke", "lineWidth"})
        marks["point"] = [p[:2] for path in spans for p in path] if show else []
        draw_points(surface, marks["point"], point)
    return result(surface, frame, **marks)
