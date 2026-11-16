"""Keep bilateral lower-cheek colour on the moving facial shell."""

from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Scripts"))
from bake_digital_head import mandibular_undertone


class MandibularUndertoneTests(unittest.TestCase):
    def test_grade_wraps_smoothly_and_stops_before_ear_chin_and_neck(self):
        height = np.linspace(1.548, 1.600, 260)
        lateral = np.full_like(height, 0.039)
        depth = np.full_like(height, 0.0536)
        near = mandibular_undertone(lateral, height, depth)
        far = mandibular_undertone(-lateral, height, depth)
        np.testing.assert_equal(near, far)
        self.assertLess(abs(np.diff(near, axis=0)).max(), 0.006)
        upper, lower = near[np.searchsorted(height, [1.572, 1.561])]
        self.assertGreater(upper[1] - lower[1], 0.09)
        # Centre of chin, concha, neck, lip margin and upper face.
        fixed = np.array(
            [
                [0, 1.557, 0.073],
                [0.058, 1.609, 0.012],
                [0.034, 1.540, 0.051],
                [0.022, 1.586, 0.092],
                [0.05, 1.640, 0.049],
            ]
        )
        np.testing.assert_allclose(mandibular_undertone(*fixed.T), 0, atol=1e-12)
