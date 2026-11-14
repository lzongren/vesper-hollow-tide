import { travelHat } from "../src/travel-hat";
import { pilgrimScabbard } from "../src/pilgrim-scabbard";
import { bake } from "./bake_glb";

const hat = travelHat();
hat.position.set(0, 0, 0);
hat.rotation.set(0, 0, 0);
await bake(hat, "PilgrimRainHat");
await bake(pilgrimScabbard(), "PilgrimScabbard");
