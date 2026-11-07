"""Axes, scales and plot layout shared by single-series Cartesian charts."""

from dataclasses import dataclass
from math import ceil, isfinite

from .._deps.vdataset import read_records
from .._deps.vscale import bands, linear, numeric_axis

GRID = "#f1f2f5"
AXIS = "#d9dde4"
DYNAMIC = {"animation", "tooltip", "hover", "select", "crosshair", "interactions",
           "animationAppear", "animationEnter", "animationUpdate", "animationExit",
           "animationDisappear", "events"}


def check_keys(obj, allowed, path):
    if not isinstance(obj, dict):
        raise ValueError(f"{path} must be an object")
    for key in obj:
        if key not in allowed:
            raise ValueError(f"Unsupported static field: {path}.{key}")


def axis_options(spec, *, secondary=False):
    kind = spec["type"]
    axes = {"bottom": {}, "left": {}}
    allowed = {"orient", "visible", "min", "max", "type"}
    if secondary:
        axes["right"] = {}
        allowed.add("seriesIndex")
    seen = set()
    items = spec.get("axes", [])
    if not isinstance(items, list):
        raise ValueError(f"{kind}.axes must be a list")
    for index, axis in enumerate(items):
        path = f"{kind}.axes[{index}]"
        check_keys(axis, allowed, path)
        side = axis.get("orient")
        if side not in axes or side in seen:
            raise ValueError(f"{path}.orient must uniquely identify a supported axis")
        if "visible" in axis and type(axis["visible"]) is not bool:
            raise ValueError(f"{path}.visible must be boolean")
        seen.add(side)
        axes[side] = axis
    return axes


@dataclass
class Axis:
    side: str
    kind: str
    domain: list
    ticks: list
    visible: bool
    reverse: bool = False
    show_labels: bool = True

    @classmethod
    def make(cls, side, kind, values, options, path):
        if kind == "linear":
            if any(type(v) not in (float, int) or not isfinite(v) for v in values):
                raise ValueError(f"{path}.{side} requires finite numeric coordinates")
            domain, ticks = numeric_axis(values, options, path=path)
        else:
            if "min" in options or "max" in options:
                raise ValueError(f"{path}: category bounds require a band domain")
            domain = list(dict.fromkeys(values))
            ticks = domain
        return cls(side, kind, domain, ticks, options.get("visible", True))

    def label(self, tick):
        return f"{tick:g}" if self.kind == "linear" else tick

    def extent(self, width, height):
        if self.side == "bottom":
            return [0, width]
        return [height, 0] if (self.kind == "linear") != self.reverse else [0, height]


def plot_bounds(width, height, pad, axes, surface):
    left = right = top = bottom = pad
    for axis in axes.values():
        if not axis.visible or not axis.show_labels or not axis.ticks:
            continue
        labels = [axis.label(tick) for tick in axis.ticks]
        if axis.side in ("left", "right"):
            gap = 12 if axis.kind == "linear" else 16
            required = pad + gap + max(surface.measure(label) for label in labels)
            if axis.side == "left":
                left = max(left, required)
            else:
                right = max(right, required)
            if axis.kind == "linear":
                top = max(top, pad + 6)
                bottom = max(bottom, pad + 6)
        elif axis.kind == "linear":
            bottom = max(bottom, pad + 20)
            right = max(right, pad + surface.measure(labels[-1]) / 2)
            left = max(left, pad + surface.measure(labels[0]) / 2)
        else:
            bottom = max(bottom, pad + 24)
    x, y = ceil(left), ceil(top)
    w, h = width - ceil(right) - x, height - ceil(bottom) - y
    if min(w, h) <= 0:
        raise ValueError("Cartesian canvas too small for axes and padding")
    return x, y, w, h


@dataclass
class CartesianFrame:
    plot: tuple
    horizontal: bool
    axes: dict
    band_positions: dict

    @property
    def positions(self):
        return self.band_positions["left" if self.horizontal else "bottom"]

    @property
    def value_side(self):
        return "bottom" if self.horizontal else "left"

    @property
    def domain(self):
        return self.axes[self.value_side].domain

    def coordinate(self, side, value):
        x, y, w, h = self.plot
        axis = self.axes[side]
        origin = x if side == "bottom" else y
        if axis.kind == "linear":
            return origin + linear(value, axis.domain, axis.extent(w, h))
        offset, band = self.band_positions[side][value]
        return origin + offset + band / 2

    def value_pixel(self, value):
        return self.coordinate(self.value_side, value)

    def point(self, category, value):
        x, y = (value, category) if self.horizontal else (category, value)
        return [self.coordinate("bottom", x), self.coordinate("left", y)]


def draw_axis(surface, frame, axis):
    if not axis.visible:
        return
    x, y, w, h = frame.plot
    bottom = axis.side == "bottom"
    if axis.kind == "band":
        if bottom:
            surface.line(x, y + h, x + w, y + h, AXIS)
        else:
            surface.line(x, y, x, y + h, AXIS)
    for tick in axis.ticks:
        p = frame.coordinate(axis.side, tick)
        label = axis.label(tick)
        if bottom and axis.kind == "linear":
            surface.line(p, y, p, y + h, GRID)
            if axis.show_labels:
                surface.label(label, p, y + h + 8, "center", "top")
        elif bottom:
            surface.line(p, y + h, p, y + h + 4, AXIS)
            surface.label(label, p, y + h + 12, "center", "top")
        elif axis.side == "right":
            surface.label(label, x + w + 12, p, "left", "middle")
        elif axis.kind == "linear":
            surface.line(x, p, x + w, p, GRID)
            surface.label(label, x - 12, p, "right", "middle")
        else:
            surface.line(x - 4, p, x, p, AXIS)
            surface.label(label, x - 16, p, "right", "middle")


def render_cartesian(spec, surface, width, height, *, marks, draw_series, allow_missing=False, allow_numeric_pair=False):
    kind = spec["type"]
    common_fields = {"type", "width", "height", "data", "xField", "yField", "direction",
                     "axes", "padding", "background"}
    check_keys(spec, common_fields | marks | DYNAMIC, kind)
    direction = spec.get("direction", "vertical")
    if direction not in ("horizontal", "vertical"):
        raise ValueError(f"{kind}.direction must be horizontal or vertical")
    horizontal = direction == "horizontal"
    category_key, value_key = ("yField", "xField") if horizontal else ("xField", "yField")
    if not all(isinstance(spec.get(k), str) for k in (category_key, value_key)):
        raise ValueError(f"{kind}.xField and {kind}.yField must be single field names")
    rows = read_records(spec.get("data"), spec[category_key], spec[value_key],
                        path=f"{kind}.data", allow_missing=allow_missing)
    options = axis_options(spec)
    category_side, numeric_side = ("left", "bottom") if horizontal else ("bottom", "left")
    first_kind = options[category_side].get("type", "band")
    supported = ("band", "linear") if allow_numeric_pair else ("band",)
    if first_kind not in supported:
        raise ValueError(f"{kind}.axes.{category_side}.type must be one of {supported}")
    if options[numeric_side].get("type", "linear") != "linear":
        raise ValueError(f"{kind}.axes.{numeric_side}.type must be linear")
    axes = {
        category_side: Axis.make(category_side, first_kind, [k for k, _ in rows],
                                 options[category_side], f"{kind}.axes"),
        numeric_side: Axis.make(numeric_side, "linear", [v for _, v in rows if v is not None],
                                options[numeric_side], f"{kind}.axes"),
    }
    frame = prepare_frame(spec, surface, width, height, axes, horizontal)
    geometry = draw_series(spec, surface, frame, rows)
    return frame_scene(surface, frame) | geometry


def prepare_frame(spec, surface, width, height, axes, horizontal=False):
    pad = spec.get("padding", 20)
    if type(pad) not in (float, int) or not isfinite(pad) or pad < 0:
        raise ValueError(f"{spec['type']}.padding must be a nonnegative number")
    plot = plot_bounds(width, height, pad, axes, surface)
    _, _, w, h = plot
    band_positions = {}
    for side, axis in axes.items():
        if axis.kind == "band":
            length = w if side == "bottom" else h
            positions = bands(axis.domain, length)
            if axis.reverse:
                positions = {key: (length - offset - band, band) for key, (offset, band) in positions.items()}
            band_positions[side] = positions
    frame = CartesianFrame(plot, horizontal, axes, band_positions)
    surface.rect((0, 0, width, height), spec.get("background", "white"))
    for axis in sorted(reversed(axes.values()), key=lambda axis: axis.kind != "linear"):
        draw_axis(surface, frame, axis)
    return frame


def frame_scene(surface, frame, order=("bottom", "left")):
    plot, axes = frame.plot, frame.axes
    _, _, w, h = plot
    return {
        "plot": list(plot),
        "labels": sorted(surface.labels, key=lambda label: (label["x"], label["y"])),
        "axes": [{"orient": side, "domain": axes[side].domain,
                  "range": axes[side].extent(w, h)}
                 for side in order],
    }
