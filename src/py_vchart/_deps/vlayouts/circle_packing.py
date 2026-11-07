"""Front-chain packing of weighted siblings in an enclosing disk."""

from dataclasses import dataclass, field
from itertools import combinations
from math import hypot, sqrt
from random import Random


@dataclass
class Disk:
    radius: float
    x: float = 0
    y: float = 0
    key: object = None
    children: list = field(default_factory=list)


def tangent(left, right, disk):
    """Place disk on the clockwise side of the directed edge left -> right."""
    dx, dy = right.x-left.x, right.y-left.y
    squared = dx*dx + dy*dy
    if not squared:
        disk.x, disk.y = left.x + disk.radius, left.y
        return
    left_sq = (left.radius + disk.radius)**2
    right_sq = (right.radius + disk.radius)**2
    # Start from the smaller tangent distance for numerical stability.
    if left_sq > right_sq:
        along = (squared + right_sq - left_sq)/(2*squared)
        across = sqrt(max(0, right_sq/squared - along*along))
        disk.x = right.x - along*dx - across*dy
        disk.y = right.y - along*dy + across*dx
    else:
        along = (squared + left_sq - right_sq)/(2*squared)
        across = sqrt(max(0, left_sq/squared - along*along))
        disk.x = left.x + along*dx - across*dy
        disk.y = left.y + along*dy + across*dx


def contains(outer, inner):
    return hypot(outer.x-inner.x, outer.y-inner.y) + inner.radius <= outer.radius + 1e-9*max(outer.radius, 1)


def pair_disk(a, b):
    dx, dy = b.x-a.x, b.y-a.y
    distance = hypot(dx, dy)
    if distance <= abs(a.radius-b.radius):
        return max((a, b), key=lambda d: d.radius)
    radius = (distance+a.radius+b.radius)/2
    ratio = (radius-a.radius)/distance
    return Disk(radius, a.x+ratio*dx, a.y+ratio*dy)


def triple_disks(a, b, c):
    # Subtract the first tangency equation from the other two. The center
    # becomes an affine function of the enclosing radius, leaving one quadratic.
    bx, by, cx, cy = b.x-a.x, b.y-a.y, c.x-a.x, c.y-a.y
    determinant = bx*cy-by*cx
    if not determinant:
        return
    def solve(p, q):
        return (cy*p-by*q)/determinant, (bx*q-cx*p)/determinant
    ux, uy = solve((bx*bx+by*by+a.radius**2-b.radius**2)/2,
                   (cx*cx+cy*cy+a.radius**2-c.radius**2)/2)
    vx, vy = solve(b.radius-a.radius, c.radius-a.radius)
    qa = vx*vx+vy*vy-1
    qb = 2*(ux*vx+uy*vy+a.radius)
    qc = ux*ux+uy*uy-a.radius**2
    if abs(qa) < 1e-14:
        radii = [-qc/qb] if qb else []
    else:
        disc = qb*qb-4*qa*qc
        radii = [] if disc < 0 else [(-qb+sign*sqrt(disc))/(2*qa) for sign in (-1, 1)]
    for radius in radii:
        if radius >= max(a.radius, b.radius, c.radius):
            yield Disk(radius, a.x+ux+radius*vx, a.y+uy+radius*vy)


def enclosing_disk(chain):
    # A minimal enclosure is supported by at most three disks. When a disk
    # falls outside, update the support and revisit the already seen disks.
    disks = list(chain)
    Random(0).shuffle(disks)
    support = []
    enclosure = None
    index = 0
    while index < len(disks):
        disk = disks[index]
        if enclosure is not None and contains(enclosure, disk):
            index += 1
            continue
        previous = support + [disk]
        options = [(disk, [disk])]
        for a in support:
            options.append((pair_disk(a, disk), [a, disk]))
        for a, b in combinations(support, 2):
            options.extend((circle, [a, b, disk]) for circle in triple_disks(a, b, disk))
        enclosure, support = min(((circle, basis) for circle, basis in options
                                  if all(contains(circle, p) for p in previous)), key=lambda item: item[0].radius)
        index = 0
    return enclosure


def edge_score(a, b):
    weight = a.radius+b.radius
    if not weight:
        return a.x*a.x+a.y*a.y
    x = (a.x*b.radius+b.x*a.radius)/weight
    y = (a.y*b.radius+b.y*a.radius)/weight
    return x*x+y*y


def pack(disks):
    first = disks[0]
    first.x = first.y = 0
    if len(disks) == 1:
        return first.radius
    second = disks[1]
    first.x, second.x, second.y = -second.radius, first.radius, 0
    if len(disks) == 2:
        return first.radius+second.radius
    tangent(first, second, disks[2])
    chain = disks[:3]
    for disk in disks[3:]:
        while True:
            a, b = chain[:2]
            tangent(b, a, disk)
            ahead, behind = 2, len(chain)-1
            forward, backward = b.radius, a.radius
            while ahead <= behind:
                scan_forward = forward <= backward
                i = ahead if scan_forward else behind
                other = chain[i]
                if hypot(other.x-disk.x, other.y-disk.y) < other.radius+disk.radius-1e-6:
                    chain = [a]+chain[i:] if scan_forward else [other]+chain[1:i]
                    break
                if scan_forward:
                    ahead += 1
                    forward += other.radius
                else:
                    behind -= 1
                    backward += other.radius
            else:
                chain.insert(1, disk)
                candidates = [0, *range(2, len(chain))]
                start = min(candidates, key=lambda j: edge_score(chain[j], chain[(j+1) % len(chain)]))
                chain = chain[start:]+chain[:start]
                break
    enclosure = enclosing_disk(chain)
    for disk in disks:
        disk.x -= enclosure.x
        disk.y -= enclosure.y
    return enclosure.radius


def packed_circles(nodes, plot, padding):
    if not nodes:
        return

    def build(node, key):
        children = [build(n, key) for n in sorted(node.children, key=lambda n: -n.weight)]
        return Disk(sqrt(node.weight), key=key, children=children)

    root = Disk(0, children=[build(n, n.key) for n in sorted(nodes, key=lambda n: -n.weight)])

    def layout(node, level, scale):
        if not node.children:
            return
        gap = padding(level)*scale
        for child in node.children:
            layout(child, level+1, scale)
            child.radius += gap
        node.radius = pack(node.children)+gap
        for child in node.children:
            child.radius -= gap

    x, y, w, h = plot
    size = min(w, h)
    layout(root, 0, 0)
    if not root.radius:
        # VChart retains the marks but has no finite scale for an all-zero tree.
        pending = list(reversed(root.children))
        while pending:
            node = pending.pop()
            yield node.key, None, None, None
            pending.extend(reversed(node.children))
        return
    layout(root, 0, root.radius/size)
    scale = size/(2*root.radius)

    def emit(parent, x, y):
        for child in parent.children:
            cx, cy = x+child.x*scale, y+child.y*scale
            yield child.key, cx, cy, child.radius*scale
            yield from emit(child, cx, cy)

    yield from emit(root, x+w/2, y+h/2)
