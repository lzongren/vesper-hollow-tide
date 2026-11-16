"""Blue-grey kiln glaze with continuous grain across the overlapping roof tiles."""

import unreal


def glaze(folder):
    lib = unreal.EditorAssetLibrary
    path = folder + "/RainGlaze"
    if lib.does_asset_exist(path):
        return lib.load_asset(path)
    mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "RainGlaze", folder, unreal.Material, unreal.MaterialFactoryNew()
    )
    mat.set_editor_property("used_with_nanite", True)
    edit = unreal.MaterialEditingLibrary

    def node(cls, x, y):
        return edit.create_material_expression(mat, cls, x, y)

    def wire(a, out, b, pin):
        if not edit.connect_material_expressions(a, out, b, pin):
            raise RuntimeError("Could not wire kiln glaze " + pin)

    def value(x, y, v):
        n = node(unreal.MaterialExpressionConstant, x, y)
        n.set_editor_property("r", v)
        return n

    pos = node(unreal.MaterialExpressionWorldPosition, -1050, 0)
    xy = node(unreal.MaterialExpressionComponentMask, -890, 0)
    xy.set_editor_property("r", True)
    xy.set_editor_property("g", True)
    wire(pos, "", xy, "")
    uv = node(unreal.MaterialExpressionMultiply, -700, 0)
    wire(xy, "", uv, "A")
    wire(value(-880, 140, 0.0042), "", uv, "B")

    def sample(name, kind, y):
        tex = node(unreal.MaterialExpressionTextureSample, -490, y)
        tex.set_editor_property(
            "texture", lib.load_asset("/Game/Vesper/Understory/Shale" + name)
        )
        tex.set_editor_property("sampler_type", kind)
        wire(uv, "", tex, "UVs")
        return tex

    smp = unreal.MaterialSamplerType
    grain = sample("Color", smp.SAMPLERTYPE_COLOR, 0)
    soot = node(unreal.MaterialExpressionDesaturation, -240, -90)
    wire(grain, "RGB", soot, "")
    wire(value(-420, -145, 1), "", soot, "Fraction")
    tint = node(unreal.MaterialExpressionConstant3Vector, -180, 36)
    tint.set_editor_property("constant", unreal.LinearColor(0.28, 0.37, 0.40, 1))
    pigment = node(unreal.MaterialExpressionMultiply, 0, -40)
    wire(tint, "", pigment, "A")
    wire(soot, "", pigment, "B")
    rough = sample("Rough", smp.SAMPLERTYPE_MASKS, 285)
    finish = node(unreal.MaterialExpressionLinearInterpolate, 0, 190)
    wire(value(-165, 178, 0.41), "", finish, "A")
    wire(value(-165, 270, 0.66), "", finish, "B")
    wire(rough, "R", finish, "Alpha")
    for component, prop in (
        (pigment, unreal.MaterialProperty.MP_BASE_COLOR),
        (finish, unreal.MaterialProperty.MP_ROUGHNESS),
    ):
        if not edit.connect_material_property(component, "", prop):
            raise RuntimeError("Could not bind the glaze surface")
    edit.recompile_material(mat)
    if not lib.save_loaded_asset(mat, only_if_is_dirty=False):
        raise RuntimeError("Could not save the blue-grey glaze")
    return mat
