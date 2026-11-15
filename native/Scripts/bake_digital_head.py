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
    return change


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


def fit_rest_pose(registered, part):
    rest = registered + portrait_contour(registered)
    if part == "head":
        rest += cheek_volume(registered)
        rest[:, 2] += forehead_profile(registered)
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
        for key, v in targets.items():
            shaped = v if key == "Blink" else relaxed + (v - p)
            # Carry the neutral sculpt with its vertices as the jaw opens.
            delta = (sculpt(shaped, section, frontal) - registered)[index]
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
        patch[mask] = (1 + gain * gate[:, :, None] + side_gain * side[:, :, None])[mask]
    return target, undertone


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
        ("HaitangDiffuse.jpg", np.uint8((base_pigment * undertone).clip(0, 255))),
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
