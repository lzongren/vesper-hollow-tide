"""Compare captured faces with the reference after a single similarity alignment."""

import argparse
import json
from pathlib import Path
import numpy as np
from PIL import Image
from fit_portrait_reference import CHECK, ROOT, align, landmarks


def compare(model):
    directory = ROOT / "docs/runtime/portrait-match"
    ref = ROOT / "native/Art/Wayfarer/spectre-face.jpg"
    target, size = landmarks(model, ref)
    reference = Image.open(ref).convert("RGB")
    images = [reference]
    results = {}
    span = np.linalg.norm(target[263, :2] - target[33, :2])
    held = [i for i in CHECK if i not in (33, 263)]
    for stage in ("before", "after"):
        path = directory / (stage + "-closed.jpg")
        src, _ = landmarks(model, path)
        m, t = align(target, src)
        aligned = (src[:, :2] - t) @ np.linalg.inv(m).T
        errors = np.linalg.norm(aligned - target[:, :2], axis=1)
        results[stage] = dict(
            mean_percent_of_outer_eye_span=round(100 * errors[held].mean() / span, 3),
            nose_vertical_px=round(float(aligned[1, 1] - target[1, 1]), 2),
            lip_vertical_px=round(float(aligned[13, 1] - target[13, 1]), 2),
            chin_vertical_px=round(float(aligned[152, 1] - target[152, 1]), 2),
        )
        # The crops use only scale, rotation and translation. The skin pixels
        # come from the Unreal screenshot, without retouching or relighting.
        img = (
            Image.open(path)
            .convert("RGB")
            .transform(
                size,
                Image.Transform.AFFINE,
                (m[0, 0], m[0, 1], t[0], m[1, 0], m[1, 1], t[1]),
                Image.Resampling.BICUBIC,
            )
        )
        images.append(img)
    montage(images, directory / "reference-before-after.jpg")

    guide = ROOT / "native/Art/Wayfarer/portrait-open.jpg"
    open_target, _ = landmarks(model, guide)
    opened = directory / "after-open.jpg"
    observed, _ = landmarks(model, opened)
    m, t = align(open_target, observed)
    posed = (
        Image.open(opened)
        .convert("RGB")
        .transform(
            size,
            Image.Transform.AFFINE,
            (m[0, 0], m[0, 1], t[0], m[1, 0], m[1, 1], t[1]),
            Image.Resampling.BICUBIC,
        )
    )
    montage(
        [Image.open(guide).convert("RGB"), posed], directory / "open-guide-and-game.jpg"
    )
    report = dict(
        reference_size=size,
        reference_outer_eye_span_px=round(span, 2),
        held_out=held,
        results=results,
    )
    (directory / "landmark-check.json").write_text(json.dumps(report, indent=2) + "\n")
    print(results)


def montage(images, destination):
    crop = (0.19, 0.18, 0.82, 0.89)
    panels = []
    for im in images:
        w, h = im.size
        panel = im.crop(
            tuple(round(v * (w if i % 2 == 0 else h)) for i, v in enumerate(crop))
        )
        panel.thumbnail((658, 740), Image.Resampling.LANCZOS)
        panels.append(panel)
    montage = Image.new(
        "RGB", (sum(p.width for p in panels) + 12, panels[0].height), (37, 36, 34)
    )
    at = 0
    for panel in panels:
        montage.paste(panel, (at, 0))
        at += panel.width + 6
    montage.save(destination, quality=95)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", type=Path)
    compare(parser.parse_args().model)
