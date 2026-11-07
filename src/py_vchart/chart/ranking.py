"""First complete page of a horizontal ranking list."""

from .._deps.vscale import linear
from .cartesian import DYNAMIC, check_keys
from .layout_helpers import BLUE, field, number


def render_ranking(spec, surface, width, height):
    hidden = ("nameLabel","valueLabel","orderLabel","rankingIcon")
    check_keys(spec,DYNAMIC | {"type","width","height","xField","yField","data","pageSize",
               "bar","barBackground","decorateHaloIcons",*hidden},"rankingList")
    if any(spec.get(k)!={"visible":False} for k in hidden) or spec.get("decorateHaloIcons",[]):
        raise ValueError("rankingList requires hidden labels, icons, and halos")
    rows = spec.get("data")
    n = spec.get("pageSize",5)
    if not isinstance(rows,list) or type(n) is not int or n<1 or len(rows)<n:
        raise ValueError("rankingList requires a complete first page")
    values = [number(row,spec.get("xField")) for row in rows]
    names = [field(row,spec.get("yField")) for row in rows[:n]]
    if len(set(names))!=n:
        raise ValueError("rankingList requires distinct names per page")
    lo,hi = min(values),max(values)
    if lo==hi:
        lo,hi = lo-10,hi+2.5
    else:
        lo -= (hi-lo)/3
        hi = lo+(hi-lo)/.8
    bar = spec.get("bar",{})
    back = spec.get("barBackground",{})
    check_keys(bar,{"height","style"},"rankingList.bar")
    check_keys(back,{"visible","style"},"rankingList.barBackground")
    for mark in (bar,back):
        check_keys(mark.get("style",{}),{"fill","cornerRadius"},"rankingList.style")
    w = width-20
    if w<=0:
        raise ValueError("rankingList requires width above 20")
    h = bar.get("height",10)
    surface.rect([0,0,width,height],"white")
    boxes = []
    step = height/(n+.9)
    for i,v in enumerate(values[:n]):
        y = step*(i+.95)
        right = 5+linear(v,[lo,hi],[0,w])
        box = [5,y-h/2,right,y+h/2]
        for mark,edge,color in [(back,w+5,"rgba(33,37,44,0.1)"),(bar,right,BLUE)]:
            if mark.get("visible",True) and (mark is bar or "height" in bar):
                style = mark.get("style",{})
                radius = style.get("cornerRadius",5)
                ctx = surface.ctx
                ctx.beginPath()
                ctx.roundRect(5,y-h/2,edge-5,h,radius)
                ctx.fillStyle = style.get("fill",color)
                ctx.fill()
        boxes.append(box)
    return dict(plot=[5,0,w,height],labels=[],axes=[
        dict(orient="left",domain=names,range=[0,height]),dict(orient="bottom",domain=[lo,hi],range=[0,w])],
        marks={"0.bar":boxes})
