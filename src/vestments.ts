import * as T from "three";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";
import { angleDiff, type Attack } from "./combat";
import type { GripKey } from "./pilgrim";

// Wrist in actor space, followed by the azimuth and elevation of the long haft.
export const bellGuard: GripKey = [0, -0.32, 2.13, 0.52, -0.52, 1.05];
const hold = (key: GripKey, time: number): GripKey => [
  time,
  key[1],
  key[2],
  key[3],
  key[4],
  key[5],
];
interface Stroke {
  lift: GripKey[];
  strike: GripKey[];
  settle: GripKey[];
}
function stroke(lift: GripKey, contact: GripKey, follow: GripKey): Stroke {
  // Damage can start on the first active tick. The lead-in already carries the
  // bell into the strike; the remaining active interval is its follow-through.
  return {
    lift: [bellGuard, hold(lift, 0.7), hold(lift, 0.78), hold(contact, 1)],
    strike: [hold(contact, 0), hold(follow, 0.78), hold(follow, 1)],
    settle: [hold(follow, 0), hold(follow, 0.18), hold(bellGuard, 1)],
  };
}
const sweep = stroke(
  [0, -0.92, 2.58, 0.08, -1.88, 0.35],
  [0, -0.29, 2.02, 0.86, -0.25, 0.04],
  [0, 0.39, 1.84, 0.65, 1.3, -0.2],
);
const toll = stroke(
  [0, -0.33, 3.38, 0.15, -0.54, 1.96],
  [0, -0.26, 1.73, 0.83, 0.02, -0.34],
  [0, -0.25, 1.44, 0.68, 0.03, -0.57],
);
const charge = stroke(
  [0, -0.62, 2.1, 0.02, -0.82, 0.43],
  [0, -0.34, 2.17, 0.82, -0.1, 0.02],
  [0, -0.22, 2.04, 0.93, 0.1, -0.12],
);
export function bellStroke(shape: Attack["shape"], state: string) {
  const motion = shape === "circle" ? toll : shape === "dash" ? charge : sweep;
  if (state === "windup") return motion.lift;
  if (state === "active") return motion.strike;
  if (state === "recover") return motion.settle;
}

/** Each transverse cloth band lags its pinned neighbour. Spring in actor space
 * so clockwise turns and lateral rolls displace the free hem in opposite directions. */
export class MantleMotion {
  private last?: [number, number, number];
  private offsets = new Float32Array(16);
  private speeds = new Float32Array(16);
  private geometry: T.BufferGeometry;
  private base: Float32Array;
  private band: Float32Array;

  constructor(mesh: T.Mesh, dropAt?: (i: number) => number) {
    this.geometry = mesh.geometry;
    const p = this.geometry.attributes.position;
    this.base = new Float32Array(p.array);
    this.band = Float32Array.from(
      { length: p.count },
      (_, i) => (dropAt ? dropAt(i) : 1 - this.geometry.attributes.uv.getY(i)) * 7,
    );
    if (p instanceof T.BufferAttribute) p.setUsage(T.DynamicDrawUsage);
  }

  step(x: number, z: number, yaw: number, dt: number, t: number, roll: number) {
    const prev = this.last;
    this.last = [x, z, yaw];
    if (!prev || dt <= 0 || Math.hypot(x - prev[0], z - prev[1]) > 1.8) {
      this.offsets.fill(0);
      this.speeds.fill(0);
    } else {
      const dx = (x - prev[0]) / dt,
        dz = (z - prev[1]) / dt;
      const lateral = dx * Math.cos(yaw) - dz * Math.sin(yaw),
        forward = dz * Math.cos(yaw) + dx * Math.sin(yaw);
      const twist = T.MathUtils.clamp(angleDiff(yaw, prev[2]) / dt, -9, 9);
      const lagX = T.MathUtils.clamp(
        -0.048 * lateral + 0.024 * twist,
        -0.52,
        0.52,
      );
      const lagZ = T.MathUtils.clamp(
        -0.045 * forward - 0.24 * roll,
        -0.62,
        0.14,
      );
      const substeps = Math.ceil(Math.min(dt, 0.08) * 120),
        h = Math.min(dt, 0.08) / substeps;
      for (let step = 0; step < substeps; step++)
        for (let j = 1; j <= 7; j++)
          for (let axis = 0; axis < 2; axis++) {
            const k = j * 2 + axis;
            const target =
              this.offsets[k - 2] * 0.74 +
              ((axis === 0 ? lagX : lagZ) * j) / 15;
            this.speeds[k] +=
              ((target - this.offsets[k]) * 170 - this.speeds[k] * 16) * h;
            this.offsets[k] += this.speeds[k] * h;
          }
    }
    const p = this.geometry.attributes.position;
    for (let i = 0; i < p.count; i++) {
      const depth = this.band[i],
        j = Math.floor(depth),
        k = 2 * j,
        next = Math.min(14, k + 2),
        f = depth - j;
      const sx = T.MathUtils.lerp(this.offsets[k], this.offsets[next], f);
      const sz = T.MathUtils.lerp(
        this.offsets[k + 1],
        this.offsets[next + 1],
        f,
      );
      const bx = this.base[i * 3],
        by = this.base[i * 3 + 1],
        bz = this.base[i * 3 + 2],
        u = depth / 7;
      const pleat =
        Math.sin(t * 3.2 + bx * 14 - u * 4) *
        (0.012 + 0.032 * Math.min(1, Math.abs(sx) + Math.abs(sz))) *
        u *
        u;
      p.setXYZ(
        i,
        bx + sx,
        by + Math.min(0.25, (sx * sx + sz * sz) * 0.65) + roll * 0.13 * u * u,
        bz + sz + pleat,
      );
    }
    p.needsUpdate = true;
    this.geometry.computeVertexNormals();
  }
}

/** The collar carries the crown. Successive lames are tied progressively
 * closer to the upper arm so the guard opens when the elbow rises. */
export class BellPauldron {
  readonly mount = new T.Group();
  private readonly bands: T.Group[] = [];
  private readonly rest = new T.Quaternion();
  private readonly change = new T.Quaternion();
  private readonly identity = new T.Quaternion();
  private readonly base = new T.Quaternion();

  constructor(root: T.Group, private arm: T.Bone, side: number, metal: T.MeshStandardMaterial,
    border: T.Material, lacquer: T.Material, lining: T.Material) {
    const collar = arm.parent!;
    root.add(this.mount);
    arm.getWorldPosition(this.mount.position);
    root.worldToLocal(this.mount.position);
    collar.attach(this.mount);
    this.base.copy(this.mount.quaternion);
    this.rest.copy(arm.quaternion).invert();
    const crown = new T.Group();
    const shell = new T.SphereGeometry(1,40,20,0,Math.PI*2,0,1.58);
    shell.scale(.438,.32,.43);
    crown.add(new T.Mesh(shell, metal));
    const rim = new T.TorusGeometry(1,.025,7,52).rotateX(Math.PI/2)
      .scale(.437,.34,.431);
    crown.add(new T.Mesh(rim,border));
    const padding = new T.Mesh(new T.SphereGeometry(1,20,14),lining);
    padding.scale.set(.34,.34,.33);
    padding.position.y=-.13;
    crown.add(padding);

    // A horned river guardian in repoussé on the outward-facing crown.
    // A single deformed surface gives the eyes, jaw and brow shared highlights.
    const relief = new T.SphereGeometry(1,64,40);
    const pos=relief.attributes.position;
    const colors=new Float32Array(pos.count*3);
    const bronzeTone=new T.Color(0xffdfaa), patina=new T.Color(0x48645a);
    const tint=new T.Color();

    const hill=(u:number,v:number,w:number,h:number)=>Math.exp(-((u/w)**2+(v/h)**2));
    for(let i=0;i<pos.count;i++){
      const u=pos.getX(i), v=pos.getY(i), z=pos.getZ(i), abs=Math.abs(u);
      const brow=hill(abs-.40,v-.27-.15*abs,.33,.15);
      const eye=hill(abs-.39,v-.13,.21,.10);
      const muzzle=hill(abs-.24,v+.22,.22,.20);
      const nose=hill(u,v+.02,.20,.35);
      const lip=hill(u,v+.53,.43,.09);
      const cheek=hill(abs-.71,v+.03,.12,.45);
      const depth=.122*z+T.MathUtils.smoothstep(z,.04,.55)*
        (.082*brow-.041*eye+.076*muzzle+.106*nose+.030*lip+.029*cheek);
      const tarnish = .20 + .36*eye + .15*hill(abs-.57,v+.38,.19,.19)
        + .13*Math.sin(8*u+3*v)*Math.cos(7*v-z);
      tint.copy(bronzeTone).lerp(patina,tarnish).multiplyScalar(.93+.09*brow+.08*nose);
      tint.toArray(colors,3*i);
      pos.setXYZ(i,.263*u*(1+.15*v),.257*v,depth);
    }
    relief.setAttribute("color",new T.BufferAttribute(colors,3));
    relief.computeVertexNormals();
    const badge=new T.Group();badge.position.set(side*.20,.12,.255);
    badge.rotation.y=side*.61;
    const casting=metal.clone();
    casting.vertexColors=true;
    badge.add(new T.Mesh(relief,casting));
    const ornaments:T.BufferGeometry[]=[];
    const wire=(pts:number[][],r:number,taper=false)=>{
      const path=new T.CatmullRomCurve3(pts.map(([x,y,z])=>new T.Vector3(x,y,z)));
      const tube=new T.TubeGeometry(path,18,r,7,false);
      if (taper) {
        const center=new T.Vector3(), point=new T.Vector3();
        const attr=tube.attributes.position;
        for (let ring=0;ring<=18;ring++) {
          const t=ring/18;
          path.getPointAt(t,center);
          for(let j=0;j<=7;j++){
            const k=ring*8+j;
            point.fromBufferAttribute(attr,k).sub(center).multiplyScalar(1.65*(1-t)**.72+.04).add(center);
            attr.setXYZ(k,point.x,point.y,point.z);
          }
        }
        tube.computeVertexNormals();
      }
      ornaments.push(tube);
    };
    for(const sign of [-1,1]){
      wire([[sign*.052,.218,.08],[sign*.124,.307,.092],[sign*.234,.331,.067],
        [sign*.262,.351,.03],[sign*.288,.382,-.014]],.026,true);
      wire([[sign*.025,.074,.177],[sign*.084,.101,.192],[sign*.158,.132,.150],
        [sign*.207,.164,.088]],.014);
      wire([[sign*.056,-.062,.170],[sign*.141,-.093,.161],[sign*.238,-.071,.087],
        [sign*.261,-.016,.061]],.012);
      ornaments.push(new T.SphereGeometry(1,13,8).scale(.031,.015,.018)
        .translate(sign*.104,.039,.113));
    }
    const crest=new T.Mesh(mergeGeometries(ornaments)!,border);
    ornaments.forEach(g=>g.dispose());
    badge.add(crest);crown.add(badge);
    this.bands.push(crown);
    for (let row = 0; row < 4; row++) {
      const band = new T.Group();
      const vertices: number[] = [],
        uvs: number[] = [],
        indices: number[] = [];
      const trimPoints: T.Vector3[] = [];
      for (let i = 0; i <= 32; i++) {
        const u = i / 32,
          angle = (u - 0.5) * 3.36;
        const edge = Math.cos(angle * 0.89),
          radius = .357 + row * .026;
        for (let j = 0; j <= 4; j++) {
          const v = j / 4,
            r = radius + 0.073 * v;
          const x = side * (Math.cos(angle) * r + 0.016 * row);
          const y =
            0.14 -
            .144 * row -
            .211 * v -
            0.09 * edge -
            0.048 * Math.sin(Math.PI * u * 3) ** 2 * v;
          const z = Math.sin(angle) * r;
          vertices.push(x, y, z);
          uvs.push(u, 1 - v);
          if (j === 4) trimPoints.push(new T.Vector3(x, y, z));
          if (i && j) {
            const b = i * 5 + j;
            if (side === 1) indices.push(b - 6, b - 1, b, b - 6, b, b - 5);
            else indices.push(b - 6, b, b - 1, b - 6, b - 5, b);
          }
        }
      }
      const geometry = new T.BufferGeometry();
      geometry.setAttribute(
        "position",
        new T.Float32BufferAttribute(vertices, 3),
      );
      geometry.setAttribute("uv", new T.Float32BufferAttribute(uvs, 2));
      geometry.setIndex(indices);
      geometry.computeVertexNormals();
      band.add(new T.Mesh(geometry,row % 2 === 0 ? lacquer : metal));
      const fittings:T.BufferGeometry[]=[
        new T.TubeGeometry(new T.CatmullRomCurve3(trimPoints),32,.012,6,false)
      ];
      // Overlaid arches on each plate echo the mouths of the votive bells.
      for(const k of [4,10,16,22,28]){
        const points=trimPoints.slice(k-2,k+3).map((point,j)=>{
          const v=point.clone();
          v.y+=.034+.060*Math.sin(j*Math.PI/4);
          v.x+=side*.011;
          return v;
        });
        fittings.push(new T.TubeGeometry(new T.CatmullRomCurve3(points),8,.007,5,false));
        const stud=trimPoints[k];
        fittings.push(new T.SphereGeometry(.021,10,7).translate(stud.x,stud.y+.11,stud.z));
      }
      band.add(new T.Mesh(mergeGeometries(fittings)!,border));
      fittings.forEach(g=>g.dispose());
      this.bands.push(band);
    }
    this.mount.add(...this.bands);
    this.mount.traverse(o=>{if(o instanceof T.Mesh)o.castShadow=o.receiveShadow=true;});
  }

  pose() {
    // Convert the arm's pose relative to its parent into the guard's bind
    // frame. Torso rotation and the source rig's centimetre scale cancel.
    this.change.copy(this.base).invert().multiply(this.arm.quaternion)
      .multiply(this.rest).multiply(this.base);
    for(let i=0;i<this.bands.length;i++)
      this.bands[i].quaternion.slerpQuaternions(this.identity,this.change,.27+i*.155);
  }
}
