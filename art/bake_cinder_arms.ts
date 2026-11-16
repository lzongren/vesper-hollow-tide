import * as T from "three";
import { cinderArmour } from "../src/cinder-armour";
import { bake } from "./bake_glb";

const arms = new T.Group();
for (const { side, cap, bracer } of cinderArmour()) {
  const arm = side < 0 ? "Right" : "Left";
  cap.name = arm + " upper arm guard";
  bracer.name = arm + " forearm guard";
  arms.add(cap, bracer);
}
await bake(arms, "CinderArmGuards");
