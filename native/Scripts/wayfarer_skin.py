"""Blend the portrait into plain skin beyond the visible facial landmarks."""

import unreal
from keeper_materials import surface


def complexion(root):
    lib = unreal.EditorAssetLibrary
    edit = unreal.MaterialEditingLibrary
    mat = surface(root, "PorcelainSkin", "WayfarerSkin", 0, 0.54)
    color = unreal.MaterialProperty.MP_BASE_COLOR
    projected = edit.get_material_property_input_node(mat, color)

    if isinstance(projected, unreal.MaterialExpressionLinearInterpolate):
        return mat

    def node(kind, x, y):
        return edit.create_material_expression(mat, kind, x, y)

    def wire(source, channel, target, pin):
        if not edit.connect_material_expressions(source, channel, target, pin):
            raise RuntimeError("Could not connect facial colour input " + pin)

    swatch = node(unreal.MaterialExpressionConstant2Vector, -720, 200)
    swatch.set_editor_property("r", 0.65)
    swatch.set_editor_property("g", 0.64)
    skin = node(unreal.MaterialExpressionTextureSample, -500, 200)
    skin.set_editor_property("texture", projected.get_editor_property("texture"))
    wire(swatch, "", skin, "UVs")
    uv = node(unreal.MaterialExpressionTextureCoordinate, -720, 340)
    uv.set_editor_property("coordinate_index", 1)
    mask = node(unreal.MaterialExpressionComponentMask, -500, 340)
    mask.set_editor_property("r", True)
    mask.set_editor_property("g", False)
    wire(uv, "", mask, "")
    blend = node(unreal.MaterialExpressionLinearInterpolate, -80, 40)
    wire(skin, "RGB", blend, "A")
    wire(projected, "RGB", blend, "B")
    wire(mask, "", blend, "Alpha")
    if not edit.connect_material_property(blend, "", color):
        raise RuntimeError("Could not install facial colour blend")
    edit.recompile_material(mat)
    if not lib.save_loaded_asset(mat, only_if_is_dirty=False):
        raise RuntimeError("Could not save the skin material")
    return mat
