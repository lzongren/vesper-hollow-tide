/** Append the playable Falling Prayers arm and finger motions to the source skin. */
import * as T from "three";
import { readFileSync, writeFileSync } from "node:fs";
import { CinderCast, sealTime } from "../src/cinder-cast";
import { Combat } from "../src/combat";
import { castFingers } from "../src/cinder-cast";

const source = readFileSync(new URL("../public/models/cinder-ascetic.glb",import.meta.url));
const jsonSize = source.readUInt32LE(12);
const model = JSON.parse(source.toString("utf8",20,20+jsonSize));
type Node = {name: string; children?: number[]; mesh?: number; translation?: number[]; rotation?: number[]; scale?: number[]; matrix?: number[]};
const nodes: Node[] = model.nodes;
const bones = nodes.map(n => {
  const bone = new T.Bone();
  if(n.matrix) new T.Matrix4().fromArray(n.matrix).decompose(bone.position,bone.quaternion,bone.scale);
  if(n.translation) bone.position.fromArray(n.translation);
  if(n.rotation) bone.quaternion.fromArray(n.rotation);
  if(n.scale) bone.scale.fromArray(n.scale);
  return bone;
});
nodes.forEach((n,i)=>n.children?.forEach(child=>bones[i].add(bones[child])));
const root = new T.Group(), scaled = new T.Group();
root.add(scaled);
for(const i of model.scenes[model.scene ?? 0].nodes) scaled.add(bones[i]);
const body = model.meshes[0].primitives[0];
const bounds = model.accessors[body.attributes.POSITION];
const size = 3.7/(bounds.max[1]-bounds.min[1]);
scaled.scale.setScalar(size);
scaled.position.set(-(bounds.min[0]+bounds.max[0])*.5*size,-bounds.min[1]*size,-(bounds.min[2]+bounds.max[2])*.5*size);
const indices = ["LeftArm","LeftForeArm","LeftHand"].map(name => nodes.findIndex(n=>n.name===name));
if(indices.includes(-1)) throw Error("Missing casting arm bone");
const [arm,fore,hand] = indices.map(i=>bones[i]);
const rig = new CinderCast(root,arm,fore,hand);
const rest = indices.map(i=>bones[i].quaternion.clone());
const frames: number[] = [], rotations: number[][] = [[],[],[]], weights: number[] = [];
const game = new Combat(2);
game.boss.attack=2;
game.emitAttack();
const windup=game.attack.windup, mark=game.hazards.find(h=>h.targeted)!;
const end=windup+mark.life+.25;
let open=0, closed=0;
for(let frame=0; frame<=Math.ceil(end*60); frame++){
  const time=frame/60;
  mark.age=Math.max(0,time-windup);
  const cast=sealTime(time<windup?"windup":"recover",true,time/windup,
    mark.age<mark.life?game.hazards:[]);
  indices.forEach((n,i)=>bones[n].quaternion.copy(rest[i]));
  root.updateMatrixWorld(true);
  rig.pose(cast,1/60);
  frames.push(time);
  indices.forEach((n,i)=>rotations[i].push(...bones[n].quaternion.toArray()));
  const fingers=castFingers(cast);
  open=T.MathUtils.damp(open,fingers.open,13,1/60);
  closed=T.MathUtils.damp(closed,fingers.closed,17,1/60);
  weights.push(open,closed);
}
const chunks: Buffer[]=[source.subarray(28+jsonSize)];
let offset=chunks[0].length;
function accessor(values: number[], type: "SCALAR" | "VEC4") {
  const data=Buffer.from(new Float32Array(values).buffer);
  const view=model.bufferViews.push({buffer:0,byteOffset:offset,byteLength:data.length})-1;
  chunks.push(data);
  offset+=data.length;
  return model.accessors.push({bufferView:view,componentType:5126,count:type==="VEC4"?values.length/4:values.length,
    type,...(type==="SCALAR"?{min:[Math.min(...values)],max:[Math.max(...values)]}:{})})-1;
}
const input=accessor(frames,"SCALAR");
const outputs=[...rotations.map(r=>accessor(r,"VEC4")),accessor(weights,"SCALAR")];
const meshNode=nodes.findIndex(n=>n.mesh===0);
if(meshNode<0) throw Error("Missing casting hand skin");
model.animations.push({name:"Falling Prayers",samplers:outputs.map(output=>({input,output,interpolation:"LINEAR"})),
  channels:[...indices,meshNode].map((node,i)=>({sampler:i,target:{node,path:i===3?"weights":"rotation"}}))});
model.buffers[0].byteLength=offset;
const json=Buffer.from(JSON.stringify(model)), padding=Buffer.alloc((4-json.length%4)%4,32);
const header=Buffer.from(source.subarray(0,20));header.writeUInt32LE(json.length+padding.length,12);
const binHeader=Buffer.from(source.subarray(20+jsonSize,28+jsonSize));binHeader.writeUInt32LE(offset);
header.writeUInt32LE(28+json.length+padding.length+offset,8);
writeFileSync(new URL("../native/Art/CinderSealCast.glb",import.meta.url),Buffer.concat([header,json,padding,binHeader,...chunks]));
