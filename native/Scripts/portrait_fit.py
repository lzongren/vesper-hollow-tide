"""Apply the measured frontal fit without requiring vision libraries in Unreal."""

from array import array
import gzip
import json
import math
import struct
import sys


def smooth(x):
    x = min(1, max(0, x))
    return x * x * (3 - 2 * x)


class PortraitFit:
    def __init__(self, path):
        blob = gzip.decompress(path.read_bytes())
        n = struct.unpack_from("<I", blob)[0]
        data = json.loads(blob[4 : 4 + n])
        self.grid = array("h")
        self.grid.frombytes(blob[4 + n :])
        if sys.byteorder != "little":
            self.grid.byteswap()
        self.nx, self.ny = data["shape"]
        self.x0, self.y0, self.x1, self.y1 = data["bounds"]
        self.camera = data["camera"]
        self.focal = data["focal"]
        self.screen = data["screen_size"]
        self.size = data["reference_size"]
        self.shift = data["shift"]
        self.c, self.s = data["alignment"][0][0], data["alignment"][1][0]
        if (
            len(self.grid) != self.nx * self.ny * 3
            or self.c * self.c + self.s * self.s < 1e-10
        ):
            raise ValueError("Invalid portrait field")

    def project(self, p):
        x, y, z = p
        cx, cy, cz = self.camera
        scale = self.focal / (cz - z)
        return self.screen[0] / 2 + scale * (x - cx), self.screen[1] / 2 - scale * (
            y - cy
        )

    def photo(self, p):
        u, v = self.project(p)
        x, y = u - self.shift[0], v - self.shift[1]
        d = self.c * self.c + self.s * self.s
        return (
            (self.c * x + self.s * y) / (d * self.size[0]),
            (-self.s * x + self.c * y) / (d * self.size[1]),
        )

    def warp(self, p):
        x, y, z = p
        # Preserve the neck seam, posterior skull, hair ornaments and costume.
        strength = smooth((y - 1.514) / 0.037) * smooth((z + 0.015) / 0.076)
        if strength == 0:
            return p
        u, v = self.project(p)
        gx = (u - self.x0) * (self.nx - 1) / (self.x1 - self.x0)
        gy = (v - self.y0) * (self.ny - 1) / (self.y1 - self.y0)
        if not (0 <= gx < self.nx - 1 and 0 <= gy < self.ny - 1):
            return p
        i, j = math.floor(gx), math.floor(gy)
        a, b = gx - i, gy - j
        start = 3 * (j * self.nx + i)

        def sample(k):
            row = start + k
            upper = self.grid[row] * (1 - a) + self.grid[row + 3] * a
            row += 3 * self.nx
            lower = self.grid[row] * (1 - a) + self.grid[row + 3] * a
            return 0.01 * strength * (upper * (1 - b) + lower * b)

        du, dv, dz = sample(0), sample(1), sample(2) * 0.001
        cx, cy, cz = self.camera
        d = cz - z - dz
        # Unproject after the change in depth so the requested image-space
        # displacement and the physical relief can be controlled independently.
        return (
            cx + (u + du - self.screen[0] / 2) * d / self.focal,
            cy - (v + dv - self.screen[1] / 2) * d / self.focal,
            z + dz,
        )


class ExpressionFit:
    """Keep identical skin points registered with both endpoints of the blink."""

    def __init__(self, art):
        self.base = PortraitFit(art / "portrait-field.gz")
        self.closed = PortraitFit(art / "portrait-closed-feedback.gz")
        self.open = PortraitFit(art / "portrait-open-feedback.gz")
        self.rims = json.loads((art / "portrait-lids.json").read_text())

    def warp(self, point, opened=False):
        first = self.base.warp(point)
        rest = self.closed.warp(first)
        zone = self.eye_mask(*self.base.photo(first))
        # A shared displacement preserves the sculpted upper/lower lid contact.
        # Sample it at the same point for each expression instead of imposing
        # an independent full-face warp over the moving eyelid margins.
        amount = 0.46 * (1 - zone)
        mouth_and_cheeks = tuple(a + (b - a) * amount for a, b in zip(first, rest))
        if not (opened and zone):
            return mouth_and_cheeks
        other = self.open.warp(first)
        return tuple(
            a + (b - c) * zone * 0.12 for a, b, c in zip(mouth_and_cheeks, other, first)
        )

    @staticmethod
    def eye_mask(u, v):
        return smooth((0.083 - abs(abs(u - 0.504) - 0.112)) / 0.027) * smooth(
            (0.059 - abs(v - 0.442)) / 0.027
        )

    def open_uv(self, point, source):
        from bisect import bisect_left

        u, v = self.base.photo(point)
        x, y, _ = source
        upper = y >= 7.266 + 0.026 * min(1, max(0, (abs(x) - 0.155) / 0.30))
        curve = self.rims[int(u > 0.5)][int(not upper)]
        if curve[0][0] <= u <= curve[-1][0]:
            i = min(len(curve) - 1, max(1, bisect_left(curve, [u])))
            (x0, y0), (x1, y1) = curve[i - 1 : i + 1]
            edge = y0 + (y1 - y0) * (u - x0) / max(1e-8, x1 - x0)
            # Keep iris and sclera pigment off the skin at either eyelid margin.
            v = min(v, edge - 0.0025) if upper else max(v, edge + 0.0030)
        return (u, v)
