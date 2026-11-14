# Magnolia Wayfarer

The fitted player uses a head and neck excerpt of the MakeHuman standard base mesh. The source OBJ explicitly releases the geometry under CC0. The original authors are Data Collection AB, Joel Palmius and Jonas Hauquier. The fitting retains the facial topology, projects a new diffuse texture and assigns hair and skin to separate surfaces. [MakeHuman source mesh and license notice](https://github.com/makehumancommunity/makehuman/blob/master/makehuman/data/3dobjs/base.obj)

The playable fitting uses an original ImageGen portrait and magnolia embroidery from the same two-panel source, saved as `magnolia-face.jpg` and `magnolia-silk.jpg`. The portrait supplies the mapped brows, eyes and lips. The fitter narrows the jaw while preserving the original topology. The comb, coiled hair, three blossoms, pearl drops and layered garment are geometry attached to the combat skeleton. The boots, gloves, trousers, sword and scabbard use the project's existing assets.

The two plum brocade streamers share a jade waist fastening. Their warp coordinate runs from the fastening to the forked tip. Regenerate the river-and-cloud embroidery with `python art/river_sash.py` and Pillow. [In-game movement](../../../docs/runtime/river-sash/)
