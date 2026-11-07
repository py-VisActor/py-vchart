"""Fit and normalize one-, two- and three-set area diagrams."""

from itertools import combinations
from math import hypot, pi, sqrt

from .venn_geometry import Circle, center_distance, crossings, intersection_area, overlap


def minimize(loss, initial):
    """Downhill simplex using the Venn layout's coordinate and loss tolerances."""

    def evaluate(point):
        return loss(point), point

    def combine(a, b, weight):
        return [(1 - weight) * x + weight * y for x, y in zip(a, b)]

    simplex = [evaluate(initial)]
    for i, value in enumerate(initial):
        point = initial.copy()
        point[i] = 1.05 * value if value else 0.001
        simplex.append(evaluate(point))
    for _ in range(500):
        simplex.sort(key=lambda item: item[0])
        best_loss, best = simplex[0]
        worst_loss, worst = simplex[-1]
        if worst_loss - best_loss < 1e-6 and max(abs(x - y) for x, y in zip(best, simplex[1][1])) < 1e-5:
            break
        center = [sum(col) / len(initial) for col in zip(*(p for _, p in simplex[:-1]))]
        reflected = evaluate(combine(center, worst, -1))
        if reflected[0] < best_loss:
            expanded = evaluate(combine(center, worst, -2))
            simplex[-1] = expanded if expanded[0] < reflected[0] else reflected
        elif reflected[0] < simplex[-2][0]:
            simplex[-1] = reflected
        else:
            inside = reflected[0] > worst_loss
            contracted = evaluate(combine(center, worst, 0.5 if inside else -0.5))
            if contracted[0] < (worst_loss if inside else reflected[0]):
                simplex[-1] = contracted
            else:
                simplex[1:] = [evaluate(combine(best, p, 0.5)) for _, p in simplex[1:]]
    return min(simplex, key=lambda item: item[0])[1]


def fit(sizes, targets):
    keys = list(sizes)
    radii = {k: sqrt(sizes[k] / pi) for k in keys}

    def desired(a, b):
        return targets.get(frozenset((a, b)), 0)

    def priority(key):
        return sum(
            desired(key, b) for b in keys if b != key and desired(key, b) + 1e-10 < min(sizes[key], sizes[b])
        )

    placed = {}
    for key in sorted(keys, key=priority, reverse=True):
        r = radii[key]
        neighbors = sorted(placed, key=lambda k: -desired(k, key))
        rings = [
            Circle(k, placed[k].x, placed[k].y, center_distance(r, radii[k], desired(k, key)))
            for k in neighbors
        ]
        candidates = []
        for i, ring in enumerate(rings):
            x, y, d = ring.x, ring.y, ring.r
            candidates.extend([(x + d, y), (x - d, y), (x, y + d), (x, y - d)])
            for other in rings[i + 1 :]:
                candidates.extend(crossings(ring, other))

        def cost(point):
            x, y = point
            return sum(
                (overlap(r, c.r, hypot(c.x - x, c.y - y)) - desired(k, key)) ** 2 for k, c in placed.items()
            )

        x, y = min(candidates, key=cost) if candidates else (0, 0)
        placed[key] = Circle(key, x, y, r)

    def unpack(points):
        return {k: Circle(k, points[2 * i], points[2 * i + 1], radii[k]) for i, k in enumerate(keys)}

    def loss(points):
        circles = unpack(points)
        total = 0
        for a, b in combinations(circles.values(), 2):
            area = overlap(a.r, b.r, hypot(a.x - b.x, a.y - b.y))
            total += (area - desired(a.key, b.key)) ** 2
        if len(keys) == 3 and frozenset(keys) in targets:
            total += (intersection_area(list(circles.values())) - targets[frozenset(keys)]) ** 2
        return total

    initial = [v for k in keys for v in (placed[k].x, placed[k].y)]
    return list(unpack(minimize(loss, initial) if loss(initial) > 0 else initial).values())


def orient(cluster):
    ordered = sorted(cluster, key=lambda c: -c.r)
    a = ordered[0]
    dx, dy = (1, 0)
    if len(ordered) > 1:
        b = ordered[1]
        distance = hypot(b.x - a.x, b.y - a.y)
        if distance:
            dx, dy = (b.x - a.x) / distance, (b.y - a.y) / distance
    result = [
        Circle(c.key, (c.x - a.x) * dx + (c.y - a.y) * dy, (c.y - a.y) * dx - (c.x - a.x) * dy, c.r)
        for c in ordered
    ]
    if len(result) == 2 and result[1].x < a.r - result[1].r:
        b = result[1]
        result[1] = Circle(b.key, a.r - b.r - 1e-10, 0, b.r)
    if len(result) == 3 and result[2].y > 0:
        result = [Circle(c.key, c.x, -c.y, c.r) for c in result]
    return result


def bounds(cluster):
    return (
        min(c.x - c.r for c in cluster),
        min(c.y - c.r for c in cluster),
        max(c.x + c.r for c in cluster),
        max(c.y + c.r for c in cluster),
    )


def layout(sizes, targets, plot, universe):
    if not sizes:
        return {}
    order = {key: index for index, key in enumerate(sizes)}
    clusters = []
    for c in fit(sizes, targets):
        group = [c]
        separate = []
        for cluster in clusters:
            if any(hypot(c.x - p.x, c.y - p.y) + 1e-10 < c.r + p.r for p in cluster):
                group.extend(cluster)
            else:
                separate.append(cluster)
        # Preserve input order for ties when orienting equal-area circles.
        clusters = separate + [sorted(group, key=lambda p: order[p.key])]
    blocks = []
    for cluster in clusters:
        group = orient(cluster)
        x, y, u, v = bounds(group)
        blocks.append(((u - x) * (v - y), group))
    blocks.sort(key=lambda item: -item[0])
    circles = blocks[0][1].copy()
    x, y, u, v = bounds(circles)
    gap = (u - x) / 50
    for i, (_, group) in enumerate(blocks[1:]):
        left, t, r, b = bounds(group)
        dx = u + gap - left if i == 0 else u - r + min(0, (r - left - u + x) / 2)
        dy = v - b + min(0, (b - t - v + y) / 2) if i == 0 else v + gap - t
        circles.extend(Circle(c.key, c.x + dx, c.y + dy, c.r) for c in group)
    x, y, u, v = bounds(circles)
    px, py, w, h = plot
    cx, cy = (x + u) / 2, (y + v) / 2
    if universe:
        scale = min(w, h) / 2 / max(hypot(c.x - cx, c.y - cy) + c.r for c in circles)
    else:
        scale = min(w / (u - x), h / (v - y))
    return {
        c.key: Circle(c.key, px + w / 2 + (c.x - cx) * scale, py + h / 2 + (c.y - cy) * scale, c.r * scale)
        for c in circles
    }
