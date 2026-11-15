"""Assemble a locally baked digital-human face on the playable combat rig."""

import base64
import json
import math
import struct
import zlib


def unpack(data, fmt):
    return list(struct.iter_unpack("<" + fmt, zlib.decompress(base64.b64decode(data))))


def neck_section(points, tris, height=1.520):
    segments = []
    for tri in tris:
        cut = []
        for i, j in zip(tri, (tri[1], tri[2], tri[0])):
            a, b = points[i], points[j]
            if (a[1] > height) == (b[1] > height):
                continue
            t = (height - a[1]) / (b[1] - a[1])
            cut.append((a[0] + (b[0] - a[0]) * t, a[2] + 0.012 + (b[2] - a[2]) * t))
        if len(cut) == 2:
            segments.append(cut)
    ring = []
    for i in range(120):
        a = i * math.tau / 120
        dx, dz = math.sin(a), math.cos(a)
        far = 0
        for (x, z), (bx, bz) in segments:
            sx, sz = bx - x, bz - z
            den = dx * sz - dz * sx
            if abs(den) < 1e-9:
                continue
            if 0 <= (x * dz - z * dx) / den <= 1:
                far = max(far, (x * sz - z * sx) / den)
        if far < 0.015:
            raise ValueError("Incomplete neck section")
        ring.append((far * dx, height, far * dz - 0.012))
    return ring


def head_weight(position):
    _, height, depth = position
    neck_blend = max(0, min(1, (height - 1.512) / 0.045))
    # The chin projects in front of the throat at the same height. Keeping it
    # on the head prevents neck rotation from flattening or twisting the jaw.
    front = max(0, min(1, (depth - 0.060) / 0.025))
    above_collar = max(0, min(1, (height - 1.520) / 0.016))
    jaw = front * above_collar
    jaw = jaw * jaw * (3 - 2 * jaw)
    return neck_blend + (1 - neck_blend) * jaw


def add_head(out, bones, cache, slots):
    data = json.loads((cache / "face.json").read_text())
    faceshape = {}
    for name, part in data["parts"].items():
        pos = unpack(part["p"], "fff")
        tri = unpack(part["tri"], "III")
        amount = [head_weight(p) for p in pos]
        attrs = dict(
            POSITION=out.data(pos, "VEC3", bounds=True),
            NORMAL=out.data(unpack(part["n"], "fff"), "VEC3"),
            TEXCOORD_0=out.data(unpack(part["uv"], "ff"), "VEC2"),
            JOINTS_0=out.data(
                [(bones["head"], bones["neck_01"], 0, 0)] * len(pos), "VEC4", 5123
            ),
            WEIGHTS_0=out.data([(t, 1 - t, 0, 0) for t in amount], "VEC4"),
        )
        primitive = dict(
            attributes=attrs,
            material=slots[name],
            indices=out.data([(k,) for face in tri for k in face], "SCALAR", 5125),
        )
        out.doc["meshes"][0]["primitives"].append(primitive)
        faceshape[id(primitive)] = {
            key: out.data(unpack(blob, "fff"), "VEC3", bounds=True)
            for key, blob in part["poses"].items()
        }
        if name == "head":
            scalp = [
                (x / 0.104, 7 + (y - 1.625) / 0.103, 0.32 + z / 0.104)
                for x, y, z in pos
            ]
            skin_faces = tri
            neck = neck_section(pos, tri)

    def finish_shapes():
        mesh = out.doc["meshes"][0]
        zero = {}
        for part in mesh["primitives"]:
            count = out.doc["accessors"][part["attributes"]["POSITION"]]["count"]
            if count not in zero:
                zero[count] = out.data([(0, 0, 0)] * count, "VEC3", bounds=True)
            authored = faceshape.get(id(part), {})
            part["targets"] = [
                {"POSITION": authored.get(name, zero[count])} for name in data["poses"]
            ]
        mesh["extras"] = dict(targetNames=data["poses"])
        mesh["weights"] = [0.0] * len(data["poses"])

    return scalp, skin_faces, neck, finish_shapes
