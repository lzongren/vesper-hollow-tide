"""Render the four inharmonic modes used by Vesper's bronze bell."""

import array
import math
import sys
import wave


def strike(path, fundamental):
    hz = 32000
    samples = array.array("h")
    partials = [(1, 1.4), (2.76, 0.7), (5.4, 0.35), (8.93, 0.16)]
    for i in range(3 * hz):
        time = i / hz
        attack = min(1, time / 0.005)
        release = min(1, (3 - time) / 0.05)
        value = sum(
            math.sin(math.tau * fundamental * ratio * time)
            * math.exp(-time / decay)
            / (index + 1)
            for index, (ratio, decay) in enumerate(partials)
        )
        samples.append(round(value * attack * release * 12500))
    if sys.byteorder != "little":
        samples.byteswap()
    with wave.open(str(path), "wb") as output:
        output.setparams((1, 2, hz, 0, "NONE", ""))
        output.writeframes(samples.tobytes())
