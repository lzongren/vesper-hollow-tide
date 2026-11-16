"""Create the UV-registered skin, eyes and moist oral surfaces in Unreal."""

import unreal
from keeper_materials import surface


def digital_finish(root, slot, cache):
    lib, edit = unreal.EditorAssetLibrary, unreal.MaterialEditingLibrary
    prop = unreal.MaterialProperty
    rough, spec = {
        "WayfarerSkin": (0.49, 0.27),
        "NecklineSkin": (0.56, 0.25),
        "WetIris": (0.22, 0.38),
        "LashFringe": (0.66, 0.20),
        "PorcelainTeeth": (0.47, 0.22),
    }[slot]
    mat = surface(
        root,
        slot + "DigitalSurface",
        slot,
        0,
        rough,
        specular=spec,
        cutout=slot == "LashFringe",
    )
    mat.set_editor_property("used_with_morph_targets", True)
    if slot in ("WayfarerSkin", "NecklineSkin"):
        dest = root + "/Finish"
        profile = (
            lib.load_asset(dest + "/HaitangSkinProfile")
            if lib.does_asset_exist(dest + "/HaitangSkinProfile")
            else unreal.AssetToolsHelpers.get_asset_tools().create_asset(
                "HaitangSkinProfile",
                dest,
                unreal.SubsurfaceProfile,
                unreal.SubsurfaceProfileFactory(),
            )
        )
        if not profile:
            raise RuntimeError("Cannot create skin diffusion profile")
        settings = profile.get_editor_property("settings")
        settings.set_editor_property(
            "surface_albedo", unreal.LinearColor(0.65, 0.40, 0.34, 1)
        )
        settings.set_editor_property(
            "mean_free_path_color", unreal.LinearColor(1, 0.43, 0.31, 1)
        )
        settings.set_editor_property("mean_free_path_distance", 0.72)
        settings.set_editor_property(
            "transmission_tint_color", unreal.LinearColor(0.40, 0.33, 0.32, 1)
        )
        profile.set_editor_property("settings", settings)
        lib.save_loaded_asset(profile, only_if_is_dirty=False)
        mat.set_editor_property(
            "shading_model", unreal.MaterialShadingModel.MSM_SUBSURFACE_PROFILE
        )
        mat.set_editor_property("subsurface_profile", profile)
        base = edit.get_material_property_input_node(mat, prop.MP_BASE_COLOR)
        if (
            isinstance(base, unreal.MaterialExpressionTextureSample)
            and slot == "NecklineSkin"
        ):
            tint = dest + "/HaitangCollar"
            if not lib.does_asset_exist(tint):
                task = unreal.AssetImportTask()
                task.filename = str(cache / "HaitangCollar.jpg")
                task.destination_path = dest
                task.automated = task.save = True
                unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            collar = lib.load_asset(tint)
            if not collar:
                raise RuntimeError("Cannot load the collar's skin pigment")
            base.set_editor_property("texture", collar)
        if isinstance(base, unreal.MaterialExpressionTextureSample):
            tint = edit.create_material_expression(
                mat, unreal.MaterialExpressionVertexColor, -360, -180
            )
            mix = edit.create_material_expression(
                mat, unreal.MaterialExpressionMultiply, -90, -90
            )
            if not (
                edit.connect_material_expressions(base, "RGB", mix, "A")
                and edit.connect_material_expressions(tint, "", mix, "B")
                and edit.connect_material_property(mix, "", prop.MP_BASE_COLOR)
            ):
                raise RuntimeError("Cannot connect anatomical skin pigment")
            if slot == "WayfarerSkin" and not edit.connect_material_property(
                tint, "A", prop.MP_AMBIENT_OCCLUSION
            ):
                raise RuntimeError("Cannot connect pinna surface visibility")
        if slot == "WayfarerSkin" and not edit.get_material_property_input_node(
            mat, prop.MP_NORMAL
        ):
            for idx, (name, compression, sampler, out, pin) in enumerate(
                (
                    (
                        "HaitangNormal",
                        unreal.TextureCompressionSettings.TC_NORMALMAP,
                        unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL,
                        prop.MP_NORMAL,
                        "RGB",
                    ),
                    (
                        "HaitangRough",
                        unreal.TextureCompressionSettings.TC_MASKS,
                        unreal.MaterialSamplerType.SAMPLERTYPE_MASKS,
                        prop.MP_ROUGHNESS,
                        "R",
                    ),
                )
            ):
                task = unreal.AssetImportTask()
                task.filename = str(cache / (name + ".png"))
                task.destination_path = dest
                task.automated = task.save = True
                unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
                tex = lib.load_asset(dest + "/" + name)
                tex.set_editor_property("compression_settings", compression)
                tex.set_editor_property("srgb", False)
                lib.save_loaded_asset(tex, only_if_is_dirty=False)
                sample = edit.create_material_expression(
                    mat, unreal.MaterialExpressionTextureSample, -380, 750 + idx * 190
                )
                sample.set_editor_property("texture", tex)
                sample.set_editor_property("sampler_type", sampler)
                if not edit.connect_material_property(sample, pin, out):
                    raise RuntimeError(name)
    if slot == "LashFringe":
        mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
        mat.set_editor_property(
            "translucency_lighting_mode",
            unreal.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING,
        )
        tex = edit.get_material_property_input_node(mat, prop.MP_BASE_COLOR)
        if not edit.connect_material_property(tex, "A", prop.MP_OPACITY):
            raise RuntimeError("Cannot wire lash transparency")
    edit.recompile_material(mat)
    if not lib.save_loaded_asset(mat, only_if_is_dirty=False):
        raise RuntimeError(slot)
    return mat
