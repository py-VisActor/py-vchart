"""Layer and size an acyclic, weighted node-link graph in logical pixels."""

from collections import deque
from dataclasses import dataclass, field


@dataclass(eq=False)
class Node:
    key: object
    category: object
    value: float
    incoming: list = field(default_factory=list)
    outgoing: list = field(default_factory=list)
    depth: int = 0
    tail: int = 0
    x: float = 0
    y: float = 0
    height: float = 0


@dataclass(eq=False)
class Link:
    source: Node
    target: Node
    value: float
    thickness: float = 0
    start: float = 0
    end: float = 0

    def __post_init__(self):
        self.source.outgoing.append(self)
        self.target.incoming.append(self)


def layers(nodes, align):
    pending = {n: len(n.incoming) for n in nodes}
    queue = deque(n for n in nodes if not pending[n])
    ordered = []
    while queue:
        node = queue.popleft()
        ordered.append(node)
        for edge in node.outgoing:
            child = edge.target
            child.depth = max(child.depth, node.depth+1)
            pending[child] -= 1
            if not pending[child]:
                queue.append(child)
    if len(ordered) != len(nodes):
        raise ValueError("sankey requires an acyclic graph")
    last = max(n.depth for n in nodes)
    for n in reversed(ordered):
        n.tail = max((link.target.tail+1 for link in n.outgoing), default=0)
    columns = [[] for _ in range(last+1)]
    for n in nodes:
        index = n.depth
        if align in ("right", "end"):
            index = last-n.tail
        elif align == "justify" and not n.outgoing:
            index = last
        elif align == "center" and not n.incoming and n.outgoing:
            index = min(link.target.depth for link in n.outgoing)-1
        columns[index].append(n)
    return columns


def assign_ports(nodes):
    for node in nodes:
        # Incoming bands follow the vertical order of their source nodes.
        node.incoming.sort(key=lambda link: link.source.y)
        for links, attr in [(node.outgoing, "start"), (node.incoming, "end")]:
            offset = 0
            for link in links:
                offset = min(offset + link.thickness, node.height)
                setattr(link, attr, node.y + offset-link.thickness/2)


def sankey_layout(nodes, length, breadth, width, gap, minimum, align, cross):
    if not nodes:
        return 0
    columns = layers(nodes, align)
    steps = len(columns)-1
    if isinstance(width, str):
        ratio = float(width[:-1])/100
        step = length/(steps+ratio) if steps+ratio else 0
        width = step*ratio
    else:
        step = (length-width)/steps if steps else float("inf")
    for n in nodes:
        n.value = max(n.value, sum(edge.value for edge in n.incoming), sum(edge.value for edge in n.outgoing))
    max_step = breadth/max(map(len, columns))
    gap = min(gap, max_step)
    if minimum+gap > max_step:
        gap = max_step/2 if minimum >= max_step else (max_step-minimum)/2
        minimum = min(max_step-gap, minimum)
    scales = []
    for column in columns:
        value = sum(n.value for n in column)
        if value:
            available = breadth-(len(column)-1)*max(gap, minimum)-minimum
            scales.append(available/value)
    scale = min(scales, default=float("inf"))
    for i, column in enumerate(columns):
        y = 0
        for n in column:
            n.x, n.y = i*step, y
            raw_height = max(n.value*scale, 0)
            n.height = max(raw_height, minimum)
            for edge in n.outgoing:
                edge.thickness = raw_height*(edge.value/n.value) if n.value else 0
            y += n.height+gap
        spare = breadth-y+gap
        for j, n in enumerate(column):
            if spare < 0 and len(column)>1:
                correction = spare/(len(column)-1)
                if gap+correction >= 0:
                    n.y += j*correction
            elif spare > 0 and cross == "end":
                n.y += spare
            elif spare > 0 and cross == "middle":
                n.y += spare/(len(column)+1)*(j+1)
    assign_ports(nodes)
    return width
