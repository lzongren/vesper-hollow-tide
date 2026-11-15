"""Install a wet cornea and a morph-compatible dark lash material."""

import unreal
from keeper_materials import surface


def lashes(root):
    lib = unreal.EditorAssetLibrary
    path = root + "/Finish/LashSilk"
    if lib.does_asset_exist(path):
        return lib.load_asset(path)
    mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "LashSilk", root + "/Finish", unreal.Material, unreal.MaterialFactoryNew()
    )
    mat.set_editor_property("two_sided", True)
    mat.set_editor_property("used_with_skeletal_mesh", True)
    mat.set_editor_property("used_with_morph_targets", True)
    edit = unreal.MaterialEditingLibrary
    rgb = edit.create_material_expression(
        mat, unreal.MaterialExpressionConstant3Vector, -180, 0
    )
    rgb.set_editor_property("constant", unreal.LinearColor(0.024, 0.012, 0.010, 1))
    edit.connect_material_property(rgb, "", unreal.MaterialProperty.MP_BASE_COLOR)
    edit.recompile_material(mat)
    lib.save_loaded_asset(mat, only_if_is_dirty=False)
    return mat


def cornea(root):
    mat = surface(root, "CourtyardCornea", "WetIris", 0, 0.31, specular=0.25)
    edit = unreal.MaterialEditingLibrary
    prop = unreal.MaterialProperty
    if not mat.get_editor_property("used_with_morph_targets"):
        mat.set_editor_property("used_with_morph_targets", True)
        edit.recompile_material(mat)
        unreal.EditorAssetLibrary.save_loaded_asset(mat, only_if_is_dirty=False)
    if edit.get_material_property_input_node(mat, prop.MP_EMISSIVE_COLOR):
        return mat

    def node(cls, x, y):
        return edit.create_material_expression(mat, cls, x, y)

    # Use the lit surface for environmental highlights. The iris rotates under it.
    uv = node(unreal.MaterialExpressionTextureCoordinate, -900, -120)
    direction = node(unreal.MaterialExpressionVectorParameter, -900, 40)
    direction.set_editor_property("parameter_name", "IrisDirection")
    direction.set_editor_property("default_value", unreal.LinearColor(0, 0, 0, 0))
    project = node(unreal.MaterialExpressionCustom, -600, -80)
    project.set_editor_property("description", "Iris on the fitted globe")
    project.set_editor_property(
        "output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT2
    )
    inputs = []
    for name in ("EyeUV", "Direction"):
        pin = unreal.CustomInput()
        pin.set_editor_property("input_name", name)
        inputs.append(pin)
    project.set_editor_property("inputs", inputs)
    project.set_editor_property(
        "code",
        """
        // wayfarer_outfit.globe projects 44.5 mm of the eye onto the atlas.
        float2 r = float2(19.2, 15.8) / 44.5;
        float2 xy = (EyeUV - 0.5) / float2(r.x, -r.y);
        float z = sqrt(saturate(1 - dot(xy, xy)));
        float2 c = sqrt(saturate(1 - Direction.xy * Direction.xy));
        float localX = c.x * xy.x - Direction.x * z;
        float yawZ = Direction.x * xy.x + c.x * z;
        float localY = c.y * xy.y - Direction.y * yawZ;
        return 0.5 + float2(localX * r.x, -localY * r.y) / 1.13;
    """,
    )
    pigment = edit.get_material_property_input_node(mat, prop.MP_BASE_COLOR)
    for source, dest, pin in (
        (uv, project, "EyeUV"),
        (direction, project, "Direction"),
        (project, pigment, "UVs"),
    ):
        if not edit.connect_material_expressions(source, "", dest, pin):
            raise RuntimeError("Could not wire iris projection at " + pin)
    iris = node(unreal.MaterialExpressionCustom, -340, 280)
    iris.set_editor_property("description", "Dark limbus and brown iris")
    iris.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    inputs = []
    for name in ("AtlasUV", "Pigment"):
        pin = unreal.CustomInput()
        pin.set_editor_property("input_name", name)
        inputs.append(pin)
    iris.set_editor_property("inputs", inputs)
    iris.set_editor_property(
        "code",
        "float r=length(AtlasUV-.5); return Pigment*lerp(.47,1.,smoothstep(.13,.16,r));",
    )
    edit.connect_material_expressions(project, "", iris, "AtlasUV")
    edit.connect_material_expressions(pigment, "RGB", iris, "Pigment")
    edit.connect_material_property(iris, "", prop.MP_BASE_COLOR)
    glint = node(unreal.MaterialExpressionCustom, -340, 450)
    glint.set_editor_property(
        "output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT1
    )
    pin = unreal.CustomInput()
    pin.set_editor_property("input_name", "EyeUV")
    glint.set_editor_property("inputs", [pin])
    glint.set_editor_property(
        "code",
        "float2 d=(EyeUV-float2(.457,.440))/float2(.009,.011); return .23*exp(-dot(d,d));",
    )
    edit.connect_material_expressions(uv, "", glint, "EyeUV")
    edit.connect_material_property(glint, "", prop.MP_EMISSIVE_COLOR)
    edit.recompile_material(mat)
    unreal.EditorAssetLibrary.save_loaded_asset(mat, only_if_is_dirty=False)
    return mat


def hair_roots(root):
    # Let the thinnest roots reveal skin continuously at close range.
    mat = surface(root, "CombedHairline", "TempleStrands", 0, 0.60, specular=0.22)
    edit = unreal.MaterialEditingLibrary
    prop = unreal.MaterialProperty
    if edit.get_material_property_input_node(mat, prop.MP_OPACITY):
        return mat
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property(
        "translucency_lighting_mode",
        unreal.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING,
    )
    image = edit.get_material_property_input_node(mat, prop.MP_BASE_COLOR)
    uv = edit.create_material_expression(
        mat, unreal.MaterialExpressionTextureCoordinate, -620, 200
    )
    v = edit.create_material_expression(
        mat, unreal.MaterialExpressionComponentMask, -440, 200
    )
    v.set_editor_property("r", False)
    v.set_editor_property("g", True)
    edit.connect_material_expressions(uv, "", v, "")
    ramp = edit.create_material_expression(
        mat, unreal.MaterialExpressionOneMinus, -280, 200
    )
    edit.connect_material_expressions(v, "", ramp, "")
    opacity = edit.create_material_expression(
        mat, unreal.MaterialExpressionMultiply, -80, 170
    )
    edit.connect_material_expressions(ramp, "", opacity, "A")
    edit.connect_material_expressions(image, "A", opacity, "B")
    if not edit.connect_material_property(opacity, "", prop.MP_OPACITY):
        raise RuntimeError("Unable to blend the hair roots into the forehead")
    edit.recompile_material(mat)
    unreal.EditorAssetLibrary.save_loaded_asset(mat, only_if_is_dirty=False)
    return mat
