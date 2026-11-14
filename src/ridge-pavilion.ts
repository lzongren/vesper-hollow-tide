import * as T from "three";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";

/** The beacon is seen from across the valley. The galleries remain open
 * around a smaller lit core so the posts and eaves separate in silhouette. */
export function ridgePavilion() {
  const root = new T.Group();
  root.name = "Mountain pass beacon";
  const slate = new T.MeshStandardMaterial({
    color: 0x415753,
    roughness: 0.68,
    side: T.DoubleSide,
  });
  const timber = new T.MeshStandardMaterial({
    color: 0x673c2e,
    roughness: 0.82,
  });
  const stone = new T.MeshStandardMaterial({
    color: 0x8c8980,
    roughness: 0.91,
  });
  const paper = new T.MeshStandardMaterial({
    color: 0xf6d394,
    emissive: 0xffa44f,
    emissiveIntensity: 2.1,
  });
  const pieces = new Map<T.Material, T.BufferGeometry[]>();
  function add(m: T.Material, g: T.BufferGeometry) {
    if (!pieces.has(m)) pieces.set(m, []);
    pieces.get(m)!.push(g.index ? g.toNonIndexed() : g);
    if (g.index) g.dispose();
  }
  function box(
    m: T.Material,
    w: number,
    h: number,
    d: number,
    x: number,
    y: number,
    z: number,
  ) {
    add(m, new T.BoxGeometry(w, h, d).translate(x, y, z));
  }
  function roof(width: number, base: number, rise: number) {
    const xyz: number[] = [];
    for (let face = 0; face < 4; face++) {
      const a = (face * Math.PI) / 2;
      const sample = (u: number, t: number) => {
        const span = width * (0.1 + 0.9 * t),
          x = u * span,
          z = span;
        const lift =
          base +
          rise * (1 - t) ** 1.7 +
          width * 0.23 * Math.abs(u) ** 3 * t ** 2;
        return [
          x * Math.cos(a) + z * Math.sin(a),
          lift,
          z * Math.cos(a) - x * Math.sin(a),
        ];
      };
      for (let i = 0; i < 12; i++)
        for (let j = 0; j < 5; j++) {
          const u = i / 6 - 1,
            t = j / 5,
            a = sample(u, t),
            b = sample(u + 1 / 6, t),
            c = sample(u, t + 0.2),
            d = sample(u + 1 / 6, t + 0.2);
          xyz.push(...a, ...c, ...b, ...b, ...c, ...d);
          if (j === 4)
            xyz.push(
              ...c,
              ...d,
              ...[c[0], c[1] - 0.14, c[2]],
              ...d,
              ...[d[0], d[1] - 0.14, d[2]],
              ...[c[0], c[1] - 0.14, c[2]],
            );
        }
    }
    const g = new T.BufferGeometry();
    g.setAttribute("position", new T.Float32BufferAttribute(xyz, 3));
    g.computeVertexNormals();
    add(slate, g);
  }
  box(stone, 6.1, 1.2, 6.1, 0, 0, 0);
  box(stone, 5.7, 0.28, 5.7, 0, 0.7, 0);
  for (let i = 0; i < 3; i++) {
    const y = 0.86 + 2.33 * i,
      span = 2.47 - i * 0.46;
    box(timber, span * 2 + 0.3, 0.22, span * 2 + 0.3, 0, y, 0);
    box(
      i === 0 ? timber : paper,
      span * 1.19,
      1.57,
      span * 1.19,
      0,
      y + 0.86,
      0,
    );
    for (const side of [-1, 1]) {
      for (const offset of [-span, 0, span]) {
        box(timber, 0.18, 1.98, 0.18, offset, y + 1.07, side * span);
        if (!offset)
          box(timber, 0.18, 1.98, 0.18, side * span, y + 1.07, offset);
        if (i > 0) {
          box(
            timber,
            0.095,
            1.65,
            0.12,
            offset * 0.46,
            y + 0.88,
            side * span * 0.61,
          );
          box(
            timber,
            0.12,
            1.65,
            0.095,
            side * span * 0.61,
            y + 0.88,
            offset * 0.46,
          );
        }
      }
      box(timber, 2 * span + 0.16, 0.13, 0.13, 0, y + 0.66, side * span);
      box(timber, 0.13, 0.13, 2 * span + 0.16, side * span, y + 0.66, 0);
    }
    roof(span + 0.7, y + 1.84, i === 2 ? 1.72 : 1.24);
  }
  add(
    slate,
    new T.CylinderGeometry(0.065, 0.16, 1.55, 8).translate(0, 9.64, 0),
  );
  add(slate, new T.SphereGeometry(0.22, 10, 6).translate(0, 9.48, 0));
  for (const [mat, geos] of pieces) {
    // Roof surfaces share only positions and normals with the geometric trims.
    for (const g of geos) g.deleteAttribute("uv");
    root.add(new T.Mesh(mergeGeometries(geos), mat));
    for (const g of geos) g.dispose();
  }
  return root;
}
