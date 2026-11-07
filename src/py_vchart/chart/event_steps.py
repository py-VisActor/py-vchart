"""Static step-by-step event chart with users in separate lanes."""

from .._deps.vscale import bands
from .._deps.vrender.controls import rounded_rect, control_symbol
from .cartesian import AXIS, GRID, check_keys
from .layout_helpers import palette_for
from .stat_matrix import text_at


def render_event_steps(spec, surface, width, height):
    check_keys(
        spec,
        {
            "type",
            "width",
            "height",
            "mode",
            "eventData",
            "stepMediumMap",
            "userImageMap",
            "patternData",
            "actionData",
            "colors",
            "mediumConnection",
        },
        "sequenceAnalysis",
    )
    if (
        spec.get("mode") != "step"
        or spec.get("mediumConnection")
        or any(spec.get("userImageMap", {}).values())
    ):
        raise ValueError("sequenceAnalysis supports step mode with text lanes")
    events = [(row["user_id"], d) for row in spec["eventData"] for d in row["dots"]]
    users = list(dict.fromkeys(user for user, _ in events))
    steps = list(dict.fromkeys(d["step"] for _, d in events))
    categories = list(dict.fromkeys(d["action_type"] for _, d in events))
    left, top = 72, 46
    w, h = width - left - 30, height - top - 88
    if min(w, h) <= 0 or not steps:
        raise ValueError("sequenceAnalysis requires steps and a positive plot area")
    bottom = top + h
    sx = bands(steps, w / 0.8)
    sy = bands(users, h / 0.8)
    xloc = {k: left + a + b / 2 for k, (a, b) in sx.items()}
    yloc = {k: top + h / 0.8 - (a + b / 2) for k, (a, b) in sy.items()}
    labels = []

    def rich(x, y, align, baseline):
        labels.append(
            dict(text="[object Object]", x=x, y=y, align=align, baseline=baseline)
        )

    surface.rect((0, 0, width, height), "white")
    for y in (top, bottom):
        surface.line(left, y, left + w, y, AXIS)
    for i, k in enumerate(steps):
        x = xloc[k]
        if x <= left + w:
            surface.line(x, top, x, top - 4, AXIS)
            rich(x, top - 12, "center", "bottom")
            m = spec["stepMediumMap"][k]
            prefix, suffix = m["medium_type"] + "... ", f"+{m['count']}"
            u, v = int(surface.measure(prefix)), int(surface.measure(suffix))
            x0 = x - (u + v) / 2
            surface.rect((x0 + u, top - 26, x0 + u + v, top - 12), "#cccccc")
            text_at(surface, prefix, x0, top - 14, 12, "#89909d")
            text_at(surface, suffix, x0 + u, top - 14, 12, "#89909d")
        bx = left + w / 0.8 * (i + 0.5) / len(steps)
        if bx <= left + w:
            surface.line(bx, bottom, bx, bottom + 4, AXIS)
            surface.label(k, bx, bottom + 12, "center", "top")
    ctx = surface.ctx
    for k, cy in yloc.items():
        if top <= cy <= bottom:
            rich(left - 12, cy, "right", "middle")
            ctx.save()
            ctx.setLineDash([3, 3])
            surface.line(left, cy, left + w, cy, GRID)
            ctx.restore()
    points = [[xloc[d["step"]], yloc[user]] for user, d in events]
    nodes = {d["node_name"]: pt for (_, d), pt in zip(events, points)}
    ctx.save()
    ctx.beginPath()
    ctx.rect(left, top, w, h)
    ctx.clip()
    links = []
    for edge in spec.get("patternData", []):
        a, b = nodes[edge["from"]], nodes[edge["to"]]
        surface.polyline([a, b], "#1664ff", 1)
        links.extend([a, b])
    colors = spec.get("colors", palette_for(len(categories)))
    for (_, d), p in zip(events, points):
        surface.circle(
            *p, 10, colors[categories.index(d["action_type"]) % len(colors)], None, 0
        )
    ctx.restore()
    rounded_rect(surface, left + w + 2, top + 2, 6, (h - 4) * 0.8, 3, "rgba(0,0,0,0.3)")
    rounded_rect(surface, left + 2, bottom + 26, (w - 4) * 0.8, 6, 3, "rgba(0,0,0,0.3)")
    x0, x1 = left + 10, left + w - 10
    y = height - 32
    surface.rect((x0, y - 10, x1, y + 10), "#f1f3f4")
    surface.rect((x0, y - 10, x1, y + 10), "rgba(0,64,255,0.1)")
    surface.outline((x0 + 0.5, y - 9.5, x1 - 0.5, y + 9.5), "rgba(0,64,255,0.2)")
    for x in [x0, x1]:
        control_symbol(surface, "zoomHandle", x, y, 24, "white", "#aeb5be", 1.2)
    return dict(
        plot=[left, top, w, h],
        axes=[
            dict(orient="top", domain=steps, range=[0, w]),
            dict(orient="bottom", domain=steps, range=[0, w]),
            dict(orient="left", domain=users, range=[h, 0]),
        ],
        labels=sorted(labels + surface.labels, key=lambda l: (l["x"], l["y"])),
        marks={"0.link": links, "1.dot": points},
    )
