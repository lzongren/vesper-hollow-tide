"""Install the bell court's open rain gallery and light its sheltered fighting lane."""

import json
from pathlib import Path
import sys

import unreal

project = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
sys.path.insert(0, str(project / "Scripts"))
from bell_gallery_mesh import bake
from egret_screen import bake as bake_screen
from route_material_usage import prepare
from gallery_roof_material import glaze

lib = unreal.EditorAssetLibrary
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
if not levels.load_level("/Game/Vesper/Maps/MountainPilgrimage"):
    raise RuntimeError("Missing mountain route")

root = "/Game/Vesper/RouteArt/BellRainGallery"


def fitted_mesh(name, generate):
    path = root + f"/{name}/StaticMeshes/{name}"
    if not lib.does_asset_exist(path):
        source = project / "Saved" / (name + ".glb")
        generate(source)
        job = unreal.AssetImportTask()
        job.filename, job.destination_path = str(source), root
        job.automated = job.save = True
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([job])
    mesh = lib.load_asset(path)
    if not mesh:
        raise RuntimeError("Missing gallery mesh " + path)
    prepare([mesh], root + "/Shaders")
    body = mesh.get_editor_property("body_setup")
    body.set_editor_property(
        "collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE
    )
    if not lib.save_loaded_asset(mesh, only_if_is_dirty=False):
        raise RuntimeError("Could not save collision for " + name)
    return mesh


mesh = fitted_mesh(
    "BellRainGallery", lambda target: bake(project / "SourceAssets", target)
)
screen = fitted_mesh(
    "BellEgretScreen",
    lambda target: bake_screen(
        project / "SourceAssets", project / "Art/BellCourt", target
    ),
)

existing = [a for a in actors.get_all_level_actors() if "VesperBellRain" in a.tags]
for old in existing:
    actors.destroy_actor(old)


def place(cls, xyz, label, aim=None):
    loc = unreal.Vector(*xyz)
    rot = (
        unreal.MathLibrary.find_look_at_rotation(loc, unreal.Vector(*aim))
        if aim
        else unreal.Rotator()
    )
    actor = actors.spawn_actor_from_class(cls, loc, rot)
    actor.set_actor_label(label)
    actor.tags = ["VesperBellRain"]
    return actor


centre = 3730
hall = place(unreal.StaticMeshActor, (centre, 0, 5.5), "Rain gallery at the bell court")
hall.static_mesh_component.set_static_mesh(mesh)
hall.static_mesh_component.set_collision_profile_name("BlockAll")
hall.set_actor_enable_collision(True)
wall = place(unreal.StaticMeshActor, (4520, 624, 5.5), "Plum and egrets spirit screen")
wall.static_mesh_component.set_static_mesh(screen)
wall.static_mesh_component.set_collision_profile_name("BlockAll")
wall.set_actor_enable_collision(True)
tile = glaze(root + "/Shaders")
for comp, skin in (
    (hall.static_mesh_component, mesh),
    (wall.static_mesh_component, screen),
):
    for i, slot in enumerate(skin.static_materials):
        if str(slot.material_slot_name) in ("KilnGrey", "GlazedRim", "RainTiles"):
            comp.set_material(i, tile)


def light(cls, xyz, aim, name, lumens, radius, tint):
    actor = place(cls, xyz, name, aim)
    comp = actor.light_component
    comp.set_mobility(unreal.ComponentMobility.MOVABLE)
    comp.set_editor_property("intensity_units", unreal.LightUnits.LUMENS)
    comp.set_intensity(lumens)
    comp.set_editor_property("attenuation_radius", radius)
    comp.set_light_color(unreal.LinearColor(*tint, 1))
    return comp


# Open sky on the unscreened side provides a single broad, coherent key.
opening = light(
    unreal.RectLight,
    (centre - 320, 465, 320),
    (centre + 90, -110, 142),
    "Open side of the rain gallery",
    345,
    1280,
    (0.71, 0.81, 1.0),
)
opening.set_editor_property("source_width", 530)
opening.set_editor_property("source_height", 235)
# Low light from the open eastern gable outlines weapons against the dark soffit.
edge = light(
    unreal.SpotLight,
    (centre + 880, 195, 387),
    (centre - 80, -70, 116),
    "Light under the eastern eave",
    165,
    1480,
    (1.0, 0.74, 0.46),
)
edge.set_editor_property("inner_cone_angle", 22)
edge.set_editor_property("outer_cone_angle", 53)
edge.set_editor_property("source_radius", 48)
for i, offset in enumerate((-438, 438)):
    wick = light(
        unreal.PointLight,
        (centre + offset, -482, 326),
        None,
        f"Gallery lantern {i + 1}",
        72,
        360,
        (1.0, 0.46, 0.18),
    )
    wick.set_editor_property("source_radius", 19)
    wick.set_editor_property("cast_shadows", False)

# A low oblique wash picks up the chisel work without flattening the feather relief.
wash = light(
    unreal.RectLight,
    (4365, 912, 390),
    (4500, 560, 205),
    "Window light on the carved screen",
    14,
    730,
    (0.82, 0.87, 0.91),
)
wash.set_editor_property("source_width", 145)
wash.set_editor_property("source_height", 95)
if not levels.save_current_level():
    raise RuntimeError("Could not save the rain gallery")
report = dict(
    revision=3,
    screen=screen.get_path_name(),
    mesh=mesh.get_path_name(),
    centre_cm=centre,
    lanterns=2,
)
(project / "Saved" / "BellRainGallery.json").write_text(json.dumps(report))
unreal.log("VESPER_RAIN_GALLERY_READY " + str(report))
