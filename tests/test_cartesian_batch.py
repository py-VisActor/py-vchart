import json
import unittest
from importlib.util import find_spec
from pathlib import Path

from py_vchart import VChart

CASES = Path(__file__).resolve().parent / "cases"


def spec(kind, case):
    return json.loads((CASES / kind / case / "spec.json").read_text())


@unittest.skipUnless(find_spec("py_skia_canvas"), "install render extra")
class CartesianBatchTests(unittest.TestCase):
    def test_secondary_scale_recomputes_without_changing_bar_domain(self):
        data = spec("common", "right-axis")
        chart = VChart(data).render()
        before = chart.scene["axes"]
        data["data"]["values"][0]["hi"] = 800
        chart.render()
        self.assertEqual(before[1]["domain"], chart.scene["axes"][1]["domain"])
        self.assertNotEqual(before[2]["domain"], chart.scene["axes"][2]["domain"])
        self.assertEqual(chart.to_png(), VChart(data).to_png())

    def test_stacks_keep_independent_positive_and_negative_totals(self):
        chart = VChart(spec("bar", "stacked")).render()
        boxes = chart.scene["bars"]
        self.assertAlmostEqual(boxes[0][1], boxes[1][3])
        self.assertAlmostEqual(boxes[2][3], boxes[3][1])
        self.assertAlmostEqual(boxes[4][3], boxes[5][1])

    def test_bin_width_follows_interval(self):
        boxes = VChart(spec("histogram", "basic")).render().scene["marks"]["bar"]
        widths = [right-left for left, _, right, _ in boxes]
        self.assertAlmostEqual(widths[1], 2*widths[0])
        self.assertAlmostEqual(widths[2], 3*widths[0])

    def test_empty_waterfall_has_total_and_no_delta(self):
        chart = VChart(spec("waterfall", "empty")).render()
        self.assertEqual(chart.scene["axes"][0]["domain"], ["total"])
        box, = chart.scene["marks"]["bar"]
        self.assertEqual(box[1], box[3])
