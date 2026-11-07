"""Static decoration shared by the ranking and sequence panels."""

from .control_icons import PATHS


def control_symbol(surface, name, x, y, size, fill, stroke=None, line_width=1):
    from py_skia_canvas import Path2D

    path = Path2D(PATHS[name])
    bounds = path.bounds
    scale = size / max(bounds["width"], bounds["height"])
    ctx = surface.ctx
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(scale, scale)
    ctx.fillStyle = fill
    ctx.fill(path)
    if stroke:
        ctx.strokeStyle = stroke
        ctx.lineWidth = line_width / scale
        ctx.stroke(path)
    ctx.restore()


def rounded_rect(surface, x, y, w, h, radius, color):
    ctx = surface.ctx
    ctx.beginPath()
    ctx.roundRect(x, y, w, h, radius)
    ctx.fillStyle = color
    ctx.fill()


def slider_thumb(surface, x, y, color):
    """Paint the color handle and its offset, shadow-casting white rim."""
    from math import floor, pi
    import numpy as np
    from py_skia_canvas import ImageData

    ctx = surface.ctx
    ctx.save()
    ctx.shadowColor = "rgba(33,37,44,0.09)"
    ctx.shadowBlur = 10
    ctx.shadowOffsetY = 4
    surface.circle(x, y, 10, color, None, 0)
    ctx.beginPath()
    ctx.arc(x, y, 5.8, 0, 2 * pi)
    ctx.lineWidth = 2
    ctx.strokeStyle = "white"
    ctx.stroke()
    ctx.restore()

    # The Canvas backend rounds separate passes. Composite the rim shadow
    # on the opaque face in 8-bit premultiplied color, as Chromium does.
    left, top = floor(x - 5), floor(y - 5)
    pixels = (
        np.frombuffer(bytes(ctx.getImageData(left, top, 11, 11).data), dtype=np.uint8)
        .reshape(11, 11, 4)
        .copy()
    )
    ys, xs = np.ogrid[:11, :11]
    dx, dy = xs + left + 0.5 - x, ys + top + 0.5 - y
    face = dx**2 + dy**2 <= (5.8 - 1 - 0.5) ** 2
    r = np.hypot(dx, dy - 4)
    # Gaussian convolution of a thin circular rim of radius R and width 2.
    radius, sigma = 5.8, 6
    mask = (
        2
        * radius
        / sigma**2
        * np.exp(-(r * r + radius**2) / (2 * sigma**2))
        * np.i0(r * radius / sigma**2)
    )
    alpha = np.rint(mask * 25.5).astype(int)[:, :, None]
    ink = np.array([int(color[i : i + 2], 16) for i in (1, 3, 5)])
    shaded = ink * (255 - alpha) // 255 + np.array([33, 37, 44]) * alpha // 255
    pixels[face, :3] = shaded[face]
    ctx.putImageData(ImageData(pixels.tobytes(), 11, 11), left, top)
