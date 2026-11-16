"""Bake the valley-wide diffuse tint, with needle beds under trees and exposed scree."""

from math import exp, floor
from random import Random
import struct
import zlib


def bake(path, trees):
    side = 512
    # Cover the same 432 m square as MountainValley.glb.
    cell = 43200 / side
    shade = [0.0] * (side * side)
    for x, y, span in trees:
        u, v = (x + 11900) / cell, (y + 21600) / cell
        radius = 520 * span / cell
        for j in range(
            max(0, floor(v - 2 * radius)), min(side, int(v + 2 * radius) + 1)
        ):
            for i in range(
                max(0, floor(u - 2 * radius)), min(side, int(u + 2 * radius) + 1)
            ):
                r2 = ((i - u) ** 2 + (j - v) ** 2) / (radius * radius)
                shade[j * side + i] = max(shade[j * side + i], exp(-1.3 * r2))
    rng = Random(719)
    grids = {
        s: [[rng.random() for _ in range(s + 1)] for _ in range(s + 1)]
        for s in (9, 29, 83)
    }

    def noise(s, u, v):
        grid = grids[s]
        x, y = u * s, v * s
        i, j = int(x), int(y)
        a, b = x - i, y - j
        a = a * a * (3 - 2 * a)
        b = b * b * (3 - 2 * b)
        return (1 - b) * (grid[j][i] * (1 - a) + grid[j][i + 1] * a) + b * (
            grid[j + 1][i] * (1 - a) + grid[j + 1][i + 1] * a
        )

    raw = bytearray()
    for j in range(side):
        raw.append(0)
        for i in range(side):
            u, v = (i + 0.5) / side, (j + 0.5) / side
            density = (
                0.57 * noise(9, u, v) + 0.32 * noise(29, u, v) + 0.11 * noise(83, u, v)
            )
            heath = min(1, max(0, (density - 0.27) * 2.7))
            dark = 1 - 0.53 * shade[j * side + i]
            # Linear multipliers on the original scanned forest-floor textures.
            raw.extend(
                round(255 * dark * c)
                for c in (0.44 - 0.29 * heath, 0.51 - 0.20 * heath, 0.43 - 0.23 * heath)
            )

    def chunk(tag, data):
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data))
        )

    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", side, side, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )
