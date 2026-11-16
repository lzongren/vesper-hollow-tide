"""A waterline and mineral finish shared by the quarried stone on the garden bridge."""

import unreal


def stone_finishes(root):
    lib = unreal.EditorAssetLibrary
    edit = unreal.MaterialEditingLibrary
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    path = root + "/Shaders"
    name = "CoursedPondGranite"
    mat = (
        lib.load_asset(path + "/" + name)
        if lib.does_asset_exist(path + "/" + name)
        else None
    )
    if not mat:
        mat = tools.create_asset(
            name, path, unreal.Material, unreal.MaterialFactoryNew()
        )

        def node(cls, x, y):
            return edit.create_material_expression(mat, cls, x, y)

        def wire(src, channel, dst, pin):
            if not edit.connect_material_expressions(src, channel, dst, pin):
                raise RuntimeError("Cannot wire stone input " + pin)

        def prop(src, channel, key):
            if not edit.connect_material_property(src, channel, key):
                raise RuntimeError("Cannot wire stone output " + str(key))

        def texture(key, y, sampler):
            tex = lib.load_asset(root + "/LotusBridge/Textures/rock-" + key)
            if not tex:
                raise RuntimeError("Missing bridge texture " + key)
            sample = node(unreal.MaterialExpressionTextureSample, -680, y)
            sample.set_editor_property("texture", tex)
            sample.set_editor_property("sampler_type", sampler)
            return sample

        stone = texture("color", -230, unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
        relief = texture("normal", 270, unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
        pigment = node(unreal.MaterialExpressionVectorParameter, -680, -50)
        pigment.set_editor_property("parameter_name", "StoneTint")
        pigment.set_editor_property(
            "default_value", unreal.LinearColor(0.55, 0.60, 0.56, 1)
        )
        finish = node(unreal.MaterialExpressionCustom, -310, -110)
        finish.set_editor_property(
            "description", "Mineral grain and damp masonry at the pond level"
        )
        finish.set_editor_property(
            "output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT4
        )
        pins = []
        for key in ("Grain", "Tint", "World", "Courses"):
            pin = unreal.CustomInput()
            pin.set_editor_property("input_name", key)
            pins.append(pin)
        finish.set_editor_property("inputs", pins)
        finish.set_editor_property(
            "code",
            """
            float lum = dot(Grain,float3(.30,.59,.11));
            float band = 8*sin(World.x*.021+World.y*.014)+5*sin(World.y*.05)-92;
            float wet = 1-smoothstep(band-8,band+40,World.z);
            float salt = exp(-abs(World.z-band-32.)/6.) * (.30+lum);
            float3 dry = Tint * (.24 + 1.08*lum) + .06*(Grain-lum);
            float3 color = dry*lerp(float3(1,1,1),float3(.26,.36,.30),wet) + .024*salt;
            // World Y follows the span. Only the two vertical spandrels use
            // coursed masonry; the radial arch stones keep their cut faces.
            float py = World.z + .46*sin(.042*World.y) + .67*sin(.021*World.y+2.);
            float row = floor(py/35.);
            float w = 79. + 15.*sin(1.72*row);
            float px = World.y + 34.*row + 21.*sin(2.7*row) + .47*sin(.11*py);
            float2 cell = frac(float2(px/w,py/35.));
            float2 edge = min(cell,1.-cell)*float2(w,35.);
            float distanceToJoint = min(edge.x,edge.y);
            float seam = 1.-smoothstep(.45,1.9,distanceToJoint+1.2*(lum-.35));
            float patina = frac(sin(dot(float2(floor(px/w),row),float2(4.31,8.09)))*4375.41);
            float lip = (1.-smoothstep(.6,2.6,cell.y*35.))*smoothstep(.25,1.30,distanceToJoint);
            color *= lerp(1.,(.86+.21*patina)*(1.-.53*seam)+.12*lip,Courses);
            return float4(color,lerp(.76,.34,wet));
        """,
        )
        joints = node(unreal.MaterialExpressionScalarParameter, -680, 230)
        joints.set_editor_property("parameter_name", "Courses")
        joints.set_editor_property("default_value", 0.0)
        wire(joints, "", finish, "Courses")
        wire(stone, "RGB", finish, "Grain")
        wire(pigment, "", finish, "Tint")
        wire(
            node(unreal.MaterialExpressionWorldPosition, -680, 120), "", finish, "World"
        )
        for channels, result in (
            ("rgb", unreal.MaterialProperty.MP_BASE_COLOR),
            ("a", unreal.MaterialProperty.MP_ROUGHNESS),
        ):
            mask = node(
                unreal.MaterialExpressionComponentMask,
                0,
                0 if channels == "rgb" else 145,
            )
            for letter in "rgba":
                mask.set_editor_property(letter, letter in channels)
            wire(finish, "", mask, "")
            prop(mask, "", result)
        prop(relief, "RGB", unreal.MaterialProperty.MP_NORMAL)
        edit.set_base_material_usage(mat, unreal.MaterialUsage.MATUSAGE_NANITE, True)
        edit.recompile_material(mat)
        if not lib.save_loaded_asset(mat, only_if_is_dirty=False):
            raise RuntimeError("Could not save pond granite")
    result = {}
    for slot, rgb in {
        "PaleWeatheredStone": (0.44, 0.50, 0.48),
        "CloudGreyArch": (0.64, 0.68, 0.60),
        "BasaltSpringer": (0.20, 0.25, 0.24),
        "PittedKerb": (0.34, 0.39, 0.36),
        "SawnQuay": (0.51, 0.54, 0.49),
        "ShallowBed": (0.23, 0.29, 0.21),
    }.items():
        name = "Dressed" + slot
        inst = (
            lib.load_asset(path + "/" + name)
            if lib.does_asset_exist(path + "/" + name)
            else None
        )
        if not inst:
            inst = tools.create_asset(
                name,
                path,
                unreal.MaterialInstanceConstant,
                unreal.MaterialInstanceConstantFactoryNew(),
            )
            edit.set_material_instance_parent(inst, mat)
            edit.set_material_instance_vector_parameter_value(
                inst, "StoneTint", unreal.LinearColor(*rgb, 1)
            )
            edit.set_material_instance_scalar_parameter_value(
                inst, "Courses", 1.0 if slot == "PaleWeatheredStone" else 0.0
            )
            edit.update_material_instance(inst)
            if not lib.save_loaded_asset(inst, only_if_is_dirty=False):
                raise RuntimeError("Could not save stone finish " + slot)
        result[slot] = inst
    return result
