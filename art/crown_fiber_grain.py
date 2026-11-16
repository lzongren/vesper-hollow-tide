"""Bake the dressed scalp's fiber grain in rest UVs from the profile hair study.

The default registration cage is the combed cap before its central fringe
was tucked into the root veil. Pass a fitted GLB to try a new registration.
Only local, neutral luminance differences
inside a hair-only matte are used. Skin, backdrop and lighting are excluded.
"""

import argparse
import json
import struct
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ART = Path(__file__).resolve().parents[1] / "native/Art/Wayfarer"
COLS, ROWS = 144, 38


def cap_grid(glb):
    with glb.open("rb") as f:
        ident, version, _ = struct.unpack("<4sII", f.read(12))
        if (ident, version) != (b"glTF", 2):
            raise ValueError("Expected the fitted GLB")
        length, kind = struct.unpack("<II", f.read(8))
        if kind != 0x4E4F534A:
            raise ValueError("Expected a JSON chunk")
        doc = json.loads(f.read(length))
        _, kind = struct.unpack("<II", f.read(8))
        origin = f.tell()
        names = [m["name"] for m in doc["materials"]]
        shared = "CrownSilk" not in names
        slot = names.index("InkHair" if shared else "CrownSilk")
        part = next(p for p in doc["meshes"][0]["primitives"] if p["material"] == slot)
        acc = doc["accessors"][part["attributes"]["POSITION"]]
        view = doc["bufferViews"][acc["bufferView"]]
        if (
            acc["componentType"] != 5126
            or view.get("byteStride", 12) != 12
            or kind != 0x004E4942
        ):
            raise ValueError("Expected packed GLB rest positions")
        # In 55/56 the cap follows the low chignon in a shared material.
        start = 49 * 25 if shared else 0
        size = (ROWS + 1) * (COLS + 1)
        if acc["count"] < start + size or (not shared and acc["count"] != size):
            raise ValueError("Unexpected dressed scalp topology")
        f.seek(
            origin + view.get("byteOffset", 0) + acc.get("byteOffset", 0) + 12 * start
        )
        return np.frombuffer(f.read(12 * size), "<f4").reshape(ROWS + 1, COLS + 1, 3)


def coverage_mask():
    # Inset the outer hair silhouette, then trace the hair side of the
    # forehead, helix and nape. The forehead feathering comes from geometry.
    matte = Image.new("L", (1254, 1254))
    ImageDraw.Draw(matte).polygon(
        [
            (146, 0),
            (755, 0),
            (831, 42),
            (899, 103),
            (935, 150),
            (952, 184),
            (942, 192),
            (901, 202),
            (858, 235),
            (814, 295),
            (768, 360),
            (724, 432),
            (685, 509),
            (654, 550),
            (624, 559),
            (584, 533),
            (545, 509),
            (499, 491),
            (463, 493),
            (430, 510),
            (401, 558),
            (387, 634),
            (367, 713),
            (351, 786),
            (320, 784),
            (253, 755),
            (197, 709),
            (147, 647),
            (104, 534),
            (101, 443),
            (78, 345),
            (72, 247),
            (90, 150),
        ],
        fill=255,
    )
    return (
        np.asarray(matte.filter(ImageFilter.GaussianBlur(11)), dtype=np.float32) / 255
    )


def sample(a, x, y):
    x = x.clip(0, a.shape[1] - 1.001)
    y = y.clip(0, a.shape[0] - 1.001)
    i, j = x.astype(int), y.astype(int)
    fx, fy = x - i, y - j
    return (1 - fy) * ((1 - fx) * a[j, i] + fx * a[j, i + 1]) + fy * (
        (1 - fx) * a[j + 1, i] + fx * a[j + 1, i + 1]
    )


def ease(v):
    t = v.clip(0, 1)
    return t * t * (3 - 2 * t)


def bake(glb, art, output):
    if glb is None:
        with np.load(
            Path(__file__).with_name("reference") / "crown-registration.npz"
        ) as data:
            grid = data["rest"]
        if grid.shape != (ROWS + 1, COLS + 1, 3) or not np.isfinite(grid).all():
            raise ValueError("Invalid crown registration cage")
    else:
        grid = cap_grid(glb)
    ref = Image.open(art / "sculpt-profile.jpg").convert("L")
    if ref.size != (1254, 1254):
        raise ValueError("Profile study must match the original camera registration")
    grey = np.asarray(ref, dtype=np.float32)
    near = np.asarray(ref.filter(ImageFilter.GaussianBlur(16)), dtype=np.float32)
    far = np.asarray(ref.filter(ImageFilter.GaussianBlur(50)), dtype=np.float32)
    grain = (grey - near) + 0.52 * (near - far)
    matte = coverage_mask()
    base = np.asarray(Image.open(art / "hair.jpg").convert("L"), dtype=np.float32)
    w, h = 4096, 1280
    u = (np.arange(w) + 0.5) / w
    a = u * 2 * np.pi
    out = np.empty((h, w, 3), dtype=np.uint8)
    tilt = np.deg2rad(88)
    # Same near eye and near commissure as the 88 degree fixed-game camera.
    q = (4 + 307j) / (19 + 371j)
    for yy in range(0, h, 32):
        v = 1 - (np.arange(yy, min(yy + 32, h))[:, None] + 0.5) / h
        p = np.stack([sample(grid[:, :, i], u * COLS, v * ROWS) for i in range(3)], -1)
        xx, zz = -abs(p[:, :, 0]), p[:, :, 2] - 0.08638235
        depth = -np.sin(tilt) * xx + np.cos(tilt) * zz
        scale = (1280 / np.tan(np.deg2rad(7))) / (2 - depth)
        pix = (
            956
            + 521j
            + q
            * (
                (-111 + scale * (np.cos(tilt) * xx + np.sin(tilt) * zz))
                - 1j * scale * (p[:, :, 1] - 1.65503121)
            )
        )
        x, y = pix.real, pix.imag
        # The unseen opposite temple gets its own small directional offset.
        x = x + 5 * np.maximum(0, np.sin(a)) * np.sin(3 * np.pi * v)
        weight = (
            sample(matte, x, y)
            * ease((y + 2) / 32)
            * ease((abs(np.sin(a)) - 0.055) / 0.27)
        )
        drift = np.sin(np.pi * v) * (
            0.18 * np.sin(2 * a + 0.7) + 0.09 * np.sin(5 * a - 2 * v)
        )
        b = sample(
            base,
            ((5 * u + drift) % 1) * (base.shape[1] - 1),
            (0.96 - 0.92 * v) * (base.shape[0] - 1),
        )
        old = 31 + 0.79 * (b - 30)
        new = 32 + 1.23 * sample(grain, x, y)
        tone = (1 - weight) * old + weight * new
        out[yy : yy + len(v)] = np.uint8(
            np.rint(tone[:, :, None] + [4, 0, -2]).clip(9, 102)
        )
    Image.fromarray(out).save(output, quality=94, subsampling=0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("glb", nargs="?", type=Path)
    parser.add_argument("--art", type=Path, default=ART)
    parser.add_argument("--out", type=Path, default=ART / "crown-fiber-grain.jpg")
    args = parser.parse_args()
    bake(args.glb, args.art, args.out)
