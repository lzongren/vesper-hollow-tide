"""Render a quiet loop of ripples under the stone arch and drops from lotus leaves."""

from array import array
from math import exp, sin, tau
from random import Random
import sys
import wave


def bake(path):
    rate = 24000
    duration = 16
    rng = Random(416)
    samples = array("f", [0]) * (rate * duration)
    # Lapping water: two overlapping bands of noise rise and fall along the edge.
    slow = mid = fast = 0
    for i in range(len(samples)):
        t = i / rate
        n = rng.uniform(-1, 1)
        slow += 0.023 * (n - slow)
        mid += 0.12 * (n - mid)
        fast += 0.42 * (n - fast)
        push = (0.5 + 0.5 * sin(tau * t / 4 + 0.70 * sin(tau * t / 16))) ** 3
        samples[i] = (0.028 + 0.052 * push) * (mid - slow) + 0.016 * push * (fast - mid)
    for _ in range(54):
        start = rng.randrange(len(samples))
        f = rng.uniform(510, 1780)
        damp = rng.uniform(0.018, 0.055)
        amp = rng.uniform(0.018, 0.073)
        for i in range(int(damp * rate * 7)):
            t = i / rate
            # A water drop creates a short resonant bubble with a rising partial.
            phase = tau * f * (t + 0.13 * (t - damp * (1 - exp(-t / damp))))
            body = (1 - exp(-t / 0.0013)) * exp(-t / damp)
            samples[(start + i) % len(samples)] += (
                amp * body * (sin(phase) + 0.18 * sin(2.08 * phase))
            )
    pcm = array("h", (round(32767 * v) for v in samples))
    if sys.byteorder != "little":
        pcm.byteswap()
    with wave.open(str(path), "wb") as wav:
        wav.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        wav.writeframes(pcm.tobytes())


def install(project, root, actors):
    import unreal

    lib = unreal.EditorAssetLibrary
    name = "UnderTheCrescentBridge"
    asset = root + "/" + name
    if not lib.does_asset_exist(asset):
        source = project / "Saved" / (name + ".wav")
        bake(source)
        job = unreal.AssetImportTask()
        job.filename = str(source)
        job.destination_path = root
        job.automated = job.save = True
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([job])
    wave_asset = lib.load_asset(asset)
    if not wave_asset:
        raise RuntimeError("Missing water-edge ambience")
    wave_asset.set_editor_property("looping", True)
    wave_asset.set_editor_property(
        "virtualization_mode", unreal.VirtualizationMode.PLAY_WHEN_SILENT
    )
    if not lib.save_loaded_asset(wave_asset, only_if_is_dirty=False):
        raise RuntimeError("Could not save water-edge loop")
    a = actors.spawn_actor_from_class(
        unreal.AmbientSound, unreal.Vector(13800, 2310, -65)
    )
    a.tags = ["VesperMoonWater"]
    a.set_actor_label("Lapping water under the crescent bridge")
    c = a.audio_component
    c.set_sound(wave_asset)
    c.set_editor_property("auto_activate", True)
    c.set_editor_property("volume_multiplier", 0.72)
    c.set_editor_property("override_attenuation", True)
    attenuation = c.get_editor_property("attenuation_overrides")
    attenuation.set_editor_property(
        "attenuation_shape_extents", unreal.Vector(420, 0, 0)
    )
    attenuation.set_editor_property("falloff_distance", 1850)
    c.set_editor_property("attenuation_overrides", attenuation)
