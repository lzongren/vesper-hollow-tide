"""Light the playable valley beneath a broken evening cloud deck."""

import json
from pathlib import Path

import unreal

project = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
lib = unreal.EditorAssetLibrary
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if not levels.load_level("/Game/Vesper/Maps/MountainPilgrimage"):
    raise RuntimeError("Cannot load pilgrimage")
folder = "/Game/Vesper/HighlandSky"
tools = unreal.AssetToolsHelpers.get_asset_tools()
cube_path = folder + "/MountainOvercast"
if not lib.does_asset_exist(cube_path):
    imp = unreal.AssetImportTask()
    imp.filename = str(project / "Art" / "MountainOvercast.hdr")
    imp.destination_path = folder
    imp.automated = imp.save = True
    tools.import_asset_tasks([imp])
cube = lib.load_asset(cube_path)
if not isinstance(cube, unreal.TextureCube):
    raise TypeError("Expected a longitude-latitude HDR cubemap")
mat_path = folder + "/CloudVault"
edit = unreal.MaterialEditingLibrary
if lib.does_asset_exist(mat_path):
    mat = lib.load_asset(mat_path)
    edit.delete_all_material_expressions(mat)
else:
    mat = tools.create_asset(
        "CloudVault", folder, unreal.Material, unreal.MaterialFactoryNew()
    )
mat.set_editor_property("two_sided", True)
mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
mat.set_editor_property("is_sky", True)


def node(cls, x):
    return edit.create_material_expression(mat, cls, x, 0)


def connect(a, out, b, pin):
    if not edit.connect_material_expressions(a, out, b, pin):
        raise RuntimeError("Invalid sky graph connection " + pin)


view = node(unreal.MaterialExpressionCameraVectorWS, -600)
neg = node(unreal.MaterialExpressionMultiply, -400)
neg.set_editor_property("const_b", -1)
connect(view, "", neg, "A")
sample = node(unreal.MaterialExpressionTextureSample, -200)
sample.set_editor_property("texture", cube)
sample.set_editor_property(
    "sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR
)
connect(neg, "", sample, "UVs")
if not edit.connect_material_property(
    sample, "RGB", unreal.MaterialProperty.MP_EMISSIVE_COLOR
):
    raise RuntimeError("Cannot connect sky radiance")
edit.recompile_material(mat)
if not lib.save_loaded_asset(mat, only_if_is_dirty=False):
    raise RuntimeError("Cannot save sky material")

scene = actors.get_all_level_actors()
for actor in scene:
    if actor.get_actor_label() in (
        "Mountain cloud vault",
        "Mountain exposure",
        "Cloudbank bounce",
    ):
        actors.destroy_actor(actor)


def one(cls):
    matches = [
        a
        for a in actors.get_all_level_actors()
        if isinstance(a, cls) and "VesperStoneBounce" not in a.tags
    ]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one {cls}: {len(matches)}")
    return matches[0]


sun = one(unreal.DirectionalLight)
sun.set_actor_rotation(unreal.Rotator(0, -26, 32), False)
sun.light_component.set_editor_property("atmosphere_sun_light", False)
sun.light_component.set_editor_property("forward_shading_priority", 1)
sun.light_component.set_editor_property("intensity", 3.4)
sun.light_component.set_editor_property("light_source_angle", 2.3)
sun.light_component.set_light_color(unreal.LinearColor(1, 0.86, 0.66, 1))
sky = one(unreal.SkyLight).get_component_by_class(unreal.SkyLightComponent)
sky.set_mobility(unreal.ComponentMobility.MOVABLE)
sky.set_editor_property("real_time_capture", False)
sky.set_editor_property("source_type", unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
sky.set_cubemap(cube)
sky.set_intensity(5.0)
sky.set_editor_property("lower_hemisphere_is_black", False)
# Broad cool light from the open side of the valley restores texture in the key's shadows.
bounce = actors.spawn_actor_from_class(
    unreal.DirectionalLight, unreal.Vector(0, 0, 2000), unreal.Rotator(0, -55, -118)
)
bounce.set_actor_label("Cloudbank bounce")
bounce.light_component.set_editor_property("atmosphere_sun_light", False)
bounce.light_component.set_editor_property("cast_shadows", False)
bounce.light_component.set_editor_property("intensity", 1.55)
bounce.light_component.set_light_color(unreal.LinearColor(0.67, 0.81, 1, 1))
fog = one(unreal.ExponentialHeightFog).get_component_by_class(
    unreal.ExponentialHeightFogComponent
)
fog.set_editor_property("fog_density", 0.012)
fog.set_editor_property("fog_height_falloff", 0.27)
fog.set_editor_property("start_distance", 1700)
fog.set_editor_property("fog_max_opacity", 0.63)
fog.set_editor_property(
    "fog_inscattering_luminance", unreal.LinearColor(0.048, 0.066, 0.085, 1)
)
atmosphere = one(unreal.SkyAtmosphere)
atmosphere.get_component_by_class(unreal.SkyAtmosphereComponent).set_visibility(False)
dome = actors.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(9700, 0, 0))
dome.set_actor_label("Mountain cloud vault")
dome.set_actor_scale3d(unreal.Vector(2100, 2100, 2100))
dome.static_mesh_component.set_static_mesh(
    lib.load_asset("/Engine/BasicShapes/Sphere.Sphere")
)
dome.static_mesh_component.set_material(0, mat)
dome.static_mesh_component.set_editor_property("cast_shadow", False)
dome.static_mesh_component.set_editor_property("visible_in_ray_tracing", False)
dome.set_actor_enable_collision(False)
volume = actors.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector(0, 0, 0))
volume.set_actor_label("Mountain exposure")
volume.set_editor_property("unbound", True)
volume.set_editor_property("priority", 1)
settings = volume.get_editor_property("settings")
for k, v in {
    "auto_exposure_min_brightness": 0.2,
    "auto_exposure_max_brightness": 1.6,
    "auto_exposure_bias": 0.0,
    "bloom_intensity": 0.19,
    "vignette_intensity": 0.22,
}.items():
    settings.set_editor_property("override_" + k, True)
    settings.set_editor_property(k, v)
volume.set_editor_property("settings", settings)
# Interchange's summit-pine material has no colour texture. Restore the
# baked branch colours and keep a dark pine tone even on white import vertices.
ridge_path = folder + "/SummitNeedles"
if lib.does_asset_exist(ridge_path):
    needles = lib.load_asset(ridge_path)
    edit.delete_all_material_expressions(needles)
else:
    needles = tools.create_asset(
        "SummitNeedles", folder, unreal.Material, unreal.MaterialFactoryNew()
    )
needles.set_editor_property("two_sided", True)
vertex = edit.create_material_expression(
    needles, unreal.MaterialExpressionVertexColor, -400, 0
)
tint = edit.create_material_expression(
    needles, unreal.MaterialExpressionConstant3Vector, -400, 160
)
tint.set_editor_property("constant", unreal.LinearColor(0.12, 0.18, 0.16, 1))
mul = edit.create_material_expression(
    needles, unreal.MaterialExpressionMultiply, -150, 0
)
connect(vertex, "", mul, "A")
connect(tint, "", mul, "B")
if not edit.connect_material_property(mul, "", unreal.MaterialProperty.MP_BASE_COLOR):
    raise RuntimeError("Cannot connect summit pine colour")
edit.recompile_material(needles)
if not lib.save_loaded_asset(needles, only_if_is_dirty=False):
    raise RuntimeError("Cannot save summit pine material")
ridge_count = 0
for actor in actors.get_all_level_actors():
    if actor.get_actor_label().startswith("Distant ridge Summit_pines"):
        actor.static_mesh_component.set_material(0, needles)
        ridge_count += 1
if ridge_count != 3:
    raise RuntimeError(f"Expected three summit pine groups, found {ridge_count}")
if not levels.save_current_level():
    raise RuntimeError("Cannot save mountain lighting")
report = {
    "sky": cube.get_path_name(),
    "summit_pine_groups": ridge_count,
    "sun_lux": 3.4,
    "sun_forward_priority": sun.light_component.get_editor_property("forward_shading_priority"),
    "skylight_intensity": 5.0,
    "bounce_lux": 1.55,
    "fog_density": 0.012,
    "fog_start_cm": 1700,
    "exposure_ev100": [0.2, 1.6],
}
(project / "Saved" / "MountainEvening.json").write_text(json.dumps(report, indent=2))
unreal.log("VESPER_MOUNTAIN_EVENING " + str(report))
