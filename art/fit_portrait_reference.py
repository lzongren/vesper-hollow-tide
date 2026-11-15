"""Fit a landmark displacement field to a capture from probe_portrait_match.py.

Usage: python art/fit_portrait_reference.py face_landmarker.task old-player.glb
Reads the checked-in reference and baseline. The model is only used at art bake time.
"""

import argparse
import gzip
import json
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.interpolate import RBFInterpolator
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "native/Scripts"))
from bind_pilgrim import Glb

# Keep these independent of the fit for comparison against new engine renders.
CHECK = [
    1,
    13,
    14,
    33,
    61,
    70,
    93,
    98,
    107,
    152,
    234,
    263,
    291,
    300,
    323,
    327,
    336,
    454,
]
F = 1280 / np.tan(np.deg2rad(7))
CAM = np.array([0, 1.65503121, 2.08638235])


def landmarks(model, path):
    import mediapipe as mp
    from mediapipe.tasks.python import vision
    from mediapipe.tasks.python.core.base_options import BaseOptions

    pic = np.asarray(Image.open(path).convert("RGB"))
    h, w = pic.shape[:2]
    options = vision.FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(model)), num_faces=1
    )
    with vision.FaceLandmarker.create_from_options(options) as detector:
        result = detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=pic))
    if len(result.face_landmarks) != 1:
        raise ValueError(f"One detectable face required in {path}")
    return np.array(
        [(v.x * w, v.y * h, v.z * w) for v in result.face_landmarks[0][:468]]
    ), (w, h)


def align(reference, observed):
    # Two outer canthi determine translation, isotropic size and roll.
    re = reference[[33, 263], :2]
    se = observed[[33, 263], :2]
    a, b = re[1] - re[0], se[1] - se[0]
    denom = a @ a
    c = (a @ b) / denom
    s = (a[0] * b[1] - a[1] * b[0]) / denom
    matrix = np.array([[c, -s], [s, c]])
    translation = se.mean(0) - re.mean(0) @ matrix.T
    return matrix, translation


def bake(model, glb):
    folder = ROOT / "native/Art/Wayfarer"
    target, size = landmarks(model, folder / "spectre-face.jpg")
    source, dims = landmarks(
        model, ROOT / "docs/runtime/portrait-match/before-closed.jpg"
    )
    assert dims == (2560, 1440)
    matrix, shift = align(target, source)
    wanted = target[:, :2] @ matrix.T + shift
    scale = np.linalg.norm(matrix[:, 0])
    mesh = Glb(glb)
    part = next(
        p
        for p in mesh.doc["meshes"][0]["primitives"]
        if mesh.doc["materials"][p["material"]]["name"] == "WayfarerSkin"
    )
    p = np.array(mesh.values(part["attributes"]["POSITION"])) + np.array(
        mesh.values(part["targets"][0]["POSITION"])
    )
    # The cheek and nose relief of the actual mesh calibrate the relative
    # depth prior. A single photograph supplies no absolute profile depth.
    xy = [1280, 720] + (p[:, :2] - CAM[:2]) * [F, -F] / (CAM[2] - p[:, 2, None])
    near = cKDTree(xy).query(source[:, :2], k=16)[1]
    measured = p[near, 2].max(axis=1)
    interior = (
        (abs(source[:, 0] - 1280) < 230) & (source[:, 1] > 550) & (source[:, 1] < 1110)
    )
    gain, zero = np.polyfit(-source[interior, 2], measured[interior], 1)
    estimate = zero - gain * scale * target[:, 2]
    dz = np.clip(0.48 * (estimate - measured), -0.005, 0.005)
    # Smooth image displacement and bounded depth, with stationary supports
    # around the hair, ears and below the jaw to preserve the attachment.
    keep = np.ones(468, dtype=bool)
    keep[CHECK] = False
    pts = source[keep, :2]
    disp = np.c_[wanted - source[:, :2], dz * 1000][keep]
    write_field(folder / "portrait-field.gz", pts, disp, size, dims, matrix, shift)
    bake_feedback(model, folder, target, size, dims, matrix, shift)

    print(
        "baseline held-out mean, pixels:",
        np.linalg.norm((wanted - source[:, :2])[CHECK], axis=1).mean(),
    )


EYE_RIMS = [
    (
        [33, 246, 161, 160, 159, 158, 157, 173, 133],
        [33, 7, 163, 144, 145, 153, 154, 155, 133],
    ),
    (
        [263, 466, 388, 387, 386, 385, 384, 398, 362],
        [263, 249, 390, 373, 374, 380, 381, 382, 362],
    ),
]


def bake_feedback(model, folder, target, size, dims, matrix, shift):
    guide, _ = landmarks(model, folder / "portrait-open.jpg")
    rims = [
        [sorted((guide[ids, :2] / size).tolist()) for ids in pair] for pair in EYE_RIMS
    ]
    (folder / "portrait-lids.json").write_text(
        json.dumps(rims, separators=(",", ":")) + "\n"
    )
    keep = np.ones(468, dtype=bool)
    keep[CHECK] = False
    for pose, reference in (("closed", target), ("open", guide)):
        observed, _ = landmarks(
            model, ROOT / "docs/runtime/portrait-match/calibration" / (pose + ".jpg")
        )
        delta = reference[:, :2] @ matrix.T + shift - observed[:, :2]
        write_field(
            folder / ("portrait-" + pose + "-feedback.gz"),
            observed[keep, :2],
            np.c_[0.68 * delta[keep], np.zeros(keep.sum())],
            size,
            dims,
            matrix,
            shift,
        )


def write_field(path, pts, disp, size, dims, matrix, shift):
    x0, y0, x1, y1 = 704, 64, 1856, 1376
    anchors = np.array(
        [(x, y) for x in np.linspace(x0, x1, 13) for y in (y0, y1)]
        + [(x, y) for x in (x0, x1) for y in np.linspace(y0 + 50, y1 - 50, 13)]
    )
    pts = np.vstack((pts, anchors))
    disp = np.vstack((disp, np.zeros((len(anchors), 3))))
    solver = RBFInterpolator(
        pts / 420, disp, kernel="thin_plate_spline", smoothing=0.003
    )
    nx, ny = 73, 83
    xx, yy = np.meshgrid(np.linspace(x0, x1, nx), np.linspace(y0, y1, ny))
    grid = solver(np.c_[xx.ravel(), yy.ravel()] / 420).reshape(ny, nx, 3)
    grid[:, :, :2] = np.clip(grid[:, :, :2], -80, 80)
    grid[:, :, 2] = np.clip(grid[:, :, 2], -5, 5)
    meta = dict(
        bounds=[x0, y0, x1, y1],
        shape=[nx, ny],
        camera=CAM.tolist(),
        focal=F,
        reference_size=size,
        screen_size=dims,
        alignment=matrix.tolist(),
        shift=shift.tolist(),
    )
    header = json.dumps(meta, separators=(",", ":")).encode()
    payload = (
        struct.pack("<I", len(header))
        + header
        + np.rint(grid * 100).astype("<i2").tobytes()
    )
    path.write_bytes(gzip.compress(payload, mtime=0))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", type=Path)
    parser.add_argument("glb", type=Path)
    args = parser.parse_args()
    bake(args.model, args.glb)
