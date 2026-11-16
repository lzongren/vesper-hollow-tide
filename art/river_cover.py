"""Grade an aligned Xingping Sentinel-2 crop into the river-valley ground cover."""

from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import from_bounds
from rasterio.vrt import WarpedVRT

from extract_river_heights import CROP

SCENE = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/49/R/DH/2024/10/S2B_49RDH_20241003_0_L2A"


def raster(name, transform, width, height, method):
    with (
        rasterio.open(f"{SCENE}/{name}.tif") as src,
        WarpedVRT(
            src,
            crs="EPSG:4326",
            transform=transform,
            width=width,
            height=height,
            resampling=method,
        ) as warped,
    ):
        return warped.read()


def bake(heights, output):
    import gzip

    width, height = 1440, 1200
    left, top, right, bottom = CROP
    transform = from_bounds(
        110 + left / 3600,
        25 - (bottom - 1) / 3600,
        110 + (right - 1) / 3600,
        25 - top / 3600,
        width,
        height,
    )
    rgb = raster("TCI", transform, width, height, Resampling.bilinear).astype(
        np.float32
    )
    classes = raster("SCL", transform, width, height, Resampling.nearest)[0]
    if np.any(classes == 0) or np.any(classes >= 8):
        raise ValueError("Incomplete or cloudy land-cover sample")
    luminance = 0.24 * rgb[0] + 0.66 * rgb[1] + 0.10 * rgb[2]
    local = np.asarray(
        Image.fromarray(luminance.astype(np.uint8)).filter(ImageFilter.GaussianBlur(5)),
        dtype=float,
    )
    elevation = (
        np.frombuffer(gzip.decompress(heights.read_bytes()), dtype="<u2")
        .reshape(bottom - top, right - left)
        .astype(np.float32)
        * 0.1
    )
    dy, dx = np.gradient(elevation, 30.8, 28.0)
    slope = np.hypot(dx, dy)
    sm = np.asarray(
        Image.fromarray(slope).resize((width, height), Image.Resampling.BILINEAR)
    )
    # Modern fields, roofs and roads have no place on the fictional pilgrimage.
    # Keep forest mottling from the orbital sample; infer bare slopes from relief.
    detail = np.clip((luminance - local) * 0.018, -0.32, 0.32)
    forest = classes == 4
    brightness = np.where(
        forest, np.clip((local - 42) / 70, -0.30, 0.50) + detail, 0.07
    )
    rock = np.clip((sm - 0.55) / 0.80, 0, 1)
    rock = np.clip(rock + 0.12 * np.where(forest, detail, 0), 0, 1)
    veg = np.array([60, 80, 70]) + brightness[:, :, None] * np.array([39, 38, 32])
    limestone = np.array([134, 137, 128]) + np.clip(detail, -0.15, 0.18)[
        :, :, None
    ] * np.array([40, 37, 32])
    color = veg + (limestone - veg) * rock[:, :, None]
    Image.fromarray(np.clip(color, 0, 255).astype(np.uint8)).save(
        output, quality=94, subsampling=0
    )


if __name__ == "__main__":
    folder = Path(__file__).resolve().parents[1] / "native" / "Art" / "RiverPeaks"
    bake(folder / "Xingping.r16.gz", folder / "ValleyCover.jpg")
