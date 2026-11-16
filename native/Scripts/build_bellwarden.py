"""Fit both combatants and place the Bellwarden in the actual first court."""

import json
import runpy
from pathlib import Path

import unreal

project = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
lib = unreal.EditorAssetLibrary
duel = "/Game/Vesper/Duel/"
combat = "/Game/Variant_Combat/Blueprints/"
level = "/Game/Vesper/Maps/MountainPilgrimage"
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def outfit(folder):
    meshes = [
        p
        for p in lib.list_assets(folder)
        if str(lib.find_asset_data(p).asset_class_path.asset_name) == "SkeletalMesh"
    ]
    if len(meshes) != 1:
        raise RuntimeError(f"Expected one fitted character in {folder}: {meshes}")
    return lib.load_asset(meshes[0])


def duplicate(source, name):
    path = duel + name
    return (
        lib.load_asset(path)
        if lib.does_asset_exist(path)
        else lib.duplicate_asset(source, path)
    )


def fit(source, name, mesh, stats):
    # The StateTree and combat controller cast to the template pawn types.
    # Subclasses preserve those casts while keeping the stock defaults intact.
    path = duel + name
    if lib.does_asset_exist(path):
        bp = lib.load_asset(path)
    else:
        factory = unreal.BlueprintFactory()
        factory.set_editor_property(
            "parent_class", lib.load_asset(combat + source).generated_class()
        )
        bp = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            name, duel.rstrip("/"), unreal.Blueprint, factory
        )
    subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    library = unreal.SubobjectDataBlueprintFunctionLibrary
    for handle in subsystem.k2_gather_subobject_data_for_blueprint(bp):
        component = library.get_object_for_blueprint(library.get_data(handle), bp)
        if isinstance(component, unreal.SkeletalMeshComponent):
            component.set_skeletal_mesh_asset(mesh)
            component.set_editor_property("override_materials", [])
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    defaults = unreal.get_default_object(bp.generated_class())
    defaults.mesh.set_skeletal_mesh_asset(mesh)
    defaults.mesh.set_editor_property("override_materials", [])
    for prop, value in stats.items():
        defaults.set_editor_property(prop, value)
    if not lib.save_loaded_asset(bp, only_if_is_dirty=False):
        raise RuntimeError("Could not save " + name)
    return bp.generated_class()


def import_tone(name, fundamental):
    wav = project / "Saved" / (name + ".wav")
    if not lib.does_asset_exist(duel + name):
        runpy.run_path(str(project / "Scripts" / "belfry_audio.py"))["strike"](
            wav, fundamental
        )
        task = unreal.AssetImportTask()
        task.filename, task.destination_path = str(wav), duel.rstrip("/")
        task.automated = task.save = True
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    if not lib.load_asset(duel + name):
        raise RuntimeError("Could not load " + name)


def mesh_for(name, model, **gear):
    folder = duel + name
    if not lib.does_directory_exist(folder):
        staging = project / "Saved" / "PilgrimFitting"
        output = staging / (name + ".glb")
        runpy.run_path(str(project / "Scripts" / "bind_pilgrim.py"))["build"](
            staging / "LocalRig.glb",
            project / "SourceAssets" / model,
            project / "Art",
            project / "SourceAssets",
            output,
            **gear,
        )
        task = unreal.AssetImportTask()
        task.filename, task.destination_path = str(output), folder
        task.replace_existing = task.automated = task.save = True
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    return outfit(folder)


def build():
    boss_skin = mesh_for("TollKeeper", "pilgrim.glb", bellwarden=True)
    runpy.run_path(str(project / "Scripts" / "keeper_materials.py"))["finish"](boss_skin)
    hero_skin = mesh_for("SwordPilgrim", "pilgrim.glb", armed=True)
    soldier = lib.load_asset(combat + "AI/BP_CombatEnemy")
    skeleton = unreal.get_default_object(
        soldier.generated_class()
    ).mesh.skeletal_mesh_asset.skeleton
    for skin in (boss_skin, hero_skin):
        skin.skeleton.set_editor_property("compatible_skeletons", [skeleton])
        lib.save_loaded_asset(skin.skeleton, only_if_is_dirty=False)
    import_tone("BronzeSweep", 109.9)
    import_tone("GraveToll", 73.4)
    boss_class = fit(
        "AI/BP_CombatEnemy",
        "BP_BelfryKeeper",
        boss_skin,
        {
            "ai_controller_class": unreal.AIController.static_class(),
            "Max HP": 12.0,
            "Current HP": 12.0,
            "Melee Damage": 2.0,
            "Melee Knockback Impulse": 220.0,
            "Melee Launch Impulse": 65.0,
            "Melee Trace Distance": 150.0,
            "Melee Trace Radius": 50.0,
        },
    )
    player = fit(
        "BP_CombatCharacter",
        "BP_BelfryPilgrim",
        hero_skin,
        {
            "Melee Knockback Impulse": 150.0,
            "Melee Launch Impulse": 55.0,
            "Default Camera Distance": 420.0,
            "Shoulder Offset": 118.0,
            "Max HP": 10.0,
            "Current HP": 10.0,
            "Melee Damage": 1.0,
        },
    )
    mode = duplicate(combat + "BP_CombatGameMode", "BP_BelfryMode")
    unreal.BlueprintEditorLibrary.compile_blueprint(mode)
    unreal.get_default_object(mode.generated_class()).set_editor_property(
        "default_pawn_class", player
    )
    lib.save_loaded_asset(mode, only_if_is_dirty=False)
    if not levels.load_level(level):
        raise RuntimeError("Missing mountain route")
    for a in actors.get_all_level_actors():
        if a.actor_has_tag("BelfryDuel"):
            actors.destroy_actor(a)
    boss = actors.spawn_actor_from_class(
        boss_class, unreal.Vector(4390, 120, 170), unreal.Rotator(yaw=180)
    )
    boss.tags = ["BelfryDuel", "Bellwarden"]
    boss.set_actor_label("Bellwarden | Keeper of the last toll")
    boss.set_actor_scale3d(unreal.Vector(1.5, 1.5, 1.5))
    bounds = actors.spawn_actor_from_class(
        unreal.NavMeshBoundsVolume, unreal.Vector(4170, 0, 180)
    )
    bounds.tags = ["BelfryDuel"]
    bounds.set_actor_label("Bellwarden court navigation")
    _, extent = bounds.get_actor_bounds(False)
    unreal.log("VESPER_BRUSH " + str(extent))
    if min(extent.x, extent.y, extent.z) <= 0:
        raise RuntimeError("Navigation brush is empty")
    bounds.set_actor_scale3d(
        unreal.Vector(1290 / extent.x, 1190 / extent.y, 310 / extent.z)
    )
    world = boss.get_world()
    # A scaled fighter needs a wider capsule but still uses the human nav agent.
    # Find the baked mesh with a path beginning and ending on the floor.
    nav = unreal.NavigationSystemV1.get_navigation_system(world)
    nav.on_navigation_bounds_updated(bounds)
    world.get_world_settings().set_editor_property(
        "default_game_mode", mode.generated_class()
    )
    unreal.SystemLibrary.execute_console_command(boss, "RebuildNavigation")
    route = unreal.NavigationSystemV1.find_path_to_location_synchronously(
        world, unreal.Vector(3760, 120, 8), unreal.Vector(4390, 120, 8)
    )
    if not route or route.is_partial() or len(route.path_points) < 2:
        raise RuntimeError("No traversable navigation path across the first court")
    if not levels.save_current_level():
        raise RuntimeError("Could not save the court")
    report = {
        "boss": boss_class.get_name(),
        "mesh": boss_skin.get_path_name(),
        "player": player.get_name(),
        "center_cm": [4390, 120],
        "revision": 3,
    }
    (project / "Saved" / "BelfryDuel.json").write_text(json.dumps(report, indent=2))
    unreal.log("VESPER_BELFRY_READY")


if __name__ == "__main__":
    build()
