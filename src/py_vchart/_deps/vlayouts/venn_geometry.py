"""Areas and boundary arcs of intersections of disks."""

from dataclasses import dataclass
from itertools import combinations
from math import acos, atan2, hypot, pi, sin, sqrt, tau


@dataclass(frozen=True)
class Circle:
    key: str
    x: float
    y: float
    r: float


@dataclass(frozen=True)
class Arc:
    circle: Circle
    start: tuple
    end: tuple
    sweep: float


def segment_area(r, width):
    width = min(2 * r, max(0, width))
    return r * r * acos(1 - width / r) - (r - width) * sqrt(width * (2 * r - width))


def overlap(r, s, distance):
    if distance >= r + s:
        return 0
    if distance <= abs(r - s):
        return pi * min(r, s) * min(r, s)
    return segment_area(r, r - (distance * distance - s * s + r * r) / (2 * distance)) + segment_area(
        s, s - (distance * distance - r * r + s * s) / (2 * distance)
    )


def center_distance(r, s, area):
    if area == 0:
        return r + s
    if area + 1e-10 >= pi * min(r, s) ** 2:
        return abs(r - s)
    low, step = 0, r + s
    while step > 1e-10:
        step /= 2
        mid = low + step
        if overlap(r, s, mid) >= area:
            low = mid
    return mid


def crossings(a, b):
    dx, dy = b.x - a.x, b.y - a.y
    distance = hypot(dx, dy)
    if not abs(a.r - b.r) < distance < a.r + b.r:
        return []
    along = (a.r * a.r - b.r * b.r + distance * distance) / (2 * distance)
    scale = sqrt(max(0, a.r * a.r - along * along)) / distance
    x, y = a.x + along * dx / distance, a.y + along * dy / distance
    return [(x - dy * scale, y + dx * scale), (x + dy * scale, y - dx * scale)]


def boundary(circles):
    vertices = []
    for a, b in combinations(circles, 2):
        for x, y in crossings(a, b):
            if all(hypot(x - c.x, y - c.y) <= c.r + 1e-10 for c in circles):
                vertices.append((x, y, {a, b}))
    if len(vertices) < 2:
        c = min(circles, key=lambda c: c.r)
        if all(hypot(c.x - p.x, c.y - p.y) + c.r <= p.r + 1e-10 for p in circles):
            return [Arc(c, (c.x, c.y + c.r), (c.x - 1e-10, c.y + c.r), tau)]
        return []
    cx = sum(v[0] for v in vertices) / len(vertices)
    cy = sum(v[1] for v in vertices) / len(vertices)
    vertices.sort(key=lambda v: atan2(v[1] - cy, v[0] - cx), reverse=True)
    arcs = []
    for i, (x, y, parents) in enumerate(vertices):
        u, v, other = vertices[(i + 1) % len(vertices)]
        if hypot(x - u, y - v) < 1e-12:
            continue
        candidates = []
        for c in circles:
            if c not in parents or c not in other:
                continue
            sweep = (atan2(y - c.y, x - c.x) - atan2(v - c.y, u - c.x)) % tau
            candidates.append((c.r * sin(sweep / 4) ** 2, Arc(c, (x, y), (u, v), sweep)))
        if candidates:
            arcs.append(min(candidates, key=lambda choice: choice[0])[1])
    return arcs


def intersection_area(circles):
    arcs = boundary(circles)
    if len(arcs) == 1:
        return pi * arcs[0].circle.r ** 2
    # Signed chord polygon plus the circular segment at each edge.
    return sum(
        (a.end[0] * a.start[1] - a.start[0] * a.end[1] + a.circle.r**2 * (a.sweep - sin(a.sweep))) / 2
        for a in arcs
    )
