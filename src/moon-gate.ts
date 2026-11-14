import * as T from "three";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";

interface GateFinishes {
  timber: T.Material;
  bronze: T.Material;
  ceramic: T.Material;
  paper: T.Material;
  stone: T.Material;
}

export const porchLamp = new T.Vector3(-3.98, 5.15, 2.0);

/** A rain porch for the moon gate. Local ground is y=0, with the court on +z.
 * The crest is shorter than the eaves. Each tile run bends and fans out to
 * meet the corner rafters, including the underside visible in a low view. */
export function moonGatePorch(m: GateFinishes) {
  const porch = new T.Group();
  porch.name = "Moon gate rain porch";
  const batches = new Map<T.Material, T.BufferGeometry[]>();
  function add(material: T.Material, geometry: T.BufferGeometry) {
    let batch = batches.get(material);
    if (!batch) batches.set(material, (batch = []));
    const flat = geometry.index ? geometry.toNonIndexed() : geometry;
    if (flat !== geometry) geometry.dispose();
    batch.push(flat);
  }
  function block(
    mat: T.Material,
    x: number,
    y: number,
    z: number,
    w: number,
    h: number,
    d: number,
  ) {
    add(mat, new T.BoxGeometry(w, h, d).translate(x, y, z));
  }
  function timber(
    a: T.Vector3,
    b: T.Vector3,
    w: number,
    h: number,
    mat = m.timber,
  ) {
    const dir = b.clone().sub(a),
      center = a.clone().lerp(b, 0.5);
    const beam = new T.BoxGeometry(w, h, dir.length() + 0.015);
    beam.applyQuaternion(
      new T.Quaternion().setFromUnitVectors(
        new T.Vector3(0, 0, 1),
        dir.normalize(),
      ),
    );
    add(mat, beam.translate(center.x, center.y, center.z));
  }
  const point = (u: number, t: number, face: number) =>
    new T.Vector3(
      u * (6.56 + 2.52 * t),
      8.85 -
        2.38 * t +
        0.66 * t * t +
        Math.pow(Math.abs(u), 6) * (0.35 + 1.22 * t),
      face * t * 2.64,
    );
  // Surface grids preserve metre-scale UVs across individual courses.
  function patch(
    mat: T.Material,
    width: number,
    depth: number,
    sample: (x: number, y: number) => T.Vector3,
    reverse: boolean,
  ) {
    const xyz: number[] = [],
      uv: number[] = [],
      idx: number[] = [];
    for (let row = 0; row <= depth; row++)
      for (let col = 0; col <= width; col++) {
        const p = sample(col / width, row / depth);
        xyz.push(p.x, p.y, p.z);
        uv.push(p.x * 0.43, (p.y + p.z * 0.65) * 0.43);
        if (row && col) {
          const c = row * (width + 1) + col,
            a = c - width - 2,
            b = a + 1,
            d = c - 1;
          if (reverse) idx.push(a, c, b, a, d, c);
          else idx.push(a, b, c, a, c, d);
        }
      }
    const g = new T.BufferGeometry();
    g.setAttribute("position", new T.Float32BufferAttribute(xyz, 3));
    g.setAttribute("uv", new T.Float32BufferAttribute(uv, 2));
    g.setIndex(idx);
    g.computeVertexNormals();
    add(mat, g);
  }
  for (const face of [-1, 1]) {
    patch(m.timber, 42, 6, (x, y) => point(x * 2 - 1, y, face), face > 0);
    // Tops of flat pans step over the next course; the convex cover tiles
    // straddle their seams. Front lips catch the key light even from the arena.
    const bays = 50,
      courses = 6;
    for (let row = 0; row < courses; row++) {
      const t0 = row / courses,
        t1 = (row + 1) / courses;
      patch(
        m.ceramic,
        100,
        2,
        (x, y) => {
          const t = T.MathUtils.lerp(t0, t1, y),
            p = point(x * 2 - 1, t, face);
          p.y += 0.092 + 0.056 * y + 0.047 * Math.cos(x * bays * Math.PI * 2);
          return p;
        },
        face > 0,
      );
      patch(
        m.ceramic,
        100,
        1,
        (x, y) => {
          const p = point(x * 2 - 1, t1, face);
          p.y += 0.09 + 0.06 * y + 0.047 * Math.cos(x * bays * Math.PI * 2);
          return p;
        },
        face < 0,
      );
    }
    for (let j = 0; j <= bays; j++) {
      const u = (2 * j) / bays - 1;
      patch(
        m.ceramic,
        8,
        12,
        (x, y) => {
          const p = point(u, y, face),
            a = Math.PI * x;
          p.x -= 0.083 * Math.cos(a);
          p.y += 0.14 + 0.091 * Math.sin(a);
          return p;
        },
        face > 0,
      );
      const end = point(u, 1, face);
      const disk = new T.CylinderGeometry(0.109, 0.113, 0.07, 12).rotateX(
        Math.PI / 2,
      );
      add(m.ceramic, disk.translate(end.x, end.y + 0.12, end.z + face * 0.025));
      if (j % 2 === 0) {
        const dot = new T.SphereGeometry(0.043, 8, 5).scale(1, 1, 0.44);
        add(m.bronze, dot.translate(end.x, end.y + 0.12, end.z + face * 0.073));
      }
    }
    for (let j = 0; j < 40; j++) {
      const u = j / 20 - 1;
      const a = point(u, 1, face),
        b = point(u + 0.05, 1, face);
      a.y -= 0.05;
      b.y -= 0.05;
      // A lengthwise fascia under the tile ends follows their sweep.
      const beam = new T.BoxGeometry(a.distanceTo(b) + 0.03, 0.18, 0.17);
      beam.rotateZ(Math.atan2(b.y - a.y, b.x - a.x));
      const c = a.lerp(b, 0.5);
      add(m.timber, beam.translate(c.x, c.y, c.z));
    }
    for (let j = 0; j <= 18; j++) {
      const u = j / 9 - 1;
      for (let k = 0; k < 3; k++) {
        const a = point(u, k / 3, face),
          b = point(u, (k + 1) / 3, face);
        a.y -= 0.1;
        b.y -= 0.1;
        timber(a, b, 0.142, 0.17);
      }
    }
  }
  // Triangular hips close the side return below the short ends of the ridge.
  for (const s of [-1, 1]) {
    patch(
      m.ceramic,
      12,
      8,
      (x, t) => {
        const p = point(s, t, 1);
        p.z *= x * 2 - 1;
        p.y += 0.12;
        return p;
      },
      s < 0,
    );
  }
  for (const [lift, r, mat] of [
    [0.16, 0.19, m.ceramic],
    [0.37, 0.081, m.bronze],
  ] as const) {
    const pts = Array.from({ length: 21 }, (_, i) =>
      point(i / 10 - 1, 0, 1).add(new T.Vector3(0, lift, 0)),
    );
    add(mat, new T.TubeGeometry(new T.CatmullRomCurve3(pts), 60, r, 8, false));
  }
  // A pair of pierced tail ornaments carry the curved silhouette past the crest.
  for (const s of [-1, 1]) {
    const root = point(s, 0, 1);
    const scroll = new T.Shape();
    scroll.moveTo(-0.46, 0.04);
    scroll.bezierCurveTo(-0.23, 0.55, 0.58, 0.46, 0.88, 1.65);
    scroll.bezierCurveTo(1.14, 0.99, 1.02, 0.65, 0.8, 0.37);
    scroll.bezierCurveTo(1.25, 0.59, 1.49, 0.91, 1.69, 1.29);
    scroll.bezierCurveTo(1.67, 0.49, 1.05, -0.15, 0.22, -0.11);
    scroll.closePath();
    const hole = new T.Path();
    hole.moveTo(0.34, 0.19);
    hole.quadraticCurveTo(0.75, 0.44, 0.85, 0.82);
    hole.quadraticCurveTo(0.8, 0.28, 0.34, 0.19);
    scroll.holes.push(hole);
    const shape = new T.ExtrudeGeometry(scroll, {
      depth: 0.21,
      bevelSize: 0.035,
      bevelThickness: 0.033,
      bevelSegments: 2,
      curveSegments: 13,
    });
    shape.translate(0, 0, -0.105);
    if (s < 0) shape.rotateY(Math.PI);
    add(m.ceramic, shape.translate(root.x, root.y + 0.2, 0));
    const crest = [
      [0.0, 0.16],
      [0.34, 0.4],
      [0.67, 0.82],
      [0.87, 1.43],
    ].map(([x, y]) => new T.Vector3(root.x + s * x, root.y + y + 0.2, 0.15));
    add(
      m.bronze,
      new T.TubeGeometry(new T.CatmullRomCurve3(crest), 18, 0.035, 6, false),
    );
  }
  // Paired posts flank the opening without intruding into the moon aperture.
  for (const x of [-7.8, -3.36, 3.36, 7.8]) {
    const z = 1.42,
      profile = [
        [0.38, 0],
        [0.4, 0.16],
        [0.34, 0.23],
        [0.29, 0.29],
        [0.32, 0.39],
        [0.24, 0.51],
      ];
    add(
      m.stone,
      new T.LatheGeometry(
        profile.map(([r, y]) => new T.Vector2(r, y)),
        16,
      ).translate(x, 0, z),
    );
    add(
      m.timber,
      new T.CylinderGeometry(0.196, 0.237, 5.91, 18).translate(x, 3.41, z),
    );
    for (const y of [0.58, 5.89])
      add(
        m.bronze,
        new T.CylinderGeometry(0.246, 0.246, 0.075, 20).translate(x, y, z),
      );
    for (let tier = 0; tier < 3; tier++) {
      const y = 6.04 + tier * 0.23,
        w = 0.58 + tier * 0.4;
      block(m.timber, x, y, z, w, 0.16, 0.38);
      block(m.timber, x, y + 0.12, z, 0.32, 0.15, 0.55 + tier * 0.25);
      for (const s of [-1, 1])
        block(m.bronze, x + s * (w / 2 - 0.1), y + 0.135, z, 0.17, 0.13, 0.36);
    }
  }
  block(m.timber, 0, 6.83, 1.42, 16.9, 0.29, 0.47);
  block(m.bronze, 0, 6.78, 1.67, 16.75, 0.035, 0.038);
  // A single working lamp lights the sheltered front of the gate. The other
  // bay stays open to cool skylight, leaving an unequal interval of shadow.
  const { x: lx, y: ly, z: lz } = porchLamp;
  block(m.timber, lx, 6.56, 1.75, 0.15, 0.17, 0.75);
  block(m.bronze, lx, 6.11, lz, 0.038, 0.83, 0.038);
  const lanternProfile = [
    [0.15, -0.63],
    [0.3, -0.53],
    [0.42, -0.32],
    [0.46, -0.08],
    [0.45, 0.21],
    [0.36, 0.45],
    [0.24, 0.55],
    [0.14, 0.6],
  ];
  const lanternRings = lanternProfile.map(([r, y]) => new T.Vector2(r, y));
  add(m.paper, new T.LatheGeometry(lanternRings, 48).translate(lx, ly, lz));
  for (let rib = 0; rib < 12; rib++) {
    const a = (rib * Math.PI) / 6;
    const path = lanternProfile.map(
      ([r, y]) =>
        new T.Vector3(
          lx + (r + 0.012) * Math.cos(a),
          ly + y,
          lz + (r + 0.012) * Math.sin(a),
        ),
    );
    add(
      m.timber,
      new T.TubeGeometry(new T.CatmullRomCurve3(path), 18, 0.018, 5, false),
    );
  }
  for (const [r, y] of [
    [0.31, -0.52],
    [0.458, -0.09],
    [0.449, 0.2],
    [0.252, 0.53],
  ]) {
    add(
      m.bronze,
      new T.TorusGeometry(r, 0.015, 6, 48)
        .rotateX(Math.PI / 2)
        .translate(lx, ly + y, lz),
    );
  }
  for (const s of [-1, 1]) {
    add(
      m.bronze,
      new T.CylinderGeometry(0.23, 0.25, 0.12, 12).translate(
        lx,
        ly + s * 0.59,
        lz,
      ),
    );
    const tip = new T.SphereGeometry(0.1, 12, 8).scale(1, 1.34, 1);
    add(m.bronze, tip.translate(lx, ly + s * 0.71, lz));
  }
  for (let i = 0; i < 7; i++) {
    const a = (i * Math.PI * 2) / 7;
    const path = [
      new T.Vector3(lx, ly - 0.77, lz),
      new T.Vector3(
        lx + 0.045 * Math.cos(a),
        ly - 0.94,
        lz + 0.045 * Math.sin(a),
      ),
      new T.Vector3(
        lx + 0.082 * Math.cos(a),
        ly - 1.24 + 0.045 * Math.sin(2 * a),
        lz + 0.082 * Math.sin(a),
      ),
    ];
    add(
      m.timber,
      new T.TubeGeometry(new T.CatmullRomCurve3(path), 6, 0.01, 4, false),
    );
  }
  // Scrolled spandrels grow out of the posts and meet the longitudinal beam.
  for (const x of [-7.8, -3.36, 3.36, 7.8])
    for (const sign of [-1, 1]) {
      const cloud = new T.Shape();
      cloud.moveTo(0, 0);
      cloud.lineTo(0, -0.78);
      cloud.bezierCurveTo(0.1, -0.7, 0.18, -0.52, 0.33, -0.5);
      cloud.bezierCurveTo(0.62, -0.58, 0.72, -0.2, 0.5, -0.2);
      cloud.bezierCurveTo(0.42, -0.21, 0.45, -0.33, 0.55, -0.33);
      cloud.bezierCurveTo(0.33, -0.43, 0.24, -0.16, 0.53, -0.11);
      cloud.bezierCurveTo(0.74, -0.08, 0.78, -0.25, 0.97, -0.22);
      cloud.quadraticCurveTo(1.18, -0.2, 1.3, 0);
      cloud.closePath();
      const g = new T.ExtrudeGeometry(cloud, {
        depth: 0.14,
        bevelEnabled: true,
        bevelSize: 0.016,
        bevelThickness: 0.016,
        bevelSegments: 1,
        curveSegments: 9,
      });
      g.translate(0, 0, -0.07);
      if (sign < 0) g.rotateY(Math.PI);
      add(m.timber, g.translate(x, 6.72, 1.56));
    }
  for (const [material, parts] of batches) {
    const mesh = new T.Mesh(mergeGeometries(parts), material);
    mesh.castShadow = mesh.receiveShadow = true;
    porch.add(mesh);
    parts.forEach((p) => p.dispose());
  }
  return porch;
}
