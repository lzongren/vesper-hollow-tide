from pathlib import Path
import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Scripts"))
from court_face import CourtFace
from digital_head import neck_section


class DigitalHeadTest(unittest.TestCase):
    def test_neckline_has_a_continuous_front_and_back(self):
        import math

        points = [
            (
                0.05 * math.sin(i * math.tau / 24),
                y,
                0.04 * math.cos(i * math.tau / 24) - 0.012,
            )
            for y in (1.50, 1.54)
            for i in range(24)
        ]
        triangles = []
        for i in range(24):
            j = (i + 1) % 24
            triangles.extend([(i, j, 24 + i), (j, 24 + j, 24 + i)])
        rim = neck_section(points, triangles)
        self.assertEqual(len(rim), 120)
        self.assertAlmostEqual(rim[0][2], 0.028)
        self.assertAlmostEqual(rim[30][0], 0.05)
        self.assertAlmostEqual(rim[60][2], -0.052)
        self.assertTrue(all(abs(v[1] - 1.52) < 1e-8 for v in rim))

    def test_exertion_follows_actual_attack_and_settles_on_release(self):
        channels = {}
        anim = SimpleNamespace(
            get_current_active_montage=lambda: "attack",
            montage_get_position=lambda _: 0.2,
        )
        mesh = SimpleNamespace(
            skeletal_mesh_asset=SimpleNamespace(
                get_all_morph_target_names=lambda: ["JawOpen", "Focus"]
            ),
            get_anim_instance=lambda: anim,
            set_morph_target=channels.__setitem__,
        )
        pawn = SimpleNamespace(
            mesh=mesh, get_velocity=lambda: SimpleNamespace(length=lambda: 0)
        )
        face = CourtFace()
        for _ in range(30):
            face.update(pawn, True, 1 / 60)
        self.assertGreater(channels["JawOpen"], 0.20)
        self.assertGreater(channels["Focus"], 0.45)
        anim.get_current_active_montage = lambda: None
        for _ in range(60):
            face.update(pawn, None, 1 / 60)
        self.assertLess(channels["JawOpen"], 0.03)
        self.assertLess(channels["Focus"], 0.04)
