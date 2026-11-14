"""Enclose the exposed west approach with forested foothills and limestone spurs."""

import json
import math
from pathlib import Path
from random import Random
import sys
import unreal

project = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
sys.path.insert(0, str(project / "Scripts"))
import forest_canopy
from karst_spur import bake
from valley_surface import sampler

lib = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
edit = unreal.MaterialEditingLibrary
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if not levels.load_level("/Game/Vesper/Maps/MountainPilgrimage"):
    raise RuntimeError("Cannot load the mountain route")
scene = actors.get_all_level_actors()
floor = next(a for a in scene if a.get_actor_label() == "Valley floor")
ground = sampler(project, floor)
folder = "/Game/Vesper/WestPass"
for a in scene:
    if a.actor_has_tag("WestPass"):
        actors.destroy_actor(a)


def link(src, pin, dst, socket):
    if not edit.connect_material_expressions(src, pin, dst, socket):
        raise RuntimeError("Disconnected mountain material input " + socket)


def limestone():
    path = folder + "/RainwashedLimestone"
    if lib.does_asset_exist(path):
        mat = lib.load_asset(path)
        edit.delete_all_material_expressions(mat)
    else:
        mat = tools.create_asset(
            "RainwashedLimestone", folder, unreal.Material, unreal.MaterialFactoryNew()
        )

    def node(cls, x, y):
        return edit.create_material_expression(mat, cls, x, y)

    def sample(name, kind, x, y):
        tex = lib.load_asset("/Game/Vesper/Understory/Shale" + name)
        if not tex:
            raise RuntimeError("Missing scanned shale " + name)
        s = node(unreal.MaterialExpressionTextureSample, x, y)
        s.set_editor_property("texture", tex)
        s.set_editor_property("sampler_type", kind)
        return s

    albedo = sample("Color", unreal.MaterialSamplerType.SAMPLERTYPE_COLOR, -600, 0)
    color = node(unreal.MaterialExpressionDesaturation, -400, 0)
    intensity = node(unreal.MaterialExpressionConstant, -590, 100)
    intensity.set_editor_property("r", 0.78)
    link(intensity, "", color, "Fraction")
    link(albedo, "RGB", color, "")
    vertex = node(unreal.MaterialExpressionVertexColor, -400, 140)
    mul = node(unreal.MaterialExpressionMultiply, -170, 0)
    link(color, "", mul, "A")
    link(vertex, "", mul, "B")
    n = sample("Normal", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL, -180, 230)
    rough = sample("Rough", unreal.MaterialSamplerType.SAMPLERTYPE_MASKS, -180, 430)
    for src, pin, prop in [
        (mul, "", unreal.MaterialProperty.MP_BASE_COLOR),
        (n, "RGB", unreal.MaterialProperty.MP_NORMAL),
        (rough, "R", unreal.MaterialProperty.MP_ROUGHNESS),
    ]:
        if not edit.connect_material_property(src, pin, prop):
            raise RuntimeError("Incomplete cliff material")
    edit.recompile_material(mat)
    lib.save_loaded_asset(mat, only_if_is_dirty=False)
    return mat


def spur(name, seed):
    dest = folder + "/" + name
    if not lib.does_directory_exist(dest):
        source = project / "Saved" / (name + ".glb")
        bake(source, seed)
        task = unreal.AssetImportTask()
        task.filename, task.destination_path = str(source), dest
        task.save = task.automated = True
        tools.import_asset_tasks([task])
    return next(
        lib.load_asset(p)
        for p in lib.list_assets(dest)
        if str(lib.find_asset_data(p).asset_class_path.asset_name) == "StaticMesh"
    )


def place(mesh, label, pos, yaw, scale):
    a = actors.spawn_actor_from_class(
        unreal.StaticMeshActor, unreal.Vector(*pos), unreal.Rotator(yaw=yaw)
    )
    a.tags = ["WestPass"]
    a.set_actor_label(label)
    c = a.static_mesh_component
    c.set_static_mesh(mesh)
    c.set_editor_property("disallow_nanite", True)
    a.set_actor_scale3d(unreal.Vector(*scale))
    a.set_actor_enable_collision(False)
    return a


peaks = [spur("FoldedSpur", 112), spur("SplitSpur", 421)]
mat = limestone()
# In front of the western valley rim, stagger near shoulders and distant heads.
for i, (x, y, z, yaw, s, h) in enumerate(
    [
        (-13800, -8200, -180, 64, 1.62, 1.14),
        (-10250, 3600, -520, 88, 1.25, 1.05),
        (-10800, 13700, -280, 30, 1.32, 1.02),
        (-6900, -15700, -330, 5, 1.21, 0.86),
        (-22400, -10400, 60, 45, 2.02, 2.18),
        (-24100, 3900, 470, 106, 1.94, 2.26),
        (-21100, 17300, 240, 27, 1.86, 1.64),
        (3200, 20600, -350, 7, 1.28, 1.14),
        (14500, -21500, -800, -9, 1.68, 1.55),
    ]
):
    a = place(peaks[i % 2], "West pass limestone spur", (x, y, z), yaw, (s, s, h))
    a.static_mesh_component.set_material(0, mat)
# Irregular stands trace the foot of the pass and leave clearings in the gullies.
pine_paths = lib.list_assets("/Game/Vesper/RouteArt/MountainPines")
pines = [
    lib.load_asset(p)
    for p in pine_paths
    if str(lib.find_asset_data(p).asset_class_path.asset_name) == "StaticMesh"
]
if len(pines) != 2:
    raise RuntimeError("Missing mountain pine forms")
rng = Random(6519)
trees = []
for mesh in pines:
    for cx, cy, radius in [
        (-3700, -2800, 1800),
        (-7300, -1610, 2100),
        (-6100, 6200, 2500),
        (-9100, -8300, 1600),
        (-3200, 10700, 2400),
        (-8800, 2500, 1700),
    ]:
        for _ in range(9):
            a0 = rng.uniform(0, math.tau)
            distance = math.sqrt(rng.random()) * radius
            x, y = cx + distance * math.cos(a0), cy + distance * math.sin(a0)
            z = ground(x, y)
            scale = rng.uniform(0.56, 1.16)
            tree = place(
                mesh,
                "Western pine stand",
                (x, y, z - 12),
                rng.uniform(-180, 180),
                (scale, scale, scale * rng.uniform(0.91, 1.1)),
            )
            tree.static_mesh_component.set_editor_property("cast_shadow", False)
            trees.append((x, y, scale))
rock = lib.load_asset(
    "/Game/Vesper/RouteArt/PassOutcrop/rock_face_01/StaticMeshes/rock_face_01"
)
if not rock:
    raise RuntimeError("Missing scanned pass outcrop")
rocks = 0
for cx, cy, bearing in [
    (-1700, 1100, 55),
    (-3600, 2600, 102),
    (-2200, -2200, -62),
    (-7000, 7200, 17),
    (-4900, 4900, 70),
]:
    for j in range(5):
        x = cx + 230 * j * math.cos(math.radians(bearing)) + rng.uniform(-100, 100)
        y = cy + 230 * j * math.sin(math.radians(bearing)) + rng.uniform(-95, 95)
        scale = rng.uniform(0.72, 1.63)
        place(
            rock,
            "Western fractured bedrock",
            (x, y, ground(x, y) - 85),
            bearing + rng.uniform(-27, 27),
            (1.5 * scale, 0.94 * scale, scale),
        )
        rocks += 1
# The existing valley material already blends three scans with metre-scale normals.
# Duplicate it so this pass can modulate its albedo without rebuilding the rest.
underfoot = "/Game/Vesper/Understory/ValleyUnderfoot"
path = folder + "/ForestUnderfoot"
material = (
    lib.load_asset(path)
    if lib.does_asset_exist(path)
    else lib.duplicate_asset(underfoot, path)
)
mask_path = folder + "/NeedleBeds"
if not lib.does_asset_exist(mask_path):
    source = project / "Saved" / "NeedleBeds.png"
    local_trees = []
    for a in scene:
        if unreal.SystemLibrary.is_valid(a) and a.get_actor_label().startswith(
            "Mountain pine"
        ):
            pt = a.get_actor_location()
            local_trees.append((pt.x, pt.y, a.get_actor_scale3d().x))
    forest_canopy.bake(source, trees + local_trees)
    imp = unreal.AssetImportTask()
    imp.filename, imp.destination_path = str(source), folder
    imp.automated = imp.save = True
    tools.import_asset_tasks([imp])
tex = lib.load_asset(mask_path)
tex.set_editor_property("srgb", False)
tex.set_editor_property(
    "compression_settings", unreal.TextureCompressionSettings.TC_MASKS
)
tex.set_editor_property("address_x", unreal.TextureAddress.TA_CLAMP)
tex.set_editor_property("address_y", unreal.TextureAddress.TA_CLAMP)
lib.save_loaded_asset(tex, only_if_is_dirty=False)
base = edit.get_material_property_input_node(
    material, unreal.MaterialProperty.MP_BASE_COLOR
)
if not base:
    raise RuntimeError("Missing valley diffuse input")
if base.get_editor_property("desc") != "Valley canopy tint":

    def node(cls, x, y):
        return edit.create_material_expression(material, cls, x, y)

    world = node(unreal.MaterialExpressionWorldPosition, 0, -690)
    xy = node(unreal.MaterialExpressionComponentMask, 180, -690)
    xy.set_editor_property("r", True)
    xy.set_editor_property("g", True)
    link(world, "", xy, "")
    offset = node(unreal.MaterialExpressionConstant2Vector, 160, -520)
    offset.set_editor_property("r", 11900)
    offset.set_editor_property("g", 21600)
    add = node(unreal.MaterialExpressionAdd, 360, -690)
    link(xy, "", add, "A")
    link(offset, "", add, "B")
    scale = node(unreal.MaterialExpressionMultiply, 530, -690)
    scale.set_editor_property("const_b", 1 / 43200)
    link(add, "", scale, "A")
    sample = node(unreal.MaterialExpressionTextureSample, 730, -690)
    sample.set_editor_property("texture", tex)
    sample.set_editor_property(
        "sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_MASKS
    )
    link(scale, "", sample, "UVs")
    result = node(unreal.MaterialExpressionMultiply, 950, 0)
    result.set_editor_property("desc", "Valley canopy tint")
    link(sample, "RGB", result, "A")
    link(base, "", result, "B")
    if not edit.connect_material_property(
        result, "", unreal.MaterialProperty.MP_BASE_COLOR
    ):
        raise RuntimeError("Could not connect valley diffuse")
    edit.recompile_material(material)
    lib.save_loaded_asset(material, only_if_is_dirty=False)
floor.static_mesh_component.set_material(0, material)
floor.static_mesh_component.set_editor_property("disallow_nanite", True)
if not levels.save_current_level():
    raise RuntimeError("Could not save the mountain pass")
(project / "Saved" / "WestPass.json").write_text(
    json.dumps(dict(spurs=9, pines=len(trees), outcrops=rocks))
)
unreal.log("VESPER_WEST_PASS_READY")
