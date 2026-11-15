"""Single-layer pond water with world-scaled moving wind ripples."""

import unreal


def water_material(root):
    lib = unreal.EditorAssetLibrary
    edit = unreal.MaterialEditingLibrary
    name = "WillowPondWater"
    if lib.does_asset_exist(root + "/" + name):
        return lib.load_asset(root + "/" + name)
    mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        name, root, unreal.Material, unreal.MaterialFactoryNew()
    )
    mat.set_editor_property(
        "shading_model", unreal.MaterialShadingModel.MSM_SINGLE_LAYER_WATER
    )

    def node(cls, x, y):
        return edit.create_material_expression(mat, cls, x, y)

    def scalar(v, x, y):
        n = node(unreal.MaterialExpressionConstant, x, y)
        n.set_editor_property("r", v)
        return n

    def color(v, x, y):
        n = node(unreal.MaterialExpressionConstant3Vector, x, y)
        n.set_editor_property("constant", unreal.LinearColor(*v, 1))
        return n

    def wire(src, target, pin):
        if not edit.connect_material_expressions(src, "", target, pin):
            raise RuntimeError("Pond material input " + pin)

    output = node(unreal.MaterialExpressionSingleLayerWaterMaterialOutput, 200, 360)
    names = edit.get_material_expression_input_names(output)
    if len(names) != 4:
        raise RuntimeError("Unexpected water inputs " + str(names))
    for value, pin in zip(
        (
            color((0.0017, 0.0026, 0.0025), -130, 320),
            color((0.015, 0.009, 0.011), -130, 460),
            scalar(0.19, -130, 570),
            scalar(0.91, -130, 660),
        ),
        names,
    ):
        wire(value, output, pin)
    p = unreal.MaterialProperty
    ripple = node(unreal.MaterialExpressionCustom, -210, -300)
    ripple.set_editor_property("description", "Crossing breezes on the lotus pond")
    ripple.set_editor_property(
        "output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT3
    )
    pins = []
    for key in ("World", "Clock"):
        pin = unreal.CustomInput()
        pin.set_editor_property("input_name", key)
        pins.append(pin)
    ripple.set_editor_property("inputs", pins)
    ripple.set_editor_property(
        "code",
        """
        float2 uv = World.xy * .01;
        float slow = sin(dot(uv,float2(.44,.25)) - .59*Clock);
        float a = dot(uv,float2(6.3,2.4)) - 1.7*Clock + 1.2*slow + .7*sin(.71*uv.y+.16*Clock);
        float b = dot(uv,float2(-3.1,11.8)) - 2.7*Clock;
        float c = dot(uv,float2(16.7,7.1)) - 4.3*Clock + 1.2*sin(.42*uv.y);
        float2 tilt = (.028+.010*sin(.8*uv.y+.3*Clock))*cos(a)*float2(.93,.36) + .021*cos(b)*float2(-.25,.97)
                    + (.010+.007*slow)*cos(c)*float2(.92,.39);
        return normalize(float3(tilt,1));
    """,
    )
    wire(node(unreal.MaterialExpressionWorldPosition, -580, -300), ripple, "World")
    wire(node(unreal.MaterialExpressionTime, -580, -170), ripple, "Clock")
    for src, prop in (
        (ripple, p.MP_NORMAL),
        (color((0.012, 0.028, 0.021), -210, 30), p.MP_BASE_COLOR),
        (scalar(0.12, -210, 100), p.MP_ROUGHNESS),
        (scalar(0.48, -210, 160), p.MP_SPECULAR),
        (scalar(0.13, -210, 225), p.MP_OPACITY),
    ):
        if not edit.connect_material_property(src, "", prop):
            raise RuntimeError("Pond material property " + str(prop))
    edit.recompile_material(mat)
    if not lib.save_loaded_asset(mat, only_if_is_dirty=False):
        raise RuntimeError("Could not save water material")
    return mat
