"""Fit the Xingping elevation grid and wooded shoulders around the three-court valley."""

from array import array
import gzip
import math
from random import Random
import sys

from bind_pilgrim import Output, unit

WIDTH, HEIGHT = 481, 401
DX, DZ = 2.82, 2.56
ORIGIN_X = 97.0
HEIGHT_SCALE = 0.155
CENTER_COL, CENTER_ROW = 246, 206


def smooth(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


def ground_grid(source):
    elevation = array("H")
    elevation.frombytes(gzip.decompress(source.read_bytes()))
    if sys.byteorder != "little":
        elevation.byteswap()
    if len(elevation) != WIDTH * HEIGHT:
        raise ValueError("Unexpected Xingping elevation dimensions")
    ground = []
    for j in range(HEIGHT):
        x = (j - CENTER_ROW) * DX
        for i in range(WIDTH):
            z = (i - CENTER_COL) * DZ
            # The road and the playable valley floor already have authored collision.
            # Keep the scenery beneath them until the first wooded foothills.
            dist = math.hypot(max(0, abs(x) - 110), max(0, abs(z) - 16))
            shoulder = smooth(56, 136, dist)
            elev = elevation[j * WIDTH + i] * 0.10
            h = (elev - 113) * HEIGHT_SCALE
            ground.append(-12.0 + shoulder * (h + 6.0))
    return ground


def build(folder, path):
    field = ground_grid(folder / "Xingping.r16.gz")
    rng = Random(4193)
    glb = Output()
    glb.doc.update(nodes=[], meshes=[], scenes=[{"nodes": []}])
    glb.doc["asset"]["generator"] = "Vesper Li River relief"
    cover = glb.image(
        (folder / "ValleyCover.jpg").read_bytes(), "image/jpeg", "RiverCover"
    )
    glb.doc["materials"] = [
        dict(
            name="RiverLimestone",
            pbrMetallicRoughness=dict(
                baseColorTexture=cover, metallicFactor=0, roughnessFactor=0.9
            ),
        ),
        dict(
            name="RidgeLeaf",
            pbrMetallicRoughness=dict(metallicFactor=0, roughnessFactor=0.87),
        ),
    ]

    def mesh(name, slot, positions, normals, indices, uvs=None, colors=None):
        attrs = dict(
            POSITION=glb.data(positions, "VEC3", bounds=True),
            NORMAL=glb.data(normals, "VEC3"),
        )
        if uvs is not None:
            attrs["TEXCOORD_0"] = glb.data(uvs, "VEC2")
        if colors is not None:
            attrs["COLOR_0"] = glb.data(colors, "VEC3")
        prim = dict(
            material=slot,
            attributes=attrs,
            indices=glb.data([(i,) for i in indices], "SCALAR", 5125),
        )
        n = len(glb.doc["meshes"])
        glb.doc["meshes"].append(dict(name=name, primitives=[prim]))
        glb.doc["nodes"].append(dict(name=name, mesh=n))
        glb.doc["scenes"][0]["nodes"].append(n)

    points, normals, uv, faces = [], [], [], []
    for j in range(HEIGHT):
        for i in range(WIDTH):
            k = j * WIDTH + i
            x, z = (j - CENTER_ROW) * DX, (i - CENTER_COL) * DZ
            points.append((x, field[k], z))
            ja, jb = max(0, j - 1), min(HEIGHT - 1, j + 1)
            ia, ib = max(0, i - 1), min(WIDTH - 1, i + 1)
            sx = (field[jb * WIDTH + i] - field[ja * WIDTH + i]) / ((jb - ja) * DX)
            sz = (field[j * WIDTH + ib] - field[j * WIDTH + ia]) / ((ib - ia) * DZ)
            normals.append(unit((-sx, 1, -sz)))
            uv.append((i / (WIDTH - 1), j / (HEIGHT - 1)))
            if i and j:
                a, b, c, d = k - WIDTH - 1, k - WIDTH, k, k - 1
                faces.extend((a, b, c, a, c, d))
    mesh("RiverRelief", 0, points, normals, faces, uvs=uv)

    # Distant evergreens are solid, irregular crown groups. Needle cards are
    # reserved for trees close enough for individual sprays to resolve.
    pts, ns, colors, idx = [], [], [], []

    def crown(x, y, z, rx, ry, rz, phase, base):
        first = len(pts)
        segments, rings = 9, 5
        for j in range(rings + 1):
            v = j / rings
            b = (v - 0.5) * math.pi
            for n in range(segments):
                a = math.tau * n / segments
                fold = (
                    1
                    + 0.14 * math.sin(3 * a + phase + v)
                    + 0.09 * math.cos(5 * a - phase + 2 * v)
                )
                h = math.sin(b)
                pts.append(
                    (
                        x + rx * math.cos(a) * math.cos(b) * fold + 0.12 * rx * v,
                        y + ry * h + ry * 0.13 * math.cos(3 * a + phase) * math.cos(b),
                        z + rz * math.sin(a) * math.cos(b) * fold,
                    )
                )
                ns.append(
                    unit(
                        (
                            math.cos(a) * math.cos(b) / rx,
                            h / ry,
                            math.sin(a) * math.cos(b) / rz,
                        )
                    )
                )
                shade = 0.72 + 0.29 * v + 0.08 * math.sin(4 * a + phase)
                colors.append(tuple(c * shade for c in base))
                if j:
                    k = first + j * segments + n
                    nxt = first + j * segments + (n + 1) % segments
                    if j > 1:
                        idx.extend((k - segments, k, nxt - segments))
                    if j < rings:
                        idx.extend((nxt - segments, k, nxt))

    trees = 0
    for _ in range(6200):
        i = rng.randrange(4, WIDTH - 4)
        j = rng.randrange(4, HEIGHT - 4)
        k = j * WIDTH + i
        x, h, z = points[k]
        up = normals[k][1]
        if h < 5 or up < 0.49 or h > 118 or math.hypot(x * 0.85, z) > 530:
            continue
        grove = 0.43 + 0.36 * math.sin(x * 0.043 + math.sin(z * 0.069)) * math.cos(
            z * 0.049
        )
        if rng.random() > grove:
            continue
        span = rng.uniform(0.8, 2.1) * (1.10 - 0.24 * smooth(20, 93, h))
        phase = rng.uniform(0, math.tau)
        tone = rng.uniform(0.78, 1.16)
        base = (0.074 * tone, 0.10 * tone, 0.072 * tone)
        crown(x, h + 0.62 * span, z, span * 0.74, span * 1.07, span * 0.69, phase, base)
        crown(
            x + 0.51 * span,
            h + 0.41 * span,
            z - 0.32 * span,
            span * 0.55,
            span * 0.63,
            span * 0.49,
            phase + 1,
            base,
        )
        trees += 1
    mesh("RiverGroves", 1, pts, ns, idx, colors=colors)
    glb.save(path)
    return trees
