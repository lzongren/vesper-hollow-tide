"""Build the thrown feather and the bride's short blade-and-silk sound."""

import array
import math
from random import Random
import sys
import wave
from bind_pilgrim import Output


def bake_quill(path, image):
    out = Output()
    out.doc["meshes"][0]["name"] = "CastQuill"
    out.doc["nodes"] = [{"mesh": 0}]
    texture = out.image(image.read_bytes(), "image/png", "FlightVane")
    out.doc["materials"] = [
        dict(
            name="SilverQuill",
            alphaMode="MASK",
            alphaCutoff=0.32,
            doubleSided=True,
            pbrMetallicRoughness=dict(
                baseColorTexture=texture, metallicFactor=0.17, roughnessFactor=0.48
            ),
        )
    ]
    pos = []
    uv = []
    idx = []
    for j in range(13):
        t = j / 12
        for i in range(3):
            across = (i - 1) * 0.095
            pos.append(
                ((t - 0.5) * 0.7, across * 0.65 + 0.04 * math.sin(math.pi * t), across)
            )
            uv.append((i / 2, t))
        if j:
            for k in range(2):
                a = (j - 1) * 3 + k
                idx.extend((a, a + 1, a + 3, a + 3, a + 1, a + 4))
    attrs = dict(
        POSITION=out.data(pos, "VEC3", bounds=True), TEXCOORD_0=out.data(uv, "VEC2")
    )
    out.doc["meshes"][0]["primitives"] = [
        dict(
            attributes=attrs,
            material=0,
            indices=out.data([(i,) for i in idx], "SCALAR", 5125),
        )
    ]
    out.save(path)


def draw_sound(path):
    rate = 32000
    rng = Random(37)
    samples = array.array("h")
    slow = fast = phase = 0.0
    for i in range(rate):
        t = i / rate
        noise = rng.uniform(-1, 1)
        slow += 0.08 * (noise - slow)
        fast += 0.58 * (noise - fast)
        hiss = (fast - slow) * math.exp(-(((t - 0.22) / 0.12) ** 2))
        phase += math.tau * (1230 + 1400 * t) / rate
        ring = math.sin(phase) * math.exp(-6 * t) * min(1, t / 0.028)
        samples.append(round(16000 * (0.65 * hiss + 0.32 * ring)))
    if sys.byteorder != "little":
        samples.byteswap()
    with wave.open(str(path), "wb") as out:
        out.setparams((1, 2, rate, 0, "NONE", ""))
        out.writeframes(samples.tobytes())
