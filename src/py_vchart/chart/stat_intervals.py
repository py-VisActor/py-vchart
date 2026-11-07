"""Horizontal statistical estimates with optional uncertainty intervals."""

from collections import defaultdict
from math import ceil, sqrt
from statistics import mean, median, stdev

from .cartesian import Axis, CartesianFrame, AXIS, check_keys, frame_scene
from .layout_helpers import field, number
from .._deps.vscale import bands
from .statplots import axis_for


def sample_interval(values, estimator, config):
    values.sort()
    estimate = estimator(values)
    if config is False:
        return estimate,None,None
    kind = config.get("kind","confidence")
    if kind == "range":
        return estimate,values[0],values[-1]
    if len(values)<2:
        return estimate,None,None
    if kind in ("standardError","standardDeviation"):
        delta = stdev(values)*config.get("multiplier",1)
        if kind=="standardError":
            delta /= sqrt(len(values))
        return estimate,estimate-delta,estimate+delta
    distribution = values
    if kind=="confidence":
        state = config.get("seed",0)
        repeats = config.get("resamples",1000)
        if type(repeats) is not int or not 100<=repeats<=10000:
            raise ValueError("Invalid confidence resamples")
        distribution = []
        for _ in range(repeats):
            sample = []
            for _ in values:
                state = (1664525*state+1013904223) & 0xffffffff
                sample.append(values[state*len(values)//(1<<32)])
            distribution.append(estimator(sample))
        distribution.sort()
    elif kind!="percentile":
        raise ValueError("Unknown sample interval")
    level = config.get("level",.95)
    if not 0<level<1:
        raise ValueError("Invalid confidence level")
    def quantile(p):
        i = p*(len(distribution)-1)
        return distribution[int(i)]+(i-int(i))*(distribution[ceil(i)]-distribution[int(i)])
    return estimate,quantile((1-level)/2),quantile((1+level)/2)


def render_horizontal(spec,surface,width,height):
    feature = spec["type"]=="featureImportancePlot"
    allowed = {"method","interval"} if feature else {"input","interval","estimator","errorBar","referenceLine"}
    check_keys(spec,allowed|{"type","data","width","height"},spec["type"])
    rows = spec.get("data")
    if not isinstance(rows,list) or not rows or any(not isinstance(r,dict) or "series" in r for r in rows):
        raise ValueError("Horizontal estimates require a nonempty single series")
    if feature or spec.get("input")=="estimates":
        records = [(field(r,"feature" if feature else "category"),number(r,"importance" if feature else "estimate"),
                    number(r,"lower") if "lower" in r else None,number(r,"upper") if "upper" in r else None) for r in rows]
    elif spec.get("input")=="observations":
        groups = defaultdict(list)
        for r in rows:
            groups[field(r,"category")].append(number(r,"value"))
        estimator = {"mean":mean,"median":median}[spec.get("estimator","mean")]
        records = [(k,*sample_interval(vs,estimator,spec.get("errorBar",{}))) for k,vs in groups.items()]
    else:
        raise ValueError("Expected estimates or observations")
    values = [v for _,*vs in records for v in vs if v is not None]
    x = axis_for("bottom",values,False,(),feature)
    cats = [r[0] for r in records]
    y = Axis.make("left","band",cats,{},"statplot")
    label_width = max(surface.measure(str(k)) for k in cats)
    left = round(60+label_width)
    bottom = height-60
    w,h = width-left-16,bottom-16
    frame = CartesianFrame((left,16,w,h),True,{"bottom":x,"left":y},{"left":bands(cats,h)})
    surface.rect((0,0,width,height),"white")
    surface.line(left,16,left,bottom,AXIS)
    for k in cats:
        cy = frame.coordinate("left",k)
        surface.line(left-4,cy,left,cy,AXIS)
        surface.label(k,left-16,cy,"right","middle")
    for t in x.ticks:
        align = "left" if t==x.domain[0] else "right" if t==x.domain[1] else "center"
        surface.label(x.label(t),frame.coordinate("bottom",t),bottom+8,align,"top",line_height=12)
    titles = (f"重要性（{spec['method']}）","特征") if feature else ("估计值","分组")
    ctx = surface.ctx
    ctx.save()
    ctx.fontHinting = True
    ctx.fillStyle = "#606773"
    ctx.textBaseline = "alphabetic"
    ctx.textAlign = "left"
    ctx.fillText(titles[0],left+w/2-surface.measure(titles[0])/2,bottom+40.8)
    ctx.translate(left-28-label_width,16+h/2)
    ctx.rotate(-1.5707963267948966)
    ctx.fillText(titles[1],-surface.measure(titles[1])/2,-3.2)
    ctx.restore()
    bars,intervals,points,caps = [],[],[],[]
    color = "#0173b2"
    for cat,estimate,low,high in records:
        px,py = frame.point(cat,estimate)
        if feature:
            zero = frame.coordinate("bottom",0)
            half = frame.positions[cat][1]/2
            box = [min(zero,px),py-half,max(zero,px),py+half]
            surface.rect(box,color)
            bars.append(box)
        if low is not None and high is not None:
            a,b = frame.coordinate("bottom",low),frame.coordinate("bottom",high)
            box = [a,py-1,b,py+1]
            surface.rect(box,"#21252c" if feature else color)
            intervals.append(box)
            if not feature:
                caps.extend([[a,py],[b,py]])
        if not feature:
            points.append([px,py])
    for pt in points:
        surface.circle(*pt,8,color,None,0,.8)
    for px,py in caps:
        ctx.globalAlpha = .8
        surface.rect([px-1,py-5,px+1,py+5],color)
        ctx.globalAlpha = 1
    marks = {"0.bar":bars} if feature else {"0.bar":intervals,"1.point":points,"2.point":caps}
    if feature and intervals:
        marks["1.bar"] = intervals
    ref = spec.get("referenceLine")
    if ref:
        px = frame.coordinate("bottom",ref["value"])
        ctx.save()
        ctx.setLineDash([4,4])
        surface.line(px,16,px,bottom,"#606773")
        ctx.restore()
        if ref.get("label"):
            ctx.save()
            ctx.font = ctx.font.replace("12px","14px")
            text = str(ref["label"])
            label_w = surface.measure(text)
            cx = px-5
            ctx.beginPath()
            ctx.roundRect(cx-label_w/2-4,-2,label_w+8,18,3)
            ctx.fillStyle = "#f1f2f5"
            ctx.globalAlpha = .8
            ctx.fill()
            ctx.globalAlpha = 1
            ctx.fontHinting = True
            ctx.fillStyle = "#21252c"
            ctx.textAlign = "left"
            ctx.textBaseline = "alphabetic"
            ctx.fillText(text,cx-label_w/2,12.5)
            ctx.restore()
    return frame_scene(surface,frame) | {"marks":marks}
