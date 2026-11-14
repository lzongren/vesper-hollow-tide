/** Cut stone paving and a six-sided votive lantern for the mountain road. */
import * as T from "three";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";
import { bake } from "./bake_glb";
import { readFile, writeFile } from "node:fs/promises";

let state = 23983;
function random() {
  state = (Math.imul(state, 1664525) + 1013904223) >>> 0;
  return state / 4294967296;
}
function finish(name: string, geometry: T.BufferGeometry[], material: T.MeshStandardMaterial) {
  const mesh = new T.Mesh(mergeGeometries(geometry), material);
  mesh.name = name;
  return mesh;
}

const stone = new T.MeshStandardMaterial({ color: 0x808484, roughness: .56, vertexColors: true });
stone.name = "Rain darkened grey flagstone";
const stones: T.BufferGeometry[] = [];
const size = 8.3;
// Rows share end points across kits. Staggered headers break the square module.
for (let row = 0; row < 16; row++) {
  const n = 6 + Math.floor(random() * 4);
  const widths = Array.from({length: n}, () => .6 + random() * .9);
  const total = widths.reduce((a,b)=>a+b);
  let left = -size/2;
  for (const weight of widths) {
    const right = left + size * weight / total;
    const bottom = -size/2 + row * size/16, top = bottom + size/16;
    const x0=left+.009, x1=right-.009, z0=bottom+.012, z1=top-.012;
    const cut = .026+random()*.06;
    const outline=[[x0+cut,z0],[x0,z0+cut],[x0,z1-cut],[x0+cut,z1],
      [x1-cut,z1],[x1,z1-cut],[x1,z0+cut],[x1-cut,z0]];
    const positions:number[]=[], uv:number[]=[], colors:number[]=[];
    const tone=.52+random()*.46, center=[(x0+x1)/2,(z0+z1)/2];
    const h=.01+random()*.026, offset=[random()*3,random()*3];
    const lower=outline.map(([x,z])=>[x,-.095,z]);
    const bevel=outline.map(([x,z])=>[x,h-.022,z]);
    const upper=outline.map(([x,z])=>[T.MathUtils.lerp(x,center[0],.061),h,T.MathUtils.lerp(z,center[1],.08)]);
    function tri(a:number[],b:number[],c:number[],shade:number) {
      for (const [x,y,z] of [a,b,c]) {
        positions.push(x,y,z); uv.push(x/1.6+offset[0],z/1.6+offset[1]);
        colors.push(tone*shade,tone*shade,tone*shade);
      }
    }
    for(let i=0;i<8;i++){
      const j=(i+1)%8;
      tri([center[0],h+.003,center[1]],upper[i],upper[j],1);
      tri(upper[i],bevel[i],bevel[j],.85);tri(upper[i],bevel[j],upper[j],.85);
      tri(bevel[i],lower[i],lower[j],.43);tri(bevel[i],lower[j],bevel[j],.43);
    }
    const geo=new T.BufferGeometry();
    geo.setAttribute("position",new T.Float32BufferAttribute(positions,3));
    geo.setAttribute("uv",new T.Float32BufferAttribute(uv,2));
    geo.setAttribute("color",new T.Float32BufferAttribute(colors,3));
    geo.computeVertexNormals();stones.push(geo);left=right;
  }
}
const road=new T.Group();road.add(finish("Dressed shale pavers",stones,stone));
await bake(road,"ProcessionPaving");

// Embed the repository's scanned color and normal in the production GLB.
const path=new URL("../native/Art/ProcessionPaving.glb",import.meta.url);
const raw=await readFile(path), oldJson=raw.readUInt32LE(12);
const doc=JSON.parse(raw.toString("utf8",20,20+oldJson));
const blocks=[raw.subarray(28+oldJson)];
let length=blocks[0].length;
doc.images=[];doc.textures=[];doc.samplers=[{wrapS:10497,wrapT:10497}];
for(const channel of ["color","normal"]) {
  const bytes=await readFile(new URL("../public/textures/stone-"+channel+".jpg",import.meta.url));
  const padding=Buffer.alloc((4-length%4)%4);blocks.push(padding);length+=padding.length;
  const index=doc.bufferViews.push({buffer:0,byteOffset:length,byteLength:bytes.length})-1;
  doc.images.push({name:"Shale_"+channel,bufferView:index,mimeType:"image/jpeg"});
  doc.textures.push({source:doc.images.length-1,sampler:0}); blocks.push(bytes);length+=bytes.length;
}
doc.materials[0].pbrMetallicRoughness.baseColorTexture={index:0};
doc.materials[0].normalTexture={index:1,scale:.8};doc.buffers[0].byteLength=length;
const binary=Buffer.concat([...blocks,Buffer.alloc((4-length%4)%4)]);
const encoded=Buffer.from(JSON.stringify(doc));
const json=Buffer.concat([encoded,Buffer.alloc((4-encoded.length%4)%4,32)]);
const header=Buffer.from(raw.subarray(0,20)),chunk=Buffer.from(raw.subarray(20+oldJson,28+oldJson));
header.writeUInt32LE(28+json.length+binary.length,8);header.writeUInt32LE(json.length,12);
chunk.writeUInt32LE(binary.length,0);await writeFile(path,Buffer.concat([header,json,chunk,binary]));

const lantern=new T.Group();
const bronze=new T.MeshStandardMaterial({color:0x655039,metalness:.76,roughness:.43});
const jade=new T.MeshStandardMaterial({color:0x4d5c57,roughness:.77});
const gold=new T.MeshStandardMaterial({color:0xb38744,metalness:.7,roughness:.38});
const light=new T.MeshStandardMaterial({color:0xffc368,emissive:0xff6821,emissiveIntensity:2.3,roughness:.9});
const batches=new Map([[bronze,[]],[jade,[]],[gold,[]],[light,[]]] as [T.MeshStandardMaterial,T.BufferGeometry[]][]);
function part(g:T.BufferGeometry,m:T.MeshStandardMaterial,x=0,y=0,z=0,angle=0) {
  g.rotateY(angle);g.translate(x,y,z);batches.get(m)!.push(g.index?g.toNonIndexed():g);
}
function ring(y:number,bottom:number,top:number,height:number,mat:T.MeshStandardMaterial,sides=8){
  part(new T.CylinderGeometry(top,bottom,height,sides),mat,0,y,0);
}
function rod(a:T.Vector3,b:T.Vector3,width:number,m:T.MeshStandardMaterial) {
  const delta=b.clone().sub(a);const geo=new T.CylinderGeometry(width,width,delta.length(),6);
  geo.applyQuaternion(new T.Quaternion().setFromUnitVectors(new T.Vector3(0,1,0),delta.normalize()));
  const mid=a.clone().lerp(b,.5);part(geo,m,mid.x,mid.y,mid.z);
}
for(const [y,lo,hi,h] of [[.08,.5,.5,.16],[.21,.49,.37,.1],[.32,.38,.42,.12],[.44,.41,.24,.12],
  [.89,.22,.16,.84],[1.39,.17,.34,.18],[1.53,.4,.46,.13],[1.63,.46,.38,.08]])ring(y,lo,hi,h,jade);
for(const y of [.37,.51,1.28,1.53,1.67])ring(y,y<1.3?.225:.405,y<1.3?.225:.405,.025,gold);
ring(1.99,.315,.315,.65,light,6);
const polar=(angle:number,r:number,h:number)=>new T.Vector3(Math.cos(angle)*r,h,Math.sin(angle)*r);
for(let k=0;k<6;k++) {
  const a=k*Math.PI/3+Math.PI/6,b=a+Math.PI/3;
  const start=polar(a,.36,1.64),end=polar(b,.36,1.64);
  rod(start,polar(a,.36,2.35),.039,bronze);
  for(const y of [1.7,1.82,2.2,2.31])rod(polar(a,.36,y),polar(b,.36,y),.015,gold);
  const point=(t:number,y:number)=>start.clone().lerp(end,t).setY(y);
  for(const [u,v] of [[0,.5],[.5,1]]) {
    rod(point(u,1.9),point(v,2.15),.011,bronze);rod(point(u,2.15),point(v,1.9),.011,bronze);
  }
  // Upturned corners and a bell on each end of the eave.
  rod(polar(a,.34,2.49),polar(a,.59,2.45),.034,gold);
  rod(polar(a,.59,2.45),polar(a,.69,2.54),.026,gold);
  const tip=polar(a,.64,2.34);
  rod(tip,tip.clone().setY(2.47),.008,bronze);
  part(new T.CylinderGeometry(.022,.048,.065,8),gold,tip.x,tip.y,tip.z);
}
for(const [y,lo,hi,h] of [[2.36,.52,.57,.06],[2.43,.62,.42,.11],[2.55,.43,.26,.14],[2.67,.26,.12,.1]])
  ring(y,lo,hi,h,bronze,6);
ring(2.76,.14,.065,.1,gold);ring(2.92,.085,0,.25,bronze);
for(const [mat,list] of batches) {
  mat.name=mat===jade?"Carved grey stone":mat===bronze?"Patinated bronze":mat===gold?"Worn brass":"Amber silk";
  lantern.add(finish(mat.name,list,mat));
}
await bake(lantern,"ProcessionLantern");
