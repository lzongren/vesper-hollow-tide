import * as T from "three";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";

/** The altar is cut from dressed blocks. Each exposed arris has a cut face;
 * relief rises from the arch face towards the courtyard along +Z. */
export function shrinePortal(
  rock: T.MeshStandardMaterial,
  bronze: T.MeshStandardMaterial,
) {
  const root = new T.Group();
  root.name = "Lotus arch and processional stair";
  const stone = rock.clone();
  stone.name = "Smoke-stained limestone";
  stone.color.setHex(0xc6bda5);
  stone.vertexColors = true;
  const stoneParts: T.BufferGeometry[] = [],
    metalParts: T.BufferGeometry[] = [];
  const axis = 4.14,
    face = -19.56;
  let seed = 18491;
  const random = () =>
    (seed = (1664525 * seed + 1013904223) >>> 0) / 4294967296;

  function place(
    geometry: T.BufferGeometry,
    x: number,
    y: number,
    z: number,
    tint: number,
    gilded = false,
  ) {
    const g = geometry.index ? geometry.toNonIndexed() : geometry;
    if (g !== geometry) geometry.dispose();
    g.translate(x, y, z);
    const { position, normal, uv } = g.attributes;
    const colors: number[] = [],
      pigment = new T.Color(tint);
    const offset = random() * 9;
    for (let i = 0; i < position.count; i++) {
      const px = position.getX(i),
        py = position.getY(i),
        pz = position.getZ(i);
      const nx = Math.abs(normal.getX(i)),
        ny = Math.abs(normal.getY(i)),
        nz = Math.abs(normal.getZ(i));
      uv.setXY(
        i,
        offset + (nx > nz && nx > ny ? pz : px) * 0.33,
        (ny > nz && ny > nx ? pz : py) * 0.33,
      );
      if (!gilded) colors.push(pigment.r, pigment.g, pigment.b);
    }
    if (!gilded)
      g.setAttribute("color", new T.Float32BufferAttribute(colors, 3));
    (gilded ? metalParts : stoneParts).push(g);
  }

  function cut(points: number[][], depth: number, bevel: number) {
    const outline = new T.Shape(points.map(([x, y]) => new T.Vector2(x, y)));
    return new T.ExtrudeGeometry(outline, {
      depth,
      bevelEnabled: true,
      bevelSegments: 1,
      bevelThickness: bevel,
      bevelSize: bevel,
      curveSegments: 4,
    });
  }
  function block(
    x: number,
    y: number,
    front: number,
    w: number,
    h: number,
    d: number,
    tint: number,
  ) {
    const l = -w / 2,
      r = w / 2,
      b = -h / 2,
      t = h / 2;
    const chip = Math.min(h * 0.36, 0.035 + random() * 0.13);
    const points = [
      [l, b + 0.025],
      [l + 0.036, b],
      [r - 0.04, b],
      [r, b + 0.045],
      [r, t - chip * 0.5],
      [r - chip, t],
      [l + chip * 1.4, t],
      [l, t - chip],
    ];
    place(cut(points, d, Math.min(h * 0.11, 0.035)), x, y, front - d, tint);
  }
  const tones = [0xc7b9a1, 0xebdfc6, 0xc0b9a4, 0xded1be, 0xa99f8e, 0xd4c6b3];
  function limestone() {
    return tones[Math.floor(random() * tones.length)];
  }
  function wedge(
    inner: number,
    outer: number,
    a: number,
    b: number,
    front: number,
    depth: number,
    tint: number,
    gilded = false,
  ) {
    const points = [];
    for (let k = 0; k <= 5; k++) {
      const theta = a + ((b - a) * k) / 5;
      points.push([inner * Math.cos(theta), inner * Math.sin(theta)]);
    }
    for (let k = 5; k >= 0; k--) {
      const theta = a + ((b - a) * k) / 5;
      points.push([outer * Math.cos(theta), outer * Math.sin(theta)]);
    }
    place(
      cut(points, depth, Math.min(0.024, (outer - inner) * 0.18)),
      0,
      axis,
      front - depth,
      tint,
      gilded,
    );
  }
  // Each leaf has a high spine, two sloping lobes and an undercut perimeter.
  function petal(width: number, height: number, rise: number, turn: number) {
    const positions: number[] = [],
      uvs: number[] = [];
    const profile = [0.035, 0.55, 0.92, 1, 0.93, 0.75, 0.5, 0.25, 0.018];
    const sections = profile.map((spread, i) => {
      const t = i / (profile.length - 1);
      const fold = rise * (0.12 + 0.88 * Math.sin(Math.PI * Math.pow(t, 0.83)));
      return [-1, -0.53, 0, 0.53, 1].map((u) => [
        u * spread * width,
        t * height,
        fold * (1 - Math.abs(u)) + 0.014,
      ]);
    });
    for (let row = 1; row < sections.length; row++) {
      for (let col = 0; col < 4; col++) {
        const lower = sections[row - 1],
          upper = sections[row];
        for (const point of [
          lower[col],
          lower[col + 1],
          upper[col + 1],
          lower[col],
          upper[col + 1],
          upper[col],
        ]) {
          positions.push(...point);
          uvs.push(0, 0);
        }
      }
    }
    const g = new T.BufferGeometry();
    g.setAttribute("position", new T.Float32BufferAttribute(positions, 3));
    g.setAttribute("uv", new T.Float32BufferAttribute(uvs, 2));
    g.computeVertexNormals();
    return g.rotateZ(turn);
  }

  for (let i = 0; i < 25; i++) {
    const center = (Math.PI * (i + 0.5)) / 25,
      half = Math.PI / 50;
    const a = center - half + 0.006,
      b = center + half - 0.006;
    const crown = i === 12,
      depthOffset = random() * 0.1;
    wedge(
      crown ? 4.18 : 4.36,
      crown ? 6.1 : 5.76 + random() * 0.1,
      a,
      b,
      face + depthOffset,
      2.35,
      limestone(),
    );
    wedge(4.31, 4.45, a, b, face + 0.2, 0.28, 0xffffff, true);
    wedge(4.5, 4.67, a, b, face + 0.29, 0.32, 0xd0b79c);
    wedge(5.53, 5.7, a, b, face + 0.24, 0.32, 0xd7c4a9);
    const turn = center - Math.PI / 2;
    const radius = 4.69;
    const x = radius * Math.cos(center),
      y = axis + radius * Math.sin(center);
    place(
      petal(crown ? 0.31 : 0.255, crown ? 1.21 : 0.83, 0.22, turn),
      x,
      y,
      face + depthOffset + 0.025,
      0xe3c9a5,
    );
    place(
      petal(0.09, crown ? 0.84 : 0.58, 0.085, turn),
      x,
      y,
      face + depthOffset + 0.158,
      0xffffff,
      true,
    );
  }
  // Open bronze flame crest. The outer band frames actual sky when the
  // camera moves; the two smaller curls return into the lotus cup.
  const flameBase = axis + 5.89;
  function crestLine(path: number[][], thickness: number) {
    const curve = new T.CatmullRomCurve3(
      path.map(([x, y, z]) => new T.Vector3(x, y, z)),
    );
    place(
      new T.TubeGeometry(curve, 32, thickness, 7, false),
      0,
      flameBase,
      face - 0.09,
      0xffffff,
      true,
    );
  }
  for (const sign of [-1, 1]) {
    const sweep = (p: number[][]) => p.map(([x, y, z]) => [sign * x, y, z]);
    crestLine(
      sweep([
        [0, 0.05, 0.08],
        [0.54, 0.16, 0.13],
        [0.73, 0.47, 0.14],
        [0.64, 0.72, 0.12],
        [0.42, 0.82, 0.14],
        [0.36, 0.69, 0.16],
        [0.46, 0.62, 0.16],
      ]),
      0.065,
    );
    crestLine(
      sweep([
        [0, 0.22, 0.16],
        [0.3, 0.42, 0.17],
        [0.39, 0.72, 0.18],
        [0.28, 1.02, 0.19],
        [0.12, 1.32, 0.16],
        [0, 1.66, 0.13],
      ]),
      0.057,
    );
    place(
      petal(0.24, 0.75, 0.14, -sign * 0.84),
      sign * 0.09,
      flameBase - 0.07,
      face + 0.04,
      0xffffff,
      true,
    );
  }
  place(
    petal(0.175, 1.06, 0.19, -0.11),
    0,
    flameBase + 0.09,
    face + 0.12,
    0xffffff,
    true,
  );
  block(0, flameBase + 0.03, face + 0.11, 1.2, 0.23, 0.94, 0xc7b9a1);
  for (const side of [-1, 1]) {
    for (let i = 0; i < 6; i++) {
      block(
        side * 5.05,
        0.37 + i * 0.68,
        face + random() * 0.05,
        1.39,
        0.61,
        2.15,
        limestone(),
      );
      const x = side * 5.05;
      place(
        petal(0.24, 0.47, 0.11, 0),
        x,
        i * 0.68 + 0.1,
        face + 0.07,
        0xd8c8ae,
      );
    }
    block(side * 5.05, 4.06, face + 0.31, 1.6, 0.24, 2.45, 0xd1c2a6);
  }
  // Stagger the joints and wear down the centre of the stair under foot traffic.
  for (let course = 0; course < 5; course++) {
    const width = 10.3 - course * 0.27,
      count = course % 2 === 0 ? 7 : 6;
    const front = -16.32 - course * 0.7,
      top = 0.235 + course * 0.31;
    let left = -width / 2;
    for (let j = 0; j < count; j++) {
      const right =
        j === count - 1
          ? width / 2
          : -width / 2 + (width * (j + 1)) / count + (random() - 0.5) * 0.3;
      const x = (left + right) / 2,
        span = right - left - 0.07;
      const wear = 0.085 * Math.max(0, 1 - Math.abs(x) / 3);
      const height = top - wear + random() * 0.028;
      block(
        x,
        height / 2,
        front + random() * 0.09,
        span,
        height,
        1.04,
        limestone(),
      );
      left = right;
    }
    for (const side of [-1, 1]) {
      const x = side * (width / 2 + 0.18);
      block(x, (top + 0.31) / 2, front + 0.11, 0.5, top + 0.31, 1.06, 0xc2ae96);
      block(x, top + 0.33, front + 0.16, 0.6, 0.14, 1.12, 0xe5d3b5);
    }
  }
  for (const [parts, material] of [
    [stoneParts, stone],
    [metalParts, bronze],
  ] as const) {
    const mesh = new T.Mesh(mergeGeometries(parts), material);
    mesh.name =
      material === stone
        ? "Carved portal limestone"
        : "Bronze leaf ribs and inner moulding";
    mesh.castShadow = mesh.receiveShadow = true;
    root.add(mesh);
    parts.forEach((p) => p.dispose());
  }
  return root;
}
