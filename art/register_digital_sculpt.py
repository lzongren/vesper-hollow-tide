"""Register the initial DNA sculpt to the frontal guide after the profile pass."""

from pathlib import Path
import argparse
import json
import numpy as np
from scipy.interpolate import RBFInterpolator
from fit_portrait_reference import ROOT, align, landmarks


def fit(model):
    guide = ROOT / "native/Art/Wayfarer/portrait-open.jpg"
    capture = ROOT / "docs/runtime/digital-human/calibration.jpg"
    a, _ = landmarks(model, capture)
    b, _ = landmarks(model, guide)
    m, t = align(b, a)
    # Hold a subset of landmarks back. Keep the orbital shapes, not only the nose.
    ids = [
        10,
        21,
        54,
        103,
        67,
        109,
        338,
        297,
        332,
        284,
        251,
        162,
        127,
        234,
        93,
        132,
        58,
        172,
        136,
        150,
        149,
        176,
        148,
        377,
        400,
        378,
        379,
        365,
        397,
        288,
        361,
        323,
        454,
        356,
        389,
        130,
        133,
        160,
        144,
        159,
        145,
        158,
        153,
        359,
        362,
        387,
        373,
        386,
        374,
        385,
        380,
        105,
        334,
        66,
        296,
        107,
        336,
        9,
        168,
        197,
        6,
        4,
        5,
        2,
        97,
        326,
        102,
        331,
        48,
        278,
        64,
        294,
        51,
        281,
        37,
        267,
        39,
        269,
        40,
        270,
        78,
        308,
        12,
        15,
        17,
        83,
        313,
        84,
        314,
        18,
        199,
        175,
    ]
    px = a[ids, :2]
    delta = (b[ids, :2] @ m.T + t - px) * 0.80
    # The character's pose is anatomically symmetrical at rest. Symmetrize the
    # corrections to avoid baking a small camera yaw into the bones.
    center = a[[33, 263], 0].mean()
    reflected = np.c_[2 * center - px[:, 0], px[:, 1]]
    delta = np.vstack([delta, delta * [-1, 1]])
    xy = np.vstack([px, reflected])
    bounds = [790, 250, 1770, 1330]
    x0, y0, x1, y1 = bounds
    anchor = np.array(
        [(x, y) for x in np.linspace(x0, x1, 11) for y in (y0, y1)]
        + [(x, y) for x in (x0, x1) for y in np.linspace(y0 + 35, y1 - 35, 10)]
    )
    field = RBFInterpolator(
        np.vstack([xy, anchor]) / 440,
        np.vstack([delta, np.zeros_like(anchor)]),
        smoothing=0.003,
    )
    xx, yy = np.meshgrid(np.linspace(x0, x1, 47), np.linspace(y0, y1, 61))
    grid = field(np.c_[xx.ravel(), yy.ravel()] / 440).reshape(61, 47, 2)
    (ROOT / "native/Art/Wayfarer/digital-sculpt.json").write_text(
        json.dumps(
            dict(bounds=bounds, grid=grid.round(2).tolist()), separators=(",", ":")
        )
        + "\n"
    )


def register_pigment(model):
    guide = ROOT / "native/Art/Wayfarer/portrait-open.jpg"
    capture = ROOT / "docs/runtime/digital-human/pigment-calibration.jpg"
    a, _ = landmarks(model, capture)
    b, _ = landmarks(model, guide)
    from fit_portrait_reference import EYE_RIMS

    m, t = align(b, a)
    predicted = (a[:, :2] - t) @ np.linalg.inv(m).T
    x0, y0, x1, y1 = 790, 170, 1770, 1340
    border = np.array(
        [(x, y) for x in np.linspace(x0, x1, 11) for y in (y0, y1)]
        + [(x, y) for x in (x0, x1) for y in np.linspace(y0 + 20, y1 - 20, 10)]
    )
    solve = RBFInterpolator(
        np.vstack([a[:, :2], border]) / 440,
        np.vstack([b[:, :2] - predicted, np.zeros_like(border)]),
        smoothing=0.001,
    )
    xx, yy = np.meshgrid(np.linspace(x0, x1, 73), np.linspace(y0, y1, 85))
    p = np.c_[xx.ravel(), yy.ravel()]
    projected = (p - t) @ np.linalg.inv(m).T + solve(p / 440)
    rims = [[sorted(b[ids, :2].round(2).tolist()) for ids in pair] for pair in EYE_RIMS]
    (ROOT / "native/Art/Wayfarer/digital-pigment.json").write_text(
        json.dumps(
            dict(
                bounds=[x0, y0, x1, y1],
                grid=projected.reshape(85, 73, 2).round(2).tolist(),
                rims=rims,
            ),
            separators=(",", ":"),
        )
        + "\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", type=Path)
    model = parser.parse_args().model
    fit(model)
    register_pigment(model)
