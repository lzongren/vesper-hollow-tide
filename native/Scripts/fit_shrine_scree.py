"""Install the shrine's walkable scree and instance its mossy boulders and ferns."""

from functools import lru_cache
import json
from math import hypot
from pathlib import Path
import sys
import unreal

project = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
sys.path.insert(0, str(project / "Scripts"))
from shrine_talus import toes, build
from valley_surface import sampler
from route_material_usage import prepare
from ravine_vegetation import plant
from ravine_foliage_material import foliage

root = "/Game/Vesper/ShrineTalus"
art = project / "Art" / "ShrineTalus"
lib = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
if not levels.load_level("/Game/Vesper/Maps/MountainPilgrimage"):
    raise RuntimeError("Cannot open the pilgrimage")
scene = actors.get_all_level_actors()
cliff = next(
    a for a in scene if a.get_actor_label() == "Reliquary mountain Limestone_spurs"
)
floor = next(a for a in scene if a.get_actor_label() == "Valley floor")
sample_ground = sampler(project, floor)
frame = cliff.get_actor_transform()


def world_xy(x, y):
    p = unreal.MathLibrary.transform_location(frame, unreal.Vector(100 * x, 100 * y, 0))
    return p.x / 100, p.y / 100


@lru_cache(maxsize=200000)
def ground(x, y):
    return sample_ground(x * 100, y * 100) / 100


# Keep the shrine floor, final route segment, stairs and open galleries clear.
galleries = []
for a in scene:
    if a.get_actor_label().startswith("Reliquary side cloister"):
        p, extent = a.get_actor_bounds(False)
        galleries.append((p.x / 100, p.y / 100, extent.x / 100, extent.y / 100))


def clearance(x, y):
    lane = hypot(x - min(194, max(148, x)), y + 8) - 9
    court = hypot(x - 194, y + 8) - 18
    stairs = hypot(x - 194, y - min(-21, max(-46, y))) - 3.0
    gap = min(lane, court, stairs)
    for cx, cy, rx, ry in galleries:
        gap = min(gap, hypot(max(0, abs(x - cx) - rx), max(0, abs(y - cy) - ry)) - 1)
    return gap


def import_file(path, destination, replace=False):
    task = unreal.AssetImportTask()
    task.filename = str(path)
    task.destination_path = destination
    task.replace_existing = replace
    task.automated = task.save = True
    tools.import_asset_tasks([task])


def meshes(folder):
    return {
        obj.get_name(): obj
        for p in lib.list_assets(folder)
        if str(lib.find_asset_data(p).asset_class_path.asset_name) == "StaticMesh"
        for obj in [lib.load_asset(p)]
    }


if not lib.does_directory_exist(root + "/Boulders"):
    import_file(art / "ScreeBoulders.glb", root + "/Boulders")
stones = meshes(root + "/Boulders")
assets = [stones[f"FallenStone{i:02d}"] for i in range(1, 7)]
fern = meshes("/Game/Vesper/Understory/Ferns")
if len(fern) != 1:
    raise RuntimeError("Missing valley fern")
assets.append(next(iter(fern.values())))
bank_path = project / "Saved" / "ShrineTalus.glb"
groups, surface = build(
    toes(project / "Art" / "ShrineCliffWalk.glb", world_xy),
    ground,
    clearance,
    bank_path,
)
import_file(bank_path, root + "/FanBank", True)
bank = meshes(root + "/FanBank")["ShrineTalus"]
body = bank.get_editor_property("body_setup")
body.set_editor_property(
    "collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE
)
lib.save_loaded_asset(bank, only_if_is_dirty=False)

edit = unreal.MaterialEditingLibrary
# The original ground graph samples forest cover, paths, and damp seams
# in world XY. Continue those exact layers across the thin toe of each fan.
bank_material = root + "/ForestScree"
mat = (
    lib.load_asset(bank_material)
    if lib.does_asset_exist(bank_material)
    else lib.duplicate_asset(
        floor.static_mesh_component.get_material(0).get_path_name(), bank_material
    )
)
if not isinstance(mat, unreal.Material):
    raise RuntimeError("Expected a forest floor material")


def node(cls, x, y):
    return edit.create_material_expression(mat, cls, x, y)


def wire(src, pin, dst, socket):
    if not edit.connect_material_expressions(src, pin, dst, socket):
        raise RuntimeError("Could not wire gravel material " + socket)


def output(src, pin, prop):
    if not edit.connect_material_property(src, pin, prop):
        raise RuntimeError("Could not assign gravel surface " + str(prop))


def sample(name, x, y, kind):
    tex_path = root + "/" + name
    if not lib.does_asset_exist(tex_path):
        import_file(art / (name + ".jpg"), root)
    texture = lib.load_asset(tex_path)
    if kind != "COLOR":
        texture.set_editor_property("srgb", False)
        texture.set_editor_property(
            "compression_settings",
            unreal.TextureCompressionSettings.TC_NORMALMAP
            if kind == "NORMAL"
            else unreal.TextureCompressionSettings.TC_MASKS,
        )
        lib.save_loaded_asset(texture, only_if_is_dirty=False)
    n = node(unreal.MaterialExpressionTextureSample, x, y)
    n.set_editor_property("texture", texture)
    n.set_editor_property(
        "sampler_type", getattr(unreal.MaterialSamplerType, "SAMPLERTYPE_" + kind)
    )
    return n


prop = unreal.MaterialProperty
if (
    edit.get_material_property_input_node(mat, prop.MP_BASE_COLOR).get_editor_property(
        "desc"
    )
    != "Shrine gravel"
):
    coverage = node(unreal.MaterialExpressionVertexColor, 1200, 100)
    for i, (name, kind, pin, mp) in enumerate(
        (
            ("ScreeGravel", "COLOR", "RGB", prop.MP_BASE_COLOR),
            ("ScreeGravelNormal", "NORMAL", "RGB", prop.MP_NORMAL),
            ("ScreeGravelRough", "MASKS", "R", prop.MP_ROUGHNESS),
        )
    ):
        previous = edit.get_material_property_input_node(mat, mp)
        channel = edit.get_material_property_input_node_output_name(mat, mp)
        incoming = sample(name, 1200, 320 + i * 240, kind)
        if mp == prop.MP_BASE_COLOR:
            variation = node(unreal.MaterialExpressionMultiply, 1400, 300)
            wire(incoming, "RGB", variation, "A")
            wire(coverage, "G", variation, "B")
            incoming, pin = variation, ""
        blend = node(unreal.MaterialExpressionLinearInterpolate, 1650, i * 240)
        blend.set_editor_property("desc", "Shrine gravel")
        wire(previous, channel, blend, "A")
        wire(incoming, pin, blend, "B")
        wire(coverage, "R", blend, "Alpha")
        output(blend, "", mp)
    edit.set_base_material_usage(mat, unreal.MaterialUsage.MATUSAGE_NANITE, True)
    edit.recompile_material(mat)
    lib.save_loaded_asset(mat, only_if_is_dirty=False)
bank_shader = mat

# A scanned, engraved stone marks the turn out of the final staircase.
inscribed = meshes("/Game/Vesper/RouteArt/PassOutcrop/rock_face_01")["rock_face_01"]
lamp_parts = meshes("/Game/Vesper/RouteArt/LotusRoadLamp")
prepare([*assets, inscribed, *lamp_parts.values()], root + "/RouteShaders")
marker_material = root + "/PineRavineStone"
if lib.does_asset_exist(marker_material):
    mat = lib.load_asset(marker_material)
else:
    mat = tools.create_asset(
        "PineRavineStone", root, unreal.Material, unreal.MaterialFactoryNew()
    )
    output(sample("RavineInk", -440, 0, "COLOR"), "RGB", prop.MP_BASE_COLOR)
    output(sample("RavineInkNormal", -440, 200, "NORMAL"), "RGB", prop.MP_NORMAL)
    rough = node(unreal.MaterialExpressionTextureSample, -440, 400)
    rough.set_editor_property(
        "texture",
        lib.load_asset(
            "/Game/Vesper/RouteArt/PassOutcrop/rock_face_01/Textures/rock_face_01_rough"
        ),
    )
    rough.set_editor_property(
        "sampler_type",
        unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR
        if not rough.get_editor_property("texture").get_editor_property("srgb")
        else unreal.MaterialSamplerType.SAMPLERTYPE_COLOR,
    )
    output(rough, "G", prop.MP_ROUGHNESS)
    edit.set_base_material_usage(mat, unreal.MaterialUsage.MATUSAGE_NANITE, True)
    edit.recompile_material(mat)
    lib.save_loaded_asset(mat, only_if_is_dirty=False)
marker_label = "Pine ravine inscription"
marker = next((a for a in scene if a.get_actor_label() == marker_label), None)
if marker is None:
    marker = actors.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector())
marker.modify()
marker.set_actor_label(marker_label)
mx, my = 201, -49
mz = surface(mx, my)[0] - 0.38
marker.set_actor_location_and_rotation(
    unreal.Vector(100 * mx, 100 * my, 100 * mz), unreal.Rotator(yaw=18), False, True
)
marker.set_actor_scale3d(unreal.Vector(1.04, 1.04, 1.04))
marker.static_mesh_component.set_static_mesh(inscribed)
marker.static_mesh_component.set_material(0, mat)
marker.static_mesh_component.set_collision_profile_name("BlockAll")

plant(groups, surface, clearance, (mx, my))
foliage_materials = {}
for plant_name, source in (
    ("RavineGrass", "grass_medium_02"),
    ("RavineFlower", "dandelion_01"),
):
    destination = root + "/" + plant_name
    if not lib.does_directory_exist(destination):
        import_file(art / (plant_name + ".glb"), destination)
    parts = meshes(destination)
    material = foliage(root, destination + "/" + plant_name, plant_name, source)
    for j in range(1, 6):
        plant_mesh = parts[f"{plant_name}{j:02d}"]
        assets.append(plant_mesh)
        foliage_materials[plant_mesh] = material

label = "Cinder shrine scree"
existing = [a for a in scene if a.get_actor_label() == label]
if len(existing) > 1:
    raise RuntimeError("Duplicate shrine deposits")
owner = (
    existing[0]
    if existing
    else actors.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, 0))
)
owner.modify()
owner.set_actor_label(label)
owner.static_mesh_component.set_static_mesh(bank)
owner.static_mesh_component.set_material(0, bank_shader)
owner.static_mesh_component.set_collision_profile_name("BlockAll")
subsys = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
data = unreal.SubobjectDataBlueprintFunctionLibrary
handles = subsys.k2_gather_subobject_data_for_instance(owner)
parent = next(
    h
    for h in handles
    if data.get_object(data.get_data(h)) == owner.static_mesh_component
)
cls = unreal.HierarchicalInstancedStaticMeshComponent
old = {c.static_mesh: c for c in owner.get_components_by_class(cls)}
counts = {}
for i, asset in enumerate(assets):
    comp = old.get(asset)
    if not comp:
        args = unreal.AddNewSubobjectParams(parent_handle=parent, new_class=cls)
        handle, reason = subsys.add_new_subobject(args)
        comp = data.get_object(data.get_data(handle))
        if not isinstance(comp, cls):
            raise RuntimeError("Could not add rock instances: " + str(reason))
    comp.modify()
    comp.set_static_mesh(asset)
    comp.set_mobility(unreal.ComponentMobility.STATIC)
    comp.set_collision_profile_name("NoCollision" if i >= 6 else "BlockAll")
    if asset in foliage_materials:
        comp.set_material(0, foliage_materials[asset])
        comp.set_cull_distances(5600, 7800)
        comp.set_editor_property("world_position_offset_disable_distance", 4200)
    comp.clear_instances()
    transforms = [
        unreal.Transform(
            location=[x * 100, y * 100, z * 100],
            rotation=unreal.Rotator(roll=roll, pitch=pitch, yaw=yaw),
            scale=[s, s, s],
        )
        for x, y, z, roll, pitch, yaw, s in groups[i]
    ]
    comp.add_instances(transforms, False, True, False)
    count = comp.get_instance_count()
    if count != len(transforms) or count == 0:
        raise RuntimeError("Incomplete scree group")
    counts[asset.get_name()] = count
# A low silk lantern marks the turn towards the carving at playing distance.
lx, ly = mx - 3.42, my + 0.82
lz = surface(lx, ly)[0] - 0.035


def fixture(label, kind, position):
    actor = next((a for a in scene if a.get_actor_label() == label), None)
    if actor is None:
        actor = actors.spawn_actor_from_class(kind, position)
    actor.modify()
    actor.set_actor_label(label)
    actor.set_actor_location(position, False, True)
    return actor


base = unreal.Vector(lx * 100, ly * 100, lz * 100)
for part, mesh in lamp_parts.items():
    lamp = fixture("Ravine votive " + part, unreal.StaticMeshActor, base)
    lamp.set_actor_rotation(unreal.Rotator(yaw=14), False)
    lamp.set_actor_scale3d(unreal.Vector(0.78, 0.78, 0.78))
    lamp.static_mesh_component.set_static_mesh(mesh)
    lamp.static_mesh_component.set_collision_profile_name("BlockAll")
light = fixture(
    "Ravine votive flame", unreal.PointLight, base + unreal.Vector(0, 0, 152 * 0.78)
)
wick = light.light_component
wick.modify()
wick.set_editor_property("intensity_units", unreal.LightUnits.LUMENS)
wick.set_editor_property("intensity", 255)
wick.set_editor_property("attenuation_radius", 490)
wick.set_editor_property("source_radius", 8)
wick.set_light_color(unreal.LinearColor(1, 0.46, 0.18, 1))

sound_path = root + "/RavineWind"
if not lib.does_asset_exist(sound_path):
    import_file(art / "RavineWind.wav", root)
wind = lib.load_asset(sound_path)
wind.set_editor_property("looping", True)
# The player starts beyond the attenuation radius on the other end of the road.
wind.set_editor_property(
    "virtualization_mode", unreal.VirtualizationMode.PLAY_WHEN_SILENT
)
lib.save_loaded_asset(wind, only_if_is_dirty=False)
wind_label = "Wind in the ravine grass"
ear = unreal.Vector((mx - 1.2) * 100, (my + 1.4) * 100, (mz + 1) * 100)
amb = next((a for a in scene if a.get_actor_label() == wind_label), None)
if amb is None:
    amb = actors.spawn_actor_from_class(unreal.AmbientSound, ear)
amb.modify()
amb.set_actor_label(wind_label)
amb.set_actor_location(ear, False, True)
audio = amb.audio_component
audio.modify()
audio.set_sound(wind)
audio.set_editor_property("auto_activate", True)
audio.set_editor_property("volume_multiplier", 0.80)
audio.set_editor_property("override_attenuation", True)
falloff = audio.get_editor_property("attenuation_overrides")
falloff.set_editor_property("attenuation_shape_extents", unreal.Vector(450, 0, 0))
falloff.set_editor_property("falloff_distance", 2400)
audio.set_editor_property("attenuation_overrides", falloff)
if not levels.save_current_level():
    raise RuntimeError("Could not save shrine talus")
(project / "Saved" / "ShrineTalus.json").write_text(
    json.dumps(dict(revision=5, instances=counts, inscription=[mx, my, mz]))
)
unreal.log("VESPER_SHRINE_TALUS_READY " + str(counts) + " marker " + str((mx, my, mz)))
