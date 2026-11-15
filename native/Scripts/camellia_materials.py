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
    mat = surface(root, "CourtyardCornea", "WetIris", 0, 0.18, specular=0.52)
    edit = unreal.MaterialEditingLibrary
    prop = unreal.MaterialProperty
    if edit.get_material_property_input_node(mat, prop.MP_EMISSIVE_COLOR):
        return mat

    def node(cls, x, y):
        return edit.create_material_expression(mat, cls, x, y)

    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_CLEAR_COAT)
    # The clear-coat model defaults to a full coat at 0.1 roughness.
    # Reproject the iris atlas on the front ellipsoid. Leave the corneal
    # normals and the reflection in place as the pigment moves under them.
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
    # Approximate two soft reflections from the open side of the gallery.
    # Evaluate on the curved cornea, independently of the moving pigment.
    reflection = node(unreal.MaterialExpressionReflectionVectorWS, -690, 620)
    view = node(unreal.MaterialExpressionCameraVectorWS, -690, 750)
    glint = node(unreal.MaterialExpressionCustom, -420, 620)
    glint.set_editor_property("description", "Soft corneal catchlights")
    glint.set_editor_property(
        "output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT3
    )
    pins = []
    for key in ("Reflection", "View", "EyeUV"):
        pin = unreal.CustomInput()
        pin.set_editor_property("input_name", key)
        pins.append(pin)
    glint.set_editor_property("inputs", pins)
    glint.set_editor_property(
        "code",
        """
        float3 v = normalize(View);
        float3 axis = abs(v.z) < .98 ? float3(0,0,1) : float3(0,1,0);
        float3 right = normalize(cross(axis,v));
        float3 up = cross(v,right);
        float3 r = normalize(Reflection);
        float2 uv = float2(dot(r,right),dot(r,up));
        float2 main = (uv-float2(-.22,.18))/float2(.108,.069);
        float2 edge = (uv-float2(.175,-.085))/float2(.042,.032);
        float lit = .86*exp(-1.7*dot(main,main)) + .25*exp(-1.5*dot(edge,edge));
        // The small softbox reflection sits on the cornea, independent
        // of the iris texture as the gaze tracks an opponent.
        float2 bead=(EyeUV-float2(.457,.440))/float2(.013,.017);
        float2 spill=(EyeUV-float2(.485,.425))/float2(.006,.008);
        float front=smoothstep(.62,.94,dot(r,v));
        float catchlight=.85*exp(-dot(bead,bead)) + .27*exp(-dot(spill,spill));
        return float3(.96,.97,1.0)*(lit*front+catchlight);
    """,
    )
    for source, pin in ((reflection, "Reflection"), (view, "View"), (uv, "EyeUV")):
        if not edit.connect_material_expressions(source, "", glint, pin):
            raise RuntimeError("Could not connect corneal reflection input " + pin)
    if not edit.connect_material_property(glint, "", prop.MP_EMISSIVE_COLOR):
        raise RuntimeError("Could not attach corneal reflection")
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
