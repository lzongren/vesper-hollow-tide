import { TessellateModifier } from "three/addons/modifiers/TessellateModifier.js";
import { heronSleeve } from "./heron-sleeve";
import { MantleMotion } from "./vestments";
import { WeaponGrip } from "./pilgrim";
import { duelistSabre, heronGuards, honedSteel } from "./heron-sabres";
import * as T from "three";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";

type Section = "arm" | "hand";

/** The inner flight feathers hang from the forearm. The longer primaries fan
 * from a separate wrist so that their tips sweep back as the bird folds. */
export class HeronWing extends T.Group {
  private wrist = new T.Group();
  constructor(
    private side: number,
    template: T.BufferGeometry,
    material: T.MeshStandardMaterial,
  ) {
    super();
    this.position.set(side * 0.24, 2.18, -0.13);
    this.wrist.position.set(side * 0.94, 0.6, -0.23);
    this.add(this.wrist);
    const quills: Record<Section, T.BufferGeometry[]> = { arm: [], hand: [] };
    const vane = (
      section: Section,
      x: number,
      y: number,
      z: number,
      length: number,
      width: number,
      angle: number,
      sweep: number,
      tint: number,
      distal: boolean,
      twist: number,
    ) => {
      const g = template.clone();
      const pos = g.attributes.position,
        uv = g.attributes.uv;
      const colors = new Float32Array(pos.count * 3);
      const base = new T.Color(tint),
        tip = new T.Color(distal ? 0x303e49 : 0xd7cdba),
        color = new T.Color();
      for (let i = 0; i < pos.count; i++) {
        const v = uv.getY(i);
        const shaft = (pos.getY(i) + 0.5) * length;
        const across = pos.getX(i) * width * (1 - (distal ? 0.31 : 0.12) * v);
        const lean = angle + twist * v * v;
        pos.setXYZ(
          i,
          side * (x + shaft * Math.sin(lean) + across * Math.cos(lean)),
          y - shaft * Math.cos(lean) + across * Math.sin(lean) - 0.11 * v * v,
          z - sweep * v * v + 0.11 * v * (1 - v) + across * (0.26 + twist * 3 * v) - 0.48 * across * across,
        );
        color
          .copy(base)
          .lerp(tip, (distal ? 0.94 : 0.44) * T.MathUtils.smoothstep(v, 0.34, 0.96))
          .toArray(colors, i * 3);
      }
      g.setAttribute("color", new T.BufferAttribute(colors, 3));
      g.computeVertexNormals();
      quills[section].push(g);
    };
    // Three tiers follow a convex leading edge. A change in spacing and a slot
    // between the long distal quills break up the trailing silhouette.
    for (const section of ["arm", "hand"] as const) {
      const hand = section === "hand";
      for (let row = 0; row < 3; row++) {
        const count = hand ? [8, 11, 14][row] : [12, 14, 16][row];
        for (let j = 0; j < count; j++) {
          const u = j / (count - 1);
          const x = (hand ? 1.0 : 0.94) * u;
          const y = hand
            ? 0.22 * Math.sin(Math.PI * u) + 0.11 * u
            : 0.6 * u + 0.17 * Math.sin(Math.PI * u);
          const angle = hand ? 0.54 + 1.15 * u : -0.22 + 0.72 * u;
          const mainLength = hand
            ? 1.19 + 0.67 * Math.sin(2.35 * u)
            : 0.78 + 0.42 * u;
          const length =
            mainLength *
            [1, 0.64, 0.35][row] *
            (1 + 0.032 * Math.sin(j * 2.73));
          const tint =
            hand && row === 0 ? 0x8798a2 : [0xa3b1b3, 0xcac3b3, 0xeee2c8][row];
          vane(
            section,
            x,
            y + row * 0.034,
            -0.23 * u + row * 0.058,
            length,
            (hand ? 1.04 - 0.32 * u : 1.02) * [1, 0.86, 0.75][row],
            angle + 0.08 * row,
            (hand ? 0.72 : 0.4) * (1 - 0.24 * row),
            tint,
            hand && row === 0,
            (hand ? 0.12 : 0.045) * Math.sin(j * 2.2 + row + side * 0.3) - 0.08 * u,
          );
        }
      }
      const group = new T.Mesh(mergeGeometries(quills[section]), material);
      group.castShadow = group.receiveShadow = true;
      (hand ? this.wrist : this).add(group);
      quills[section].forEach((g) => g.dispose());
    }
  }
  pose(time: number, action: string, progress: number) {
    const keyed =
      action === "windup" ? progress : action === "active" ? 1 - progress : 0;
    const breath = Math.sin(time * 1.56 + this.side * 0.13);
    this.rotation.z = this.side * (0.1 + breath * 0.04 + keyed * 0.23);
    this.rotation.y = this.side * (0.28 - keyed * 0.29);
    this.wrist.rotation.y = this.side * (0.49 + breath * 0.045 - keyed * 0.48);
    this.wrist.rotation.z = this.side * (-0.1 + keyed * 0.17);
  }
}

/** Hollow porcelain face on the actor's head joint, with pierced eyes and a
 * projecting central ridge. Both cheek pieces share the same glazed surface. */
export function bridalMask(gold: T.Material, silk: T.Material, porcelain: T.Texture | null = null) {
  const mask = new T.Group();
  const hair = new T.MeshStandardMaterial({
    name: "Coiffure",
    color: 0x343031,
    roughness: 0.51,
    metalness: 0.04,
  });
  const glaze = new T.MeshPhysicalMaterial({
    color: 0xfff6e8,
    map: porcelain,
    vertexColors: true,
    roughness: 0.39,
    clearcoat: 0.72,
    clearcoatRoughness: 0.29,
    side: T.DoubleSide,
  });
  const pearl = new T.MeshPhysicalMaterial({ name: "Crown pearls", color: 0xeedec0, roughness: 0.28, clearcoat: 0.64 });
  const bead = new T.MeshStandardMaterial({ color: 0x7b221a, roughness: 0.33 });
  const groups = new Map<T.Material, T.BufferGeometry[]>();
  const add = (m: T.Material, g: T.BufferGeometry) => {
    if (m === glaze && !g.hasAttribute("color")) {
      const tint = new Float32Array(g.attributes.position.count * 3).fill(1);
      g.setAttribute("color", new T.BufferAttribute(tint, 3));
    }
    if (!groups.has(m)) groups.set(m, []);
    const flat = g.index ? g.toNonIndexed() : g;
    if (flat !== g) g.dispose();
    groups.get(m)!.push(flat);
  };
  const line = (m: T.Material, path: number[][], radius: number) => {
    add(
      m,
      new T.TubeGeometry(
        new T.CatmullRomCurve3(path.map(([x, y, z]) => new T.Vector3(x, y, z))),
        16,
        radius,
        6,
        false,
      ),
    );
  };
  add(
    hair,
    new T.SphereGeometry(1, 32, 24)
      .scale(0.191, 0.232, 0.167)
      .translate(0, 0.014, -0.01),
  );
  for (const side of [-1, 1]) {
    // Wind three interlaced locks around each hairpin. Each loop has an
    // open centre and a tilted axis, visible in silhouette behind the crown.
    const braid = (angle: number, lock: number, filament: number) => {
      const phase = 7 * angle + lock * 2 * Math.PI / 3 + filament * 0.29;
      const radius = 0.099 + 0.014 * Math.cos(phase) + 0.008 * Math.sin(3 * angle);
      const u = radius * Math.cos(angle);
      const v = radius * 0.85 * Math.sin(angle);
      const depth = 0.017 * Math.sin(phase);
      return new T.Vector3(
        side * (0.15 + u - v * 0.23),
        0.237 + v + u * 0.31,
        -0.045 + depth + u * 0.45 - v * 0.3,
      );
    };
    for (let lock = 0; lock < 3; lock++) {
      for (let filament = -1; filament <= 1; filament++) {
        const points = Array.from({ length: 84 }, (_, i) =>
          braid(2 * Math.PI * i / 84, lock, filament));
        const path = new T.CatmullRomCurve3(points, true);
        add(hair, new T.TubeGeometry(path, 100, filament === 0 ? 0.011 : 0.0065, 7, true));
      }
    }
    // Loose locks leave the temples and return under the veil.
    for (let j = 0; j < 3; j++) {
      line(hair, [
        [side * (0.145 + j * 0.012), 0.142, 0.076],
        [side * (0.199 + j * 0.014), 0.048, 0.083],
        [side * (0.183 + j * 0.014), -0.071, 0.091],
        [side * (0.214 + j * 0.01), -0.162, 0.04],
        [side * (0.205 + j * 0.012), -0.195 + j * 0.015, 0.022],
      ], 0.004 - j * 0.0009);
    }
    for (let k = 0; k < 5; k++) {
      const u = k / 4;
      const base = [side * (0.034 + u * 0.112), 0.163, 0.089 - u * 0.03];
      const tip = [side * (0.042 + u * 0.238), 0.395 - 0.112 * u, -0.07];
      line(gold, [base, [side * (0.062 + 0.17 * u), 0.282, 0.045], tip], 0.007);
      line(gold, [base, [side * (0.016 + 0.163 * u), 0.266, 0.06], tip], 0.004);
      add(k === 0 ? bead : pearl, new T.SphereGeometry(0.012, 10, 8)
        .scale(0.88, 1.4, 1).translate(tip[0], tip[1], tip[2]));
    }
    for (let j = 0; j < 9; j++) {
      const u = j / 8;
      line(
        hair,
        [
          [side * (0.035 + 0.065 * u), 0.21, -0.165],
          [side * (0.11 + 0.09 * u), 0.26, 0.016],
          [side * (0.18 + 0.019 * u), 0.08, 0.05],
          [side * (0.172 + 0.017 * u), -0.065, 0.02],
        ],
        0.009,
      );
    }
    line(
      gold,
      [
        [0, 0.21, -0.095],
        [side * 0.126, 0.248, -0.08],
        [side * 0.277, 0.313, -0.112],
      ],
      0.007,
    );
    for (let j = 0; j < 3; j++)
      add(
        pearl,
        new T.SphereGeometry(0.016 - j * 0.002, 12, 8).translate(
          side * (0.228 + j * 0.025),
          0.292 + j * 0.012,
          -0.1,
        ),
      );
  }
  const profile = (x: number, y: number) =>
    0.209 +
    0.052 * Math.exp(-(((x - 0.117) / 0.065) ** 2) - (((y + 0.011) / 0.061) ** 2)) -
    0.035 * Math.exp(-(((x - 0.112) / 0.062) ** 2) - (((y - 0.066) / 0.035) ** 2)) -
    3.35 * x * x +
    0.021 * Math.exp(-(((y - 0.112 - 0.24 * x) / 0.032) ** 2)) +
    0.17 * Math.exp(-155 * x * x) * T.MathUtils.clamp((0.13 - y) / 0.32, 0, 1);
  for (const side of [-1, 1]) {
    const outline = new T.Shape();
    outline.moveTo(0, 0.16);
    outline.bezierCurveTo(0.07, 0.2, 0.16, 0.23, 0.213, 0.21);
    outline.bezierCurveTo(0.217, 0.09, 0.19, -0.035, 0.14, -0.092);
    outline.bezierCurveTo(0.085, -0.122, 0.045, -0.16, 0, -0.227);
    outline.lineTo(0, 0.16);
    const eye = new T.Path();
    eye.moveTo(0.042, 0.051);
    eye.bezierCurveTo(0.081, 0.09, 0.145, 0.115, 0.174, 0.108);
    eye.bezierCurveTo(0.145, 0.065, 0.077, 0.032, 0.042, 0.051);
    outline.holes.push(eye);
    const shell = new T.ExtrudeGeometry(outline, {
      depth: 0.012,
      bevelEnabled: true,
      bevelSize: 0.004,
      bevelThickness: 0.004,
      bevelSegments: 2,
      curveSegments: 14,
    });
    const g = new TessellateModifier(0.023, 7).modify(shell);
    shell.dispose();
    const p = g.attributes.position, normals = g.attributes.normal;
    const hues = new Float32Array(p.count * 3);
    const clay = new T.Color(0xf9ecce), celadon = new T.Color(0x68928c), tint = new T.Color();
    // Differentiating the relief keeps glaze reflections smooth over the cheek
    // and leaves the bevel and the pierced eye rim with their own normals.
    const n = new T.Vector3();
    for (let i = 0; i < p.count; i++) {
      const x = p.getX(i), y = p.getY(i);
      p.setXYZ(i, x, y, p.getZ(i) + profile(x, y));
      g.attributes.uv.setXY(i, 0.5 + side * x / 0.445, (y + 0.235) / 0.443);
      const dx = (profile(x + 0.001, y) - profile(x - 0.001, y)) * 500;
      const dy = (profile(x, y + 0.001) - profile(x, y - 0.001)) * 500;
      n.fromBufferAttribute(normals, i);
      n.set(n.x - n.z * dx, n.y - n.z * dy, n.z).normalize();
      normals.setXYZ(i, n.x, n.y, n.z);
      const edge = T.MathUtils.smoothstep(x, 0.09, 0.21);
      const hollow = Math.exp(-(((y - 0.069 - 0.36 * (x - 0.1)) / 0.032) ** 2));
      tint.copy(clay).lerp(celadon, 0.10 + 0.62 * edge + 0.19 * hollow);
      tint.toArray(hues, i * 3);
    }
    g.setAttribute("color", new T.BufferAttribute(hues, 3));
    if (side < 0) {
      // Mirroring a half also reverses winding. Keep glaze on the outside.
      g.scale(-1, 1, 1);
      g.setIndex(Array.from({ length: p.count }, (_, i) => i % 3 === 0 ? i : i % 3 === 1 ? i + 1 : i - 1));
    }
    add(glaze, g);
    const trace = (points: number[][], r: number) =>
      line(
        gold,
        points.map(([x, y]) => [side * x, y, profile(x, y) + 0.02]),
        r,
      );
    trace(
      [
        [0.006, 0.127],
        [0.065, 0.112],
        [0.149, 0.142],
        [0.199, 0.19],
      ],
      0.009,
    );
    trace(
      [
        [0.038, 0.035],
        [0.092, 0.039],
        [0.16, 0.082],
      ],
      0.004,
    );
    trace(
      [
        [0.009, 0.08],
        [0.013, -0.07],
        [0.002, -0.2],
      ],
      0.005,
    );
    for (let j = 0; j < 4; j++) {
      const x = 0.078 + 0.022 * j, y = -0.076 + 0.018 * j;
      trace([[x, y], [x + 0.003, y + 0.026], [x + 0.018, y + 0.042],
        [x + 0.027, y + 0.057]], 0.0019);
    }
    for (let j = 0; j < 3; j++) {
      const x = side * (0.173 + j * 0.016),
        y = 0.09 + j * 0.028,
        l = 0.21 + j * 0.047;
      line(
        gold,
        [
          [x, y, 0.08],
          [x + side * 0.022, y - 0.08, 0.08],
          [x + side * 0.01, y - l, 0.09],
        ],
        0.0035,
      );
      add(
        bead,
        new T.SphereGeometry(0.013, 10, 8)
          .scale(1, 1.5, 1)
          .translate(x + side * 0.01, y - l, 0.09),
      );
    }
    const veil = new T.PlaneGeometry(1, 1, 10, 20),
      p2 = veil.attributes.position;
    for (let i = 0; i < p2.count; i++) {
      const u = p2.getX(i),
        fall = 0.5 - p2.getY(i);
      p2.setXYZ(
        i,
        side *
          (0.17 +
            0.14 * fall +
            0.06 * Math.sin(3 * fall) +
            u * (0.14 + 0.09 * fall)),
        0.13 - fall * (0.66 + 0.08 * Math.cos(u * 5)),
        -0.048 - 0.15 * fall + 0.028 * Math.sin(u * 12 + fall * 3),
      );
    }
    veil.computeVertexNormals();
    add(silk, veil);
  }
  for (const [material, pieces] of groups) {
    const mesh = new T.Mesh(mergeGeometries(pieces), material);
    mesh.castShadow = mesh.receiveShadow = true;
    mask.add(mesh);
    pieces.forEach((g) => g.dispose());
  }
  return mask;
}

/** Cross-collar jacket, weighted sleeves and a pleated skirt fitted to the animated skeleton. */
export function dressHeron(
  root: T.Group,
  bones: Map<string, T.Bone>,
  brocade: T.Material,
  gold: T.Material,
  weave: T.Texture,
  damask: T.Texture,
) {
  const satin = new T.MeshPhysicalMaterial({
    color: 0xe9eee0,
    map: damask,
    roughness: 0.55,
    normalMap: weave,
    normalScale: new T.Vector2(0.24, 0.24),
    sheen: 0.9,
    sheenColor: 0x98b1a4,
    sheenRoughness: 0.65,
    side: T.DoubleSide,
  });
  const enamel = new T.MeshStandardMaterial({
    color: 0x557675,
    metalness: 0.52,
    roughness: 0.32,
  });
  const ivory = new T.MeshStandardMaterial({
    color: 0xe0d2b2,
    metalness: 0.13,
    roughness: 0.39,
  });
  const steel = honedSteel();
  const place = (target: T.Object3D, g: T.BufferGeometry, m: T.Material) => {
    const mesh = new T.Mesh(g, m);
    mesh.castShadow = mesh.receiveShadow = true;
    root.add(mesh);
    target.attach(mesh);
    return mesh;
  };
  const point = (bone: T.Bone) =>
    root.worldToLocal(bone.getWorldPosition(new T.Vector3()));
  const hip = bones.get("Hips")!,
    neck = bones.get("neck")!;
  const waist = point(hip),
    collar = point(neck);
  const pattern = [
      new T.Vector2(0.58, 0.18),
      new T.Vector2(0.55, 0.42),
      new T.Vector2(0.46, 0.71),
      new T.Vector2(0.35, 1.12),
      new T.Vector2(0.23, waist.y - 0.05),
      new T.Vector2(0.24, waist.y + 0.16),
      new T.Vector2(0.32, collar.y - 0.13),
      new T.Vector2(0.18, collar.y + 0.03),
      new T.Vector2(0.11, collar.y + 0.09),
  ];

  const rings = pattern.slice(1).flatMap((end, index) => {
    const start = pattern[index];
    const steps = Math.max(2, Math.ceil((end.y - start.y) / 0.026));
    return Array.from({ length: steps }, (_, k) => start.clone().lerp(end, k / steps));
  });
  rings.push(pattern[pattern.length - 1]);
  const dress = new T.LatheGeometry(rings, 112);
  const pos = dress.attributes.position;
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i),
      z = pos.getZ(i),
      y = pos.getY(i),
      theta = Math.atan2(x, z);
    const fall = T.MathUtils.clamp(1 - y / waist.y, 0, 1),
      f = 1 + (0.012 + 0.115 * fall) * Math.cos(theta * 12 + 0.6 * fall);
    const chest = T.MathUtils.smoothstep(y, waist.y - 0.12, waist.y + 0.14)
      * (1 - T.MathUtils.smoothstep(y, collar.y - 0.12, collar.y + 0.05));
    const pull = chest * (0.018 * Math.sin(35 * y + 9 * x + 1.5 * Math.sin(theta))
      + 0.009 * Math.cos(48 * y + 11 * x));
    const radius = Math.max(0.01, Math.hypot(x, z));
    pos.setXYZ(
      i,
      x * (f + pull / radius),
      y + 0.065 * fall * Math.cos(theta * 6),
      z * 0.81 * (f + pull / radius) - 0.08 * fall,
    );
    dress.attributes.uv.setXY(i, dress.attributes.uv.getX(i) * 2.6, y * 1.16);
  }
  dress.computeVertexNormals();
  const skirts: MantleMotion[] = [];
  function hanging(g: T.BufferGeometry, mat: T.Material) {
    const y = g.attributes.position;
    const top = waist.y + 0.08;
    skirts.push(
      new MantleMotion(place(hip, g, mat), (i) =>
        T.MathUtils.clamp((top - y.getY(i)) / (top - 0.18), 0, 1),
      ),
    );
  }
  hanging(dress, satin);
  // A separate embroidered front panel tapers below the sash and breaks up the wide hem.
  const panel = new T.PlaneGeometry(1, 1, 24, 36),
    panelPos = panel.attributes.position;
  const seam: T.Vector3[][] = [[], []];
  for (let i = 0; i < panelPos.count; i++) {
    const u = panelPos.getX(i) * 2,
      fall = 0.5 - panelPos.getY(i),
      w = 0.19 + 0.16 * fall;
    const x = u * w + 0.045 * Math.sin(fall * 2.6),
      y = waist.y + 0.1 - fall * (waist.y - 0.12) + 0.085 * fall ** 4 * u * u;
    const z =
      0.202 +
      0.215 * fall -
      0.095 * u * u +
      0.013 * Math.sin(u * 11 + fall * 2);
    panelPos.setXYZ(i, x, y, z);
    if (Math.abs(u) === 1)
      seam[u < 0 ? 0 : 1].push(new T.Vector3(x, y, z + 0.008));
  }
  panel.computeVertexNormals();
  hanging(panel, brocade);
  for (const edge of seam)
    hanging(
      new T.TubeGeometry(new T.CatmullRomCurve3(edge), 36, 0.009, 5, false),
      gold,
    );
  for (const [y, w, d, h] of [
    [waist.y + 0.08, 0.27, 0.21, 0.052],
    [collar.y, 0.23, 0.17, 0.022],
  ]) {
    const band = new T.TorusGeometry(1, 0.14, 8, 48)
      .rotateX(Math.PI / 2)
      .scale(w, h / 0.14, d)
      .translate(0, y, 0);
    place(hip, band, gold);
  }
  const cord = (
    target: T.Bone,
    points: T.Vector3[],
    r: number,
    mat: T.Material,
  ) =>
    place(
      target,
      new T.TubeGeometry(new T.CatmullRomCurve3(points), 24, r, 6, false),
      mat,
    );
  // The pleated silk throat wraps under the mask and tucks inside the crossed collar.
  const throat = new T.SphereGeometry(1, 72, 36);
  const surface = throat.attributes.position;
  for (let i = 0; i < surface.count; i++) {
    const x = surface.getX(i), y = surface.getY(i), z = surface.getZ(i);
    const theta = Math.atan2(x, z);
    const bias = 0.075 * Math.sin(17 * y + 2.7 * Math.sin(theta) + 0.6 * Math.sin(3 * theta));
    surface.setXYZ(i, collar.x + x * 0.128 * (1 + bias), collar.y + 0.13 + 0.24 * y,
      collar.z + z * 0.134 * (1 + bias));
  }
  throat.computeVertexNormals();
  place(hip, throat, brocade);
  // Crossed collar with an embroidered facing and a knotted girdle.
  for (const side of [-1, 1]) {
    const edge = [
      new T.Vector3(side * 0.115, collar.y + 0.055, 0.129),
      new T.Vector3(side * 0.151, collar.y - 0.025, 0.171),
      new T.Vector3(side * 0.061, collar.y - 0.16, 0.239),
      new T.Vector3(-side * 0.18, waist.y + 0.19, 0.161),
    ];
    // The right front laps across the chest. The under-collar ends at the crossing.
    if (side < 0) edge.splice(3, 1, new T.Vector3(-0.01, collar.y - 0.27, 0.274));
    const path = new T.CatmullRomCurve3(edge);
    const lapel = new T.PlaneGeometry(1, 1, 8, 36);
    const points = lapel.attributes.position, facing = lapel.attributes.uv;
    const border: T.Vector3[] = [];
    for (let i = 0; i < points.count; i++) {
      const t = 1 - facing.getY(i), across = facing.getX(i) * 2 - 1;
      const p = path.getPoint(t), tangent = path.getTangent(t);
      const width = 0.049 + 0.009 * Math.sin(t * Math.PI);
      p.x -= tangent.y * across * width;
      p.y += tangent.x * across * width;
      p.z += 0.019 + 0.011 * (1 - across * across) + (side > 0 ? 0.017 : 0);
      points.setXYZ(i, p.x, p.y, p.z);
      facing.setXY(i, 0.34 + 0.19 * across, 0.15 + t * 0.7);
      if (across === 1) border.push(p);
    }
    lapel.computeVertexNormals();
    place(hip, lapel, brocade);
    cord(hip, border, 0.0045, gold);
    const drop = [
      new T.Vector3(side * 0.097, waist.y + 0.09, 0.23),
      new T.Vector3(side * 0.142, waist.y - 0.075, 0.229),
      new T.Vector3(side * 0.124, waist.y - 0.19, 0.26),
    ];
    cord(hip, drop, 0.011, gold);
    place(
      hip,
      new T.SphereGeometry(0.031, 12, 10)
        .scale(0.86, 1.4, 0.6)
        .translate(side * 0.124, waist.y - 0.2, 0.26),
      enamel,
    );
  }
  const sleeveSilk = satin.clone();
  sleeveSilk.color.setHex(0xe0e7d4);
  sleeveSilk.roughness = 0.67;
  sleeveSilk.sheenColor.setHex(0xd3c4a0);
  const grips = {} as Record<"Left" | "Right", WeaponGrip>;
  for (const name of ["Left", "Right"] as const) {
    const side = name === "Left" ? 1 : -1;
    heronSleeve(root, bones.get(name + "Arm")!, bones.get(name + "ForeArm")!,
      bones.get(name + "Hand")!, side, sleeveSilk, brocade, gold);
    const sword = duelistSabre(side, {
      skin: ivory,
      steel,
      bronze: gold,
      binding: enamel,
    });
    root.add(sword);
    grips[name] = new WeaponGrip(
      root,
      bones.get(name + "Arm")!,
      bones.get(name + "ForeArm")!,
      bones.get(name + "Hand")!,
      sword,
      heronGuards[name],
      undefined,
      side,
    );
  }
  return { grips, skirts };
}
