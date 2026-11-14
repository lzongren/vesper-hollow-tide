/** Bake the playable finial, shaft and six movable rings for Unreal Interchange.
 * Run with npx tsx art/export_ring_staff.ts. Requires Node 22 and the locked npm dependencies. */
import { bake } from "./bake_glb";
import * as T from "three";
import { RingStaff } from "../src/ring-staff";

const materials = [
  new T.MeshStandardMaterial({ name: "Lacquered wood", color: 0x61382c, roughness: .50 }),
  new T.MeshStandardMaterial({ name: "Worn bronze", color: 0xc8af71, metalness: .78, roughness: .42 }),
  new T.MeshStandardMaterial({ name: "Grip binding", color: 0x171c1b, metalness: .40, roughness: .35 }),
  new T.MeshStandardMaterial({ name: "Ember", emissive: 0xffb553, emissiveIntensity: 3 }),
] as const;
const staff = new RingStaff(...materials);
staff.name = "SaintsRingStaff";
const solidNames = ["Shaft", "WrappedGrip", "BronzeFinial", "Ember"];
let ring = 0;
for (const child of staff.children) {
  const mesh = child as T.Mesh;
  mesh.name = mesh.geometry.type === "TorusGeometry"
    ? "LooseRing_" + ++ring
    : solidNames.shift()!;
}
await bake(staff, "SaintsRingStaff");
