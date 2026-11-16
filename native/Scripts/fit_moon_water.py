"""Set the crescent bridge, lotus beds and reflective water into the Moon Gate court."""

import json
from pathlib import Path
import sys
import unreal

project = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
sys.path.insert(0, str(project / "Scripts"))
from pond_sound import install as pond_ambience
from moon_bridge import bridge
from moon_escarpment import escarpment, grove
from lotus_beds import surface, planting
from moon_water_material import water_material
from moon_bridge_material import stone_finishes
from route_material_usage import prepare
from valley_surface import sampler

root = "/Game/Vesper/RouteArt/MoonWater"
lib = unreal.EditorAssetLibrary
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if not levels.load_level("/Game/Vesper/Maps/MountainPilgrimage"):
    raise RuntimeError("Missing mountain route")


def import_mesh(name, bake, solid):
    path = root + f"/{name}/StaticMeshes/{name}"
    if not lib.does_asset_exist(path):
        file = project / "Saved" / (name + ".glb")
        bake(project / "SourceAssets", file)
        task = unreal.AssetImportTask()
        task.filename = str(file)
        task.destination_path = root
        task.automated = task.save = True
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    asset = lib.load_asset(path)
    if not asset:
        raise RuntimeError("Missing garden mesh " + path)
    prepare([asset], root + "/Shaders")
    if name in ("LotusWater", "GardenLotus"):
        config = asset.get_editor_property("nanite_settings")
        config.set_editor_property("enabled", False)
        asset.set_editor_property("nanite_settings", config)
        if not lib.save_loaded_asset(asset, only_if_is_dirty=False):
            raise RuntimeError("Could not save conventional pond mesh " + name)
    if solid:
        asset.get_editor_property("body_setup").set_editor_property(
            "collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE
        )
        if not lib.save_loaded_asset(asset, only_if_is_dirty=False):
            raise RuntimeError("Could not save bridge collision")
    return asset


meshes = {
    key: import_mesh(key, bake, key == "LotusBridge")
    for key, bake in (
        ("LotusBridge", bridge),
        ("LotusWater", surface),
        ("GardenLotus", planting),
    )
}
water = water_material(root + "/Shaders")
stone = stone_finishes(root)
for old in actors.get_all_level_actors():
    if old.actor_has_tag("VesperMoonWater"):
        actors.destroy_actor(old)
center = (14140, 2280, 0)
for key, label in (
    ("LotusBridge", "Crescent bridge and lotus quay"),
    ("LotusWater", "Moon court pond"),
    ("GardenLotus", "Lotus colonies in the moon court"),
):
    actor = actors.spawn_actor_from_class(
        unreal.StaticMeshActor, unreal.Vector(*center), unreal.Rotator()
    )
    actor.tags = ["VesperMoonWater"]
    actor.set_actor_label(label)
    comp = actor.static_mesh_component
    comp.set_static_mesh(meshes[key])
    solid = key == "LotusBridge"
    comp.set_collision_profile_name("BlockAll" if solid else "NoCollision")
    actor.set_actor_enable_collision(solid)
    if key == "LotusBridge":
        for index, slot in enumerate(meshes[key].static_materials):
            comp.set_material(index, stone[str(slot.material_slot_name)])
    if key == "LotusWater":
        comp.set_editor_property("disallow_nanite", True)
        comp.set_material(0, water)
        comp.set_cast_shadow(False)
# Replace the mountain in its existing frame so that the seven other spurs
# and the summit trees keep their positions and weathered materials.
for label, name, bake, material in (
    (
        "Reliquary mountain Limestone_spurs",
        "MoonEscarpment",
        escarpment,
        "WeatheredShrineFace",
    ),
    ("Reliquary mountain Summit_pines", "MoonSummitPines", grove, "DistantNeedleCrown"),
):
    matches = [a for a in actors.get_all_level_actors() if a.get_actor_label() == label]
    if len(matches) != 1:
        raise RuntimeError("Missing shrine scenery " + label)
    actor = matches[0]
    actor.modify()
    comp = actor.static_mesh_component
    comp.modify()
    replacement = import_mesh(name, bake, False)
    finish = lib.load_asset("/Game/Vesper/RiverPeaks/" + material)
    if not finish:
        raise RuntimeError("Missing shrine material " + material)
    comp.set_static_mesh(replacement)
    comp.set_material(0, finish)
    actor.set_actor_enable_collision(False)
    meshes[name] = replacement
scene = actors.get_all_level_actors()
cliff = next(
    a for a in scene if a.get_actor_label() == "Reliquary mountain Limestone_spurs"
)
north = unreal.MathLibrary.transform_location(
    cliff.get_actor_transform(), unreal.Vector(-700, 3800, 0)
)
ground = sampler(
    project, next(a for a in scene if a.get_actor_label() == "Valley floor")
)
for actor in scene:
    label = actor.get_actor_label()
    if label in (
        "Reliquary mountain ShrineCliffWalk_node_2",
        "Reliquary mountain ShrineCliffWalk_node_3",
    ):
        # Move the ledge walkway and its votive lamp with their supporting spur.
        actor.modify()
        actor.set_actor_location(north, False, True)
        if label.endswith("node_2"):
            actor.static_mesh_component.set_material(0, stone["PittedKerb"])
    elif label == "Mountain pine":
        loc = actor.get_actor_location()
        if 12900 < loc.x < 15560 and 835 < loc.y < 3750:
            y = 3970 + 0.64 * (loc.y - 835)
            actor.modify()
            actor.set_actor_location(
                unreal.Vector(loc.x, y, ground(loc.x, y) - 12), False, True
            )
    elif label == "Cinder shrine scree":
        for inst in actor.get_components_by_class(unreal.InstancedStaticMeshComponent):
            if not inst.static_mesh:
                continue
            remove = []
            for i in range(inst.get_instance_count()):
                loc = inst.get_instance_transform(i, True).translation
                if 12905 < loc.x < 15540 and 820 < loc.y < 3740:
                    remove.append(i)
            if remove:
                actor.modify()
                inst.modify()
                for i in reversed(remove):
                    if not inst.remove_instance(i):
                        raise RuntimeError("Could not clear submerged scree")
pond_ambience(project, root, actors)
if not levels.save_current_level():
    raise RuntimeError("Could not save Moon Gate court")
report = dict(
    revision=7, center=center, assets=[m.get_path_name() for m in meshes.values()]
)
(project / "Saved" / "MoonWater.json").write_text(json.dumps(report))
unreal.log("VESPER_MOON_WATER_READY " + str(report))
