"""OHLC candles on the shared Cartesian frame."""

from .layout_helpers import field, make_frame, number, records, result
from .point import mark_options


def render_candlestick(spec, surface, width, height):
    fields = ["openField", "highField", "lowField", "closeField"]
    rows = records(spec, {*fields, "candlestick", "rising", "falling", "doji"})
    keys = [field(row, spec.get("xField")) for row in rows]
    prices = [[number(row, spec.get(k)) for k in fields] for row in rows]
    frame = make_frame(spec, surface, width, height, keys, [v for row in prices for v in row])
    marks = draw_candles(spec, surface, frame, keys, prices)
    return result(surface,frame,candlestick=marks)


def draw_candles(spec, surface, frame, keys, prices):
    visible, base = mark_options(spec, "candlestick", {"lineWidth","stroke","boxFill","boxWidth"})
    marks = []
    for key, (opening, high, low, closing) in zip(keys, prices):
        if not visible:
            continue
        role = "rising" if closing > opening else "falling" if closing < opening else "doji"
        show, specific = mark_options(spec, role, {"lineWidth","stroke","boxFill"})
        if not show:
            continue
        style = base | specific
        color = {"rising":"#ff0000","falling":"#00aa00","doji":"black"}[role]
        stroke = style.get("stroke",color)
        breadth = style.get("boxWidth",frame.positions[key][1])
        x, o = frame.point(key,opening)
        h,l,c = [frame.value_pixel(v) for v in (high,low,closing)]
        marks.append([x,breadth,o,h,l,c])
        ctx = surface.ctx
        ctx.save()
        ctx.lineWidth = style.get("lineWidth",1)
        surface.line(x,h,x,l,stroke)
        box = [x-breadth/2,min(o,c),x+breadth/2,max(o,c)]
        surface.rect(box,style.get("boxFill",color))
        if o == c:
            surface.line(box[0],o,box[2],o,stroke)
        else:
            surface.outline(box,stroke)
        ctx.restore()
    return marks
