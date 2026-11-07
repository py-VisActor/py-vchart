import json
import unittest
from importlib.util import find_spec
from pathlib import Path

from py_vchart import VChart
from py_vchart.chart.stat_panels import hexagons
from py_vchart.chart.swarm import swarm_offsets

CASES = Path(__file__).parent / "cases"


def sample(kind, name="first-frame"):
    return json.loads((CASES / kind / name / "spec.json").read_text(encoding="utf8"))


class StatisticalLayoutTests(unittest.TestCase):
    def test_hexagons_preserve_counts_under_reordering(self):
        rows = sample("hexbinPlot", "repeated-values")["data"]
        bins, domains, aspect = hexagons(rows, 8)
        self.assertEqual(sum(count for _, count in bins), len(rows))
        self.assertEqual(max(count for _, count in bins), 3)
        self.assertEqual(hexagons(rows[::-1], 8), (bins, domains, aspect))

    def test_swarm_ties_use_stable_identifiers(self):
        points = [(15, "b", 0), (15, "a", 1), (50, "c", 2)]
        offsets = swarm_offsets(points, 20)
        self.assertEqual(offsets, swarm_offsets(points[::-1], 20))
        self.assertEqual(offsets[1], offsets[2])
        self.assertGreaterEqual(abs(offsets[0] - offsets[1]), 7.49)


@unittest.skipUnless(
    find_spec("py_skia_canvas") and find_spec("skia"), "install render extras"
)
class StaticExtensionTests(unittest.TestCase):
    def test_pixel_sequence_defaults_and_frame_order(self):
        spec = sample("sequenceScatterPixel", "pixel-background")
        rows = spec["data"]["0"]
        spec["data"] = {"12": [], "2": rows}
        spec["backgroundColors"] = {"2": spec["backgroundColors"]["0"]}
        chart = VChart(spec).render()
        self.assertEqual(
            chart.to_png(),
            VChart(sample("sequenceScatterPixel", "pixel-background")).to_png(),
        )
        self.assertEqual(int.from_bytes(chart.to_png()[16:20], "big"), 300)

    def test_image_cloud_uses_current_data_on_rerender(self):
        spec = sample("imageCloud")
        chart = VChart(spec).render()
        self.assertEqual(len(chart.scene["marks"]["image"]), 5)
        spec["data"]["values"].clear()
        self.assertEqual(chart.render().scene["marks"]["image"], [])

    def test_pictogram_spec_does_not_mutate_registered_svg(self):
        spec = sample("pictogram")
        spec["svg"] = "transformed-test-source"
        VChart.register_svg_source(
            spec["svg"],
            '<svg viewBox="0 0 5 5"><g transform="scale(2)"><circle name="west" cx="1" cy="1" r="1" fill="#17a"/></g></svg>',
        )
        original = VChart(spec).to_png()
        recolored = VChart(spec | {"pictogram": {"style": {"fill": "red"}}}).to_png()
        self.assertNotEqual(original, recolored)
        self.assertEqual(original, VChart(spec).to_png())

    def test_pictogram_rejects_external_image(self):
        spec = sample("pictogram")
        spec["svg"] = "external-image-test"
        VChart.register_svg_source(
            spec["svg"],
            '<svg viewBox="0 0 10 10"><image href="https://example.invalid/no.png"/></svg>',
        )
        with self.assertRaisesRegex(ValueError, "embedded images"):
            VChart(spec).render()

    def test_mask_relayout_uses_current_data(self):
        spec = sample("wordCloud", "two-island-mask")
        chart = VChart(spec).render()
        old = chart.to_png()
        spec["data"]["values"].clear()
        self.assertEqual(chart.render().scene["marks"]["word"], [])
        self.assertNotEqual(chart.to_png(), old)

    def test_group_missing_from_a_panel_keeps_legend_color(self):
        spec = sample("pairPlot", "grouped-missing-series")
        first = VChart(spec).render()
        self.assertEqual(len(first.scene["marks"]["1.point"]), 4)
        spec["colors"]["categorical"].reverse()
        second = VChart(spec).render()
        self.assertEqual(first.scene, second.scene)
        self.assertNotEqual(first.to_png(), second.to_png())
