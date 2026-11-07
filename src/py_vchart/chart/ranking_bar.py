"""Static first time slice of a ranking bar chart."""

from math import ceil, floor, log10, sqrt
from .cartesian import Axis, CartesianFrame, draw_axis, frame_scene, check_keys
from .._deps.vscale import bands
from .._deps.vrender.controls import rounded_rect, control_symbol
from .layout_helpers import palette_for, number
from .stat_matrix import text_at


def render_ranking_bar(spec, surface, width, height):
    check_keys(
        spec,
        {
            "type",
            "width",
            "height",
            "timeField",
            "xField",
            "yField",
            "data",
            "topN",
            "color",
            "timeLabel",
            "label",
            "nameLabel",
            "background",
            "interval",
        },
        "rankingBar",
    )
    data = spec["data"]
    time_field, xfield, yfield = (spec[k] for k in ("timeField", "xField", "yField"))
    if not data:
        raise ValueError("rankingBar requires time slices")
    time = min((r[time_field] for r in data), key=str)
    rows = sorted(
        (r for r in data if r[time_field] == time), key=lambda r: -number(r, xfield)
    )[: spec.get("topN", 10)]
    cats = [r[yfield] for r in rows]
    values = [r[xfield] for r in rows]
    lo, hi = min(0, min(values)), max(0, max(values))
    if hi == lo:
        hi = 1
    power = 10 ** floor(log10((hi - lo) / 5))
    ratio = (hi - lo) / 5 / power
    factor = (
        10
        if ratio >= sqrt(50)
        else 5
        if ratio >= sqrt(10)
        else 2
        if ratio >= sqrt(2)
        else 1
    )
    step = factor * power
    ticks = [i * step for i in range(ceil(lo / step), floor(hi / step) + 1)]
    y = Axis.make("left", "band", cats, {}, "rankingBar")
    x = Axis("bottom", "linear", [lo, hi], ticks, True)
    left = ceil(36 + max(surface.measure(k) for k in cats))
    w, h = width - left - 20, height - 112
    scale_w = w - width * 0.1
    frame = CartesianFrame(
        (left, 20, scale_w, h), True, {"left": y, "bottom": x}, {"left": bands(cats, h)}
    )
    surface.rect((0, 0, width, height), spec.get("background", "white"))
    draw_axis(surface, frame, x)
    draw_axis(surface, frame, y)
    marks = []
    palette = palette_for(len(cats))
    for i, r in enumerate(rows):
        name, v = r[yfield], r[xfield]
        a, b = frame.positions[name]
        px, cy = frame.point(name, v)
        zero = frame.coordinate("bottom", 0)
        box = [min(zero, px), 20 + a, max(zero, px), 20 + a + b]
        color = spec.get("color", {}).get(name, palette[i % len(palette)])
        surface.rect(box, color)
        marks.append(box)
        if spec.get("label", {}).get("visible", True):
            label = spec.get("label", {}).get("style", {})
            text_at(
                surface,
                str(v),
                px + 4,
                cy + 4.5,
                label.get("fontSize", 12),
                label.get("fill", "#404040"),
            )
        name_label = spec.get("nameLabel", {})
        if name_label.get("visible", False):
            label = name_label.get("style", {})
            at_end = name_label.get("position") == "bar-end"
            text_at(
                surface,
                name,
                box[2] - 4 if at_end else box[0] + 4,
                cy + 4.5,
                label.get("fontSize", 12),
                label.get("fill", "#ffffff"),
                "right" if at_end else "left",
            )
    if spec.get("timeLabel", {}).get("visible", True):
        style = spec.get("timeLabel", {}).get("style", {})
        ctx = surface.ctx
        ctx.save()
        ctx.font = f'{style.get("fontWeight", 600)} {style.get("fontSize", 200)}px "Microsoft YaHei"'
        ctx.textAlign = style.get("textAlign", "end")
        ctx.textBaseline = style.get("textBaseline", "bottom")
        ctx.fillStyle = style.get("fill", "grey")
        ctx.globalAlpha = style.get("fillOpacity", 0.5)
        ctx.fillText(str(time), style.get("x", width - 50), style.get("y", height - 80))
        ctx.restore()
    cy = height - 46
    rounded_rect(surface, 96, cy - 5, width - 116, 10, 5, "#f1f3f4")
    for i, icon in enumerate(("iconPause", "iconLeft", "iconRight")):
        surface.ctx.globalAlpha = 0.8
        control_symbol(surface, icon, 30 + 22 * i, cy - 6, 12, "#0040ff")
    surface.ctx.globalAlpha = 1
    surface.circle(96, cy, 15, "#0040ff", "white", 2)
    scene = frame_scene(surface, frame, ("left", "bottom"))
    scene["plot"][2] = w
    return scene | {"marks": {"0.bar": marks}}
