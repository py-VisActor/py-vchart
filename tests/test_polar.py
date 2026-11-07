import io
import json
import sys
import unittest
from importlib.util import find_spec
from pathlib import Path

from py_vchart import VChart

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(find_spec("py_skia_canvas") and find_spec("PIL"), "install render and test extras")
class PolarRegressionTests(unittest.TestCase):
    def test_visual_comparator_rejects_geometry_faults(self):
        from unittest.mock import patch
        from PIL import Image, ImageDraw
        from py_vchart._deps.vrender import Surface

        sys.path.insert(0, str(ROOT / "tools/visual"))
        self.addCleanup(sys.path.pop, 0)
        from pixels import compare, passes

        for kind, case, fault in [
            ("pie", "partial", "reverse"), ("pie", "ring", "hole"),
            ("gauge", "basic", "pointer"), ("radar", "basic", "closure"),
            ("liquid", "basic", "overflow"),
        ]:
            with self.subTest(fault=fault):
                folder = ROOT / "tests/cases" / kind / case
                spec = json.loads((folder / "spec.json").read_text())
                if fault == "reverse":
                    spec["startAngle"], spec["endAngle"] = spec["endAngle"], spec["startAngle"]
                elif fault == "hole":
                    spec["innerRadius"] = 0
                if fault == "closure":
                    original = Surface.polyline
                    with patch.object(Surface, "polyline", lambda s, pts, *args: original(s, pts[:-1], *args)):
                        data = VChart(spec).to_png()
                else:
                    data = VChart(spec).to_png()
                with Image.open(io.BytesIO(data)) as candidate, Image.open(folder / "expected.png") as reference:
                    if fault == "pointer":
                        box = (130, 90, 230, 190)
                        candidate.paste(candidate.crop(box), (134, 90))
                    elif fault == "overflow":
                        ImageDraw.Draw(candidate).rectangle((30, 195, 88, 215), fill="#1664ff")
                    metrics, _ = compare(reference, candidate)
                    self.assertFalse(passes(metrics))
