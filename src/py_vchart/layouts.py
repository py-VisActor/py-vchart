"""Pure geometry adapters for embedding VChart in another native painter.

These functions run the same scales/series/layout functions as the chart
renderers. They return ordinary Python values and never allocate a Canvas.
The caller owns presentation, fonts, legends, accessibility and export.
"""
from math import hypot, isfinite, pi, tau


class _GeometrySurface:
    """Ink sink for existing series functions; this API returns geometry only."""
    def __init__(self):
        self.labels = []

    def rect(self, *args, **kwargs):
        pass

    def sector(self, *args, **kwargs):
        pass

    def circle(self, *args, **kwargs):
        pass

    def polyline(self, *args, **kwargs):
        pass

    def line(self, *args, **kwargs):
        pass


def _positive(value, name):
    if type(value) not in (float, int) or not isfinite(value) or value <= 0:
        raise ValueError(name + ' must be positive and finite')
    return value


def pie(values, radius=1, inner_radius=0):
    """Return ``(start, end, inner, outer)`` arcs in Canvas radians."""
    from .chart.polar import render_pie
    radius = _positive(radius, 'radius')
    spec = {'type': 'pie', 'data': {'values': [{'k': i, 'v': v} for i, v in enumerate(values)]},
            'categoryField': 'k', 'valueField': 'v', 'padding': 0,
            'outerRadius': 1, 'innerRadius': inner_radius}
    scene = render_pie(spec, _GeometrySurface(), radius * 2, radius * 2)
    return tuple((a[4], a[5], a[2], a[3]) for a in scene['marks']['pie'])


def scatter(points, width, height, x_domain=(0, 1), y_domain=(0, 1)):
    """Numeric scatter point projection through VChart's actual frame."""
    from .chart.scatter import render_scatter
    spec = {'type': 'scatter', 'data': {'values': [{'x': x, 'y': y} for x, y in points]},
            'xField': 'x', 'yField': 'y', 'padding': 0,
            'axes': [{'orient': 'bottom', 'type': 'linear', 'visible': False,
                      'min': x_domain[0], 'max': x_domain[1]},
                     {'orient': 'left', 'type': 'linear', 'visible': False,
                      'min': y_domain[0], 'max': y_domain[1]}]}
    return tuple(tuple(p) for p in render_scatter(spec, _GeometrySurface(),
                 _positive(width, 'width'), _positive(height, 'height'))['points'])


def position(kind, domain, extent, value, *, reverse=False):
    """Use the same native band centers/linear projection for host axes."""
    from ._deps.vscale import bands, linear
    start, end = extent
    if kind == 'band':
        offset, breadth = bands(list(domain), end - start)[value]
        return start + offset + breadth / 2
    lo, hi = domain
    if lo == hi:
        lo, hi = lo - .5, hi + .5
    return linear(value, (lo, hi), (end, start) if reverse else (start, end))


def cartesian(kind, rows, width, height, x_domain, y_domain, *, x_kind='band', horizontal=False, category_padding=0):
    """Use VChart bar/line series with explicit embedding domains.

    Returns point segments and rectangle bounds local to the supplied plot.
    Numeric bar intervals are centered on the continuous frame coordinates;
    their breadth uses the closest projected spacing, preserving x distances.
    """
    from .chart.cartesian import Axis, prepare_frame
    from .chart.bar import draw_bars
    from .chart.line import draw_line
    if kind not in ('line', 'bar'):
        raise ValueError('cartesian layout requires line or bar')
    from ._deps.vscale import bands
    cs, vs = ('left', 'bottom') if horizontal else ('bottom', 'left')
    def nondegenerate(domain):
        return (domain[0] - .5, domain[1] + .5) if domain[0] == domain[1] else domain
    xd = nondegenerate(x_domain) if x_kind == 'linear' else x_domain
    yd = nondegenerate(y_domain)
    axes = {cs: Axis.make(cs, x_kind, list(xd), {'visible': False,
                       **({'min': xd[0], 'max': xd[1]} if x_kind == 'linear' else {})}, 'embedding.axes'),
            vs: Axis.make(vs, 'linear', [y for _, y in rows if y is not None],
                          {'visible': False, 'min': yd[0], 'max': yd[1]}, 'embedding.axes')}
    surface = _GeometrySurface()
    spec = {'type': kind, 'padding': 0, 'direction': 'horizontal' if horizontal else 'vertical',
            'point': {'visible': False}}
    iw = width if horizontal else width - 2 * category_padding
    ih = height - 2 * category_padding if horizontal else height
    frame = prepare_frame(spec, surface, _positive(iw, 'width'), _positive(ih, 'height'), axes, horizontal)
    if kind == 'bar' and x_kind == 'linear':
        keys = list(dict.fromkeys(x for x, _ in rows))
        centers = {x: frame.coordinate(cs, x) for x in keys}
        ordered = sorted(set(centers.values()))
        distance = min((b - a for a, b in zip(ordered, ordered[1:])), default=ih if horizontal else iw)
        breadth = distance * .9
        frame.band_positions[cs] = {x: (center - breadth / 2, breadth) for x, center in centers.items()}
    data = draw_line(spec, surface, frame, rows) if kind == 'line' else draw_bars(spec, surface, frame, rows)
    dx, dy = (0, category_padding) if horizontal else (category_padding, 0)
    if 'segments' in data:
        data['segments'] = [[(x + dx, y + dy) for x, y in segment] for segment in data['segments']]
    if 'bars' in data:
        data['bars'] = [(a + dx, b + dy, c + dx, d + dy) for a, b, c, d in data['bars']]
    return data


def radar(values, minimum, maximum, *, center=(0, 0), radius=1):
    """Project a radar curve using the native polar frame and linear scale."""
    from .chart.polar import PolarFrame
    from ._deps.vscale import linear
    radius = _positive(radius, 'radius')
    if not isfinite(minimum) or not isfinite(maximum) or maximum <= minimum:
        raise ValueError('Radar maximum must exceed minimum')
    spec = {'type': 'radar', 'data': {'values': [{'v': v} for v in values]}, 'valueField': 'v', 'padding': 0}
    frame = PolarFrame(spec, _GeometrySurface(), radius * 2, radius * 2, ())
    result = []
    for i, value in enumerate(values):
        angle = -pi / 2 + tau * i / len(values)
        x, y = frame.point(angle, linear(min(max(value, minimum), maximum), (minimum, maximum), (0, radius)))
        result.append((x - radius + center[0], y - radius + center[1]))
    return tuple(result)


def sankey(node_ids, links, width, height, *, node_width=10, node_gap=12, alignment='justify'):
    """Return immutable node/edge records from VChart's Sankey algorithm."""
    from ._deps.vlayouts.sankey import Node, Link, sankey_layout
    from .chart.plot import nonnegative
    nodes = {name: Node(name, name, 0) for name in node_ids}
    edges = [Link(nodes[a], nodes[b], nonnegative(value, 'Sankey link')) for a, b, value in links]
    real_width = sankey_layout(list(nodes.values()), _positive(width, 'width'), _positive(height, 'height'),
                               node_width, node_gap, 0, alignment, 'middle')
    node_data = tuple({'id': n.key, 'x0': n.x, 'y0': n.y, 'x1': n.x + real_width,
                       'y1': n.y + n.height, 'value': n.value, 'layer': n.depth} for n in nodes.values())
    edge_data = tuple({'index': i, 'source': e.source.key, 'target': e.target.key,
                       'width': e.thickness, 'y0': e.start, 'y1': e.end} for i, e in enumerate(edges))
    return node_data, edge_data


def treemap(rows, width, height, *, key='id', value='value', padding=10, header=25):
    """Recursive section/leaf boxes using the native binary tile algorithm.

    Unlike the chart scene's root-color leaf groups, embedding output retains
    every node identity so a host can attach section labels and clipped text.
    """
    from ._deps.vlayouts.hierarchy import hierarchy, binary_tiles, inset
    roots = hierarchy(rows, key, value)
    result = []
    def visit(nodes, box, depth, parent):
        total = sum(n.weight for n in nodes)
        for node, bounds in binary_tiles(nodes, total, box):
            result.append({'id': node.key, 'box': tuple(bounds), 'depth': depth,
                           'parent': parent, 'section': bool(node.children), 'value': node.weight})
            if node.children:
                inner = inset(bounds, padding)
                inner[1] = min(inner[3], inner[1] + header)
                visit(node.children, inner, depth + 1, node.key)
    visit(roots, (0, 0, _positive(width, 'width'), _positive(height, 'height')), 0, None)
    return tuple(result)


def venn(areas, width, height, *, padding=15):
    """Circle/region geometry from the native Venn provider, up to three sets."""
    from .chart.venn import read_areas
    from ._deps.vlayouts.venn import layout, minimize
    from ._deps.vlayouts.venn_geometry import boundary
    data = [{'sets': list(sets), 'size': size} for sets, size in areas]
    _, sizes, targets = read_areas({'data': {'values': data}})
    circles = layout(sizes, targets, (padding, padding, _positive(width, 'width') - 2 * padding,
                                     _positive(height, 'height') - 2 * padding), False)
    regions = []
    for keys, _ in areas:
        interior = [circles[k] for k in keys]
        exterior = [c for k, c in circles.items() if k not in keys]
        arcs = boundary(interior)
        candidates = [(c.x, c.y) for c in interior]
        if arcs:
            candidates.append((sum(a.start[0] for a in arcs) / len(arcs), sum(a.start[1] for a in arcs) / len(arcs)))
        def margin(p):
            distances = [c.r - hypot(p[0] - c.x, p[1] - c.y) for c in interior]
            distances += [hypot(p[0] - c.x, p[1] - c.y) - c.r for c in exterior]
            return min(distances, default=0)
        point = max(candidates, key=margin) if candidates else (0, 0)
        if candidates:
            optimized = minimize(lambda p: -margin(p), list(point))
            if margin(optimized) > margin(point):
                point = optimized
        path = ''
        if len(arcs) == 1 and arcs[0].sweep >= tau - 1e-8:
            c = arcs[0].circle
            path = f'M{c.x-c.r:g},{c.y:g}A{c.r:g},{c.r:g} 0 1,0 {c.x+c.r:g},{c.y:g}A{c.r:g},{c.r:g} 0 1,0 {c.x-c.r:g},{c.y:g}Z'
        elif arcs:
            path = f'M{arcs[0].start[0]:g},{arcs[0].start[1]:g}'
            for arc in arcs:
                path += f'A{arc.circle.r:g},{arc.circle.r:g} 0 {int(arc.sweep > pi)},1 {arc.end[0]:g},{arc.end[1]:g}'
            path += 'Z'
        regions.append({'sets': tuple(keys), 'path': path, 'center': tuple(point),
                        'circles': tuple((c.x, c.y, c.r) for c in interior)})
    return {'circles': tuple((k, c.x, c.y, c.r) for k, c in circles.items()), 'regions': tuple(regions)}
