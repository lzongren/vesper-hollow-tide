import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Scripts"))
from scalp_fit import scalp_radius
from wayfarer_blink import Blink, lid_delta


class FacialFittingTests(unittest.TestCase):
    def test_lids_meet_without_moving_the_brows_or_cheek(self):
        for x in (-0.31, 0.31):
            top = lid_delta(x, 7.332, 1.405)
            lower = lid_delta(x, 7.240, 1.401)
            self.assertLess(abs(0.103 * (7.332 - 7.240) + top[1] - lower[1]), 0.001)
            self.assertEqual(lid_delta(x, 7.61, 1.4), (0, 0, 0))
            self.assertEqual(lid_delta(x, 7.08, 1.4), (0, 0, 0))

    def test_hair_seats_on_outer_surface(self):
        vertices = [
            (-1, 7, 0),
            (1, 7, 0),
            (1, 7, 2),
            (-1, 7, 2),
            (-1, 9, 0),
            (1, 9, 0),
            (1, 9, 2),
            (-1, 9, 2),
        ]
        sides = [[0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]
        fitted = scalp_radius(vertices, sides)
        self.assertAlmostEqual(fitted(0, 7.93, 3), 1.44)
        self.assertAlmostEqual(fitted(-1e-20, 7.93, 3), 1.44)
        self.assertEqual(fitted(0, 9.8, 3), 3)

    def test_blink_reopens_and_restarts_on_respawn(self):
        weights = []

        def pawn(names):
            return SimpleNamespace(
                mesh=SimpleNamespace(
                    skeletal_mesh_asset=SimpleNamespace(
                        get_all_morph_target_names=lambda: names
                    ),
                    set_morph_target=lambda n, w: weights.append((n, w)),
                )
            )

        face = Blink()
        first, second = pawn(["Blink"]), pawn(["Blink"])
        for _ in range(250):
            face.update(first, 1 / 60)
        self.assertEqual(weights[-1], ("Blink", 0.0))
        self.assertEqual(max(w for _, w in weights), 1.0)
        face.update(second, 1 / 60)
        self.assertEqual(face.index, 0)
        self.assertAlmostEqual(face.age, 1 / 60)
