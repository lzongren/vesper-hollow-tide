"""Bake an original spherical HDR overcast sky with a break in its cloud deck."""

import math
import sys
from pathlib import Path

import numpy as np


def smooth(x):
    return x * x * (3 - 2 * x)


def value_noise(x, y, z, seed):
    ix, iy, iz = (np.floor(v).astype(np.int64) for v in (x, y, z))
    fx, fy, fz = (smooth(v - i) for v, i in zip((x, y, z), (ix, iy, iz)))
    total = np.zeros_like(x)
    for a in (0, 1):
        for b in (0, 1):
            for c in (0, 1):
                n = (
                    ((ix + a) * 73856093)
                    ^ ((iy + b) * 19349663)
                    ^ ((iz + c) * 83492791)
                    ^ seed
                )
                n = (n ^ (n >> 13)) * 1274126177
                v = ((n ^ (n >> 16)) & 65535) / 65535
                total += (
                    v
                    * (fx if a else 1 - fx)
                    * (fy if b else 1 - fy)
                    * (fz if c else 1 - fz)
                )
    return total


def write_hdr(path, image):
    h, w, _ = image.shape
    peak = np.maximum(image.max(axis=2), 1e-10)
    _, ex = np.frexp(peak)
    rgb = (image * np.exp2(8 - ex)[:, :, None]).clip(0, 255).astype(np.uint8)
    rgbe = np.concatenate((rgb, (ex + 128).astype(np.uint8)[:, :, None]), axis=2)
    with path.open("wb") as f:
        f.write(f"#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n-Y {h} +X {w}\n".encode())
        for row in rgbe:
            f.write(bytes((2, 2, w >> 8, w & 255)))
            for ch in row.T:
                for i in range(0, w, 128):
                    part = ch[i : i + 128]
                    f.write(bytes([len(part)]))
                    f.write(part.tobytes())


def bake(path, w=1536, h=768):
    lon = ((np.arange(w) + 0.5) / w * 2 - 1) * math.pi
    lat = (0.5 - (np.arange(h) + 0.5) / h) * math.pi
    x = np.cos(lat[:, None]) * np.cos(lon)
    y = np.cos(lat[:, None]) * np.sin(lon)
    z = np.broadcast_to(np.sin(lat[:, None]), x.shape)
    # A curved cloud layer keeps low clouds compressed toward the horizon.
    depth = 1 / (np.maximum(z, 0) + 0.24)
    qx = x * depth * 1.65
    qy = y * depth * 2.85
    qz = z * 1.7
    warp = value_noise(qx * 0.55, qy * 0.55, qz, 311)
    density = np.zeros_like(x)
    for i, weight in enumerate((0.50, 0.235, 0.137, 0.074, 0.035, 0.019)):
        k = 2.08**i
        density += weight * value_noise(
            (qx + warp * 0.72) * k,
            (qy - warp * 0.48) * k,
            qz * k + 13.7 * i,
            419 + i * 19,
        )
    # Light comes from a low opening behind the cloud front.
    sun = np.maximum(0, x * 0.71 - y * 0.65 + z * 0.27)
    opening = np.power(sun, 10)
    cloud = smooth(np.clip((density - 0.31 - opening * 0.085) / 0.35, 0, 1))
    overhead = np.maximum(z, 0) ** 0.52
    top = np.array([0.095, 0.162, 0.225])
    horizon = np.array([0.38, 0.38, 0.32])
    clear = horizon + (top - horizon) * overhead[:, :, None]
    clear += opening[:, :, None] * np.array([0.69, 0.41, 0.15])
    edge = np.maximum(0, 1 - np.abs(density - 0.48) * 7) * opening
    mass = (0.45 + 0.66 * (1 - cloud))[:, :, None] * np.array([0.115, 0.145, 0.175])
    mass += edge[:, :, None] * np.array([0.33, 0.225, 0.12])
    rgb = clear * (1 - cloud[:, :, None]) + mass * cloud[:, :, None]
    # Below-horizon radiance also contributes to the captured diffuse light.
    blend = smooth(np.clip(-z / 0.18, 0, 1))[:, :, None]
    rgb = rgb * (1 - blend) + np.array([0.085, 0.094, 0.087]) * blend
    write_hdr(path, rgb)


if __name__ == "__main__":
    bake(Path(sys.argv[1]))
