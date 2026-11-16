import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Scripts"))
from road_outline import boundary, rectangle


def perimeter(polygons):
    return sum(math.dist(a, b) for a, b in boundary(polygons))


class RoadOutlineTests(unittest.TestCase):
    def test_overlap_splits_edges_and_removes_hidden_foundations(self):
        road = rectangle(0, 0, 10, 2)
        court = rectangle(4, 0, 6, 6)
        self.assertAlmostEqual(perimeter([road, court]), 36)
        self.assertAlmostEqual(perimeter([court, road]), 36)

    def test_collinear_touching_decks_have_no_internal_wall(self):
        self.assertAlmostEqual(
            perimeter([rectangle(0, 0, 4, 2), rectangle(4, 0, 4, 2)]), 20
        )

    def test_identical_footprints_are_faced_once(self):
        self.assertAlmostEqual(
            perimeter([rectangle(0, 0, 4, 2), rectangle(0, 0, 4, 2)]), 12
        )

    def test_rotation_preserves_length(self):
        self.assertAlmostEqual(perimeter([rectangle(10, -6, 7, 2, 0.61)]), 18)
