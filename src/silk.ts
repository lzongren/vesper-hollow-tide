import * as T from "three";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";

const cols = 6,
  rows = 8,
  width = cols + 1;
const v = new T.Vector3(),
  delta = new T.Vector3(),
  restPoint = new T.Vector3();
const matrix = new T.Matrix4(),
  inverse = new T.Matrix4();

export interface Cut {
  side: number; // -1 and 1 are the two front skirts; 0 is the broad back panel.
  back: boolean;
  shoulder: boolean;
}
function pattern(cut: Cut, u: number, t: number, h: number) {
  const across = 2 * u - 1,
    s = cut.side;
  const pleat =
    Math.cos((u * 3.0 + t * 0.13) * Math.PI * 2) * (0.005 + 0.011 * t);
  let x: number, y: number, z: number;
  if (cut.back) {
    const a = across * (cut.shoulder ? 1.54 : 1.27);
    x = Math.sin(a) * (cut.shoulder ? 0.082 + 0.142 * t : 0.142 + 0.08 * t);
    z =
      -Math.cos(a) * (cut.shoulder ? 0.077 + 0.074 * t : 0.089 + 0.111 * t) -
      0.025 -
      pleat;
    y = cut.shoulder
      ? 0.852 - 0.245 * t + 0.036 * across ** 2 * t
      : 0.71 - 0.511 * t + 0.077 * across ** 2 * t;
    // The short cape hangs from the neckline and both upper arms. Three
    // overlapping tension folds sag towards the centre of the back.
    if (cut.shoulder) {
      const span = Math.sin(Math.PI * u);
      const slack = span * Math.sin(Math.PI * t);
      const seam = t - .37 * span + .055 * across;
      let relief = 0;
      for (const ridge of [.04, .28, .56]) {
        const d = (seam - ridge) / .083;
        relief += .023 * Math.exp(-d * d) - .011 * Math.exp(-2 * (d - 1.15) ** 2);
      }
      z -= slack * relief;
      y -= .023 * slack * span;
    }
  } else {
    const a = (0.02 + u * 1.64) * s;
    x = Math.sin(a) * (0.116 + 0.07 * t) + s * (0.006 + 0.01 * t);
    z = Math.cos(a) * (0.096 + 0.055 * t) + 0.004 + pleat;
    y = 0.617 - t * (0.398 - 0.07 * u) - 0.016 * Math.sin(Math.PI * u) * t;
  }
  return new T.Vector3(x * h, y * h, z * h);
}
function silkMaterial(map: T.Texture, lining: T.Color, trim: T.Color) {
  const mat = new T.MeshPhysicalMaterial({
    map,
    side: T.DoubleSide,
    roughness: 0.67,
    sheen: 0.44,
    sheenColor: 0xb99e81,
    sheenRoughness: 0.74,
  });
  mat.onBeforeCompile = (shader) => {
    shader.uniforms.silkLining = { value: lining };
    shader.uniforms.silkEdge = { value: trim };
    shader.fragmentShader = shader.fragmentShader
      .replace(
        "#include <common>",
        "#include <common>\nuniform vec3 silkLining, silkEdge;",
      )
      .replace(
        "#include <map_fragment>",
        `#include <map_fragment>
        vec2 p=vMapUv;
        float hem=min(min(p.x,1.-p.x),p.y);
        float band=1.-smoothstep(.006,.012,hem);
        float couch=(1.-smoothstep(.002,.005,abs(hem-.025)))*.84;
        if(!gl_FrontFacing){diffuseColor.rgb=silkLining*(.72+.38*dot(diffuseColor.rgb,vec3(.25,.6,.15)));}
        diffuseColor.rgb=mix(diffuseColor.rgb,silkEdge,max(band,couch));`,
      );
  };
  return mat;
}

type Link = { a: number; b: number; length: number };
/** Coarse inextensible cloth is stepped in world space. A finer sewing pattern
 * interpolates the displacement and preserves the cut's small rest folds. */
export class SilkPanel {
  readonly mesh: T.Mesh;
  private base: T.Vector3[] = [];
  private current: T.Vector3[] = [];
  private previous: T.Vector3[] = [];
  private targets: T.Vector3[] = [];
  private links: Link[] = [];
  private skin: { i: number; u: number; t: number }[] = [];
  private rest: Float32Array;
  private lastRoot = new T.Vector3(Infinity, 0, 0);
  private bind: T.Matrix4;
  constructor(
    private root: T.Group,
    private anchor: T.Bone,
    private cut: Cut,
    private height: number,
    material: T.Material,
    private knees: readonly T.Bone[],
    private elbows: readonly T.Bone[] = [],
  ) {
    root.updateWorldMatrix(true, true);
    this.bind = anchor.matrixWorld.clone().invert().multiply(root.matrixWorld);
    for (let j = 0; j <= rows; j++)
      for (let i = 0; i <= cols; i++) {
        const p = pattern(cut, i / cols, j / rows, height);
        this.base.push(p);
        this.current.push(p.clone());
        this.previous.push(p.clone());
        this.targets.push(p.clone());
      }
    const link = (a: number, b: number) =>
      this.links.push({ a, b, length: this.base[a].distanceTo(this.base[b]) });
    for (let j = 0; j <= rows; j++)
      for (let i = 0; i <= cols; i++) {
        const k = j * width + i;
        if (i < cols) link(k, k + 1);
        if (j < rows) link(k, k + width);
        if (i < cols && j < rows) {
          link(k, k + width + 1);
          link(k + 1, k + width);
        }
      }
    const nx = 32,
      ny = 32,
      g = new T.PlaneGeometry(1, 1, nx, ny);
    const attr = g.attributes.position,
      uv = g.attributes.uv;
    for (let i = 0; i < attr.count; i++) {
      const u = uv.getX(i),
        t = 1 - uv.getY(i);
      const p = pattern(cut, u, t, height);
      // Continue one embroidered motif across both front skirts.
      if (!cut.back) uv.setX(i, 0.5 + 0.5 * cut.side * u);
      attr.setXYZ(i, p.x, p.y, p.z);
      const c = Math.min(cols - 1, Math.floor(u * cols)),
        r = Math.min(rows - 1, Math.floor(t * rows));
      this.skin.push({ i: r * width + c, u: u * cols - c, t: t * rows - r });
    }
    // UVs run left to right looking at the outside face.
    if (cut.back || cut.side < 0) {
      const ix = g.index!;
      for (let i = 0; i < ix.count; i += 3) {
        const tmp = ix.getX(i);
        ix.setX(i, ix.getX(i + 1));
        ix.setX(i + 1, tmp);
      }
    }
    this.rest = new Float32Array(attr.array);
    (attr as T.BufferAttribute).setUsage(T.DynamicDrawUsage);
    g.computeVertexNormals();
    this.mesh = new T.Mesh(g, material);
    this.mesh.castShadow = this.mesh.receiveShadow = true;
    this.mesh.frustumCulled = false;
    root.add(this.mesh);
  }
  update(dt: number, time: number) {
    this.anchor.updateWorldMatrix(true, false);
    matrix.multiplyMatrices(this.anchor.matrixWorld, this.bind);
    inverse.copy(this.root.matrixWorld).invert();
    const reset =
      this.lastRoot.distanceTo(this.root.position) > this.height * 0.7 ||
      dt > 0.12;
    this.lastRoot.copy(this.root.position);
    for (let k = 0; k < this.base.length; k++) {
      this.targets[k].copy(this.base[k]).applyMatrix4(matrix);
      if (reset) {
        this.current[k].copy(this.targets[k]);
        this.previous[k].copy(this.targets[k]);
      }
    }
    const kneePositions = this.knees.map((b) =>
      b.getWorldPosition(new T.Vector3()).applyMatrix4(inverse),
    );
    for (let side = 0; side < this.elbows.length; side++) {
      // The arm draws the corresponding shoulder of the cape outward and up.
      const elbow = this.elbows[side].getWorldPosition(v).applyMatrix4(inverse);
      const lift = T.MathUtils.clamp(elbow.y / this.height - 0.63, 0, 0.24);
      const spread = T.MathUtils.clamp(
        Math.abs(elbow.x) / this.height - 0.15,
        0,
        0.18,
      );
      for (let col = 0; col <= cols; col++) {
        const weight = (side ? col / cols : 1 - col / cols) ** 3,
          p = this.targets[col];
        p.applyMatrix4(inverse);
        p.y += lift * weight * this.height * 0.35;
        p.x += (side ? 1 : -1) * spread * weight * this.height * 0.6;
        p.applyMatrix4(this.root.matrixWorld);
      }
    }
    const steps = Math.max(1, Math.ceil(Math.min(dt, 0.06) * 120)),
      h = Math.min(dt, 0.06) / steps;
    for (let step = 0; step < steps; step++) {
      for (let k = 0; k < this.current.length; k++) {
        const p = this.current[k],
          q = this.previous[k],
          target = this.targets[k],
          t = Math.floor(k / width) / rows;
        if (t === 0) {
          p.copy(target);
          q.copy(target);
          continue;
        }
        delta
          .copy(p)
          .sub(q)
          .multiplyScalar((Math.exp(-h * 6) * h) / this.lastStep);
        delta.clampLength(0, this.height * 3 * h);
        q.copy(p);
        p.add(delta).addScaledVector(
          v.copy(target).sub(p),
          (72 - 48 * t) * h * h,
        );
        p.y -= this.height * 1.9 * h * h;
        p.x +=
          Math.sin(time * 2.2 + t * 4 + this.cut.side) *
          this.height *
          0.46 *
          t *
          h *
          h;
      }
      this.lastStep = Math.max(0.0001, h);
      for (let iter = 0; iter < 4; iter++) {
        for (const { a, b, length } of this.links) {
          const p = this.current[a],
            q = this.current[b];
          delta.subVectors(q, p);
          const d = Math.max(0.00001, delta.length());
          delta.multiplyScalar((d - length) / d);
          if (a >= width && b >= width) {
            p.addScaledVector(delta, 0.5);
            q.addScaledVector(delta, -0.5);
          } else if (a >= width) p.add(delta);
          else if (b >= width) q.sub(delta);
        }
        for (let k = width; k < this.current.length; k++) {
          const p = this.current[k];
          v.copy(p).applyMatrix4(inverse);
          const ideal = this.base[k],
            height = this.height;
          // The inner cloth surface rides outside the body's and bent knees' silhouettes.
          const depth = this.cut.back ? -1 : 1;
          const body = Math.sqrt(
            Math.max(0, 1 - (v.x / (0.145 * height)) ** 2),
          );
          let boundary = (0.034 + 0.064 * body) * height;
          for (const knee of kneePositions) {
            const dx = (v.x - knee.x) / (0.085 * height),
              dy = (v.y - knee.y) / (0.165 * height);
            const cap = 1 - dx * dx - dy * dy;
            if (cap > 0)
              boundary = Math.max(
                boundary,
                depth * knee.z + Math.sqrt(cap) * height * 0.062,
              );
          }
          if (Math.abs(ideal.x) < height * 0.175 && v.z * depth < boundary)
            v.z = depth * boundary;
          v.y = Math.max(0.018 * height - this.root.position.y, v.y);
          p.copy(v.applyMatrix4(this.root.matrixWorld));
        }
      }
    }
    const attr = this.mesh.geometry.attributes.position;
    for (let k = 0; k < this.current.length; k++)
      this.targets[k]
        .copy(this.current[k])
        .applyMatrix4(inverse)
        .sub(this.base[k]);
    for (let j = 0; j < this.skin.length; j++) {
      const { i, u, t } = this.skin[j],
        off = this.targets;
      restPoint
        .fromArray(this.rest, j * 3)
        .addScaledVector(off[i], (1 - u) * (1 - t))
        .addScaledVector(off[i + 1], u * (1 - t))
        .addScaledVector(off[i + width], (1 - u) * t)
        .addScaledVector(off[i + width + 1], u * t);
      attr.setXYZ(j, restPoint.x, restPoint.y, restPoint.z);
    }
    attr.needsUpdate = true;
    this.mesh.geometry.computeVertexNormals();
  }
  private lastStep = 1 / 120;
}

/** Curved, overlapping lapels and a girdle cover the join between the breast and
 * the two front skirts. The clasp and braided cord are mounted to the same bone. */
function fittedBodice(
  root: T.Group,
  bone: T.Bone,
  h: number,
  silk: T.Material,
  gilt: T.Material,
  dark: T.Material,
) {
  const dress = new T.Group();
  root.add(dress);
  function band(
    x0: number,
    x1: number,
    y0: number,
    y1: number,
    radius: number,
    taper: number,
  ) {
    const g = new T.PlaneGeometry(1, 1, 32, 14),
      p = g.attributes.position,
      uv = g.attributes.uv;
    for (let i = 0; i < p.count; i++) {
      const u = uv.getX(i),
        t = 1 - uv.getY(i),
        a = T.MathUtils.lerp(x0, x1, u);
      const y = T.MathUtils.lerp(y0, y1, t);
      const r = radius + t * taper;
      p.setXYZ(
        i,
        Math.sin(a) * r * h,
        y * h,
        (Math.cos(a) * (r * 0.67) + 0.007) * h,
      );
    }
    g.computeVertexNormals();
    return g;
  }
  const shirt = new T.Mesh(
    band(-Math.PI, Math.PI, 0.812, 0.568, 0.135, -0.017),
    silk,
  );
  shirt.castShadow = shirt.receiveShadow = true;
  dress.add(shirt);
  for (const s of [-1, 1]) {
    const pts = [
      new T.Vector3(s * 0.06 * h, 0.824 * h, 0.078 * h),
      new T.Vector3(s * 0.035 * h, 0.79 * h, 0.105 * h),
      new T.Vector3(-s * 0.019 * h, 0.737 * h, 0.112 * h),
      new T.Vector3(-s * 0.074 * h, 0.681 * h, 0.088 * h),
    ];
    const cord = new T.CatmullRomCurve3(pts);
    const lapel = new T.Mesh(new T.TubeGeometry(cord, 28, 0.012 * h, 8), dark);
    dress.add(lapel);
    pts.forEach((p) => (p.z += 0.01 * h));
    dress.add(
      new T.Mesh(
        new T.TubeGeometry(new T.CatmullRomCurve3(pts), 28, 0.003 * h, 6),
        gilt,
      ),
    );
  }
  const belt = new T.Mesh(
    band(-Math.PI, Math.PI, 0.635, 0.586, 0.145, 0),
    dark,
  );
  belt.castShadow = true;
  dress.add(belt);
  const gold: T.BufferGeometry[] = [];
  for (const y of [0.594, 0.625])
    gold.push(
      new T.TorusGeometry(1, 0.012, 6, 72)
        .rotateX(Math.PI / 2)
        .scale(0.147 * h, 0.19 * h, 0.099 * h)
        .translate(0, y * h, 0.007 * h),
    );
  for (let i = 0; i < 16; i++) {
    const a = (i / 16) * Math.PI * 2;
    gold.push(
      new T.BoxGeometry(0.024 * h, 0.022 * h, 0.008 * h)
        .rotateY(a)
        .translate(
          Math.sin(a) * 0.148 * h,
          0.611 * h,
          (Math.cos(a) * 0.1 + 0.007) * h,
        ),
    );
  }
  const disc = new T.SphereGeometry(1, 24, 16)
    .scale(0.038 * h, 0.03 * h, 0.012 * h)
    .translate(0, 0.61 * h, 0.115 * h);
  gold.push(disc);
  const fittings = new T.Mesh(mergeGeometries(gold), gilt);
  gold.forEach((g) => g.dispose());
  fittings.castShadow = true;
  dress.add(fittings);
  bone.attach(dress);
}

export function ceremonialSilks(
  root: T.Group,
  bones: Map<string, T.Bone>,
  height: number,
  face: T.Texture,
  metal: T.Material,
  dark: T.Material,
  warden: boolean,
) {
  const silk = silkMaterial(
    face,
    new T.Color(warden ? 0x752934 : 0x313b41),
    new T.Color(warden ? 0xc0a36b : 0x976547),
  );
  const lining = new T.MeshPhysicalMaterial({
    map: face,
    color: warden ? 0x89887c : 0x9b8683,
    side: T.DoubleSide,
    roughness: 0.8,
    sheen: 0.4,
  });
  const torso = bones.get("Spine")!,
    hips = bones.get("Hips")!;
  fittedBodice(root, torso, height, lining, metal, dark);
  const knees = [bones.get("LeftLeg")!, bones.get("RightLeg")!];
  const cuts: Cut[] = [
    { side: 0, back: true, shoulder: false },
    { side: 0, back: true, shoulder: true },
    { side: -1, back: false, shoulder: false },
    { side: 1, back: false, shoulder: false },
  ];
  return cuts.map(
    (c) =>
      new SilkPanel(
        root,
        c.back ? torso : hips,
        c,
        height,
        silk,
        knees,
        c.shoulder
          ? [bones.get("RightForeArm")!, bones.get("LeftForeArm")!]
          : [],
      ),
  );
}
