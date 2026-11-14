import * as T from "three";
import { BellPauldron } from "../src/vestments";
import { bake } from "./bake_glb";

// Each fitting has its own shoulder socket origin. The fitting clip exercises
// the same collar-to-arm rotation gradient used after IK in the browser.
for (const side of [-1, 1]) {
  const root = new T.Group(), collar = new T.Bone(), arm = new T.Bone();
  root.add(collar);
  collar.add(arm);
  const bronze = new T.MeshStandardMaterial({name:"Cast bronze", color:0xc7a777, metalness:.57, roughness:.62});
  const rim = new T.MeshStandardMaterial({name:"Worn gilt", color:0xc8af71, metalness:.75, roughness:.55});
  const lacquer = new T.MeshStandardMaterial({name:"Oxide red lacquer", color:0x68372b, metalness:.24, roughness:.39});
  const lining = new T.MeshStandardMaterial({name:"Padded lining", color:0x171c1b, metalness:.4, roughness:.35});
  const guard = new BellPauldron(root,arm,side,bronze,rim,lacquer,lining);
  const bands = guard.mount.children;
  const samples = bands.map(() => [] as number[]);
  const times = [0,.30,.65,1.05,1.45];
  bands.forEach((band,i) => {band.name = i === 0 ? "Crown" : "Lame"+i;});
  for (const rise of [0,.65,1.1,.42,0]) {
    arm.rotation.set(-rise*.48,side*rise*.17,side*rise);
    guard.pose();
    bands.forEach((band,i) => samples[i].push(...band.quaternion.toArray()));
  }
  const tracks = bands.map((band,i)=>new T.QuaternionKeyframeTrack(band.name+".quaternion",times,samples[i]));
  root.attach(guard.mount);
  await bake(guard.mount,side<0?"BellwardenRightPauldron":"BellwardenLeftPauldron",[
    new T.AnimationClip("Fitting lift",times[times.length-1],tracks),
  ]);
}
