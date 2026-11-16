"""Build sloping debris fans and sample their surface for rock and fern instances."""

from collections import defaultdict
from math import atan2, ceil, cos, floor, hypot, sin, tau
from random import Random

from bind_pilgrim import Glb, Output, unit


def toes(path, world_xy):
    """Read the eight lower outlines in the coordinate frame of the placed cliffs."""
    source = Glb(path)
    node = next(n for n in source.doc["nodes"] if n.get("name") == "Limestone spurs")
    primitive = source.doc["meshes"][node["mesh"]]["primitives"][0]
    vertices = source.values(primitive["attributes"]["POSITION"])
    bottom = min(y for _, y, _ in vertices)
    rings = []
    ring = []
    for x, y, z in vertices:
        if abs(y - bottom) < 1e-4:
            ring.append(world_xy(x, z))
        elif ring:
            if (
                len(ring) < 4
                or hypot(ring[0][0] - ring[-1][0], ring[0][1] - ring[-1][1]) > 0.001
            ):
                raise ValueError("Open lower cliff outline")
            rings.append(ring[:-1])
            ring = []
    if len(rings) != 8:
        raise ValueError("Expected eight shrine spurs")
    return rings


def smooth(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


GRID = 0.75


def build(rings, ground, clearance, path):
    rng = Random(42281)
    # Heights are accumulated on one world grid, so overlapping deposits share
    # a single surface. The outer skirt drops under the original valley.
    nodes = {}
    for ring in rings:
        cx = sum(p[0] for p in ring) / len(ring)
        cy = sum(p[1] for p in ring) / len(ring)
        for j in range(0, len(ring), 5):
            x, y = ring[j]
            theta = atan2(y - cy, x - cx)
            nx, ny = cos(theta), sin(theta)
            # Bury the crest in the cliff, leaving the outward slope visible.
            setback = rng.uniform(2.4, 4.2)
            x -= setback * nx
            y -= setback * ny
            reach = rng.uniform(11.0, 22.0)
            breadth = rng.uniform(4.8, 10.3)
            peak = rng.uniform(1.65, 4.2)
            # The toe of a long slide narrows with distance. Adjacent short
            # deposits break up its margins and continue inside the cliff.
            limit = ceil((reach + breadth + 4) / GRID)
            for gx in range(floor(x / GRID) - limit, floor(x / GRID) + limit + 1):
                dx = gx * GRID - x
                for gy in range(floor(y / GRID) - limit, floor(y / GRID) + limit + 1):
                    dy = gy * GRID - y
                    run, side = dx * nx + dy * ny, -dx * ny + dy * nx
                    if run < -5 or run >= reach or abs(side) > breadth + 2:
                        continue
                    width = breadth * (1 - 0.30 * max(0, run / reach))
                    skew = 0.75 * sin(run * 0.31 + theta) + 0.032 * run
                    r = (run / reach if run >= 0 else run / 5.0) ** 2 + (
                        (side - skew) / width
                    ) ** 2
                    if r >= 1:
                        continue
                    wx, wy = gx * GRID, gy * GRID
                    safe = smooth(clearance(wx, wy) / 3.2)
                    if safe <= 0:
                        continue
                    h = peak * (1 - r) ** 2 * safe
                    h *= (
                        1
                        + 0.10 * sin(wx * 0.83 + wy * 0.36)
                        + 0.055 * cos(wy * 1.6 - wx * 0.61)
                    )
                    nodes[gx, gy] = max(h, nodes.get((gx, gy), 0))
    cells = set()
    for gx, gy in nodes:
        for dx, dy in ((-1, -1), (-1, 0), (0, -1), (0, 0)):
            cells.add((gx + dx, gy + dy))
    pos, norm, uv, col, faces = [], [], [], [], []
    lookup = {}

    def vertex(i, j):
        key = (i, j)
        if key not in lookup:
            x, y = i * GRID, j * GRID
            h = nodes.get(key, 0)
            bed = ground(x, y)
            lookup[key] = len(pos)
            pos.append((x, bed + h - 0.11, y))

            def level(a, b):
                return nodes.get((a, b), 0) + ground(a * GRID, b * GRID)

            norm.append(
                unit(
                    (
                        -(level(i + 1, j) - level(i - 1, j)) / (2 * GRID),
                        1,
                        -(level(i, j + 1) - level(i, j - 1)) / (2 * GRID),
                    )
                )
            )
            uv.append((x / 3.6, y / 3.6))
            coverage = smooth((h - 0.18) / 1.12)
            col.append(
                (coverage, 0.74 + 0.18 * sin(0.31 * x + 0.18 * y) * cos(0.37 * y), 0)
            )
        return lookup[key]

    for i, j in sorted(cells):
        a, b, c, d = (
            vertex(i, j),
            vertex(i + 1, j),
            vertex(i, j + 1),
            vertex(i + 1, j + 1),
        )
        faces.extend((a, d, b, a, c, d))
    out = Output()
    attrs = {
        "POSITION": out.data(pos, "VEC3", bounds=True),
        "NORMAL": out.data(norm, "VEC3"),
        "TEXCOORD_0": out.data(uv, "VEC2"),
        "COLOR_0": out.data(col, "VEC3"),
    }
    out.doc.update(
        meshes=[
            {
                "name": "ShrineTalus",
                "primitives": [
                    {
                        "attributes": attrs,
                        "indices": out.data([(i,) for i in faces], "SCALAR", 5125),
                    }
                ],
            }
        ],
        nodes=[{"mesh": 0, "name": "ShrineTalus"}],
        scenes=[{"nodes": [0]}],
    )
    out.save(path)

    def sample(x, y):
        i, j = floor(x / GRID), floor(y / GRID)
        if (i, j) not in cells:
            return ground(x, y), 0.0
        u, v = x / GRID - i, y / GRID - j
        a, b, c, d = (
            pos[lookup[k]][1] for k in ((i, j), (i + 1, j), (i, j + 1), (i + 1, j + 1))
        )
        height = (
            a * (1 - max(u, v)) + b * max(0, u - v) + c * max(0, v - u) + d * min(u, v)
        )
        bed = ground(x, y)
        return max(bed, height), max(0, height - bed)

    batches = defaultdict(list)
    for i, j in sorted(cells):
        x, y = (i + rng.random()) * GRID, (j + rng.random()) * GRID
        if clearance(x, y) < 1.3:
            continue
        z, depth = sample(x, y)

        # A few outsized blocks sit in debris chutes. The feathered toe is
        # mostly grit, isolated pebbles and patches of ferns.
        pocket = 0.5 + 0.5 * sin(x * 0.47 + sin(y * 0.38)) * cos(y * 0.31 - x * 0.24)
        if rng.random() < (0.015 + 0.29 * pocket) * (
            0.13 + 0.87 * smooth(depth / 0.50)
        ):
            large = rng.random() < 0.10 * smooth(depth / 1.65)
            size = rng.uniform(0.54, 1.7) if large else rng.uniform(0.095, 0.47)
            batches[rng.randrange(6)].append(
                (
                    x,
                    y,
                    z - 0.12 * size,
                    rng.uniform(-12, 12),
                    rng.uniform(-13, 13),
                    rng.uniform(-180, 180),
                    size,
                )
            )
        elif depth < 1.35 and rng.random() < 0.080 * pocket**2:
            for _ in range(rng.randint(2, 6)):
                a, r = rng.uniform(0, tau), rng.uniform(0, 2.1)
                fx, fy = x + r * cos(a), y + r * sin(a)
                if clearance(fx, fy) < 1.3:
                    continue
                fz, _ = sample(fx, fy)
                batches[6].append(
                    (
                        fx,
                        fy,
                        fz - 0.024,
                        0,
                        0,
                        rng.uniform(-180, 180),
                        rng.uniform(0.75, 1.8),
                    )
                )
    return batches, sample
