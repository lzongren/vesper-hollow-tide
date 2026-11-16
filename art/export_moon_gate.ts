/** Bake the playable roof, brackets, columns and lamp in glTF metres. */
import * as T from "three";
import { moonGatePorch } from "../src/moon-gate";
import { bake } from "./bake_glb";

const porch = moonGatePorch({
  timber: new T.MeshStandardMaterial({
    name: "Lacquered timber",
    color: 0x723b2b,
    roughness: 0.61,
  }),
  ceramic: new T.MeshPhysicalMaterial({
    name: "Glazed roof tile",
    color: 0x506e68,
    roughness: 0.44,
    clearcoat: 0.46,
    clearcoatRoughness: 0.31,
  }),
  bronze: new T.MeshStandardMaterial({
    name: "Weathered bronze",
    color: 0xb1935c,
    metalness: 0.72,
    roughness: 0.45,
  }),
  stone: new T.MeshStandardMaterial({
    name: "Carved stone",
    color: 0x80877e,
    roughness: 0.84,
  }),
  paper: new T.MeshStandardMaterial({
    name: "Lantern paper",
    color: 0xf2bc83,
    emissive: 0xff8f42,
    emissiveIntensity: 1.28,
    roughness: 0.89,
  }),
});
for (const child of porch.children) {
  child.name = (child as T.Mesh<T.BufferGeometry, T.Material>).material.name;
}
await bake(porch, "MoonGatePorch");
