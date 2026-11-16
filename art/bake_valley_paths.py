"""Bake the valley's route, seep and soil variation into a world-space control map."""

import itertools
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def noise(x, y):
    ix = np.floor(x).astype(np.int32)
    iy = np.floor(y).astype(np.int32)
    u = x - ix
    v = y - iy
    u = u * u * (3 - 2 * u)
    v = v * v * (3 - 2 * v)
    result = np.zeros_like(u)
    for a in (0, 1):
        for b in (0, 1):
            h = ((ix + a) * 73856093) ^ ((iy + b) * 19349663)
            h = (h ^ (h >> 13)) * 1274126177
            result += (
                ((h ^ (h >> 16)) & 65535)
                / 65535
                * (u if a else 1 - u)
                * (v if b else 1 - v)
            )
    return result


def bake(out, n=1024):
    # The imported floor spans 432 metres around UE (97,0). Pixel centres
    # and the material's world-position transform use the same orientation.
    grid = (np.arange(n, dtype=np.float32) + 0.5) * 432 / n - 216
    x, y = np.meshgrid(grid + 97, grid)
    large = noise(x * 0.072, y * 0.072)
    fine = noise(x * 0.81, y * 0.81)
    warp = (large - 0.5) * 2.0 + (fine - 0.5) * 0.7
    path_distance = np.full_like(x, 999)

    def trail(points):
        for (ax, ay), (bx, by) in itertools.pairwise(points):
            dx, dy = bx - ax, by - ay
            t = np.clip(((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy), 0, 1)
            np.minimum(
                path_distance,
                np.hypot(x - ax - t * dx, y - ay - t * dy),
                out=path_distance,
            )

    # Branches meet all three valley stair landings; the trail bends around the courts.
    trail(
        [
            (-12, -8),
            (8, -13),
            (27, -20),
            (34, -26),
            (42, -28),
            (51, -27),
            (63, -19),
            (80, -16),
            (94, -13),
            (108, -9),
            (115, -9),
            (127, -12),
            (141, -19),
            (156, -24),
            (171, -28),
            (188, -33),
            (194, -33),
            (211, -28),
        ]
    )
    for sx, sy in [(42, 0), (115, 16), (194, -8)]:
        trail([(sx, sy - 19), (sx, sy - 26), (sx, sy - 29)])
    trail(
        [(-13, 9), (2, 10), (11, 12), (23, 13), (32, 17), (46, 20), (59, 20), (72, 25)]
    )
    ramp = lambda v: np.clip(v, 0, 1) ** 2 * (3 - 2 * np.clip(v, 0, 1))
    path = ramp((2.25 + warp - path_distance) / 1.65)
    river = 29 * np.sin((x - 97) / 47)
    seep = ramp((8.0 + 3.8 * warp - np.abs(y - river)) / 8.0)
    rock = ramp((0.47 * large + 0.53 * noise(x * 0.16 + 11, y * 0.16) - 0.48) / 0.26)
    wetrock = np.clip(seep * (0.36 + 0.64 * rock) + rock * 0.53, 0, 1) * (
        1 - path * 0.87
    )
    macro = np.clip(0.19 + 0.63 * large + 0.17 * fine, 0, 1)
    Image.fromarray(np.uint8(np.dstack([path, wetrock, macro]) * 255 + 0.5)).save(
        out, optimize=True
    )


if __name__ == "__main__":
    bake(Path(sys.argv[1]))
