"""Bake two orthogonal colour/coverage views of four Poly Haven conifers.

Input directories are named pine_tree_01 and fir_tree_01. Each contains the 1K
glTF, its external BIN, diffuse textures, and the matching twig alpha map saved
as twig-alpha.jpg. Only the baked atlas is needed on the game machine.
"""

import argparse
import json
from pathlib import Path

import moderngl
import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt

VERT = """
#version 330
in vec3 position;
in vec3 normal;
in vec2 uv;
uniform vec2 right_axis;
uniform float height;
out vec2 coord;
out vec3 N;
void main(){
    vec2 depth_axis=vec2(-right_axis.y,right_axis.x);
    gl_Position=vec4(dot(position.xz,right_axis)/(height*.32),
                     2.*position.y/height-.975, -dot(position.xz,depth_axis)/height, 1.);
    coord=uv;
    N=normal;
}
"""
FRAG = """
#version 330
in vec2 coord; in vec3 N;
uniform sampler2D color_tex; uniform sampler2D mask_tex;
uniform bool use_mask;
uniform vec2 uv_scale; uniform vec2 uv_offset;
uniform vec2 right_axis;
out vec4 out_color;
void main(){
    vec2 uv=coord*uv_scale+uv_offset;
    if(use_mask && texture(mask_tex,uv).r<.40) discard;
    vec3 c=texture(color_tex,uv).rgb;
    vec3 L=normalize(vec3(right_axis.x*.62,.80,right_axis.y*.62));
    float light=.79+.21*abs(dot(normalize(N),L));
    out_color=vec4(c*light*vec3(.94,1.,.94)+vec3(.044,.068,.056),1.);
}
"""


def accessor(doc, buf, index):
    a = doc["accessors"][index]
    b = doc["bufferViews"][a["bufferView"]]
    dtype = np.dtype({5123: "<u2", 5125: "<u4", 5126: "<f4"}[a["componentType"]])
    width = {"VEC3": 3, "VEC2": 2, "SCALAR": 1}[a["type"]]
    return np.ndarray(
        (a["count"], width),
        dtype=dtype,
        buffer=buf,
        offset=b.get("byteOffset", 0) + a.get("byteOffset", 0),
        strides=(b.get("byteStride", dtype.itemsize * width), dtype.itemsize),
    )


def render(ctx, program, directory, index):
    path = next(directory.glob("*.gltf"))
    doc = json.loads(path.read_text())
    buf = np.memmap(directory / doc["buffers"][0]["uri"], mode="r", dtype="u1")
    parts = doc["meshes"][index]["primitives"]
    height = (
        max(doc["accessors"][p["attributes"]["POSITION"]]["max"][1] for p in parts)
        * 1.02
    )
    program["height"].value = height
    size = 768
    fb = [ctx.simple_framebuffer((size, size)) for _ in range(2)]
    for f in fb:
        f.use()
        f.clear(0, 0, 0, 0, depth=1.0)

    def texture(path, mode):
        im = Image.open(path).convert(mode)
        tex = ctx.texture(im.size, len(mode), im.tobytes(), alignment=1)
        tex.build_mipmaps()
        return tex

    mask = texture(directory / "twig-alpha.jpg", "L")
    mask.use(1)
    for p in parts:
        mat = doc["materials"][p["material"]]
        ref = mat["pbrMetallicRoughness"]["baseColorTexture"]
        view = doc["textures"][ref["index"]]
        tex = texture(directory / doc["images"][view["source"]]["uri"], "RGB")
        tex.use(0)
        transform = ref.get("extensions", {}).get("KHR_texture_transform", {})
        program["uv_scale"].value = tuple(transform.get("scale", (1, 1)))
        program["uv_offset"].value = tuple(transform.get("offset", (0, 0)))
        program["use_mask"].value = "twig" in mat["name"] and mat.get("alphaMode") in (
            "BLEND",
            "MASK",
        )
        attrs = [
            accessor(doc, buf, p["attributes"][key])
            for key in ("POSITION", "NORMAL", "TEXCOORD_0")
        ]
        vert = ctx.buffer(
            np.ascontiguousarray(np.concatenate(attrs, axis=1), dtype="f4")
        )
        idx = ctx.buffer(
            np.ascontiguousarray(accessor(doc, buf, p["indices"]), dtype="u4")
        )
        vao = ctx.vertex_array(
            program,
            [(vert, "3f 3f 2f", "position", "normal", "uv")],
            idx,
            index_element_size=4,
        )
        for i, f in enumerate(fb):
            f.use()
            program["right_axis"].value = ((1.0, 0.0), (0.0, 1.0))[i]
            vao.render()
        vao.release()
        idx.release()
        vert.release()
        tex.release()
    mask.release()
    tiles = []
    for f in fb:
        pixels = f.read(components=4, alignment=1)
        im = Image.frombytes("RGBA", (size, size), pixels).transpose(
            Image.Transpose.FLIP_TOP_BOTTOM
        )
        im = im.resize((512, 512), Image.Resampling.LANCZOS)
        # Extend colour through the transparent edge before Unreal filters mips.
        arr = np.array(im)
        y, x = distance_transform_edt(
            arr[:, :, 3] < 22, return_distances=False, return_indices=True
        )
        arr[:, :, :3] = arr[y, x, :3]
        tiles.append(Image.fromarray(arr))
        f.release()
    return tiles


def bake(source, output):
    ctx = moderngl.create_standalone_context(backend="egl")
    ctx.enable(moderngl.DEPTH_TEST)
    program = ctx.program(vertex_shader=VERT, fragment_shader=FRAG)
    program["color_tex"].value = 0
    program["mask_tex"].value = 1
    atlas = Image.new("RGBA", (2048, 1024))
    for col, (model, index) in enumerate(
        (
            ("pine_tree_01", 0),
            ("pine_tree_01", 1),
            ("fir_tree_01", 0),
            ("fir_tree_01", 1),
        )
    ):
        for row, tile in enumerate(render(ctx, program, source / model, index)):
            atlas.paste(tile, (512 * col, 512 * row))
    atlas.save(output)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source", type=Path)
    ap.add_argument("output", type=Path)
    args = ap.parse_args()
    bake(args.source, args.output)
