"""Rasterize small axis and legend glyph runs at their device-pixel origins."""

from functools import lru_cache
from math import ceil, floor


@lru_cache(maxsize=96)
def raster_font(family, size, weight=400, italic=False):
    import skia

    style = skia.FontStyle(
        int({"normal": 400, "bold": 700}.get(weight, weight)),
        5,
        skia.FontStyle.kItalic_Slant if italic else skia.FontStyle.kUpright_Slant,
    )
    face = skia.FontMgr.RefDefault().matchFamilyStyle(family, style)
    font = skia.Font(face, size)
    font.setLinearMetrics(True)
    font.setHinting(skia.FontHinting.kFull)
    font.setSubpixel(True)
    font.setBaselineSnap(False)
    font.setEdging(skia.Font.kSubpixelAntiAlias)
    return font


@lru_cache(maxsize=128)
def _rgba(color):
    from . import Surface

    sample = Surface(1, 1)
    sample.rect((0, 0, 1, 1), color)
    return tuple(sample.ctx.getImageData(0, 0, 1, 1).data)


def glyph_run(
    surface,
    text,
    x,
    y,
    size,
    color,
    align="left",
    *,
    bold=False,
    weight=None,
    italic=False,
    family="Microsoft YaHei",
):
    """Composite a single line using the current transform and alphabetic baseline."""
    import skia
    import numpy as np
    from py_skia_canvas import ImageData

    text = str(text)
    if not text:
        return
    ctx = surface.ctx
    font = raster_font(
        family, size, weight if weight is not None else (700 if bold else 400), italic
    )
    glyphs = font.textToGlyphs(text)
    advance = font.measureText(text)
    x -= {"left": 0, "center": 0.5, "right": 1}[align] * advance
    m = ctx.getTransform()
    corners = [
        (m.a * u + m.c * v + m.e, m.b * u + m.d * v + m.f)
        for u in (x - size, x + advance + size)
        for v in (y - size * 1.5, y + size * 0.5)
    ]
    dx = max(0, floor(min(u for u, _ in corners)))
    dy = max(0, floor(min(v for _, v in corners)))
    w = min(int(surface.canvas.width), ceil(max(u for u, _ in corners))) - dx
    h = min(int(surface.canvas.height), ceil(max(v for _, v in corners))) - dy
    if min(w, h) <= 0:
        return
    tile = skia.Surface.MakeRasterN32Premul(w, h)
    canvas = tile.getCanvas()
    canvas.setMatrix(
        skia.Matrix.MakeAll(m.a, m.c, m.e - dx, m.b, m.d, m.f - dy, 0, 0, 1)
    )
    red, green, blue, opacity = _rgba(color)
    ink = 0xFF000000 | (red << 16) | (green << 8) | blue
    paint = skia.Paint(Color=ink, AntiAlias=True)
    blob = skia.TextBlob.MakeFromPosTextH(text, font.getXPos(glyphs), 0, font)
    canvas.drawTextBlob(blob, x, y, paint)
    rgba = tile.makeImageSnapshot().toarray(
        colorType=skia.ColorType.kRGBA_8888_ColorType
    )
    coverage = rgba[:, :, 3:4].astype(float) / 255
    # Grayscale contrast compensation before compositing. Preserve the
    # fractional coverage until all three ink channels have been blended.
    coverage += 0.145 * coverage * (1 - coverage)
    coverage *= ctx.globalAlpha * opacity / 255
    bg = np.frombuffer(
        bytes(ctx.getImageData(dx, dy, w, h).data), dtype=np.uint8
    ).reshape(h, w, 4)
    dst_alpha = bg[:, :, 3:4] / 255 * (1 - coverage)
    out_alpha = coverage + dst_alpha
    foreground = np.array([red, green, blue])
    blended = (foreground * coverage + bg[:, :, :3] * dst_alpha) / np.where(
        out_alpha > 0, out_alpha, 1
    )
    pixels = np.rint(np.concatenate((blended, out_alpha * 255), axis=2)).astype(
        np.uint8
    )
    ctx.putImageData(ImageData(pixels.tobytes(), w, h), dx, dy)
