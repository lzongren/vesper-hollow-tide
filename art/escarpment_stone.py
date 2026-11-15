"""Grade the two CC0 Cliff Side scans for the shaded limestone clefts."""

import argparse
from hashlib import md5
from pathlib import Path

import numpy as np
from PIL import Image


def bake(diffuse, occlusion, output):
    for path, digest in (
        (diffuse, "6d129836144e271b30071281241e237d"),
        (occlusion, "2872dca209647f5723418eddbf63e059"),
    ):
        if md5(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f"Expected Poly Haven Cliff Side 2K JPEG at {path}")
    rgb = np.asarray(Image.open(diffuse).convert("RGB"), dtype=np.float32) / 255
    ao = np.asarray(Image.open(occlusion).convert("L"), dtype=np.float32) / 255
    luma = rgb @ [0.30, 0.56, 0.14]
    # Leave coarse fissures legible at the middle-distance mip levels.
    tone = np.clip((luma - 0.40) * 1.46 + 0.43, 0.10, 0.80)
    tone *= 0.51 + 0.49 * ao
    mineral = tone[..., None] * np.array([1.02, 1.025, 0.95])
    mineral += (rgb - luma[..., None]) * 0.11
    Image.fromarray(np.uint8(np.clip(mineral * 255, 0, 255))).save(output, quality=94)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("diffuse", "occlusion", "output"):
        parser.add_argument(key, type=Path)
    args = parser.parse_args()
    bake(args.diffuse, args.occlusion, args.output)
