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
  const pos = (r: number, a: number, lift = 0) =>
    new T.Vector3(
      Math.sin(a) * r,
      0.19 * (1 - r / 0.46) ** 1.4 +
        0.014 * Math.cos(a * 2 - 0.6) * (r / 0.46) ** 2 +
        lift,
      Math.cos(a) * r * 0.94,
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
        colors.push(color.r, color.g, color.b);
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
  const lining = new T.Mesh(
    new T.ConeGeometry(0.447, 0.18, 64, 1, true),
    new T.MeshStandardMaterial({
      color: 0x463720,
      side: T.DoubleSide,
      roughness: 0.89,
    }),
  );
  lining.position.y = 0.08;
  lining.scale.z = 0.94;
  hat.add(lining);
  const knot = new T.Mesh(
    new T.SphereGeometry(0.042, 16, 12),
    new T.MeshStandardMaterial({ color: 0x973b25, roughness: 0.62 }),
  );
  knot.scale.y = 0.6;
  knot.position.y = 0.179;
  hat.add(knot);
  hat.position.set(0, 1.885, 0);
  hat.rotation.x = 0.055;
  return hat;
}
