"""Continuous positions and category bands for the static bar slice."""

from math import ceil, floor, isfinite, log10, sqrt


def linear(value, domain, extent):
    lo, hi = domain
    start, end = extent
    return start + (value - lo) / (hi - lo) * (end - start)


def bands(categories, length):
    # VChart defaults: 10% inner padding, 30% outer padding.
    count = len(categories)
    step = length / (max(1, count - 0.1) + 0.6)
    start = (length - step * (count - 0.1)) / 2
    return {key: (start + i * step, 0.9 * step) for i, key in enumerate(categories)}


def numeric_axis(values, options, *, path="bar.axes", include_zero=True):
    low = options.get("min", min([0, *values]) if include_zero else min(values))
    high = options.get("max", max([0, *values]) if include_zero else max(values))
    if any(type(v) not in (int, float) or not isfinite(v) for v in (low, high)):
        raise ValueError(f"{path}: min and max must be finite numbers")
    if high == low == 0 and not ("min" in options and "max" in options):
        high = 1
    if high <= low:
        raise ValueError(f"{path}: max must exceed min")
    raw = (high - low) / 5
    power = 10 ** floor(log10(raw))
    ratio = raw / power
    factor = 10 if ratio >= sqrt(50) else 5 if ratio >= sqrt(10) else 2 if ratio >= sqrt(2) else 1
    step = factor * power
    # Positive whole-unit ticks may increase their step to avoid overcrowding.
    if step >= 1:
        while ceil(high / step) - floor(low / step) + 1 > 6:
            step += power * (2 if factor == 10 else 1)
    first, last = floor(low / step), ceil(high / step)
    ticks = [float(f"{i * step:.14g}") for i in range(first, last + 1)]
    low = options.get("min", ticks[0])
    high = options.get("max", ticks[-1])
    return [low, high], [v for v in ticks if low <= v <= high]
