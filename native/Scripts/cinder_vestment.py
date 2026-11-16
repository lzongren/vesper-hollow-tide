"""A folded brocade stole, with long embroidered lappets bound to the nearer leg."""

from math import sin, cos, pi
from bind_pilgrim import cross, unit


def stole(out, bones, source):
    brocade = out.image(
        (source / "cinder-brocade.jpg").read_bytes(), "image/jpeg", "VermilionBrocade"
    )
    out.doc["materials"].append(
        dict(
            name="Vermilion prayer stole",
            doubleSided=True,
            pbrMetallicRoughness=dict(
                baseColorTexture=brocade, roughnessFactor=0.77, metallicFactor=0.09
            ),
        )
    )
    p = []
    n = []
    uv = []
    joints = []
    weights = []
    idx = []
    for side, suffix in [(-1, "r"), (1, "l")]:

        def sample(u, v):
            # Front lappets cross the collar, turn over the shoulder and fall down the back.
            if v < 0.48:
                t = v / 0.48
                x = 0.19 - 0.055 * t
                y = 0.33 + 1.16 * t
                z = 0.28 - 0.11 * t + 0.035 * sin(pi * t)
            elif v < 0.58:
                t = (v - 0.48) / 0.1
                x = 0.135 + 0.035 * sin(pi * t)
                y = 1.49 + 0.063 * sin(pi * t)
                z = 0.17 - 0.335 * t
            else:
                t = (v - 0.58) / 0.42
                x = 0.135 + 0.07 * t
                y = 1.49 - 1.04 * t
                z = -0.165 - 0.09 * t
            width = 0.165 + 0.035 * (1 - sin(pi * v))
            z += 0.023 * sin(u * 3 * pi + 0.65 * v)
            return (side * (x + (u - 0.5) * width), y - 0.018 * cos(3 * pi * u), z)

        for row in range(73):
            v = row / 72
            for col in range(15):
                u = col / 14
                point = sample(u, v)
                p.append(point)
                uv.append((u, v * 2.9))
                a, b = sample(min(1, u + 0.001), v), sample(max(0, u - 0.001), v)
                c, d = sample(u, min(1, v + 0.001)), sample(u, max(0, v - 0.001))
                normal = unit(
                    cross(
                        tuple(i - k for i, k in zip(a, b)),
                        tuple(i - k for i, k in zip(c, d)),
                    )
                )
                n.append(normal)
                y = point[1]
                if y < 1:
                    name, other = "thigh_" + suffix, "pelvis"
                    w = min(0.78, (1 - y) * 1.65)
                else:
                    name, other = "spine_05", "pelvis"
                    w = min(1, (y - 1) / 0.34)
                joints.append((bones[name], bones[other], 0, 0))
                weights.append((w, 1 - w, 0, 0))
                if row and col:
                    i = len(p) - 1
                    idx.extend((i - 16, i - 15, i, i - 16, i, i - 1))
    attrs = dict(
        POSITION=out.data(p, "VEC3", bounds=True),
        NORMAL=out.data(n, "VEC3"),
        TEXCOORD_0=out.data(uv, "VEC2"),
        JOINTS_0=out.data(joints, "VEC4", 5123),
        WEIGHTS_0=out.data(weights, "VEC4"),
    )
    out.doc["meshes"][0]["primitives"].append(
        dict(
            attributes=attrs,
            indices=out.data([(i,) for i in idx], "SCALAR", 5125),
            material=len(out.doc["materials"]) - 1,
        )
    )
