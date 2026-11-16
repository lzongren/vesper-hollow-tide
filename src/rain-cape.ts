import * as T from "three";

/** A sewn palm-fibre cape. Each strip samples the shoulder cloth beneath it,
 * so the sewn edge, overlaps and tips all travel with the existing simulation. */
export class RainCape extends T.Mesh<T.BufferGeometry, T.MeshStandardMaterial> {
  private readonly corners: Uint16Array;
  private readonly weights: Float32Array;
  private readonly offsets: Float32Array;

  constructor(panel: T.PlaneGeometry) {
    const g = new T.BufferGeometry();
    const mat = new T.MeshStandardMaterial({
      side: T.DoubleSide,
      vertexColors: true,
      roughness: 0.88,
    });
    super(g, mat);
    this.name = "Knotted palm rain cape";
    this.castShadow = this.receiveShadow = true;
    this.frustumCulled = false;
    const indices: number[] = [],
      colors: number[] = [],
      slots: number[] = [],
      blends: number[] = [],
      offsets: number[] = [];
    const cols = panel.parameters.widthSegments,
      rows = panel.parameters.heightSegments;
    const tawny = new T.Color(0xac8357),
      umber = new T.Color(0x493a2c),
      straw = new T.Color(0xc3a379);
    const tint = new T.Color();
    let seed = 35617;
    const random = () => {
      seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
      return seed / 4294967296;
    };
    function point(
      u: number,
      t: number,
      depth: number,
      drop: number,
      color: T.Color,
    ) {
      const x = T.MathUtils.clamp(u, 0, 1) * cols,
        y = T.MathUtils.clamp(t, 0, 1) * rows;
      const col = Math.min(cols - 1, Math.floor(x)),
        row = Math.min(rows - 1, Math.floor(y));
      const dx = x - col,
        dy = y - row,
        a = row * (cols + 1) + col;
      slots.push(a, a + 1, a + cols + 1, a + cols + 2);
      blends.push((1 - dx) * (1 - dy), dx * (1 - dy), (1 - dx) * dy, dx * dy);
      const angle = (u * 2 - 1) * 1.54;
      offsets.push(Math.sin(angle) * depth, drop, -Math.cos(angle) * depth);
      colors.push(color.r, color.g, color.b);
    }
    // Lower courses tuck under the lifted edge above. Adjacent strips start
    // in little bundles, then fan apart around the arms.
    for (let course = 3; course >= 0; course--) {
      const bundles = 24 + course * 3;
      for (let bundle = 0; bundle < bundles; bundle++) {
        const center = (bundle + 0.5) / bundles;
        const slope = (center - 0.5) * 0.032 + 0.008 * Math.sin(bundle * 2.17);
        const hem =
          0.69 +
          0.22 * Math.sin(Math.PI * center) +
          0.045 * Math.sin(8 * center + 0.24) +
          0.047 * Math.sin(bundle * 1.17);
        const start =
          0.07 + course * 0.172 + 0.045 * Math.sin(Math.PI * center);
        for (let k = 0; k < 4; k++) {
          const offset = (k - 1.5) * 0.0068;
          const end =
            course === 3 ? hem + 0.1 * random() : start + 0.27 + 0.1 * random();
          const bend = slope + offset * 0.83 + (random() - 0.5) * 0.015;
          const width = (0.0045 + 0.0018 * random()) * (1 + 0.23 * course);
          const loose = 0.019 + random() * 0.038;
          const tone = 0.13 + 0.53 * random() + 0.12 * Math.sin(bundle * 1.23);
          const first = colors.length / 3;
          for (let j = 0; j <= 6; j++) {
            const v = j / 6,
              t = T.MathUtils.lerp(start, end, v);
            const u = center + offset * (0.65 + v) + bend * v * v;
            const w =
              width * (0.92 + 0.28 * Math.sin(Math.PI * v) - 0.81 * v ** 5);
            const lift =
              0.009 +
              0.005 * (3 - course) +
              0.011 * Math.sin(Math.PI * v) +
              loose * v ** 3;
            for (const edge of [-1, 0, 1]) {
              tint
                .copy(umber)
                .lerp(tawny, tone)
                .lerp(straw, 0.1 * v + 0.18 * (edge === 0 ? 1 : 0));
              tint.multiplyScalar(0.67 + 0.32 * v + 0.08 * edge);
              point(
                u + edge * w,
                t,
                lift + (1 - Math.abs(edge)) * 0.0045,
                -(0.04 + 0.046 * Math.sin(bundle * 1.81) ** 2) * v ** 3,
                tint,
              );
            }
            if (j < 6)
              for (let e = 0; e < 2; e++) {
                const a = first + 3 * j + e;
                indices.push(a, a + 1, a + 3, a + 1, a + 4, a + 3);
              }
          }
        }
      }
    }
    // Braided binding is sewn across the collar. Crossings alternate in depth.
    for (let thread = 0; thread < 3; thread++) {
      const first = colors.length / 3;
      for (let j = 0; j <= 180; j++) {
        const u = j / 180,
          phase = u * 29 * Math.PI * 2 + (thread * Math.PI * 2) / 3;
        const t =
          0.065 + 0.047 * Math.sin(Math.PI * u) + 0.01 * Math.sin(phase);
        tint.setHex(
          thread === 0 ? 0x9a6840 : thread === 1 ? 0x553d2c : 0xbc9466,
        );
        for (const dir of [-1, 1])
          point(u, t + 0.008 * dir, 0.036 + 0.004 * Math.cos(phase), 0, tint);
        const a = first + 2 * j;
        if (j < 180) indices.push(a, a + 1, a + 2, a + 1, a + 3, a + 2);
      }
    }
    this.corners = Uint16Array.from(slots);
    this.weights = Float32Array.from(blends);
    this.offsets = Float32Array.from(offsets);
    const p = new T.Float32BufferAttribute(colors.length, 3).setUsage(
      T.DynamicDrawUsage,
    );
    g.setAttribute("position", p);
    g.setAttribute("color", new T.Float32BufferAttribute(colors, 3));
    g.setIndex(indices);
    this.fit(panel.attributes.position as T.BufferAttribute);
    (g.attributes.normal as T.BufferAttribute).setUsage(T.DynamicDrawUsage);
  }

  fit(panel: T.BufferAttribute) {
    const dest = this.geometry.attributes.position as T.BufferAttribute;
    const points = panel.array;
    for (let i = 0; i < dest.count; i++) {
      let x = this.offsets[3 * i],
        y = this.offsets[3 * i + 1],
        z = this.offsets[3 * i + 2];
      for (let j = 0; j < 4; j++) {
        const k = 4 * i + j,
          source = this.corners[k] * 3,
          w = this.weights[k];
        x += points[source] * w;
        y += points[source + 1] * w;
        z += points[source + 2] * w;
      }
      dest.setXYZ(i, x, y, z);
    }
    dest.needsUpdate = true;
    this.geometry.computeVertexNormals();
  }
}
