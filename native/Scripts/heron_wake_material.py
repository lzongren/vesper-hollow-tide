"""A translucent silver-green thread for each moving flight feather."""

import unreal


def slipstream(folder):
    lib = unreal.EditorAssetLibrary
    path = folder + "/HeronAirSilk"
    if lib.does_asset_exist(path):
        return lib.load_asset(path)
    mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "HeronAirSilk", folder, unreal.Material, unreal.MaterialFactoryNew()
    )
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property("two_sided", True)
    edit = unreal.MaterialEditingLibrary

    def node(cls, x, y):
        return edit.create_material_expression(mat, cls, x, y)

    uv = node(unreal.MaterialExpressionTextureCoordinate, -600, 30)
    flight = node(unreal.MaterialExpressionScalarParameter, -600, 170)
    flight.set_editor_property("parameter_name", "Flight")
    flight.set_editor_property("default_value", 0.0)
    mask = node(unreal.MaterialExpressionCustom, -290, 60)
    mask.set_editor_property("description", "Split air and tapered pearl core")
    mask.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT1)
    inputs = []
    for name in ("UV", "Strength"):
        input_pin = unreal.CustomInput()
        input_pin.set_editor_property("input_name", name)
        inputs.append(input_pin)
    mask.set_editor_property("inputs", inputs)
    mask.set_editor_property(
        "code",
        """
        float across = abs(2*UV.x-1);
        float ridge = exp(-19*across*across);
        float wisp = exp(-8*across*across);
        return Strength * (.75*ridge+.24*wisp) * smoothstep(0,.06,UV.y) * pow(saturate(1-UV.y),.80);
    """,
    )
    for source, pin in ((uv, "UV"), (flight, "Strength")):
        if not edit.connect_material_expressions(source, "", mask, pin):
            raise RuntimeError("Missing slipstream input " + pin)
    pearl = node(unreal.MaterialExpressionConstant3Vector, -230, -130)
    pearl.set_editor_property("constant", unreal.LinearColor(0.94, 2.1, 1.87, 1))
    for source, prop in (
        (mask, unreal.MaterialProperty.MP_OPACITY),
        (pearl, unreal.MaterialProperty.MP_EMISSIVE_COLOR),
    ):
        if not edit.connect_material_property(source, "", prop):
            raise RuntimeError("Could not compile the flight material")
    edit.recompile_material(mat)
    if not lib.save_loaded_asset(mat, only_if_is_dirty=False):
        raise RuntimeError("Could not save the flight material")
    return mat
