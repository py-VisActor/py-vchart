"""Static hierarchy marks with root-category colors."""

from math import radians, tau

from .._deps.vdataset import inline_values
from .._deps.vlayouts.circle_packing import packed_circles
from .._deps.vlayouts.hierarchy import hierarchy, sunburst_arcs, treemap_tiles
from .cartesian import DYNAMIC, check_keys
from .layout_helpers import palette_for
from .plot import hidden_label, nonnegative, plot_region


def prepare(spec, surface, width, height, options):
    base = {"type", "data", "categoryField", "valueField", "width", "height", "background", "padding", "label"}
    check_keys(spec, base | options | DYNAMIC, spec["type"])
    hidden_label(spec, default=spec["type"] in ("sunburst", "circlePacking"))
    plot = plot_region(spec, surface, width, height)
    rows = inline_values(spec.get("data"), spec["type"] + ".data")
    nodes = hierarchy(rows, spec.get("categoryField", "name"), spec.get("valueField", "value"))
    if spec["type"] == "circlePacking":
        nodes.sort(key=lambda node: -node.weight)
    keys = dict.fromkeys(node.key for node in nodes)
    palette = palette_for(len(keys))
    colors = {key: palette[i % len(palette)] for i, key in enumerate(keys)}
    return nodes, colors, dict(plot=plot, axes=[], labels=[], marks={})


def padding_by_depth(padding, path):
    if isinstance(padding, list):
        levels = [nonnegative(p, path) for p in padding]
        return lambda depth: levels[depth] if depth < len(levels) else 0
    uniform = nonnegative(padding, path)
    return lambda depth: uniform


def render_treemap(spec, surface, width, height):
    nodes, colors, scene = prepare(spec, surface, width, height, {"gapWidth", "nodePadding", "splitType"})
    if spec.get("splitType", "binary") != "binary":
        raise ValueError("treemap.splitType currently requires binary")
    gap = nonnegative(spec.get("gapWidth", 1), "treemap.gapWidth")
    at_depth = padding_by_depth(spec.get("nodePadding", [5]), "treemap.nodePadding")
    x, y, w, h = scene["plot"]
    leaves = []
    for key, box in treemap_tiles(nodes, (x, y, x+w, y+h), gap, at_depth):
        surface.rect(box, colors[key])
        leaves.append(box)
    scene["marks"].update(nonLeaf=[], leaf=leaves)
    return scene


def render_sunburst(spec, surface, width, height):
    nodes, colors, scene = prepare(spec, surface, width, height, {"innerRadius", "outerRadius", "startAngle", "endAngle"})
    inner = nonnegative(spec.get("innerRadius", 0), "sunburst.innerRadius")
    outer = nonnegative(spec.get("outerRadius", 1), "sunburst.outerRadius")
    if not inner <= outer <= 1:
        raise ValueError("Invalid sunburst radii")
    radius = min(scene["plot"][2:])/2
    angles = [radians(spec.get("startAngle", -90)), radians(spec.get("endAngle", 270))]
    marks = []
    for key, arc in sunburst_arcs(nodes, angles, [inner*radius, outer*radius]):
        mark = [width/2, height/2, *arc]
        surface.sector(*mark, colors[key], stroke="white")
        marks.append(mark)
    scene["marks"]["sunburst"] = marks
    return scene


def render_circle_packing(spec, surface, width, height):
    nodes, colors, scene = prepare(spec, surface, width, height, {"layoutPadding"})
    padding = padding_by_depth(spec.get("layoutPadding", 5), "circlePacking.layoutPadding")
    marks = []
    for key, x, y, radius in packed_circles(nodes, scene["plot"], padding):
        mark = [x, y, 0, radius, 0, tau]
        if radius is not None:
            surface.sector(*mark, colors[key], stroke="white")
        marks.append(mark)
    scene["marks"]["circlePacking"] = marks
    return scene
