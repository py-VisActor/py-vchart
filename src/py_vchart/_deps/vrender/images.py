"""Decode self-contained image resources without network access."""

import base64


def embedded_image(uri):
    from py_skia_canvas import Image

    if (
        not isinstance(uri, str)
        or not uri.startswith("data:image/")
        or ";base64," not in uri
    ):
        raise ValueError("Expected an embedded base64 image")
    return Image(base64.b64decode(uri.split(",", 1)[1], validate=True))


def draw_fitted_image(ctx, uri, x, y, width, height, style):
    """Fit an embedded image into a static card's content box."""
    from math import floor

    image = embedded_image(uri)
    mode = style.get("imageMode", "contain")
    if mode == "fill":
        iw, ih = width, height
    elif mode in ("contain", "cover", "auto"):
        scale = (
            1
            if mode == "auto"
            else (min if mode == "contain" else max)(
                width / image.width, height / image.height
            )
        )
        iw, ih = image.width * scale, image.height * scale
    else:
        raise ValueError(f"Unsupported card imageMode {mode}")
    position = style.get("imagePosition", "center")
    left = x + (
        0
        if "left" in position
        else width - iw
        if "right" in position
        else (width - iw) / 2
    )
    top = y + (
        0
        if "top" in position
        else height - ih
        if "bottom" in position
        else (height - ih) / 2
    )
    ctx.save()
    if mode in ("cover", "auto"):
        ctx.beginPath()
        ctx.rect(x, y, width, height)
        ctx.clip()
    ctx.globalAlpha = style.get("opacity", 1)
    x0, y0 = floor(left + 0.5), floor(top + 0.5)
    ctx.drawImage(
        image, x0, y0, floor(left + iw + 0.5) - x0, floor(top + ih + 0.5) - y0
    )
    ctx.restore()
