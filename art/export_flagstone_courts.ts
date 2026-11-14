import { readFile, writeFile } from "node:fs/promises";
import * as T from "three";
import { flagstoneSeal } from "../src/flagstone-seal";
import { bake } from "./bake_glb";

// Preserve the prepared JPEGs byte-for-byte. GLTFExporter normally needs a
// browser canvas to re-encode its material images; the Node build has none.
async function embedStoneMaps(file: URL, court: string) {
  const glb = await readFile(file);
  const endJson = 20 + glb.readUInt32LE(12);
  const doc = JSON.parse(glb.toString("utf8", 20, endJson));
  const chunks = [glb.subarray(endJson + 8)];
  let offset = chunks[0].length;
  doc.images = [];
  doc.textures = [];
  for (const channel of ["inlay", "relief", "surface"]) {
    const data = await readFile(new URL(`../public/art/${court}-${channel}.jpg`, import.meta.url));
    const bufferView = doc.bufferViews.push({ buffer: 0, byteOffset: offset, byteLength: data.length }) - 1;
    const source = doc.images.push({ bufferView, mimeType: "image/jpeg" }) - 1;
    doc.textures.push({ source });
    const padding = Buffer.alloc((4 - data.length % 4) % 4);
    chunks.push(data, padding);
    offset += data.length + padding.length;
  }
  const material = doc.materials[0];
  Object.assign(material.pbrMetallicRoughness, {
    baseColorTexture: { index: 0 }, metallicRoughnessTexture: { index: 2 },
    roughnessFactor: 1, metallicFactor: 1,
  });
  material.normalTexture = { index: 1 };
  doc.buffers[0].byteLength = offset;
  const json = Buffer.from(JSON.stringify(doc));
  const padded = Buffer.alloc(Math.ceil(json.length / 4) * 4, 0x20);
  json.copy(padded);
  const header = Buffer.from(glb.subarray(0, 20));
  header.writeUInt32LE(28 + padded.length + offset, 8);
  header.writeUInt32LE(padded.length, 12);
  const binHeader = Buffer.from(glb.subarray(endJson, endJson + 8));
  binHeader.writeUInt32LE(offset, 0);
  await writeFile(file, Buffer.concat([header, padded, binHeader, ...chunks]));
}

for (const [index, name] of ["Belfry", "Heron", "Cinder"].entries()) {
  let seed = 1901 + index;
  const random = () => {
    seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
    return seed / 4294967296;
  };
  const group = new T.Group();
  const geometry = flagstoneSeal(random);
  // glTF samples from the upper-left; the live TextureLoader flips its JPEGs.
  const uv = geometry.getAttribute("uv");
  for (let i = 0; i < uv.count; i++) uv.setY(i, 1 - uv.getY(i));
  const stone = new T.MeshStandardMaterial({
    name: `${name} mosaic`, vertexColors: true, roughness: 1,
    color: index === 0 ? 0xf1eee2 : 0xf5f1e7,
  });
  group.add(new T.Mesh(geometry, stone));
  await bake(group, `${name}Flagstones`);
  await embedStoneMaps(new URL(`../native/Art/${name}Flagstones.glb`, import.meta.url), name.toLowerCase());
}
