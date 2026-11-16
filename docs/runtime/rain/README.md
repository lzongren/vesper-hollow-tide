# Rain on the three courts

[Heron encounter with game audio](heron-rain.mp4) · [Belfry](belfry.jpg) · [Heron garden](heron.jpg) · [Cinder shrine](cinders.jpg)

The three images are 2560 × 1440 screenshots of player-controlled combat in Windows Edge on an RTX 5080. The 8.59-second moving capture at 1600 × 900 follows the player's camera through the Heron fight. Its audio comes from the same browser session.

The ground combines the engraved material, a world-space water-depth mask and a reflected scene view. Small rings disturb reflections at rain impacts and footfalls. Each court uses a different area of standing water. The runoff gutter has four bronze grates, with gaps in the raised curb at the outlets. Stone, architecture and actors retain their ordinary depth and cast shadows during play.

ImageGen provided three original overhead material plates under `public/art/`. The requested designs were twin bronze dragons circling an ancient bell for the belfry, cracked ivory porcelain cranes in dark slate for the garden, and a cinnabar phoenix above a brazier for the shrine. The reflections are rendered during play.

[Frame intervals from the capture run](frame-intervals.json) are browser animation callbacks during six seconds of combat in each encounter. The capture run included screenshot automation. The samples contain long intervals, including a 1.13-second interval in the belfry. These timings do not establish sustained 60 fps.

A separate [ten-second run per encounter](uninterrupted.json) sampled the same build at 1440p with screenshot capture disabled.

| Encounter | Median (ms) | 95th percentile (ms) | Longest (ms) |
| --- | ---: | ---: | ---: |
| The Bellwarden | 16.7 | 16.8 | 1701.8 |
| The Veiled Heron | 16.7 | 16.8 | 1151 |
| Saint of Cinders | 16.7 | 16.8 | 634 |
