"""Recast rvscanners' digitized porcelain lion for the entrance to the bell court."""

import argparse
import hashlib
from pathlib import Path
import sys

import fast_simplification
import numpy as np
from scipy.ndimage import gaussian_filter, map_coordinates
from scipy.spatial import cKDTree
import trimesh
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "native/Scripts"))
from bind_pilgrim import Output

SOURCE_SHA256 = "464941acc455abd8142194baa65613dd3c8ab5400efe7c925cbc0169bc1251b9"


def casting(source):
    if hashlib.sha256(source.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError("Expected the archived rvscanners guardian lion")
    original = trimesh.load_scene(source).to_mesh()
    original.merge_vertices(merge_tex=True, merge_norm=True)
    v, f = fast_simplification.simplify(
        original.vertices, original.faces, target_count=185000
    )
    a = np.radians(61.5)
    rotation = np.array(
        [[np.cos(a), 0, -np.sin(a)], [0, 1, 0], [np.sin(a), 0, np.cos(a)]]
    )
    v = v @ rotation
    lo, hi = v.min(axis=0), v.max(axis=0)
    v -= [(hi[0] + lo[0]) / 2, lo[1], (hi[2] + lo[2]) / 2]
    v *= 2.82 / (hi[1] - lo[1])
    v[:, 1] += 0.26
    return trimesh.Trimesh(v, f, process=False)


def field(v, frequency, seed):
    rng = np.random.default_rng(seed)
    cube = gaussian_filter(rng.standard_normal((64, 64, 64)), 1.05, mode="wrap")
    result = map_coordinates(cube, v.T * frequency + 21, order=1, mode="grid-wrap")
    return np.clip(result / cube.std(), -2.8, 2.8)


def alloy(mesh):
    v, n = mesh.vertices, mesh.vertex_normals
    # The signed offset from the surrounding surface separates proud details
    # from recesses, independently of a directional light or a camera.
    near = cKDTree(v).query(v, k=55, workers=4)[1]
    centre = v[near].mean(axis=1)
    relief = np.einsum("ij,ij->i", v - centre, n)
    wear = np.clip(relief / 0.007, 0, 1)
    pocket = np.clip(-relief / 0.006, 0, 1)
    bloom = field(v, 9.4, 83)
    grain = field(v, 39, 24)
    base = np.clip(
        0.35 + 0.18 * bloom + 0.085 * grain + 0.50 * pocket - 0.45 * wear, 0, 1
    )
    oxide = base**1.4
    bronze = np.array([0.31, 0.147, 0.052])
    verdigris = np.array([0.044, 0.147, 0.122])
    high = np.array([0.50, 0.278, 0.095])
    metal = bronze + (high - bronze) * wear[:, None]
    rgb = metal + (verdigris - metal) * oxide[:, None]
    rgb *= np.clip(0.94 + 0.075 * grain - 0.18 * pocket, 0.60, 1.13)[:, None]
    rough = 0.41 + 0.40 * oxide - 0.07 * wear
    metallic = 0.83 - 0.48 * oxide
    return rgb, np.column_stack((rough, metallic))


def footing(mesh):
    # Two shallow grey limestone courses, with bevels following the lion pedestal.
    dx, dz = np.ptp(mesh.vertices, axis=0)[[0, 2]] / 2
    levels = [
        (-0.025, 0.13),
        (0.025, 0.15),
        (0.105, 0.15),
        (0.128, 0.13),
        (0.14, 0.073),
        (0.20, 0.073),
        (0.217, 0.09),
        (0.25, 0.09),
        (0.274, 0.070),
    ]
    verts = []
    for h, overhang in levels:
        x, z = dx + overhang, dz + overhang
        c = 0.062
        verts.extend(
            [
                (x - c, h, z),
                (x, h, z - c),
                (x, h, -z + c),
                (x - c, h, -z),
                (-x + c, h, -z),
                (-x, h, -z + c),
                (-x, h, z - c),
                (-x + c, h, z),
            ]
        )
    faces = []
    for j in range(len(levels) - 1):
        for i in range(8):
            a = j * 8 + i
            b = j * 8 + (i + 1) % 8
            faces.extend(((a, b, b + 8), (a, b + 8, a + 8)))
    for i in range(1, 7):
        faces.append((0, i + 1, i))
        k = len(verts) - 8
        faces.append((k, k + i, k + i + 1))
    stone = trimesh.Trimesh(verts, faces, process=False)
    stone.fix_normals()
    return stone


def bake(source, output):
    lion = casting(source)
    bronze, mask = alloy(lion)
    slab = footing(lion)
    out = Output()
    out.doc.update(nodes=[], meshes=[], scenes=[{"nodes": [0, 1]}])
    for index, (name, model, colors, params) in enumerate(
        (
            ("CastLion", lion, bronze, mask),
            (
                "CarvedFoot",
                slab,
                np.tile([0.145, 0.161, 0.151], (len(slab.vertices), 1)),
                np.tile([0.86, 0.025], (len(slab.vertices), 1)),
            ),
        )
    ):
        out.doc["materials"].append(
            dict(
                name=name + "Finish",
                pbrMetallicRoughness=dict(
                    metallicFactor=0.65 if index == 0 else 0.025,
                    roughnessFactor=0.60 if index == 0 else 0.86,
                ),
            )
        )
        attributes = dict(
            POSITION=out.data(model.vertices, "VEC3", bounds=True),
            NORMAL=out.data(model.vertex_normals, "VEC3"),
            COLOR_0=out.data(colors, "VEC3"),
            TEXCOORD_0=out.data(params, "VEC2"),
        )
        out.doc["meshes"].append(
            dict(
                name=name,
                primitives=[
                    dict(
                        attributes=attributes,
                        indices=out.data(model.faces.reshape(-1, 1), "SCALAR", 5125),
                        material=index,
                    )
                ],
            )
        )
        out.doc["nodes"].append(dict(name=name, mesh=index))
    out.doc["asset"].update(
        generator="Vesper bell court foundry",
        copyright="Lion geometry derived from Chinese guardian lion by rvscanners, CC BY 4.0",
    )
    out.save(output)
    # Convert the rusty-metal scan into a deposition mask. The native shader
    # interprets this luminance as the coverage of copper oxides.
    scan = Path(__file__).resolve().parents[1] / "public/textures/metal-color.jpg"
    pixels = np.asarray(Image.open(scan).convert("RGB"), dtype=float) / 255
    stain = pixels[:, :, 0] - pixels[:, :, 2]
    coarse = gaussian_filter(stain, 13, mode="wrap")
    alpha = np.clip(0.21 + 0.83 * stain + 0.23 * coarse, 0.15, 0.90)
    encoded = np.where(
        alpha <= 0.0031308, 12.92 * alpha, 1.055 * alpha ** (1 / 2.4) - 0.055
    )
    Image.fromarray(np.uint8(255 * encoded)).convert("RGB").save(
        output.with_name("CastingBloom.jpg"), quality=95
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    bake(args.source, args.output)
