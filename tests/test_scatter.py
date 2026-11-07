import json
import unittest
from importlib.util import find_spec
from pathlib import Path

from py_vchart import VChart

CASES = Path(__file__).resolve().parent / "cases/scatter"


def load(name):
    return json.loads((CASES / name / "spec.json").read_text())


@unittest.skipUnless(find_spec("py_skia_canvas"), "install render extra")
class ScatterTests(unittest.TestCase):
    def test_numeric_spacing_requires_linear_axis(self):
        band = VChart(load("signed")).render().scene
        linear = VChart(load("dual-linear")).render().scene
        self.assertEqual(band["axes"][0]["domain"], [-3, 0, 2, 8])
        self.assertEqual(linear["axes"][0]["domain"], [-3, 9])
        self.assertNotEqual(band["points"], linear["points"])

    def test_overlap_keeps_both_observations(self):
        spec = load("overlap")
        chart = VChart(spec).render()
        self.assertEqual(chart.scene["points"][0], chart.scene["points"][1])
        original = chart.to_png()
        del spec["data"]["values"][0]
        self.assertNotEqual(chart.render().to_png(), original)
        self.assertEqual(chart.to_png(), VChart(spec).to_png())

    def test_unsupported_and_invalid_encodings(self):
        for extra, path in [({"sizeField": "z"}, "scatter.sizeField"),
                            ({"point": {"style": {"fillOpacity": -1}}}, "scatter.point.style.fillOpacity")]:
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, path):
                VChart(load("signed") | extra).render()
