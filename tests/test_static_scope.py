import unittest

from py_vchart import VChart
from py_vchart.core import RENDERERS


class StaticScopeTests(unittest.TestCase):
    def test_registered_types_are_two_dimensional(self):
        self.assertIn("wordCloud", RENDERERS)
        self.assertFalse(any(kind.lower().endswith("3d") for kind in RENDERERS))

    def test_upstream_3d_types_are_rejected(self):
        for kind in ("bar3d", "rangeColumn3d", "histogram3d", "pie3d", "funnel3d", "wordCloud3d"):
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, "Unsupported chart type"):
                VChart({"type": kind}).render()
