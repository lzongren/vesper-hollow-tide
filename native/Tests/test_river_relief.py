"""Guard the playable corridor and the outside elevations when fitting the DEM."""

from array import array
import gzip
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Scripts"))
from river_relief import CENTER_COL, CENTER_ROW, DX, DZ, HEIGHT, WIDTH, ground_grid


class RiverReliefTests(unittest.TestCase):
    def test_route_stays_below_collision_while_far_peaks_keep_source_relief(self):
        asset = Path(__file__).resolve().parents[1] / "Art/RiverPeaks/Xingping.r16.gz"
        fitted = ground_grid(asset)
        raw = array("H")
        raw.frombytes(gzip.decompress(asset.read_bytes()))
        if sys.byteorder != "little":
            raw.byteswap()
        self.assertEqual(len(fitted), WIDTH * HEIGHT)
        for row in range(HEIGHT):
            x = (row - CENTER_ROW) * DX
            for col in range(WIDTH):
                z = (col - CENTER_COL) * DZ
                i = row * WIDTH + col
                if abs(x) <= 110 and abs(z) <= 60:
                    self.assertEqual(fitted[i], -12)
                if abs(z) >= 160:
                    self.assertAlmostEqual(fitted[i], (raw[i] * 0.1 - 113) * 0.155 - 6)

    def test_short_height_field_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "river.r16.gz"
            path.write_bytes(gzip.compress(bytes(4)))
            with self.assertRaisesRegex(ValueError, "dimensions"):
                ground_grid(path)
