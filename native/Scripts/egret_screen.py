"""A standing grey-brick screen with a fitted, physically carved western face."""

from math import cos, pi, sin
from bell_gallery_mesh import Joinery
from bind_pilgrim import unit


def bake(source, art, dest):
    g = Joinery(source)
    g.glb.doc["meshes"][0]["name"] = g.glb.doc["nodes"][0]["name"] = "BellEgretScreen"
    brick = g.material(
        "BlueGreyBrick", "rock-color", "rock-normal", (0.38, 0.43, 0.45), 0.79
    )
    cap = g.material(
        "RainTiles", "stone-color", "stone-normal", (0.24, 0.31, 0.32), 0.49
    )
    footing = g.material(
        "ChiselStone", "stone-color", "stone-normal", (0.67, 0.63, 0.54), 0.80
    )
    band = g.material(
        "WornBrickLip", "rock-color", "rock-normal", (0.68, 0.63, 0.53), 0.72
    )
    plate = g.material("EgretBrickCarving", None, None, (1, 1, 1), 0.78)
    mat = g.glb.doc["materials"][plate]
    for dst, path in (("color", "EgretClay"), ("normal", "EgretChisel")):
        sample = g.glb.image((art / (path + ".jpg")).read_bytes(), "image/jpeg", path)
        if dst == "color":
            mat["pbrMetallicRoughness"]["baseColorTexture"] = sample
        else:
            mat["normalTexture"] = sample

    # World X is the wall's thickness. World Y follows the long front face.
    def course(slot, y, x, z0, z1, depth, h):
        g.beam(slot, (x, y, z0), (x, y, z1), depth, h)

    for y, w, h, span in (
        (0.15, 0.92, 0.30, 3.32),
        (0.36, 0.76, 0.12, 3.25),
        (0.69, 0.65, 0.54, 3.16),
        (1.00, 0.75, 0.10, 3.23),
    ):
        course(footing, y, 0, -span, span, w, h)
    course(brick, 2.37, 0, -3.10, 3.10, 0.53, 2.70)
    # Eight short brick courses remain visible on the reverse and at either end.
    for row in range(8):
        y = 1.19 + row * 0.324
        a = -3.09
        while a < 3.085:
            length = 0.475 if a == -3.09 and row % 2 else 0.95
            b = min(3.09, a + length)
            course(brick, y, 0.273, a + 0.009, b - 0.009, 0.034, 0.309)
            a = b

    w, h = 5.42, 2.52
    nx, ny = 257, 129
    buf = (art / "EgretHeight.pgm").read_bytes().split(b"\n", 3)[-1]
    if len(buf) != nx * ny:
        raise ValueError("Unexpected egret relief grid")
    pos, nor, uv, indices = g.sections[plate]
    for j in range(ny):
        v = j / (ny - 1)
        for i in range(nx):
            u = i / (nx - 1)
            d = buf[j * nx + i] / 255 * 0.077
            du = (
                0.077
                * (buf[j * nx + min(i + 1, nx - 1)] - buf[j * nx + max(i - 1, 0)])
                / (255 * (2 * w / (nx - 1)))
            )
            dv = (
                0.077
                * (buf[min(j + 1, ny - 1) * nx + i] - buf[max(j - 1, 0) * nx + i])
                / (255 * (2 * h / (ny - 1)))
            )
            # Facing west, image right is positive world Y.
            pos.append((-0.284 - d, 2.38 + (0.5 - v) * h, (u - 0.5) * w))
            nor.append(unit((-1, dv, -du)))
            uv.append((u, v))
    for j in range(ny - 1):
        for i in range(nx - 1):
            a = j * nx + i
            indices.extend((a, a + nx, a + 1, a + 1, a + nx, a + nx + 1))

    for y in (1.065, 3.695):
        course(band, y, -0.313, -2.85, 2.85, 0.145, 0.105)
    for z in (-2.78, 2.78):
        g.beam(band, (-0.313, 1.07, z), (-0.313, 3.69, z), 0.116, 0.14)
    for y, width, height, reach in ((3.80, 0.77, 0.15, 3.19), (3.93, 0.92, 0.12, 3.26)):
        course(brick, y, 0, -reach, reach, width, height)
    for k in range(37):
        z = -3.24 + k * 0.18
        for side in (-1, 1):
            g.beam(cap, (0, 4.20, z), (side * 0.55, 3.99, z), 0.178, 0.07)
            for seg in range(6):
                a, b = pi * seg / 6, pi * (seg + 1) / 6

                def rib(t, x, y):
                    return (x, y + 0.048 * sin(t), z + 0.075 + 0.043 * cos(t))

                g.face(
                    cap,
                    [
                        rib(a, 0, 4.24),
                        rib(b, 0, 4.24),
                        rib(b, side * 0.56, 4.03),
                        rib(a, side * 0.56, 4.03),
                    ],
                    (0, 1, 0),
                )
    course(cap, 4.26, 0, -3.36, 3.36, 0.19, 0.12)
    g.save(dest)
