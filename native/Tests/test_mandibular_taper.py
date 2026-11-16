"""Regress the lower cheek roll independently of the ear and chin sculpts."""

from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Scripts"))
from bake_digital_head import mandibular_taper


class MandibularTaperTests(unittest.TestCase):
    def test_underside_turns_in_below_the_ridge_and_releases_at_the_neck(self):
        for z in (0.048, 0.054, 0.060):
            # Cross the registered line at several stations from ear to chin.
            along = z - 0.060
            ridge = 1.5638 - 0.539 * along + 3.88 * along**2
            levels = (0.014, 0.010, 0.006, 0.002, 0, -0.004, -0.009, -0.028)
            samples = np.array([[-0.044, ridge + h, z] for h in levels])
            d = mandibular_taper(samples)
            self.assertLess(d[0, 0], 0.002)
            # At this lateral station the upper jaw stays shallow, while
            # the lower section rolls inward over the next nine millimetres.
            self.assertLess(d[4, 0], 0.0025)
            self.assertGreater(d[5, 0], d[4, 0] + 0.0014)
            self.assertGreater(d[6, 0], d[5, 0] + 0.002)
            # No sharp shelf in any 4 mm interval across the roll.
            rate = np.diff(d[:7, 0]) / np.diff(levels[:7])
            self.assertLess(np.max(np.abs(rate)), 0.55)
            self.assertGreater(d[6, 0], 0.005)
            self.assertLess(d[7, 0], 0.001)
            mirror = np.array([-1, 1, 1])
            np.testing.assert_allclose(mandibular_taper(samples * mirror), d * mirror)

    def test_chin_mouth_upper_cheek_and_neck_collar_stay_fixed(self):
        protected = np.array(
            [
                [0.011, 1.557, 0.122],  # forward mental pad
                [0.013, 1.584, 0.124],  # lower lip
                [-0.060, 1.632, 0.081],  # malar prominence
                [-0.073, 1.623, 0.014],  # pinna
                [-0.049, 1.528, 0.036],  # neck ring
            ]
        )
        np.testing.assert_array_equal(mandibular_taper(protected), 0)
        turn = mandibular_taper(np.array([[-0.046, 1.591, 0.098]]))[0]
        self.assertGreater(turn[0], 0.001)
        self.assertLess(turn[2], -0.001)
        self.assertEqual(turn[1], 0)
