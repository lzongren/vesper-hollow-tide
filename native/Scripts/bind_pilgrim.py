"""Fit the repository's pilgrim, mantle and gear to the local locomotion skeleton.

Only joint transforms are read from the local reference export. All rendered
vertices and materials come from Vesper's assets. Coordinates here are glTF metres.
"""

import copy
import json
import math
from pathlib import Path
import runpy
import struct

FORMATS = {5121: "B", 5123: "H", 5125: "I", 5126: "f"}
WIDTHS = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}
AXES = range(3)


class Glb:
    def __init__(self, path):
        raw = path.read_bytes()
        n = struct.unpack_from("<I", raw, 12)[0]
        self.doc = json.loads(raw[20 : 20 + n])
        self.binary = raw[28 + n :]

    def view(self, index):
        v = self.doc["bufferViews"][index]
        off = v.get("byteOffset", 0)
        return self.binary[off : off + v["byteLength"]]

    def values(self, index):
        a = self.doc["accessors"][index]
        v = self.doc["bufferViews"][a["bufferView"]]
        row = struct.Struct("<" + str(WIDTHS[a["type"]]) + FORMATS[a["componentType"]])
        stride = v.get("byteStride", row.size)
        off = v.get("byteOffset", 0) + a.get("byteOffset", 0)
        return [
            row.unpack_from(self.binary, off + i * stride) for i in range(a["count"])
        ]


class Output:
    def __init__(self):
        self.doc = {
            "asset": {"version": "2.0", "generator": "Vesper pilgrim fitting"},
            "bufferViews": [],
            "accessors": [],
            "materials": [],
            "images": [],
            "textures": [],
            "meshes": [{"name": "Wayfarer", "primitives": []}],
            "scene": 0,
            "scenes": [{"nodes": [0]}],
        }
        self.binary = bytearray()

    def block(self, raw):
        self.binary.extend(bytes(-len(self.binary) % 4))
        self.doc["bufferViews"].append(
            {"buffer": 0, "byteOffset": len(self.binary), "byteLength": len(raw)}
        )
        self.binary.extend(raw)
        return len(self.doc["bufferViews"]) - 1

    def data(self, rows, kind, component=5126, bounds=False):
        row = struct.Struct("<" + str(WIDTHS[kind]) + FORMATS[component])
        raw = bytearray(row.size * len(rows))
        for i, r in enumerate(rows):
            row.pack_into(raw, i * row.size, *r)
        a = {
            "bufferView": self.block(raw),
            "componentType": component,
            "count": len(rows),
            "type": kind,
        }
        if bounds:
            a.update(min=list(map(min, zip(*rows))), max=list(map(max, zip(*rows))))
        self.doc["accessors"].append(a)
        return len(self.doc["accessors"]) - 1

    def image(self, raw, mime, name):
        idx = len(self.doc["images"])
        self.doc["images"].append(
            {"name": name, "bufferView": self.block(raw), "mimeType": mime}
        )
        self.doc["textures"].append({"source": idx})
        return {"index": len(self.doc["textures"]) - 1}

    def save(self, path):
        self.doc["buffers"] = [{"byteLength": len(self.binary)}]
        j = json.dumps(self.doc, separators=(",", ":")).encode()
        j += b" " * (-len(j) % 4)
        self.binary.extend(bytes(-len(self.binary) % 4))
        path.write_bytes(
            struct.pack(
                "<4sIIII",
                b"glTF",
                2,
                28 + len(j) + len(self.binary),
                len(j),
                0x4E4F534A,
            )
            + j
            + struct.pack("<II", len(self.binary), 0x004E4942)
            + self.binary
        )


def unit(a):
    n = math.sqrt(sum(v * v for v in a)) or 1
    return tuple(v / n for v in a)


def cross(a, b):
    x, y, z = a
    u, v, w = b
    return (y * w - z * v, z * u - x * w, x * v - y * u)


def align(a, b):
    a, b = unit(a), unit(b)
    k = cross(a, b)
    cosine = sum(x * y for x, y in zip(a, b))
    # Quaternion for the shortest swing between the two limb directions.
    if cosine < -1 + 1e-8:
        axis = min([(1, 0, 0), (0, 1, 0), (0, 0, 1)], key=lambda x: abs(sum(i*j for i, j in zip(a, x))))
        return (*unit(cross(a, axis)), 0.0)
    return unit((*k, 1 + cosine))


def rotate(q, p):
    v = cross(q[:3], p)
    w = cross(q[:3], v)
    return tuple(p[i] + 2 * (q[3] * v[i] + w[i]) for i in AXES)


def rest_position(matrix):
    # Invert an orthogonal scaled inverse-bind matrix for its translation only.
    return tuple(
        -sum(matrix[k * 4 + i] * matrix[12 + i] for i in AXES)
        / sum(matrix[k * 4 + i] ** 2 for i in AXES)
        for k in AXES
    )


def joint_positions(asset):
    skin = asset.doc["skins"][0]
    return {
        asset.doc["nodes"][j]["name"]: rest_position(m)
        for j, m in zip(skin["joints"], asset.values(skin["inverseBindMatrices"]))
    }


def build(reference, body_path, art, textures, output, *, bellwarden=False, armed=False, heron=False, cinder=False, wayfarer=False):
    base, rig, out = Glb(body_path), Glb(reference), Output()
    skin = rig.doc["skins"][0]
    source = joint_positions(base)
    target = joint_positions(rig)
    mapping = {
        "Hips": "pelvis",
        "Spine02": "spine_02",
        "Spine01": "spine_04",
        "Spine": "spine_05",
        "neck": "neck_01",
        "Head": "head",
        "head_end": "head",
        "headfront": "head",
    }
    for side, suffix in [("Left", "_l"), ("Right", "_r")]:
        for src, dst in zip(
            ["Shoulder", "Arm", "ForeArm", "Hand", "UpLeg", "Leg", "Foot", "ToeBase"],
            [
                "clavicle",
                "upperarm",
                "lowerarm",
                "hand",
                "thigh",
                "calf",
                "foot",
                "ball",
            ],
        ):
            mapping[side + src] = dst + suffix
    children = {
        "Hips": "Spine02",
        "Spine02": "Spine01",
        "Spine01": "Spine",
        "Spine": "neck",
        "neck": "Head",
    }
    for side in ("Left", "Right"):
        for chain in (
            ["Shoulder", "Arm", "ForeArm", "Hand"],
            ["UpLeg", "Leg", "Foot", "ToeBase"],
        ):
            children.update({side + a: side + b for a, b in zip(chain, chain[1:])})
    transforms = {}
    for name, dst in mapping.items():
        anchor = "Head" if name in ("head_end", "headfront") else name
        src_pos, end_pos = source[anchor], target[dst]
        q = (0, 0, 0, 1)
        if name in children:
            child = children[name]
            q = align(
                [source[child][i] - src_pos[i] for i in AXES],
                [target[mapping[child]][i] - end_pos[i] for i in AXES],
            )
        transforms[name] = (src_pos, end_pos, q)
    out.doc["nodes"] = copy.deepcopy(rig.doc["nodes"])
    out.doc["scenes"] = copy.deepcopy(rig.doc["scenes"])
    for node in out.doc["nodes"]:
        if "mesh" in node:
            node["mesh"] = 0
    out.doc["skins"] = [
        dict(
            skin,
            inverseBindMatrices=out.data(
                rig.values(skin["inverseBindMatrices"]), "MAT4"
            ),
        )
    ]
    lookup = {
        rig.doc["nodes"][node]["name"]: i for i, node in enumerate(skin["joints"])
    }
    source_names = [
        base.doc["nodes"][j]["name"] for j in base.doc["skins"][0]["joints"]
    ]

    def materials(asset, prefix):
        first = len(out.doc["materials"])
        translated = {}
        for i, t in enumerate(asset.doc.get("textures", [])):
            img = asset.doc["images"][t["source"]]
            translated[i] = out.image(
                asset.view(img["bufferView"]), img["mimeType"], prefix + str(i)
            )
        bronze = prefix in ("RightPlate", "LeftPlate")
        if bronze:
            patina = out.image((textures / "metal-color.jpg").read_bytes(), "image/jpeg", prefix + "Patina")
            pitting = out.image((textures / "metal-normal.jpg").read_bytes(), "image/jpeg", prefix + "Hammer")
        for i, original in enumerate(asset.doc["materials"]):
            m = copy.deepcopy(original)
            m["name"] = prefix + "_" + str(i)
            for slots in (m, m.get("pbrMetallicRoughness", {})):
                for k, v in slots.items():
                    if k.endswith("Texture") and isinstance(v, dict):
                        v["index"] = translated[v["index"]]["index"]
            if prefix == "Mantle" and original.get("name") == "Woven heron brocade":
                m["pbrMetallicRoughness"]["baseColorTexture"] = out.image(
                    (textures / "pilgrim-brocade-color.jpg").read_bytes(),
                    "image/jpeg",
                    "HeronBrocade",
                )
                m["normalTexture"] = out.image(
                    (textures / "pilgrim-brocade-normal.jpg").read_bytes(),
                    "image/jpeg",
                    "HeronStitch",
                )
            if bronze and original.get("name") == "Cast bronze":
                m["pbrMetallicRoughness"].update(baseColorTexture=patina,
                    baseColorFactor=[.74,.71,.61,1], roughnessFactor=.52, metallicFactor=.67)
                m["normalTexture"] = dict(pitting, scale=.47)
            if wayfarer and prefix == "Pilgrim":
                m["pbrMetallicRoughness"]["baseColorTexture"] = out.image(
                    (art / "Wayfarer" / "leather.jpg").read_bytes(), "image/jpeg", "TravelLeather")
                m.pop("emissiveTexture", None)
                m["emissiveFactor"] = [0,0,0]
            if bellwarden and prefix == "Pilgrim":
                m.pop("emissiveTexture", None)
                m["emissiveFactor"] = [0, 0, 0]
                m.pop("extensions", None)
                m["pbrMetallicRoughness"].update(baseColorFactor=[.30, .20, .13, 1],
                                                 roughnessFactor=.84, metallicFactor=.04)
            out.doc["materials"].append(m)
        return first

    def primitive(asset, prim, positions, normals, joints, weights, material):
        src = prim["attributes"]
        attrs = {
            "POSITION": out.data(positions, "VEC3", bounds=True),
            "NORMAL": out.data(normals, "VEC3"),
            "JOINTS_0": out.data(joints, "VEC4", 5123),
            "WEIGHTS_0": out.data(weights, "VEC4"),
        }
        for attr in ("TEXCOORD_0", "COLOR_0"):
            if attr in src:
                a = asset.doc["accessors"][src[attr]]
                attrs[attr] = out.data(
                    asset.values(src[attr]), a["type"], a["componentType"]
                )
                if a.get("normalized"):
                    out.doc["accessors"][attrs[attr]]["normalized"] = True
        # Keep the authored winding and UVs; the engine derives tangents after fitting.
        p = {"attributes": attrs, "material": material}
        if "indices" in prim:
            p["indices"] = out.data(asset.values(prim["indices"]), "SCALAR", 5125)
        out.doc["meshes"][0]["primitives"].append(p)

    offset = materials(base, "Pilgrim")
    for prim in base.doc["meshes"][0]["primitives"]:
        a = prim["attributes"]
        vertices = []
        normals = []
        joints = []
        weights = base.values(a["WEIGHTS_0"])
        for pos, nor, ids, ws in zip(
            base.values(a["POSITION"]),
            base.values(a["NORMAL"]),
            base.values(a["JOINTS_0"]),
            weights,
        ):
            new = [0.0, 0.0, 0.0]
            normal = [0.0, 0.0, 0.0]
            mapped = tuple(lookup[mapping[source_names[i]]] for i in ids)
            for i, w in zip(ids, ws):
                if w <= 0:
                    continue
                origin, dest, q = transforms[source_names[i]]
                delta = rotate(q, tuple(pos[k] - origin[k] for k in AXES))
                direction = rotate(q, nor)
                for k in AXES:
                    new[k] += w * (dest[k] + delta[k])
                    normal[k] += w * direction[k]
            vertices.append(new)
            normals.append(unit(normal))
            joints.append(mapped)
        primitive(
            base, prim, vertices, normals, joints, weights, offset + prim["material"]
        )
        if wayfarer:
            # Keep the original gloves, trousers and boots underneath the tailoring.
            keep = []
            for position, joint_ids, influence in zip(vertices, base.values(a["JOINTS_0"]), weights):
                glove = any("Hand" in source_names[i] and w > 0.44
                            for i, w in zip(joint_ids, influence))
                keep.append(position[1] < 0.81 or glove)
            indices = base.values(prim["indices"])
            kept = []
            for i in range(0, len(indices), 3):
                face = indices[i:i + 3]
                if all(keep[index] for index, in face):
                    kept.extend(face)
            out.doc["meshes"][0]["primitives"][-1]["indices"] = out.data(kept, "SCALAR", 5125)

    gear = [
        ("PilgrimRainHat", "Bamboo", "head"),
        ("PilgrimScabbard", "SwordCase", "pelvis"),
        ("PilgrimMantle", "Mantle", "spine_05"),
    ]
    if wayfarer:
        gear = [item for item in gear if item[1] == "SwordCase"]
    if armed:
        gear.append(("PilgrimJian", "Jian", "hand_r"))
    if bellwarden:
        gear = [
            ("BellwardenLeftPauldron", "LeftPlate", "upperarm_l"),
            ("BellwardenRightPauldron", "RightPlate", "upperarm_r"),
            ("tide-bell", "Toll", "hand_r"),
        ]
    if heron:
        gear = [
            ("HeronBridalMask", "Porcelain", "head"),
            ("HeronSabres", "Sabres", "hand_r"),
        ]
    if cinder:
        gear = [
            ("CinderVotiveHead", "Votive", "head"),
            ("CinderArmGuards", "Cuffs", "upperarm_l"),
            ("SaintsRingStaff", "Khakkhara", "hand_r"),
        ]
    for file, prefix, bone in gear:
        asset = Glb((textures if prefix == "Toll" else art) / (file + ".glb"))
        offset = materials(asset, prefix)
        parents = (
            {
                child: parent
                for parent in asset.doc["nodes"]
                for child in parent.get("children", [])
            }
            if cinder
            else {}
        )
        for node_id, node in enumerate(asset.doc["nodes"]):
            if "mesh" not in node:
                continue
            if cinder:
                parent = parents[node_id]["name"]
                if prefix == "Cuffs":
                    bone = ("lowerarm" if "forearm" in parent else "upperarm") + (
                        "_r" if parent.startswith("Right") else "_l"
                    )
                elif prefix == "Votive":
                    bone = "spine_05" if "mandorla" in parent else "head"
            if heron and prefix == "Sabres":
                bone = "hand_l" if node["name"].startswith("Left") else "hand_r"
            m = node.get("matrix")
            if m:

                def pose(p):
                    return tuple(
                        sum(m[j * 4 + k] * p[j] for j in AXES) + m[12 + k] for k in AXES
                    )

                def axis(n):
                    return unit(
                        tuple(sum(m[j * 4 + k] * n[j] for j in AXES) for k in AXES)
                    )
            else:
                q = node.get("rotation", (0, 0, 0, 1))
                s = node.get("scale", (1, 1, 1))
                t = node.get("translation", (0, 0, 0))

                def pose(p):
                    return tuple(
                        x + y
                        for x, y in zip(rotate(q, [v * f for v, f in zip(p, s)]), t)
                    )

                def axis(n):
                    return unit(rotate(q, [v / f for v, f in zip(n, s)]))

            for prim in asset.doc["meshes"][node["mesh"]]["primitives"]:
                a = prim["attributes"]
                vs = []
                ns = []
                js = []
                ws = []
                for p, n in zip(asset.values(a["POSITION"]), asset.values(a["NORMAL"])):
                    x, y, z = pose(p)
                    normal = axis(n)
                    bones = [bone]
                    w = [1.0]
                    if bellwarden:
                        # Shoulder castings sit over the upper arms. The bell hangs
                        # mouth down with the fingers gripping its crown.
                        scale = 0.32 if prefix == "Toll" else 0.48
                        x, y, z = [v * scale + a for v, a in zip((x, y, z), target[bone])]
                        y += -0.57 if prefix == "Toll" else 0.045
                    elif cinder:
                        if prefix == "Votive":
                            scale = 0.49
                            shift = (
                                (0, 0.34, -0.20)
                                if bone == "spine_05"
                                else (0, 0.06, -0.095)
                            )
                        elif prefix == "Cuffs":
                            scale = 0.52
                            shift = (0, 0.01, 0)
                        else:
                            scale = 0.85
                            turn = align((0, 1, 0), (0.04, 0.60, 0.80))
                            x, y, z = rotate(turn, (x, y, z))
                            normal = rotate(turn, normal)
                            shift = (0, 0, 0)
                        x, y, z = [
                            v * scale + a + d
                            for v, a, d in zip((x, y, z), target[bone], shift)
                        ]
                    elif heron:
                        if prefix == "Porcelain":
                            x, y, z = [v * 0.79 + a for v, a in zip((x, y, z), target[bone])]
                            y += 0.11
                            z += 0.065
                        else:
                            # Fit each local wrist independently in the target bind pose.
                            turn = align((0, 1, 0), (0.28 if bone == "hand_l" else -0.28, 0.1, 1))
                            x, y, z = [v * 0.87 + a for v, a in zip(rotate(turn,(x,y,z)), target[bone])]
                            normal = rotate(turn, normal)
                    elif prefix == "Jian":
                        turn = align((0, 1, 0), (0, .16, 1))
                        x, y, z = [v + a for v, a in zip(rotate(turn, (x, y, z)), target[bone])]
                        normal = rotate(turn, normal)
                    elif prefix == "Bamboo":
                        x += target["head"][0]
                        y += target["head"][1] + 0.216
                        z += target["head"][2]
                    elif prefix == "SwordCase":
                        if wayfarer:
                            x, y, z = .77 * x, .87 * y, .77 * z
                        turn = align((0, -1, 0), (0.22, -0.84, -0.5))
                        x, y, z = rotate(turn, (x, y, z))
                        x += 0.21
                        y += 1.035
                        z -= 0.005
                        normal = rotate(turn, normal)
                    else:
                        # Skirt panels follow the near thigh below the belt. Blend the
                        # upper mantle across the rib cage to keep its collar seated.
                        if y < 1.16:
                            thigh = "thigh_l" if x > 0 else "thigh_r"
                            leg = max(0, min(0.76, (1.12 - y) * 1.9))
                            bones = ["pelvis", thigh]
                            w = [1 - leg, leg]
                        else:
                            rib = max(0, min(1, (y - 1.13) / 0.28))
                            bones = ["spine_02", "spine_05"]
                            w = [1 - rib, rib]
                        y -= 0.028
                    vs.append((x, y, z))
                    ns.append(normal)
                    js.append(([lookup[b] for b in bones] + [0] * 4)[:4])
                    ws.append((w + [0.0] * 4)[:4])
                primitive(asset, prim, vs, ns, js, ws, offset + prim["material"])
    if bellwarden:
        add_regalia = runpy.run_path(str(Path(__file__).with_name("keeper_regalia.py")))["add_regalia"]
        add_regalia(out, lookup, textures)
    if heron:
        add_dress = runpy.run_path(str(Path(__file__).with_name("heron_dress.py")))["add_dress"]
        add_dress(out, lookup, target, textures)
    if cinder:
        add_stole = runpy.run_path(str(Path(__file__).with_name("cinder_vestment.py")))["stole"]
        add_stole(out, lookup, textures)
    if wayfarer:
        from wayfarer_outfit import dress
        dress(out, lookup, target, art / "Wayfarer")
    out.save(output)
