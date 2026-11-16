"""Seat the painted threshold on the east side of the usable route and hang the bell."""

from pathlib import Path
import json
from math import cos, radians, sin
import sys

import unreal

project = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
sys.path.insert(0, str(project / "Scripts"))
import belfry_hall_mesh

lib = unreal.EditorAssetLibrary
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
tools = unreal.AssetToolsHelpers.get_asset_tools()
level = "/Game/Vesper/Maps/MountainPilgrimage"
base = "/Game/Vesper/RouteArt/BellHall"
edit = unreal.MaterialEditingLibrary
prop = unreal.MaterialProperty


def geometry(name, source):
    folder = base + "/" + name
    if not lib.does_directory_exist(folder):
        task = unreal.AssetImportTask()
        task.filename, task.destination_path = str(source), folder
        task.automated = task.save = True
        tools.import_asset_tasks([task])
    return [
        lib.load_asset(p)
        for p in lib.list_assets(folder)
        if str(lib.find_asset_data(p).asset_class_path.asset_name) == "StaticMesh"
    ]


def finish(name, texture, tint, rough, metal=0, normal=None, vertex=False, emission=0):
    folder = base + "/Surfaces"
    path = folder + "/" + name
    if lib.does_asset_exist(path):
        mat = lib.load_asset(path)
        edit.set_base_material_usage(mat, unreal.MaterialUsage.MATUSAGE_NANITE, True)
        edit.recompile_material(mat)
        lib.save_loaded_asset(mat, only_if_is_dirty=False)
        return mat
    mat = tools.create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())
    mat.set_editor_property("two_sided", True)
    edit.set_base_material_usage(mat, unreal.MaterialUsage.MATUSAGE_NANITE, True)

    def node(cls, x, y):
        return edit.create_material_expression(mat, cls, x, y)

    def wire(a, p, b, q):
        if not edit.connect_material_expressions(a, p, b, q):
            raise RuntimeError("Unconnected material expression in " + name)

    def channel(a, p, target):
        if not edit.connect_material_property(a, p, target):
            raise RuntimeError("Unconnected channel in " + name)

    def sample(asset, y, kind):
        tex = lib.load_asset(texroot + asset)
        if not tex:
            raise RuntimeError("Missing hall texture " + asset)
        item = node(unreal.MaterialExpressionTextureSample, -800, y)
        item.set_editor_property("texture", tex)
        item.set_editor_property("sampler_type", kind)
        return item

    rgb = sample(texture, 0, unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
    dye = node(unreal.MaterialExpressionConstant3Vector, -800, 170)
    dye.set_editor_property("constant", unreal.LinearColor(*tint, 1))
    dyed = node(unreal.MaterialExpressionMultiply, -540, 0)
    wire(rgb, "RGB", dyed, "A")
    wire(dye, "", dyed, "B")
    if vertex:
        colors = node(unreal.MaterialExpressionVertexColor, -530, 190)
        product = node(unreal.MaterialExpressionMultiply, -310, 0)
        wire(dyed, "", product, "A")
        wire(colors, "", product, "B")
        dyed = product
    channel(dyed, "", prop.MP_BASE_COLOR)
    if emission:
        glow = node(unreal.MaterialExpressionMultiply, -145, 200)
        glow.set_editor_property("const_b", emission)
        wire(dyed, "", glow, "A")
        channel(glow, "", prop.MP_EMISSIVE_COLOR)
    if normal:
        channel(
            sample(normal, -200, unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL),
            "RGB",
            prop.MP_NORMAL,
        )
    for i, (value, target) in enumerate(
        [(rough, prop.MP_ROUGHNESS), (metal, prop.MP_METALLIC)]
    ):
        scalar = node(unreal.MaterialExpressionConstant, -190, 370 + i * 110)
        scalar.set_editor_property("r", value)
        channel(scalar, "", target)
    edit.recompile_material(mat)
    if not lib.save_loaded_asset(mat, only_if_is_dirty=False):
        raise RuntimeError("Cannot save " + name)
    return mat


if not levels.load_level(level):
    raise RuntimeError("Missing mountain route")
output = project / "Saved" / "BellChamber.glb"
belfry_hall_mesh.bake(project / "SourceAssets", output)
parts = geometry("BellChamber", output)
bell = geometry("Casting", project / "SourceAssets" / "tide-bell.glb")
if len(parts) != 8 or len(bell) != 1:
    raise RuntimeError(f"Unexpected hall geometry: {len(parts)} + {len(bell)}")
texroot = parts[0].get_path_name().split("/StaticMeshes/")[0] + "/Textures/"


def textured(name, color, normal, rough, metal=0, vertex=True, tint=(1, 1, 1)):
    return finish(
        name,
        color + "Color",
        tint,
        rough,
        metal,
        normal + "Normal" if normal else None,
        vertex,
    )


masonry = textured("CutTerrace", "Terrace_masonry", "Terrace_masonry", 0.85)
cedar = textured("Cedar", "Smoke_aged_cedar", "Smoke_aged_cedar", 0.78)
kiln = textured("Kiln", "Kiln_tiles", "Kiln_tiles", 0.57)
gilt = textured("Bronze", "Cast_ridge_bronze", "Cast_ridge_bronze", 0.58, 0.55)
fresco = finish("Dragons", "Paired_dragon_fasciaColor", (1, 0.86, 0.71), 0.78)
silk = finish(
    "WindowPaper",
    "Clerestory_silkColor",
    (1, 0.72, 0.42),
    0.92,
    vertex=True,
    emission=0.58,
)
coatings = {
    "Kiln_tiles": kiln,
    "Terrace_masonry": masonry,
    "Smoke_aged_cedar": cedar,
    "Paired_dragon_fascia": fresco,
    "Cast_ridge_bronze": gilt,
    "Sanctum_screen": finish(
        "Sanctum", "Sanctum_screenColor", (1, 0.89, 0.73), 0.76, emission=0.24
    ),
    "Bell_hall_tablet": finish(
        "Inscription", "Bell_hall_tabletColor", (0.96, 0.84, 0.62), 0.66, emission=0.12
    ),
    "Clerestory_silk": silk,
}
stone = textured(
    "LampStone",
    "Terrace_masonry",
    "Terrace_masonry",
    0.85,
    vertex=False,
    tint=(0.48, 0.55, 0.52),
)
lacquer = textured(
    "OxideTimber",
    "Smoke_aged_cedar",
    "Smoke_aged_cedar",
    0.67,
    vertex=False,
    tint=(0.52, 0.225, 0.14),
)
glaze = textured(
    "GalleryGlaze",
    "Kiln_tiles",
    "Kiln_tiles",
    0.50,
    vertex=False,
    tint=(0.22, 0.38, 0.34),
)
metal = textured(
    "Patina",
    "Cast_ridge_bronze",
    "Cast_ridge_bronze",
    0.59,
    0.68,
    False,
    (0.55, 0.56, 0.45),
)
existing = {
    "Stone_footing": stone,
    "Carved_grey_stone": stone,
    "Carved_column_plinth": stone,
    "Red_lacquer_timber": lacquer,
    "Oxide-red_posts": lacquer,
    "Celadon_tiles": glaze,
    "Patinated_bronze": metal,
    "Paired_dragons_on_the_tie_beam": fresco,
}
# glTF +Z faces local UE +Y. At yaw 62 the terrace faces the player's
# approach. Its front steps sit off the road on the north side of the bend.
origin = unreal.Vector(6150, -1160, 8)
rot = unreal.Rotator(yaw=62)
for a in actors.get_all_level_actors():
    if a.actor_has_tag("VesperBellHall"):
        actors.destroy_actor(a)
        continue
    if not isinstance(a, unreal.StaticMeshActor):
        continue
    comp = a.static_mesh_component
    mesh = comp.static_mesh
    if not mesh:
        continue
    path = mesh.get_path_name()
    if "/BelfryPaintedFront/" in path:
        a.set_actor_location_and_rotation(origin, rot, False, True)
    if not any(
        k in path
        for k in ("/WestWaterGallery/", "/ProcessionLantern/", "/BelfryPaintedFront/")
    ):
        continue
    for i, s in enumerate(mesh.static_materials):
        mat = existing.get(str(s.material_slot_name))
        if mat:
            comp.set_material(i, mat)


def place(mesh, pos, scale=1):
    a = actors.spawn_actor_from_class(unreal.StaticMeshActor, pos, rot)
    a.tags = ["VesperBellHall"]
    a.set_actor_label("Bell hall " + mesh.get_name())
    a.static_mesh_component.set_static_mesh(mesh)
    a.set_actor_scale3d(unreal.Vector(scale, scale, scale))
    a.set_actor_enable_collision(False)
    return a


for mesh in parts:
    a = place(mesh, origin)
    if any(
        str(s.material_slot_name) in {"Terrace_masonry", "Smoke_aged_cedar"}
        for s in mesh.static_materials
    ):
        body = mesh.get_editor_property("body_setup")
        body.set_editor_property(
            "collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE
        )
        lib.save_loaded_asset(mesh, only_if_is_dirty=False)
        a.static_mesh_component.set_collision_profile_name("BlockAll")
        a.set_actor_enable_collision(True)
    for i, slot in enumerate(mesh.static_materials):
        a.static_mesh_component.set_material(i, coatings[str(slot.material_slot_name)])
# Cast bell hangs inside the portico, clear of the alcove's painted screen.
a = place(
    bell[0],
    origin
    + unreal.Vector(-70 * sin(radians(rot.yaw)), 70 * cos(radians(rot.yaw)), 178),
    1.34,
)
a.static_mesh_component.set_material(0, metal)
if not levels.save_current_level():
    raise RuntimeError("Failed to save bell hall")
(project / "Saved" / "BellHall.json").write_text(
    json.dumps({"revision": 1, "chamber_parts": len(parts), "bell": bell[0].get_name()})
)
unreal.log("VESPER_BELL_HALL_SAVED")
