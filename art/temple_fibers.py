"""Paint four combed temple clusters with tapered coverage in straight alpha."""

from pathlib import Path
import math
import random
from PIL import Image, ImageDraw

rng = random.Random(340)
size = 1024
im = Image.new("RGBA", (size, size), (44, 32, 28, 0))
pen = ImageDraw.Draw(im)
for card in range(4):
    for strand in range(96):
        root = rng.uniform(-0.43, 0.43)
        group = round(root * 7) / 7
        reach = rng.uniform(0.55, 0.97) - 0.21 * abs(root)
        phase = rng.uniform(-0.3, 0.3)
        shade = rng.randrange(36, 59)
        alpha = rng.randrange(80, 199)
        last = None
        for step in range(65):
            t = step / 64
            sweep = 0.052 * math.sin(4.1 * t + phase + card)
            x = root * (1 - t) + (group * 0.37 + phase * 0.11) * t + sweep
            point = ((card + 0.5 + x) * 256, reach * t * 1023)
            if last:
                pen.line(
                    [last, point],
                    fill=(
                        shade,
                        int(shade * 0.78),
                        int(shade * 0.66),
                        round(alpha * (1 - t**3)),
                    ),
                    width=2 if t < 0.72 else 1,
                )
            last = point
im.save(Path(__file__).resolve().parents[1] / "native/Art/Wayfarer/temple-fibers.png")
