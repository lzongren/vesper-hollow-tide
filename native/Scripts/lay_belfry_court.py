"""Replace the oversized painted forecourt with dressed stone and a small bronze seal."""

import json
import sys
from pathlib import Path

import unreal

project = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
sys.path.insert(0, str(project / "Scripts"))
from court_pavement import bake

lib = unreal.EditorAssetLibrary
edit = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
root = "/Game/Vesper/RouteArt/BelfryPavement"
prop = unreal.MaterialProperty


def slab_surface():
    path = root + "/HewnSlate"
    if lib.does_asset_exist(path):
        mat = lib.load_asset(path)
        edit.delete_all_material_expressions(mat)
    else:
        mat = tools.create_asset(
            "HewnSlate", root, unreal.Material, unreal.MaterialFactoryNew()
        )
    edit.set_base_material_usage(mat, unreal.MaterialUsage.MATUSAGE_NANITE, True)

    def node(cls, x, y):
        return edit.create_material_expression(mat, cls, x, y)

    def wire(a, out, b, pin):
        if not edit.connect_material_expressions(a, out, b, pin):
            raise RuntimeError(f"Cannot connect {out} to {pin}")

    def channel(a, out, target):
        if not edit.connect_material_property(a, out, target):
            raise RuntimeError(f"Cannot connect {target}")

    def sample(name, kind, y):
        tex = lib.load_asset("/Game/Vesper/Understory/Shale" + name)
        if not tex:
            raise RuntimeError("Missing registered rock scan " + name)
        s = node(unreal.MaterialExpressionTextureSample, -800, y)
        s.texture = tex
        s.sampler_type = kind
        return s

    def mix(a, a_pin, b, b_pin, mask, mask_pin, x, y):
        m = node(unreal.MaterialExpressionLinearInterpolate, x, y)
        wire(a, a_pin, m, "A")
        wire(b, b_pin, m, "B")
        wire(mask, mask_pin, m, "Alpha")
        return m

    smp = unreal.MaterialSamplerType
    color = sample("Color", smp.SAMPLERTYPE_COLOR, -150)
    normal = sample("Normal", smp.SAMPLERTYPE_NORMAL, 210)
    rough = sample("Rough", smp.SAMPLERTYPE_MASKS, 590)
    stone = node(unreal.MaterialExpressionDesaturation, -540, -150)
    grey = node(unreal.MaterialExpressionConstant, -800, -320)
    grey.r = 0.92
    wire(grey, "", stone, "Fraction")
    wire(color, "RGB", stone, "")
    vertex = node(unreal.MaterialExpressionVertexColor, -760, 90)
    tint = node(unreal.MaterialExpressionMultiply, -330, -150)
    wire(stone, "", tint, "A")
    wire(vertex, "", tint, "B")
    damp = node(unreal.MaterialExpressionMultiply, -120, -20)
    damp.set_editor_property("const_b", 0.48)
    wire(tint, "", damp, "A")
    slate = node(unreal.MaterialExpressionMultiply, 290, -120)
    slate.set_editor_property("const_b", 0.32)
    wire(mix(tint, "", damp, "", vertex, "A", 80, -120), "", slate, "A")
    channel(slate, "", prop.MP_BASE_COLOR)
    # Rainwater gathers in low runs. Their shallower relief and roughness
    # pick up the hall light, while the dry stones retain the scanned grain.
    level = node(unreal.MaterialExpressionConstant3Vector, -530, 390)
    level.constant = unreal.LinearColor(0, 0, 1, 1)
    strength = node(unreal.MaterialExpressionMultiply, -510, 510)
    strength.set_editor_property("const_b", 0.75)
    wire(vertex, "A", strength, "A")
    normals = mix(normal, "RGB", level, "", strength, "", -230, 265)
    n = node(unreal.MaterialExpressionNormalize, -20, 265)
    wire(normals, "", n, "")
    channel(n, "", prop.MP_NORMAL)
    wet = node(unreal.MaterialExpressionConstant, -510, 735)
    wet.r = 0.21
    channel(mix(rough, "R", wet, "", vertex, "A", -210, 645), "", prop.MP_ROUGHNESS)
    edit.recompile_material(mat)
    if not lib.save_loaded_asset(mat, only_if_is_dirty=False):
        raise RuntimeError("Could not save forecourt material")
    return mat


if not levels.load_level("/Game/Vesper/Maps/MountainPilgrimage"):
    raise RuntimeError("Missing mountain map")
source = project / "Saved" / "BelfryCourt.glb"
blocks = bake(source)
folder = root + "/Geometry"
if not lib.does_directory_exist(folder):
    task = unreal.AssetImportTask()
    task.filename, task.destination_path = str(source), folder
    task.automated = task.save = True
    tools.import_asset_tasks([task])
meshes = [
    lib.load_asset(path)
    for path in lib.list_assets(folder)
    if str(lib.find_asset_data(path).asset_class_path.asset_name) == "StaticMesh"
]
if len(meshes) != 1:
    raise RuntimeError("Expected the joined forecourt stone and ironwork")
mesh = meshes[0]
paving = slab_surface()
iron = lib.load_asset("/Game/Vesper/RouteArt/BellHall/Surfaces/Patina")
if not iron:
    raise RuntimeError("Missing cast iron finish")
original = None
for actor in actors.get_all_level_actors():
    if actor.actor_has_tag("VesperNewCourt"):
        actors.destroy_actor(actor)
    elif isinstance(actor, unreal.StaticMeshActor):
        part = actor.static_mesh_component.static_mesh
        if part and "/BelfryFlagstones/" in part.get_path_name():
            original = actor
if not original:
    raise RuntimeError("Missing original central seal")
# Preserve the encounter's original physical floor and navigation. Only the
# new dressed stone and scaled seal render above it.
original.set_actor_hidden_in_game(True)
original.static_mesh_component.set_editor_property("visible", False)
center = original.get_actor_location()
# The foundation outcrops were fitted against the narrow road before this
# court was dressed. Keep their exposed side faces below the finished floor.
for actor in actors.get_all_level_actors():
    if actor.get_actor_label() != "Causeway bedrock":
        continue
    middle, extent = actor.get_actor_bounds(False)
    if (
        abs(middle.x - center.x) < 1460 + extent.x
        and abs(middle.y - center.y) < 1400 + extent.y
    ):
        top = middle.z + extent.z
        if top > -5:
            actor.add_actor_world_offset(unreal.Vector(0, 0, -5 - top), False, True)


def place(part, z, label):
    a = actors.spawn_actor_from_class(
        unreal.StaticMeshActor, unreal.Vector(center.x, center.y, z)
    )
    a.tags = ["VesperNewCourt"]
    a.set_actor_label(label)
    a.static_mesh_component.set_static_mesh(part)
    a.set_actor_enable_collision(False)
    return a


deck = place(mesh, 5.3, "Dressed slate forecourt")
for i, slot in enumerate(mesh.static_materials):
    deck.static_mesh_component.set_material(
        i, {"Paving": paving, "DrainIron": iron}[str(slot.material_slot_name)]
    )
seal = place(original.static_mesh_component.static_mesh, 6.5, "Cast bell seal")
seal.set_actor_scale3d(unreal.Vector(0.28, 0.28, 0.34))
if not levels.save_current_level():
    raise RuntimeError("Failed to save forecourt")
report = {"blocks": blocks, "deck_metres": [29.2, 28], "seal_diameter_metres": 3.55}
(project / "Saved" / "Forecourt.json").write_text(json.dumps(report))
unreal.log("VESPER_FORECOURT_SAVED " + str(report))
