import * as T from "three";
import { cinderIcon } from "../src/cinder-icon";
import { bake } from "./bake_glb";

const icon = new T.Group();
const { mask, halo } = cinderIcon();
mask.position.set(0, 3.076, -0.132);
halo.position.set(0, 3.28, -0.42);
icon.add(mask, halo);
await bake(icon, "CinderVotiveHead");
