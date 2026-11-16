import * as T from "three";
import { waterGallery } from "../src/landmarks";
import { bake } from "./bake_glb";

const stone = new T.MeshStandardMaterial({
  name: "Stone footing",
  color: 0x929284,
  roughness: 0.87,
});
const timber = new T.MeshStandardMaterial({
  name: "Red lacquer timber",
  color: 0x80422e,
  roughness: 0.67,
});
const tile = new T.MeshStandardMaterial({
  name: "Celadon tiles",
  color: 0x506e68,
  roughness: 0.44,
  side: T.DoubleSide,
});
const paper = new T.MeshStandardMaterial({
  name: "Lantern silk",
  color: 0xe9bd92,
  emissive: 0xe39553,
  emissiveIntensity: 0.8,
});
const dark = new T.MeshStandardMaterial({
  name: "Lantern chain",
  color: 0x322f2b,
  roughness: 0.83,
});
const gallery = waterGallery(
  { rock: stone, wall: stone, dark },
  tile,
  timber,
  paper,
);
gallery.position.set(0, 0, 0);
gallery.rotation.set(0, 0, 0);
await bake(gallery, "WestWaterGallery");
