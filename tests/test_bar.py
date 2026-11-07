import json
import sys
import tempfile
import unittest
from importlib.util import find_spec
from pathlib import Path

from py_vchart import VChart
from py_vchart._deps.vscale import bands, numeric_axis

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "tests/cases/bar/signed-baseline"


def spec():
    return json.loads((CASE / "spec.json").read_text())


class ScaleTests(unittest.TestCase):
    def test_single_category_is_centered(self):
        self.assertEqual(bands(["A"], 160)["A"], (35, 90))

    def test_signed_numeric_domain(self):
        self.assertEqual(numeric_axis([-3, 8], {}), ([-3, 9], [-3, 0, 3, 6, 9]))


@unittest.skipUnless(find_spec("py_skia_canvas"), "install render extra")
class BarTests(unittest.TestCase):
    def test_repeated_render_and_ignored_dynamic_configuration(self):
        source = spec()
        chart = VChart(source)
        original = chart.to_png()
        source.update(tooltip={"visible": True}, animation=True, hover=True)
        self.assertEqual(original, chart.render().to_png())
        source["data"][0]["values"] = []
        self.assertEqual(chart.render().to_png(), VChart(source).to_png())
        self.assertEqual(chart.scene["bars"], [])

    def test_style_changes_pixels_without_changing_geometry(self):
        plain = VChart(spec()).render()
        colored = VChart(spec() | {"bar": {"style": {"fill": "#ff0000"}}}).render()
        self.assertEqual(colored.scene, plain.scene)
        self.assertNotEqual(colored.to_png(), plain.to_png())

    def test_static_unsupported_option_is_diagnosed(self):
        for extra, message in [({"stack": True}, "bar.stack"), ({"axes": None}, "bar.axes"),
                               ({"label": {"visible": True}}, "bar.label"),
                               ({"bar": {"style": {"opacity": 0.2}}}, "bar.bar.style.opacity")]:
            with self.subTest(extra=extra), self.assertRaisesRegex(ValueError, message):
                VChart(spec() | extra).render()


@unittest.skipUnless(find_spec("py_skia_canvas") and find_spec("PIL"), "install render and test extras")
class OracleTests(unittest.TestCase):
    def test_visual_cases(self):
        sys.path.insert(0, str(ROOT / "tools/visual"))
        self.addCleanup(sys.path.pop, 0)
        from check_cartesian import run_batch
        from py_vchart.core import RENDERERS
        with tempfile.TemporaryDirectory() as directory:
            self.assertTrue(run_batch(Path(directory), RENDERERS))

    def test_visual_comparator_detects_bar_faults(self):
        sys.path.insert(0, str(ROOT / "tools/visual"))
        self.addCleanup(sys.path.pop, 0)
        from PIL import Image, ImageDraw
        from pixels import compare, passes
        with Image.open(CASE / "expected.png") as expected:
            box = (85, 40, 206, 154)
            for fault in ("removed", "recolored", "shifted"):
                with self.subTest(fault=fault):
                    actual = expected.copy()
                    ImageDraw.Draw(actual).rectangle(box, fill="red" if fault == "recolored" else "white")
                    if fault == "shifted":
                        actual.paste(expected.crop(box), (box[0] + 1, box[1]))
                    metrics, _ = compare(expected, actual)
                    self.assertFalse(passes(metrics))
