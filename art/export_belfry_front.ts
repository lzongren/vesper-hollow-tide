import { readFile, writeFile } from "node:fs/promises";
import * as T from "three";
import { belfryFront } from "../src/belfry-front";
import { bake } from "./bake_glb";

// GLTFExporter on Node has no canvas JPEG encoder. Preserve the four local
// JPEGs as exact binary buffer views and bind them to the exported materials.
const files = ["art/belfry-dragon-beam.jpg", "art/belfry-paper.jpg", "textures/wood-color.jpg", "textures/rock-color.jpg"];
const textures = files.map(() => new T.Texture());
const front = belfryFront(textures[0], textures[1], textures[2], textures[3]);
const maps = new Map<string, {color: number; emission: number}>();
front.traverse(o => {
  if (!(o instanceof T.Mesh)) return;
  const mat = o.material as T.MeshStandardMaterial;
  maps.set(mat.name, {color:textures.indexOf(mat.map!), emission:textures.indexOf(mat.emissiveMap!)});
  mat.map = mat.emissiveMap = null;
  // glTF has a top-left image origin; all browser inputs use TextureLoader.
  const uv = o.geometry.getAttribute("uv");
  for(let i=0;i<uv.count;i++) uv.setY(i,1-uv.getY(i));
});
await bake(front,"BelfryPaintedFront");
const file = new URL("../native/Art/BelfryPaintedFront.glb", import.meta.url);
const src = await readFile(file);
const end = 20 + src.readUInt32LE(12);
const doc = JSON.parse(src.toString("utf8",20,end));
const chunks = [src.subarray(end+8)];
let offset = chunks[0].length;
doc.images = [];
doc.textures = [];
for(const path of files) {
  const image = await readFile(new URL("../public/"+path,import.meta.url));
  const view = doc.bufferViews.push({buffer:0,byteOffset:offset,byteLength:image.length})-1;
  const source = doc.images.push({bufferView:view,mimeType:"image/jpeg"})-1;
  doc.textures.push({source});
  const pad = Buffer.alloc((4-image.length%4)%4);
  chunks.push(image,pad);
  offset += image.length+pad.length;
}
for(const material of doc.materials) {
  const map = maps.get(material.name)!;
  if(map.color >= 0)material.pbrMetallicRoughness.baseColorTexture = {index:map.color};
  if(map.emission >= 0)material.emissiveTexture = {index:map.emission};
}
doc.buffers[0].byteLength = offset;
const json = Buffer.from(JSON.stringify(doc));
const padded = Buffer.alloc(Math.ceil(json.length/4)*4,0x20);
json.copy(padded);
const header = Buffer.from(src.subarray(0,20)), binaryHeader = Buffer.from(src.subarray(end,end+8));
header.writeUInt32LE(28+padded.length+offset,8);
header.writeUInt32LE(padded.length,12);
binaryHeader.writeUInt32LE(offset,0);
await writeFile(file,Buffer.concat([header,padded,binaryHeader,...chunks]));
