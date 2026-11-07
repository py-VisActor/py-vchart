"""Scoped render settings; no native objects survive a chart invocation."""
from contextlib import contextmanager
from contextvars import ContextVar

settings = ContextVar('vchart_render_settings', default=('cpu', 'canvas'))
active_context = ContextVar('vchart_active_context', default=None)
map_sources = ContextVar('vchart_map_sources', default=None)
svg_sources = ContextVar('vchart_svg_sources', default=None)


@contextmanager
def render_scope(backend, text_engine, context=None):
    a=settings.set((backend,text_engine));b=active_context.set(context)
    try:yield
    finally:active_context.reset(b);settings.reset(a)


@contextmanager
def resource_scope(maps,svgs):
    a=map_sources.set(maps);b=svg_sources.set(svgs)
    try:yield
    finally:svg_sources.reset(b);map_sources.reset(a)
