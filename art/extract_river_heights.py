"""Extract the Xingping crop used by the native mountain backdrop."""

import argparse
from array import array
import gzip
import hashlib
from pathlib import Path
import sys

from PIL import Image

DIGEST = "fc2cd2f77f8f6b2901f5667aaf536ddd255d5295db01cf64b878c8b4ee2020bf"
CROP = (1545, 120, 2026, 521)


def extract(source: Path, destination: Path):
    if hashlib.sha256(source.read_bytes()).hexdigest() != DIGEST:
        raise ValueError("Expected the unmodified Copernicus N24 E110 GLO-30 tile")
    with Image.open(source) as image:
        patch = image.crop(CROP)
        # Preserve tenth-metre heights without depending on a GeoTIFF reader at launch.
        values = array("H", (round(v * 10) for v in patch.getdata()))
    if sys.byteorder != "little":
        values.byteswap()
    destination.write_bytes(gzip.compress(values.tobytes(), compresslevel=9, mtime=0))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    opts = parser.parse_args()
    extract(opts.source, opts.destination)
