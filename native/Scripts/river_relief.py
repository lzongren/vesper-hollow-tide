"""Fit the Xingping elevation grid and wooded shoulders around the three-court valley."""

from array import array
import gzip
import math
from random import Random
import sys

from bind_pilgrim import Glb, Output, cross, unit

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


def terrain_sample(field, row, col):
    """Intersect the emitted triangle under a fractional grid position."""
    j, i = int(row), int(col)
    v, u = row - j, col - i
    k = j * WIDTH + i
    a, b, c, d = field[k], field[k + 1], field[k + WIDTH + 1], field[k + WIDTH]
    dz, dx = (b - a, c - b) if u >= v else (c - d, d - a)
    height = a + u * dz + v * dx
    up = 1 / math.sqrt(1 + (dx / DX) ** 2 + (dz / DZ) ** 2)
    return height, up


def forest(field):
    rng = Random(4193)
    for j in range(2, HEIGHT - 2):
        for i in range(2, WIDTH - 2):
            row, col = j + rng.uniform(0.06, 0.94), i + rng.uniform(0.06, 0.94)
            x, z = (row - CENTER_ROW) * DX, (col - CENTER_COL) * DZ
            h, up = terrain_sample(field, row, col)
            if h < 0.5 or up < 0.48 or math.hypot(x * 0.85, z) > 560:
                continue
            pocket = (
                math.sin(x * 0.078 + math.sin(z * 0.052))
                + 0.65 * math.cos(z * 0.091 + x * 0.037)
                + 0.40 * math.sin(z * 0.184 - x * 0.143)
            )
            shelter = smooth(0.48, 0.81, up)
            density = (0.04 + 0.72 * smooth(-1.05, 0.77, pocket)) * shelter
            if rng.random() > density:
                continue
            size = rng.uniform(3.4, 7.6) * (0.82 + 0.22 * shelter)
            pine = math.sin(z * 0.047 + math.cos(x * 0.076)) + rng.uniform(-1, 1) > 0
            variant = (0 if pine else 2) + rng.randrange(2)
            yield (
                x,
                h,
                z,
                size,
                variant,
                rng.uniform(0, math.tau),
                rng.uniform(0.84, 1.15),
            )


def summit_forest(path):
    """Seed the upward-facing ledges of the eight rocks in their own local space."""
    rock = Glb(path)
    node = next(n for n in rock.doc["nodes"] if n.get("name") == "Limestone spurs")
    prim = rock.doc["meshes"][node["mesh"]]["primitives"][0]
    vertices = rock.values(prim["attributes"]["POSITION"])
    indices = [i for (i,) in rock.values(prim["indices"])]
    rng = Random(214)
    for i in range(0, len(indices), 3):
        a, b, c = (vertices[k] for k in indices[i : i + 3])
        ab = tuple(t - s for s, t in zip(a, b))
        ac = tuple(t - s for s, t in zip(a, c))
        normal = cross(ab, ac)
        length = math.hypot(*normal)
        if length < 1e-7 or normal[1] < 0.59 * length:
            continue
        density = 0.17 * smooth(0.59, 0.90, normal[1] / length)
        sites = int(rng.random() + normal[1] * 0.5 * density)
        for _ in range(sites):
            u, v = rng.random(), rng.random()
            if u + v > 1:
                u, v = 1 - u, 1 - v
            x, h, z = (p + u * q + v * r for p, q, r in zip(a, ab, ac))
            if h > 3.8:
                yield (
                    x,
                    h,
                    z,
                    rng.uniform(2.1, 4.7),
                    rng.randrange(4),
                    rng.uniform(0, math.tau),
                    rng.uniform(0.97, 1.28),
                )


def build(folder, path):
    field = ground_grid(folder / "Xingping.r16.gz")
    glb = Output()
    glb.doc.update(nodes=[], meshes=[], scenes=[{"nodes": []}])
    glb.doc["asset"]["generator"] = "Vesper Li River relief"
    cover = glb.image(
        (folder / "ValleyCover.jpg").read_bytes(), "image/jpeg", "RiverCover"
    )
    leaves = glb.image(
        (folder / "ConiferViews.png").read_bytes(), "image/png", "ConiferViews"
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
            doubleSided=True,
            alphaMode="MASK",
            alphaCutoff=0.30,
            pbrMetallicRoughness=dict(
                baseColorTexture=leaves, metallicFactor=0, roughnessFactor=0.90
            ),
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

    points, normals, uv, faces, rock = [], [], [], [], []
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
            exposure = 1 - smooth(0.49, 0.88, normals[-1][1])
            seams = 0.76 + 0.18 * math.sin(0.18 * x + 0.061 * z + 0.52 * field[k])
            rock.append((exposure * seams, 0.0, 0.0))
            uv.append((i / (WIDTH - 1), j / (HEIGHT - 1)))
            if i and j:
                a, b, c, d = k - WIDTH - 1, k - WIDTH, k, k - 1
                faces.extend((a, b, c, a, c, d))
    mesh("RiverRelief", 0, points, normals, faces, uvs=uv, colors=rock)

    def groves(name, sites):
        pts, ns, atlas, idx = [], [], [], []
        trees = 0
        # Both cards represent the same tree seen from perpendicular directions.
        # Bury the transparent margin under the triangle supporting the trunk.
        for x, h, z, size, variant, yaw, spread in sites:
            half_width = 0.32 * size * spread
            base = h - 0.025 * size
            for side in range(2):
                a = yaw + side * math.pi / 2
                dx, dz = half_width * math.cos(a), half_width * math.sin(a)
                start = len(pts)
                for across, top in ((-1, 0), (1, 0), (1, 1), (-1, 1)):
                    pts.append((x + across * dx, base + top * size, z + across * dz))
                    ns.append((0, 1, 0))
                    u = (variant + (0.001 if across < 0 else 0.999)) / 4
                    v = (side + (0.001 if top else 0.999)) / 2
                    atlas.append((u, v))
                idx.extend(start + k for k in (0, 1, 2, 0, 2, 3))
            trees += 1
        mesh(name, 1, pts, ns, idx, uvs=atlas)
        return trees

    trees = groves("RiverGroves", forest(field))
    groves("ShrineGroves", summit_forest(folder.parent / "ShrineCliffWalk.glb"))
    glb.save(path)
    return trees
