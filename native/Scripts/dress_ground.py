"""Apply landscape-scale paths and damp seams over scanned undergrowth materials."""

import json
import math
import runpy
from pathlib import Path
from random import Random

import unreal

project = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
sources = project / "Art" / "Understory"
folder = "/Game/Vesper/Understory"
lib = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
edit = unreal.MaterialEditingLibrary
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if not levels.load_level("/Game/Vesper/Maps/MountainPilgrimage"):
    raise RuntimeError("Cannot load the valley map")


def texture(name, path, kind):
    target = folder + "/" + name
    if lib.does_asset_exist(target):
        tex = lib.load_asset(target)
    else:
        task = unreal.AssetImportTask()
        task.filename = str(path)
        task.destination_name = name
        task.destination_path = folder
        task.automated = task.save = True
        tools.import_asset_tasks([task])
        tex = lib.load_asset(target)
    if not isinstance(tex, unreal.Texture2D):
        raise TypeError("Missing ground map " + name)
    tex.set_editor_property("srgb", kind == "Color")
    if kind == "Normal":
        tex.set_editor_property(
            "compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP
        )
    elif kind in ("Rough", "Mask"):
        tex.set_editor_property(
            "compression_settings", unreal.TextureCompressionSettings.TC_MASKS
        )
    if kind == "Mask":
        tex.set_editor_property("address_x", unreal.TextureAddress.TA_CLAMP)
        tex.set_editor_property("address_y", unreal.TextureAddress.TA_CLAMP)
    lib.save_loaded_asset(tex, only_if_is_dirty=False)
    return tex


target = folder + "/ValleyUnderfoot"
if lib.does_asset_exist(target):
    material = lib.load_asset(target)
    edit.delete_all_material_expressions(material)
else:
    material = tools.create_asset(
        "ValleyUnderfoot", folder, unreal.Material, unreal.MaterialFactoryNew()
    )


def node(cls, x, y):
    return edit.create_material_expression(material, cls, x, y)


def link(source, output, target, pin):
    if not edit.connect_material_expressions(source, output, target, pin):
        raise RuntimeError(f"Cannot connect {output} to {pin}")


def scalar_scale(source, factor, x, y):
    m = node(unreal.MaterialExpressionMultiply, x, y)
    m.set_editor_property("const_b", factor)
    link(source, "", m, "A")
    return m


def sample(name, path, kind, uv, x, y):
    n = node(unreal.MaterialExpressionTextureSample, x, y)
    n.set_editor_property("texture", texture(name, path, kind))
    n.set_editor_property(
        "sampler_type",
        {
            "Color": unreal.MaterialSamplerType.SAMPLERTYPE_COLOR,
            "Normal": unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL,
            "Mask": unreal.MaterialSamplerType.SAMPLERTYPE_MASKS,
            "Rough": unreal.MaterialSamplerType.SAMPLERTYPE_MASKS,
        }[kind],
    )
    link(uv, "", n, "UVs")
    return n


def mix(a, ach, b, bch, mask, channel, x, y):
    m = node(unreal.MaterialExpressionLinearInterpolate, x, y)
    link(a, ach, m, "A")
    link(b, bch, m, "B")
    link(mask, channel, m, "Alpha")
    return m


def constant(v, x, y):
    n = node(unreal.MaterialExpressionConstant3Vector, x, y)
    n.set_editor_property("constant", unreal.LinearColor(*v, 1))
    return n


world = node(unreal.MaterialExpressionWorldPosition, -1400, 0)
xy = node(unreal.MaterialExpressionComponentMask, -1230, 0)
xy.set_editor_property("R", True)
xy.set_editor_property("G", True)
link(world, "", xy, "")
origin = node(unreal.MaterialExpressionConstant2Vector, -1200, -220)
origin.set_editor_property("r", 11900)
origin.set_editor_property("g", 21600)
shift = node(unreal.MaterialExpressionAdd, -980, -150)
link(xy, "", shift, "A")
link(origin, "", shift, "B")
mask = sample(
    "ValleyPaths",
    sources / "ValleyPaths.png",
    "Mask",
    scalar_scale(shift, 1 / 43200, -810, -160),
    -590,
    -160,
)
layers = []
for i, (tag, prefix, span) in enumerate(
    [
        ("forest_floor", "Litter", 210),
        ("forest_ground_04", "Trail", 307),
        ("rock", "Shale", 318),
    ]
):
    uv = scalar_scale(xy, 1 / span, -910, 280 + i * 620)
    textures = {}
    for j, kind in enumerate(("Color", "Normal", "Rough")):
        path = (
            sources / (tag + "_" + kind + ".jpg")
            if tag != "rock"
            else project / "SourceAssets" / ("rock-" + kind.lower() + ".jpg")
        )
        textures[kind] = sample(
            prefix + kind, path, kind, uv, -650, 280 + i * 620 + j * 190
        )
    layers.append(textures)
# Low-albedo, smooth rock appears chiefly in the valley's drainage hollows.
wet = node(unreal.MaterialExpressionMultiply, -240, 1540)
link(layers[2]["Color"], "RGB", wet, "A")
link(constant((0.36, 0.45, 0.45), -450, 1520), "", wet, "B")
sheen = node(unreal.MaterialExpressionMultiply, -230, 1860)
sheen.set_editor_property("const_b", 0.48)
link(layers[2]["Rough"], "R", sheen, "A")
mod = mix(
    constant((0.60, 0.64, 0.52), -100, -140),
    "",
    constant((1.12, 1.04, 0.88), -100, -30),
    "",
    mask,
    "B",
    120,
    -80,
)
for j, (kind, mp) in enumerate(
    [
        ("Color", unreal.MaterialProperty.MP_BASE_COLOR),
        ("Normal", unreal.MaterialProperty.MP_NORMAL),
        ("Rough", unreal.MaterialProperty.MP_ROUGHNESS),
    ]
):
    port = "R" if kind == "Rough" else "RGB"
    base = mix(layers[0][kind], port, layers[1][kind], port, mask, "R", 0, 320 * j)
    rock = {"Color": wet, "Rough": sheen}.get(kind, layers[2][kind])
    merged = mix(
        base, "", rock, "RGB" if kind == "Normal" else "", mask, "G", 220, 320 * j
    )
    result = merged
    if kind == "Color":
        result = node(unreal.MaterialExpressionMultiply, 450, 0)
        link(merged, "", result, "A")
        link(mod, "", result, "B")
    elif kind == "Normal":
        result = node(unreal.MaterialExpressionNormalize, 450, 320)
        link(merged, "", result, "")
    if not edit.connect_material_property(result, "", mp):
        raise RuntimeError("Missing " + kind)
edit.recompile_material(material)
if not lib.save_loaded_asset(material, only_if_is_dirty=False):
    raise RuntimeError("Cannot save forest-floor material")
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
floor = next(
    a for a in actors.get_all_level_actors() if a.get_actor_label() == "Valley floor"
)
floor.static_mesh_component.set_material(0, material)
ground = runpy.run_path(str(project / "Scripts" / "valley_surface.py"))["sampler"](
    project, floor
)
fern_folder = folder + "/Ferns"
if not lib.does_directory_exist(fern_folder):
    imp = unreal.AssetImportTask()
    imp.filename = str(sources / "ValleyFern.glb")
    imp.destination_path = fern_folder
    imp.automated = imp.save = True
    tools.import_asset_tasks([imp])
paths = [
    p
    for p in lib.list_assets(fern_folder)
    if str(lib.find_asset_data(p).asset_class_path.asset_name) == "StaticMesh"
]
if len(paths) != 1:
    raise RuntimeError("Expected one fern mesh")
fern = lib.load_asset(paths[0])
settings = fern.get_editor_property("nanite_settings")
settings.set_editor_property("enabled", False)
fern.set_editor_property("nanite_settings", settings)
lib.save_loaded_asset(fern, only_if_is_dirty=False)
for a in actors.get_all_level_actors():
    if a.get_actor_label().startswith("Understory fern"):
        actors.destroy_actor(a)
# Cluster along both banks of each flight and among the pines. Leave the central
# three-metre walking lane and the existing stair collision clear.
rng = Random(8179)
centres = []
flights = [(4200, 0), (11500, 1600), (19400, -800)]
for fx, fy in flights:
    for side in (-1, 1):
        for offset in (-1740, -2210, -2630, -3120):
            centres.append((fx + side * rng.uniform(255, 530), fy + offset))
for tree in sorted(actors.get_all_level_actors(), key=lambda a: a.get_actor_label()):
    if tree.get_actor_label().startswith("Mountain pine") and rng.random() < 0.48:
        pos = tree.get_actor_location()
        centres.append((pos.x + 120, pos.y - 70))
centres.extend([(950, 1380), (1280, 1460), (1560, 1230), (710, 1250)])
count = 0
for cx, cy in centres:
    for _ in range(rng.randint(2, 5)):
        theta = rng.random() * math.tau
        radius = rng.uniform(20, 135)
        x, y = cx + math.cos(theta) * radius, cy + math.sin(theta) * radius
        if any(abs(x - sx) < 200 and sy - 3200 < y < sy - 1100 for sx, sy in flights):
            continue
        a = actors.spawn_actor_from_class(
            unreal.StaticMeshActor,
            unreal.Vector(x, y, ground(x, y) - 1.5),
            unreal.Rotator(0, 0, rng.uniform(-180, 180)),
        )
        a.static_mesh_component.set_static_mesh(fern)
        a.set_actor_label("Understory fern")
        scale = rng.uniform(0.64, 1.53)
        a.set_actor_scale3d(
            unreal.Vector(scale, scale, scale * rng.uniform(0.85, 1.13))
        )
        a.set_actor_enable_collision(False)
        count += 1
if not levels.save_current_level():
    raise RuntimeError("Cannot save the ground surface")
report = {
    "surface": material.get_path_name(),
    "ferns": count,
    "floor": floor.static_mesh_component.static_mesh.get_path_name(),
    "control_width_m": 432,
    "scan_widths_m": [2.10, 3.07, 3.18],
}
(project / "Saved" / "Understory.json").write_text(json.dumps(report, indent=2))
unreal.log("VESPER_UNDERSTORY_SAVED " + str(report))
