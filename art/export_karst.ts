/** Package the garden geography, beacon and limestone albedo in one native asset. */
import { readFile, writeFile } from "node:fs/promises";
import * as T from "three";
import { karstSpurs } from "../src/karst";
import { bake } from "./bake_glb";

const group = karstSpurs(1, new T.Texture());
const cliff = group.getObjectByName("Limestone spurs") as T.Mesh<
  T.BufferGeometry,
  T.MeshStandardMaterial
>;
cliff.material.name = "Pale karst limestone";
cliff.material.map = null;
cliff.material.bumpMap = null;
// glTF uses the opposite image origin to a browser-loaded Three texture.
const uv = cliff.geometry.getAttribute("uv");
for (let i = 0; i < uv.count; i++) uv.setY(i, 1 - uv.getY(i));
await bake(group, "GardenRidges");

const path = new URL("../native/Art/GardenRidges.glb", import.meta.url);
const base = await readFile(path),
  jsonLength = base.readUInt32LE(12);
const gltf = JSON.parse(base.toString("utf8", 20, 20 + jsonLength));
const binary = base.subarray(28 + jsonLength);
const image = await readFile(
  new URL("../public/art/karst-limestone.jpg", import.meta.url),
);
const index = gltf.bufferViews.length;
gltf.bufferViews.push({
  buffer: 0,
  byteOffset: binary.length,
  byteLength: image.length,
});
gltf.images = [
  { bufferView: index, mimeType: "image/jpeg", name: "Eroded limestone" },
];
gltf.samplers = [
  { wrapS: 33648, wrapT: 33648, magFilter: 9729, minFilter: 9987 },
];
gltf.textures = [{ source: 0, sampler: 0 }];
const material = gltf.materials.find(
  (m: { name?: string }) => m.name === cliff.material.name,
);
material.pbrMetallicRoughness.baseColorTexture = { index: 0 };
gltf.buffers[0].byteLength = binary.length + image.length;
const json = Buffer.from(JSON.stringify(gltf));
const jsonPadding = Buffer.alloc((4 - (json.length % 4)) % 4, 0x20);
const binaryPadding = Buffer.alloc((4 - (image.length % 4)) % 4);
const header = Buffer.from(base.subarray(0, 20)),
  binHeader = Buffer.from(base.subarray(20 + jsonLength, 28 + jsonLength));
header.writeUInt32LE(json.length + jsonPadding.length, 12);
binHeader.writeUInt32LE(binary.length + image.length + binaryPadding.length, 0);
header.writeUInt32LE(
  28 + header.readUInt32LE(12) + binHeader.readUInt32LE(0),
  8,
);
await writeFile(
  path,
  Buffer.concat([
    header,
    json,
    jsonPadding,
    binHeader,
    binary,
    image,
    binaryPadding,
  ]),
);
