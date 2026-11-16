import json
from pathlib import Path
import sys
import unittest

NATIVE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(NATIVE / "Scripts"))
from camellia_face import projection
from camellia_lids import aperture, blink_delta


class CamelliaHeadTest(unittest.TestCase):
    def test_sculpt_keeps_neck_seam_and_eye_sockets_registered(self):
        art = NATIVE / "Art" / "Wayfarer"
        points = json.loads((art / "head.json").read_text())["vertices"]
        deltas = json.loads((art / "camellia-head.json").read_text())
        self.assertEqual(len(points), len(deltas))
        for p, delta in zip(points, deltas):
            if p[1] <= 5.86:
                self.assertEqual(delta, [0, 0, 0])
        for side in (-1, 1):
            lids = [
                (p, d)
                for p, d in zip(points, deltas)
                if 0.29 < p[0] * side < 0.34 and 7.23 < p[1] < 7.35 and p[2] > 1.37
            ]
            self.assertGreater(len(lids), 4)
            for axis in (1, 2):
                self.assertLess(abs(sum(d[axis] for _, d in lids) / len(lids)), 0.003)

    def test_skin_projection_straddles_lash_fringe_and_registers_lips(self):
        for side in (-1, 1):
            upper = projection(side * 0.31, 7.332)[1]
            lower = projection(side * 0.31, 7.240)[1]
            self.assertLess(upper, 0.45)
            self.assertGreater(lower, 0.467)
        self.assertAlmostEqual(projection(0, 6.604)[1], 0.688)

    def test_open_eye_closes_at_the_centre_of_each_lid(self):
        for x in (-0.31, 0.31):
            rest, closed = [], []
            for y in (7.332, 7.240):
                z = 1.405
                height = 0.103 * (y + (y - 7.274) * aperture(x, y, z))
                rest.append(height)
                closed.append(height + blink_delta(x, y, z)[1])
            self.assertTrue(0.0118 < rest[0] - rest[1] < 0.0126)
            self.assertLess(abs(closed[0] - closed[1]), 0.001)
