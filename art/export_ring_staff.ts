/** Bake the playable finial, shaft and six movable rings for Unreal Interchange.
 * Run with npx tsx art/export_ring_staff.ts. Requires Node 22 and the locked npm dependencies. */
import { writeFile } from "node:fs/promises";
import * as T from "three";
import { GLTFExporter } from "three/addons/exporters/GLTFExporter.js";
import { RingStaff } from "../src/ring-staff";

// GLTFExporter's binary path uses this one FileReader operation on Node.
class BinaryReader {
  result?: ArrayBuffer;
  onloadend?: () => void;
  async readAsArrayBuffer(blob: Blob) {
    this.result = await blob.arrayBuffer();
    this.onloadend?.();
  }
}
Object.defineProperty(globalThis, "FileReader", { value: BinaryReader, configurable: true });

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
const output = await new GLTFExporter().parseAsync(staff, { binary: true });
if (!(output instanceof ArrayBuffer)) throw Error("Expected a binary glTF asset");
await writeFile(new URL("../native/Art/SaintsRingStaff.glb", import.meta.url), new Uint8Array(output));
