"""Blend the portrait into plain skin beyond the visible facial landmarks."""

from pathlib import Path

import unreal
from keeper_materials import surface


def complexion(root):
    lib = unreal.EditorAssetLibrary
    edit = unreal.MaterialEditingLibrary
    mat = surface(root, "CamelliaComplexion", "WayfarerSkin", 0, 0.52, specular=0.29)
    if not mat.get_editor_property("used_with_morph_targets"):
        mat.set_editor_property("used_with_morph_targets", True)
        edit.recompile_material(mat)
        lib.save_loaded_asset(mat, only_if_is_dirty=False)
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
    # A light rouge follows the face UVs so it stays on the cheeks and lip
    # vermilion while the actor turns in and out of the eaves.
    paint = node(unreal.MaterialExpressionCustom, -290, -200)
    paint.set_editor_property("description", "Haitang cheek and lip rouge")
    paint.set_editor_property(
        "output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT3
    )
    inputs = []
    for key in ("Face", "UV"):
        pin = unreal.CustomInput()
        pin.set_editor_property("input_name", key)
        inputs.append(pin)
    paint.set_editor_property("inputs", inputs)
    paint.set_editor_property(
        "code",
        """
        float2 ch = (float2(abs(UV.x-.504), UV.y) - float2(.137,.545)) / float2(.071,.051);
        float2 lp = (UV-float2(.504,.689)) / float2(.082,.027);
        float rouge = exp(-dot(ch,ch)) * .045;
        float lip = exp(-dot(lp,lp)) * smoothstep(.026,.082,Face.r-Face.g);
        return Face * lerp(float3(1,1,1),float3(1.18,.59,.71),rouge)
                    * lerp(float3(1,1,1),float3(1.08,.63,.77),lip*.18);
    """,
    )
    wire(projected, "RGB", paint, "Face")
    wire(node(unreal.MaterialExpressionTextureCoordinate, -720, -200), "", paint, "UV")
    wire(paint, "", blend, "B")
    wire(mask, "", blend, "Alpha")
    if not edit.connect_material_property(blend, "", color):
        raise RuntimeError("Could not install facial colour blend")
    # Give the skin a restrained warm transmission on backlit cheeks and ears.
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_SUBSURFACE)
    tint = node(unreal.MaterialExpressionMultiply, 40, 200)
    warm = node(unreal.MaterialExpressionConstant3Vector, -180, 300)
    warm.set_editor_property("constant", unreal.LinearColor(0.34, 0.17, 0.13, 1))
    wire(blend, "", tint, "A")
    wire(warm, "", tint, "B")
    density = node(unreal.MaterialExpressionConstant, 40, 370)
    density.set_editor_property("r", 0.84)
    if not edit.connect_material_property(
        tint, "", unreal.MaterialProperty.MP_SUBSURFACE_COLOR
    ):
        raise RuntimeError("Could not install skin transmission")
    if not edit.connect_material_property(
        density, "", unreal.MaterialProperty.MP_OPACITY
    ):
        raise RuntimeError("Could not install skin density")
    # UV1 fades the registered portrait off at the temples and the neck.
    # Apply the same mask to relief and oiliness to avoid stretching pores there.
    directory = Path(
        unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
    )
    finish = root + "/Finish"
    neutral_normal = node(unreal.MaterialExpressionConstant3Vector, -390, 660)
    neutral_normal.set_editor_property("constant", unreal.LinearColor(0, 0, 1, 1))
    original_rough = edit.get_material_property_input_node(
        mat, unreal.MaterialProperty.MP_ROUGHNESS
    )
    for name, compression, sampler, neutral, channel, output, row in (
        (
            "CamelliaSkinNormal",
            unreal.TextureCompressionSettings.TC_NORMALMAP,
            unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL,
            neutral_normal,
            "RGB",
            unreal.MaterialProperty.MP_NORMAL,
            620,
        ),
        (
            "CamelliaSkinRough",
            unreal.TextureCompressionSettings.TC_MASKS,
            unreal.MaterialSamplerType.SAMPLERTYPE_MASKS,
            original_rough,
            "R",
            unreal.MaterialProperty.MP_ROUGHNESS,
            850,
        ),
    ):
        path = finish + "/" + name
        if not lib.does_asset_exist(path):
            task = unreal.AssetImportTask()
            task.filename = str(directory / "Art" / "Wayfarer" / (name + ".png"))
            task.destination_path = finish
            task.automated = task.save = True
            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        texture = lib.load_asset(path)
        texture.set_editor_property("compression_settings", compression)
        texture.set_editor_property("srgb", False)
        lib.save_loaded_asset(texture, only_if_is_dirty=False)
        sample = node(unreal.MaterialExpressionTextureSample, -590, row)
        sample.set_editor_property("texture", texture)
        sample.set_editor_property("sampler_type", sampler)
        mix = node(unreal.MaterialExpressionLinearInterpolate, -140, row)
        wire(neutral, "", mix, "A")
        wire(sample, channel, mix, "B")
        wire(mask, "", mix, "Alpha")
        if not edit.connect_material_property(mix, "", output):
            raise RuntimeError("Could not attach " + name)
    edit.recompile_material(mat)
    if not lib.save_loaded_asset(mat, only_if_is_dirty=False):
        raise RuntimeError("Could not save the skin material")
    return mat
