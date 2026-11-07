"""Python implementation of VisActor VChart."""

from importlib.metadata import version

__version__ = version("py-visactor-vchart")

from .core import VChart

__all__ = ["VChart", "__version__"]
