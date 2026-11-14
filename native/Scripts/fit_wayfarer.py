"""Install the crane-coated player on the existing combat pawn blueprint."""

from pathlib import Path
import json
import sys
import unreal

project = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
sys.path.insert(0, str(project / "Scripts"))
from build_bellwarden import mesh_for, fit, lib, combat
from keeper_materials import surface

mesh = mesh_for("CraneWayfarerCourt", "pilgrim.glb", armed=True, wayfarer=True)
bp = lib.load_asset(combat + "BP_CombatCharacter")
reference = unreal.get_default_object(
    bp.generated_class()
).mesh.skeletal_mesh_asset.skeleton
mesh.skeleton.set_editor_property("compatible_skeletons", [reference])
lib.save_loaded_asset(mesh.skeleton, only_if_is_dirty=False)
root = mesh.get_path_name().split("/SkeletalMeshes/")[0]
slots = list(mesh.materials)
finishes = {
    "WayfarerSkin": (0, 0.59),
    "CraneSilk": (0.06, 0.63),
    "MidnightSilk": (0.03, 0.77),
    "MadderBinding": (0.03, 0.70),
    "ChasedBrass": (0.65, 0.40),
    "InkHair": (0, 0.64),
}
for slot in slots:
    name = str(slot.material_slot_name)
    if name in finishes:
        metal, rough = finishes[name]
        slot.material_interface = surface(root, name + "Surface", name, metal, rough)
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
    json.dumps({"mesh": mesh.get_path_name(), "revision": 1})
)
unreal.log("VESPER_WAYFARER_READY")
