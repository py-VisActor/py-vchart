"""Static polar layout and sector series. Angles are clockwise in canvas radians."""

from collections import defaultdict
from math import cos, isfinite, radians, sin

from .._deps.vdataset import inline_values
from .._deps.vscale import linear, numeric_axis
from .cartesian import DYNAMIC, check_keys
from .layout_helpers import field, number, palette_for
from .plot import plot_region


class PolarFrame:
    def __init__(self, spec, surface, width, height, options):
        base = {"type", "width", "height", "background", "padding", "data", "valueField"}
        check_keys(spec, base | DYNAMIC | set(options), spec["type"])
        self.rows = inline_values(spec.get("data"), spec["type"] + ".data")
        self.values = [number(row, spec.get("valueField")) for row in self.rows]
        if any(v < 0 for v in self.values):
            raise ValueError("Polar charts require nonnegative values")
        self.plot = plot_region(spec, surface, width, height)
        self.center = [width / 2, height / 2]
        self.radius = min(self.plot[2:]) / 2
        self.surface = surface
        self.angles = [radians(spec.get("startAngle", -90)), radians(spec.get("endAngle", 270))]
        self.axes = []
        self.marks = {}

    def radii(self, spec, inner, outer):
        ratios = [spec.get("innerRadius", inner), spec.get("outerRadius", outer)]
        if not all(isfinite(v) for v in ratios) or not 0 <= ratios[0] <= ratios[1] <= 1:
            raise ValueError("Invalid innerRadius or outerRadius")
        return [self.radius * v for v in ratios]

    def point(self, angle, radius):
        return [self.center[0] + cos(angle) * radius, self.center[1] + sin(angle) * radius]

    def axis(self, orient, domain, extent):
        self.axes.append(dict(orient=orient, domain=domain, range=extent))

    def sector(self, name, inner, outer, start, end, color, opacity=1):
        arc = [*self.center, inner, outer, start, end]
        self.marks.setdefault(name, []).append(arc)
        self.surface.sector(*arc, color, opacity)

    def scene(self):
        labels = sorted(self.surface.labels, key=lambda label: (label["x"], label["y"]))
        return dict(plot=self.plot, axes=self.axes, labels=labels, marks=self.marks)


SECTOR_OPTIONS = {"categoryField", "startAngle", "endAngle", "innerRadius", "outerRadius"}


def render_pie(spec, surface, width, height):
    frame = PolarFrame(spec, surface, width, height, SECTOR_OPTIONS)
    inner, outer = frame.radii(spec, 0, .6)
    categories = [field(row, spec.get("categoryField")) for row in frame.rows]
    keys = list(dict.fromkeys(categories))
    colors = palette_for(len(keys))
    total = sum(frame.values)
    start, end = frame.angles
    angle = start
    frame.marks["pie"] = []
    for key, value in zip(categories, frame.values):
        following = angle + (end - start) * value / total if total else angle
        frame.sector("pie", inner, outer, angle, following, colors[keys.index(key) % len(colors)])
        angle = following
    return frame.scene()


def render_rose(spec, surface, width, height):
    frame = PolarFrame(spec, surface, width, height, SECTOR_OPTIONS | {"seriesField", "stack"})
    fields = spec.get("categoryField")
    fields = fields if isinstance(fields, list) else [fields]
    if len(fields) not in (1, 2):
        raise ValueError("rose.categoryField requires one or two fields")
    keys = [field(row, fields[0]) for row in frame.rows]
    categories = list(dict.fromkeys(keys))
    group_key = spec.get("seriesField")
    groups = [field(row, group_key) if group_key else None for row in frame.rows]
    series = list(dict.fromkeys(groups))
    colors = palette_for(len(series))
    slots = [field(row, fields[1]) for row in frame.rows] if len(fields) == 2 else [None] * len(keys)
    bands = list(dict.fromkeys(slots))
    totals = defaultdict(float)
    ranges = []
    for key, slot, value in zip(keys, slots, frame.values):
        base = totals[key, slot] if spec.get("stack", bool(group_key)) else 0
        ranges.append((base, base + value))
        totals[key, slot] = base + value
    domain, _ = numeric_axis([high for _, high in ranges], {})
    extent = frame.radii(spec, 0, .6)
    frame.axis("angle", categories, frame.angles)
    frame.axis("radius", domain, extent)
    frame.marks["rose"] = []
    for key, slot, group, (low, high) in zip(keys, slots, groups, ranges):
        step = (frame.angles[1] - frame.angles[0]) / (len(categories) * len(bands))
        start = frame.angles[0] + (categories.index(key) * len(bands) + bands.index(slot)) * step
        frame.sector("rose", linear(low, domain, extent), linear(high, domain, extent),
                     start, start + step, colors[series.index(group) % len(colors)])
    return frame.scene()
