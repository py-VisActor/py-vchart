"""Public offscreen rendering entry point."""

from .._deps.vrender import Surface
from ..chart.bar import render_bar
from ..chart.line import render_line

from ..chart.scatter import render_scatter

from ..chart.cells import render_heatmap, render_mosaic, render_progress
from ..chart.common import render_common
from ..chart.interval import render_interval
from ..chart.statistical import render_box_plot, render_histogram, render_waterfall

from ..chart.polar import render_pie, render_rose
from ..chart.radial import render_radar, render_indicator
from ..chart.liquid import render_liquid

from ..chart.correlation import render_correlation
from ..chart.swarm import render_swarm
from ..chart.stat_panels import render_pairs, render_hexbin
from ..chart.stat_matrix import render_matrix
from ..chart.stat_intervals import render_horizontal
from ..chart.statplots import OPTIONS as STATPLOTS, render_stat
from ..chart.ranking_bar import render_ranking_bar
from ..chart.ranking import render_ranking
from ..chart.timeline import render_timeline
from ..chart.word_cloud import render_words
from ..chart.candlestick import render_candlestick
from ..chart.venn import render_venn
from ..chart.scatter_sequence import render_scatter_sequence
from ..chart.storyline import render_storyline
from ..chart.event_steps import render_event_steps
from ..chart.sequence import render_combination, render_sequence
from ..chart.images import register_svg_source, render_image_cloud, render_pictogram
from ..chart.map import register_map, render_map
from ..chart.sankey import render_sankey
from ..chart.funnel import render_funnel
from ..chart.hierarchy import render_treemap, render_sunburst, render_circle_packing

CARTESIAN_RENDERERS = {
    "bar": render_bar, "line": render_line, "scatter": render_scatter,
    "area": render_interval, "rangeArea": render_interval, "rangeColumn": render_interval,
    "waterfall": render_waterfall, "histogram": render_histogram, "boxPlot": render_box_plot,
    "heatmap": render_heatmap, "mosaic": render_mosaic, "linearProgress": render_progress,
    "common": render_common,
}


POLAR_RENDERERS = {
    "pie": render_pie, "rose": render_rose, "radar": render_radar,
    "gauge": render_indicator, "circularProgress": render_indicator, "liquid": render_liquid,
}
GEOMETRY_RENDERERS = {"funnel": render_funnel, "treemap": render_treemap, "sunburst": render_sunburst,
                      "circlePacking": render_circle_packing, "sankey": render_sankey,
                      "correlation": render_correlation, "venn": render_venn}
EXTENSION_RENDERERS = {
    "storyline": render_storyline, "sequenceAnalysis": render_event_steps,
    "sequence": render_sequence, "combinationCandlestick": render_combination,
    "pictogram": render_pictogram, "imageCloud": render_image_cloud,
    "candlestick": render_candlestick,
    "conversionFunnel": render_funnel,
    "rankingList": render_ranking, "rankingBar": render_ranking_bar,
    "timeline": render_timeline,
}
EXTENSION_RENDERERS.update(dict.fromkeys(("sequenceScatterPixel", "sequenceScatterKDE", "sequenceScatterLink"), render_scatter_sequence))
STAT_RENDERERS = dict.fromkeys(STATPLOTS, render_stat)
STAT_RENDERERS.update(shapBeeswarmPlot=render_swarm, pairPlot=render_pairs, hexbinPlot=render_hexbin)
STAT_RENDERERS.update(dict.fromkeys(("featureImportancePlot", "pointIntervalPlot"), render_horizontal))
STAT_RENDERERS.update(dict.fromkeys(("missingValueMatrix", "correlationMatrix", "confusionMatrix"), render_matrix))
RENDERERS = (
    STAT_RENDERERS | CARTESIAN_RENDERERS | POLAR_RENDERERS | GEOMETRY_RENDERERS
    | EXTENSION_RENDERERS | {"map": render_map, "wordCloud": render_words}
)


class VChart:
    register_svg_source = staticmethod(register_svg_source)
    register_map = staticmethod(register_map)

    def __init__(self, spec):
        self.spec = spec

    def render(self):
        """Render the current spec, returning this chart for PNG export."""
        kind = self.spec.get("type") if isinstance(self.spec, dict) else None
        if not isinstance(kind, str) or kind not in RENDERERS:
            raise ValueError(f"Unsupported chart type; expected one of {tuple(RENDERERS)}")
        width = self.spec.get("width", 640)
        height = self.spec.get("height", 480)
        if kind == "sequenceScatterPixel":
            width = height = 300
        if not all(type(n) is int and 1 <= n <= 8192 for n in (width, height)):
            raise ValueError(f"{kind}.width and {kind}.height must be integers between 1 and 8192")
        surface = Surface(width, height, text_contrast=.5 if kind == "wordCloud" else 0)
        renderer = RENDERERS[kind]
        rows = self.spec.get("data")
        if (kind in ("histogram", "boxPlot") and isinstance(rows, list)
                and all(isinstance(row, dict) and "value" in row for row in rows)
                and "xField" not in self.spec and "yField" not in self.spec):
            renderer = render_stat
        scene = renderer(self.spec, surface, width, height)
        self.scene = scene
        self._surface = surface
        return self

    def to_png(self):
        """Return the most recently rendered frame as PNG bytes."""
        if not hasattr(self, "_surface"):
            self.render()
        return self._surface.png()
