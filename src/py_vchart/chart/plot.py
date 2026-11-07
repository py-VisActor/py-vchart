"""Shared drawing region for static charts without Cartesian axes."""

from math import isfinite


def plot_region(spec, surface, width, height):
    pad = spec.get("padding", 20)
    if type(pad) not in (int, float) or not 0 <= pad < min(width, height) / 2:
        raise ValueError("Invalid plot padding")
    surface.rect((0, 0, width, height), spec.get("background", "white"))
    return [pad, pad, width - 2 * pad, height - 2 * pad]


def nonnegative(value, path):
    if type(value) not in (int, float) or not isfinite(value) or value < 0:
        raise ValueError(f"{path} must be a finite nonnegative number")
    return value


def hidden_label(spec, default=False):
    if spec.get("label", {"visible": default}) != {"visible": False}:
        raise ValueError(f"{spec['type']}.label currently requires visible=false")
