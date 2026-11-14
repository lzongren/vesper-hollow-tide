# Magnolia Wayfarer

The fitted player uses a head and neck excerpt of the MakeHuman standard base mesh. The source OBJ explicitly releases the geometry under CC0. The original authors are Data Collection AB, Joel Palmius and Jonas Hauquier. The fitting retains the facial topology, projects a new diffuse texture and assigns hair and skin to separate surfaces. [MakeHuman source mesh and license notice](https://github.com/makehumancommunity/makehuman/blob/master/makehuman/data/3dobjs/base.obj)

The riding coat uses the original magnolia embroidery in `magnolia-silk.jpg`. The current fitted head projects [plum-face.jpg](plum-face.jpg), a makeup pass over the original portrait in [ruyi-face.jpg](ruyi-face.jpg), onto the eyelids, lips and facial surface. The older `magnolia-face.jpg` is preserved with the earlier fitting. The fitter narrows the jaw while preserving the original topology. The butterfly pin, coiled hair, pearl drops and layered garment are geometry attached to the combat skeleton. The boots, gloves, trousers, sword and scabbard use the project's existing assets.

The two plum brocade streamers share a jade waist fastening. Their warp coordinate runs from the fastening to the forked tip. Regenerate the river-and-cloud embroidery with `python art/river_sash.py` and Pillow. [In-game movement](../../../docs/runtime/river-sash/)

The present fitting adds a four-lobed cloud collar over the riding coat. Each lobe maps the full embroidered magnolia to a separately weighted panel. Two lines of brass piping enclose the rose silk binding. The swept locks travel from an offset part toward the temples. The eyes use a smoother material than the surrounding face.

The cloud collar uses the built-in ImageGen textile source in [ruyi-embroidery.jpg](ruyi-embroidery.jpg). Its generation prompt follows.

> Square orthographic flat diffuse textile scan for an original classical Chinese swordswoman's embroidered silk cloud collar. All-over fine deep midnight peacock-blue silk ground. One central exquisite small ivory magnolia bloom flanked by mirrored slender kingfisher-teal curled leaves and gold couching ruyi scrolls. Upper and lower margins are mostly plain silk; motif compact, centered, complete in the middle 65 percent, no border. Individual satin stitches and restrained wine-red stamens, aged pale champagne threads. Completely flat, edge to edge fabric, soft even diffuse light, no objects, labels, text, body, clothing shape or cast shadows.

The built-in ImageGen portrait used this prompt.

> Square texture projection photograph, ultra-real natural skin for original game heroine, beautiful adult Han Chinese swordswoman age 28, Ming-inspired restrained elegance. Strictly front orthographic symmetric head, direct neutral gaze, calm slightly lifted outer eye corners, fine softly arched willow brows, warm brown almond eyes with visible natural sclera, small vermilion-stained lips closed, warm ivory skin with subtle blush, soft oval jaw and defined delicate cheekbones, serene confident rather than smiling. Black hair pulled back cleanly behind ears, center part. Even neutral frontal diffuse illumination with no hard shadows, no glossy makeup, no painted marks, no jewelry, no text or costume in frame. Tight face texture crop: top of hair at top frame, chin around 89% from top, left pupil at 38% across, right pupil at 62%, eye centers around 46% down, mouth at 73%, nose at 61%. Flat grey background, realistic skin pores and natural color variation, beauty of a Chinese classical film portrait.

## Plum blossom and butterfly fitting

The face carries a five-petal cinnabar *huadian*, a carmine lip glaze and a soft cheek wash. The hairline sits on cross sections of the fitted head. Two alpha-masked panels break up its edge at the temples. The blue-green butterfly wings have gilt outlines, wire veins, small antennae and a pearl body. The open and closed lids use one skinned mesh with a bilateral blink morph. Regenerate the makeup and hair mask with Pillow using `python art/plum_fitting.py`. [In-game portraits](../../../docs/runtime/plum-wayfarer/)
