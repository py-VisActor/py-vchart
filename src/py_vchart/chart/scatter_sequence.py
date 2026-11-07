"""First-frame scatter sequence charts. Frames are selected in JavaScript key order."""

from collections import defaultdict
from math import ceil, exp, floor, pi
from .cartesian import (
    Axis,
    CartesianFrame,
    draw_axis,
    frame_scene,
    plot_bounds,
    check_keys,
)
from .layout_helpers import number
from .stat_matrix import text_at

CLASSES = [
    (150, 10, 100),
    (31, 119, 180),
    (255, 127, 14),
    (44, 160, 44),
    (214, 39, 40),
    (148, 103, 189),
    (140, 86, 75),
    (227, 119, 194),
    (127, 127, 127),
    (188, 189, 34),
    (23, 190, 207),
]


def class_color(label, brighter=False):
    try:
        index = int(label)
        if index < 0:
            raise ValueError
        r, g, b = CLASSES[index]
    except (ValueError, IndexError, TypeError):
        raise ValueError(
            "sequenceScatterKDE supports class labels 0 through 10"
        ) from None
    return f"rgb({r},{g},{min(255, b + 50) if brighter else b})"


def draw_density(surface, frame, rows):
    groups = defaultdict(list)
    for r in rows:
        groups[r["label"]].append((number(r, "x"), number(r, "y")))
    left, top, _, _ = frame.plot
    for group_index, (label, points) in enumerate(groups.items()):
        xs, ys = zip(*points)
        x0 = min(xs) - 0.2 * (max(xs) - min(xs))
        y0 = min(ys) - 0.2 * (max(ys) - min(ys))
        bandwidth = len(points) ** (-1 / 6)
        factor = 10 / (2 * pi * len(points) * bandwidth**2)
        color = class_color(label, True)
        ctx = surface.ctx
        ctx.save()
        ctx.fillStyle = color
        if group_index:
            ctx.globalAlpha = 0
        for i in range(150):
            x = x0 + 0.1 * i
            px = frame.coordinate("bottom", x) - left + 54
            if px - 2.5 >= surface.canvas.width or px + 2.5 < 0:
                continue
            x_weights = [exp(-0.5 * ((x - u) / bandwidth) ** 2) for u in xs]
            for j in range(150):
                y = y0 + 0.1 * j
                py = frame.coordinate("left", y) - top + 26
                alpha = factor * sum(
                    a * exp(-0.5 * ((y - v) / bandwidth) ** 2)
                    for a, v in zip(x_weights, ys)
                )
                # Canvas keeps the previous alpha when assigned a value above one.
                if alpha <= 1:
                    ctx.globalAlpha = alpha
                if -2 < py < surface.canvas.height + 2:
                    ctx.fillRect(px - 2.5, py - 1.25, 5, 2.5)
        ctx.restore()


def render_scatter_sequence(spec, surface, width, height):
    kind = spec["type"]
    pixel, link = kind == "sequenceScatterPixel", kind == "sequenceScatterLink"
    allowed = (
        {"backgroundColors"}
        if pixel
        else {"scope", "taskType", "labelColor"}
        if link
        else {"seriesField"}
    )
    check_keys(
        spec,
        allowed
        | {
            "type",
            "width",
            "height",
            "data",
            "xField",
            "yField",
            "infoLabel",
            "player",
        },
        kind,
    )
    data = spec["data"]
    if not data:
        raise ValueError(f"{kind} requires at least one frame")
    keys = list(data)
    indices = [
        int(k)
        for k in keys
        if str(k).isdecimal() and str(int(k)) == str(k) and int(k) < 4294967295
    ]
    key = str(min(indices)) if indices else keys[0]
    if link and spec.get("taskType") != "neighborhood":
        raise ValueError("sequenceScatterLink requires a local neighborhood frame")
    rows = data[key]["nodes"] if link else data[key]
    coords = [(number(r, spec["xField"]), number(r, spec["yField"])) for r in rows]
    axes = {}
    for i, side in enumerate(("bottom", "left")):
        options = dict(zip(("min", "max"), spec["scope"][i::2])) if link else {}
        axes[side] = Axis.make(side, "linear", [p[i] for p in coords], options, kind)
    axes["left"].reverse = link
    rect = list(plot_bounds(width, height, 20, axes, surface))
    if link:
        rect[2] -= 51
    frame = CartesianFrame(rect, False, axes, {})
    surface.rect((0, 0, width, height), "white")
    # Upstream paints the image custom mark over the axes and below the points.
    for side in ("left", "bottom"):
        draw_axis(surface, frame, axes[side])
    if pixel and key in spec.get("backgroundColors", {}):
        matrix = spec["backgroundColors"][key]
        from py_skia_canvas import ImageData

        rgba = bytearray(300 * 300 * 4)
        rgba[3::4] = bytes([255]) * (300 * 300)
        for y, row in enumerate(matrix[:300]):
            for x, col in enumerate(row[:300]):
                pos = (y * 300 + x) * 4
                rgba[pos : pos + 3] = bytes(
                    max(0, min(255, floor(c * 255 + 0.5))) for c in col
                )
        surface.ctx.putImageData(ImageData(bytes(rgba), 300, 300), 0, 0)
    if not (pixel or link):
        draw_density(surface, frame, rows)
    points = [frame.point(x, y) for x, y in coords]
    for pt, row in zip(points, rows):
        if link:
            color = spec["labelColor"].get(row["label"], "gray")
            surface.circle(*pt, 6, color, None, 0, row.get("confidence", 1))
            ctx = surface.ctx
            ctx.save()
            ctx.font = 'italic 12px "Times New Roman"'
            ctx.globalAlpha = 0.6
            text_at(
                surface,
                row["id"],
                pt[0],
                pt[1] - 9.9,
                12,
                "black",
                "center",
                italic=True,
                family="Times New Roman",
            )
            ctx.restore()
        else:
            surface.circle(
                *pt,
                8 if pixel else 5,
                "#1664ff" if pixel else class_color(row[spec["seriesField"]]),
                None,
                0,
                0.8,
            )
    style = spec.get("infoLabel", {}).get("style", {})
    if not link and style.get("visible", True):
        ctx = surface.ctx
        ctx.save()
        size = style.get("fontSize", 100 if pixel else 25)
        ctx.font = f'bold {size}px "Microsoft YaHei"'
        ctx.globalAlpha = style.get("fillOpacity", 0.2)
        ctx.textAlign = "left"
        ctx.textBaseline = "top"
        ctx.fillStyle = style.get("fill", "black")
        ctx.fillText(key, style.get("x", 50 if pixel else 10), style.get("y", 10))
        ctx.restore()
    marks = {"0.point": points}
    if link:
        xs, ys, xe, ye = spec["scope"]
        origin = frame.coordinate("left", 0)
        shape = [
            frame.point(x, y)
            for x, y in [(xs, ys), (xs, ye), (xe, ye), (xe, ys), (xs, ys)]
        ]
        marks = {
            "0.area": [[x, y, x, origin] for x, y in shape],
            "1.line": [],
            "2.point": points,
        }
        categories = list(dict.fromkeys(r["label"] for r in rows))
        for i, label in enumerate(categories):
            y = height / 2 + 6 + (i - (len(categories) - 1) / 2) * 30
            x = width - 35
            color = spec["labelColor"].get(label, "gray")
            surface.circle(x, y, 10, color, None, 0)
            ctx = surface.ctx
            ctx.beginPath()
            ctx.arc(x, y, 7, 0, 2 * pi)
            ctx.lineWidth = 1
            ctx.strokeStyle = color
            ctx.stroke()
    return frame_scene(surface, frame, ("left", "bottom")) | {"marks": marks}
