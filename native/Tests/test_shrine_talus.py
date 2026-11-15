import sys
import unittest
from collections import defaultdict
from math import cos, pi, sin
from pathlib import Path
from tempfile import TemporaryDirectory

NATIVE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(NATIVE / "Scripts"))
from bind_pilgrim import Glb
from ravine_vegetation import plant
from shrine_talus import build, toes


class ShrineTalusTest(unittest.TestCase):
    def test_cliff_footprints_use_actor_transform(self):
        path = NATIVE / "Art/ShrineCliffWalk.glb"
        a = toes(path, lambda x, y: (x, y))
        b = toes(path, lambda x, y: (5 - y, 3 + x))
        self.assertEqual(len(a), 8)
        for ring, mapped in zip(a, b):
            self.assertGreaterEqual(len(set(ring)), 8)
            self.assertEqual(mapped, [(5 - y, 3 + x) for x, y in ring])

    def test_walkable_surface_and_planting_respect_open_lane(self):
        ring = [(10 * cos(i * pi / 18), 10 * sin(i * pi / 18)) for i in range(36)]

        def ground(x, y):
            return 0.042 * x + 0.073 * y - 1.6

        def clearance(x, y):
            return abs(y) - 2

        with TemporaryDirectory() as d:
            p = Path(d) / "bank.glb"
            groups, sample = build([ring], ground, clearance, p)
            first = p.read_bytes()
            self.assertEqual(groups, build([ring], ground, clearance, p)[0])
            self.assertEqual(first, p.read_bytes())
            data = Glb(p)
            attrs = data.doc["meshes"][0]["primitives"][0]["attributes"]
            verts = data.values(attrs["POSITION"])
            self.assertTrue(any(h > ground(x, y) + 0.4 for x, h, y in verts))
            for x, h, y in verts:
                self.assertAlmostEqual(sample(x, y)[0], max(h, ground(x, y)), places=4)
            self.assertGreater(len(groups[6]), 5)
            for i, instances in groups.items():
                for x, y, z, _, _, _, scale in instances:
                    self.assertGreaterEqual(clearance(x, y), 1.3)
                    self.assertAlmostEqual(
                        z + (0.024 if i == 6 else 0.12 * scale), sample(x, y)[0]
                    )
            for x in range(-15, 16):
                self.assertEqual(sample(x, 0), (ground(x, 0), 0))

    def test_verge_roots_fit_the_ground_and_leave_the_stair_open(self):
        def ground(x, y):
            return 0.06 * x + 0.13 * y, 0

        def clear(x, y):
            return abs(x - 194) - 2.4

        groups = defaultdict(list)
        plant(groups, ground, clear, (201, -49))
        self.assertTrue(all(groups[i] for i in range(7, 17)))
        for index in range(7, 17):
            for x, y, z, *_ in groups[index]:
                self.assertGreaterEqual(clear(x, y), 0.32)
                self.assertAlmostEqual(z + 0.012, ground(x, y)[0])

    def test_each_scanned_grass_clump_has_fixed_roots_and_moving_tips(self):
        for name in ("RavineGrass", "RavineFlower"):
            scan = Glb(NATIVE / "Art" / "ShrineTalus" / (name + ".glb"))
            self.assertEqual(len(scan.doc["nodes"]), 5)
            for mesh in scan.doc["meshes"]:
                attrs = mesh["primitives"][0]["attributes"]
                weights = [c[1] for c in scan.values(attrs["COLOR_0"])]
                self.assertLess(min(weights), 0.02)
                self.assertGreater(max(weights), 0.98)
            texture = scan.doc["materials"][0]["pbrMetallicRoughness"][
                "baseColorTexture"
            ]["index"]
            im = scan.doc["images"][scan.doc["textures"][texture]["source"]]
            self.assertEqual(im["mimeType"], "image/png")
            self.assertEqual(scan.view(im["bufferView"])[25], 6)  # PNG colour type RGBA
