"""Sculpt the Ashen Reliquary guardian against its painted source in image space."""

from io import BytesIO
import json
from pathlib import Path
import struct

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "public/art/cinder-mask.jpg"
TARGET = ROOT / "public/models/cinder-relief.glb"


def sculpt(cols=225, rows=151):
    # Coordinates below are traced on a 740 x 493 study of the original painting.
    x, y = np.meshgrid(np.linspace(0, 740, cols), np.linspace(0, 493, rows))
    # Work outward from the medial axis once for both sides of the casting.
    left = np.minimum(x, 740 - x)
    depth = np.zeros_like(x)
    gilt = np.zeros_like(x)

    def dome(cx, cy, rx, ry):
        squared = ((left - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
        return np.maximum(1 - squared, 0) ** 1.35

    def sweep(points):
        # Interpolate centre, radius and height along the same smooth spline.
        knots = np.array([points[0], *points, points[-1]], dtype=float)
        result = np.zeros_like(x)
        for i in range(1, len(knots) - 2):
            a, b, c, d = knots[i - 1 : i + 3]
            for t in np.linspace(0, 1, 9):
                cx, cy, radius, height = 0.5 * (
                    2 * b
                    + (-a + c) * t
                    + (2 * a - 5 * b + 4 * c - d) * t * t
                    + (-a + 3 * b - 3 * c + d) * t**3
                )
                distance = ((left - cx) ** 2 + (y - cy) ** 2) / radius**2
                profile = np.sqrt(np.maximum(1 - distance, 0))
                np.maximum(result, height * profile**1.5, out=result)
        return result

    # The paired dragons double back at the knees. The upper coil comes
    # forward where it crosses the lower length of the body.
    coil = sweep(
        [
            (345, 423, 17, 0.24),
            (295, 388, 20, 0.31),
            (263, 335, 24, 0.46),
            (232, 341, 22, 0.52),
            (201, 379, 23, 0.44),
            (163, 410, 23, 0.34),
            (112, 412, 21, 0.34),
            (89, 385, 19, 0.32),
            (105, 344, 16, 0.24),
        ]
    )
    body = sweep(
        [
            (171, 392, 16, 0.24),
            (167, 352, 22, 0.41),
            (170, 303, 24, 0.59),
            (147, 267, 23, 0.63),
            (99, 246, 20, 0.61),
            (56, 240, 20, 0.56),
            (39, 207, 21, 0.57),
            (45, 174, 19, 0.64),
            (73, 146, 18, 0.70),
        ]
    )
    head = sweep(
        [
            (61, 153, 22, 0.57),
            (84, 136, 23, 0.80),
            (110, 125, 18, 0.89),
            (144, 115, 11, 0.76),
            (175, 112, 5, 0.64),
        ]
    )
    jaw = sweep(
        [
            (86, 137, 14, 0.55),
            (113, 146, 13, 0.65),
            (139, 167, 9, 0.58),
            (158, 177, 4, 0.46),
        ]
    )
    horn = sweep(
        [
            (275, 111, 24, 0.63),
            (243, 100, 23, 0.84),
            (222, 78, 18, 0.78),
            (216, 50, 13, 0.58),
            (226, 24, 8, 0.42),
            (242, 5, 2, 0.16),
        ]
    )
    fang = sweep([(324, 215, 10, 0.95), (319, 232, 8, 1.03), (307, 253, 3, 0.75)])
    cheek = sweep(
        [
            (272, 268, 21, 0.45),
            (269, 244, 24, 0.68),
            (281, 213, 25, 0.92),
            (309, 202, 19, 1.03),
            (330, 195, 12, 0.91),
        ]
    )
    brow = sweep(
        [
            (269, 120, 12, 0.75),
            (293, 139, 17, 1.12),
            (321, 146, 17, 1.35),
            (343, 137, 13, 1.28),
            (357, 143, 6, 1.05),
        ]
    )
    depth = np.maximum.reduce([depth, coil, body, head, jaw, horn])
    face = 0.94 * dome(370, 185, 120, 139) + 0.38 * dome(370, 121, 83, 65)
    face += 0.91 * dome(370, 193, 43, 33) + 0.39 * dome(370, 274, 42, 28)
    face += 0.58 * dome(321, 165, 19, 14) + 0.35 * dome(370, 94, 25, 23)
    depth = np.maximum.reduce(
        [depth, face, cheek, brow, fang, 0.50 * dome(370, 310, 27, 41)]
    )
    gilt = np.maximum.reduce(
        [
            gilt,
            body * 0.58,
            head * 0.74,
            horn * 0.38,
            brow * 0.34,
            fang * 0.72,
            0.82 * dome(321, 165, 15, 10),
            dome(370, 94, 22, 21),
        ]
    )

    with Image.open(SOURCE) as source:
        gray = source.convert("L").resize((cols, rows), Image.Resampling.LANCZOS)
        pigment = np.array(gray, dtype=float) / 255
        broad = np.array(gray.filter(ImageFilter.GaussianBlur(2.6)), dtype=float) / 255
    # Local chisel marks are a shallow final pass over the authored volumes.
    depth += (pigment - broad) * 0.17 + broad * 0.09
    z = depth - 0.29 * ((x - 370) / 370) ** 2
    positions = np.stack(((x / 740 - 0.5) * 10.8, (0.5 - y / 493) * 7.8, z), axis=-1)
    dy, dx = np.gradient(positions, axis=(0, 1))
    normal = np.cross(dy, dx)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    uv = np.stack((x / 740, y / 493), axis=-1)
    idx = np.arange(cols * rows, dtype=np.uint16).reshape(rows, cols)
    a, b, c, d = idx[:-1, :-1], idx[1:, :-1], idx[:-1, 1:], idx[1:, 1:]
    faces = np.stack((a, b, c, c, b, d), axis=-1)
    return positions, normal, uv, faces, gilt, pigment


def build():
    position, normal, uv, faces, gilding, pigment = sculpt()
    data = bytearray()
    views, accessors = [], []

    def view(raw, target=None):
        data.extend(b"\x00" * (-len(data) % 4))
        item = {"buffer": 0, "byteOffset": len(data), "byteLength": len(raw)}
        if target:
            item["target"] = target
        views.append(item)
        data.extend(raw)
        return len(views) - 1

    def attribute(arr, width, kind):
        is_index = width == 1
        arr = np.ascontiguousarray(arr, dtype="<u2" if is_index else "<f4").reshape(
            -1, width
        )
        info = {
            "bufferView": view(arr.tobytes(), 34963 if is_index else 34962),
            "componentType": 5123 if is_index else 5126,
            "count": len(arr),
            "type": kind,
        }
        if not accessors:
            info.update(min=arr.min(axis=0).tolist(), max=arr.max(axis=0).tolist())
        accessors.append(info)
        return len(accessors) - 1

    attributes = {
        "POSITION": attribute(position, 3, "VEC3"),
        "NORMAL": attribute(normal, 3, "VEC3"),
        "TEXCOORD_0": attribute(uv, 2, "VEC2"),
    }
    indices = attribute(faces, 1, "SCALAR")
    # The worn raised bronze takes a tighter highlight than the sooty recesses.
    channels = np.stack(
        (
            np.ones_like(gilding),
            np.clip(0.88 - 0.42 * gilding - 0.11 * pigment, 0, 1),
            np.clip(0.17 + 0.70 * gilding, 0, 1),
        ),
        axis=-1,
    )
    orm = BytesIO()
    Image.fromarray(np.uint8(channels * 255)).save(orm, format="PNG")
    images = [
        {"bufferView": view(SOURCE.read_bytes()), "mimeType": "image/jpeg"},
        {"bufferView": view(orm.getvalue()), "mimeType": "image/png"},
    ]
    doc = {
        "asset": {"version": "2.0", "generator": "Vesper shrine relief"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"name": "Guardian and paired dragons", "mesh": 0}],
        "meshes": [
            {
                "primitives": [
                    {"attributes": attributes, "indices": indices, "material": 0}
                ]
            }
        ],
        "materials": [
            {
                "name": "Gilt fire-darkened bronze",
                "pbrMetallicRoughness": {
                    "baseColorTexture": {"index": 0},
                    "metallicRoughnessTexture": {"index": 1},
                },
            }
        ],
        "images": images,
        "textures": [{"source": 0}, {"source": 1}],
        "buffers": [{"byteLength": len(data)}],
        "bufferViews": views,
        "accessors": accessors,
    }
    meta = json.dumps(doc, separators=(",", ":")).encode()
    meta += b" " * (-len(meta) % 4)
    data.extend(b"\x00" * (-len(data) % 4))
    TARGET.write_bytes(
        struct.pack(
            "<4sIIII", b"glTF", 2, 28 + len(meta) + len(data), len(meta), 0x4E4F534A
        )
        + meta
        + struct.pack("<II", len(data), 0x004E4942)
        + data
    )


if __name__ == "__main__":
    build()
