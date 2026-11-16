"""Bake three chipped ashlar retaining-wall bays as static geometry, in glTF metres."""

from pathlib import Path
from random import Random

from bind_pilgrim import Output, cross, unit

BAY = 6.4


def bake_walls(textures, output):
    glb = Output()
    glb.doc.update(nodes=[], meshes=[], scenes=[{"nodes": []}])
    glb.doc["asset"]["generator"] = "Vesper retaining masonry"
    color = glb.image(
        (textures / "rock-color.jpg").read_bytes(), "image/jpeg", "Quarry face"
    )
    normal = glb.image(
        (textures / "rock-normal.jpg").read_bytes(), "image/jpeg", "Split stone grain"
    )
    glb.doc["materials"].append(
        {
            "name": "Split ashlar",
            "pbrMetallicRoughness": {
                "baseColorTexture": color,
                "roughnessFactor": 0.86,
                "metallicFactor": 0,
            },
            "normalTexture": normal,
        }
    )

    for variant in range(4):
        append_variant(glb, variant)
    glb.save(output)


def append_variant(glb, variant):
    rng = Random(29137 + variant)
    pos, nor, uv, rgb = [], [], [], []

    def block(x0, x1, y0, y1, depth, shade, bevel):
        ox, oy = rng.uniform(0, 6), rng.uniform(0, 6)
        bits = [rng.uniform(0.035, 0.105) for _ in range(4)]

        # Coordinates along the wall and across it, clockwise as seen from above.
        def ring(y, inset):
            a, b = x0 + inset, x1 - inset
            d = depth - inset
            return [
                (a + bits[0], y, -d),
                (a, y, -d + bits[0]),
                (a, y, d - bits[1]),
                (a + bits[1], y, d),
                (b - bits[2], y, d),
                (b, y, d - bits[2]),
                (b, y, -d + bits[3]),
                (b - bits[3], y, -d),
            ]

        bottom = ring(y0, bevel * 0.5)
        low = ring(y0 + bevel, 0)
        high = ring(y1 - bevel, 0)
        top = ring(y1, bevel)

        def triangle(a, b, c, face_shade):
            n = unit(
                cross(
                    tuple(j - i for i, j in zip(a, b)),
                    tuple(j - i for i, j in zip(a, c)),
                )
            )
            for x, y, z in (a, b, c):
                pos.append((x, y, z))
                nor.append(n)
                if abs(n[1]) > 0.7:
                    uv.append((ox + x / 1.45, oy + z / 1.45))
                elif abs(n[0]) > 0.7:
                    uv.append((ox + z / 1.45, oy - y / 1.45))
                else:
                    uv.append((ox + x / 1.45, oy - y / 1.45))
                # Damp courses nearest the valley pick up a subdued green cast.
                damp = max(0, min(1, (-y - 1) / 4))
                rgb.append(
                    tuple(
                        v * face_shade
                        for v in (
                            shade * (1 - 0.22 * damp),
                            shade * (1 - 0.13 * damp),
                            shade * (1 - 0.25 * damp),
                        )
                    )
                )

        for i in range(8):
            j = (i + 1) % 8
            for upper, lower, factor in [
                (top, high, 0.97),
                (high, low, 1),
                (low, bottom, 0.73),
            ]:
                triangle(upper[i], lower[i], lower[j], factor)
                triangle(upper[i], lower[j], upper[j], factor)
            triangle(((x0 + x1) / 2, y1, 0), top[i], top[j], 1.04)
            triangle(((x0 + x1) / 2, y0, 0), bottom[j], bottom[i], 0.66)

    if variant == 3:
        for left, right in [(-1.25, -0.37), (-0.37, 0.44), (0.44, 1.25)]:
            block(
                left + 0.007,
                right - 0.007,
                -0.38,
                0,
                0.195,
                rng.uniform(0.63, 0.77),
                0.022,
            )
        for side in (-1, 1):
            cx = side * 1.38
            block(cx - 0.145, cx + 0.145, -0.57, 0.11, 0.189, 0.61, 0.023)
        name = "DescentTread"
    else:
        # Courses change bond at every lift. Block widths close exactly at each bay end.
        for row in range(15):
            h = 0.40 if row else 0.27
            top = -0.045 if row == 0 else -0.315 - (row - 1) * 0.40
            weights = [rng.uniform(0.65, 1.55) for _ in range(rng.choice([5, 6, 7]))]
            x = -BAY / 2
            for w in weights:
                end = x + BAY * w / sum(weights)
                depth = (0.32 if row == 0 else 0.22 + row * 0.020) + rng.uniform(
                    -0.018, 0.03
                )
                block(
                    x + 0.011,
                    end - 0.011,
                    top - h + 0.012,
                    top,
                    depth,
                    rng.uniform(0.48, 0.78),
                    rng.uniform(0.019, 0.04),
                )
                x = end
        # Offset stone footing and stepped buttress, with an oversized drip cap.
        bx = (-0.32 + variant * 0.27) * BAY / 2
        for k in range(9):
            top = -1.02 - 0.52 * k
            width = 0.66 + 0.064 * k
            block(
                bx - width / 2,
                bx + width / 2,
                top - 0.51,
                top,
                0.41 + 0.057 * k,
                rng.uniform(0.50, 0.68),
                0.045,
            )
        block(bx - 0.42, bx + 0.42, -1.1, -0.98, 0.48, 0.71, 0.035)
        name = f"AshlarBay{variant + 1}"
    attrs = {
        "POSITION": glb.data(pos, "VEC3", bounds=True),
        "NORMAL": glb.data(nor, "VEC3"),
        "TEXCOORD_0": glb.data(uv, "VEC2"),
        "COLOR_0": glb.data(rgb, "VEC3"),
    }
    glb.doc["meshes"].append(
        {"name": name, "primitives": [{"attributes": attrs, "material": 0}]}
    )
    glb.doc["nodes"].append({"name": name, "mesh": variant})
    glb.doc["scenes"][0]["nodes"].append(variant)


if __name__ == "__main__":
    import sys

    bake_walls(Path(sys.argv[1]), Path(sys.argv[2]))
