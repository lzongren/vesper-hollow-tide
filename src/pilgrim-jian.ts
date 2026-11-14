import * as T from "three";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";

// Weapon socket origin is the centre of the closed hand. Units are metres.
export const jianPoint = 1.43;
export function pilgrimJian() {
  const sword = new T.Group();
  sword.name = "Pilgrim's rain jian";
  const steel = new T.MeshStandardMaterial({
    name: "Longitudinally polished steel",
    color: 0xdce2df,
    vertexColors: true,
    metalness: 0.77,
    roughness: 0.32,
    envMapIntensity: 0.9,
  });
  const patina = new T.MeshStandardMaterial({
    name: "Dark cast bronze",
    color: 0x817252,
    metalness: 0.77,
    roughness: 0.47,
  });
  const brass = new T.MeshStandardMaterial({
    name: "Polished brass wire",
    color: 0xc2a16b,
    metalness: 0.76,
    roughness: 0.33,
  });
  const silk = new T.MeshStandardMaterial({
    name: "Cord over lacquer",
    color: 0x612e2c,
    roughness: 0.73,
  });
  const batches = new Map<T.Material, T.BufferGeometry[]>();
  function add(mat: T.Material, g: T.BufferGeometry) {
    if (!batches.has(mat)) batches.set(mat, []);
    batches.get(mat)!.push(g.index ? g.toNonIndexed() : g);
    if (g.index) g.dispose();
  }
  function ferrule(y: number, r: number, h: number, mat: T.Material) {
    add(
      mat,
      new T.CylinderGeometry(r, r, h, 20).scale(1, 1, 0.75).translate(0, y, 0),
    );
  }
  function wire(points: T.Vector3[], radius: number, mat: T.Material) {
    add(
      mat,
      new T.TubeGeometry(
        new T.CatmullRomCurve3(points),
        points.length * 2,
        radius,
        6,
        false,
      ),
    );
  }
  add(silk, new T.CylinderGeometry(0.039, 0.043, 0.29, 20).scale(1, 1, 0.76));
  for (const sign of [-1, 1]) {
    const turns = Array.from({ length: 73 }, (_, i) => {
      const t = i / 72,
        angle = sign * t * Math.PI * 12,
        r = 0.044 - 0.004 * t;
      return new T.Vector3(
        r * Math.cos(angle),
        -0.14 + t * 0.28,
        r * 0.76 * Math.sin(angle),
      );
    });
    wire(turns, 0.0035, silk);
  }
  for (const y of [-0.15, 0.147]) {
    ferrule(y, 0.048, 0.028, patina);
    ferrule(y + 0.005, 0.049, 0.005, brass);
  }
  // A pierced pommel, with two chased rims around its cord aperture.
  const pommel = new T.TorusGeometry(0.043, 0.016, 10, 32).scale(1, 0.95, 0.78);
  add(patina, pommel.translate(0, -0.187, 0));
  for (const z of [-0.01, 0.01])
    add(
      brass,
      new T.TorusGeometry(0.04, 0.0027, 6, 32)
        .scale(1, 0.95, 1)
        .translate(0, -0.187, z),
    );
  const outline = new T.Shape();
  outline.moveTo(0, 0.064);
  outline.bezierCurveTo(0.046, 0.061, 0.089, 0.028, 0.145, 0.042);
  outline.bezierCurveTo(0.133, 0.004, 0.097, -0.023, 0.065, -0.019);
  outline.quadraticCurveTo(0.032, -0.011, 0, -0.036);
  outline.quadraticCurveTo(-0.032, -0.011, -0.065, -0.019);
  outline.bezierCurveTo(-0.097, -0.023, -0.133, 0.004, -0.145, 0.042);
  outline.bezierCurveTo(-0.089, 0.028, -0.046, 0.061, 0, 0.064);
  add(
    patina,
    new T.ExtrudeGeometry(outline, {
      depth: 0.026,
      bevelThickness: 0.005,
      bevelSize: 0.004,
      bevelSegments: 2,
      curveSegments: 10,
    }).translate(0, 0.173, -0.013),
  );
  for (const z of [-0.019, 0.019]) {
    for (const sign of [-1, 1])
      wire(
        [
          [0.015, 0.196],
          [0.041, 0.19],
          [0.077, 0.177],
          [0.106, 0.18],
          [0.127, 0.195],
        ].map(([x, y]) => new T.Vector3(x * sign, y, z)),
        0.0026,
        brass,
      );
  }
  const collar = new T.CylinderGeometry(0.043, 0.057, 0.083, 4)
    .rotateY(Math.PI / 2)
    .scale(1, 1, 0.36);
  add(brass, collar.translate(0, 0.235, 0));
  // Bilateral diamond section with a narrow cutting bevel. Faces split at the
  // ridge, while the two long facets hold different reflected values in motion.
  const levels = [
    [0.262, 0.051, 0.012],
    [0.35, 0.049, 0.0105],
    [0.93, 0.038, 0.008],
    [1.22, 0.03, 0.0068],
    [1.32, 0.022, 0.0055],
    [jianPoint, 0, 0],
  ];
  const cross = [
    [-1, 0],
    [-0.76, 0.26],
    [0, 1],
    [0.76, 0.26],
    [1, 0],
    [0.76, -0.26],
    [0, -1],
    [-0.76, -0.26],
    [-1, 0],
  ];
  const pos: number[] = [],
    uv: number[] = [],
    col: number[] = [],
    idx: number[] = [];
  for (let k = 0; k < cross.length - 1; k++) {
    const start = pos.length / 3;
    for (const [y, w, d] of levels) {
      for (let h = 0; h < 2; h++) {
        const [u, v] = cross[k + h];
        pos.push(w * u, y, d * v);
        uv.push((u + 1) * 0.5, (y - 0.262) / (jianPoint - 0.262));
        const light = Math.abs(u) > 0.77 ? 0.97 : 0.65 + 0.14 * Math.abs(v);
        col.push(light * 0.94, light * 0.98, light);
      }
    }
    for (let j = 0; j < levels.length - 1; j++) {
      const a = start + j * 2;
      idx.push(a, a + 1, a + 2);
      if (j < levels.length - 2) idx.push(a + 1, a + 3, a + 2);
    }
  }
  const g = new T.BufferGeometry();
  g.setAttribute("position", new T.Float32BufferAttribute(pos, 3));
  g.setAttribute("color", new T.Float32BufferAttribute(col, 3));
  g.setAttribute("uv", new T.Float32BufferAttribute(uv, 2));
  g.setIndex(idx);
  g.computeVertexNormals();
  add(steel, g);
  // The constellation is set just proud of the two flats at the blade's forte.
  for (const side of [-1, 1]) {
    const stars = [
      [0.012, 0.32],
      [0.02, 0.354],
      [0.015, 0.39],
      [0.007, 0.424],
      [0.016, 0.461],
      [0.012, 0.497],
      [0.004, 0.527],
    ];
    for (const [x, y] of stars) {
      const z = side * (0.0107 * (1 - x / 0.049) + 0.001);
      add(
        brass,
        new T.SphereGeometry(0.0039, 8, 6).scale(1, 1, 0.26).translate(x, y, z),
      );
    }
  }
  for (const [mat, parts] of batches) {
    const mesh = new T.Mesh(mergeGeometries(parts), mat);
    mesh.name = mat.name;
    mesh.castShadow = mesh.receiveShadow = true;
    sword.add(mesh);
    parts.forEach((g) => g.dispose());
  }
  return sword;
}
