# The lamp at the Hall of the Taming Tide

[Full Bellwarden encounter with audio](bellwarden.mp4) · [Same-pose lighting comparison](comparison.jpg) · [Current 1440p frame](bellwarden.jpg) · [Previous 1440p frame](previous.jpg) · [Side view](side.jpg)

A suspended silk lamp casts warm light across the bell and the embossed face. A cooler moon grazes the back of the shoulders. Both lights stay in the court as the camera circles. Depth limits the light scattered by mist at the first surface. The main door opens onto a second lintel, interior posts, a hanging bell and candle stands. Two clerestory bays remain bright.

The comparison uses the production builds before and after the lighting change. In Windows Edge on an RTX 5080 the input sequence and the number of 60 Hz simulation frames were the same for each pose. The original screenshots retain their HUD at 2560 × 1440. The comparison places scaled copies side by side. These stepped captures measure appearance only.

In the matched windup, mean linear-sRGB luminance in a mask region increased from 0.057 to 0.082. The left gallery decreased from 0.050 to 0.038. The sample rectangles in normalized image coordinates are (0.500, 0.228) to (0.527, 0.306) for the mask and (0.012, 0.255) to (0.285, 0.530) for the gallery. Both refer to the same frame pair. The light studies for the garden and shrine use a pale green key from the east and an amber key from the west.

The 52.70-second, 1600 × 900 film follows one uninterrupted Pilgrim run through the awakened phase to the Bellwarden's fall. It preserves all 802 delivered screencast frames and the game's synchronized stereo audio. The mean recording rate was 15.2 images per second. The result screen's clock measures simulation time.

## End-to-end playthrough

The keyboard driver watched the public HUD and entered each fight from the encounter menu. All three opponents reached their awakened phase and then zero health. The final victory screen displayed *The last bell fades*. [HUD results and timing samples](victories.json)

| Encounter | Game clock | Parries | Hits taken |
| --- | ---: | ---: | ---: |
| Bellwarden | 0:27 | 3 | 0 |
| Veiled Heron | 0:28 | 5 | 0 |
| Saint of Cinders | 0:39 | 4 | 5 |

A second run stepped the simulation at 60 Hz and let each opponent defeat the player. All three reached the defeat screen. Retry restored 100/100 player health in each court, and the pause menu returned to the encounter selector. [Defeat results](defeats.json) · [Garden of Veils](heron.jpg) · [Ashen Reliquary](cinders.jpg)

## Remaining visual and motion issues

The garden entrance camera can put the orange canopy in front of a fighter during a lateral move. At the Bellwarden's feet the edge of the attack indicator reads as a flat sector. The captured gameplay also has visible stalls. The longest browser animation callback gaps were 3.09 seconds in the recorded bell fight, 1.64 seconds in the garden and 2.64 seconds at the shrine. Only the bell fight used screencast capture. The gaps include encounter transitions. Their cause has not been isolated.
