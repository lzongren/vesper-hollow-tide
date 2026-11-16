"""Synthesize a looping pine gust and the small bronze eave chimes of the bell court."""

from pathlib import Path
import wave
import numpy as np

RATE, SECONDS = 32000, 31


def render(path):
    rng = np.random.default_rng(1531)
    t = np.arange(RATE * SECONDS) / RATE
    hz = np.fft.rfftfreq(len(t), 1 / RATE)

    def band(lo, hi):
        noise = np.fft.rfft(rng.standard_normal(len(t)))
        mask = (1 - np.exp(-((hz / lo) ** 4))) * np.exp(-((hz / hi) ** 2))
        shaped = np.fft.irfft(noise * mask, n=len(t))
        return shaped / shaped.std()

    phase = 2 * np.pi * t / SECONDS
    gust = (
        0.51
        + 0.23 * np.cos(phase - 0.8)
        + 0.16 * np.sin(3 * phase + 0.3)
        + 0.08 * np.cos(7 * phase)
    ) ** 2
    bed = (0.012 + 0.029 * gust) * band(85, 520) + (0.004 + 0.018 * gust) * band(
        590, 4300
    )
    # Each strike has a short impact, a pair of slightly split modes and a
    # longer inharmonic tail. All tails decay before the next loop.
    for start, pitch, level in (
        (3.41, 764, 0.13),
        (3.72, 1141, 0.065),
        (4.69, 904, 0.09),
        (14.48, 904, 0.073),
        (21.26, 764, 0.115),
        (21.53, 1141, 0.064),
    ):
        age = t - start
        use = (age >= 0) & (age < 5)
        u = age[use]
        ring = np.zeros_like(u)
        for ratio, amp, decay in (
            (1, 0.76, 0.83),
            (1.003, 0.21, 0.91),
            (2.64, 0.24, 0.43),
            (4.14, 0.14, 0.25),
            (6.58, 0.045, 0.16),
        ):
            ring += amp * np.exp(-u / decay) * np.sin(2 * np.pi * pitch * ratio * u)
        bed[use] += level * (1 - np.exp(-u / 0.0023)) * ring
    # Periodic Fourier noise makes the wind continue smoothly across the seam.
    with wave.open(str(path), "wb") as wav:
        wav.setparams((1, 2, RATE, 0, "NONE", ""))
        wav.writeframes(np.int16(np.clip(bed, -1, 1) * 32767).astype("<i2").tobytes())


if __name__ == "__main__":
    render(Path(__file__).resolve().parents[1] / "native/Art/BellCourt/EaveWind.wav")
