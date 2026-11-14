"""Build the playable clothed pilgrim from local template bones and Vesper art."""

import json
import runpy
from pathlib import Path
import unreal

project = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
lib = unreal.EditorAssetLibrary
base = "/Game/ThirdPerson/Blueprints/"
root = "/Game/Vesper/Pilgrim/"
template = lib.load_asset(base + "BP_ThirdPersonCharacter")
source = unreal.get_default_object(template.generated_class()).mesh.skeletal_mesh_asset
staging = project / "Saved" / "PilgrimFitting"
staging.mkdir(parents=True, exist_ok=True)
reference = staging / "LocalRig.glb"
options = unreal.GLTFExportOptions()
if "texture_image_format" in dir(options):
    options.texture_image_format = unreal.GLTFTextureImageFormat.NONE
task = unreal.AssetExportTask()
task.object = source
task.filename = str(reference)
task.options = options
task.automated = task.replace_identical = True
task.prompt = False
if not unreal.Exporter.run_asset_export_task(task):
    raise RuntimeError("Unable to export the local reference skeleton")
out = staging / "Wayfarer.glb"
runpy.run_path(str(project / "Scripts" / "bind_pilgrim.py"))["build"](
    reference,
    project / "SourceAssets" / "pilgrim.glb",
    project / "Art",
    project / "SourceAssets",
    out,
)
folder = root + "Outfit"
if not any(str(lib.find_asset_data(p).asset_class_path.asset_name) == "SkeletalMesh" for p in lib.list_assets(folder)):
    imp = unreal.AssetImportTask()
    imp.filename = str(out)
    imp.destination_path = folder
    imp.replace_existing = imp.automated = imp.save = True
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([imp])
skins = [
    p
    for p in lib.list_assets(folder)
    if str(lib.find_asset_data(p).asset_class_path.asset_name) == "SkeletalMesh"
]
if len(skins) != 1:
    raise RuntimeError("Expected one outfit mesh, got " + str(skins))
skin = lib.load_asset(skins[0])
# Both meshes were built from the same reference transforms. Declare the outfit's
# skeleton compatible with the installed locomotion animations on the target asset.
fitted_skeleton = skin.skeleton
compatible = list(fitted_skeleton.get_editor_property("compatible_skeletons"))
if source.skeleton not in compatible:
    compatible.append(source.skeleton)
    fitted_skeleton.set_editor_property("compatible_skeletons", compatible)
    lib.save_loaded_asset(fitted_skeleton, only_if_is_dirty=False)


def duplicate(name, dest):
    path = root + dest
    if lib.does_asset_exist(path):
        return lib.load_asset(path)
    return lib.duplicate_asset(base + name, path)


pawn = duplicate("BP_ThirdPersonCharacter", "BP_Wayfarer")
subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
library = unreal.SubobjectDataBlueprintFunctionLibrary
components = []
for handle in subsystem.k2_gather_subobject_data_for_blueprint(pawn):
    data = library.get_data(handle)
    obj = library.get_object_for_blueprint(data, pawn)
    if isinstance(obj, unreal.SkeletalMeshComponent):
        components.append(obj)
if len(components) != 1:
    raise RuntimeError(
        "Cannot identify the character mesh component: " + str(components)
    )
components[0].set_skeletal_mesh_asset(skin)
unreal.BlueprintEditorLibrary.compile_blueprint(pawn)
cdo = unreal.get_default_object(pawn.generated_class())
cdo.mesh.set_skeletal_mesh_asset(skin)
# Ease the first stride and stop over several locomotion frames.
movement = cdo.character_movement
movement.set_editor_property("max_acceleration", 1600.0)
movement.set_editor_property("braking_deceleration_walking", 1450.0)
movement.set_editor_property("use_separate_braking_friction", True)
movement.set_editor_property("braking_friction", 1.0)
movement.set_editor_property("rotation_rate", unreal.Rotator(0.0, 0.0, 440.0))
if not lib.save_loaded_asset(pawn, only_if_is_dirty=False):
    raise RuntimeError("Failed to save pilgrim character")
mode = duplicate("BP_ThirdPersonGameMode", "BP_PilgrimageMode")
unreal.BlueprintEditorLibrary.compile_blueprint(mode)
unreal.get_default_object(mode.generated_class()).set_editor_property(
    "default_pawn_class", pawn.generated_class()
)
if not lib.save_loaded_asset(mode, only_if_is_dirty=False):
    raise RuntimeError("Failed to save pilgrim game mode")
report = {
    "locomotion_revision": 2,
    "mesh": skin.get_path_name(),
    "pawn": pawn.generated_class().get_name(),
    "game_mode": mode.generated_class().get_name(),
    "material_slots": len(skin.materials),
    "animation_class": str(cdo.mesh.anim_class.get_name()),
    "skeleton": skin.skeleton.get_path_name(),
}
(project / "Saved" / "FittedPilgrim.json").write_text(json.dumps(report))
unreal.log("VESPER_PILGRIM_FITTED " + str(report))
