# Three courts on the RTX 5080

Windows Edge 157 rendered the browser production build of `ce61b40` at 2560×1440. A fresh headless browser session entered each fight through its menu. WebGL reported ANGLE on the NVIDIA GeForce RTX 5080 using Direct3D 11. The screenshots retain the combat HUD and the original viewport.

| Encounter | Recorded frames in 6 s | Mean FPS | Median interval | 95th percentile | 99th percentile |
| --- | ---: | ---: | ---: | ---: | ---: |
| [The Bellwarden](rtx-lotus.jpg) | 252 | 42.0 | 16.7 ms | 16.9 ms | 300.3 ms |
| [The Veiled Heron](rtx-plume.jpg) | 229 | 38.1 | 16.7 ms | 16.8 ms | 367.1 ms |
| [Saint of Cinders](rtx-cinder.jpg) | 255 | 42.5 | 16.7 ms | 16.8 ms | 433.8 ms |

Each sample covers the opening exchange with movement, attacks, a dodge and a parry. The automated capture measured differences between `requestAnimationFrame` timestamps. Each fight had several long intervals. Their cause needs profiling, and a six-second sample cannot establish sustained frame rate over a full fight. The [raw intervals](measurements.json) preserve every measurement. Native Unreal gameplay remains unverified.
