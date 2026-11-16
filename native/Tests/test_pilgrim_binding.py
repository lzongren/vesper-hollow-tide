import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Scripts"))
from bind_pilgrim import align, rest_position, rotate


class PilgrimBindingTests(unittest.TestCase):
    def test_opposite_and_oblique_limb_rest_directions(self):
        source = (1, 0, 0)
        for target in [(-1, 0, 0), (0, 1, 0), (0.5, 0, math.sqrt(0.75))]:
            with self.subTest(target=target):
                for actual, expected in zip(rotate(align(source, target), source), target):
                    self.assertAlmostEqual(actual, expected)

    def test_scaled_rotated_inverse_bind_origin(self):
        matrix = [0, 2, 0, 0, -3, 0, 0, 0, 0, 0, 4, 0, 6, -2, -12, 1]
        self.assertEqual(rest_position(matrix), (1, 2, 3))
