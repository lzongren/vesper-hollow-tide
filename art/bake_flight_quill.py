"""Build the Heron's dimensional flight feather from its original painted vane."""

from math import cos, pi, sin, tau
from pathlib import Path
import sys
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "native/Scripts"))
from bell_gallery_mesh import Joinery


def bake(source, dest):
    g = Joinery(source.parent)
    g.glb.doc["meshes"][0]["name"] = "HeronSilkFlight"
    g.glb.doc["nodes"][0]["name"] = "HeronSilkFlight"
    g.glb.doc["asset"]["generator"] = "Vesper pearl and kingfisher flight feather"
    with Image.open(source) as im:
        alpha = im.convert("RGBA").getchannel("A")
    w, h = alpha.size
    image = g.glb.image(source.read_bytes(), "image/png", "FlightSilk")
    silk = g.material("PearlVane", None, None, (1, 1, 1), 0.42, 0.10)
    mat = g.glb.doc["materials"][silk]
    mat["pbrMetallicRoughness"]["baseColorTexture"] = image
    mat.update(alphaMode="MASK", alphaCutoff=0.25)
    lake = g.material("KingfisherEdge", None, None, (0.012, 0.19, 0.22), 0.30, 0.34)
    bronze = g.material("QuillGold", None, None, (0.78, 0.42, 0.12), 0.29, 0.72)
    silver = g.material("QuillPearl", None, None, (0.58, 0.76, 0.72), 0.33, 0.20)
    # Row boundaries are taken from the opaque part of the painting. Keep the
    # quill narrow at the squared-off butt and fill out into the swept upper vane.
    stations = []
    for j in range(49):
        v = 0.987 - 0.977 * j / 48
        row = min(h - 1, round(v * (h - 1)))
        ids = [i for i in range(w) if alpha.getpixel((i, row)) > 84]
        if not ids:
            raise ValueError(f"Missing feather silhouette at {row}")
        lo, hi = ids[0] / (w - 1), ids[-1] / (w - 1)
        stations.append((v, lo, hi))

    def vane(j, u):
        t = j / 48
        v, lo, hi = stations[j]
        uv = lo + (hi - lo) * u
        lateral = (uv - 0.47) * 0.80
        camber = (1 - (2 * u - 1) ** 2) * 0.045 * sin(pi * t)
        return (
            (t - 0.50) * 1.12,
            0.052 * sin(pi * t) + camber + lateral * 0.17,
            lateral,
        ), (uv, v)

    for j in range(48):
        for k in range(8):
            points = [
                vane(r, c / 8)
                for r, c in ((j, k), (j + 1, k), (j + 1, k + 1), (j, k + 1))
            ]
            g.face(silk, [p for p, _ in points], (0, 1, 0), [uv for _, uv in points])
        for edge in (0, 1):
            # A pigmented underside and narrow leading edge survive foreshortening.
            u0, u1 = (0.005, 0.07) if edge == 0 else (0.92, 0.995)
            pts = [
                vane(r, u)[0] for r, u in ((j, u0), (j + 1, u0), (j + 1, u1), (j, u1))
            ]
            g.face(lake, [(x, y + 0.0018, z) for x, y, z in pts], (0, 1, 0))
    # A raised, tapering gilt rachis and dark quill socket cast their own shadows.
    for j in range(48):

        def shaft(row, a):
            t = row / 48
            (x, y, z), _ = vane(row, 0.45)
            radius = 0.0105 * (1 - 0.83 * t)
            return (x, y + 0.005 + radius * cos(a), z + radius * sin(a))

        for k in range(8):
            a, b = tau * k / 8, tau * (k + 1) / 8
            g.face(
                bronze if j > 10 else lake,
                [shaft(j, a), shaft(j + 1, a), shaft(j + 1, b), shaft(j, b)],
                (0, cos((a + b) / 2), sin((a + b) / 2)),
            )
    # Split barbs on the trailing edges, each rooted inside the vane.
    for side in (0, 1):
        for j in range(15 + side, 39, 3):
            start = vane(j, 0.09 if side == 0 else 0.92)[0]
            end = vane(j + 3, 0 if side == 0 else 1)[0]
            sign = 2 * side - 1
            x, y, z = end
            g.face(
                silver if j % 3 == 0 else lake,
                [
                    start,
                    (x - 0.025, y + 0.004, z),
                    (x + 0.075, y - 0.009, z + sign * 0.034),
                    (x + 0.012, y, z + sign * 0.008),
                ],
                (0, 1, 0),
            )
    # Two slipstreams peel off opposite barbs and converge behind the quill.
    # They are hidden in the hand; the flight material uses longitudinal UVs
    # to taper the light and leave air between the two ribbons.
    stream = g.material("VaneSlipstream", None, None, (0.25, 0.64, 0.62), 0.63)
    for side in (-1, 1):

        def ribbon(t, u):
            curl = sin(pi * t)
            across = 2 * u - 1
            span = (0.041 + 0.039 * curl) * (1 - 0.70 * t)
            x = -0.23 - 1.34 * t
            y = (
                0.030
                + 0.083 * curl
                + 0.061 * sin(2 * pi * t + 0.4 * side) * t
                + across * span * 0.83
            )
            z = side * (0.098 + 0.135 * curl - 0.053 * t) + across * span * 0.56
            return x, y, z

        for k in range(28):
            a, b = k / 28, (k + 1) / 28
            coords = ((a, 0), (b, 0), (b, 1), (a, 1))
            g.face(
                stream,
                [ribbon(t, u) for t, u in coords],
                (0, 1, 0),
                [(u, t) for t, u in coords],
            )
    g.save(dest)


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    bake(root / "public/art/heron-quill.png", root / "native/Art/HeronSilkFlight.glb")
