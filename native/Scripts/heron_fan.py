"""Pose the boss's pooled flight feathers against the animated casting hand."""

import math
import unreal

CAST_SECONDS = 1.12


def smooth(start, end, value):
    t = max(0.0, min(1.0, (value - start) / (end - start)))
    return t * t * (3 - 2 * t)


def heading(yaw):
    a = math.radians(yaw)
    return unreal.Vector(math.cos(a), math.sin(a), 0)


def flight_rotation(yaw, lane, travel):
    # Air pressure lifts the stem and rolls the curved vane in a shallow bank.
    phase = travel / 235 + 0.36 * lane
    return unreal.Rotator(
        pitch=29 + 6 * math.sin(phase),
        yaw=yaw,
        roll=37 + 25 * math.sin(phase + 0.5) + lane * 5,
    )


def unfold(duel, now):
    blend = 1 - (duel.deadline - now) / CAST_SECONDS
    if blend <= 0:
        return
    spread = smooth(0.08, 0.68, blend)
    throw = smooth(0.78, 1, blend)
    fwd = duel.axis
    side = duel.actor.get_actor_right_vector()
    up = unreal.Vector(0, 0, 1)
    hand = duel.actor.mesh.get_socket_location("hand_l")
    hub = hand + fwd * 23 + up * 8
    release = duel.actor.get_actor_location() + fwd * 52
    for i, quill in enumerate(duel.feathers):
        lane = i - (len(duel.feathers) - 1) / 2
        theta = math.radians(lane * (4 + 19 * spread) - 6)
        face = side * math.sin(theta) + up * math.cos(theta) + fwd * 0.14
        face = face / face.length()
        scale = 0.34 + 0.66 * smooth(0, 0.47, blend)
        loc = (hub + face * (54 * scale)) * (1 - throw) + release * throw
        # Match the visible rotation at release; find the shortest rotation
        # between the displayed vane and its initial bank on the flight path.
        folded = unreal.MathLibrary.make_rot_from_xz(face, fwd)
        rot = unreal.MathLibrary.r_lerp(
            folded, flight_rotation(duel.yaw + lane * 10, lane, 0), throw, True
        )
        quill.set_actor_scale3d(unreal.Vector(scale, scale, scale))
        quill.set_actor_location_and_rotation(loc, rot, False, True)
        quill.set_actor_hidden_in_game(False)
