"""Helpers for chart types that derive two axis domains from richer records."""

from math import isfinite

from .._deps.vdataset import inline_values
from .cartesian import Axis, DYNAMIC, axis_options, check_keys, frame_scene, prepare_frame

BLUE = "#1664ff"
SMALL_PALETTE = ("#1664ff", "#1ac6ff", "#ff8a00", "#3cc780", "#7442d4",
                 "#ffc400", "#304d77", "#b48deb", "#009488", "#ff7dda")
LARGE_PALETTE = ("#1664ff", "#b2cfff", "#1ac6ff", "#94efff", "#ff8a00", "#ffce7a",
                 "#3cc780", "#b9edcd", "#7442d4", "#ddc5fa", "#ffc400", "#fae878",
                 "#304d77", "#8b959e", "#b48deb", "#efe3ff", "#009488", "#59baa8",
                 "#ff7dda", "#ffcfee")


def palette_for(count):
    return SMALL_PALETTE if count <= len(SMALL_PALETTE) else LARGE_PALETTE


BASE = {"type", "width", "height", "padding", "background", "data", "axes", "direction", "xField", "yField"}


def records(spec, extra=()):
    check_keys(spec, BASE | DYNAMIC | set(extra), spec["type"])
    direction = spec.get("direction", "vertical")
    if direction not in ("horizontal", "vertical"):
        raise ValueError(f"{spec['type']}.direction must be horizontal or vertical")
    values = inline_values(spec.get("data"), f"{spec['type']}.data")
    if not all(isinstance(row, dict) for row in values):
        raise ValueError(f"{spec['type']}.data.values requires records")
    return values


def fields(spec, horizontal=False):
    return (spec.get("yField"), spec.get("xField")) if horizontal else (spec.get("xField"), spec.get("yField"))


def field(row, key):
    if not isinstance(key, str) or key not in row:
        raise ValueError(f"Missing data field: {key}")
    return row[key]


def number(row, key):
    value = field(row, key)
    if type(value) not in (float, int) or not isfinite(value):
        raise ValueError(f"Expected finite number in field {key}")
    return value


def make_frame(spec, surface, width, height, categories, values, *, horizontal=False,
               first_kind="band", second_kind="linear", reverse_side=None, defaults=None,
               hide_labels=None):
    cat_side, val_side = ("left", "bottom") if horizontal else ("bottom", "left")
    options = axis_options(spec)
    axes = {}
    for side, kind, domain in [(cat_side, first_kind, categories), (val_side, second_kind, values)]:
        config = (defaults or {}).get(side, {}) | options[side]
        if config.get("type", kind) != kind:
            raise ValueError(f"{spec['type']}.axes.{side}.type must be {kind}")
        axis = Axis.make(side, kind, domain, config, f"{spec['type']}.axes")
        axis.reverse = side == reverse_side
        axis.show_labels = side != hide_labels
        axes[side] = axis
    frame = prepare_frame(spec, surface, width, height, axes, horizontal)
    return frame


def result(surface, frame, **marks):
    return frame_scene(surface, frame) | {"marks": marks}


def rect_between(frame, category, start, end, thickness=None):
    offset, band = frame.positions[category]
    x, y, _, _ = frame.plot
    breadth = band if thickness is None else thickness
    edge = offset + (band - breadth) / 2
    low, high = sorted((frame.value_pixel(start), frame.value_pixel(end)))
    if frame.horizontal:
        return [low, y + edge, high, y + edge + breadth]
    return [x + edge, low, x + edge + breadth, high]
