import json
import tempfile
import unittest
from importlib.util import find_spec
from pathlib import Path

from py_vchart import VChart

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "tests/cases/line"


@unittest.skipUnless(find_spec("py_skia_canvas"), "install render extra")
class LineTests(unittest.TestCase):
    def test_gap_keeps_category_but_splits_path(self):
        spec = json.loads((CASES / "gaps/spec.json").read_text())
        del spec["data"]["values"][1]["y"]
        chart = VChart(spec).render()
        self.assertEqual(chart.scene["axes"][0]["domain"], list("ABCDEF"))
        self.assertEqual([len(path) for path in chart.scene["segments"]], [1, 2, 1])
        self.assertEqual(len(chart.scene["points"]), 4)
        with self.assertRaisesRegex(ValueError, "bar.data"):
            VChart(spec | {"type": "bar"}).render()

    def test_switch_series_on_same_chart(self):
        spec = json.loads((CASES / "single/spec.json").read_text())
        chart = VChart(spec).render()
        line = chart.to_png()
        spec["type"] = "bar"
        self.assertEqual(chart.render().to_png(), VChart(spec).to_png())
        self.assertIn("bars", chart.scene)
        spec["type"] = "line"
        self.assertEqual(chart.render().to_png(), line)

    def test_unsupported_curve_is_identified(self):
        spec = json.loads((CASES / "basic-demo/spec.json").read_text())
        spec["line"] = {"style": {"curveType": "monotone"}}
        with self.assertRaisesRegex(ValueError, r"line\.line\.style\.curveType"):
            VChart(spec).render()
