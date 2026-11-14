import * as T from "three";
import type { Attack } from "./combat";

/** Ground-space geometry follows the simulation angle (+Z forward). Thin double
 * lines mark the actual limit, with a quiet transparent wash inside it. */
export function warningFiligree(attack: Attack) {
  const warning = new T.Group();
  const { shape, range, arc } = attack;
  const metal = attack.parryable ? 0xffce85 : 0xff7155;
  function band(alpha: number) {
    const m = new T.MeshBasicMaterial({
      color: metal,
      transparent: true,
      opacity: alpha,
      depthWrite: false,
      side: T.DoubleSide,
    });
    m.userData.strength = alpha;
    return m;
  }
  const line = band(0.86),
    fine = band(0.4),
    wash = band(0.07);
  function insert(geometry: T.BufferGeometry, material: T.Material) {
    const mesh = new T.Mesh(geometry, material);
    mesh.renderOrder = 2;
    warning.add(mesh);
    return mesh;
  }
  function arcBand(
    r: number,
    width: number,
    span: number,
    material: T.Material,
  ) {
    const g = new T.RingGeometry(
      Math.max(0.001, r - width),
      r,
      96,
      1,
      -Math.PI / 2 - span / 2,
      span,
    );
    g.rotateX(-Math.PI / 2);
    return insert(g, material);
  }
  function strip(
    x: number,
    z: number,
    w: number,
    l: number,
    angle: number,
    material: T.Material,
  ) {
    const g = new T.PlaneGeometry(w, l);
    g.rotateX(-Math.PI / 2);
    g.rotateY(angle);
    g.translate(x, 0, z);
    insert(g, material);
  }
  if (shape === "dash") {
    strip(0, range / 2, 1.4, range, 0, wash);
    for (const side of [-1, 1])
      strip(side * 0.7, range / 2, 0.032, range, 0, line);
    strip(0, range - 0.02, 1.43, 0.04, 0, line);
    strip(0, range - 0.15, 1.22, 0.024, 0, fine);
    return warning;
  }
  const partial = shape === "sector",
    span = partial ? arc : Math.PI * 2;
  const r = shape === "circle" || partial ? range : 2;
  if (partial) {
    arcBand(r, r - 0.55, span, wash);
    for (const side of [-1, 1]) {
      const a = (side * span) / 2,
        l = r - 0.55;
      strip(
        Math.sin(a) * (r - l / 2),
        Math.cos(a) * (r - l / 2),
        0.027,
        l,
        a,
        fine,
      );
    }
  }
  arcBand(r, 0.042, span, line);
  arcBand(r - 0.115, 0.017, span, fine);
  const marks = partial ? 12 : 32;
  const teeth: number[] = [];
  for (let i = 0; i < marks; i++) {
    const a = ((i + 0.5) / marks - 0.5) * span;
    for (const [da, depth] of [
      [-0.012, 0.14],
      [0.012, 0.14],
      [0, i % 3 === 1 ? 0.31 : 0.22],
    ])
      teeth.push(
        Math.sin(a + da) * (r - depth),
        0,
        Math.cos(a + da) * (r - depth),
      );
  }
  const geometry = new T.BufferGeometry();
  geometry.setAttribute("position", new T.Float32BufferAttribute(teeth, 3));
  insert(geometry, fine);
  return warning;
}
