import * as T from "three";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";

/** Split-bamboo warp and weft share a shallow, asymmetric rain-shedding brim. */
export function travelHat() {
  const hat = new T.Group();
  const bamboo = new T.MeshStandardMaterial({
    vertexColors: true,
    roughness: 0.64,
    side: T.DoubleSide,
  });
  const strips: T.BufferGeometry[] = [];
  const brim = (a: number) =>
    1 + 0.016 * Math.sin(3 * a + 0.7) + 0.009 * Math.cos(7 * a);
  const pos = (r: number, a: number, lift = 0) =>
    new T.Vector3(
      Math.sin(a) * r * brim(a),
      0.228 * Math.max(0, 1 - r / 0.46) ** 1.38 +
        0.014 * Math.cos(a * 2 - 0.6) * (r / 0.46) ** 2 +
        lift,
      Math.cos(a) * r * 0.94 * brim(a),
    );
  function strip(
    rows: number,
    tint: number,
    sample: (u: number, edge: number) => T.Vector3,
  ) {
    const v: number[] = [],
      colors: number[] = [],
      idx: number[] = [];
    const color = new T.Color(tint);
    for (let i = 0; i <= rows; i++) {
      for (const edge of [-1, 1]) {
        v.push(...sample(i / rows, edge).toArray());
        const grain = 0.94 + 0.06 * Math.sin(i * 0.47 + edge * 0.26 + tint);
        colors.push(color.r * grain, color.g * grain, color.b * grain);
      }
      const j = i * 2;
      if (i < rows) idx.push(j, j + 1, j + 2, j + 1, j + 3, j + 2);
    }
    const g = new T.BufferGeometry();
    g.setAttribute("position", new T.Float32BufferAttribute(v, 3));
    g.setAttribute("color", new T.Float32BufferAttribute(colors, 3));
    g.setIndex(idx);
    g.computeVertexNormals();
    strips.push(g);
  }
  const count = 64,
    rings = 20;
  for (let i = 0; i < count; i++) {
    const a = (i / count) * Math.PI * 2;
    strip(rings * 2, [0xac783b, 0xb98c4c, 0x997340, 0xc69c59][i % 4], (u, e) =>
      pos(
        0.036 + 0.422 * u,
        a + e * 0.032 + 0.045 * u,
        0.003 * Math.cos(Math.PI * (rings * u + i)),
      ),
    );
  }
  for (let j = 0; j < rings; j++) {
    const u = (j + 0.5) / rings,
      r = 0.036 + 0.422 * u;
    strip(count * 2, j % 4 === 0 ? 0x986d3a : 0x875f31, (t, e) =>
      pos(
        r + e * 0.008,
        t * Math.PI * 2 + 0.045 * u,
        -0.003 * Math.cos(Math.PI * (count * t + j + 0.5)),
      ),
    );
  }
  strip(128, 0x4f2e1c, (t, e) =>
    pos(0.454 + e * 0.005, t * 2 * Math.PI, 0.003 + e * 0.002),
  );
  const weave = new T.Mesh(mergeGeometries(strips), bamboo);
  strips.forEach((g) => g.dispose());
  weave.castShadow = weave.receiveShadow = true;
  hat.add(weave);
  // Match the lining to the woven crown, leaving a narrow rim of exposed reeds.
  const liningGeo = new T.PlaneGeometry(1, 1, 96, 16);
  const p = liningGeo.attributes.position,
    uv = liningGeo.attributes.uv;
  for (let i = 0; i < p.count; i++) {
    const v = pos(0.009 + uv.getY(i) * 0.441, uv.getX(i) * Math.PI * 2, -0.005);
    p.setXYZ(i, v.x, v.y, v.z);
  }
  liningGeo.computeVertexNormals();
  const lining = new T.Mesh(
    liningGeo,
    new T.MeshStandardMaterial({
      color: 0x61462c,
      side: T.DoubleSide,
      roughness: 0.94,
    }),
  );
  lining.castShadow = lining.receiveShadow = true;
  hat.add(lining);
  const cord = new T.MeshStandardMaterial({ color: 0x55362b, roughness: 0.85 });
  const crimson = new T.MeshStandardMaterial({
    color: 0x86442f,
    roughness: 0.82,
  });
  const binding = new T.MeshStandardMaterial({
    color: 0xb9a078,
    roughness: 0.69,
  });
  const ropes = new Map<T.Material, T.BufferGeometry[]>();
  function braid(
    points: T.Vector3[],
    radius: number,
    material: T.Material,
    closed = false,
  ) {
    const path = new T.CatmullRomCurve3(points, closed);
    const g = new T.TubeGeometry(
      path,
      Math.max(18, points.length * 2),
      radius,
      5,
      closed,
    );
    if (!ropes.has(material)) ropes.set(material, []);
    ropes.get(material)!.push(g);
  }
  for (let j = 0; j < 2; j++) {
    const pts = Array.from({ length: 100 }, (_, i) =>
      pos(0.453 + j * 0.005, (2 * Math.PI * i) / 100, -0.002 + j * 0.004),
    );
    braid(pts, 0.0046, j ? cord : binding, true);
  }
  for (let j = 0; j < 7; j++) {
    const r = 0.057 + j * 0.007;
    braid(
      Array.from({ length: 56 }, (_, i) =>
        pos(r, (2 * Math.PI * i) / 56, 0.006),
      ),
      0.0042,
      j % 3 === 1 ? crimson : cord,
      true,
    );
  }
  // A cord reaches from each inner cane to the nape. Two short tied ends
  // separate against the rain cape when the pilgrim turns his head.
  for (const side of [-1, 1]) {
    braid(
      [
        new T.Vector3(side * 0.216, 0.062, 0.013),
        new T.Vector3(side * 0.156, -0.093, -0.025),
        new T.Vector3(side * 0.105, -0.159, -0.084),
        new T.Vector3(0, -0.186, -0.123),
      ],
      0.008,
      cord,
    );
    braid(
      [
        new T.Vector3(0, -0.18, -0.12),
        new T.Vector3(side * 0.023, -0.213, -0.143),
        new T.Vector3(side * 0.039, -0.27, -0.159),
        new T.Vector3(side * 0.064, -0.304, -0.168),
      ],
      0.007,
      crimson,
    );
  }
  for (let j = 0; j < 24; j++) {
    const a = (j * 2 * Math.PI) / 24 + 0.046;
    braid(
      [
        pos(0.423, a - 0.01, 0.003),
        pos(0.45, a, 0.01),
        pos(0.459, a + 0.012, 0.001),
        pos(0.448, a + 0.018, -0.012),
      ],
      0.0026,
      binding,
    );
  }
  for (const [material, parts] of ropes) {
    const m = new T.Mesh(mergeGeometries(parts), material);
    m.castShadow = m.receiveShadow = true;
    hat.add(m);
    parts.forEach((g) => g.dispose());
  }
  const knot = new T.Mesh(
    new T.TorusKnotGeometry(0.024, 0.006, 60, 7, 2, 3),
    crimson,
  );
  knot.position.y = 0.223;
  knot.scale.y = 0.72;
  hat.add(knot);
  hat.position.set(0, 1.885, 0);
  hat.rotation.x = 0.055;
  return hat;
}
