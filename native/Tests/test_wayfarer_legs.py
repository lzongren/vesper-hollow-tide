from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Scripts"))
from wayfarer_legs import riding_legs


class RidingFitTest(unittest.TestCase):
    def test_bilateral_skinning_and_boot_roll(self):
        rest = {}
        soles, thighs, used = [], [], set()
        for side, suffix in ((1, "l"), (-1, "r")):
            for name, x, y, z in (
                ("thigh", 0.1, 0.96, 0),
                ("calf", 0.11, 0.50, 0.01),
                ("foot", 0.12, 0.08, 0),
                ("ball", 0.13, 0.02, 0.17),
            ):
                rest[name + "_" + suffix] = (side * x, y, z)

        def sample(slot, nu, nv, point):
            for i in range(nu + 1):
                for j in range(nv + 1):
                    _, _, weights = point(i / nu, j / nv)
                    self.assertAlmostEqual(sum(w for _, w in weights), 1)
                    self.assertGreaterEqual(min(w for _, w in weights), -1e-9)
                    used.update(bone for bone, w in weights if w > 0)
            if slot == "sole":
                heel, toe = point(0.75, 0), point(0.75, 1)
                self.assertGreater(toe[0][1], heel[0][1])
                self.assertGreater(heel[0][1], 0)
                self.assertEqual(heel[2][0][1], 1)
                self.assertEqual(toe[2][1][1], 1)
                soles.append(heel[0][0])
            if slot == "trouser":
                upper = [point(i / nu, 1)[0] for i in range(nu)]
                thighs.append(max(abs(p[0]) for p in upper))

        riding_legs(sample, rest, "trouser", "leather", "sole", "red", "gold")
        self.assertEqual(used, set(rest) | {"pelvis"})
        self.assertAlmostEqual(soles[0], -soles[1])
        self.assertTrue(all(x < 0.155 for x in thighs))
