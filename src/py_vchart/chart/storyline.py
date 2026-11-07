"""Text and image cards on the alternating landscape storyline layout."""

from math import floor, sqrt

from .._deps.vrender.images import draw_fitted_image
from .._deps.vrender.text import glyph_run
from .cartesian import check_keys


def render_storyline(spec, surface, width, height):
    check_keys(
        spec,
        {
            "type",
            "width",
            "height",
            "data",
            "layout",
            "block",
            "image",
            "line",
            "title",
            "content",
            "padding",
        },
        "storyline",
    )
    if spec.get("layout", "landscape") != "landscape":
        raise ValueError("storyline supports the landscape layout")
    blocks = spec["data"]
    if any(b.get("subImage") for b in blocks):
        raise ValueError("Secondary images require a different storyline layout")
    region = [20, 20, width - 40, height - 120]
    if "padding" in spec:
        p = spec["padding"]
        region = [p, p, width - 2 * p, height - 2 * p]
    left, top, w, h = region
    n = len(blocks)
    block = spec.get("block", {})
    pad = block.get("padding", 24)
    bw = block.get("width", max(80, floor((w - 2 * pad - 40 * (n - 1)) / max(n, 1))))
    margin = min(8, h * 0.04)
    body = h - 2 * margin
    origin = top + margin
    palette = "#e8543d"
    surface.rect((0, 0, width, height), "white")
    ctx = surface.ctx
    positions = []
    for i, b in enumerate(blocks):
        text = b.get("title", "")
        weight = max(
            4,
            sum(0.32 if c.isspace() else 1.05 if ord(c) > 255 else 0.62 for c in text),
        )
        ts = spec.get("title", {}).get("style", {})
        cs = spec.get("content", {}).get("style", {})
        size = ts.get(
            "fontSize",
            floor(
                max(
                    8,
                    min(
                        34,
                        sqrt(w * h) * 0.038 * sqrt(8 / weight),
                        bw * 2 * 0.96 / weight,
                    ),
                )
            ),
        )
        lh = ts.get("lineHeight", floor(size * 1.35 + 0.5))
        ch = cs.get("lineHeight", 23)
        raw = max(
            spec.get("image", {}).get("height", round(block.get("height", 320) * 0.42)),
            lh + 24,
        )
        reserve = min(lh + 4 + 2 * ch, max(0, (body - 48) / 2))
        band = min(
            max(raw + 24, body * 0.28),
            max(1, min(max(body - 2 * reserve, body * 0.18), body * 0.42)),
        )
        ih = min(raw, max(band - 16, 1))
        center = (
            left + w / 2
            if n == 1
            else left + pad + bw / 2 + i * (w - 2 * pad - bw) / (n - 1)
        )
        cy = (
            origin
            + body / 2
            + (-1 if i % 2 == 0 else 1)
            * min(band * 0.18, block.get("height", 320) * 0.1)
        )
        if b.get("image"):
            draw_fitted_image(
                ctx,
                b["image"],
                center - bw / 2,
                cy - ih / 2,
                bw,
                ih,
                spec.get("image", {}).get("style", {}),
            )
        positions.append([center, cy])
        cx = center - bw * 0.3
        ty = origin if i % 2 == 0 else origin + (body + band) / 2
        ctx.save()
        ctx.setLineDash([4, 4])
        ctx.lineWidth = 2
        surface.line(
            cx,
            cy + (-1 if i % 2 == 0 else 1) * (ih / 2 + 8),
            cx,
            ty + lh / 2 if i % 2 == 0 else origin + body,
            palette,
        )
        ctx.restore()
        for value, y, fs, color, bold, line_h in [
            (text, ty, size, ts.get("fill", "#1f2430"), True, lh),
            (
                b.get("content", ""),
                ty + lh + 4,
                cs.get("fontSize", 16),
                cs.get("fill", "#596173"),
                False,
                ch,
            ),
        ]:
            lines = value if isinstance(value, list) else str(value).splitlines()
            baseline = (
                floor((line_h + fs) / 2) - 1 if bold else floor((line_h + fs) / 2) - 2
            )
            for j, line in enumerate(lines):
                glyph_run(
                    surface,
                    line,
                    cx + 12,
                    y + j * line_h + baseline,
                    fs,
                    color,
                    bold=bold,
                )
    style = spec.get("line", {}).get("style", {})
    ctx.save()
    ctx.setLineDash(style.get("lineDash", [6, 5]))
    ctx.strokeStyle = style.get("stroke", palette)
    ctx.lineWidth = style.get("lineWidth", 4)
    ctx.lineCap = "round"
    ctx.lineJoin = "round"
    if len(positions) > 1:
        ctx.beginPath()
        ctx.moveTo(*positions[0])
        for i, (a, b) in enumerate(zip(positions, positions[1:])):
            prev = positions[max(0, i - 1)]
            following = positions[min(i + 2, len(positions) - 1)]
            c1 = [a[j] + (b[j] - prev[j]) / 6 for j in (0, 1)]
            c2 = [b[j] - (following[j] - a[j]) / 6 for j in (0, 1)]
            if len(positions) == 2:
                ctx.lineTo(*b)
            else:
                ctx.bezierCurveTo(*c1, *c2, *b)
        ctx.stroke()
    ctx.restore()
    for pt in positions:
        surface.circle(*pt, 14, palette, None, 0)
    return dict(plot=region, axes=[], labels=[], marks={})
