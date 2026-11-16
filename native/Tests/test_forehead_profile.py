from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Scripts"))
from bake_digital_head import (
    cheek_volume,
    fit_rest_pose,
    portrait_contour,
    portrait_skin_coverage,
)


class ForeheadProfileTest(unittest.TestCase):
    def test_rest_mesh_has_a_convex_lower_forehead_and_receding_upper_plane(self):
        registered = np.array([[0, 1.680, 0.120], [0, 1.695, 0.119], [0, 1.711, 0.115]])
        baseline = registered + portrait_contour(registered) + cheek_volume(registered)
        result = fit_rest_pose(registered, "head")
        delta = result - baseline
        np.testing.assert_array_equal(delta[:, :2], 0)
        self.assertGreater(delta[0, 2], 0.0014)
        self.assertLess(abs(delta[1, 2]), 0.00025)
        self.assertLess(delta[2, 2], -0.0015)

    def test_brow_eye_cheek_lips_and_posterior_scalp_keep_their_existing_fit(self):
        registered = np.array(
            [
                [0.030, 1.681, 0.111],
                [-0.030, 1.681, 0.111],
                [0, 1.663, 0.119],
                [0.062, 1.601, 0.063],
                [0, 1.585, 0.123],
                [0, 1.712, -0.042],
            ]
        )
        baseline = registered + portrait_contour(registered) + cheek_volume(registered)
        np.testing.assert_array_equal(fit_rest_pose(registered, "head"), baseline)

    def test_non_head_parts_do_not_receive_the_forehead_displacement(self):
        registered = np.array([[0, 1.680, 0.120], [0, 1.711, 0.115]])
        baseline = registered + portrait_contour(registered)
        for part in ("eyeLeft", "eyeRight", "teeth", "cartilage", "eyelashes"):
            with self.subTest(part=part):
                np.testing.assert_array_equal(fit_rest_pose(registered, part), baseline)

    def test_guide_hair_at_both_temples_is_excluded_from_the_skin_pigment(self):
        # The ray from the three-quarter camera lands in dressed hair at
        # (359, 334). The opposite temple has a different hairline curve.
        x = np.array([359, 353, 930, 951])
        y = np.array([334, 378, 334, 378])
        np.testing.assert_array_equal(portrait_skin_coverage(x, y), 0)

    def test_guide_brows_lids_central_forehead_and_cheek_keep_their_pigment(self):
        x = np.array([414, 845, 481, 775, 630, 440])
        y = np.array([443, 443, 547, 547, 391, 683])
        np.testing.assert_array_equal(portrait_skin_coverage(x, y), 1)

    def test_hair_to_skin_blend_is_continuous_across_the_traced_hairline(self):
        x = np.array([367, 375, 383, 884, 876, 868])
        np.testing.assert_allclose(
            portrait_skin_coverage(x, np.full(6, 410)), [0, 0.5, 1, 0, 0.5, 1]
        )


if __name__ == "__main__":
    unittest.main()
