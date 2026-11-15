"""Install the magnolia-coated player on the existing combat pawn blueprint."""

from pathlib import Path
import json
import sys
import unreal

project = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
sys.path.insert(0, str(project / "Scripts"))
from build_bellwarden import mesh_for, fit, lib, combat
from keeper_materials import surface
from sash_material import silk_motion
from wayfarer_skin import complexion
from camellia_materials import cornea, hair_roots, lashes

mesh = mesh_for("HaitangWayfarer", "pilgrim.glb", armed=True, wayfarer=True)
if not any(
    str(name).lower().endswith("blink") for name in mesh.get_all_morph_target_names()
):
    raise RuntimeError("The fitted swordswoman is missing her eyelid morph")
bp = lib.load_asset(combat + "BP_CombatCharacter")
reference = unreal.get_default_object(
    bp.generated_class()
).mesh.skeletal_mesh_asset.skeleton
mesh.skeleton.set_editor_property("compatible_skeletons", [reference])
lib.save_loaded_asset(mesh.skeleton, only_if_is_dirty=False)
root = mesh.get_path_name().split("/SkeletalMeshes/")[0]
slots = list(mesh.materials)
finishes = {
    "RuyiBrocade": (0.08, 0.62),
    "MagnoliaSilk": (0.06, 0.63),
    "CeladonSilk": (0.03, 0.77),
    "RoseBinding": (0.03, 0.70),
    "ChasedBrass": (0.65, 0.40),
}
for slot in slots:
    name = str(slot.material_slot_name)
    if name == "WayfarerSkin":
        slot.material_interface = complexion(root)
    elif name == "WetIris":
        slot.material_interface = cornea(root)
    elif name == "LashFringe":
        slot.material_interface = lashes(root)
    elif name in finishes:
        metal, rough = finishes[name]
        slot.material_interface = surface(root, name + "Surface", name, metal, rough)
    elif name == "RiverBrocade":
        slot.material_interface = silk_motion(root)
    elif name == "WillowLocks":
        slot.material_interface = surface(
            root, "CombedWillowHair", name, 0, 0.48, cutout=True, specular=0.24
        )
    elif name == "TempleStrands":
        slot.material_interface = hair_roots(root)
    elif name == "InkHair":
        slot.material_interface = surface(
            root, "BrushedInk", name, 0, 0.59, specular=0.21
        )
    elif name == "Pilgrim_0":
        slot.material_interface = surface(
            root, "TravelBoots", "TravelLeather", 0.06, 0.73
        )
    elif name.startswith("SwordCase_"):
        gilt = name in ("SwordCase_1", "SwordCase_3")
        slot.material_interface = surface(
            root,
            "OldBrass" if gilt else "DarkScabbard",
            "ChasedBrass" if gilt else "TravelLeather",
            0.65 if gilt else 0.09,
            0.47 if gilt else 0.59,
        )
mesh.set_editor_property("materials", slots)
lib.save_loaded_asset(mesh, only_if_is_dirty=False)
fit("BP_CombatCharacter", "BP_BelfryPilgrim", mesh, {})
(project / "Saved" / "WayfarerOutfit.json").write_text(
    json.dumps({"mesh": mesh.get_path_name(), "revision": 8})
)
unreal.log("VESPER_WAYFARER_READY")
