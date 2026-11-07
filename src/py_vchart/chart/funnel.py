"""Stage and conversion polygons, projected along the funnel orientation."""

from .._deps.vdataset import read_records
from .cartesian import DYNAMIC, GRID, check_keys
from .layout_helpers import palette_for
from .plot import hidden_label, nonnegative, plot_region


def breadth(value, length):
    if isinstance(value, str) and value.endswith("%"):
        return length * nonnegative(float(value[:-1]), "funnel size") / 100
    return nonnegative(value, "funnel size")


def render_funnel(spec, surface, width, height):
    check_keys(spec, DYNAMIC | {"type", "width", "height", "padding", "background", "data", "categoryField",
               "valueField", "funnelOrient", "funnelAlign", "shape", "gap", "isCone", "isTransform",
               "heightRatio", "minSize", "maxSize", "label"}, "funnel")
    hidden_label(spec)
    plot = plot_region(spec, surface, width, height)
    rows = read_records(spec.get("data"), spec.get("categoryField"), spec.get("valueField"), path="funnel.data")
    orient = spec.get("funnelOrient", "top")
    shape = spec.get("shape", "trapezoid")
    if orient not in ("top", "bottom", "left", "right") or shape not in ("rect", "trapezoid"):
        raise ValueError("Invalid funnel orientation or shape")
    sideways = orient in ("left", "right")
    length, cross = plot[2:] if sideways else plot[2:][::-1]
    align = spec.get("funnelAlign", "center")
    alignments = ("top", "center", "bottom") if sideways else ("left", "center", "right")
    if align not in alignments:
        raise ValueError("Invalid cross-axis funnelAlign")
    marks = {"funnel": []}
    transform = spec.get("isTransform", False)
    if transform:
        marks["transform"] = []
    gap = 0 if transform else nonnegative(spec.get("gap", 0), "funnel.gap")
    ratio = nonnegative(spec.get("heightRatio", .5), "funnel.heightRatio") or .5
    scene = dict(plot=plot, labels=[], axes=[], marks=marks)
    if not rows:
        return scene
    count = len(rows)
    stages = count + (ratio * (count-1) if transform else 0)
    step = (length-gap*(count-1)) / stages
    if step <= 0:
        raise ValueError("funnel.gap exceeds available space")
    link = step * ratio if transform else gap
    small, large = [breadth(spec.get(k, default), cross)
                    for k, default in (("minSize", 0), ("maxSize", "80%"))]
    values = [nonnegative(v, "funnel value") for _, v in rows]
    maximum = max(values)
    widths = [small + (large-small)*v/maximum if maximum else large for v in values]
    widths.append(small if spec.get("isCone", True) else widths[-1])
    palette = palette_for(len(set(k for k, _ in rows)))
    colors = {k: palette[i % len(palette)] for i, k in enumerate(dict.fromkeys(k for k, _ in rows))}

    def edge(position, size):
        lo = (cross-size) * alignments.index(align)/2
        hi = lo + size
        if orient in ("bottom", "right"):
            position = length-position
        if orient in ("bottom", "left"):
            lo, hi = hi, lo
        if sideways:
            return [[plot[0]+position, plot[1]+v] for v in (lo, hi)]
        return [[plot[0]+v, plot[1]+position] for v in (lo, hi)]

    def polygon(name, start, end, upper, lower, color):
        points = edge(start, upper) + edge(end, lower)[::-1]
        marks[name].append(points)
        surface.polygon(points, color)

    for i, (category, _) in enumerate(rows):
        start = i*(step+link)
        lower = widths[i] if shape == "rect" else widths[i+1]
        polygon("funnel", start, start+step, widths[i], lower, colors[category])
    if transform:
        for i in range(count-1):
            start = i*(step+link)+step
            upper = widths[i] if shape == "rect" else widths[i+1]
            polygon("transform", start, start+link, upper, widths[i+1], GRID)
    return scene
