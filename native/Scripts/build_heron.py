"""Install the Veiled Heron and navigation in the second court."""

import json
from pathlib import Path
import sys
import unreal

project = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
sys.path.insert(0, str(project / "Scripts"))
from build_bellwarden import mesh_for, fit, actors, levels, level, lib, combat

from heron_cast import bake_quill, draw_sound
from keeper_materials import surface

skin = mesh_for("VeiledHeron", "wraith.glb", heron=True)
root = skin.get_path_name().split("/SkeletalMeshes/")[0]
cloth = surface(root, "WeddingDamask", "Kingfisher_damask", 0.12, 0.61)
vane = surface(root, "PearlVane", "Pearl_flight_feathers", 0.05, 0.67, cutout=True)
mask = surface(root, "FiredGlaze", "Porcelain0", 0.09, 0.36)
mapping = {
    "Kingfisher_damask": cloth,
    "Pearl_flight_feathers": vane,
    "Porcelain_4": mask,
    "Pilgrim_0": cloth,
}
slots = list(skin.materials)
for slot in slots:
    name = str(slot.material_slot_name)
    if name in mapping:
        slot.material_interface = mapping.pop(name)
if mapping:
    raise RuntimeError("Missing Heron slots " + str(list(mapping)))
skin.set_editor_property("materials", slots)
lib.save_loaded_asset(skin, only_if_is_dirty=False)
template = lib.load_asset(combat + "AI/BP_CombatEnemy")
skeleton = unreal.get_default_object(
    template.generated_class()
).mesh.skeletal_mesh_asset.skeleton
skin.skeleton.set_editor_property("compatible_skeletons", [skeleton])
lib.save_loaded_asset(skin.skeleton, only_if_is_dirty=False)
cls = fit(
    "AI/BP_CombatEnemy",
    "BP_VeiledHeron",
    skin,
    {
        "ai_controller_class": unreal.AIController.static_class(),
        "Max HP": 15.0,
        "Current HP": 15.0,
    },
)

quill_folder = "/Game/Vesper/Duel/Quill"
quill_file = project / "Saved" / "CastQuill.glb"
tone_file = project / "Saved" / "SilkDraw.wav"
for dest, file, key in [
    (quill_folder, quill_file, None),
    ("/Game/Vesper/Duel", tone_file, "/Game/Vesper/Duel/SilkDraw"),
]:
    if (key and lib.does_asset_exist(key)) or (
        not key and lib.does_directory_exist(dest)
    ):
        continue
    if key:
        draw_sound(file)
    else:
        bake_quill(file, project / "SourceAssets" / "heron-quill.png")
    task = unreal.AssetImportTask()
    task.filename, task.destination_path = str(file), dest
    task.save = task.automated = True
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
quill = next(
    lib.load_asset(p)
    for p in lib.list_assets(quill_folder)
    if str(lib.find_asset_data(p).asset_class_path.asset_name) == "StaticMesh"
)
if not levels.load_level(level):
    raise RuntimeError("Missing pilgrimage")
for a in actors.get_all_level_actors():
    if a.actor_has_tag("HeronCourt"):
        actors.destroy_actor(a)
boss = actors.spawn_actor_from_class(
    cls, unreal.Vector(11700, 1630, 145), unreal.Rotator(yaw=180)
)
boss.tags = ["HeronCourt", "VeiledHeron"]
boss.set_actor_label("Veiled Heron | Bride of the white water")
boss.set_actor_scale3d(unreal.Vector(1.27, 1.27, 1.27))
for i in range(7):
    a = actors.spawn_actor_from_class(
        unreal.StaticMeshActor, unreal.Vector(11700, 1630, 150 + i)
    )
    a.static_mesh_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    a.static_mesh_component.set_static_mesh(quill)
    a.static_mesh_component.set_editor_property("disallow_nanite", True)
    a.static_mesh_component.set_material(0, vane)
    a.set_actor_enable_collision(False)
    a.set_actor_hidden_in_game(True)
    a.tags = ["HeronCourt", "HeronQuill"]
    a.set_actor_label("Veiled Heron flight feather")
bounds = actors.spawn_actor_from_class(
    unreal.NavMeshBoundsVolume, unreal.Vector(11500, 1600, 140)
)
bounds.tags = ["HeronCourt"]
bounds.set_actor_label("Moon gate court navigation")
_, e = bounds.get_actor_bounds(False)
bounds.set_actor_scale3d(unreal.Vector(1350 / e.x, 1230 / e.y, 320 / e.z))
nav = unreal.NavigationSystemV1.get_navigation_system(boss)
nav.on_navigation_bounds_updated(bounds)
unreal.SystemLibrary.execute_console_command(boss, "RebuildNavigation")
route = nav.find_path_to_location_synchronously(
    boss, unreal.Vector(11100, 1630, 8), unreal.Vector(11700, 1630, 8)
)
if not route or route.is_partial() or len(route.path_points) < 2:
    raise RuntimeError("Missing path across Heron court")
if not levels.save_current_level():
    raise RuntimeError("Could not save Heron encounter")
(project / "Saved" / "HeronDuel.json").write_text(
    json.dumps({"revision": 2, "boss": cls.get_name(), "mesh": skin.get_path_name()})
)
unreal.log("VESPER_HERON_READY")
