"""Public Canvas typography; calibrated reference mode is explicit."""
from ._state import active_context, settings


def font_css(family, size, weight=400, italic=False):
    weight={"normal":400,"bold":700}.get(weight,weight)
    family=str(family).strip().removesuffix(';').strip()
    return f'{"italic" if italic else "normal"} {weight} {size:g}px {family}'


class _CanvasFont:
    def __init__(self,family,size,weight,italic):
        self.css=font_css(family,size,weight,italic)

    def measureText(self,text):
        ctx=active_context.get()
        if ctx is None:
            from . import Surface
            owner=Surface(1,1);ctx=owner.ctx
        ctx.save()
        try:ctx.font=self.css;return ctx.measureText(str(text)).width
        finally:ctx.restore()


def raster_font(family,size,weight=400,italic=False):
    """Owner-local metrics adapter; no native handles in global caches."""
    if settings.get()[1]=='reference':
        from ._reference_text import raster_font as reference
        return reference(family,size,weight,italic)
    return _CanvasFont(family,size,weight,italic)


def _rgba(color):
    from ._reference_text import _rgba as sample
    return sample(color)


def glyph_run(surface,text,x,y,size,color,align='left',*,bold=False,weight=None,italic=False,family='Microsoft YaHei'):
    if surface.text_engine=='reference':
        from ._reference_text import glyph_run as reference
        return reference(surface,text,x,y,size,color,align,bold=bold,weight=weight,italic=italic,family=family)
    if not str(text):return
    ctx=surface.ctx;ctx.save()
    try:
        ctx.font=font_css(family,size,weight if weight is not None else 700 if bold else 400,italic)
        ctx.textAlign=align;ctx.textBaseline='alphabetic';ctx.fillStyle=color
        ctx.fillText(str(text),x,y)
    finally:ctx.restore()
