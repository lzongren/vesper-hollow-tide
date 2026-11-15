"""Pack the six CC0 moss-rock scans and grade the CC0 gravel for the shrine."""

import argparse
import json
import sys
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "native/Scripts"))
from bind_pilgrim import Output


def pack(directory, key, label, destination, foliage=False):
    doc = json.loads((directory / (key + ".gltf")).read_text())
    out = Output()
    out.doc = doc
    out.binary = bytearray((directory / doc["buffers"][0]["uri"]).read_bytes())
    base_index = doc["materials"][0]["pbrMetallicRoughness"]["baseColorTexture"][
        "index"
    ]
    base_image = doc["textures"][base_index]["source"]
    for index, img in enumerate(doc["images"]):
        path = directory / img.pop("uri")
        if foliage and index == base_image:
            color = Image.open(path).convert("RGBA")
            color.putalpha(Image.open(directory / "opacity").convert("L"))
            stream = BytesIO()
            color.save(stream, format="PNG")
            data = stream.getvalue()
            img.update(name=label + "Blades", mimeType="image/png")
        else:
            data = path.read_bytes()
        img["bufferView"] = out.block(data)
    for i, node in enumerate(doc["nodes"]):
        node.pop("translation", None)
        mesh = doc["meshes"][node["mesh"]]
        node["name"] = mesh["name"] = f"{label}{i + 1:02d}"
        if foliage:
            for prim in mesh["primitives"]:
                attrs = prim["attributes"]
                acc = doc["accessors"][attrs["POSITION"]]
                view = doc["bufferViews"][acc["bufferView"]]
                xyz = np.ndarray(
                    (acc["count"], 3),
                    dtype="<f4",
                    buffer=bytes(out.binary),
                    offset=view.get("byteOffset", 0) + acc.get("byteOffset", 0),
                    strides=(view.get("byteStride", 12), 4),
                )
                height = np.clip(xyz[:, 1] / max(acc["max"][1], 0.01), 0, 1) ** 1.6
                attrs["COLOR_0"] = out.data([(0, float(v), 0) for v in height], "VEC3")
    if foliage:
        doc["materials"][0].update(alphaMode="MASK", alphaCutoff=0.35)
    out.save(destination)


def bake(source, dest):
    dest.mkdir(parents=True, exist_ok=True)
    pack(source, "rock_moss_set_01", "FallenStone", dest / "ScreeBoulders.glb")
    for key, name in (
        ("grass_medium_02", "RavineGrass"),
        ("dandelion_01", "RavineFlower"),
    ):
        pack(source / key, key, name, dest / (name + ".glb"), foliage=True)
    color = np.array(
        Image.open(source / "Diffuse.jpg").convert("RGB"), dtype=np.float32
    )
    ao = np.array(Image.open(source / "AO.jpg").convert("L"), dtype=np.float32) / 255
    Image.fromarray(np.uint8(color * (0.68 + 0.32 * ao[..., None]))).save(
        dest / "ScreeGravel.jpg", quality=94
    )
    for source_name, name in (
        ("nor_dx", "ScreeGravelNormal"),
        ("Rough", "ScreeGravelRough"),
    ):
        (dest / (name + ".jpg")).write_bytes(
            (source / (source_name + ".jpg")).read_bytes()
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("dest", type=Path)
    args = parser.parse_args()
    bake(args.source, args.dest)
