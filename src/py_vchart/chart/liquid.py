"""Static liquid glyph with three clipped monotone waves."""

from math import tau

from .layout_helpers import BLUE
from .polar import PolarFrame
from .radial import unit_value


def wave(ctx, start, height, alpha):
    top = 0
    ctx.beginPath()
    ctx.moveTo(start, top + 20)
    for i in range(20):
        x = start + i * 50
        y0, y1 = (top, top + 20) if i % 2 else (top + 20, top)
        ctx.bezierCurveTo(x + 50/3, top+10 if i == 0 else y0,
                          x + 50 - 50/3, top+10 if i == 19 else y1, x + 50, y1)
    ctx.lineTo(start + 1000, top + height)
    ctx.lineTo(start, top + height)
    ctx.closePath()
    ctx.fillStyle = BLUE
    ctx.globalAlpha = alpha
    ctx.fill()
    return [[start + i*50, 0 if i % 2 else 20, height] for i in range(21)]


def render_liquid(spec, surface, width, height):
    frame = PolarFrame(spec, surface, width, height, {"maskShape"})
    value = unit_value(frame)
    shape = spec.get("maskShape", "circle")
    if shape not in {"circle", "rect"} or frame.radius <= 10:
        raise ValueError("liquid requires a circle or rect with room for the outline")
    x, y = frame.center
    rw, rh = frame.plot[2:] if shape == "rect" else [2 * frame.radius] * 2
    ctx = surface.ctx
    ctx.save()
    for inset in (0, 10):
        ctx.beginPath()
        if shape == "rect":
            ctx.rect(x-rw/2+inset, y-rh/2+inset, rw-2*inset, rh-2*inset)
        else:
            ctx.arc(x, y, rw/2-inset, 0, tau)
        if inset == 0:
            ctx.strokeStyle = "#1ac6ff"
            ctx.lineWidth = 2
            ctx.stroke()
        else:
            ctx.clip()
    bottom = y + rh/2 - 10
    level = (rh-20) * value
    origin = x + frame.plot[0]
    ctx.translate(origin, bottom-level)
    frame.marks["waves"] = []
    for offset, alpha in [(0, 1), (-40, .66), (-20, .33)]:
        points = wave(ctx, -500 + offset, level, alpha)
        frame.marks["waves"].append([[origin+px, bottom-level+py, bottom-level+base] for px, py, base in points])
    ctx.restore()
    frame.marks["liquid"] = [[origin, bottom-level, level, "rect" if shape == "rect" else "symbol",
                              x-rw/2+10, y-rh/2+10, x+rw/2-10, bottom]]
    return frame.scene()
