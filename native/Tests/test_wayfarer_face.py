import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Scripts"))
from portrait_fit import ExpressionFit
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

    def test_portrait_field_keeps_neck_seam_and_mouth_stable_during_blink(self):
        fit = ExpressionFit(Path(__file__).resolve().parents[1] / "Art/Wayfarer")
        seam = (0.024, 1.51, 0.045)
        self.assertEqual(fit.warp(seam), seam)
        self.assertEqual(fit.warp(seam, opened=True), seam)
        mouth = (0.002, 1.60, 0.1)
        self.assertEqual(fit.warp(mouth), fit.warp(mouth, opened=True))
        eye = (-0.028, 1.66, 0.097)
        self.assertNotEqual(fit.warp(eye), fit.warp(eye, opened=True))

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
        colours = []

        def pawn(names):
            return SimpleNamespace(
                mesh=SimpleNamespace(
                    skeletal_mesh_asset=SimpleNamespace(
                        get_all_morph_target_names=lambda: names
                    ),
                    get_material_index=lambda name: 1 if name == "WayfarerSkin" else -1,
                    create_dynamic_material_instance=lambda i: SimpleNamespace(
                        set_scalar_parameter_value=lambda name, w: colours.append(
                            (name, w)
                        )
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
        self.assertEqual(colours, [("LidClosure", weight) for _, weight in weights])
        face.update(second, 1 / 60)
        self.assertEqual(face.index, 0)
        self.assertAlmostEqual(face.age, 1 / 60)
