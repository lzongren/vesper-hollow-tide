"""Project the baked hot gas and soot field into a 16-frame plume for the game renderer."""

import gzip
import math
import struct
import zlib
from bind_pilgrim import Output


def bake(path, volume):
    field = gzip.decompress(volume.read_bytes())
    w, h = 160, 208
    if len(field) != w * h * 80 * 2:
        raise ValueError("Unexpected shrine fire volume dimensions")
    pixels = bytearray(w * h * 4)
    for frame in range(16):
        tx, ty = frame % 4, frame // 4
        for y in range(52):
            for x in range(40):
                trans = 1.0
                rgb = [0.0, 0.0, 0.0]
                for z in range(40):
                    j = 2 * ((z * h + ty * 52 + y) * w + tx * 40 + x)
                    heat, soot = field[j] / 255, field[j + 1] / 255
                    absorb = 1 - math.exp(-0.52 * heat - 0.34 * soot)
                    if absorb < 0.001:
                        continue
                    glow = min(1, heat * 1.95)
                    shade = (
                        0.19 + 0.81 * glow**0.42,
                        0.095 + 0.89 * glow**1.7,
                        0.055 + 0.53 * glow**3.8,
                    )
                    for k in range(3):
                        rgb[k] += trans * absorb * shade[k]
                    trans *= 1 - absorb
                alpha = 1 - trans
                idx = 4 * ((ty * 52 + 51 - y) * w + tx * 40 + x)
                if alpha > 0.001:
                    pixels[idx : idx + 4] = bytes(
                        [min(255, round(c / alpha * 255)) for c in rgb]
                        + [round(alpha * 255)]
                    )

    def chunk(name, data):
        return (
            struct.pack(">I", len(data))
            + name
            + data
            + struct.pack(">I", zlib.crc32(name + data))
        )

    raw = b"".join(b"\0" + pixels[y * w * 4 : (y + 1) * w * 4] for y in range(h))
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )
    out = Output()
    tex = out.image(png, "image/png", "ShrineFireSheet")
    out.doc["materials"].append(
        dict(
            name="Plume",
            doubleSided=True,
            alphaMode="BLEND",
            pbrMetallicRoughness=dict(baseColorTexture=tex),
        )
    )
    out.doc["meshes"][0]["name"] = "PrayerPlume"
    out.doc["nodes"] = [dict(mesh=0, name="PrayerPlume")]
    pos = [(-1.95, 0, 0), (1.95, 0, 0), (1.95, 4.55, 0), (-1.95, 4.55, 0)]
    attrs = dict(
        POSITION=out.data(pos, "VEC3", bounds=True),
        NORMAL=out.data([(0, 0, 1)] * 4, "VEC3"),
        TEXCOORD_0=out.data([(0, 1), (1, 1), (1, 0), (0, 0)], "VEC2"),
    )
    out.doc["meshes"][0]["primitives"] = [
        dict(
            attributes=attrs,
            indices=out.data([(i,) for i in (0, 1, 2, 0, 2, 3)], "SCALAR", 5125),
            material=0,
        )
    ]
    out.save(path)


def material(unreal, folder, sheet):
    lib = unreal.EditorAssetLibrary
    edit = unreal.MaterialEditingLibrary
    dest = folder + "/LivingFlame"
    if lib.does_asset_exist(dest):
        return lib.load_asset(dest)
    mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "LivingFlame", folder, unreal.Material, unreal.MaterialFactoryNew()
    )
    mat.set_editor_property("two_sided", True)
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)

    def node(cls, x, y):
        return edit.create_material_expression(mat, cls, x, y)

    def wire(a, p, b, q):
        if not edit.connect_material_expressions(a, p, b, q):
            raise RuntimeError("Fire shader pin " + q)

    uv = node(unreal.MaterialExpressionTextureCoordinate, -900, 0)
    uv.set_editor_property("u_tiling", 0.25)
    uv.set_editor_property("v_tiling", 0.25)
    offset = node(unreal.MaterialExpressionVectorParameter, -900, 140)
    offset.set_editor_property("parameter_name", "FrameUV")
    offset.set_editor_property("default_value", unreal.LinearColor(0, 0, 0, 0))
    xy = node(unreal.MaterialExpressionComponentMask, -700, 140)
    xy.set_editor_property("r", True)
    xy.set_editor_property("g", True)
    wire(offset, "", xy, "")
    add = node(unreal.MaterialExpressionAdd, -490, 0)
    wire(uv, "", add, "A")
    wire(xy, "", add, "B")
    sample = node(unreal.MaterialExpressionTextureSample, -290, 0)
    sample.set_editor_property("texture", sheet)
    wire(add, "", sample, "UVs")
    heat = node(unreal.MaterialExpressionMultiply, -70, 0)
    heat.set_editor_property("const_b", 3.4)
    wire(sample, "RGB", heat, "A")
    for n, p, target in [
        (heat, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR),
        (sample, "A", unreal.MaterialProperty.MP_OPACITY),
    ]:
        if not edit.connect_material_property(n, p, target):
            raise RuntimeError("Disconnected fire surface")
    edit.recompile_material(mat)
    if not lib.save_loaded_asset(mat, only_if_is_dirty=False):
        raise RuntimeError("Could not save fire material")
    return mat
