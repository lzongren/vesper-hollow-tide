"""Project a worn cinnabar inscription onto the original scan's own UV islands."""

import argparse
import sys
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "native/Scripts"))
from bind_pilgrim import Glb


def glyphs(font_file):
    mask = Image.new("L", (448, 896))
    font = ImageFont.truetype(str(font_file), 404)
    draw = ImageDraw.Draw(mask)
    for j, char in enumerate("松壑"):
        left, top, right, bottom = font.getbbox(char)
        draw.text(
            ((448 - right - left) / 2, 448 * j + (448 - bottom - top) / 2),
            char,
            255,
            font,
        )
    return np.asarray(mask)


def project(glb, shape, ink):
    face = glb.doc["meshes"][0]["primitives"][0]
    attrs = face["attributes"]
    positions, normals, uvs = [
        np.array(glb.values(attrs[k])) for k in ("POSITION", "NORMAL", "TEXCOORD_0")
    ]
    triangles = np.array(glb.values(face["indices"])).reshape(-1, 3)
    h, w = shape
    mask = np.zeros(shape, np.float32)
    for tri in triangles:
        pts = positions[tri]
        if (
            pts[:, 0].max() < -0.67
            or pts[:, 0].min() > 0.54
            or pts[:, 1].max() < 0.62
            or pts[:, 1].min() > 2.98
            or normals[tri, 2].max() < 0.19
        ):
            continue
        uv = uvs[tri] * [w, h] - 0.5
        x0, y0 = np.maximum(np.floor(uv.min(axis=0)).astype(int), 0)
        x1, y1 = np.minimum(np.ceil(uv.max(axis=0)).astype(int), [w - 1, h - 1])
        yy, xx = np.mgrid[y0 : y1 + 1, x0 : x1 + 1]
        ax, ay = uv[1] - uv[0]
        bx, by = uv[2] - uv[0]
        determinant = ax * by - ay * bx
        if abs(determinant) < 1e-8:
            continue
        dx, dy = xx - uv[0, 0], yy - uv[0, 1]
        u, v = (dx * by - dy * bx) / determinant, (ax * dy - ay * dx) / determinant
        weights = np.stack((1 - u - v, u, v), axis=-1)
        xyz = weights @ pts
        ix = (xyz[..., 0] + 0.67) / 1.21
        iy = (2.98 - xyz[..., 1]) / 2.36
        keep = (
            (weights.min(axis=-1) >= -0.002)
            & (ix >= 0)
            & (ix < 1)
            & (iy >= 0)
            & (iy < 1)
        )
        if not keep.any():
            continue
        facing = np.clip(((weights @ normals[tri, 2]) - 0.13) / 0.47, 0, 1)
        pigment = ink[
            np.minimum((iy[keep] * ink.shape[0]).astype(int), ink.shape[0] - 1),
            np.minimum((ix[keep] * ink.shape[1]).astype(int), ink.shape[1] - 1),
        ]
        y, x = yy[keep], xx[keep]
        mask[y, x] = np.maximum(mask[y, x], pigment * facing[keep] / 255)
    return mask


def bake(scan, font, dest):
    g = Glb(scan)

    def image_at(tex):
        image = g.doc["images"][g.doc["textures"][tex]["source"]]
        return Image.open(BytesIO(g.view(image["bufferView"]))).convert("RGB")

    mat = g.doc["materials"][0]
    albedo = image_at(mat["pbrMetallicRoughness"]["baseColorTexture"]["index"])
    base = np.asarray(albedo).astype(np.float32)
    mask = project(g, base.shape[:2], glyphs(font))
    if not 1000 < (mask > 0.5).sum() < mask.size * 0.17:
        raise ValueError("Inscription does not fit the scan")
    luma = np.asarray(albedo.convert("L")).astype(np.float32)
    smooth = np.asarray(albedo.convert("L").filter(ImageFilter.GaussianBlur(2))).astype(
        np.float32
    )
    # Exposed quartz and locally broken edges interrupt the pigment.
    stone = np.clip(1 - np.maximum(luma - smooth - 3, 0) / 25, 0.13, 1)
    strength = (mask * stone * 0.90)[..., None]
    paint = (
        np.array([150, 48, 27])
        * (0.58 + 0.48 * np.clip(luma / 120, 0, 1.35))[..., None]
    )
    dest.mkdir(parents=True, exist_ok=True)
    Image.fromarray(
        np.uint8(np.clip(base * (1 - strength) + paint * strength, 0, 255))
    ).save(dest / "RavineInk.jpg", quality=96, subsampling=0)
    # Displace the original tangent normals at the cut lip of each stroke.
    bevel = (
        np.asarray(
            Image.fromarray(np.uint8(mask * 255)).filter(ImageFilter.GaussianBlur(0.80))
        ).astype(np.float32)
        / 255
    )
    dy, dx = np.gradient(bevel)
    n = (
        np.asarray(image_at(mat["normalTexture"]["index"])).astype(np.float32) / 127.5
        - 1
    )
    n[..., 0] += 1.30 * dx
    n[..., 1] -= 1.30 * dy
    n /= np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-6)
    n[..., 1] *= -1
    Image.fromarray(np.uint8(np.clip(n * 127.5 + 127.5, 0, 255))).save(
        dest / "RavineInkNormal.jpg", quality=97, subsampling=0
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for arg in ("scan", "font", "dest"):
        p.add_argument(arg, type=Path)
    args = p.parse_args()
    bake(args.scan, args.font, args.dest)
