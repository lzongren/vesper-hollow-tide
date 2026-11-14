"""Install the measured river valley behind the playable route and reface the shrine cliffs."""

import json
from pathlib import Path
import sys
import unreal

project = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
sys.path.insert(0, str(project / "Scripts"))
from river_relief import ORIGIN_X, build

lib = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
edit = unreal.MaterialEditingLibrary
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
root = "/Game/Vesper/RiverPeaks"
folder = root + "/Foothills"
if not levels.load_level("/Game/Vesper/Maps/MountainPilgrimage"):
    raise RuntimeError("Missing pilgrimage level")


def load_meshes():
    result = {}
    if lib.does_directory_exist(folder):
        for path in lib.list_assets(folder):
            if (
                str(lib.find_asset_data(path).asset_class_path.asset_name)
                == "StaticMesh"
            ):
                mesh = lib.load_asset(path)
                result[mesh.get_name()] = mesh
    return result


meshes = load_meshes()
if set(meshes) != {"RiverGroves", "RiverRelief"}:
    path = project / "Saved" / "XingpingRelief.glb"
    count = build(project / "Art" / "RiverPeaks", path)
    unreal.log("VESPER_RIVER_GROVES " + str(count))
    task = unreal.AssetImportTask()
    task.filename = str(path)
    task.destination_path = folder
    task.automated = task.replace_existing = task.save = True
    tools.import_asset_tasks([task])
    meshes = load_meshes()
if set(meshes) != {"RiverGroves", "RiverRelief"}:
    raise RuntimeError("Incomplete terrain import: " + str(meshes))


def wire(src, pin, dst, socket):
    if not edit.connect_material_expressions(src, pin, dst, socket):
        raise RuntimeError("Could not wire " + str(pin) + " to " + str(socket))


def output(src, pin, channel):
    if not edit.connect_material_property(src, pin, channel):
        raise RuntimeError("Could not wire " + str(channel))


def finish(name, kind):
    path = root + "/" + name
    mat = (
        lib.load_asset(path)
        if lib.does_asset_exist(path)
        else tools.create_asset(
            name, root, unreal.Material, unreal.MaterialFactoryNew()
        )
    )
    edit.delete_all_material_expressions(mat)

    def node(cls, x, y):
        return edit.create_material_expression(mat, cls, x, y)

    def constant(rgb, x, y):
        c = node(unreal.MaterialExpressionConstant3Vector, x, y)
        c.set_editor_property("constant", unreal.LinearColor(*rgb, 1))
        return c

    def number(v, x, y):
        c = node(unreal.MaterialExpressionConstant, x, y)
        c.set_editor_property("r", v)
        return c

    def aligned(function, texture, x, y):
        call = node(unreal.MaterialExpressionMaterialFunctionCall, x, y)
        call.set_material_function(
            unreal.load_asset(
                "/Engine/Functions/Engine_MaterialFunctions01/Texturing/" + function
            )
        )
        tex = node(unreal.MaterialExpressionTextureObject, x - 300, y)
        tex.set_editor_property(
            "texture", lib.load_asset("/Game/Vesper/Understory/" + texture)
        )
        if texture.endswith("Normal"):
            tex.set_editor_property(
                "sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL
            )
        inputs = list(edit.get_material_expression_input_names(call))
        texture_pin = next(
            (
                pin
                for pin in inputs
                if str(pin) in ("TextureObject", "Normal", "Texture")
            ),
            None,
        )
        if texture_pin is None:
            raise RuntimeError(f"Missing texture input on {function}: {inputs}")
        wire(tex, "", call, str(texture_pin))
        wire(constant((680, 680, 680), x - 300, y + 122), "", call, "TextureSize")
        return call

    prop = unreal.MaterialProperty
    if kind == "grove":
        output(
            node(unreal.MaterialExpressionVertexColor, -240, 0),
            "",
            prop.MP_BASE_COLOR,
        )
    else:
        mapped = aligned("WorldAlignedTexture", "ShaleColor", -700, 30)
        # The orbital canopy map carries the broad colour. The rock scan is
        # projected at 6.8 metres on every axis, including near-vertical faces.
        ash = node(unreal.MaterialExpressionDesaturation, -410, 30)
        wire(mapped, "XYZ Texture", ash, "")
        factor = node(unreal.MaterialExpressionAdd, -230, 30)
        factor.set_editor_property("const_b", 0.69)
        wire(ash, "", factor, "A")
        if kind == "river":
            base = node(unreal.MaterialExpressionTextureSample, -350, -250)
            cover = lib.load_asset(folder + "/XingpingRelief/Textures/RiverCover")
            if not cover:
                raise RuntimeError("Missing aligned river cover")
            base.set_editor_property("texture", cover)
            pin = "RGB"
        else:
            normal = node(unreal.MaterialExpressionPixelNormalWS, -920, -310)
            z = node(unreal.MaterialExpressionComponentMask, -715, -310)
            z.set_editor_property("b", True)
            z.set_editor_property("r", False)
            z.set_editor_property("g", False)
            wire(normal, "", z, "")
            slope = node(unreal.MaterialExpressionSmoothStep, -520, -300)
            slope.set_editor_property("const_min", 0.46)
            slope.set_editor_property("const_max", 0.82)
            wire(z, "", slope, "Value")
            base = node(unreal.MaterialExpressionLinearInterpolate, -290, -190)
            wire(constant((0.15, 0.165, 0.155), -540, -530), "", base, "A")
            wire(constant((0.047, 0.083, 0.063), -540, -435), "", base, "B")
            wire(slope, "", base, "Alpha")
            pin = ""
        mul = node(unreal.MaterialExpressionMultiply, -35, -90)
        wire(base, pin, mul, "A")
        wire(factor, "", mul, "B")
        output(mul, "", prop.MP_BASE_COLOR)
        normal = aligned("WorldAlignedNormal", "ShaleNormal", -700, 420)
        blend = node(unreal.MaterialExpressionLinearInterpolate, -320, 440)
        wire(constant((0, 0, 1), -550, 580), "", blend, "A")
        wire(normal, "XYZ Texture", blend, "B")
        blend.set_editor_property("const_alpha", 0.29)
        output(blend, "", prop.MP_NORMAL)
    output(number(0.88, -80, 180), "", prop.MP_ROUGHNESS)
    output(number(0.18, -80, 280), "", prop.MP_SPECULAR)
    edit.set_base_material_usage(mat, unreal.MaterialUsage.MATUSAGE_NANITE, True)
    edit.recompile_material(mat)
    if not lib.save_loaded_asset(mat, only_if_is_dirty=False):
        raise RuntimeError("Cannot save " + name)
    return mat


land = finish("ForestedLimestone", "river")
leaves = finish("DistantNeedleCrown", "grove")
near = finish("WeatheredShrineFace", "shrine")
scene = actors.get_all_level_actors()
old = [
    a
    for a in scene
    if a.get_actor_label().startswith(
        ("Distant ridge Limestone_spurs", "Distant ridge Summit_pines")
    )
]
nearby = [
    a
    for a in scene
    if a.get_actor_label().startswith("Reliquary mountain Limestone_spurs")
]
if len(old) != 6 or len(nearby) != 1:
    raise RuntimeError("Unexpected ridge inventory: " + str((len(old), len(nearby))))
for key, mat in (("RiverRelief", land), ("RiverGroves", leaves)):
    label = "Xingping " + key
    matches = [a for a in scene if a.get_actor_label() == label]
    if len(matches) > 1:
        raise RuntimeError("Duplicate " + label)
    p = unreal.Vector(100 * ORIGIN_X, 0, 0)
    a = (
        matches[0]
        if matches
        else actors.spawn_actor_from_class(unreal.StaticMeshActor, p)
    )
    a.modify()
    a.set_actor_label(label)
    comp = a.static_mesh_component
    comp.set_static_mesh(meshes[key])
    comp.set_material(0, mat)
    a.set_actor_enable_collision(False)
for a in old:
    a.modify()
    a.static_mesh_component.set_visibility(False)
    a.set_actor_hidden_in_game(True)
for a in nearby:
    a.modify()
    a.static_mesh_component.set_material(0, near)
if not levels.save_current_level():
    raise RuntimeError("Could not save mountain skyline")
(project / "Saved" / "RiverPeaks.json").write_text(
    json.dumps(
        dict(
            revision=2,
            terrain=land.get_path_name(),
            replaced=len(old),
            shrine=len(nearby),
        )
    )
)
unreal.log("VESPER_RIVER_PEAKS_READY")
