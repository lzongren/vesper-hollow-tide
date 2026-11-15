"""The carved panel must have actual depth and outward normals at the feather edges."""

from pathlib import Path
import sys
import tempfile
import unittest

NATIVE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(NATIVE / "Scripts"))
from bind_pilgrim import Glb, cross, unit
from egret_screen import bake


class EgretScreenTest(unittest.TestCase):
    def test_displacement_and_normals_match_the_front_of_the_screen(self):
        art = NATIVE / "Art" / "BellCourt"
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            # The source-tool test only needs valid image buffers for the frame.
            # The actual face, carving grid and normal atlas are the shipped assets.
            for name in ("rock-color", "rock-normal", "stone-color", "stone-normal"):
                (directory / (name + ".jpg")).write_bytes(
                    (art / "EgretClay.jpg").read_bytes()
                )
            output = directory / "BellEgretScreen.glb"
            bake(directory, art, output)
            model = Glb(output)
        mesh = model.doc["meshes"][0]
        self.assertEqual(mesh["name"], "BellEgretScreen")
        panel = next(
            p
            for p in mesh["primitives"]
            if model.doc["materials"][p["material"]]["name"] == "EgretBrickCarving"
        )
        pos = model.values(panel["attributes"]["POSITION"])
        normals = model.values(panel["attributes"]["NORMAL"])
        self.assertEqual(len(pos), 257 * 129)
        self.assertGreater(max(p[0] for p in pos) - min(p[0] for p in pos), 0.045)
        minus = lambda a, b: tuple(x - y for x, y in zip(a, b))
        for j in range(1, 128, 7):
            for i in range(1, 256, 7):
                k = j * 257 + i
                normal = unit(
                    cross(
                        minus(pos[k + 257], pos[k - 257]), minus(pos[k + 1], pos[k - 1])
                    )
                )
                self.assertLess(normal[0], 0)
                self.assertGreater(
                    sum(a * b for a, b in zip(normal, normals[k])), 0.999
                )
