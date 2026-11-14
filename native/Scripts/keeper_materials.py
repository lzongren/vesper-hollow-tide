"""Assign authored RGB, cutout and relief to the keeper's skinned material slots."""

import unreal


def surface(root, name, color, metal, rough, *, normal=None, cutout=False):
    library = unreal.EditorAssetLibrary
    edit = unreal.MaterialEditingLibrary
    prop = unreal.MaterialProperty
    dest = root + "/Finish"
    path = dest + "/" + name
    if library.does_asset_exist(path):
        mat = library.load_asset(path)
        if not mat.get_editor_property("used_with_skeletal_mesh"):
            mat.set_editor_property("used_with_skeletal_mesh", True)
            edit.recompile_material(mat)
            library.save_loaded_asset(mat, only_if_is_dirty=False)
        return mat
    mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        name, dest, unreal.Material, unreal.MaterialFactoryNew()
    )
    mat.set_editor_property("two_sided", True)
    mat.set_editor_property("used_with_skeletal_mesh", True)
    if cutout:
        mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
        mat.set_editor_property("opacity_mask_clip_value", 0.52)

    def sample(texture, y, kind):
        tex = library.load_asset(root + "/Textures/" + texture)
        if tex is None:
            raise RuntimeError("Missing keeper texture " + texture)
        node = edit.create_material_expression(
            mat, unreal.MaterialExpressionTextureSample, -300, y
        )
        node.set_editor_property("texture", tex)
        node.set_editor_property("sampler_type", kind)
        return node

    def connect(node, pin, channel):
        if not edit.connect_material_property(node, pin, channel):
            raise RuntimeError("Could not connect " + name + " " + str(channel))

    base = sample(color, 0, unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
    connect(base, "RGB", prop.MP_BASE_COLOR)
    if cutout:
        connect(base, "A", prop.MP_OPACITY_MASK)
    if normal:
        relief = sample(normal, 240, unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
        connect(relief, "RGB", prop.MP_NORMAL)
    for y, value, channel in (
        (480, metal, prop.MP_METALLIC),
        (560, rough, prop.MP_ROUGHNESS),
    ):
        node = edit.create_material_expression(
            mat, unreal.MaterialExpressionConstant, -300, y
        )
        node.set_editor_property("r", value)
        connect(node, "", channel)
    edit.recompile_material(mat)
    if not library.save_loaded_asset(mat, only_if_is_dirty=False):
        raise RuntimeError("Could not save " + name)
    return mat


def finish(mesh):
    root = mesh.get_path_name().split("/SkeletalMeshes/")[0]
    library = unreal.EditorAssetLibrary
    face = surface(
        root,
        "HammeredFace",
        "Repousse_ritual_facebaseColorTexture",
        0.52,
        0.49,
        cutout=True,
    )
    bronze = surface(
        root, "OldBronze", "LeftPlatePatina", 0.65, 0.56, normal="LeftPlateHammer"
    )
    silk = surface(
        root,
        "DragonSilk",
        "Oxide_red_dragon_damaskbaseColorTexture",
        0.08,
        0.72,
        normal="Oxide_red_dragon_damasknormalTexture",
    )
    slots = list(mesh.materials)
    mapping = {"Repousse_ritual_face": face, "Oxide_red_dragon_damask": silk}
    for side in ("LeftPlate", "RightPlate"):
        for index in (0, 3):
            mapping[f"{side}_{index}"] = bronze
    for slot in slots:
        name = str(slot.material_slot_name)
        if name in mapping:
            slot.material_interface = mapping.pop(name)
    if mapping:
        raise RuntimeError("Missing keeper slots: " + str(list(mapping)))
    mesh.set_editor_property("materials", slots)
    library.save_loaded_asset(mesh, only_if_is_dirty=False)
