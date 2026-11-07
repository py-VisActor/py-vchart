import json
from pathlib import Path
import unittest

from py_vchart import VChart


class MapRegistrationTests(unittest.TestCase):
    def setUp(self):
        case = Path(__file__).parent / "cases/map/joined"
        self.geo = json.loads((case / "geo.json").read_text())
        self.spec = json.loads((case / "spec.json").read_text())
        self.spec["map"] = "map-registration-test"

    def test_invalid_replacement_preserves_registered_geometry(self):
        VChart.register_map(self.spec["map"], self.geo)
        expected = VChart(self.spec).to_png()
        self.geo["features"][0]["geometry"]["coordinates"][0].reverse()
        with self.assertRaisesRegex(ValueError, "clockwise"):
            VChart.register_map(self.spec["map"], self.geo)
        self.assertEqual(VChart(self.spec).to_png(), expected)

    def test_unknown_source(self):
        with self.assertRaisesRegex(ValueError, "registered"):
            VChart(self.spec | {"map": "unregistered-test-region"}).render()
