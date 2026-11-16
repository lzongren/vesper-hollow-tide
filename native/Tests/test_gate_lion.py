"""Check the channels and fit consumed by the Unreal guardian material."""

from pathlib import Path
import sys
import unittest
import wave

NATIVE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(NATIVE / "Scripts"))
from bind_pilgrim import Glb


class GateLionTests(unittest.TestCase):
    def test_eave_wind_is_a_spatial_mono_loop(self):
        with wave.open(str(NATIVE / "Art/BellCourt/EaveWind.wav")) as loop:
            self.assertEqual(loop.getnchannels(), 1)
            self.assertEqual(loop.getsampwidth(), 2)
            self.assertEqual(loop.getnframes(), 31 * loop.getframerate())
            first = int.from_bytes(loop.readframes(1), "little", signed=True)
            loop.setpos(loop.getnframes() - 1)
            last = int.from_bytes(loop.readframes(1), "little", signed=True)
            self.assertLess(abs(first - last), 1024)

    def test_casting_seats_on_foot_and_carries_local_finish(self):
        model = Glb(NATIVE / "Art/BellCourt/GateLion.glb")
        parts = {m["name"]: m["primitives"][0] for m in model.doc["meshes"]}
        self.assertEqual(set(parts), {"CastLion", "CarvedFoot"})
        cast, stone = (parts[name]["attributes"] for name in ("CastLion", "CarvedFoot"))
        bounds = model.doc["accessors"]
        shape, foot = (bounds[a["POSITION"]] for a in (cast, stone))
        self.assertLess(shape["min"][1], foot["max"][1])
        self.assertGreater(shape["max"][1], 3.0)
        self.assertLess(shape["max"][1], 3.2)
        for dim in (0, 2):
            self.assertLess(foot["min"][dim], shape["min"][dim])
            self.assertGreater(foot["max"][dim], shape["max"][dim])
        self.assertEqual(bounds[cast["COLOR_0"]]["count"], shape["count"])
        masks = model.values(cast["TEXCOORD_0"])
        self.assertTrue(all(0 <= r <= 1 and 0 <= m <= 1 for r, m in masks))
        self.assertGreater(max(m for _, m in masks) - min(m for _, m in masks), 0.3)
