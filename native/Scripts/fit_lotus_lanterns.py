"""Refit the existing lantern actors without rebuilding the route or its collision deck."""

import json
from pathlib import Path
import sys
import unreal

project = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
sys.path.insert(0, str(project / "Scripts"))
from lotus_lantern import build

lib = unreal.EditorAssetLibrary
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
folder = "/Game/Vesper/RouteArt/LotusRoadLamp"
replacement = {
    "Carved_grey_stone": "LotusStone",
    "Patinated_bronze": "LotusBronze",
    "Worn_brass": "LotusGilt",
    "Amber_silk": "LotusScreen",
}
report = project / "Saved" / "LotusLanterns.json"
level = "/Game/Vesper/Maps/MountainPilgrimage"
if not levels.load_level(level):
    raise RuntimeError("Cannot open pilgrimage map")


def mesh_assets():
    meshes = {}
    if lib.does_directory_exist(folder):
        for path in lib.list_assets(folder):
            if str(lib.find_asset_data(path).asset_class_path.asset_name) == "StaticMesh":
                mesh = lib.load_asset(path)
                meshes[mesh.get_name()] = mesh
    return meshes



meshes = mesh_assets()
if set(meshes) != set(replacement.values()):
    asset = project / "Saved" / "LotusRoadLamp.glb"
    build(project / "SourceAssets", project / "Art" / "LanternLandscape.jpg", asset)
    task = unreal.AssetImportTask()
    task.filename = str(asset)
    task.destination_path = folder
    task.automated = task.replace_existing = task.save = True
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    meshes = mesh_assets()
if set(meshes) != set(replacement.values()):
    raise RuntimeError("Incomplete lantern import: " + str(sorted(meshes)))


def site(actor):
    p = actor.get_actor_location()
    return round(p.x, 1), round(p.y, 1)


groups = {}
lights = {}
for actor in actors.get_all_level_actors():
    label = actor.get_actor_label()
    if label.startswith("Procession lantern") and isinstance(
        actor, unreal.StaticMeshActor
    ):
        comp = actor.static_mesh_component
        mesh = comp.static_mesh
        name = mesh.get_name()
        if "/ProcessionLantern/" in mesh.get_path_name() and name in replacement:
            name = replacement[name]
        elif not (mesh.get_path_name().startswith(folder + "/") and name in meshes):
            raise RuntimeError("Unknown route fixture: " + mesh.get_path_name())
        members = groups.setdefault(site(actor), {})
        if name in members:
            raise RuntimeError("Duplicate lantern fitting: " + name)
        members[name] = comp
    elif label.startswith("Votive light") and isinstance(actor, unreal.PointLight):
        pos = site(actor)
        if pos in lights:
            raise RuntimeError("Duplicate road light")
        lights[pos] = actor
expected = json.loads((project / "Saved" / "Procession.json").read_text())["lanterns"]
if (
    len(groups) != expected
    or groups.keys() != lights.keys()
    or any(set(group) != set(meshes) for group in groups.values())
):
    raise RuntimeError(
        "Incomplete lantern placements: " + str((len(groups), len(lights), expected))
    )
for key, members in groups.items():
    for name, comp in members.items():
        comp.modify()
        comp.set_editor_property("override_materials", [])
        comp.set_static_mesh(meshes[name])
    light = lights[key]
    pos = light.get_actor_location()
    light.set_actor_location(unreal.Vector(pos.x, pos.y, 152), False, True)
if not levels.save_current_level():
    raise RuntimeError("Could not save the lantern fitting")
report.write_text(
    json.dumps(
        dict(
            revision=1,
            sites=len(groups),
            components=sum(len(g) for g in groups.values()),
            lights=len(lights),
            screen_height_cm=152,
        )
    )
)
unreal.log("VESPER_LOTUS_LANTERNS_READY")
