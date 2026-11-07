"""Static geographic areas joined to inline records by feature name."""

from .._deps.vdataset import inline_values
from .._deps.vlayouts.geo import fit_paths, read_features
from .cartesian import DYNAMIC, check_keys
from .layout_helpers import palette_for
from .plot import hidden_label, plot_region
from .point import mark_options

_sources = {}


def register_map(name, geojson):
    if not isinstance(name, str) or not name:
        raise ValueError("map requires a nonempty registration name")
    _sources[name] = read_features(geojson)


def render_map(spec, surface, width, height):
    check_keys(spec, DYNAMIC | {"type", "width", "height", "padding", "background", "map",
               "nameField", "nameProperty", "seriesField", "valueField", "data", "defaultFillColor",
               "area", "label"}, "map")
    hidden_label(spec)
    name = spec.get("map")
    if not isinstance(name, str) or name not in _sources:
        raise ValueError("map requires a local source registered with VChart.register_map")
    features = _sources[name]
    plot = plot_region(spec, surface, width, height)
    paths = fit_paths(features, plot)
    rows = inline_values(spec.get("data", {"values": []}), "map.data")
    by_name, groups = {}, {}
    for row in rows:
        field = spec.get("nameField")
        if not isinstance(row, dict) or not isinstance(row.get(field), str):
            raise ValueError("map requires a string nameField on every record")
        by_name.setdefault(row[field], row)
        group = row.get(spec["seriesField"]) if "seriesField" in spec else True
        if group is not None and not isinstance(group, (str, int, float, bool)):
            raise ValueError("map seriesField requires scalar values")
        if group is not None:
            groups.setdefault(group, len(groups))
    palette = palette_for(len(groups))
    visible, style = mark_options(spec, "area", {"fill", "stroke", "lineWidth"})
    fallback = spec.get("defaultFillColor", "#f3f3f3")
    if not all(isinstance(c, str) for c in (fallback, style.get("fill", fallback))):
        raise ValueError("map requires literal fill colors")
    marks = []
    for (properties, _), rings in zip(features, paths):
        if not visible:
            continue
        row = by_name.get(properties.get(spec.get("nameProperty", "name")))
        color = fallback
        if row is not None:
            group = row.get(spec["seriesField"]) if "seriesField" in spec else True
            if group in groups:
                color = palette[groups[group] % len(palette)]
        color = style.get("fill", color)
        surface.polygon_rings(rings, color, style.get("stroke", "black"), style.get("lineWidth", 0.5))
        marks.append([rings, color.lower()])
    return dict(plot=plot, axes=[], labels=[], marks={"area": marks})
