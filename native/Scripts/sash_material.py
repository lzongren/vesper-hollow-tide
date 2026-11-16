"""Curve the trailing brocade along its authored warp coordinate in world space."""

import unreal
from keeper_materials import surface


def silk_motion(root):
    edit = unreal.MaterialEditingLibrary
    mat = surface(root, "WovenStreamers", "RiverBrocade", 0.04, 0.65)
    dst = unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET
    if edit.get_material_property_input_node(mat, dst):
        return mat

    def node(kind, x, y):
        return edit.create_material_expression(mat, kind, x, y)

    def link(a, pin, b, socket):
        if not edit.connect_material_expressions(a, pin, b, socket):
            raise RuntimeError("Could not wire sash " + socket)

    uv = node(unreal.MaterialExpressionTextureCoordinate, -900, 800)
    v = node(unreal.MaterialExpressionComponentMask, -700, 800)
    v.set_editor_property("r", False)
    v.set_editor_property("g", True)
    link(uv, "", v, "")
    square = node(unreal.MaterialExpressionMultiply, -480, 800)
    link(v, "", square, "A")
    link(v, "", square, "B")
    drag = node(unreal.MaterialExpressionVectorParameter, -480, 980)
    drag.set_editor_property("parameter_name", "HemOffsetCm")
    weighted = node(unreal.MaterialExpressionMultiply, -255, 830)
    link(square, "", weighted, "A")
    link(drag, "", weighted, "B")
    if not edit.connect_material_property(weighted, "", dst):
        raise RuntimeError("Could not attach the sash displacement")
    mat.set_editor_property("max_world_position_offset_displacement", 32.0)
    edit.recompile_material(mat)
    if not unreal.EditorAssetLibrary.save_loaded_asset(mat, only_if_is_dirty=False):
        raise RuntimeError("Could not save the sash material")
    return mat
