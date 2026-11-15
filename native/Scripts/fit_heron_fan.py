"""Fit the seven existing cast actors without replacing the boss or navigation."""

from pathlib import Path
import json
import sys
import unreal

project = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
sys.path.insert(0, str(project / "Scripts"))
from route_material_usage import prepare
from heron_flight_sound import release
from heron_wake_material import slipstream

lib = unreal.EditorAssetLibrary
root = "/Game/Vesper/Duel/HeronFlightArt"
asset = root + "/HeronSilkFlight/StaticMeshes/HeronSilkFlight"
if not lib.does_asset_exist(asset):
    task = unreal.AssetImportTask()
    task.filename = str(project / "Art/HeronSilkFlight.glb")
    task.destination_path = root
    task.automated = task.save = True
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
if not lib.does_asset_exist(root + "/VaneRelease"):
    wav = project / "Saved/VaneRelease.wav"
    release(wav)
    task = unreal.AssetImportTask()
    task.filename = str(wav)
    task.destination_path = root
    task.automated = task.save = True
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
if not lib.load_asset(root + "/VaneRelease"):
    raise RuntimeError("Missing feather release cue")
mesh = lib.load_asset(asset)
if not mesh:
    raise RuntimeError("Could not import the flight feather")
prepare([mesh], root + "/Finish")
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
if not levels.load_level("/Game/Vesper/Maps/MountainPilgrimage"):
    raise RuntimeError("Missing mountain route")
flock = [a for a in actors.get_all_level_actors() if a.actor_has_tag("HeronQuill")]
if len(flock) != 7:
    raise RuntimeError("Expected seven cast actors")
wake_slot = next(
    i
    for i, m in enumerate(mesh.static_materials)
    if str(m.material_slot_name) == "VaneSlipstream"
)
wake = slipstream(root + "/Finish")
for quill in flock:
    comp = quill.static_mesh_component
    comp.set_static_mesh(mesh)
    comp.set_editor_property("override_materials", [])
    comp.set_material(wake_slot, wake)
    comp.set_editor_property("cast_shadow", True)
    quill.set_actor_enable_collision(False)
    quill.set_actor_hidden_in_game(True)
if not levels.save_current_level():
    raise RuntimeError("Could not save the fitted fan")
(project / "Saved/HeronFan.json").write_text(
    json.dumps(dict(revision=3, mesh=asset, count=len(flock)))
)
unreal.log("VESPER_HERON_FAN_READY")
