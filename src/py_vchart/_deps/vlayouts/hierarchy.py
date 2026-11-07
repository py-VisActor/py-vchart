"""Weighted hierarchy, rectangular partitions and concentric rings."""

from bisect import bisect_left
from dataclasses import dataclass
from itertools import accumulate
from math import isfinite


@dataclass
class Node:
    key: object
    weight: float
    children: list
    levels: int


def hierarchy(rows, key, value):
    nodes = []
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get(key), (int, float, str)):
            raise ValueError("Hierarchy nodes require a scalar category")
        children = row.get("children", [])
        if not isinstance(children, list):
            raise ValueError("Hierarchy children must be an array")
        descendants = hierarchy(children, key, value)
        weight = row.get(value, 0)
        if type(weight) not in (int, float) or not isfinite(weight) or weight < 0:
            raise ValueError("Hierarchy weights must be finite and nonnegative")
        nodes.append(Node(row[key], max(weight, sum(n.weight for n in descendants)), descendants,
                          1 + max((n.levels for n in descendants), default=0)))
    return nodes


def binary_tiles(nodes, weight, box):
    """Split the longer edge at the sibling boundary nearest half the weight."""
    sums = list(accumulate((n.weight for n in nodes), initial=0))
    pending = [(0, len(nodes), weight, box)] if nodes else []
    while pending:
        first, stop, total, bounds = pending.pop()
        if stop == first + 1:
            yield nodes[first], bounds
            continue
        target = sums[first] + total/2
        cut = min(bisect_left(sums, target, first+1, stop), stop-1)
        if cut > first+1 and target-sums[cut-1] < sums[cut]-target:
            cut -= 1
        part = sums[cut] - sums[first]
        x, y, right, bottom = bounds
        fraction = part / total if total else 1
        if right-x > bottom-y:
            split = x + (right-x)*fraction
            left_box, right_box = (x,y,split,bottom), (split,y,right,bottom)
        else:
            split = y + (bottom-y)*fraction
            left_box, right_box = (x,y,right,split), (x,split,right,bottom)
        pending.append((cut, stop, total-part, right_box))
        pending.append((first, cut, part, left_box))


def inset(box, amount):
    x, y, right, bottom = box
    dx = min(amount, (right-x)/2)
    dy = min(amount, (bottom-y)/2)
    return [x+dx, y+dy, right-dx, bottom-dy]


def treemap_tiles(roots, box, gap, padding):
    total = sum(node.weight for node in roots)
    area = (box[2]-box[0])*(box[3]-box[1])

    def visible(node):
        return total > 0 and node.weight*area/total >= 10

    def visit(node, bounds, depth, key):
        children = [child for child in node.children if visible(child)]
        if not children:
            yield key, bounds
            return
        space = padding(depth)
        if 2*space < min(bounds[2]-bounds[0], bounds[3]-bounds[1]):
            bounds = inset(bounds, space)
        for child, tile in binary_tiles(children, node.weight, inset(bounds, -gap/2)):
            yield from visit(child, inset(tile, gap/2), depth+1, key)

    for node, tile in binary_tiles([n for n in roots if visible(n)], total, inset(box, -gap/2)):
        yield from visit(node, inset(tile, gap/2), 0, node.key)


def sunburst_arcs(roots, angles, radii):
    levels = max((node.levels for node in roots), default=1)
    step = (radii[1]-radii[0])/levels

    def visit(nodes, total, start, end, depth, root=None):
        scale = (end-start)/total if total else 0
        for node in nodes:
            key = node.key if root is None else root
            stop = start + node.weight*scale
            yield key, (radii[0]+depth*step, radii[0]+(depth+1)*step, start, stop)
            yield from visit(node.children, node.weight, start, stop, depth+1, key)
            start = stop

    yield from visit(roots, sum(n.weight for n in roots), *angles, 0)
