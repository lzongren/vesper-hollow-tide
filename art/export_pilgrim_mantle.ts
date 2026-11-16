import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import * as T from "three";
import { SilkPanel } from "../src/silk";
import { bake } from "./bake_glb";

const cloak = new T.Group(), anchor = new T.Bone();
const cloth = new T.MeshStandardMaterial({ name: "Woven heron brocade", side: T.DoubleSide, roughness: .78 });
for (const cut of [
  {side: 0, back: true, shoulder: false},
  {side: -1, back: false, shoulder: false},
  {side: 1, back: false, shoulder: false},
  {side: 0, back: true, shoulder: true},
]) {
  const panel = new SilkPanel(cloak, anchor, cut, 1.89, cloth, [], [], cut.shoulder, true);
  panel.update(0, 0);
}
await bake(cloak, "PilgrimMantle");
execFileSync(process.env.PYTHON || (process.platform === "win32" ? "python" : "python3"), [
  fileURLToPath(new URL("./bake_palm_fibre.py", import.meta.url)),
  fileURLToPath(new URL("../native/Art/PilgrimMantle.glb", import.meta.url)),
], { stdio: "inherit" });
