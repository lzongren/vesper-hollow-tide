"""An original spatial release cue: silk brushing, quill flex and gilt fittings."""

from array import array
from math import exp, sin, tanh, tau
from random import Random
import sys
import wave


def release(path):
    rate = 48000
    rng = Random(734)
    samples = array("h")
    low = mid = 0.0
    for i in range(int(0.86 * rate)):
        t = i / rate
        white = rng.uniform(-1, 1)
        low += 0.038 * (white - low)
        mid += 0.48 * (white - mid)
        # A broad sweep precedes the two short snaps of the opening vanes.
        envelope = sum(
            gain * exp(-(((t - centre) / width) ** 2))
            for centre, width, gain in (
                (0.105, 0.074, 0.54),
                (0.169, 0.022, 0.77),
                (0.213, 0.032, 0.47),
                (0.315, 0.094, 0.35),
            )
        )
        flutter = 0.82 + 0.18 * sin(tau * (39 * t - 19 * t * t))
        brush = (mid - low) * envelope * flutter
        ring = 0.0
        for onset, hz, gain, damping in (
            (0.146, 1213, 0.18, 13),
            (0.182, 1861, 0.12, 18),
            (0.186, 2837, 0.045, 24),
        ):
            age = t - onset
            if age > 0:
                ring += (
                    gain
                    * sin(tau * hz * age)
                    * exp(-damping * age)
                    * (1 - exp(-age * 370))
                )
        low_sweep = (
            0.12 * sin(tau * (325 * t - 84 * t * t)) * exp(-(((t - 0.11) / 0.091) ** 2))
        )
        window = min(1, t / 0.009, (0.86 - t) / 0.032)
        samples.append(round(24700 * tanh(brush + ring + low_sweep) * window))
    if sys.byteorder != "little":
        samples.byteswap()
    with wave.open(str(path), "wb") as target:
        target.setparams((1, 2, rate, 0, "NONE", ""))
        target.writeframes(samples.tobytes())
