"""Generate the valley floor in metres. Interchange imports its GLB into Unreal."""
import json
import math
import struct
from pathlib import Path


def bake_valley(source, output):
    vertices, normals, uvs, faces = [], [], [], []
    n, step = 145, 3.0

    def height(x, z):
        radius = math.hypot(x, z)
        rim = max(0, min(1, (radius - 108) / 81))
        relief = math.sin(x / 28 + math.sin(z / 17)) * math.cos(z / 24)
        stream = math.exp(-((z - 29 * math.sin(x / 47)) / 13) ** 2)
        return -3.2 - 2.6 * stream + relief * 1.1 + rim * rim * (11 + 10 * relief)

    for row in range(n):
        for col in range(n):
            x, z = (col - (n - 1) / 2) * step, (row - (n - 1) / 2) * step
            y = height(x, z)
            dx = (height(x + 0.5, z) - height(x - 0.5, z))
            dz = (height(x, z + 0.5) - height(x, z - 0.5))
            length = math.sqrt(1 + dx * dx + dz * dz)
            vertices.extend((x, y, z))
            normals.extend((-dx / length, 1 / length, -dz / length))
            uvs.extend((x / 3.2, z / 3.2))
            if row and col:
                i = row * n + col
                faces.extend((i - n - 1, i - 1, i, i - n - 1, i, i - n))

    data, views = bytearray(), []
    def block(raw):
        data.extend(bytes(-len(data) % 4))
        views.append({"buffer": 0, "byteOffset": len(data), "byteLength": len(raw)})
        data.extend(raw)
        return len(views) - 1

    accessors = []
    for values, dimensions, count, fmt, component in [
        (vertices, "VEC3", n*n, "f", 5126), (normals, "VEC3", n*n, "f", 5126),
        (uvs, "VEC2", n*n, "f", 5126), (faces, "SCALAR", len(faces), "H", 5123)
    ]:
        accessors.append({"bufferView": block(struct.pack("<" + str(len(values)) + fmt, *values)),
                          "componentType": component, "count": count, "type": dimensions})
    accessors[0].update(min=[min(vertices[k::3]) for k in range(3)], max=[max(vertices[k::3]) for k in range(3)])
    image = block((source / "rock-color.jpg").read_bytes())
    document = {"asset":{"version":"2.0"},"scene":0,"scenes":[{"nodes":[0]}],"nodes":[{"mesh":0}],
                "meshes":[{"name":"Mountain valley","primitives":[{"attributes":{"POSITION":0,"NORMAL":1,"TEXCOORD_0":2},"indices":3,"material":0}]}],
                "materials":[{"name":"Weathered valley earth","pbrMetallicRoughness":{"baseColorTexture":{"index":0},
                "baseColorFactor":[0.34,0.40,0.28,1],"metallicFactor":0,"roughnessFactor":0.94}}],
                "images":[{"bufferView":image,"mimeType":"image/jpeg"}],"textures":[{"source":0}],
                "accessors":accessors,"bufferViews":views,"buffers":[{"byteLength":len(data)}]}
    header = json.dumps(document,separators=(",",":")).encode()
    header += b" " * (-len(header) % 4)
    data.extend(bytes(-len(data) % 4))
    output.write_bytes(struct.pack("<4sIIII",b"glTF",2,28+len(header)+len(data),len(header),0x4E4F534A)
                       +header+struct.pack("<II",len(data),0x004E4942)+data)


if __name__ == "__main__":
    project = Path(__file__).resolve().parents[1]
    bake_valley(project.parent / "public" / "textures", project / "Art" / "MountainValley.glb")
