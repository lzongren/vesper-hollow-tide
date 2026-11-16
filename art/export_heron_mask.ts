/** Bake the playable Heron headpiece in metres. Run with npx tsx art/export_heron_mask.ts. */
import { readFile, writeFile } from "node:fs/promises";
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
  if (child.name === "Porcelain") {
    const uv = (child as T.Mesh).geometry.getAttribute("uv");
    for (let i = 0; i < uv.count; i++) uv.setY(i, 1 - uv.getY(i));
  }
}
await bake(headpiece, "HeronBridalMask");

// Embed the original JPEG bytes. The headless exporter has no browser canvas
// for encoding an image, and the exchange asset needs to travel as one GLB.
const file = new URL("../native/Art/HeronBridalMask.glb", import.meta.url);
const glb = await readFile(file);
const jsonEnd = 20 + glb.readUInt32LE(12);
const gltf = JSON.parse(glb.toString("utf8", 20, jsonEnd));
const binary = glb.subarray(jsonEnd + 8);
const image = await readFile(new URL("../public/art/heron-porcelain.jpg", import.meta.url));
const imageView = gltf.bufferViews.length;
gltf.bufferViews.push({ buffer: 0, byteOffset: binary.length, byteLength: image.length });
gltf.images = [{ name: "Painted glaze", mimeType: "image/jpeg", bufferView: imageView }];
gltf.textures = [{ source: 0 }];
const glaze = gltf.materials.find((m: { name: string }) => m.name === "Porcelain");
glaze.pbrMetallicRoughness.baseColorTexture = { index: 0 };
gltf.buffers[0].byteLength = binary.length + image.length;
const json = Buffer.from(JSON.stringify(gltf));
const jsonPadding = Buffer.alloc((4 - json.length % 4) % 4, 0x20);
const binPadding = Buffer.alloc((4 - image.length % 4) % 4);
const header = Buffer.from(glb.subarray(0, 20));
const binHeader = Buffer.from(glb.subarray(jsonEnd, jsonEnd + 8));
header.writeUInt32LE(json.length + jsonPadding.length, 12);
binHeader.writeUInt32LE(binary.length + image.length + binPadding.length, 0);
header.writeUInt32LE(28 + header.readUInt32LE(12) + binHeader.readUInt32LE(0), 8);
await writeFile(file, Buffer.concat([header, json, jsonPadding, binHeader, binary, image, binPadding]));
