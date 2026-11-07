"""Stacked Cartesian regions sharing a horizontal categorical axis."""

from math import ceil
from .._deps.vscale import bands
from .._deps.vdataset import inline_values
from .bar import draw_bars
from .candlestick import draw_candles
from .cartesian import Axis, CartesianFrame, check_keys, draw_axis, frame_scene
from .layout_helpers import number, palette_for
from .line import draw_line


def band_frame(surface, rect, categories, values, options):
    x = Axis.make("bottom", "band", categories, {}, "series.xField")
    y = Axis.make("left", "linear", values, options, "series.yField")
    return CartesianFrame(
        rect, False, {"bottom": x, "left": y}, {"bottom": bands(x.domain, rect[2])}
    )


def series_marks(series, rows, surface, frame, color):
    points = [(r[series["xField"]], number(r, series["yField"])) for r in rows]
    if series["type"] == "bar":
        config = {
            "bar": {"style": {"fill": color} | series.get("bar", {}).get("style", {})}
        }
        return {"bar": draw_bars(config, surface, frame, points)["bars"]}
    if series["type"] == "line":
        config = {
            "type": "line",
            "line": {"style": {"stroke": color}},
            "point": {"style": {"fill": color}},
        }
        geom = draw_line(
            config | {k: v for k, v in series.items() if k in ("point", "line")},
            surface,
            frame,
            points,
        )
        return {
            "point": geom["points"],
            "line": [p for segment in geom["segments"] for p in segment],
        }
    raise ValueError("Expected a bar or line series")


def render_combination(spec, surface, width, height):
    check_keys(
        spec,
        {
            "type",
            "width",
            "height",
            "candlestickSeries",
            "previewSeries",
            "axes",
            "padding",
            "previewHeight",
        },
        "combinationCandlestick",
    )
    candles = spec["candlestickSeries"]
    rows = inline_values(candles["data"], path="candlestickSeries.data")
    keys = [r[candles["xField"]] for r in rows]
    prices = [
        [
            number(r, candles[k])
            for k in ("openField", "highField", "lowField", "closeField")
        ]
        for r in rows
    ]
    options = next((a for a in spec.get("axes", []) if a.get("orient") == "left"), {})
    values = [v for row in prices for v in row]
    axis = Axis.make("left", "linear", values, options, "candlestickSeries")
    pad = spec.get("padding", 20)
    left = ceil(pad + 12 + max(surface.measure(axis.label(t)) for t in axis.ticks))
    w = width - pad - left
    available = height - 2 * pad - 24
    preview = spec.get("previewSeries")
    h = available if preview is None else spec.get("previewHeight", available / 2)
    if isinstance(h, str) and h.endswith("%"):
        h = float(h[:-1]) * (height - 2 * pad) / 100
    frame = band_frame(surface, (left, pad, w, h), keys, values, options)
    surface.rect((0, 0, width, height), "white")
    for side in ("left", "bottom"):
        draw_axis(surface, frame, frame.axes[side])
    marks = {"candlestick": draw_candles(candles, surface, frame, keys, prices)}
    scene = frame_scene(surface, frame)
    if preview:
        rows = inline_values(preview["data"], path="previewSeries.data")
        v = [number(r, preview["yField"]) for r in rows]
        sub = band_frame(surface, (left, pad + h + 24, w, available - h), keys, v, {})
        marks.update(series_marks(preview, rows, surface, sub, palette_for(2)[1]))
        scene["axes"].append(frame_scene(surface, sub)["axes"][1])
    return scene | {"marks": marks}


def render_sequence(spec, surface, width, height):
    check_keys(
        spec,
        {
            "type",
            "width",
            "height",
            "padding",
            "appendPadding",
            "axes",
            "series",
            "data",
        },
        "sequence",
    )
    series = spec["series"]
    if not series or spec.get("axes", [{}])[0].get("orient") != "bottom":
        raise ValueError("sequence requires series and a bottom axis")
    datasets = spec.get("data", [])
    if isinstance(datasets, dict):
        datasets = [datasets]
    data = []
    keys = []
    for s in series:
        ds = s.get("data")
        if ds is None:
            ds = (
                next((d for d in datasets if d.get("id") == s.get("dataId")), None)
                if "dataId" in s
                else datasets[s.get("dataIndex", 0)]
            )
        rows = inline_values(ds, path="sequence.series.data")
        data.append(rows)
        keys.extend(r[s["xField"]] for r in rows)
    p = spec.get("padding", 20)
    left = p + spec.get("appendPadding", {}).get("left", 0)
    w = width - left - p - 12 - spec.get("appendPadding", {}).get("right", 0)
    top = p
    color = palette_for(len(series))[(len(series) - 1) % len(palette_for(len(series)))]
    frames, marks = [], {}
    surface.rect((0, 0, width, height), "white")
    for s, rows in zip(series, data):
        h = s.get("height", (height - 60) / len(series) - 20)
        frame = band_frame(
            surface, (left, top, w, h), keys, [number(r, s["yField"]) for r in rows], {}
        )
        if s.get("grid", {}).get("visible", True):
            surface.line(
                left,
                top + h,
                left + w,
                top + h,
                s.get("grid", {}).get("style", {}).get("stroke", "#dfdfdf"),
            )
        marks.update(series_marks(s, rows, surface, frame, color))
        frames.append(frame)
        top += h + s.get("padding", 20)
    ax = frames[0].axes["bottom"]
    draw_axis(
        surface,
        CartesianFrame(
            (left, top + 20, w, 0), False, {"bottom": ax}, frames[0].band_positions
        ),
        ax,
    )
    scene = frame_scene(surface, frames[0])
    scene["axes"].extend(frame_scene(surface, f)["axes"][1] for f in frames[1:])
    return scene | {"marks": marks}
