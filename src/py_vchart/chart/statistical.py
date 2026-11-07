"""Histogram bins, box-and-whisker summaries, and cumulative waterfall columns."""

from .layout_helpers import BLUE, field, fields, make_frame, number, records, rect_between, result
from .cartesian import check_keys
from .point import draw_points, mark_options


def render_histogram(spec, surface, width, height):
    rows = records(spec, {"x2Field", "y2Field", "bar"})
    horizontal = spec.get("direction") == "horizontal"
    start, count = fields(spec, horizontal)
    end = spec.get("y2Field" if horizontal else "x2Field")
    bins = [(number(r, start), number(r, end), number(r, count)) for r in rows]
    frame = make_frame(spec, surface, width, height, [v for a, b, _ in bins for v in (a, b)],
                       [v for _, _, v in bins], horizontal=horizontal, first_kind="linear", reverse_side="left" if horizontal else None)
    visible, style = mark_options(spec, "bar", {"fill"})
    boxes = []
    for a, b, count in bins if visible else []:
        x, y = frame.point(a, 0)
        x1, y1 = frame.point(b, count)
        box = [min(x, x1), min(y, y1), max(x, x1), max(y, y1)]
        surface.rect(box, style.get("fill", BLUE))
        boxes.append(box)
    return result(surface, frame, bar=boxes)


def render_box_plot(spec, surface, width, height):
    quantiles = ("minField", "q1Field", "medianField", "q3Field", "maxField")
    rows = records(spec, {*quantiles, "boxWidth", "outliersField", "outlier"})
    horizontal = spec.get("direction") == "horizontal"
    cat, _ = fields(spec, horizontal)
    keys = [field(r, cat) for r in rows]
    summaries = [[number(r, spec.get(k)) for k in quantiles] for r in rows]
    outliers = [field(row, spec["outliersField"]) for row in rows] if "outliersField" in spec else []
    if not all(isinstance(values, list) for values in outliers):
        raise ValueError("boxPlot.outliersField must identify lists of values")
    domain = [v for q in summaries + outliers for v in q]
    frame = make_frame(spec, surface, width, height, keys, domain,
                       horizontal=horizontal)
    marks = []
    for key, q in zip(keys, summaries):
        center = frame.point(key, 0)[1 if horizontal else 0]
        breadth = spec.get("boxWidth", frame.positions[key][1])
        if type(breadth) not in (float, int) or breadth <= 0:
            raise ValueError("boxPlot.boxWidth must be a positive number")
        points = [frame.point(key, v) for v in q]
        marks.append([center, breadth, *[frame.value_pixel(v) for v in q]])
        surface.line(*points[0], *points[-1], BLUE)
        box = rect_between(frame, key, q[1], q[3], breadth)
        surface.rect(box, "white")
        surface.outline(box, BLUE)
        for i in (0, 2, 4):
            x, y = points[i]
            if horizontal:
                surface.line(x, y - breadth / 2, x, y + breadth / 2, BLUE)
            else:
                surface.line(x - breadth / 2, y, x + breadth / 2, y, BLUE)
    geometry = {"boxPlot": marks}
    if "outliersField" in spec:
        show, style = mark_options(spec, "outlier", {"fill", "size", "stroke", "lineWidth"})
        points = [frame.point(k, v) for k, values in zip(keys, outliers) for v in values] if show else []
        draw_points(surface, points, style, size=10, width=0)
        geometry["outlier"] = points
    return result(surface, frame, **geometry)


def render_waterfall(spec, surface, width, height):
    rows = records(spec, {"stackLabel", "leaderLine"})
    horizontal = spec.get("direction") == "horizontal"
    cat, val = fields(spec, horizontal)
    labels = spec.get("stackLabel", {})
    check_keys(labels, {"visible"}, "waterfall.stackLabel")
    leader = spec.get("leaderLine", {})
    check_keys(leader, {"visible"}, "waterfall.leaderLine")
    running = 0
    intervals = []
    for row in rows:
        delta = number(row, val)
        intervals.append((field(row, cat), running, running + delta, "increase" if delta >= 0 else "decrease"))
        running += delta
    intervals.append(("total", 0, running, "total"))
    keys = [k for k, *_ in intervals]
    frame = make_frame(spec, surface, width, height, keys, [b for _, _, b, _ in intervals], horizontal=horizontal)
    colors = {"increase": BLUE, "decrease": "#1ac6ff", "total": "#ff8a00"}
    bars = []
    previous = None
    for key, start, end, role in intervals:
        box = rect_between(frame, key, start, end)
        if previous and leader.get("visible", True):
            coord = frame.value_pixel(running if role == "total" else start)
            ctx = surface.ctx
            ctx.save()
            ctx.setLineDash([4, 4])
            if horizontal:
                surface.line(coord, previous[3], coord, box[1], "black")
            else:
                surface.line(previous[2], coord, box[0], coord, "black")
            ctx.restore()
        surface.rect(box, colors[role])
        bars.append(box)
        previous = box
    annotations = draw_totals(surface, frame, intervals) if labels.get("visible", True) else []
    return result(surface, frame, bar=bars, stackLabel=annotations)


def draw_totals(surface, frame, intervals):
    marks = []
    ctx = surface.ctx
    ctx.save()
    ctx.fillStyle = "black"
    ctx.font = ctx.font.replace("12px", "14px")
    for key, start, end, _ in intervals:
        x, y = frame.point(key, end)
        positive = end >= start
        if frame.horizontal:
            ctx.textAlign = "left" if positive else "right"
            ctx.textBaseline = "middle"
            anchor = x + (12 if positive else -12)
            marks.append([f"{end-start:g}", anchor, y])
            ctx.fillText(f"{end-start:g}", anchor, y)
        else:
            ctx.textAlign = "center"
            ctx.textBaseline = "bottom" if positive else "top"
            top = frame.plot[1]
            anchor = max(top + 15.4, y - 12) if positive else min(top + frame.plot[3] - 15.4, y + 12)
            marks.append([f"{end-start:g}", x, anchor])
            ctx.fillText(f"{end-start:g}", x, anchor + (1 if positive else -2))
    ctx.restore()
    return marks
