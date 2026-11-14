/** Bake the playable Heron headpiece in metres. Run with npx tsx art/export_heron_mask.ts. */
import * as T from "three";
import { bridalMask } from "../src/heron";
import { bake } from "./bake_glb";

const bronze = new T.MeshStandardMaterial({
  name: "Worn bronze",
  color: 0xc8af71,
  metalness: 0.78,
  roughness: 0.42,
});
const silk = new T.MeshStandardMaterial({
  name: "Bridal silk",
  color: 0x385b58,
  roughness: 0.67,
  side: T.DoubleSide,
});
const headpiece = bridalMask(bronze, silk);
for (const child of headpiece.children) {
  const { material } = child as T.Mesh<
    T.BufferGeometry,
    T.MeshStandardMaterial
  >;
  child.name =
    material.name ||
    (material instanceof T.MeshPhysicalMaterial
      ? "Porcelain"
      : material.color.getHex() === 0x252a2d
        ? "Coiffure"
        : "Garnets");
  material.name ||= child.name;
}
await bake(headpiece, "HeronBridalMask");
