"""Seat the pair of bronze guardian lions at the approach to the first duel."""

import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assets = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
edit = unreal.MaterialEditingLibrary
root = "/Game/Vesper/BellCourtLions"
if not levels.load_level("/Game/Vesper/Maps/MountainPilgrimage"):
    raise RuntimeError("Could not open the mountain route")


def load_parts():
    paths = assets.list_assets(root) if assets.does_directory_exist(root) else []
    parts = {}
    for path in paths:
        if (
            str(assets.find_asset_data(path).asset_class_path.asset_name)
            == "StaticMesh"
        ):
            mesh = assets.load_asset(path)
            parts[mesh.get_name()] = mesh
    return parts


parts = load_parts()
if set(parts) != {"CastLion", "CarvedFoot"}:
    task = unreal.AssetImportTask()
    task.filename = str(project / "Art" / "BellCourt" / "GateLion.glb")
    task.destination_path = root
    task.automated = task.replace_existing = task.save = True
    tools.import_asset_tasks([task])
    parts = load_parts()
if set(parts) != {"CastLion", "CarvedFoot"}:
    raise RuntimeError("Incomplete guardian casting " + str(parts))


def import_patina():
    name = "CastingBloom"
    if not assets.does_asset_exist(root + "/" + name):
        task = unreal.AssetImportTask()
        task.filename = str(project / "Art" / "BellCourt" / (name + ".jpg"))
        task.destination_path = root
        task.automated = task.save = True
        tools.import_asset_tasks([task])
    if not assets.load_asset(root + "/" + name):
        raise RuntimeError("Missing casting patina texture")


import_patina()


def finish(name, stone):
    path = root + "/" + name
    mat = (
        assets.load_asset(path)
        if assets.does_asset_exist(path)
        else tools.create_asset(
            name, root, unreal.Material, unreal.MaterialFactoryNew()
        )
    )
    edit.delete_all_material_expressions(mat)

    def node(cls, x, y):
        return edit.create_material_expression(mat, cls, x, y)

    def wire(src, out, dst, pin):
        if not edit.connect_material_expressions(src, out, dst, pin):
            raise RuntimeError("Could not connect " + str(pin))

    def output(src, pin, prop):
        if not edit.connect_material_property(src, pin, prop):
            raise RuntimeError("Could not set " + str(prop))

    def rgb(v, x, y):
        expr = node(unreal.MaterialExpressionConstant3Vector, x, y)
        expr.set_editor_property("constant", unreal.LinearColor(*v, 1))
        return expr

    def project_texture(function, texture, x, y):
        call = node(unreal.MaterialExpressionMaterialFunctionCall, x, y)
        call.set_material_function(
            unreal.load_asset(
                "/Engine/Functions/Engine_MaterialFunctions01/Texturing/" + function
            )
        )
        tex = node(unreal.MaterialExpressionTextureObject, x - 300, y)
        asset = assets.load_asset(
            (root + "/" if texture == "CastingBloom" else "/Game/Vesper/Understory/")
            + texture
        )
        if asset is None:
            raise RuntimeError("Missing surface scan " + texture)
        tex.set_editor_property("texture", asset)
        if texture.endswith("Normal"):
            tex.set_editor_property(
                "sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL
            )
        names = edit.get_material_expression_input_names(call)
        pin = next(
            str(n) for n in names if str(n) in ("TextureObject", "Texture", "Normal")
        )
        wire(tex, "", call, pin)
        size = 95 if stone else (86 if texture == "CastingBloom" else 27)
        wire(rgb((size,) * 3, x - 300, y + 140), "", call, "TextureSize")
        return call

    prop = unreal.MaterialProperty
    color = node(unreal.MaterialExpressionVertexColor, -500, 0)
    if stone:
        scan = project_texture("WorldAlignedTexture", "ShaleColor", -720, -270)
        shade = node(unreal.MaterialExpressionAdd, -360, -150)
        shade.set_editor_property("const_b", 0.52)
        wire(scan, "XYZ Texture", shade, "A")
        tint = node(unreal.MaterialExpressionMultiply, -120, -80)
        wire(color, "", tint, "A")
        wire(shade, "", tint, "B")
        color = tint
    else:
        # Scanned pitting breaks up the continuous highlights on the broad breast
        # and cheeks. Relief-baked vertex colours still pick out the chased ridges.
        patina = project_texture("WorldAlignedTexture", "CastingBloom", -950, -360)
        density = node(unreal.MaterialExpressionDesaturation, -570, -310)
        wire(patina, "XYZ Texture", density, "")
        dark = node(unreal.MaterialExpressionMultiply, -260, -210)
        dark.set_editor_property("const_b", 0.62)
        wire(color, "", dark, "A")
        weather = node(unreal.MaterialExpressionLinearInterpolate, -50, -180)
        wire(dark, "", weather, "A")
        wire(rgb((0.033, 0.101, 0.076), -300, -380), "", weather, "B")
        wire(density, "", weather, "Alpha")
        color = weather
    output(color, "", prop.MP_BASE_COLOR)
    uv = node(unreal.MaterialExpressionTextureCoordinate, -530, 250)
    for channel, material_prop in (("r", prop.MP_ROUGHNESS), ("g", prop.MP_METALLIC)):
        mask = node(
            unreal.MaterialExpressionComponentMask, -265, 240 if channel == "r" else 345
        )
        mask.set_editor_property("r", channel == "r")
        mask.set_editor_property("g", channel == "g")
        wire(uv, "", mask, "")
        if not stone:
            worn = node(
                unreal.MaterialExpressionLinearInterpolate,
                -80,
                250 if channel == "r" else 350,
            )
            worn.set_editor_property("const_b", 0.92 if channel == "r" else 0.24)
            wire(mask, "", worn, "A")
            wire(density, "", worn, "Alpha")
            mask = worn
        output(mask, "", material_prop)
    relief = project_texture("WorldAlignedNormal", "ShaleNormal", -680, 510)
    blend = node(unreal.MaterialExpressionLinearInterpolate, -115, 495)
    wire(rgb((0, 0, 1), -390, 680), "", blend, "A")
    wire(relief, "XYZ Texture", blend, "B")
    blend.set_editor_property("const_alpha", 0.42 if stone else 0.19)
    output(blend, "", prop.MP_NORMAL)
    edit.set_base_material_usage(mat, unreal.MaterialUsage.MATUSAGE_NANITE, True)
    edit.recompile_material(mat)
    if not assets.save_loaded_asset(mat, only_if_is_dirty=False):
        raise RuntimeError("Cannot save " + path)
    return mat


materials = {
    "CastLion": finish("WeatheredCastBronze", False),
    "CarvedFoot": finish("GreyStoneCourse", True),
}
for mesh in parts.values():
    mesh.get_editor_property("body_setup").set_editor_property(
        "collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE
    )
    if not assets.save_loaded_asset(mesh, only_if_is_dirty=False):
        raise RuntimeError("Cannot save guardian collision")
existing = actors.get_all_level_actors()
installed = []
for side, y, angle in (("North", -337, 165), ("South", 337, 195)):
    for key, mesh in parts.items():
        label = "Bell gate " + side + " " + key
        matches = [a for a in existing if a.get_actor_label() == label]
        if len(matches) > 1:
            raise RuntimeError("Duplicate " + label)
        pos = unreal.Vector(3030, y, 4)
        rot = unreal.Rotator(yaw=angle)
        a = (
            matches[0]
            if matches
            else actors.spawn_actor_from_class(unreal.StaticMeshActor, pos, rot)
        )
        a.modify()
        a.set_actor_location_and_rotation(pos, rot, False, True)
        a.set_actor_label(label)
        comp = a.static_mesh_component
        comp.set_static_mesh(mesh)
        comp.set_material(0, materials[key])
        comp.set_collision_profile_name("BlockAll")
        a.set_actor_enable_collision(True)
        installed.append(label)
# The wind bell belongs to the hall eaves, across the court from the incoming player.
sound_path = root + "/EaveWind"
if not assets.does_asset_exist(sound_path):
    task = unreal.AssetImportTask()
    task.filename = str(project / "Art" / "BellCourt" / "EaveWind.wav")
    task.destination_path = root
    task.automated = task.save = True
    tools.import_asset_tasks([task])
wave = assets.load_asset(sound_path)
if not wave:
    raise RuntimeError("Missing bell court ambience")
wave.set_editor_property("looping", True)
if not assets.save_loaded_asset(wave, only_if_is_dirty=False):
    raise RuntimeError("Could not save looping wind bed")
label = "Bell court eave chimes"
matches = [a for a in existing if a.get_actor_label() == label]
if len(matches) > 1:
    raise RuntimeError("Duplicate bell court ambience")
position = unreal.Vector(5840, -1020, 430)
amb = (
    matches[0]
    if matches
    else actors.spawn_actor_from_class(unreal.AmbientSound, position)
)
amb.modify()
amb.set_actor_label(label)
component = amb.audio_component
component.modify()
component.set_sound(wave)
component.set_editor_property("volume_multiplier", 0.80)
component.set_editor_property("override_attenuation", True)
falloff = component.get_editor_property("attenuation_overrides")
falloff.set_editor_property("attenuation_shape_extents", unreal.Vector(1150, 0, 0))
falloff.set_editor_property("falloff_distance", 5600)
component.set_editor_property("attenuation_overrides", falloff)
if not levels.save_current_level():
    raise RuntimeError("Could not save gate lions")
(project / "Saved" / "BellGateLions.json").write_text(
    json.dumps(dict(revision=2, actors=installed, ambience=wave.get_path_name()))
)
unreal.log("VESPER_BELL_GATE_LIONS_READY")
