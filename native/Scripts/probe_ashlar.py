"""Optional standalone capture. Walk the possessed traveller down a flight and inspect the bank."""

import json
import time
from pathlib import Path

import unreal

out = (
    Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()))
    / "AshlarProbe"
)
out.mkdir(exist_ok=True)
controller = None
stage = 0
since = None
shots = []
track = []
ascent = []
forest_ticks = []
stages = [
    ("road", (1300, 240, 100), -6, 7.0),
    ("stairs", (4200, -1250, 115), -90, 5.0),
    ("toe", None, 94, 4.5),
    ("return", None, 90, 5.2),
    ("bank", (1100, 1150, 100), -23, 6.0),
    ("forest timing", None, -23, 9.0),
]
entered = False
shot = False


def record(dt):
    global controller, stage, since, entered, shot
    if controller is None:
        controller = next(
            (
                c
                for c in unreal.ObjectIterator(unreal.PlayerController)
                if c.is_local_controller() and c.get_controlled_pawn()
            ),
            None,
        )
        if controller is None:
            return
        since = time.perf_counter() + 12
    if time.perf_counter() < since:
        return
    pawn = controller.get_controlled_pawn()
    label, xyz, yaw, duration = stages[stage]
    if not entered:
        if xyz:
            pawn.set_actor_location(unreal.Vector(*xyz), False, True)
        pawn.set_actor_rotation(unreal.Rotator(0, 0, yaw), False)
        controller.set_control_rotation(unreal.Rotator(0, -6, yaw))
        entered = True
    t = time.perf_counter() - since
    if label == "stairs" and 1.0 < t < 3.35:
        pawn.add_movement_input(unreal.Vector(0, -1, 0), 1)
    if label == "return" and 0.6 < t < 3.45:
        pawn.add_movement_input(unreal.Vector(0, 1, 0), 1)
    pos = pawn.get_actor_location()
    if label in ("stairs", "return"):
        samples = track if label == "stairs" else ascent
        samples.append(
            [
                round(t, 3),
                round(pos.y, 1),
                round(pos.z, 1),
                str(pawn.character_movement.movement_mode),
            ]
        )
    if label == "forest timing" and t >= 1:
        forest_ticks.append(round(t, 6))
    if (
        label != "forest timing"
        and not shot
        and t >= (2.25 if label == "stairs" else duration - 1.3)
    ):
        unreal.SystemLibrary.execute_console_command(pawn, "Shot", controller)
        shots.append(
            {
                "label": label,
                "position_cm": [round(v, 1) for v in [pos.x, pos.y, pos.z]],
                "yaw": yaw,
            }
        )
        unreal.log("VESPER_ASHLAR_FRAME " + label)
        shot = True
    if t >= duration:
        stage += 1
        since = time.perf_counter()
        shot = entered = False
        if stage == len(stages):
            (out / "route.json").write_text(
                json.dumps(
                    {
                        "pawn": pawn.get_class().get_name(),
                        "skeletal_mesh": pawn.mesh.skeletal_mesh_asset.get_path_name(),
                        "cape_material": pawn.mesh.get_material(
                            pawn.mesh.get_material_index("Mantle_1")
                        ).get_path_name(),
                        "animation": pawn.mesh.get_anim_instance()
                        .get_class()
                        .get_name(),
                        "shots": shots,
                        "descent": track,
                        "ascent": ascent,
                        "forest_ticks": forest_ticks,
                    }
                )
            )
            unreal.unregister_slate_post_tick_callback(handle)
            unreal.log("VESPER_ASHLAR_WALKED")


handle = unreal.register_slate_post_tick_callback(record)
unreal.log("VESPER_ASHLAR_ARMED")
