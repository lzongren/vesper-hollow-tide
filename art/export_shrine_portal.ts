import * as T from "three";
import { shrinePortal } from "../src/shrine-portal";
import { bake } from "./bake_glb";

// Native material instances can bind the same tiling scans as the browser.
// Keep their two-times repeat and glTF image orientation in the exchange UVs.
const stone = new T.MeshStandardMaterial({ metalness: 0.05, roughness: 1 });
const bronze = new T.MeshStandardMaterial({
  name: "Aged bronze",
  color: 0xc8af71,
  metalness: 0.75,
  roughness: 0.65,
});
const model = shrinePortal(stone, bronze);
for (const part of model.children) {
  const mesh = part as T.Mesh;
  const uv = mesh.geometry.getAttribute("uv");
  for (let i = 0; i < uv.count; i++)
    uv.setXY(i, 2 * uv.getX(i), 1 - 2 * uv.getY(i));
  // Use the centre of the threshold as the native placement pivot.
  mesh.geometry.translate(0, 0, 19.56);
}
await bake(model, "ShrineLotusPortal");
