"""Bake selected Epic DNA joint and corrective poses onto Haitang's game skeleton.

Run with the pinned local DNA reader, NumPy and Pillow via prepare_digital_head.py.
All source geometry is in centimetres, Y up and Z towards the face.
"""

import base64
import json
from pathlib import Path
import sys
import zlib

import numpy as np
from PIL import Image, ImageFilter

POSES = {
    "Blink": ("eyeBlink", "eye_blink"),
    "JawOpen": ("jawOpen", "jaw_open"),
    "Focus": ("browDown", "brow_down"),
    "LookLeft": ("eyeLookLeft", "eye_lookLeft"),
    "LookRight": ("eyeLookRight", "eye_lookRight"),
    "LookUp": ("eyeLookUp", "eye_lookUp"),
    "LookDown": ("eyeLookDown", "eye_lookDown"),
}
PARTS = {"head", "teeth", "eyeLeft", "eyeRight", "eyelashes", "cartilage"}


def pack(a, dtype):
    return base64.b64encode(
        zlib.compress(np.asarray(a, dtype=dtype).tobytes(), 6)
    ).decode()


def rotations(deg):
    a, b, c = np.deg2rad(deg).T
    x, y, z = np.cos(a), np.cos(b), np.cos(c)
    s, t, u = np.sin(a), np.sin(b), np.sin(c)
    return np.stack(
        [
            z * y,
            z * t * s - u * x,
            z * t * x + u * s,
            u * y,
            u * t * s + z * x,
            u * t * x - z * s,
            -t,
            y * s,
            y * x,
        ],
        -1,
    ).reshape(-1, 3, 3)


def palette(d, control=None):
    count = d.getJointCount()
    offsets = np.zeros((count, 9))
    if control:
        active = {
            i
            for i in range(d.getRawControlCount())
            if d.getRawControlName(i).split(".")[-1]
            in (control, control + "L", control + "R")
        }
        if not active:
            raise ValueError(control)
        for group in range(d.getJointGroupCount()):
            inputs = d.getJointGroupInputIndices(group)
            columns = [i for i, k in enumerate(inputs) if k in active]
            if not columns:
                continue
            outputs = np.array(d.getJointGroupOutputIndices(group))
            mat = np.array(d.getJointGroupValues(group)).reshape(
                len(outputs), len(inputs)
            )
            np.add.at(offsets.ravel(), outputs, mat[:, columns].sum(axis=1))
    t = (
        np.array([d.getNeutralJointTranslation(i) for i in range(count)])
        + offsets[:, :3]
    )
    r = rotations(
        np.array([d.getNeutralJointRotation(i) for i in range(count)])
    ) @ rotations(offsets[:, 3:6])
    m = np.tile(np.eye(4), (count, 1, 1))
    m[:, :3, :3] = r * (1 + offsets[:, None, 6:9])
    m[:, :3, 3] = t
    for i in range(count):
        parent = d.getJointParentIndex(i)
        if parent != i:
            m[i] = m[parent] @ m[i]
    return m


def sculpt(points, section, frontal):
    x, y, z = points.T

    def region(xc, yc, rx, ry):
        return np.exp(-(((np.abs(x) - xc) / rx) ** 2) - ((y - yc) / ry) ** 2)

    front = np.clip((z - 3.6) / 4, 0, 1)
    nose = region(0, 145.95, 2.6, 1.65)
    jaw = region(3.1, 140.55, 2.4, 2.0)
    lip = region(0, 142.55, 3.0, 1.0)
    brow = region(2.9, 150.9, 2.2, 0.9)
    cheek = region(3.7, 146.0, 2.2, 2.0)
    width = x * (1 - front * (0.18 * nose + 0.15 * jaw + 0.078 * lip))
    height = y + front * (0.18 * cheek - 0.14 * brow + 0.12 * region(0, 139.0, 3, 1.2))
    depth = (
        z
        + (
            np.interp(y, section[0], section[1]) * np.exp(-((x / 2.5) ** 2))
            + 0.20 * cheek
            - 0.16 * brow
        )
        * front
    )
    world = np.stack(
        (width * 0.01, 1.656 + (height - 149.15) * 0.01, 0.015 + depth * 0.01), axis=1
    )
    # Frontal registration is a secondary correction to the profile sculpt.
    # Restrict it to the anterior face and preserve the registered neck section.
    bounds, grid = frontal
    f = 1280 / np.tan(np.deg2rad(7))
    scale = f / (2.08638235 - world[:, 2])
    xx = 1280 + world[:, 0] * scale
    yy = 720 - (world[:, 1] - 1.65503121) * scale
    nx, ny = grid.shape[1] - 1, grid.shape[0] - 1
    gx = np.clip((xx - bounds[0]) * nx / (bounds[2] - bounds[0]), 0, nx - 1.0e-7)
    gy = np.clip((yy - bounds[1]) * ny / (bounds[3] - bounds[1]), 0, ny - 1.0e-7)
    i = gx.astype(int)
    j = gy.astype(int)
    u = (gx - i)[:, None]
    v = (gy - j)[:, None]
    offset = (1 - v) * ((1 - u) * grid[j, i] + u * grid[j, i + 1]) + v * (
        (1 - u) * grid[j + 1, i] + u * grid[j + 1, i + 1]
    )
    falloff = np.clip((world[:, 2] + 0.002) / 0.066, 0, 1) * np.clip(
        (world[:, 1] - 1.52) / 0.037, 0, 1
    )
    world[:, :2] += offset * np.array([1, -1]) * (falloff / scale)[:, None]
    return world


def portrait_contour(rest):
    """Fit the mandibular arch, nasal base and lip corners in neutral head space."""
    x, height, depth = rest.T

    # Fit the remaining contour after the jaw is fully weighted to the head.
    # Anchor the lip seam and the neck ring.
    def ramp(t):
        t = np.clip(t, 0, 1)
        return t * t * (3 - 2 * t)

    lower_face = ramp((1.580 - height) / 0.028) * ramp((depth - 0.051) / 0.038)
    central = np.exp(-((x / 0.0195) ** 2))
    wings = np.exp(-(((abs(x) - 0.032) / 0.020) ** 2))
    offset = np.zeros_like(rest)
    offset[:, 0] = -x * 0.073 * wings * lower_face
    offset[:, 1] = (0.0002 * wings - 0.0019 * central) * lower_face
    # Register the nasal base and lip against the eye line without moving the
    # eye sockets. Apply the same displacement to the oral mesh as to the skin.
    front = ramp((depth - 0.068) / 0.035)
    nose = np.exp(-((x / 0.021) ** 4) - ((height - 1.609) / 0.019) ** 4)
    mouth = np.exp(-((x / 0.030) ** 4) - ((height - 1.586) / 0.013) ** 4)
    offset[:, 1] -= front * (0.0023 * nose + 0.0017 * mouth)
    offset[:, 0] += front * 0.13 * x * mouth
    return offset


def cheek_volume(rest):
    """Displace the buccal fat pad and front of the cheek in neutral metres."""
    x, y, z = rest.T
    side = np.abs(x)
    front = np.clip((z - 0.021) / 0.046, 0, 1)
    front *= front * (3 - 2 * front)
    malar = np.exp(-(((side - 0.057) / 0.023) ** 2) - ((y - 1.636) / 0.022) ** 2)
    buccal = np.exp(-(((side - 0.048) / 0.023) ** 2) - ((y - 1.597) / 0.027) ** 2)
    change = np.zeros_like(rest)
    change[:, 0] = np.sign(x) * front * (0.0028 * malar + 0.0029 * buccal)
    # Fill the soft transition lateral to the mouth in depth. The
    # registered frontal outline and the lip seam keep their positions.
    oral_pad = np.exp(-(((side - 0.043) / 0.016) ** 2) - ((y - 1.590) / 0.022) ** 2)
    change[:, 2] = front * (0.0010 * malar + 0.0024 * buccal + 0.0009 * oral_pad)
    # Give the side of the cheek a soft roll from the malar pad towards
    # the mouth. The depth window excludes the ear and anterior lip.
    roll = np.exp(
        -(((side - 0.064) / 0.019) ** 2)
        - ((y - 1.622) / 0.030) ** 2
        - ((z - 0.079) / 0.026) ** 2
    )
    change[:, 0] += np.sign(x) * 0.00125 * roll
    change[:, 2] += 0.00065 * roll

    # Fit the footprint in the previously shaped head. The lower outline
    # seen from the front and the forward cheek seen at 38 degrees are
    # different points on the same cheek cross-section.
    cheek_x, cheek_y, cheek_z = (rest + change).T
    width = np.abs(cheek_x)
    outline = np.exp(
        -(((cheek_y - 1.594) / 0.017) ** 4)
        - ((cheek_z - (0.064 + 0.26 * (cheek_y - 1.594))) / 0.018) ** 2
        - ((width - 0.061) / 0.017) ** 4
    )
    change[:, 0] -= np.sign(x) * 0.00150 * outline
    # An oblique pad rolls forward under the outer eye and blends back
    # towards the mouth. Its high point stays lateral to the nose and lips.
    ridge_x = 0.050 + 0.28 * (cheek_y - 1.616)
    pad = np.exp(
        -(((width - ridge_x) / 0.017) ** 2)
        - ((cheek_y - 1.619) / 0.029) ** 2
        - ((cheek_z - 0.095) / 0.017) ** 2
    )
    change[:, 2] += 0.0020 * pad
    change[:, 1] += 0.00042 * pad
    return change + jaw_and_neck_planes(rest + portrait_contour(rest) + change)


def jaw_and_neck_planes(rest):
    """Refine the lower cheek against the registered ear-to-chin curve, in metres."""
    x, y, z = rest.T
    side = np.abs(x)

    def ramp(t):
        t = np.clip(t, 0, 1)
        return t * t * (3 - 2 * t)

    # In side view the jaw seam crosses skin, not the background. Its ridge
    # falls from the rear masseter toward the chin. Tuck the plane below the
    # ridge, leaving the high cheek and anterior lip pad at their old volume.
    along = z - 0.060
    ridge_y = 1.5638 - 0.539 * along + 3.88 * along**2
    height = y - ridge_y
    length = ramp((z - 0.017) / 0.019) * (1 - ramp((z - 0.084) / 0.021))
    flank = ramp((side - 0.017) / 0.024)
    # A rolled cheek meets a sloping underside. A centered hollow would
    # tilt *both* sides of this ridge into the light and flatten the jaw.
    below = ramp((0.003 - height) / 0.013)
    below *= np.exp(-((np.minimum(height + 0.014, 0) / 0.024) ** 2))
    cheek = np.exp(-(((z - 0.060) / 0.029) ** 4) - ((y - 1.587) / 0.023) ** 2)
    # Keep the head-to-clothing ring untouched and avoid shaping the pinna.
    lower = ramp((y - 1.523) / 0.015) * (1 - ramp((y - 1.608) / 0.015))
    delta = np.zeros_like(rest)
    delta[:, 0] = (
        -np.sign(x) * flank * length * lower * (0.0080 * below + 0.0035 * cheek)
    )
    delta[:, 2] = -0.0013 * flank * length * lower * cheek

    # The previous under-chin turned into the neck too far back and ended
    # almost flat. Round that corner locally; lift the slightly low middle
    # and bring the front pad down without moving the mouth or narrowing it.
    middle = np.exp(-(((z - 0.084) / 0.009) ** 2) - ((x / 0.027) ** 4))
    chin = np.exp(-(((z - 0.108) / 0.013) ** 4) - ((x / 0.023) ** 4))
    sole = np.exp(-(((y - 1.549) / 0.009) ** 4))
    # The reference mental pad also projects in front of the lip-to-chin
    # hollow. Bring the pad forward without stretching the lip seam.
    central = np.exp(-((x / 0.023) ** 4))
    lower_lip = 1 - ramp((y - 1.569) / 0.011)
    pad = np.exp(-(((y - 1.558) / 0.017) ** 4))
    delta[:, 2] += 0.00515 * central * pad * lower_lip * ramp((z - 0.085) / 0.021)
    delta[:, 1] += sole * (0.00115 * middle - 0.00265 * chin)
    # A diagonal section coordinate remains monotone around the bend from
    # the front of the neck to the horizontal underside of the mandible.
    # Move the *existing bend* onto the reference curve along that diagonal.
    # A local forward bulge in the throat alone produces an unwanted step.
    section = 1000 * (z + y - 1.600)
    knots = (
        -28,
        -17,
        -9,
        -3.8,
        1.3,
        5.3,
        9.5,
        11.7,
        12.6,
        14.2,
        15.3,
        16.6,
        18.1,
        19.7,
        21.3,
        23,
        25.1,
        27.2,
        29,
        32,
        38,
    )
    surface_z = np.interp(
        section,
        knots,
        (
            58.5,
            59.5,
            60.2,
            60.9,
            61.9,
            62.7,
            63.4,
            64.3,
            65.0,
            66.2,
            67.3,
            69.0,
            70.8,
            72.9,
            75.0,
            77.3,
            80.0,
            82.5,
            84.6,
            87.6,
            94,
        ),
    )
    outward = np.interp(
        section,
        knots,
        (
            0,
            2.9,
            4.6,
            5.7,
            6.3,
            6.6,
            6.9,
            6.7,
            6.25,
            5.50,
            4.85,
            4.0,
            2.9,
            1.70,
            0.45,
            -0.25,
            -0.90,
            -1.35,
            -1.35,
            -0.85,
            0,
        ),
    )
    core = np.exp(-(((1000 * z - surface_z) / 14) ** 2) - ((x / 0.028) ** 4))
    core *= ramp((y - 1.520) / 0.013) * (1 - ramp((y - 1.556) / 0.013))
    swing = 0.00092 * core * outward
    delta[:, 2] += swing
    delta[:, 1] -= swing
    delta += mandibular_taper(rest + delta)
    return delta


def mandibular_taper(rest):
    """Roll the lower lateral cheek over the jaw into the submandibular plane."""
    x, y, z = rest.T
    side = np.abs(x)

    def ramp(t):
        t = np.clip(t, 0, 1)
        return t * t * (3 - 2 * t)

    # Trace the art's sloping jaw from the masseter towards the chin on the
    # already fitted skin. The turn is below this line, not on the cheekbone.
    along = z - 0.060
    line = 1.5638 - 0.539 * along + 3.88 * along**2
    line += 0.0016 * ramp((0.053 - z) / 0.013) - 0.0007 * ramp((z - 0.054) / 0.008)
    height = y - line
    flank = ramp((side - 0.018) / 0.016)
    band = flank * ramp((y - 1.538) / 0.016) * ramp((1.609 - y) / 0.010)
    length = ramp((z - 0.034) / 0.011) * ramp((0.077 - z) / 0.019)
    shoulder = -0.002 + 0.0015 * ramp((z - 0.050) / 0.010)
    # The artwork's jaw crossing lies about a third of the way between
    # the low and high trial rolls over the continuous ear-to-chin section.
    lift = 0.00035 + 0.0042 * (1 - ramp((z - 0.039) / 0.014))
    roll_height = height - lift
    under = 0.5 * (1 - np.tanh((roll_height - shoulder + 0.00375) / 0.0045))
    under *= np.exp(-((np.minimum(roll_height + 0.015, 0) / 0.020) ** 2))

    # The skin above the jaw turns more slowly than its underside. Keep
    # this shallow taper behind the frontal silhouette near mouth level.
    rear = np.exp(-(((height - 0.009) / 0.015) ** 2) - ((z - 0.043) / 0.019) ** 4)
    rear *= ramp((z - 0.023) / 0.014)
    # Ease the anterior cheek back into the oral pad in three-quarter view.
    # The depth window avoids the sides of the neck and the central lips.
    oblique = np.exp(
        -(((z - 0.098) / 0.013) ** 2)
        - ((y - 1.591) / 0.015) ** 2
        - ((side - 0.046) / 0.017) ** 2
    )
    delta = np.zeros_like(rest)
    # Release the underside gradually across its width as well as its
    # height. A narrow lateral mask cuts a groove in the neck-facing skin.
    underside_flank = (
        ramp((side - 0.015) / 0.026)
        * ramp((y - 1.537) / 0.019)
        * ramp((1.609 - y) / 0.010)
    )
    delta[:, 0] = -np.sign(x) * (
        band * (0.0018 * rear + 0.0013 * oblique)
        + 0.0068 * underside_flank * length * under
    )
    delta[:, 2] = -band * 0.0012 * oblique
    return delta


def forehead_profile(rest):
    """Depth correction in metres for the exposed forehead in the profile guide."""
    x, height, depth = rest.T

    def ramp(t):
        t = np.clip(t, 0, 1)
        return t * t * (3 - 2 * t)

    # The central forehead gains convexity immediately above the brow.
    # Its upper plane slopes back into the anterior hairline.
    lower = 0.00150 * np.exp(-(((height - 1.680) / 0.0125) ** 2))
    upper = 0.00160 * np.exp(-(((height - 1.711) / 0.0135) ** 2))
    # The arches sit higher laterally. Keep the eye sockets and eyebrow
    # ridges out of the displacement and fade across the side of the skull.
    arch = 1.668 + 0.021 * ramp((np.abs(x) - 0.006) / 0.019)
    above_brow = ramp((height - arch) / 0.008)
    anterior = ramp((depth - 0.072) / 0.029)
    width = np.exp(-((x / 0.037) ** 4))
    return (lower - upper) * above_brow * anterior * width


def ear_cartilage_offset(rest):
    """Fit the free pinna and its cartilage in the head's bilateral neutral space."""
    x, y, z = rest.T
    side = abs(x)
    change = np.zeros_like(rest)

    # The free rim is lateral to the mastoid. The root of the canal and the
    # skin approaching the jaw move less, so the pinna stays joined.
    def ramp(a):
        a = np.clip(a, 0.0, 1.0)
        return a * a * (3.0 - 2.0 * a)

    local = (
        ramp((side - 0.056) / 0.017)
        * ramp((y - 1.591) / 0.016)
        * ramp((1.675 - y) / 0.012)
        * ramp((z + 0.012) / 0.014)
        * ramp((0.040 - z) / 0.014)
    )
    active = local > 0
    height = (y[active] - 1.640) * 1000
    forward = z[active] * 1000
    lateral = side[active] * 1000

    # Paths follow the scan's helix, scapha and the two crura of the
    # antihelix. Coordinates are millimetres (anterior, superior). Moving
    # the lateral surface changes the real fold and its relit normal.
    def fold(path, width):
        distance = np.full_like(forward, np.inf)
        for (za, ya), (zb, yb) in zip(path, path[1:]):
            dz, dy = zb - za, yb - ya
            t = np.clip(
                ((forward - za) * dz + (height - ya) * dy) / (dz * dz + dy * dy), 0, 1
            )
            distance = np.minimum(
                distance, (forward - za - dz * t) ** 2 + (height - ya - dy * t) ** 2
            )
        return np.exp(-distance / width**2)

    def pad(zc, yc, rz, ry):
        return np.exp(-(((forward - zc) / rz) ** 2) - ((height - yc) / ry) ** 2)

    rim = fold(
        [
            (21, 19),
            (16, 21),
            (12, 21),
            (8, 19),
            (5, 14),
            (3, 9),
            (3, 4),
            (4, -2),
            (6, -6),
            (9, -11),
        ],
        2.1,
    )
    scapha = fold([(14, 17), (10.5, 14), (7.8, 10), (6.6, 5), (7.4, 0), (8.9, -4)], 2.3)
    antihelix = fold(
        [
            (14.6, -10),
            (11.8, -7),
            (10.4, -3),
            (11.9, 0.3),
            (13.4, 2.3),
            (16.5, 6),
            (19.2, 9),
        ],
        2.5,
    )
    superior_crus = fold(
        [
            (12.0, 0.3),
            (10.8, 3.3),
            (10.0, 6.0),
            (10.1, 8.7),
            (11.2, 11.4),
            (12.5, 13.2),
        ],
        2.25,
    )
    exposed = ramp((lateral - 63) / 11)
    ridges = np.maximum(antihelix, 1.09 * superior_crus)
    relief = exposed * (1.05 * rim - 1.45 * scapha + 1.65 * ridges)
    # Separate the cymba and cavum behind the meatus; leave an actual
    # raised crus between them. The floor remains continuous with the tragus.
    relief -= 1.95 * pad(20.5, 4.0, 4.4, 3.4) + 2.35 * pad(20.2, -6.1, 5.4, 4.0)
    relief += 1.15 * pad(25.8, -0.3, 2.7, 3.2) + 0.85 * pad(19.8, -12.5, 3.6, 2.5)
    relief -= 0.85 * pad(15.2, 12.7, 2.9, 2.7)
    relief -= 0.55 * exposed * pad(13.5, 7.1, 1.95, 3.0)
    weight = local[active]
    change[active, 0] = np.sign(x[active]) * relief * weight / 1000
    # The guide places the upper margin and lobe lower and more posterior.
    # Give the hanging lobe more travel than the root near the ear canal.
    change[active, 1] = -(0.0064 + 0.0016 * ramp((-height - 2) / 22)) * weight
    change[active, 2] = -(0.0056 + 0.0007 * ramp(height / 16)) * weight
    # The residual registration error is at the superior and posterior
    # rim. Taper the adjustment to zero well above the lobe piercing.
    upper = weight * ramp((height + 9) / 16) * ramp((32 - forward) / 13)
    change[active, 1] -= 0.00165 * upper
    change[active, 2] -= 0.00375 * upper
    # Round the anterior wall where the tragus returns to the cavum.
    # At the deep wall the scan turns through an abrupt right angle.
    corner = pad(23.5, -14.1, 5.1, 4.5) * ramp((lateral - 58) / 5)
    corner *= ramp((71 - lateral) / 6) * ramp((height + 22) / 6)
    change[active, 0] += np.sign(x[active]) * 0.0013 * corner
    change[active, 1] += 0.00085 * corner
    change[active, 2] += 0.00090 * corner
    return change


def round_conchal_wall(points, faces):
    """Unroll the projecting tragal wall over the floor of the cavum."""
    x, y, z = points.T
    lateral = abs(x)

    def ramp(v):
        v = np.clip(v, 0.0, 1.0)
        return v * v * (3 - 2 * v)

    # Both the outer lip and the skin behind it are in this window. A
    # planar mask alone would pull the lobe and the adjoining cheek along.
    local = (
        ramp((lateral - 0.053) / 0.006)
        * ramp((0.078 - lateral) / 0.006)
        * ramp((y - 1.6135) / 0.007)
        * ramp((1.640 - y) / 0.0085)
        * ramp((z - 0.008) / 0.010)
        * ramp((0.041 - z) / 0.010)
    )
    # In section the free wall doubles back 6–9 mm over the bowl.
    # Rotate that overhang open, carrying the transition round its lower
    # end. The upper entrance stays narrow. The lower floor descends into
    # the turn while the outer skin wraps gradually around the tragus.
    depth = np.clip(lateral - 0.065, -0.0065, 0.0065)
    lower = ramp((1.632 - y) / 0.010)
    tip = np.exp(-(((z - 0.026) / 0.009) ** 2 + ((y - 1.624) / 0.007) ** 2))
    result = points.copy()
    result[:, 0] -= np.sign(x) * local * 0.40 * depth
    result[:, 2] += local * depth * (1.34 - 0.29 * lower)
    result[:, 1] += local * (0.74 * lower * depth - 0.0036 * tip)

    # Relax only connected scan neighbours. The source mesh uses a welded
    # position layout here, before UV seam expansion. This rounds both
    # tangents across the return without bridging across the canal.
    patch = faces[np.any(local[faces] > 0, axis=1)]
    edges = np.concatenate((patch[:, [0, 1]], patch[:, [1, 2]], patch[:, [2, 0]]))
    edges = np.unique(np.sort(edges, axis=1), axis=0)
    i, j = np.concatenate((edges, edges[:, ::-1])).T
    weight = 1 / np.maximum(np.linalg.norm(points[j] - points[i], axis=1), 0.0003)
    totals = np.bincount(i, weight, minlength=len(points))
    active = np.flatnonzero((local > 0) & (totals > 0))
    for _ in range(9):
        sums = np.zeros_like(result)
        np.add.at(sums, i, weight[:, None] * result[j])
        delta = sums[active] / totals[active, None] - result[active]
        result[active] += 0.38 * local[active, None] * delta
    # The cavum is deeper centrally and turns down and forward below the
    # tragus. Cup the gently unfolded floor along that oblique axis. Only
    # the compact free end of the tragus turns back over the entrance.
    lateral, height, forward = abs(result[:, 0]), result[:, 1], result[:, 2]
    along = forward - 0.0218
    bowl_height = height - 1.6251 + 0.48 * along
    bowl = np.exp(-((along / 0.0073) ** 2 + (bowl_height / 0.0056) ** 2))
    lip = np.exp(
        -(((forward - 0.0271) / 0.0050) ** 2 + ((height - 1.6305) / 0.0047) ** 2)
    )
    free = ramp((lateral - 0.0615) / 0.0054)
    root = np.exp(
        -(((forward - 0.0265) / 0.0085) ** 2 + ((height - 1.631) / 0.0065) ** 2)
    )
    result[:, 0] += np.sign(x) * local * (0.00115 * lip * free - 0.0032 * bowl)
    result[:, 2] -= local * (0.0027 * lip * free + 0.0015 * root)
    return result


def ear_ambient_visibility(points, faces, normals):
    """Cosine-weighted visibility of nearby pinna triangles, in the neutral pose."""
    x, y, z = points.T

    def ramp(v):
        v = np.clip(v, 0, 1)
        return v * v * (3 - 2 * v)

    region = (
        ramp((abs(x) - 0.053) / 0.011)
        * ramp((y - 1.595) / 0.012)
        * ramp((1.666 - y) / 0.013)
        * ramp((z + 0.014) / 0.011)
        * ramp((0.034 - z) / 0.009)
    )
    visibility = np.ones(len(points), dtype=np.float32)
    radius = 0.018
    # Same deterministic cosine-weighted hemisphere on both sides. Ray length
    # limits this signal to local cartilage, independent of the scene lights.
    k = np.arange(32, dtype=float) + 0.5
    disk_r = np.sqrt(k / len(k))
    phi = k * np.pi * (3 - np.sqrt(5))
    disk_x = disk_r * np.cos(phi)
    disk_y = disk_r * np.sin(phi)
    axial = np.sqrt(1 - disk_r**2)
    for side in (-1, 1):
        active = np.flatnonzero((region > 0) & (side * x > 0))
        if not len(active):
            continue
        q = points[active]
        lo, hi = q.min(0) - radius, q.max(0) + radius
        triangles = points[faces]
        inside = ((triangles.max(1) >= lo) & (triangles.min(1) <= hi)).all(1)
        a, b, c = triangles[inside].transpose(1, 0, 2)
        e1, e2 = b - a, c - a
        plane = np.cross(e1, e2)
        aa = (e1 * e1).sum(1)
        ab = (e1 * e2).sum(1)
        bb = (e2 * e2).sum(1)
        determinant = aa * bb - ab * ab
        centers = (a + b + c) / 3
        reach = radius + np.maximum.reduce(
            [np.linalg.norm(v - centers, axis=1) for v in (a, b, c)]
        )
        for i in active:
            normal = normals[i]
            if np.linalg.norm(normal) < 0.9:
                continue
            origin = points[i] + 0.00030 * normal
            tangent = np.cross(
                normal, [0, 1, 0] if abs(normal[1]) < 0.94 else [0, 0, 1]
            )
            tangent /= np.linalg.norm(tangent)
            bitangent = side * np.cross(normal, tangent)
            rays = (
                disk_x[:, None] * tangent
                + disk_y[:, None] * bitangent
                + axial[:, None] * normal
            )
            sub = np.flatnonzero(
                (((centers - origin) ** 2).sum(1) < reach**2) & (determinant > 1e-19)
            )
            if not len(sub):
                continue
            denom = rays @ plane[sub].T
            numerator = ((a[sub] - origin) * plane[sub]).sum(1)
            dist = np.divide(
                numerator[None, :],
                denom,
                out=np.full_like(denom, np.inf),
                where=abs(denom) > 1e-13,
            )
            ri, local_face = np.where((dist > 0.00025) & (dist < radius))
            tri = sub[local_face]
            lengths = dist[ri, local_face]
            hit = origin + lengths[:, None] * rays[ri] - a[tri]
            s1, s2 = (hit * e1[tri]).sum(1), (hit * e2[tri]).sum(1)
            u = (bb[tri] * s1 - ab[tri] * s2) / determinant[tri]
            v = (aa[tri] * s2 - ab[tri] * s1) / determinant[tri]
            actual = (u >= 0) & (v >= 0) & (u + v <= 1)
            first = np.full(len(rays), radius)
            np.minimum.at(first, ri[actual], lengths[actual])
            blocked = (1 - (first / radius) ** 2) ** 2
            visibility[i] = 1 - region[i] * min(0.55, 0.85 * blocked.mean())
    return visibility


def fit_rest_pose(registered, part):
    rest = registered + portrait_contour(registered)
    if part == "head":
        rest += cheek_volume(registered)
        rest[:, 2] += forehead_profile(registered)
        rest += ear_cartilage_offset(registered)
    return rest


def profile_section(p, guide):
    # Profile eye centre and scale registered to the frontal interocular scale.
    im = np.array(Image.open(guide).convert("RGB").resize((1254, 1254)), dtype=float)
    levels = np.arange(139.0, 153.1, 0.25)
    correction = []
    for y in levels:
        row = int(round(521 - (y - 149.15) * 45.2))
        rgb = im[row, 920:1140]
        skin = np.where((rgb[:, 0] - rgb[:, 2] > 19) & (rgb[:, 0] - rgb[:, 1] > 8))[0]
        nearby = p[(abs(p[:, 1] - y) < 0.22) & (abs(p[:, 0]) < 1.0)]
        if not len(skin) or not len(nearby):
            correction.append(0)
            continue
        wanted = 9.43 + (920 + skin[-1] - 969) / 45.2
        correction.append(np.clip(wanted - nearby[:, 2].max(), -0.8, 0.8))
    return levels, np.convolve(correction, [0.15, 0.7, 0.15], "same")


def shape_mesh(d, mi, transforms):
    pts = np.stack(
        [
            d.getVertexPositionXs(mi),
            d.getVertexPositionYs(mi),
            d.getVertexPositionZs(mi),
        ],
        axis=1,
    )
    ji = []
    vi = []
    weights = []
    for i in range(len(pts)):
        joints = d.getSkinWeightsJointIndices(mi, i)
        ji.extend(joints)
        vi.extend([i] * len(joints))
        weights.extend(d.getSkinWeightsValues(mi, i))
    ji, vi, weights = np.array(ji), np.array(vi), np.array(weights)
    dst = {}
    targets = {
        d.getBlendShapeChannelName(d.getBlendShapeChannelIndex(mi, j)): j
        for j in range(d.getBlendShapeTargetCount(mi))
    }
    for name, (_, shape) in POSES.items():
        corrected = pts.copy()
        for suffix in ("", "_L", "_R"):
            j = targets.get(shape + suffix)
            if j is None:
                continue
            ids = d.getBlendShapeTargetVertexIndices(mi, j)
            delta = np.stack(
                [
                    d.getBlendShapeTargetDeltaXs(mi, j),
                    d.getBlendShapeTargetDeltaYs(mi, j),
                    d.getBlendShapeTargetDeltaZs(mi, j),
                ],
                axis=1,
            )
            corrected[ids] += delta
        m = transforms[name][ji]
        v = np.einsum("ijk,ik->ij", m[:, :3, :3], corrected[vi]) + m[:, :3, 3]
        result = np.zeros_like(pts)
        np.add.at(result, vi, v * weights[:, None])
        dst[name] = result
    return pts, dst


def triangles(d, i):
    faces = []
    for j in range(d.getFaceCount(i)):
        f = d.getFaceVertexLayoutIndices(i, j)
        for k in range(1, len(f) - 1):
            faces.append((f[0], f[k], f[k + 1]))
    return np.array(faces)


def bake(cache, art):
    import dna

    stream = dna.FileStream(
        str(cache / "Ada.dna"),
        dna.FileStream.AccessMode_Read,
        dna.FileStream.OpenMode_Binary,
    )
    d = dna.BinaryStreamReader(stream, dna.DataLayer_All)
    d.read()
    if not dna.Status.isOk():
        raise ValueError(dna.Status.get().message)
    registration = json.loads((art / "digital-sculpt.json").read_text())
    frontal = (registration["bounds"], np.array(registration["grid"]))
    neutral = palette(d)
    inverse = np.linalg.inv(neutral)
    transforms = {
        name: palette(d, control) @ inverse for name, (control, _) in POSES.items()
    }
    # Catch unit/axis errors before baking skin weights around a displaced pivot.
    eye_joint = next(
        i for i in range(d.getJointCount()) if d.getJointName(i) == "FACIAL_L_Eye"
    )
    if np.linalg.norm(neutral[eye_joint, :3, 3] - [3.05, 149.13, 8.12]) > 1.5:
        raise ValueError("Unexpected eye pivot " + str(neutral[eye_joint, :3, 3]))
    parts = {}
    for mi in d.getMeshIndicesForLOD(0):
        name = d.getMeshName(mi).split("_")[0]
        if name not in PARTS:
            continue
        p, targets = shape_mesh(d, mi, transforms)
        if name == "head":
            section = profile_section(p, art / "sculpt-profile.jpg")
        # Relax the neutral orbital muscles and keep the lips in light contact.
        relaxed = p + 0.12 * (targets["Blink"] - p)
        registered = sculpt(relaxed, section, frontal)
        rest = fit_rest_pose(registered, name)
        layout = np.array(
            [d.getVertexLayout(mi, i) for i in range(d.getVertexLayoutCount(mi))]
        )
        uv = np.array(
            [
                d.getVertexTextureCoordinate(mi, i)
                for i in range(d.getVertexTextureCoordinateCount(mi))
            ]
        )
        uv[:, 1] = 1 - uv[:, 1]
        face = triangles(d, mi)
        index = layout[:, 0]
        if name == "head":
            # The original shoulder apron sits inside the game's neckline.
            face = face[np.max(rest[index[face], 1], axis=1) >= 1.5195]
            rest = round_conchal_wall(rest, index[face])
        triangles_xyz = rest[index[face]]
        area = np.cross(
            triangles_xyz[:, 1] - triangles_xyz[:, 0],
            triangles_xyz[:, 2] - triangles_xyz[:, 0],
        )
        normals = np.zeros_like(rest)
        for corner in range(3):
            np.add.at(normals, index[face[:, corner]], area)
        normals /= np.maximum(1e-12, np.linalg.norm(normals, axis=1, keepdims=True))
        pose = {}
        if name == "head":
            # The pierced lobule follows the head with the earring. The donor
            # jaw target otherwise tugs this spot by roughly 1.3 mm. Fade
            # that motion locally and keep the surrounding jaw articulation.
            hole = (
                np.minimum(np.abs(rest[:, 0] - 0.0742), np.abs(rest[:, 0] + 0.0742))
                ** 2
            )
            hole += (rest[:, 1] - 1.6075) ** 2 + (rest[:, 2] - 0.0160) ** 2
            lobe_motion = np.clip((np.sqrt(hole) - 0.0035) / 0.009, 0, 1)
            lobe_motion *= lobe_motion * (3 - 2 * lobe_motion)
        for key, v in targets.items():
            shaped = v if key == "Blink" else relaxed + (v - p)
            # Carry the neutral sculpt with its vertices as the jaw opens.
            delta = (sculpt(shaped, section, frontal) - registered)[index]
            if name == "head":
                delta *= lobe_motion[index, None]
            if np.abs(delta).max() > 0.00001:
                pose[key] = pack(delta, "<f4")
        parts[name] = {
            "p": pack(rest[index], "<f4"),
            "n": pack(normals[index], "<f4"),
            "uv": pack(uv[layout[:, 1]], "<f4"),
            "tri": pack(face, "<u4"),
            "poses": pose,
        }
        if name == "head":
            visibility = ear_ambient_visibility(rest, index[face], normals)
            parts[name]["ear_visibility"] = pack(visibility[index], "<f4")
            # The pigment guide was registered on the original mesh. Keep
            # each UV texel with its anatomical vertex when the lip moves.
            paint_surface = dict(parts[name], p=pack(registered[index], "<f4"))
    textures(cache, art, paint_surface)
    tmp = cache / "face.json.tmp"
    tmp.write_text(
        json.dumps({"parts": parts, "poses": list(POSES)}, separators=(",", ":"))
    )
    tmp.replace(cache / "face.json")


def portrait_skin_coverage(x, y):
    """Exclude the guide's dressed hair from the projected forehead pigment."""
    # Trace the visible skin on each side of the 1254px portrait. Below the
    # outer brow the temple curls turn inward differently on the two sides.
    heights = [215, 235, 260, 290, 320, 350, 380, 410, 440, 480, 520, 575, 635]
    left = np.interp(
        y, heights, [600, 544, 490, 455, 429, 402, 384, 371, 355, 348, 342, 334, 320]
    )
    right = np.interp(
        y, heights, [654, 722, 764, 796, 826, 849, 865, 880, 898, 905, 910, 917, 928]
    )
    # Sampled skin can carry the existing makeup while shaded edge texels fade
    # into the scan's own pigment and pore detail. The outer brow stays inside.
    distance = np.minimum(x - left, right - x)
    keep = np.clip((distance + 4) / 16, 0, 1)
    keep *= keep * (3 - 2 * keep)
    release = np.clip((y - 610) / 70, 0, 1)
    release *= release * (3 - 2 * release)
    return keep + release * (1 - keep)


def mandibular_undertone(x, y, z):
    """Blend the cheek powder into the warmer underside of the mandibular arch."""

    def smooth(t):
        t = np.clip(t, 0, 1)
        return t * t * (3 - 2 * t)

    # Neutral surface stations (metres), from behind the masseter towards
    # the chin. Both UV islands follow the same anatomy through animation.
    stations = [0.031, 0.0367, 0.0423, 0.0479, 0.0536, 0.0593, 0.0650, 0.0707, 0.0764]
    heights = [1.5860, 1.5801, 1.5766, 1.5693, 1.5663, 1.5639, 1.5613, 1.5591, 1.5569]
    height = y - np.interp(z, stations, heights)
    placement = smooth((z - 0.032) / 0.010) * smooth((0.078 - z) / 0.012)
    placement *= smooth((np.abs(x) - 0.016) / 0.011) * smooth((y - 1.546) / 0.007)
    # Use broad upper and lower skin tones. A soft transition retains
    # scanned pores and lets the actual mesh catch light as the head turns.
    upper = 0.5 + 0.5 * np.tanh(height / 0.0031)
    upper *= smooth((0.033 - height) / 0.016)
    lower = (
        (1 - upper)
        * smooth((height + 0.015) / 0.009)
        * smooth((0.012 - height) / 0.006)
    )
    front = smooth((z - 0.046) / 0.014)
    upper_rgb = np.stack(
        (-0.012 - 0.030 * front, 0.145 - 0.115 * front, 0.130 - 0.115 * front), axis=-1
    )
    lower_rgb = np.stack(
        (-0.085 - 0.055 * front, 0.002 - 0.105 * front, -0.060 - 0.082 * front), axis=-1
    )
    # Faint green/ochre in the deeper hollow balances the red subsurface
    # cast below the ear. The neck and collar use their own skin swatch.
    hollow = np.exp(-(((height + 0.0105) / 0.0048) ** 2))
    return placement[..., None] * (
        upper[..., None] * upper_rgb
        + lower[..., None] * lower_rgb
        + hollow[..., None] * [-0.023, 0.039, 0.033]
    )


def cosmetics(diffuse, head, art):
    def unpack(key, dtype, width):
        return np.frombuffer(
            zlib.decompress(base64.b64decode(head[key])), dtype=dtype
        ).reshape(-1, width)

    xyz = unpack("p", "<f4", 3)
    uv = unpack("uv", "<f4", 2) * 2047
    tris = unpack("tri", "<u4", 3)
    front = (xyz[:, 2] > 0.021) & (xyz[:, 1] > 1.544) & (xyz[:, 1] < 1.74)
    calibration = json.loads((art / "digital-pigment.json").read_text())
    grid = np.array(calibration["grid"])
    x0, y0, x1, y1 = calibration["bounds"]
    normals = unpack("n", "<f4", 3)
    nx, ny = grid.shape[1] - 1, grid.shape[0] - 1
    target = np.array(diffuse.resize((2048, 2048), Image.Resampling.BICUBIC))
    ref = np.asarray(
        Image.open(art / "portrait-open.jpg").convert("RGB").resize((1254, 1254)),
        dtype=float,
    )
    # Isolate soft regional variation from the registered guide. Removing its
    # luminance prevents directional shadows from being printed into albedo.
    guide = Image.fromarray(ref.astype(np.uint8))
    chroma = np.asarray(guide.filter(ImageFilter.GaussianBlur(5)), dtype=float)
    chroma -= np.asarray(guide.filter(ImageFilter.GaussianBlur(38)), dtype=float)
    chroma -= (chroma @ [0.2126, 0.7152, 0.0722])[:, :, None]
    # Record the spatial pigment correction separately. Adjacent UV triangles
    # share edge texels; applying a gain within the raster loop would double it.
    undertone = np.ones((2048, 2048, 3), dtype=np.float32)
    for ids in tris[front[tris].any(axis=1)]:
        tri = uv[ids]
        lo = np.maximum(np.floor(tri.min(0)).astype(int), 0)
        hi = np.minimum(np.ceil(tri.max(0)).astype(int), 2047)
        yy, xx = np.mgrid[lo[1] : hi[1] + 1, lo[0] : hi[0] + 1]
        mat = (tri[1:] - tri[0]).T
        if abs(np.linalg.det(mat)) < 1e-6:
            continue
        b = (np.stack((xx, yy), axis=-1) - tri[0]) @ np.linalg.inv(mat).T
        mask = (b >= -0.01).all(-1) & (b.sum(-1) <= 1.01)
        point = xyz[ids[0]] + b @ (xyz[ids[1:]] - xyz[ids[0]])
        scale = (1280 / np.tan(np.deg2rad(7))) / (2.08638235 - point[:, :, 2])
        gx = np.clip(
            (1280 + point[:, :, 0] * scale - x0) * nx / (x1 - x0), 0, nx - 1.0e-6
        )
        gy = np.clip(
            (720 - (point[:, :, 1] - 1.65503121) * scale - y0) * ny / (y1 - y0),
            0,
            ny - 1.0e-6,
        )
        i = gx.astype(int)
        j = gy.astype(int)
        u = (gx - i)[:, :, None]
        v = (gy - j)[:, :, None]
        sample = (1 - v) * ((1 - u) * grid[j, i] + u * grid[j, i + 1]) + v * (
            (1 - u) * grid[j + 1, i] + u * grid[j + 1, i + 1]
        )
        sx, sy = sample[:, :, 0], sample[:, :, 1]
        # At the eyelid margin fetch skin just beyond the guide's lashes.
        # This avoids baking sclera, iris or lash cards onto a mobile lid.
        for top, lower in calibration["rims"]:
            top = np.asarray(top)
            lower = np.asarray(lower)
            upper = np.interp(sx, top[:, 0], top[:, 1]) - 3
            bottom = np.interp(sx, lower[:, 0], lower[:, 1]) + 3
            inside = (sx > top[0, 0]) & (sx < top[-1, 0]) & (sy > upper) & (sy < bottom)
            sy = np.where(
                inside, np.where(sy < (upper + bottom) / 2, upper, bottom), sy
            )
        u = np.clip(sx, 0, 1252)
        v = np.clip(sy, 0, 1252)
        i = u.astype(int)
        j = v.astype(int)
        u = (u - i)[:, :, None]
        v = (v - j)[:, :, None]
        pigment = (1 - v) * ((1 - u) * ref[j, i] + u * ref[j, i + 1]) + v * (
            (1 - u) * ref[j + 1, i] + u * ref[j + 1, i + 1]
        )
        # Flash-free neutral guide supplies makeup and character skin colour.
        # Preserve scanned microstructure and leave the orbit, nostril cavities
        # and the side of the skull under the physical surface materials.
        skin = target[lo[1] : hi[1] + 1, lo[0] : hi[0] + 1]
        facing = normals[ids[0], 2] + b @ (normals[ids[1:], 2] - normals[ids[0], 2])
        depth = np.clip((point[:, :, 2] - 0.045) / 0.035, 0, 1)
        border = (
            np.clip((sy - 225) / 110, 0, 1)
            * np.clip((1030 - sy) / 95, 0, 1)
            * np.clip((325 - abs(sx - 630)) / 55, 0, 1)
        )
        cosmetic = (
            np.exp(-(((sy - 866) / 48) ** 4) - ((sx - 632) / 120) ** 6)
            + np.exp(-(((sy - 475) / 105) ** 4) - ((abs(sx - 630) - 146) / 140) ** 6)
            + np.exp(-(((sy - 391) / 28) ** 4) - ((sx - 630) / 32) ** 4)
        )
        weight = np.clip(
            (0.48 + 0.49 * np.minimum(1, cosmetic))
            * depth
            * border
            * np.clip((facing + 0.13) / 0.68, 0, 1),
            0,
            0.96,
        )
        weight *= portrait_skin_coverage(sx, sy)
        # Prevent the dark center of an actual nostril from being printed twice.
        nostril = (
            (abs(sx - 630) < 69) & (sy > 727) & (sy < 789) & (pigment[:, :, 0] < 131)
        )
        weight[nostril] *= 0.18
        lit = pigment * np.array([0.93, 0.945, 0.975])
        result = skin * (1 - weight[:, :, None]) + lit * weight[:, :, None]
        skin[mask] = np.uint8(result[mask].clip(0, 255))
        # Reference-space positions are expressed in interpupillary distances.
        # Keep a trace of blush across the upper cheeks while easing the donor
        # scan's orange pigment below the malar pad and around the mandible.
        lateral = abs(sx - 629) / 282
        height = (sy - 547) / 282
        high = np.exp(-(((lateral - 0.60) / 0.42) ** 4) - ((height - 0.30) / 0.26) ** 2)
        brow = np.exp(-((lateral / 0.75) ** 4) - ((height + 0.60) / 0.46) ** 2)
        flank = np.exp(
            -(((lateral - 0.72) / 0.37) ** 4) - ((height - 1.12) / 0.57) ** 4
        )
        # Restrict to the facial shell and fade to the surrounding scanned skin.
        gate = np.clip((point[:, :, 2] - 0.035) / 0.032, 0, 1)
        gate *= np.clip((facing + 0.30) / 0.45, 0, 1)
        gain = (
            high[:, :, None] * [-0.026, -0.068, -0.048]
            + brow[:, :, None] * [-0.009, -0.035, -0.029]
            + flank[:, :, None] * [0.026, 0.098, 0.135]
        )
        malar_center = 0.59 + 0.026 * np.sign(sx - 629)
        malar = np.exp(
            -(((lateral - malar_center) / 0.38) ** 2)
            - ((height - 0.47 + 0.24 * (lateral - malar_center)) / 0.31) ** 2
        )
        jaw = np.exp(-(((lateral - 0.48) / 0.31) ** 4) - ((height - 1.29) / 0.27) ** 2)
        cheek = np.exp(
            -(((lateral - 0.60) / 0.37) ** 4) - ((height - 0.66) / 0.49) ** 4
        )
        pigment_delta = (1 - v) * (
            (1 - u) * chroma[j, i] + u * chroma[j, i + 1]
        ) + v * ((1 - u) * chroma[j + 1, i] + u * chroma[j + 1, i + 1])
        gain += malar[:, :, None] * [0.006, -0.006, -0.008]
        gain += cheek[:, :, None] * np.clip(pigment_delta / 90, -0.055, 0.055)
        gain += jaw[:, :, None] * [0.012, 0.026, -0.030]
        # Keep warm ochre in the lower cheek. The ivory collar catches the
        # convex jaw, while the recessed neck retains more subsurface red.
        x, y, z = np.moveaxis(point, 2, 0)
        lower_pad = np.exp(
            -(((abs(x) - 0.043) / 0.025) ** 2) - ((y - 1.577) / 0.024) ** 2
        )
        gain += lower_pad[:, :, None] * [-0.014, -0.036, -0.080]

        # Patches follow the strict profile guide: a warm malar high point,
        # a quieter masseter and a more gradual falloff outside the lip.
        # Side-facing scan texels extend beyond the frontal makeup mask.
        def pad(y0, z0, ry, rz):
            return np.exp(-(((y - y0) / ry) ** 2) - ((z - z0) / rz) ** 2)

        # Include the back of the cheek as the skin turns away from the
        # camera. Fade its pigment into the unpainted scalp across 18 mm.
        fade = np.clip((z - 0.021) / 0.018, 0, 1)
        side = np.exp(-(((abs(x) - 0.061) / 0.020) ** 4)) * fade**2 * (3 - 2 * fade)
        side_gain = (
            pad(1.630, 0.084, 0.012, 0.016)[:, :, None] * [0.070, 0.058, 0.064]
            + pad(1.615, 0.079, 0.014, 0.018)[:, :, None] * [0.018, -0.012, -0.014]
            + pad(1.606, 0.049, 0.020, 0.018)[:, :, None] * [-0.012, 0.066, 0.049]
            + pad(1.581, 0.067, 0.016, 0.019)[:, :, None] * [0.050, 0.020, -0.016]
            + pad(1.590, 0.095, 0.013, 0.012)[:, :, None] * [-0.043, -0.053, -0.043]
        )
        # Registered skin samples behind the brow tail are progressively
        # warmer towards the hairline. Keep the correction above the
        # cheekbone and behind the painted outer eyelid.
        side_gain += (
            pad(1.665, 0.079, 0.015, 0.013)[:, :, None] * [-0.028, 0.024, 0.023]
            + pad(1.670, 0.081, 0.007, 0.011)[:, :, None] * [0.020, 0.044, 0.059]
            # The frontal view exposes skin farther forward than the
            # profile sample. Keep a shaded midtone behind the brow tail.
            + pad(1.662, 0.079, 0.006, 0.010)[:, :, None] * [-0.012, -0.032, -0.026]
            + pad(1.663, 0.094, 0.009, 0.009)[:, :, None] * [-0.027, 0.009, 0.030]
        )
        patch = undertone[lo[1] : hi[1] + 1, lo[0] : hi[0] + 1]
        patch[mask] = (
            1
            + gain * gate[:, :, None]
            + side_gain * side[:, :, None]
            + mandibular_undertone(x, y, z)
        )[mask]
    return target, undertone


def correct_cavum_pigment(pigment):
    """Recover the local cartilage hue from adjacent texels of the same ear."""
    h, w = pigment.shape[:2]
    for u, v in ((0.1776, 0.4579), (0.8212, 0.4550)):
        rx, ry = 0.0070 * w, 0.0150 * h
        cx, cy = u * w, v * h
        x0, x1 = int(cx - rx), int(cx + rx) + 1
        y0, y1 = int(cy - ry), int(cy + ry) + 1
        patch = pigment[y0:y1, x0:x1]
        rgb = patch.astype(float)
        y, x = np.mgrid[y0:y1, x0:x1]
        radius = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
        warm = rgb[:, :, 0] - rgb[:, :, 1]
        neighbors = (radius < 1) & (warm > 30)
        if not np.any(neighbors):
            continue
        # Preserve high-frequency luminance and the darker entrance. The
        # donor scan contains cyan texels normally hidden under the tragus.
        luma = rgb @ [0.2126, 0.7152, 0.0722]
        local_chroma = np.median((rgb - luma[:, :, None])[neighbors], axis=0)
        fade = np.clip((1 - radius) / 0.48, 0, 1)
        correction = np.clip((25 - warm) / 25, 0, 1)
        amount = (fade * fade * (3 - 2 * fade)) * (correction**2 * (3 - 2 * correction))
        target = luma[:, :, None] + local_chroma
        patch[:] = np.uint8(
            np.rint(rgb + amount[:, :, None] * (target - rgb)).clip(0, 255)
        )
    return pigment


def textures(cache, art, head):
    # Shift the scan's diffuse reflectance to Haitang's cheek swatch. Retain
    # spatial pigment variation in the scan, including the ear and lip folds.
    base = np.array(
        Image.open(cache / "head_color_map.tga").convert("RGB"), dtype=float
    )
    h, w = base.shape[:2]
    median = np.median(
        base[int(0.46 * h) : int(0.51 * h), int(0.33 * w) : int(0.39 * w)], axis=(0, 1)
    )
    ref = np.asarray(
        Image.open(art / "portrait-open.jpg").convert("RGB").resize((512, 512))
    )
    wanted = np.median(ref[257:275, 159:176], axis=(0, 1))
    # Separate fine skin variation from the sample's original undertone.
    low = np.asarray(
        Image.fromarray(base.astype(np.uint8)).filter(ImageFilter.GaussianBlur(12)),
        dtype=float,
    )
    reflectance = (base - low) * 1.15 + (low - median) * 0.36
    rgb = wanted * np.array([0.91, 0.93, 0.94]) + reflectance
    y, x = np.indices((h, w))
    u = x / w
    v = y / h
    # Keep a softly bounded base vermilion under the registered lip pigment.
    lip = np.exp(-(((u - 0.495) / 0.077) ** 4) - ((v - 0.584) / 0.029) ** 4)
    lip_tone = np.array([153.0, 80.0, 82.0]) + (base - low) * 0.65
    rgb = rgb * (1 - lip[:, :, None]) + lip_tone * lip[:, :, None]
    diffuse = Image.fromarray(np.uint8(rgb.clip(0, 255)))
    base_pigment, undertone = cosmetics(diffuse, head, art)
    # Retain a warm blush in the lit cheeks and neutralize the yellow scan
    # undertone in shadow. The vermilion and lash line keep their own pigment.
    # The torso UVs sample a small cheek swatch. Give them the same base
    # pigment but leave facial blush out of the neck, shoulders and arms.
    for filename, pigment in (
        (
            "HaitangDiffuse.jpg",
            correct_cavum_pigment(np.uint8((base_pigment * undertone).clip(0, 255))),
        ),
        ("HaitangCollar.jpg", base_pigment),
    ):
        painted = pigment.astype(float)
        skin_mask = np.clip((painted[:, :, 1] - 42) / 76, 0, 1)
        skin_mask *= np.clip((133 - (painted[:, :, 0] - painted[:, :, 1])) / 47, 0, 1)
        balance = np.array([1.047, 0.954, 1.006])
        painted *= 1 + skin_mask[:, :, None] * (balance - 1)
        Image.fromarray(np.uint8(painted.clip(0, 255))).save(
            cache / filename, quality=96
        )
    for name, src in (
        ("HaitangEye", "eyes_color_map"),
        ("HaitangTeeth", "teeth_color_map"),
    ):
        Image.open(cache / (src + ".tga")).convert("RGB").save(
            cache / (name + ".jpg"), quality=95
        )
    coverage = (
        Image.open(cache / "eyelashes_color_map.tga").convert("RGBA").getchannel("A")
    )
    lashes = Image.new("RGBA", coverage.size, (29, 21, 22, 255))
    lashes.putalpha(coverage)
    lashes.save(cache / "HaitangLashes.png")
    # Preserve the skin's broad normal field and layer tiled detail at pore scale.
    normal = (
        np.array(Image.open(cache / "head_normal_map.tga").convert("RGB"), dtype=float)
        / 127.5
        - 1
    )
    micro = (
        np.array(
            Image.open(cache / "head_micro_normal_map.tga")
            .convert("RGB")
            .resize((w // 4, h // 4)),
            dtype=float,
        )
        / 127.5
        - 1
    )
    normal[:, :, :2] += np.tile(micro, (4, 4, 1))[:h, :w, :2] * 0.22
    normal /= np.maximum(np.linalg.norm(normal, axis=2, keepdims=True), 1e-6)
    Image.fromarray(np.uint8(np.clip((normal + 1) * 127.5, 0, 255))).save(
        cache / "HaitangNormal.png"
    )
    rough = Image.open(cache / "head_roughness_map.tga").getchannel("R")
    rough.point(lambda a: min(187, max(112, round(0.61 * a + 15)))).save(
        cache / "HaitangRough.png"
    )


if __name__ == "__main__":
    bake(Path(sys.argv[1]), Path(sys.argv[2]))
