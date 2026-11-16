from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Scripts"))
from portrait_subdivision import refine


class PortraitSubdivisionTest(unittest.TestCase):
    def test_shared_edge_and_eyelid_boundary(self):
        points = [(x, y, 0) for y in (0, 1) for x in (0, 1, 2)]
        fitted, quads = refine(points, [[0, 1, 4, 3], [1, 2, 5, 4]])
        self.assertEqual(len(fitted), 15)
        self.assertEqual(len(quads), 8)
        self.assertEqual(fitted[0], (0.125, 0.125, 0))
        self.assertEqual(fitted[1], (1, 0, 0))
        shared = fitted.index((1, 0.5, 0))
        self.assertEqual(sum(shared in quad for quad in quads), 4)
