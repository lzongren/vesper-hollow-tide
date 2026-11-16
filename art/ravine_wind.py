"""Render a looping bed of sheltered wind, grass swishes and dry seed rattles."""

import wave
from pathlib import Path

import numpy as np


def render(path):
    rate, seconds = 32000, 29
    n = rate * seconds
    t = np.arange(n) / rate
    f = np.fft.rfftfreq(n, 1 / rate)
    rng = np.random.default_rng(12685)

    def layer(centre, width):
        spectrum = np.fft.rfft(rng.standard_normal(n))
        band = np.exp(-0.5 * (np.log2(np.maximum(f, 1) / centre) / width) ** 2)
        signal = np.fft.irfft(spectrum * band, n)
        return signal / max(np.std(signal), 0.0001)

    def pulse(at, width):
        d = (t - at + seconds / 2) % seconds - seconds / 2
        return np.exp(-0.5 * (d / width) ** 2)

    gust = sum(
        amp * pulse(at, length)
        for at, length, amp in (
            (3.6, 1.4, 0.7),
            (7.1, 0.72, 0.32),
            (15.8, 2.6, 0.94),
            (23.2, 0.86, 0.59),
        )
    )
    wind = (0.019 + 0.033 * gust) * layer(185, 0.72)
    wind += (0.008 + 0.024 * gust**1.45) * layer(690, 0.80)
    small = np.zeros(n)
    for _ in range(74):
        at = rng.uniform(0, seconds)
        small += (
            rng.uniform(0.005, 0.022)
            * pulse(at, rng.uniform(0.020, 0.16))
            * (0.2 + gust[int(at * rate)])
        )
    wind += (0.002 + small) * layer(3500, 0.68)
    for at in (5.7, 17.5, 17.83, 24.4):
        ticks = np.zeros(n)
        for j in range(rng.integers(4, 10)):
            ticks += (
                pulse(at + j * rng.uniform(0.016, 0.032), rng.uniform(0.0018, 0.006))
                * 0.032
            )
        wind += ticks * layer(2100, 0.51)
    # FFT-filtered noise and circular envelopes wrap at the sample boundary.
    pcm = np.rint(32767 * np.clip(wind, -0.90, 0.90)).astype("<i2")
    with wave.open(str(path), "wb") as stream:
        stream.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        stream.writeframes(pcm.tobytes())


if __name__ == "__main__":
    render(
        Path(__file__).resolve().parents[1] / "native/Art/ShrineTalus/RavineWind.wav"
    )
