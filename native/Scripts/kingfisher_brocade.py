"""Overdye the rose ground of the collar, preserving ivory and gold embroidery."""

import unreal
from keeper_materials import surface


def overdyed_collar(root):
    mat = surface(root, "LakeBlueSilk", "RuyiBrocade", 0.08, 0.61)
    edit = unreal.MaterialEditingLibrary
    prop = unreal.MaterialProperty.MP_BASE_COLOR
    base = edit.get_material_property_input_node(mat, prop)
    if isinstance(base, unreal.MaterialExpressionCustom):
        return mat
    dye = edit.create_material_expression(mat, unreal.MaterialExpressionCustom, -30, 0)
    dye.set_editor_property("description", "Lake-blue ground, reserved embroidery")
    dye.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    pin = unreal.CustomInput()
    pin.set_editor_property("input_name", "Silk")
    dye.set_editor_property("inputs", [pin])
    dye.set_editor_property(
        "code",
        """
        float3 c = Silk;
        float rose = smoothstep(1.08, 1.52, c.r / max(0.002,c.g))
                   * smoothstep(0.91, 1.10, c.b / max(0.002,c.g));
        float value = dot(c,float3(.30,.60,.10));
        return lerp(c,value*float3(.24,.91,1.03),rose);
    """,
    )
    if not edit.connect_material_expressions(
        base, "RGB", dye, "Silk"
    ) or not edit.connect_material_property(dye, "", prop):
        raise RuntimeError("Could not connect the dyed silk")
    edit.recompile_material(mat)
    unreal.EditorAssetLibrary.save_loaded_asset(mat, only_if_is_dirty=False)
    return mat
