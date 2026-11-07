"""Grid cells, weighted columns and linear progress tracks."""

from math import floor

from .cartesian import check_keys
from .layout_helpers import BLUE, field, fields, frame_scene, make_frame, number, palette_for, records, rect_between, result
from .point import mark_options


def render_progress(spec, surface, width, height):
    rows = records(spec, {"bandWidth", "track", "progress"})
    horizontal = spec.get("direction", "horizontal") == "horizontal"
    cat, val = fields(spec, horizontal)
    keys = [field(r, cat) for r in rows]
    values = [number(r, val) for r in rows]
    side = "bottom" if horizontal else "left"
    defaults = {s: {"visible": any(a.get("orient") == s for a in spec.get("axes", []))}
                for s in ("bottom", "left")}
    defaults[side].update(min=0, max=1)
    frame = make_frame(spec, surface, width, height, keys, values, horizontal=horizontal,
                       reverse_side="left" if horizontal else None, defaults=defaults)
    breadth = spec.get("bandWidth", 30)
    if type(breadth) not in (int, float) or breadth <= 0:
        raise ValueError("linearProgress.bandWidth must be positive")
    marks = {}
    for name, color in (("track", "#e7ebed"), ("progress", BLUE)):
        show, style = mark_options(spec, name, {"fill"})
        boxes = []
        for key, v in zip(keys, values) if show else []:
            low, high = frame.domain
            box = rect_between(frame, key, low, high if name == "track" else v, breadth)
            surface.rect(box, style.get("fill", color))
            boxes.append(box)
        marks[name] = boxes
    specified = [a["orient"] for a in spec.get("axes", [])]
    order = tuple(dict.fromkeys([*specified, "left", "bottom"]))
    return frame_scene(surface, frame, order) | {"marks": marks}


def color_ramp(config):
    check_keys(config, {"type", "domain", "range"}, "heatmap.color")
    if config.get("type") != "linear" or len(config.get("domain", [])) != 2 or len(config.get("range", [])) != 2:
        raise ValueError("heatmap.color requires a two-stop linear color scale")
    low, high = config["domain"]
    if high <= low:
        raise ValueError("heatmap.color.domain must increase")
    rgb = []
    for color in config["range"]:
        if not isinstance(color, str) or len(color) != 7 or not color.startswith("#"):
            raise ValueError("heatmap.color.range requires #rrggbb colors")
        rgb.append(tuple(int(color[i:i+2], 16) for i in (1, 3, 5)))

    def paint(value):
        t = (value - low) / (high - low)
        channels = [min(255, max(0, floor(a + (b - a) * t + 0.5))) for a, b in zip(*rgb)]
        return "rgb(%d,%d,%d)" % tuple(channels)
    return paint


def render_heatmap(spec, surface, width, height):
    rows = records(spec, {"valueField", "color", "cell"})
    xfield, yfield = fields(spec)
    keys = [(field(r, xfield), field(r, yfield)) for r in rows]
    frame = make_frame(spec, surface, width, height, [x for x, _ in keys], [y for _, y in keys],
                       second_kind="band", reverse_side="left")
    show, style = mark_options(spec, "cell", {"fill"})
    paint = color_ramp(spec["color"]) if "color" in spec else None
    domain = list(dict.fromkeys(number(row, spec.get("valueField")) for row in rows))
    palette = palette_for(1)
    ordinal = {value: palette[(i + 1) % len(palette)] for i, value in enumerate(domain)}
    boxes = []
    for (x, y), row in zip(keys, rows) if show else []:
        px, py = frame.point(x, y)
        sx, sy = frame.band_positions["bottom"][x][1]/2, frame.band_positions["left"][y][1]/2
        box = [px-sx, py-sy, px+sx, py+sy]
        value = number(row, spec.get("valueField"))
        color = style.get("fill", paint(value) if paint else ordinal[value])
        surface.rect(box, color)
        boxes.append(box)
    return result(surface, frame, cell=boxes)


def render_mosaic(spec, surface, width, height):
    rows = records(spec, {"bandWidthField", "bar"})
    if spec.get("direction", "vertical") != "vertical":
        raise ValueError("mosaic.direction currently supports vertical")
    cat, val = fields(spec)
    keys = [field(r, cat) for r in rows]
    if len(set(keys)) != len(keys):
        raise ValueError("mosaic: repeated categories require grouped or stacked layout")
    weights = [number(r, spec.get("bandWidthField", val)) for r in rows]
    if any(w < 0 for w in weights) or (weights and not sum(weights)):
        raise ValueError("mosaic requires nonnegative widths with positive sum")
    values = [number(r, val) for r in rows]
    frame = make_frame(spec, surface, width, height, [0, 1], values, first_kind="linear", hide_labels="bottom")
    show, style = mark_options(spec, "bar", {"fill", "stroke", "lineWidth"})
    cursor, total = 0, sum(weights)
    boxes = []
    for weight, value in zip(weights, values) if show else []:
        left, baseline = frame.point(cursor / total, 0)
        cursor += weight
        right, edge = frame.point(cursor / total, value)
        box = [left, min(edge, baseline), right, max(edge, baseline)]
        surface.rect(box, style.get("fill", BLUE))
        if style.get("lineWidth", 1):
            surface.outline(box, style.get("stroke", "white"), style.get("lineWidth", 1))
        boxes.append(box)
    return result(surface, frame, bar=boxes)
