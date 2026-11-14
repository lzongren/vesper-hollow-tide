# Mountain Pilgrimage

[Unreal map measurements](map.json) · [Launch from a Windows checkout](../../../native/README.md)

## Browser combat

[Movement and lock-on capture](browser-motion.mp4) · [Three full encounter results](browser-results.json)

Walking now ramps up to 5.2 metres per second, and releasing the control applies a faster braking curve. Gait phase advances with actual distance. A dodge travels 4.48 metres with a continuous velocity curve while retaining the original invulnerability window. The close-range lock-on camera shifts sideways to separate fighters on wide screens.

The RTX 5080 test played each browser fight to victory on Pilgrim difficulty. The 95th-percentile animation callback interval during active combat was 16.8 ms in all three. The slowest combat interval was 59.2 ms. Initial loads took 6.3–19.2 seconds. The MP4 uses deterministic browser stepping for inspection of movement and the camera. Live timing comes from the separate full-encounter runs.

The first standalone launch exposed a missing Nanite material permutation on the imported glTF surfaces. The preparation pass resaved all 36 route meshes for conventional rendering. The project also disables offline path tracing and enables the skin cache required by its real-time ray tracing configuration.
