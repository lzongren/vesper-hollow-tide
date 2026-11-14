"""Bake two buoyant bursts into the RG8 volume sampled by CinderFire.

Run with NumPy. The grid order is depth, height, width. Sixteen snapshots
are tiled in a 4 x 4 sheet, with the two simulations stacked in depth.
"""
import gzip
from pathlib import Path

import numpy as np

X, Y, Z = 40, 52, 40
FRAMES = 16
z, y, x = np.indices((Z, Y, X), dtype=np.float32)
atlas = np.zeros((2 * Z, 4 * Y, 4 * X, 2), dtype=np.uint8)


def advect(fields, velocity):
    """Backtrace one step, trilinearly resampling all fields together."""
    vx, vy, vz = velocity
    bx = np.clip(x - vx, 0, X - 1.001)
    by = np.clip(y - vy, 0, Y - 1.001)
    bz = np.clip(z - vz, 0, Z - 1.001)
    ix, iy, iz = (a.astype(int) for a in (bx, by, bz))
    dx, dy, dz = bx - ix, by - iy, bz - iz
    result = np.zeros_like(fields)
    for k, wz in enumerate((1 - dz, dz)):
        for j, wy in enumerate((1 - dy, dy)):
            for i, wx in enumerate((1 - dx, dx)):
                result += fields[:, iz + k, iy + j, ix + i] * (wx * wy * wz)
    return result


def project(v):
    # A small incompressible pressure solve allows the hot jet to billow out
    # around its head. A two-cell margin keeps the periodic stencil out of view.
    axes = (2, 1, 0)
    div = sum((np.roll(c, -1, ax) - np.roll(c, 1, ax)) * .5 for c, ax in zip(v, axes))
    pressure = np.zeros_like(div)
    for _ in range(10):
        pressure = (sum(np.roll(pressure, a, ax) for a in (-1, 1) for ax in axes) - div) / 6
    for c, ax in zip(v, axes):
        c -= .5 * (np.roll(pressure, -1, ax) - np.roll(pressure, 1, ax))
        c[:, :, :2] = c[:, :, -2:] = c[:2] = c[-2:] = 0


def bake(kind):
    fields = np.zeros((5, Z, Y, X), np.float32)
    vents = ([(-7, 1, 2.35), (1, -6, 2.8), (6, 4, 2.4)] if kind == 0 else
             [(-6, -5, 2.3), (-2, 5, 3.3), (7, -2, 2.1)])
    for tick in range(48):
        vx, vy, vz, fuel, soot = fields
        t = tick / 47
        fuel *= .942
        soot *= .981
        # Handfuls of paper catch in staggered pulses at different vents.
        for j, (ox, oz, radius) in enumerate(vents):
            pulse = np.exp(-((t - (.14 + j * .077)) / (.16 + .025 * j)) ** 2)
            pulse += .54 * np.exp(-((t - (.49 + .11*j)) / .105)**2)
            cx = 19.5 + ox + .8 * np.sin(tick * .16 + j)
            cz = 19.5 + oz + .9 * np.cos(tick * .19 + j)
            nozzle = np.exp(-((x - cx) ** 2 + (z - cz) ** 2) / radius ** 2
                            - ((y - 2.7) / 2.4) ** 2)
            fuel[:] = np.maximum(fuel, 1.65 * pulse * nozzle)
            vy += (2.7 + .85*np.sin(j*2.41+kind)) * pulse * nozzle
            vx += np.cos(j*2.13+kind)*.63*pulse*nozzle
            vz += np.sin(j*2.13+kind)*.68*pulse*nozzle
        phase = kind * 2.7
        # Transverse vortices drag different sides of a rising sheet in
        # opposite directions. Lift and smoke generation follow the local heat.
        vx += fuel * (.23 * np.sin(.29*y + .19*z + tick*.11 + phase) + .10*(kind*2-1))
        vz += fuel * (.26 * np.cos(.28*x - .17*y - tick*.12 + phase))
        vy += .55 * fuel + .21 * soot
        soot[:] = np.minimum(1, soot + .10 * fuel * (.2 + .8*np.minimum(y/10, 1)))
        project(fields[:3])
        fields = advect(fields, fields[:3])
        if tick % 3 == 2:
            frame = tick // 3
            hot = np.minimum(1, fields[3]**.70)
            smoke = np.minimum(1, fields[4]**.83)
            # A smooth edge avoids reading an adjacent tile at any mip.
            edge = np.clip(np.minimum.reduce([x, X-1-x, z, Z-1-z, Y-1-y]) / 3, 0, 1)
            data = np.stack((hot*edge, smoke*edge), axis=-1)
            ty, tx = divmod(frame, 4)
            atlas[kind*Z:(kind+1)*Z, ty*Y:(ty+1)*Y, tx*X:(tx+1)*X] = np.rint(data*255)


if __name__ == "__main__":
    for kind in range(2):
        bake(kind)
    target = Path(__file__).resolve().parents[1] / "public/textures/shrine-fire.rg8.gz"
    target.write_bytes(gzip.compress(atlas.tobytes(), compresslevel=9, mtime=0))
    print(target.name, target.stat().st_size)
