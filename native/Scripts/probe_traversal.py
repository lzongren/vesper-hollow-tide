"""Optional standalone diagnostic. Move the template pawn and record real UE frames."""
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
tick = None
marks = [(0.1, "start")] + [(1 + n / 8, f"run-{n:02d}") for n in range(48)] + [(7.2,"stop")]


def record(dt):
    global controller, start, ready
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
        (output/'motion.json').write_text(json.dumps({"samples":samples,"frames":frames,"pawn":pawn.get_class().get_name()}))
        unreal.unregister_slate_post_tick_callback(tick)
        unreal.log('VESPER_TRAVERSAL_PROBED')


tick = unreal.register_slate_post_tick_callback(record)
unreal.log('VESPER_TRAVERSAL_PROBE_ARMED')
