"""Static categorical event lanes, in horizontal or vertical orientation."""

from .._deps.vdataset import inline_values
from .cartesian import DYNAMIC, check_keys
from .layout_helpers import field, palette_for
from .plot import plot_region
from .point import mark_options


def centers(domain, start, end):
    return {key:start+(end-start)*(i+.5)/len(domain) for i,key in enumerate(domain)}


def render_timeline(spec, surface, width, height):
    check_keys(spec, DYNAMIC | {"type","width","height","padding","background","data","direction",
               "timeField","seriesField","eventField","dot","line","title","subTitle"}, "timeline")
    if any(spec.get(k, {"visible":False}) != {"visible":False} for k in ("title","subTitle")):
        raise ValueError("timeline supports hidden titles")
    if spec.get("eventField") and "title" not in spec:
        raise ValueError("timeline.eventField requires title.visible=false")
    direction = spec.get("direction","horizontal")
    if direction not in ("horizontal","vertical"):
        raise ValueError("Invalid timeline direction")
    vertical = direction == "vertical"
    rows = inline_values(spec.get("data"),"timeline.data")
    records = [(field(row,spec.get("timeField")),field(row,spec["seriesField"]) if "seriesField" in spec else None)
               for row in rows]
    times = list(dict.fromkeys(t for t,_ in records))
    lanes = list(dict.fromkeys(g for _,g in records))
    plot = plot_region(spec,surface,width,height)
    x,y,w,h = plot
    tick = centers(times,y,y+h) if vertical else centers(times,x,x+w)
    lane = centers(lanes,x,x+w) if vertical else centers(lanes,y+h,y)
    show,style = mark_options(spec,"line",{"stroke","lineWidth"})
    marks = {}
    if show:
        marks["line"] = []
        for p in lane.values():
            segment = [[p,y],[p,y+h]] if vertical else [[x,p],[x+w,p]]
            surface.polyline(segment,style.get("stroke","#c0c3c7"),style.get("lineWidth",1))
            marks["line"].extend(segment)
    show,style = mark_options(spec,"dot",{"fill","size"})
    if show:
        marks["dot"] = []
        palette = palette_for(len(lanes))
        colors = {k:palette[i%len(palette)] for i,k in enumerate(lanes)}
        for t,g in records:
            point = [lane[g],tick[t]] if vertical else [tick[t],lane[g]]
            marks["dot"].append(point)
            surface.circle(*point,style.get("size",8),style.get("fill",colors[g]),None,0)
    axes = [dict(orient="bottom",domain=lanes if vertical else times,range=[0,w]),
            dict(orient="left",domain=times if vertical else lanes,range=[0,h] if vertical else [h,0])]
    return dict(plot=plot,labels=[],axes=axes,marks=marks)
