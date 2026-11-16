"""Guard the shared lower-face sculpt, attachment, and local visibility masks."""

from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Scripts"))
from bake_digital_head import ear_ambient_visibility, jaw_and_neck_planes


class JawAndPinnaTests(unittest.TestCase):
    def test_lower_cheeks_taper_symmetrically_but_the_lip_and_high_cheeks_hold(self):
        pts = np.array(
            [
                [-0.054, 1.581, 0.061],
                [0.054, 1.581, 0.061],
                [0.061, 1.638, 0.068],
                [0, 1.583, 0.119],
                [0, 1.557, 0.108],
                [0.015, 1.519, 0.058],
            ]
        )
        d = jaw_and_neck_planes(pts)
        self.assertGreater(d[0, 0], 0.002)
        np.testing.assert_allclose(d[1], d[0] * [-1, 1, 1])
        np.testing.assert_allclose(d[[2, 3, 5]], 0, atol=1e-7)
        self.assertGreater(d[4, 2], 0.004)

    def test_occlusion_is_local_and_responds_to_real_nearby_occluders(self):
        # Receiver normal points laterally out from the ear. A separate sheet
        # covers that hemisphere. Far-away skin must not receive the ear AO.
        pts = np.array(
            [
                [0.075, 1.624, 0.014],
                [0, 1.64, 0.11],
                [0.078, 1.604, -0.006],
                [0.078, 1.644, -0.006],
                [0.078, 1.644, 0.034],
                [0.078, 1.604, 0.034],
            ]
        )
        norm = np.tile([1.0, 0.0, 0.0], (len(pts), 1))
        faces = np.array([[2, 3, 4], [2, 4, 5]])
        shadow = ear_ambient_visibility(pts, faces, norm)
        self.assertLess(shadow[0], 0.85)
        self.assertEqual(shadow[1], 1)
        pts[2:, 0] += 0.040
        self.assertEqual(ear_ambient_visibility(pts, faces, norm)[0], 1)
