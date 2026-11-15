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
    rotation = unreal.Rotator(pitch=22, yaw=yaw)
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
    component.set_intensity(1.08)
    component.set_light_color(unreal.LinearColor(0.97, 0.99, 1.0, 1))

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
(project / "Saved/StoneBounce.json").write_text(json.dumps({"revision": 3}))
unreal.log("VESPER_STONE_BOUNCE_READY")
