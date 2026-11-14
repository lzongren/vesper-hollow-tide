"""Bake registered roughness, metal and relief from the three painted medallions."""
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

ART = Path(__file__).resolve().parents[1] / "public" / "art"


def blur(field, sigma):
    image = Image.fromarray(np.uint8(np.clip(field, 0, 1) * 255))
    return np.asarray(image.filter(ImageFilter.GaussianBlur(sigma)), dtype=np.float32) / 255


def bake(name):
    im = Image.open(ART / f"{name}-inlay.jpg").convert("RGB")
    im.thumbnail((1536, 1536), Image.Resampling.LANCZOS)
    r, g, b = (np.asarray(im, dtype=np.float32) / 255).transpose(2, 0, 1)
    light = r * 0.28 + g * 0.55 + b * 0.17
    baseline = blur(light, 8)
    detail = light - baseline
    # Gilding and oxidized copper have distinct chroma. The crane court is
    # a pale stone mosaic and has no warm metal channel.
    metal = np.clip((r - b - 0.075) * 5, 0, 1) if name != "heron" else np.zeros_like(light)
    pale = np.clip((baseline - 0.35) * 2.7, 0, 1)
    ridge = np.clip(detail * 3, -0.55, 0.55)
    rough = np.clip(0.84 - 0.25 * metal - 0.16 * pale + 0.14 * ridge, 0.43, 0.93)
    # Red holds local drainage, green roughness, blue metalness.
    drainage = np.clip(0.51 + 0.62 * ridge + 0.23 * metal + 0.12 * pale, 0, 1)
    packed = np.stack([drainage, rough, metal * 0.82], axis=-1)
    Image.fromarray(np.uint8(packed * 255)).save(ART / f"{name}-surface.jpg", quality=88, subsampling=0)
    height = 1.5 * blur(light, 1.3) + 0.7 * blur(pale, 2) + 1.2 * blur(metal, 1.4) + 0.24 * detail
    dy, dx = np.gradient(height)
    normal = np.stack([-dx, dy, np.ones_like(dx)], axis=-1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    Image.fromarray(np.uint8(127.5 * (1 + normal))).save(ART / f"{name}-relief.jpg", quality=91, subsampling=0)


if __name__ == "__main__":
    for court in ("belfry", "heron", "cinder"):
        bake(court)
