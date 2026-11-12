# Asset provenance

All characters, weapons, arenas, effects, story names, and audio patterns were created for this project. Existing game assets are not included.

- `public/art/vesper-cover.png`: generated with the built-in OpenAI image-generation tool for this project on 2026-11-11. The in-game scene uses separate original procedural 3D geometry; the cover is concept/title art, not a gameplay screenshot.
- `public/favicon.svg`: original geometric project emblem.
- `src/scene.ts`: original procedural meshes, texture generation, animation, lighting, and effects.
- `src/audio.ts`: original synthesis and composition code; no recordings or samples from other games.
- `public/fonts/cormorant-garamond.ttf`: Cormorant Garamond from Google Fonts, SIL Open Font License. License included beside the file.
- `public/fonts/inter.ttf`: Inter from Google Fonts, SIL Open Font License. License included beside the file.
- Three.js, TypeScript, Vite, and other dependencies retain their upstream licenses; see the lockfile for exact versions.

## Cover-art generation prompt

Use case: stylized-concept. Asset type: original dark fantasy action game title-screen artwork, cinematic wide 16:9 landscape. No words, letters, typography, logos or watermark. An abandoned tidal monastery of black stone rising from luminous mist at night. Right of center, a lone masked swordswoman with long ragged vermilion cloak and an elegant narrow sword, seen from behind at medium distance, faces an enormous ancient bronze ritual bell suspended within a broken cathedral arch. A delicate constellation halo and a pale eclipsed moon above. Pale feathers drifting through air, shallow reflective water, wet obsidian steps, a few warm votive candles, cypress silhouettes. East Asian ceremonial shapes blended with austere gothic ruins, completely original world and costume, not any existing game character. Painterly prestige concept art, exquisite intricate material detail, atmospheric depth, restrained ivory / charcoal / oxidized teal / muted cinnabar palette. Strong silhouette and beautiful composition. Left 45 percent relatively quiet dark fog for UI title and text overlay, no big objects there. Rich light and contrast around central-right figure and bell. Elegant melancholy, haunting beauty, no gore.
