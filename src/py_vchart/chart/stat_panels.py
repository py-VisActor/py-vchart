"""Numeric panels used by pair plots and hexagonal count maps."""

from bisect import bisect_right
from collections import Counter
from math import ceil, floor, isfinite, log2, log10, pi, sqrt

from .._deps.vrender.controls import slider_thumb
from .._deps.vscale.stat_colors import VIRIDIS
from .cartesian import GRID, Axis, CartesianFrame, check_keys, frame_scene
from .stat_matrix import ramp, text_at
from .statplots import STAT_COLORS, draw_legend


def extent(values):
    if not values:
        return 0, 1
    lo, hi = min(values), max(values)
    if lo == hi:
        radius = max(1, abs(lo)) / 2
        return lo - radius, hi + radius
    return lo, hi


def numeric_panel(surface, rect, domains, titles, tick_count):
    axes = {}
    for side, (lo, hi) in zip(("bottom", "left"), domains):
        power = 10 ** floor(log10((hi - lo) / tick_count))
        ratio = (hi - lo) / (power * tick_count)
        factor = (
            10
            if ratio >= sqrt(50)
            else 5
            if ratio >= sqrt(10)
            else 2
            if ratio >= sqrt(2)
            else 1
        )
        step = factor * power
        ticks = [
            float(f"{i * step:.14g}")
            for i in range(ceil(lo / step), floor(hi / step) + 1)
        ]
        if side == "left" and len(ticks) > 1:
            # Grid rows and tick labels share the axis sampling interval.
            separation = rect[3] * step / (hi - lo)
            ticks = ticks[:: max(1, ceil(20 / separation))]
        axes[side] = Axis(side, "linear", [lo, hi], ticks, True)
    frame = CartesianFrame(rect, False, axes, {})
    left, top, w, h = rect
    for side, axis in axes.items():
        for tick in axis.ticks:
            pos = frame.coordinate(side, tick)
            if side == "left":
                surface.line(left, pos, left + w, pos, GRID)
                baseline = (
                    "bottom"
                    if tick == axis.domain[0]
                    else "top"
                    if tick == axis.domain[1]
                    else "middle"
                )
                x, y, align = left - 12, pos, "right"
                offset = {"bottom": -1, "top": 11, "middle": 5}[baseline]
            else:
                align = (
                    "left"
                    if tick == axis.domain[0]
                    else "right"
                    if tick == axis.domain[1]
                    else "center"
                )
                x, y, baseline, offset = pos, top + h + 8, "top", 11
            label = axis.label(tick)
            surface.labels.append(
                dict(text=label, x=x, y=y, align=align, baseline=baseline)
            )
            text_at(surface, label, x, floor(y + offset + 0.5), 12, "#89909d", align)
    text_at(
        surface,
        titles[0],
        left + w / 2,
        floor(top + h + 40.8 + 0.5),
        12,
        "#606773",
        "center",
    )
    axis = axes["left"]
    width = max((surface.measure(axis.label(t)) for t in axis.ticks), default=0)
    surface.ctx.save()
    surface.ctx.translate(left - width - 24, top + h / 2)
    surface.ctx.rotate(-pi / 2)
    text_at(surface, titles[1], 0, -2.8, 12, "#606773", "center")
    surface.ctx.restore()
    return frame


def render_pairs(spec, surface, width, height):
    check_keys(
        spec,
        {"type", "variables", "data", "width", "height", "diagonal", "colors"},
        "pairPlot",
    )
    variables = spec["variables"]
    rows = spec["data"]["observations"]
    groups = list(dict.fromkeys(r.get("series") for r in rows))
    grouped = any(g is not None for g in groups)
    if grouped and None in groups:
        raise ValueError("pairPlot requires a series on every grouped observation")
    palette = spec.get("colors", {}).get("categorical", "colorblind")
    if palette == "colorblind":
        palette = STAT_COLORS
    elif palette == "deep":
        from .._deps.vscale.stat_colors import DEEP

        palette = DEEP
    elif palette == "vchart":
        from .layout_helpers import palette_for

        palette = palette_for(len(groups))
    if not isinstance(palette, (tuple, list)) or not palette:
        raise ValueError("Expected a nonempty categorical palette")
    colors = {g: palette[i % len(palette)] for i, g in enumerate(groups)}
    diagonal = spec.get("diagonal", {})
    if diagonal.get("type", "histogram") != "histogram":
        raise ValueError("pairPlot requires histogram diagonal panels")
    columns = {
        k: [r["values"][k] for r in rows if r["values"][k] is not None]
        for k in variables
    }
    domains = {k: extent(v) for k, v in columns.items()}
    n = len(variables)
    if not n or len(columns) != n:
        raise ValueError("pairPlot requires distinct variables")
    w = (width - 32) / n - 74
    h = max(30, (height - 90 - (32 if grouped else 0)) / n - 50)
    if w <= 0:
        raise ValueError("pairPlot canvas too narrow")
    surface.rect((0, 0, width, height), "white")
    axes, marks = [], {}
    for i, y in enumerate(variables):
        for j, x in enumerate(variables):
            rect = (80 + j * (w + 74), 24 + i * (h + 50), w, h)
            name = str(i * n + j)
            if i == j:
                values = columns[x]
                lo, hi = domains[x]
                count = diagonal.get("binning", {}).get(
                    "binCount", min(200, ceil(log2(max(1, len(values))) + 1))
                )
                if type(count) is not int or not 1 <= count <= 200:
                    raise ValueError("binCount must be an integer between 1 and 200")
                if len(set(values)) < 2:
                    count = 1
                edges = [lo + (hi - lo) * (b / count) for b in range(count + 1)]
                counts = {}
                for row in rows:
                    v = row["values"][x]
                    if v is not None:
                        bucket = min(count - 1, bisect_right(edges, v) - 1)
                        counts.setdefault(row.get("series"), Counter())[bucket] += 1
                frame = numeric_panel(
                    surface,
                    rect,
                    [
                        domains[x],
                        (0, max((max(c.values()) for c in counts.values()), default=1)),
                    ],
                    [x, f"计数 · n={len(values)}"],
                    3,
                )
                boxes = []
                for group, bins in counts.items():
                    for b in range(count):
                        box = [
                            *frame.point(edges[b], bins[b]),
                            *frame.point(edges[b + 1], 0),
                        ]
                        surface.ctx.globalAlpha = 115 / 255
                        surface.rect(box, colors[group])
                        surface.ctx.globalAlpha = 1
                        boxes.append(box)
                marks[name + ".bar"] = boxes
            else:
                pairs = [
                    (r["values"][x], r["values"][y], r.get("series"))
                    for r in rows
                    if r["values"][x] is not None and r["values"][y] is not None
                ]
                frame = numeric_panel(
                    surface,
                    rect,
                    [domains[x], domains[y]],
                    [x, f"{y} · n={len(pairs)}"],
                    3,
                )
                points = [frame.point(px, py) for px, py, _ in pairs]
                for point, (_, _, group) in zip(points, pairs):
                    surface.circle(*point, 7, colors[group], None, 0, 0.8)
                marks[name + ".point"] = points
            axes.extend(frame_scene(surface, frame)["axes"])
    if grouped:
        draw_legend(
            surface, width, groups, "circle", palette, center_y=24 + n * (h + 50) + 25.8
        )
    return {
        "plot": [80, 24, w, h],
        "axes": axes,
        "marks": marks,
        "labels": sorted(surface.labels, key=lambda label: (label["x"], label["y"])),
    }


def hexagons(rows, resolution):
    xs, ys = zip(*[(r["x"], r["y"]) for r in rows])
    if not all(isfinite(v) for values in (xs, ys) for v in values):
        raise ValueError("hexbinPlot requires finite coordinates")
    x0, x1 = extent(xs)
    y0, y1 = extent(ys)
    radius = 2 / (3 * resolution)
    step = sqrt(3) * radius
    counts = Counter()
    for x, y in zip(xs, ys):
        u, v = (x - x0) / (x1 - x0), (y - y0) / (y1 - y0)
        qf = 2 * u / (3 * radius)
        sf = v / step - qf / 2
        tf = -qf - sf
        q, s, t = (floor(value + 0.5) for value in (qf, sf, tf))
        dq, ds, dt = abs(q - qf), abs(s - sf), abs(t - tf)
        if dq >= ds and dq >= dt:
            q = -s - t
        elif ds >= dt:
            s = -q - t
        counts[q, s] += 1
    offsets = [
        (radius, 0),
        (radius / 2, step / 2),
        (-radius / 2, step / 2),
        (-radius, 0),
        (-radius / 2, -step / 2),
        (radius / 2, -step / 2),
    ]
    bins = []
    for (q, s), count in sorted(counts.items()):
        u, v = 1.5 * radius * q, step * (s + q / 2)
        vertices = [
            (x0 + (u + du) * (x1 - x0), y0 + (v + dv) * (y1 - y0)) for du, dv in offsets
        ]
        bins.append((vertices, count))
    vx, vy = zip(*(p for vertices, _ in bins for p in vertices))
    xd, yd = extent(vx), extent(vy)
    aspect = ((xd[1] - xd[0]) / (x1 - x0)) / ((yd[1] - yd[0]) / (y1 - y0))
    return bins, (xd, yd), aspect


def render_hexbin(spec, surface, width, height):
    check_keys(
        spec,
        {"type", "data", "binning", "fieldLabels", "width", "height"},
        "hexbinPlot",
    )
    resolution = spec.get("binning", {}).get("xBins", 30)
    if type(resolution) is not int or not 1 <= resolution <= 200:
        raise ValueError("hexbinPlot xBins must be an integer between 1 and 200")
    rows = spec["data"]
    bins, domains, aspect = (
        hexagons(rows, resolution) if rows else ([], [(0, 1), (0, 1)], 1)
    )
    labels = spec.get("fieldLabels", {})
    y = Axis.make(
        "left",
        "linear",
        list(domains[1]),
        dict(zip(("min", "max"), domains[1])),
        "hexbinPlot",
    )
    left = round(56 + max(surface.measure(y.label(t)) for t in y.ticks))
    h = min(height - 76, (width - left - (68 if rows else 16)) / aspect)
    if h <= 0:
        raise ValueError("hexbinPlot canvas too small")
    surface.rect((0, 0, width, height), "white")
    frame = numeric_panel(
        surface,
        (left, 16, h * aspect, h),
        domains,
        [labels.get("x", "x"), labels.get("y", "y")],
        5,
    )
    maximum = max((count for _, count in bins), default=1)
    marks = []
    for vertices, count in bins:
        polygon = [frame.point(*p) for p in vertices]
        surface.polygon_rings([polygon], ramp(VIRIDIS, count / maximum), "white", 0.5)
        marks.append(polygon)
    if rows:
        continuous_legend(surface, width, height, labels.get("count", "计数"), maximum)
    return frame_scene(surface, frame) | {"marks": {"0.polygon": marks}}


def continuous_legend(surface, width, height, title, maximum, header_height=0):
    left = width - 16 - max(42, surface.measure(title))
    x = left + 20.6
    y = (height - 200 + header_height) / 2 + 13.35
    text_at(surface, title, left, floor(y - 48.2) + 12.8, 12, "#21252c")
    gradient = surface.ctx.createLinearGradient(x, y, x, y + 200)
    for i, color in enumerate(VIRIDIS):
        gradient.addColorStop(i / (len(VIRIDIS) - 1), color)
    # The native track is clipped to the rail, including its fractional edges.
    rail = (x - 4, y, x + 4, y + 200)
    surface.rect(rail, "#f1f3f4")
    surface.ctx.save()
    surface.ctx.beginPath()
    surface.ctx.rect(x - 4, y, 8, 200)
    surface.ctx.clip()
    surface.rect(rail, gradient)
    surface.ctx.restore()
    for pos, value, color in [(y, 0, VIRIDIS[0]), (y + 200, maximum, VIRIDIS[-1])]:
        slider_thumb(surface, x, pos, color)
        text_at(surface, str(value), x + 11, pos + 5, 12, "#606773")
