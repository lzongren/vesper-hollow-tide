import math
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Scripts"))
from court_face import CourtFace
from scalp_fit import fit_hair_margin
from digital_head import head_weight, neck_section, skin_reflectance


class DigitalHeadTest(unittest.TestCase):
    def test_menton_follows_the_head_while_throat_and_collar_keep_their_blend(self):
        self.assertEqual(head_weight((0, 1.541, 0.11)), 1)
        self.assertAlmostEqual(head_weight((0, 1.541, 0.052)), (1.541 - 1.512) / 0.045)
        self.assertAlmostEqual(head_weight((0.024, 1.52, 0.09)), (1.52 - 1.512) / 0.045)

    def test_throat_pigment_crosses_neck_join_and_spares_the_lips(self):
        forward = (0, 0, 1)
        across = [skin_reflectance((0, y, 0.056), forward) for y in (1.519, 1.521)]
        for left, right in zip(*across):
            self.assertAlmostEqual(left, right, places=3)
        self.assertLess(across[0][0], across[0][1])
        for channel in skin_reflectance((0, 1.588, 0.112), forward):
            self.assertAlmostEqual(channel, 1, places=3)

    def test_chin_underside_keeps_more_warmth_than_the_forward_facing_skin(self):
        tip = (0, 1.55, 0.113)
        face = skin_reflectance(tip, (0, 0, 1))
        underside = skin_reflectance(tip, (0, -1, 0))
        self.assertLess(underside[2], underside[0])
        self.assertLess(underside[0], face[0])

    def test_roots_follow_the_margin_past_the_ear_on_either_side(self):
        def cap(a, row):
            # A lower section crosses the helix and suddenly widens.
            radius = 0.10 + 0.02 * math.exp(-(((row - 0.05) / 0.01) ** 2))
            return (
                radius * math.sin(a),
                1.65 + row * 0.15,
                0.025 + radius * math.cos(a),
            )

        surface = fit_hair_margin(cap, lambda _: 0.10)
        for angle in (-1.90, 1.90):
            root, middle, tip = (surface(angle, row) for row in (0.10, 0.075, 0.05))
            self.assertLess(tip[1], root[1])
            self.assertAlmostEqual(math.dist(tip, root), 0.05 * 0.153, places=5)
            for r, m, t in zip(root, middle, tip):
                self.assertAlmostEqual(m, (r + t) / 2, places=7)
        self.assertEqual(surface(0, 0.05), cap(0, 0.05))

    def test_neckline_has_a_continuous_front_and_back(self):
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
