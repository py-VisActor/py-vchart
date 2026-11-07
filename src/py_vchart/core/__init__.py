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

    def __init__(self,spec,backend='cpu',text_engine='canvas',maps=None,svgs=None):
        from copy import deepcopy
        from collections.abc import Mapping
        from ..chart.map import _sources
        from ..chart.images import _svg_sources,validate_svg
        from .._deps.vlayouts.geo import read_features
        if backend not in ('cpu','auto','gpu'):raise ValueError('backend must be cpu, auto, or gpu')
        if text_engine not in ('canvas','reference'):raise ValueError('text_engine must be canvas or reference')
        self.spec=spec;self.backend=backend;self.text_engine=text_engine
        self._maps=deepcopy(_sources) if maps is None else {}
        self._svgs=deepcopy(_svg_sources) if svgs is None else {}
        for supplied,target,convert in ((maps,self._maps,read_features),(svgs,self._svgs,validate_svg)):
            if supplied is None:continue
            if not isinstance(supplied,Mapping):raise TypeError('maps/svgs must be explicit mappings')
            for name,source in supplied.items():
                if not isinstance(name,str) or not name:raise ValueError('Resource names must be nonempty strings')
                target[name]=deepcopy(convert(deepcopy(source)))

    @staticmethod
    def supported_types():
        return tuple(RENDERERS)

    @staticmethod
    def spec_size(spec):
        if not isinstance(spec,dict) or spec.get('type') not in RENDERERS:
            raise ValueError('Unsupported chart type')
        width,height=(300,300) if spec['type']=='sequenceScatterPixel' else (spec.get('width',640),spec.get('height',480))
        if not all(type(n) is int and 1<=n<=8192 for n in (width,height)):
            raise ValueError('Chart width/height must be integers between 1 and 8192')
        return width,height

    @property
    def width(self):return self.spec_size(self.spec)[0]

    @property
    def height(self):return self.spec_size(self.spec)[1]

    @property
    def engine(self):
        if not hasattr(self,'_surface'):self.render()
        return dict(self._surface.canvas.engine)

    def _draw(self,surface,width,height):
        from .._deps.vrender._state import render_scope,resource_scope
        renderer=RENDERERS[self.spec['type']];rows=self.spec.get('data')
        if (self.spec['type'] in ('histogram','boxPlot') and isinstance(rows,list)
                and all(isinstance(row,dict) and 'value' in row for row in rows)
                and 'xField' not in self.spec and 'yField' not in self.spec):renderer=render_stat
        backend='gpu' if surface.canvas.engine.get('renderer')=='GPU' else 'cpu'
        with render_scope(backend,self.text_engine,surface.ctx),resource_scope(self._maps,self._svgs):
            scene=renderer(self.spec,surface,width,height)
        self.scene=_plain_scene(scene);self._surface=surface
        return self

    def render(self):
        """Render an owned Canvas; default native text has no skia-python path."""
        width,height=self.spec_size(self.spec)
        surface=Surface(width,height,text_contrast=.5 if self.spec['type']=='wordCloud' else 0,
                        backend=self.backend,text_engine=self.text_engine)
        result=self._draw(surface,width,height);self._borrowed=False
        return result

    def draw_to(self,canvas,*,x=0,y=0):
        """Draw vectors on a borrowed owner Canvas, without device/size changes.

        The host Canvas owns backend selection. Only mask-layout internals may
        allocate their own raster surfaces. scene holds pure metadata afterward.
        """
        from math import isfinite
        if self.text_engine!='canvas':
            raise ValueError('draw_to requires text_engine=canvas; reference is an offscreen regression mode')
        if not all(type(v) in (int,float) and isfinite(v) for v in (x,y)):raise ValueError('draw_to origin must be finite')
        width,height=self.spec_size(self.spec);surface=Surface.from_canvas(canvas,text_engine=self.text_engine)
        from py_skia_canvas import Path2D
        ctx=surface.ctx;ctx.save()
        try:
            ctx.translate(x,y);clip=Path2D();clip.rect(0,0,width,height);ctx.clip(clip)
            from .._deps.vrender import FONT
            ctx.font=FONT
            result=self._draw(surface,width,height)
        finally:ctx.restore()
        self._borrowed=True
        return result

    @staticmethod
    def _export_options(format,options):
        format=str(format).lower();format='jpg' if format=='jpeg' else format
        if format not in ('png','jpg','webp','svg','pdf'):raise ValueError('Unsupported static export format')
        options={} if options is None else dict(options)
        allowed={'quality','density','matte','outline','downsample','msaa','colorType'}
        if set(options)-allowed:raise ValueError('Unsupported export options: '+str(sorted(set(options)-allowed)))
        density=options.get('density',1)
        if type(density) is not int or density<1:raise ValueError('density must be a positive integer')
        return format,options

    def export_size(self,format='png',options=None):
        format,options=self._export_options(format,options)
        density=options.get('density',1) if format in ('png','jpg','webp') else 1
        width,height=self.width*density,self.height*density
        if format in ('png','jpg','webp') and (max(width,height)>32768 or width*height>8192**2):
            raise ValueError('Raster export exceeds 32768px edge or 8192 squared pixel budget')
        return width,height

    def to_buffer(self,format='png',options=None):
        format,options=self._export_options(format,options)
        self.export_size(format,options)
        if not hasattr(self,'_surface') or getattr(self,'_borrowed',False):self.render()
        return self._surface.encode(format,options)

    def to_png(self):
        return self.to_buffer('png')


def _plain_scene(value):
    """No native/context objects cross the public geometry metadata boundary."""
    from dataclasses import is_dataclass,asdict
    from collections.abc import Mapping
    if is_dataclass(value):return _plain_scene(asdict(value))
    if isinstance(value,Mapping):return {key:_plain_scene(item) for key,item in value.items()}
    if isinstance(value,(list,tuple)):return [_plain_scene(item) for item in value]
    if type(value).__module__.startswith('numpy'):
        return _plain_scene(value.tolist() if hasattr(value,'tolist') else value.item())
    if value is None or isinstance(value,(str,int,float,bool)):return value
    raise TypeError('Chart scene contains non-value object: '+type(value).__name__)


def supported_types():
    return VChart.supported_types()
