"""Bake the valley's soft reflected light for the playable character."""

import json
from pathlib import Path

import unreal

project = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
if not levels.load_level("/Game/Vesper/Maps/MountainPilgrimage"):
    raise RuntimeError("Cannot load the playable mountain map")

# Two diffuse lobes approximate the broad reflection from pale paving in
# the open valley. Their world directions stay fixed as the player turns.
# A separate light channel lets the architecture retain its baked art grade.
tag = "VesperStoneBounce"
existing = {
    a.get_actor_label(): a for a in actors.get_all_level_actors() if tag in a.tags
}
for label, yaw in (("Courtyard stone, west", -29), ("Courtyard stone, east", 114)):
    rotation = unreal.Rotator(pitch=38, yaw=yaw)
    light = existing.get(label)
    if light is None:
        light = actors.spawn_actor_from_class(
            unreal.DirectionalLight, unreal.Vector(0, 0, 400), rotation
        )
        light.set_actor_label(label)
        light.set_editor_property("tags", [tag])
    light.set_actor_rotation(rotation, False)
    component = light.light_component
    component.set_mobility(unreal.ComponentMobility.MOVABLE)
    component.set_editor_property("atmosphere_sun_light", False)
    component.set_editor_property("cast_shadows", False)
    component.set_lighting_channels(False, True, False)
    component.set_specular_scale(0.0)
    component.set_intensity(1.15)
    component.set_light_color(unreal.LinearColor(0.97, 0.99, 1.0, 1))

# A short-range diffuse light represents reflection off the ivory stole.
# Combat attaches it to the wearer's lower face once per possession.
collars = [a for a in actors.get_all_level_actors() if "VesperStoleBounce" in a.tags]
if len(collars) > 1:
    raise RuntimeError("Duplicate stole bounce lights")
if collars and collars[0].get_class() != unreal.PointLight.static_class():
    actors.destroy_actor(collars.pop())
stole = (
    collars[0]
    if collars
    else actors.spawn_actor_from_class(unreal.PointLight, unreal.Vector(0, 0, 0))
)
stole.set_actor_label("Ivory stole reflection")
stole.set_editor_property("tags", ["VesperStoleBounce"])
lamp = stole.light_component
lamp.set_mobility(unreal.ComponentMobility.MOVABLE)
lamp.set_lighting_channels(False, True, False)
lamp.set_editor_property("intensity_units", unreal.LightUnits.CANDELAS)
lamp.set_editor_property("cast_shadows", False)
lamp.set_editor_property("attenuation_radius", 32.0)
lamp.set_editor_property("source_radius", 3.0)
lamp.set_specular_scale(0.0)
lamp.set_light_color(unreal.LinearColor(0.965, 0.99, 0.93, 1))
lamp.set_intensity(0)

lib = unreal.EditorAssetLibrary
bp = lib.load_asset("/Game/Vesper/Duel/BP_BelfryPilgrim")
subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
library = unreal.SubobjectDataBlueprintFunctionLibrary
for handle in subsystem.k2_gather_subobject_data_for_blueprint(bp):
    template = library.get_object_for_blueprint(library.get_data(handle), bp)
    if isinstance(template, unreal.SkeletalMeshComponent):
        template.set_lighting_channels(True, True, False)
unreal.BlueprintEditorLibrary.compile_blueprint(bp)
unreal.get_default_object(bp.generated_class()).mesh.set_lighting_channels(
    True, True, False
)
if (
    not lib.save_loaded_asset(bp, only_if_is_dirty=False)
    or not levels.save_current_level()
):
    raise RuntimeError("Could not save character lighting")
(project / "Saved/StoneBounce.json").write_text(json.dumps({"revision": 9}))
unreal.log("VESPER_STONE_BOUNCE_READY")
