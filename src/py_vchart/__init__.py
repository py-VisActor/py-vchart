"""Python implementation of VisActor VChart."""

from importlib.metadata import version

__version__ = version("py-visactor-vchart")

from .core import VChart, supported_types

__all__ = ["VChart", "supported_types", "__version__"]
