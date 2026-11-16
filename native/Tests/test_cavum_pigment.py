"""Regression for the blue-green scan pigment exposed under the tragus."""

from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Scripts"))
from bake_digital_head import correct_cavum_pigment


class CavumPigmentTests(unittest.TestCase):
    def test_exposed_ear_patch_inherits_cartilage_hue_at_its_own_brightness(self):
        atlas = np.empty((512, 512, 3), dtype=np.uint8)
        atlas[:] = [180, 125, 121]
        ear_pixels = [(234, 91), (233, 420)]
        for location in [*ear_pixels, (255, 255)]:
            atlas[location] = [84, 115, 120]

        fixed = correct_cavum_pigment(atlas.copy())
        changed = {tuple(yx) for yx in np.argwhere(np.any(fixed != atlas, axis=2))}
        self.assertEqual(changed, set(ear_pixels))
        luma = np.array([0.2126, 0.7152, 0.0722])
        for location in ear_pixels:
            rgb = fixed[location].astype(float)
            self.assertGreater(rgb[0] - rgb[1], 45)
            self.assertLess(abs((rgb - atlas[location]) @ luma), 1)
