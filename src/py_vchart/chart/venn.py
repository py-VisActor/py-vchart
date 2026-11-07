"""Static singleton circles and their filled intersection paths."""

from math import pi, tau

from .._deps.vdataset import inline_values
from .._deps.vlayouts.venn import layout
from .._deps.vlayouts.venn_geometry import Circle, boundary
from .cartesian import DYNAMIC, check_keys
from .layout_helpers import palette_for
from .plot import hidden_label, nonnegative, plot_region
from .point import mark_options


def read_areas(spec):
    rows = inline_values(spec.get("data"), "venn.data")
    areas, sizes, targets = [], {}, {}
    for row in rows:
        category = spec.get("categoryField", "sets")
        if not isinstance(row, dict) or category not in row:
            raise ValueError("venn requires a set field on each record")
        sets = row[category]
        keys = sets if isinstance(sets, list) else [sets]
        if not all(isinstance(k, str) for k in keys) or len(keys) != len(set(keys)):
            raise ValueError("venn requires distinct string set names")
        key = frozenset(keys)
        if key in targets:
            raise ValueError("venn requires one area per combination")
        value = nonnegative(row.get(spec.get("valueField", "size")), "venn area")
        targets[key] = value
        if len(keys) == 1:
            if not value:
                raise ValueError("venn singleton areas must be positive")
            sizes[keys[0]] = value
        group = row.get(spec["seriesField"]) if "seriesField" in spec else len(areas)
        if isinstance(group, list):
            group = tuple(group)
        areas.append((keys, group))
    if len(sizes) > 3 or any(not key.issubset(sizes) for key in targets):
        raise ValueError("venn requires up to three declared singleton sets")
    return areas, sizes, targets


def render_venn(spec, surface, width, height):
    check_keys(
        spec,
        DYNAMIC
        | {
            "type",
            "data",
            "width",
            "height",
            "padding",
            "background",
            "categoryField",
            "valueField",
            "seriesField",
            "label",
            "overlapLabel",
            "circle",
            "overlap",
        },
        "venn",
    )
    hidden_label(spec, default=True)
    if spec.get("overlapLabel") != {"visible": False}:
        raise ValueError("venn.overlapLabel currently requires visible=false")
    plot = plot_region(spec, surface, width, height)
    px, py, w, h = plot
    areas, sizes, targets = read_areas(spec)
    circles = layout(sizes, targets, plot, frozenset() in targets)
    outer = Circle("", px + w / 2, py + h / 2, min(w, h) / 2)
    groups = dict.fromkeys(group for _, group in areas)
    palette = palette_for(len(groups))
    colors = {group: palette[i % len(palette)] for i, group in enumerate(groups)}
    marks = {"circle": [], "overlap": []}
    for name in marks:
        visible, style = mark_options(spec, name, {"fill", "opacity"})
        alpha = nonnegative(style.get("opacity", 0.8), f"venn.{name}.opacity")
        if alpha > 1:
            raise ValueError("venn opacity must be between zero and one")
        if not visible:
            continue
        paths = []
        for keys, group in areas:
            color = style.get("fill", colors[group])
            if name == "circle" and len(keys) < 2:
                c = circles[keys[0]] if keys else outer
                marks[name].append([c.x, c.y, 0, c.r, 0, tau])
                surface.circle(c.x, c.y, 2 * c.r, color, None, 0, alpha)
            elif name == "overlap" and len(keys) >= 2:
                arcs = boundary([circles[k] for k in keys])
                marks[name].append(
                    sorted([[a.circle.key, *a.start, *a.end, a.circle.r, int(a.sweep > pi)] for a in arcs])
                )
                if arcs:
                    paths.append((len(keys), arcs, color))
        for _, arcs, color in sorted(paths, key=lambda path: path[0]):
            surface.fill_arc_path(arcs, color, alpha)
    return dict(plot=plot, axes=[], labels=[], marks=marks)
