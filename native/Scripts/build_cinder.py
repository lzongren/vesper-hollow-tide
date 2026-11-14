"""Fit the Saint, light the relief and install his cast geometry in the final sanctuary."""

import json
import math
from pathlib import Path
import sys
import unreal

project = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
sys.path.insert(0, str(project / "Scripts"))
from build_bellwarden import (
    mesh_for,
    fit,
    actors,
    levels,
    level,
    lib,
    combat,
    import_tone,
)
from keeper_materials import surface
from cinder_rite import bake
import cinder_fire

root = "/Game/Vesper/Duel/CinderRites"
skin = mesh_for("CinderSaint", "cinder-ascetic.glb", cinder=True)
package = skin.get_path_name().split("/SkeletalMeshes/")[0]
slots = list(skin.materials)
for slot in slots:
    name = str(slot.material_slot_name)
    if name == "Pilgrim_0":
        slot.material_interface = surface(
            package, "AshenHide", "Pilgrim2", 0.07, 0.71, normal="Pilgrim4"
        )
    if name == "Vermilion_prayer_stole":
        slot.material_interface = surface(
            package, "StoleSilk", "VermilionBrocade", 0.1, 0.68
        )
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
    "BP_CinderSaint",
    skin,
    {
        "ai_controller_class": unreal.AIController.static_class(),
        "Max HP": 18.0,
        "Current HP": 18.0,
    },
)


def mesh_asset(name, file):
    folder = root + "/" + name
    paths = lib.list_assets(folder) if lib.does_directory_exist(folder) else []
    if not paths:
        task = unreal.AssetImportTask()
        task.filename, task.destination_path = str(file), folder
        task.save = task.automated = True
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        paths = lib.list_assets(folder)
    return next(
        lib.load_asset(p)
        for p in paths
        if str(lib.find_asset_data(p).asset_class_path.asset_name) == "StaticMesh"
    )


def glow(name, color):
    if lib.does_asset_exist(root + "/" + name):
        return lib.load_asset(root + "/" + name)
    mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        name, root, unreal.Material, unreal.MaterialFactoryNew()
    )
    mat.set_editor_property("two_sided", True)
    edit = unreal.MaterialEditingLibrary
    for target, col, y in [
        (unreal.MaterialProperty.MP_BASE_COLOR, (0.34, 0.075, 0.019), 0),
        (unreal.MaterialProperty.MP_EMISSIVE_COLOR, color, 180),
    ]:
        n = edit.create_material_expression(
            mat, unreal.MaterialExpressionConstant3Vector, -240, y
        )
        n.set_editor_property("constant", unreal.LinearColor(*col, 1))
        if not edit.connect_material_property(n, "", target):
            raise RuntimeError("Disconnected rite surface")
    edit.recompile_material(mat)
    lib.save_loaded_asset(mat, only_if_is_dirty=False)
    return mat


seal_file = project / "Saved" / "PrayerSeal.glb"
bake(seal_file)
fire_file = project / "Saved" / "PrayerPlume.glb"
cinder_fire.bake(fire_file, project / "SourceAssets" / "shrine-fire.rg8.gz")
meshes = [mesh_asset("PrayerSeal", seal_file), mesh_asset("PrayerPlume", fire_file)]
fire_root = meshes[1].get_path_name().split("/StaticMeshes/")[0]
sheet = lib.load_asset(fire_root + "/Textures/ShrineFireSheet")
surfaces = [
    glow("IncisedCopper", (2.9, 0.57, 0.048)),
    cinder_fire.material(unreal, root, sheet),
]
relief = mesh_asset("Reliquary", project / "SourceAssets" / "cinder-relief.glb")
import_tone("PrayerBell", 146.8)
if not levels.load_level(level):
    raise RuntimeError("Missing final court")
for a in actors.get_all_level_actors():
    if a.actor_has_tag("CinderCourt"):
        actors.destroy_actor(a)
    elif (
        isinstance(a, unreal.StaticMeshActor)
        and a.static_mesh_component.static_mesh
        and "/ShrineLotusPortal/" in a.static_mesh_component.static_mesh.get_path_name()
    ):
        a.set_actor_rotation(unreal.Rotator(yaw=90), False)
        for i, slot in enumerate(a.static_mesh_component.static_mesh.static_materials):
            name = (
                "LampStone"
                if "limestone" in str(slot.material_slot_name).lower()
                else "Patina"
            )
            a.static_mesh_component.set_material(
                i, lib.load_asset("/Game/Vesper/RouteArt/BellHall/Surfaces/" + name)
            )
boss = actors.spawn_actor_from_class(
    cls, unreal.Vector(19600, -830, 156), unreal.Rotator(yaw=180)
)
boss.tags = ["CinderCourt", "CinderSaint"]
boss.set_actor_label("Saint of Cinders | The prayer that would not die")
boss.set_actor_scale3d(unreal.Vector(1.48, 1.48, 1.48))


def place(mesh, pos, yaw, label):
    a = actors.spawn_actor_from_class(
        unreal.StaticMeshActor, unreal.Vector(*pos), unreal.Rotator(yaw=yaw)
    )
    a.tags = ["CinderCourt"]
    a.set_actor_label(label)
    a.static_mesh_component.set_static_mesh(mesh)
    a.static_mesh_component.set_editor_property("disallow_nanite", True)
    a.set_actor_enable_collision(False)
    return a


place(relief, (20410, -800, 393), 90, "Guardian and paired dragons")
# Set the relief into a precinct, with shelter on either side of the nave.
# Existing dressed gallery components supply their matching finish overrides.
gallery = {}
for original in actors.get_all_level_actors():
    if not isinstance(original, unreal.StaticMeshActor):
        continue
    comp = original.static_mesh_component
    part = comp.static_mesh
    if not part:
        continue
    path = part.get_path_name()
    if "/MoonGatePorch/" in path:
        # The road leaves this court on a diagonal. The open central bay
        # straddles that line, with the posts and their stone feet to the sides.
        road_angle = math.degrees(math.atan2(-2400, 3300))
        original.set_actor_rotation(unreal.Rotator(yaw=90 + road_angle), False)
        original.set_actor_location(
            unreal.Vector(12400, 1600 - 900 * 2400 / 3300, 8), False, True
        )
    if "/MoonGatePorch/" in path or "/WestWaterGallery/" in path:
        body = part.get_editor_property("body_setup")
        body.set_editor_property(
            "collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE
        )
        if not lib.save_loaded_asset(part, only_if_is_dirty=False):
            raise RuntimeError("Could not save architectural collision for " + path)
    if "/WestWaterGallery/" in path:
        gallery[path] = comp
        # The gallery extends along its local X axis. Turn existing galleries
        # parallel to their roads so their footings do not cross the playable lane.
        dx, dy = (
            (3400, 1600) if original.get_actor_location().x < 10000 else (3300, -2400)
        )
        original.set_actor_rotation(
            unreal.Rotator(yaw=math.degrees(math.atan2(dy, dx))), False
        )
if not gallery:
    raise RuntimeError("Missing covered gallery")
for side in (-1, 1):
    for comp in gallery.values():
        a = place(
            comp.static_mesh,
            (20310, -800 + side * 1380, 2),
            90,
            "Reliquary side cloister",
        )
        for i, mat in enumerate(comp.get_materials()):
            a.static_mesh_component.set_material(i, mat)

cliffs = root + "/ShrineCliffs"
if not lib.does_directory_exist(cliffs):
    imp = unreal.AssetImportTask()
    imp.filename, imp.destination_path = (
        str(project / "Art" / "ShrineCliffWalk.glb"),
        cliffs,
    )
    imp.save = imp.automated = True
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([imp])
for key in lib.list_assets(cliffs):
    if str(lib.find_asset_data(key).asset_class_path.asset_name) != "StaticMesh":
        continue
    part = lib.load_asset(key)
    a = place(part, (19400, -800, -265), -19, "Reliquary mountain " + part.get_name())
    a.set_actor_scale3d(unreal.Vector(1.15, 1.15, 0.90))
    if "Summit" in part.get_name():
        a.static_mesh_component.set_material(
            0, lib.load_asset("/Game/Vesper/HighlandSky/SummitNeedles")
        )
# Grove on the far side of the relief closes gaps below the limestone ridges.
pines = [
    lib.load_asset(p)
    for p in lib.list_assets("/Game/Vesper/RouteArt/MountainPines")
    if str(lib.find_asset_data(p).asset_class_path.asset_name) == "StaticMesh"
]
for i, (x, y, z, size) in enumerate(
    [
        (21150, -1770, -180, 1.44),
        (21200, -2920, -260, 1.1),
        (20910, 380, -155, 1.21),
        (21440, 1150, -220, 1.42),
        (22250, -2050, -240, 1.53),
        (21900, 780, -230, 1.67),
        (21750, -710, -140, 1.22),
    ]
):
    a = place(pines[i % len(pines)], (x, y, z), i * 73, "Reliquary grove")
    a.set_actor_scale3d(unreal.Vector(size, size, size))
for side in [-1, 1]:
    light = actors.spawn_actor_from_class(
        unreal.PointLight, unreal.Vector(20080, -800 + side * 320, 205)
    )
    light.tags = ["CinderCourt"]
    light.set_actor_label("Reliquary brazier glow")
    c = light.light_component
    c.set_light_color(unreal.LinearColor(1, 0.345, 0.11, 1))
    c.set_editor_property("intensity_units", unreal.LightUnits.LUMENS)
    c.set_editor_property("intensity", 1850)
    c.set_editor_property("attenuation_radius", 840)
for tag in ("CinderWave", "CinderMark", "CinderFlame"):
    surface_index = int(tag == "CinderFlame")
    a = place(meshes[surface_index], (19600, -830, 22), 0, tag)
    a.tags = ["CinderCourt", tag]
    a.static_mesh_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    a.static_mesh_component.set_material(0, surfaces[surface_index])
    a.set_actor_hidden_in_game(True)
bounds = actors.spawn_actor_from_class(
    unreal.NavMeshBoundsVolume, unreal.Vector(19400, -800, 140)
)
bounds.tags = ["CinderCourt"]
bounds.set_actor_label("Reliquary court navigation")
_, e = bounds.get_actor_bounds(False)
bounds.set_actor_scale3d(unreal.Vector(1370 / e.x, 1220 / e.y, 320 / e.z))
nav = unreal.NavigationSystemV1.get_navigation_system(boss)
nav.on_navigation_bounds_updated(bounds)
unreal.SystemLibrary.execute_console_command(boss, "RebuildNavigation")
route = nav.find_path_to_location_synchronously(
    boss, unreal.Vector(19000, -830, 8), unreal.Vector(19600, -830, 8)
)
if not route or route.is_partial() or len(route.path_points) < 2:
    raise RuntimeError("No path across final court")
if not levels.save_current_level():
    raise RuntimeError("Could not save final court")
(project / "Saved" / "CinderDuel.json").write_text(
    json.dumps({"revision": 2, "boss": cls.get_name(), "mesh": skin.get_path_name(), "effects": 3})
)
unreal.log("VESPER_CINDER_READY")
