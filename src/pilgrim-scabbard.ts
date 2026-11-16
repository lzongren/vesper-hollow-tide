import * as T from "three";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";
import { jianPoint } from "./pilgrim-jian";

/** The jian is already drawn in the arena. A lined wooden case hangs from
 * two cord loops at the left hip. Build the hardware around the empty mouth. */
export function pilgrimScabbard() {
  const scabbard = new T.Group();
  scabbard.name = "Empty river-cloud scabbard";
  const length = jianPoint - 0.262 + 0.035;
  const lacquer = new T.MeshPhysicalMaterial({
    name: "Ox-blood lacquer",
    color: 0x4d201f,
    roughness: 0.44,
    clearcoat: 0.46,
    clearcoatRoughness: 0.36,
    vertexColors: true,
  });
  const bronze = new T.MeshStandardMaterial({
    name: "Verdigris bronze",
    color: 0x7a7956,
    metalness: 0.65,
    roughness: 0.49,
  });
  const gold = new T.MeshStandardMaterial({
    name: "Worn gilt edges",
    color: 0xbfa377,
    metalness: 0.72,
    roughness: 0.42,
  });
  const dark = new T.MeshStandardMaterial({
    name: "Textile liner",
    color: 0x332b28,
    roughness: 0.93,
    side: T.DoubleSide,
  });
  const silk = new T.MeshStandardMaterial({
    name: "Knotted silk",
    color: 0x813d31,
    roughness: 0.85,
  });
  const pieces = new Map<T.Material, T.BufferGeometry[]>();
  function add(m: T.Material, g: T.BufferGeometry) {
    if (!pieces.has(m)) pieces.set(m, []);
    const flat = g.index ? g.toNonIndexed() : g;
    pieces.get(m)!.push(flat);
    if (flat !== g) g.dispose();
  }
  const cross = (t: number, a: number, extra = 0) => {
    const flare = 1 - 0.34 * t;
    return new T.Vector3(
      Math.sign(Math.cos(a)) *
        Math.abs(Math.cos(a)) ** 0.68 *
        (0.063 * flare + extra),
      -length * t,
      Math.sign(Math.sin(a)) *
        Math.abs(Math.sin(a)) ** 0.67 *
        (0.023 * flare + extra),
    );
  };
  function shell(lo: number, hi: number, extra: number, m: T.Material) {
    const geo = new T.PlaneGeometry(1, 1, 36, 12);
    const p = geo.attributes.position,
      uv = geo.attributes.uv;
    const tint = new Float32Array(p.count * 3);
    for (let i = 0; i < p.count; i++) {
      const a = uv.getX(i) * Math.PI * 2,
        t = T.MathUtils.lerp(lo, hi, 1 - uv.getY(i));
      const v = cross(t, a, extra);
      p.setXYZ(i, v.x, v.y, v.z);
      const grain =
        0.83 +
        0.1 * Math.sin(9 * a + 2 * Math.sin(5 * t)) +
        0.04 * Math.cos(39 * a + 17 * t);
      tint.set([grain, grain * 0.98, grain * 0.96], i * 3);
    }
    if (m !== dark) {
      const triangles = geo.index!;
      for (let i = 0; i < triangles.count; i += 3) {
        const a = triangles.getX(i);
        triangles.setX(i, triangles.getX(i + 1));
        triangles.setX(i + 1, a);
      }
    }
    geo.computeVertexNormals();
    if (m === lacquer)
      geo.setAttribute("color", new T.BufferAttribute(tint, 3));
    add(m, geo);
  }
  function wire(path: T.Vector3[], r: number, m: T.Material, closed = false) {
    add(
      m,
      new T.TubeGeometry(
        new T.CatmullRomCurve3(path, closed),
        Math.max(16, path.length * 2),
        r,
        6,
        closed,
      ),
    );
  }
  function rim(t: number, r: number, m: T.Material, extra: number) {
    wire(
      Array.from({ length: 44 }, (_, i) =>
        cross(t, (Math.PI * 2 * i) / 44, extra),
      ),
      r,
      m,
      true,
    );
  }
  shell(0.004, 0.992, 0, lacquer);
  shell(0, 0.046, 0.0015, bronze);
  shell(0.0, 0.058, -0.0036, dark);
  // The visible cavity ends behind the bronze lip.
  add(
    dark,
    new T.CircleGeometry(1, 36)
      .rotateX(-Math.PI / 2)
      .scale(0.057, 1, 0.021)
      .translate(0, -0.061, 0),
  );
  for (const t of [0.0, 0.043, 0.192, 0.223, 0.383, 0.412, 0.91, 0.988])
    rim(t, 0.0035, gold, 0.0018);
  shell(0.193, 0.222, 0.002, bronze);
  shell(0.384, 0.411, 0.002, bronze);
  shell(0.91, 0.99, 0.002, bronze);
  add(
    bronze,
    new T.SphereGeometry(1, 24, 10)
      .scale(0.044, 0.024, 0.0175)
      .translate(0, -length * 0.988, 0),
  );
  for (const t of [0.205, 0.396]) {
    add(
      bronze,
      new T.TorusGeometry(0.022, 0.0048, 8, 16).translate(
        -0.062,
        -length * t,
        0,
      ),
    );
  }
  // Fine inlaid cloud scrolls near the chape and throat.
  for (const band of [0.065, 0.82]) {
    const path = Array.from({ length: 29 }, (_, i) => {
      const u = i / 28,
        t = band + 0.062 * u;
      const a =
        1.5 +
        0.77 * Math.sin(Math.PI * 2 * u) +
        0.25 * Math.sin(Math.PI * 4 * u);
      return cross(t, a, 0.0018);
    });
    wire(path, 0.0018, gold);
    wire(
      path.map((p) => new T.Vector3(-p.x, p.y, -p.z)),
      0.0018,
      gold,
    );
  }
  for (const z of [-0.006, 0.006]) {
    wire(
      [
        new T.Vector3(-0.077, -0.25, z),
        new T.Vector3(-0.104, -0.215, z),
        new T.Vector3(-0.088, -0.132, z),
        new T.Vector3(-0.045, -0.081, z),
        new T.Vector3(0, -0.072, z),
      ],
      0.0065,
      silk,
    );
    wire(
      [
        new T.Vector3(-0.076, -0.472, z),
        new T.Vector3(-0.112, -0.443, z),
        new T.Vector3(-0.108, -0.29, z),
        new T.Vector3(-0.095, -0.216, z),
      ],
      0.0058,
      silk,
    );
  }
  for (const [m, geos] of pieces) {
    const mesh = new T.Mesh(mergeGeometries(geos), m);
    mesh.castShadow = mesh.receiveShadow = true;
    scabbard.add(mesh);
    geos.forEach((g) => g.dispose());
  }
  return scabbard;
}
