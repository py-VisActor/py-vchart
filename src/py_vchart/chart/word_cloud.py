"""Static word clouds with fast shape spirals or raster-mask placement."""

from math import ceil, cos, hypot, pi, radians, sin, sqrt

from .._deps.vdataset import inline_values
from .._deps.vlayouts.word_mask import (
    FAST_SHAPES,
    MaskBoard,
    filling_layout,
    glyph_offsets,
    raster_mask,
    spiral_radius,
)
from .._deps.vrender.text import glyph_run
from .cartesian import DYNAMIC, check_keys
from .layout_helpers import field
from .plot import nonnegative, plot_region


def place(bounds, index, width, height, occupied, shape="circle"):
    w, h = bounds
    x, y = width / 2, height / 2
    left, top = x - w / 2, y - 0.79 * h
    radius = 0
    while any(
        left <= r and left + w >= l and top <= b and top + h >= t
        for l, t, r, b in occupied
    ):
        radius += 0.5
        if radius > hypot(width, height) / 2:
            return None
        angle = radius if index % 2 == 0 else -radius
        distance = radius * spiral_radius(shape, radius / hypot(width, height) * 4 * pi)
        x = width / 2 + distance * cos(angle)
        y = height / 2 + distance * sin(angle)
        left, top = x - w / 2, y - h / 2
    if left < 0 or top < 0 or left + w > width or top + h > height:
        return None
    occupied.append((left, top, left + w, top + h))
    return x, y


def render_words(spec, surface, width, height):
    check_keys(
        spec,
        DYNAMIC
        | {
            "type",
            "width",
            "height",
            "padding",
            "data",
            "background",
            "nameField",
            "fillingWord",
            "maskShape",
            "wordMask",
            "wordCloudShapeConfig",
            "valueField",
            "fontSizeRange",
            "random",
            "wordCloudConfig",
            "word",
            "rotateAngles",
        },
        "wordCloud",
    )
    mask = spec.get("maskShape")
    fast_shape = mask if isinstance(mask, str) and mask in FAST_SHAPES else "circle"
    if isinstance(mask, str) and mask in FAST_SHAPES:
        mask = None
    if mask is None and (
        spec.get("random") is not False
        or spec.get("wordCloudConfig") != {"layoutMode": "fast"}
    ):
        raise ValueError(
            "wordCloud requires deterministic random=false and layoutMode=fast"
        )
    angles = spec.get("rotateAngles", [0])
    if len(angles) != 1:
        raise ValueError("wordCloud requires a single fixed rotation")
    angle = radians(angles[0])
    word = spec.get("word", {})
    check_keys(word, {"style", "padding"}, "word")
    style = word.get("style", {})
    check_keys(style, {"fontFamily", "fontWeight", "fill"}, "word.style")
    rows = inline_values(spec.get("data"), "wordCloud.data")
    sizes = [
        nonnegative(row[spec["valueField"]], "valueField")
        if "valueField" in spec
        else 0
        for row in rows
    ]
    lower, upper = spec.get("fontSizeRange", [20, 40])
    plot = plot_region(spec, surface, width, height)
    board = None
    if mask is not None:
        options = spec.get("wordCloudShapeConfig", {})

        if (
            spec.get("wordCloudConfig", {}).get("layoutMode", "default") != "default"
            or options.get("layoutMode", "default") != "default"
        ):
            raise ValueError("Shape masks require the default static layout")
        tile, allowed = raster_mask(mask, ceil(plot[2]), ceil(plot[3]))
        if isinstance(mask, dict) and spec.get("wordMask", {}).get("visible"):
            surface.ctx.drawImage(tile.canvas, plot[0], plot[1])
        board = MaskBoard(allowed)
    marks, occupied, keywords = [], [], []
    ctx = surface.ctx
    ctx.fontHinting = True
    order = sorted(range(len(rows)), key=sizes.__getitem__, reverse=True)
    lo, hi = (min(sizes), max(sizes)) if sizes else (0, 0)
    fractions = [
        (sqrt(v) - sqrt(lo)) / (sqrt(hi) - sqrt(lo))
        if hi > lo
        else int(len(rows) == 1 and "valueField" in spec)
        for v in sizes
    ]
    font_sizes = [lower + t * (upper - lower) for t in fractions]
    if board:
        font_sizes = [
            max(options.get("minInitFontSize", 10), int(v)) for v in font_sizes
        ]
        regions = board.word_regions([font_sizes[j] for j in order])

    def paint(text, position, size, rotation, family, weight):
        x, y = plot[0] + position[0], plot[1] + position[1]
        marks.append([text, x, y, size, rotation])
        ctx.save()
        ctx.translate(x, round(y) if rotation == 0 else y)
        ctx.rotate(rotation)
        glyph_run(
            surface,
            text,
            0,
            0,
            size,
            style.get("fill", "#1664ff"),
            "center",
            weight=weight,
            family=family,
        )
        ctx.restore()

    for i, idx in enumerate(order):
        size = font_sizes[idx]
        weight = style.get(
            "fontWeight",
            (200 if hi == lo else 200 + 300 * (sizes[idx] - lo) / (hi - lo))
            if "valueField" in spec
            else "normal",
        )
        ctx.font = f"{weight} {size}px {style.get('fontFamily', 'Arial')}"
        text = str(field(rows[idx], spec.get("nameField")))
        w, h = surface.measure(text), size * 1.1
        bounds = (
            abs(w * cos(angle)) + abs(h * sin(angle)),
            abs(w * sin(angle)) + abs(h * cos(angle)),
        )
        if board:
            step = options.get("stepFactor", 1)
            if step <= 0:
                raise ValueError("stepFactor must be positive")
            pos = (
                board.place(
                    glyph_offsets(
                        text,
                        style.get("fontFamily", "Arial"),
                        weight,
                        size,
                        w,
                        angle,
                        word.get("padding", 1),
                    ),
                    step,
                    regions[i],
                )
                if regions[i]
                else None
            )
        else:
            pos = place(bounds, i, plot[2], plot[3], occupied, fast_shape)
        if board:
            keywords.append((text, pos is not None))
        if pos is None:
            continue
        paint(text, pos, size, angle, style.get("fontFamily", "Arial"), weight)
    if board:
        fill = spec.get("fillingWord", {})
        fill_style = fill.get("style", {})
        family = fill_style.get("fontFamily", "Microsoft YaHei")
        weight = fill_style.get("fontWeight", "normal")
        for text, px, py, size, rotation in filling_layout(
            board, keywords, options, family, weight, fill.get("padding", 1)
        ):
            paint(text, (px, py), size, rotation, family, weight)
    return dict(plot=plot, axes=[], labels=[], marks={"word": marks})
