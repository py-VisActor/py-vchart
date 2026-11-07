"""Per-feature collision layout for the static SHAP summary plot."""

from collections import defaultdict
from math import sqrt, pi
from .cartesian import Axis, CartesianFrame, check_keys, frame_scene, AXIS
from .statplots import axis_for
from .stat_matrix import ramp, text_at
from .stat_panels import continuous_legend
from .._deps.vscale import bands
from .._deps.vscale.stat_colors import VIRIDIS


def swarm_offsets(points, half_width):
    active = []
    result = {}
    for x, key, index in sorted(points):
        active = [(px, off) for px, off in active if x - px <= 7]
        candidates = [0]
        for px, off in active:
            distance = sqrt(7.5**2 - (x - px) ** 2)
            candidates.extend((off + distance, off - distance))
        for off in sorted(candidates, key=lambda v: (abs(v), v)):
            if abs(off) + 3.5 <= half_width and all(
                (off - old) ** 2 + (x - px) ** 2 >= 7.49**2 for px, old in active
            ):
                result[index] = off
                active.append((x, off))
                break
        else:
            result[index] = 0
    return result


def render_swarm(spec, surface, width, height):
    check_keys(
        spec,
        {"type", "data", "featureOrder", "fieldLabels", "width", "height"},
        "shapBeeswarmPlot",
    )
    rows = spec["data"]
    groups = defaultdict(list)
    for i, row in enumerate(rows):
        groups[row["feature"]].append(i)
    cats = spec.get("featureOrder", list(groups))
    if not rows or set(cats) != set(groups):
        raise ValueError("Expected observations for each feature")
    x = axis_for("bottom", [r["shapValue"] for r in rows], False, (), False)
    y = Axis.make("left", "band", cats, {}, "shapBeeswarmPlot")
    left = round(60 + max(surface.measure(k) for k in cats))
    top = 57
    w, h = width - left - 112, height - top - 60
    frame = CartesianFrame(
        (left, top, w, h), True, {"left": y, "bottom": x}, {"left": bands(cats, h)}
    )
    surface.rect((0, 0, width, height), "white")
    text_at(
        surface,
        "颜色表示特征内的相对值；灰色表示缺失或常量，空心警告色表示拥挤重叠。",
        16,
        35,
        14,
        "#89909d",
    )
    surface.line(left, top, left, top + h, AXIS)
    for cat in cats:
        cy = frame.coordinate("left", cat)
        surface.line(left - 4, cy, left, cy, AXIS)
        surface.label(cat, left - 16, cy, "right", "middle")
    for t in x.ticks:
        align = (
            "left" if t == x.domain[0] else "right" if t == x.domain[1] else "center"
        )
        surface.label(
            x.label(t),
            frame.coordinate("bottom", t),
            top + h + 8,
            align,
            "top",
            line_height=12,
        )
    titles = spec.get("fieldLabels", {})
    text_at(
        surface,
        titles.get("shapValue", "SHAP 值"),
        left + w / 2,
        top + h + 40.8,
        12,
        "#606773",
        "center",
    )
    ctx = surface.ctx
    ctx.save()
    ctx.translate(32, top + h / 2)
    ctx.rotate(-pi / 2)
    text_at(surface, titles.get("feature", "特征"), 0, -3.2, 12, "#606773", "center")
    ctx.restore()
    points = [None] * len(rows)
    for cat, indices in groups.items():
        xs = [
            (frame.coordinate("bottom", rows[i]["shapValue"]), str(rows[i]["id"]), i)
            for i in indices
        ]
        offsets = swarm_offsets(xs, frame.positions[cat][1] * 0.45)
        vals = [
            rows[i]["featureValue"]
            for i in indices
            if rows[i]["featureValue"] is not None
        ]
        lo, hi = (min(vals), max(vals)) if vals else (0, 0)
        for px, _, i in xs:
            py = frame.coordinate("left", cat) + offsets[i]
            points[i] = [px, py]
            v = rows[i]["featureValue"]
            color = (
                "#bcc1cb"
                if v is None
                else "#89909d"
                if lo == hi
                else ramp(VIRIDIS, (v - lo) / (hi - lo))
            )
            surface.circle(px, py, 7, color, "white", 1)
    ctx.save()
    ctx.setLineDash([4, 4])
    px = frame.coordinate("bottom", 0)
    surface.line(px, top, px, top + h, "#606773")
    ctx.restore()
    continuous_legend(surface, width, height, "特征内相对值", 1, 41)
    return frame_scene(surface, frame) | {"marks": {"0.point": points}}
