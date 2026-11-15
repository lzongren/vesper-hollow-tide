"""Guard the playable corridor and the outside elevations when fitting the DEM."""

from array import array
import gzip
import math
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Scripts"))
from river_relief import (
    CENTER_COL,
    CENTER_ROW,
    DX,
    DZ,
    HEIGHT,
    WIDTH,
    ground_grid,
    terrain_sample,
    forest,
)


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

    def test_roots_use_the_same_diagonal_as_the_terrain_mesh(self):
        field = [0.0] * (2 * WIDTH)
        field[1], field[WIDTH], field[WIDTH + 1] = 2, 8, 13
        for row, col, height, dx, dz in (
            (0.25, 0.75, 4.25, 11, 2),
            (0.75, 0.25, 7.25, 8, 5),
        ):
            root, up = terrain_sample(field, row, col)
            self.assertAlmostEqual(root, height)
            self.assertAlmostEqual(
                up, 1 / math.sqrt(1 + (dx / DX) ** 2 + (dz / DZ) ** 2)
            )

    def test_wooded_slopes_leave_the_playable_corridor_clear(self):
        asset = Path(__file__).resolve().parents[1] / "Art/RiverPeaks/Xingping.r16.gz"
        field = ground_grid(asset)
        variants = set()
        for x, h, z, size, variant, _, _ in forest(field):
            self.assertFalse(abs(x) <= 110 and abs(z) <= 60)
            sampled, up = terrain_sample(
                field, x / DX + CENTER_ROW, z / DZ + CENTER_COL
            )
            self.assertAlmostEqual(sampled, h)
            self.assertGreaterEqual(up, 0.48)
            self.assertGreater(size, 0)
            variants.add(variant)
        self.assertEqual(variants, set(range(4)))

    def test_short_height_field_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "river.r16.gz"
            path.write_bytes(gzip.compress(bytes(4)))
            with self.assertRaisesRegex(ValueError, "dimensions"):
                ground_grid(path)
