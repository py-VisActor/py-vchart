"""Static node-link Sankey chart."""

from math import isfinite

from .._deps.vdataset import inline_values
from .._deps.vlayouts.sankey import Link, Node, sankey_layout
from .cartesian import DYNAMIC, check_keys
from .layout_helpers import palette_for
from .plot import hidden_label, nonnegative, plot_region


def graph_data(data):
    rows = inline_values(data, "sankey.data")
    if len(rows) == 2:
        graph = {view.get("id"): inline_values(view, "sankey.data") for view in rows if isinstance(view, dict)}
        if set(graph) != {"nodes", "links"}:
            raise ValueError("sankey.data requires nodes and links views")
        return graph
    if len(rows) != 1 or not isinstance(rows[0], dict):
        raise ValueError("sankey.data requires one node-link graph")
    return rows[0]


def parse_graph(spec):
    graph = graph_data(spec.get("data"))
    if not all(isinstance(graph.get(key), list) for key in ("nodes", "links")):
        raise ValueError("sankey requires explicit nodes and links arrays")
    by_key = {}
    for i, row in enumerate(graph["nodes"]):
        if not isinstance(row, dict):
            raise ValueError("sankey nodes must be records")
        key = row.get(spec["nodeKey"]) if "nodeKey" in spec else i
        category = row.get(spec.get("categoryField", "name"))
        if type(key) not in (str, int) or key in by_key or type(category) not in (str, int, float):
            raise ValueError("sankey requires scalar categories and unique node keys")
        by_key[key] = Node(key, category, nonnegative(row.get("value", 0), "sankey node value"))
    links = []
    for row in graph["links"]:
        if not isinstance(row, dict):
            raise ValueError("sankey links must be records")
        source = row.get(spec.get("sourceField", "source"))
        target = row.get(spec.get("targetField", "target"))
        if type(source) not in (str, int) or type(target) not in (str, int) or source not in by_key or target not in by_key:
            raise ValueError("sankey link endpoints must reference declared nodes")
        value = nonnegative(row.get(spec.get("valueField", "value")), "sankey link value")
        links.append(Link(by_key[source], by_key[target], value))
    return list(by_key.values()), links


def render_sankey(spec, surface, width, height):
    options = {"type", "data", "width", "height", "background", "padding", "label", "categoryField",
               "sourceField", "targetField", "valueField", "nodeKey", "direction", "nodeGap", "nodeWidth",
               "minNodeHeight", "dropIsolatedNode", "nodeAlign", "crossNodeAlign"}
    check_keys(spec, options | DYNAMIC, "sankey")
    hidden_label(spec)
    plot = plot_region(spec, surface, width, height)
    nodes, links = parse_graph(spec)
    keys = dict.fromkeys(n.category for n in nodes)
    palette = palette_for(len(keys))
    colors = {key: palette[i % len(palette)] for i, key in enumerate(keys)}
    names = [n.category for n in nodes]
    if spec.get("dropIsolatedNode", False):
        nodes = [n for n in nodes if n.incoming or n.outgoing]
    align, cross = spec.get("nodeAlign", "justify"), spec.get("crossNodeAlign", "middle")
    direction = spec.get("direction", "horizontal")
    if align not in {"left", "right", "start", "end", "center", "justify"} or cross not in {"start", "middle", "end"}:
        raise ValueError("Unsupported sankey node alignment")
    if direction not in ("horizontal", "vertical"):
        raise ValueError("Invalid sankey.direction")
    vertical = direction == "vertical"
    length, breadth = plot[2:][::-1] if vertical else plot[2:]
    node_width = spec.get("nodeWidth", 10)
    if isinstance(node_width, str) and node_width.endswith("%"):
        if not 0 < float(node_width[:-1]) <= 100:
            raise ValueError("sankey.nodeWidth percentage must be in (0, 100]")
    else:
        nonnegative(node_width, "sankey.nodeWidth")
    node_width = sankey_layout(nodes, length, breadth, node_width,
                               nonnegative(spec.get("nodeGap", 8), "sankey.nodeGap"),
                               nonnegative(spec.get("minNodeHeight", 4), "sankey.minNodeHeight"), align, cross)

    def point(x, y):
        return [plot[0]+y, plot[1]+x] if vertical else [plot[0]+x, plot[1]+y]

    marks = {"node": [], "link": []}
    for edge in links:
        x0, x1 = edge.source.x+node_width, edge.target.x
        key = edge.source.key
        if isinstance(key, int):
            key = names[key] if 0 <= key < len(names) else None
        if key not in colors:
            colors[key] = palette[len(colors) % len(palette)]
        band = [*point(x0, edge.start), *point(x1, edge.end), edge.thickness]
        if all(map(isfinite, band)):
            surface.flow_band(x0, edge.start, x1, edge.end, edge.thickness, plot[:2], vertical, colors[key], .15)
        marks["link"].append([v if isfinite(v) else None for v in band])
    for node in nodes:
        box = point(node.x, node.y) + point(node.x+node_width, node.y+node.height)
        if all(map(isfinite, box)):
            surface.rect(box, colors[node.category])
        else:
            # A nonfinite edge makes both bounds on its axis undefined.
            for i in (0, 1):
                if not (isfinite(box[i]) and isfinite(box[i+2])):
                    box[i] = box[i+2] = None
        marks["node"].append(box)
    return dict(plot=plot, labels=[], axes=[], marks=marks)
