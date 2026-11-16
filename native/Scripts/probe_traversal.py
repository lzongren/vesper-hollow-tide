"""Optional standalone diagnostic. Move the possessed pawn and record real UE frames."""
import json
import time
from pathlib import Path
import unreal

output = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())) / "TraversalProbe"
output.mkdir(exist_ok=True)
start = None
ready = None
controller = None
samples = []
frames = []
return_start = None
return_samples = []
turn_samples = []
turn_shots = [(.12,"start"),(.8,"turn"),(1.55,"stride"),(2.25,"brake"),(2.95,"rest")]
tick = None
marks = [(0.1, "start")] + [(1 + n / 8, f"run-{n:02d}") for n in range(48)] + [(7.2,"stop")]


def record(dt):
    global controller, start, ready, return_start
    if controller is None:
        for pc in unreal.ObjectIterator(unreal.PlayerController):
            if pc.get_controlled_pawn() is not None and pc.is_local_controller():
                controller = pc
                break
        if controller is None:
            return
        ready = time.perf_counter() + 15
    if time.perf_counter() < ready:
        return
    if start is None:
        start = time.perf_counter()
    t = time.perf_counter() - start
    pawn = controller.get_controlled_pawn()
    if pawn is None:
        return
    if return_start is not None:
        # Allow the last PNG readback to finish, then measure a run with no captures.
        elapsed = time.perf_counter() - return_start
        if elapsed < 0:
            return
        if elapsed >= 8:
            if not turn_samples:
                (output/"return.json").write_text(json.dumps({
                    "pawn":pawn.get_class().get_name(), "samples":return_samples
                }))
                unreal.log("VESPER_RETURN_MEASURED")
            turn_time = elapsed - 8
            if .35 <= turn_time < 1.95:
                pawn.add_movement_input(unreal.Vector(0,1,0), 1)
            mesh = pawn.mesh
            left = mesh.get_socket_location("foot_l") - pawn.get_actor_location()
            right = mesh.get_socket_location("foot_r") - pawn.get_actor_location()
            turn_samples.append([round(turn_time,4), round(pawn.get_actor_rotation().yaw,2),
                                 round(pawn.get_velocity().length(),2),round(left.z,2),round(right.z,2)])
            if turn_shots and turn_time >= turn_shots[0][0]:
                turn_shots.pop(0)
                unreal.SystemLibrary.execute_console_command(pawn, "Shot", controller)
            if turn_time >= 3.4:
                (output/"turn.json").write_text(json.dumps({"samples":turn_samples}))
                unreal.unregister_slate_post_tick_callback(tick)
                unreal.log("VESPER_PILGRIM_TURNED")
            return
        if 0.9 <= elapsed < 6.25:
            pawn.add_movement_input(unreal.Vector(-1,0,0), 1)
        pos, vel = pawn.get_actor_location(), pawn.get_velocity()
        return_samples.append([round(elapsed,5),round(dt*1000,2),round(pos.x,2),
                               round(pos.y,2),round(pos.z,2),round(vel.length(),2)])
        return
    if 0.9 <= t < 6.25:
        pawn.add_movement_input(unreal.Vector(1,0,0), 1)
    pos, vel = pawn.get_actor_location(), pawn.get_velocity()
    samples.append([round(t,4), round(dt*1000,2), round(pos.x,2), round(pos.y,2), round(pos.z,2), round(vel.length(),2)])
    if marks and t >= marks[0][0]:
        # PNG readback can outlast a sampling slot. Skip stale shots.
        while len(marks) > 1 and t >= marks[1][0]:
            marks.pop(0)
        _, name = marks.pop(0)
        unreal.SystemLibrary.execute_console_command(pawn, 'Shot', controller)
        frames.append([name,round(t,3)])
    if t >= 8:
        (output/"appearance.json").write_text(json.dumps({
            "pawn": pawn.get_class().get_path_name(),
            "skeletal_mesh": pawn.mesh.skeletal_mesh_asset.get_path_name(),
            "animation": pawn.mesh.get_anim_instance().get_class().get_path_name(),
            "acceleration_cm_s2": pawn.character_movement.max_acceleration,
            "braking_cm_s2": pawn.character_movement.braking_deceleration_walking,
            "yaw_rate_deg_s": pawn.character_movement.rotation_rate.yaw,
            "slots": [str(name) for name in pawn.mesh.get_material_slot_names()]
        },indent=2))
        (output/'motion.json').write_text(json.dumps({"samples":samples,"frames":frames,"pawn":pawn.get_class().get_name()}))
        return_start = time.perf_counter() + 4
        unreal.log('VESPER_TRAVERSAL_PROBED')


tick = unreal.register_slate_post_tick_callback(record)
unreal.log('VESPER_TRAVERSAL_PROBE_ARMED')
