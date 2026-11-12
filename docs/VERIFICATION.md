# Verification record

Initial validation: 2026-11-11, Apple Silicon macOS (`arm64`), Node.js 25.6.1, local Chrome through an isolated Playwright session.

## Automated simulation

23 tests pass. They cover action costs, attack direction, one hit per strike, insufficient stamina, dodge-window boundaries, parry timing, unparryable attacks, posture and ripostes, timed and interrupted healing, recoverable health, second phases for all bosses, projectile/ring/eruption creation, arena bounds, terminal death/victory, difficulty modifiers, bounded frame deltas, and malformed/versioned saves.

A deterministic combat agent defeats each of the three bosses on both Penitent and Pilgrim using the same movement/action input path as a player, without editing health or damage. This verifies reachability of wins and the authored rules; it does not substitute for human difficulty balancing.

## Browser checks

- Title screen inspected at 1440 × 900 and 390 × 844.
- Guide, encounter selection, loading, live 3D rendering and HUD inspected.
- Keyboard movement, heavy-attack damage, stamina use, dodging, death/retry and pause confirmed in the browser.
- Pausing suspends the Web Audio context; normal play resumes it.
- All fonts and art are bundled locally; no runtime account, API key, remote model call, or external font server is required.
- Production TypeScript check and Vite build pass.
- Production dependency audit reports zero vulnerabilities at validation time.

Build workers briefly stalled on a local read of an installed Three.js type definition. Reinstalling the locked dependencies in a fresh temporary directory resolved the local tooling issue; no game code change was required for that repair.

## Limits

The game combines original procedural architecture with CC0 rigged character models, scanned materials and synthesized audio. These are prototype characters and code-driven poses, not commercial-quality bespoke animation. Physical controllers, iOS/Android devices, Safari, and non-Mac ARM hardware have not been manually tested. Touch and gamepad controls are implemented but should receive physical-device playtesting before claiming broad platform certification. Save data belongs to the current browser/origin and does not synchronize between devices. GPU performance depends on hardware and resolution; a Performance mode disables SSAO, bloom and shadows and limits pixel ratio.

## Realism revision (2026-11-11)

All three encounters load textured GLB actors and PBR courtyards in local Chrome. The first arena was inspected through movement, a heavy strike (620 to 573 boss HP), dodging, damage and pause using real keyboard events. Movement is now camera-relative. An active-combat 180-frame requestAnimationFrame sample at 1440 x 900, High quality, on the Apple Silicon Mac averaged 8.29 ms, with a 9.60 ms 95th percentile. This is a short local browser sample, not a broad GPU benchmark or guarantee.

Screenshots in this directory are captures of the actual renderer, not the generated title illustration. Asset source and license data is included in `imported-assets.json`. The heavier art downloads are approximately 35 MB before browser caching.
