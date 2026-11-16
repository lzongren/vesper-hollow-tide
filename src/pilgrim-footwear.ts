import * as T from "three";

// The pilgrim mesh stores its bind positions in metres. Work in that space so
// the seams and leather grain follow the original skin weights during a roll.
function dressBoot(material: T.MeshStandardMaterial) {
  material.onBeforeCompile = (shader) => {
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", "#include <common>\nvarying vec3 bootRest;")
      .replace(
        "#include <begin_vertex>",
        "#include <begin_vertex>\nbootRest=position;",
      );
    shader.fragmentShader = shader.fragmentShader
      .replace(
        "#include <common>",
        `#include <common>
      varying vec3 bootRest;
      float hideGrain(vec2 p) {
        vec2 i=floor(p), f=fract(p); f=f*f*(3.-2.*f);
        vec4 k=vec4(0.,1.,57.,58.)+i.x+57.*i.y;
        vec4 n=fract(sin(mod(k,2431.17))*4375.143);
        return mix(mix(n.x,n.y,f.x),mix(n.z,n.w,f.x),f.y);
      }`,
      )
      .replace(
        "#include <color_fragment>",
        `#include <color_fragment>
      float bootWeight=1.-smoothstep(.265,.285,bootRest.y);
      float rightSide=step(bootRest.x,0.);
      vec2 ankle=mix(vec2(.155,-.0255),vec2(-.167,-.096),rightSide);
      vec2 forward=normalize(mix(vec2(.046,.097),vec2(-.039,.134),rightSide));
      vec2 delta=bootRest.xz-ankle;
      float along=dot(delta,forward), across=dot(delta,vec2(forward.y,-forward.x));
      vec2 grainUV=vec2(along*280.+bootRest.y*90.,across*300.+bootRest.y*200.);
      float pores=mix(hideGrain(grainUV),.5,smoothstep(.55,1.5,length(fwidth(grainUV))));
      float wear=hideGrain(grainUV*.047);
      float toe=smoothstep(.065,.2,along);
      float welt=.026+.01*toe;
      float seam=bootRest.y-welt;
      float sole=1.-smoothstep(-.001,.002,seam);
      float stitches=step(.42,fract(along*67.+across*49.))*exp(-abs(seam-.005)*500.);
      vec3 leather=mix(vec3(.046,.022,.016),vec3(.16,.073,.039),wear*.72+pores*.18);
      float heel=1.-smoothstep(-.035,.085,along);
      float counterHeight=.06+.035*heel;
      float counter=heel*(1.-smoothstep(counterHeight-.004,counterHeight,bootRest.y));
      leather*=1.-.21*counter;
      float heelSeam=heel*exp(-abs(bootRest.y-counterHeight+.009)*580.);
      stitches=max(stitches,heelSeam*step(.36,fract(across*91.+along*77.)));
      leather*=.92+.08*cos(bootRest.y*295.+along*35.+2.*wear)*(1.-toe);
      vec3 hide=mix(leather,vec3(.045,.035,.027)*(.8+.3*pores),sole);
      hide=mix(hide,vec3(.38,.24,.125),stitches*.82);
      diffuseColor.rgb=mix(diffuseColor.rgb,hide,bootWeight);`,
      )
      .replace(
        "#include <roughnessmap_fragment>",
        `#include <roughnessmap_fragment>
        roughnessFactor=mix(roughnessFactor,.49+.21*wear+.08*sole,bootWeight);`,
      )
      .replace(
        "#include <metalnessmap_fragment>",
        `#include <metalnessmap_fragment>
        metalnessFactor*=1.-bootWeight;`,
      );
  };
  material.customProgramCacheKey = () => "pilgrim-waxed-boots";
}

export function fitTravelBoots(
  root: T.Group,
  model: T.Group,
  bones: Map<string, T.Bone>,
  weave: T.Texture,
) {
  model.traverse((o) => {
    if (o instanceof T.SkinnedMesh) {
      const materials = Array.isArray(o.material) ? o.material : [o.material];
      for (const m of materials)
        if (m instanceof T.MeshStandardMaterial) dressBoot(m);
    }
  });
  const canvas = new T.MeshStandardMaterial({
    name: "Indigo travel wraps",
    vertexColors: true,
    roughness: 0.88,
    normalMap: weave,
    normalScale: new T.Vector2(0.24, 0.24),
    side: T.DoubleSide,
  });
  const cord = new T.MeshStandardMaterial({
    name: "Worn hemp knot",
    color: 0xa39272,
    roughness: 0.96,
  });
  const harness = new T.MeshStandardMaterial({
    name: "Waxed leather ties",
    color: 0x774a32,
    roughness: 0.63,
    side: T.DoubleSide,
  });
  const faded = new T.Color(0x716e60),
    indigo = new T.Color(0x38434b),
    edge = new T.Color(0x99876c);
  for (const side of ["Left", "Right"] as const) {
    const shin = bones.get(side + "Leg")!,
      ankle = bones.get(side + "Foot")!;
    const knee = root.worldToLocal(shin.getWorldPosition(new T.Vector3()));
    const foot = root.worldToLocal(ankle.getWorldPosition(new T.Vector3()));
    const sign = side === "Left" ? 1 : -1;
    // The shin bone sits towards the front of the actual calf. Centre the
    // cloth on the calf belly, then taper into the ankle above the boot.
    const profile = (t: number, a: number, extra = 0) => {
      const belly = Math.exp(-(((t - 0.64) / 0.31) ** 2));
      const x = T.MathUtils.lerp(foot.x, knee.x, t);
      const z =
        T.MathUtils.lerp(foot.z, knee.z, t) -
        (0.035 + 0.05 * t + (sign < 0 ? -0.047 * (1 - t) : 0));
      const rx = 0.059 + 0.027 * belly + 0.026 * t + extra;
      const rz = 0.072 + 0.032 * belly + 0.028 * t + extra;
      return new T.Vector3(
        x + rx * Math.cos(a),
        T.MathUtils.lerp(foot.y, knee.y, t),
        z + rz * Math.sin(a),
      );
    };
    const pos: number[] = [],
      uv: number[] = [],
      color: number[] = [],
      indices: number[] = [];
    const turns = 6,
      columns = 64,
      rows = 7;
    // Model individual overlapping linen strips. The return at the back is
    // under the knot, and the raised selvage is actual geometry.
    for (let band = 0; band < turns; band++) {
      const start = pos.length / 3;
      for (let row = 0; row <= rows; row++)
        for (let col = 0; col <= columns; col++) {
          const u = col / columns,
            v = row / rows,
            a = u * 2 * Math.PI;
          const t =
            0.055 +
            band * 0.135 +
            v * 0.171 +
            0.034 * Math.sin(a * sign + 0.51 * band);
          const roll = Math.exp(-(((v - 0.86) / 0.15) ** 2));
          const ridge =
            0.0025 +
            0.004 * Math.cos(5 * a + band) * Math.sin(v * Math.PI) +
            0.0055 * roll +
            0.003 * v;
          const p = profile(t, a, ridge);
          pos.push(p.x, p.y, p.z);
          uv.push(u * 3.5, v * 0.34 + band * 0.18);
          const tint = indigo
            .clone()
            .lerp(
              faded,
              0.24 +
                0.22 * Math.sin(band * 1.9) +
                0.12 * Math.cos(a * 2 + band),
            )
            .lerp(edge, 0.55 * roll);
          color.push(tint.r, tint.g, tint.b);
          if (row && col) {
            const i = start + row * (columns + 1) + col;
            indices.push(
              i - columns - 2,
              i - 1,
              i - columns - 1,
              i - columns - 1,
              i - 1,
              i,
            );
          }
        }
    }
    const g = new T.BufferGeometry();
    g.setAttribute("position", new T.Float32BufferAttribute(pos, 3));
    g.setAttribute("uv", new T.Float32BufferAttribute(uv, 2));
    g.setAttribute("color", new T.Float32BufferAttribute(color, 3));
    g.setIndex(indices);
    g.computeVertexNormals();
    const gaiter = new T.Group();
    gaiter.name = side + " wrapped gaiter";
    gaiter.add(new T.Mesh(g, canvas));
    const fasten = (points: T.Vector3[], r: number) => {
      const path = new T.CatmullRomCurve3(points);
      gaiter.add(
        new T.Mesh(
          new T.TubeGeometry(path, points.length * 2, r, 6, false),
          cord,
        ),
      );
    };
    // Two flat straps bind the linen in a figure eight. Preserve the
    // crossing order by giving the ascending outer strap an extra lift.
    for (const direction of [-1, 1]) {
      const strap = new T.PlaneGeometry(1, 1, 5, 112);
      const points = strap.attributes.position,
        uv = strap.attributes.uv;
      for (let i = 0; i < points.count; i++) {
        const across = uv.getX(i) - 0.5,
          along = uv.getY(i);
        const a = sign * (1.16 + direction * 2.24 * Math.PI * along);
        const t = 0.13 + 0.64 * along + 0.042 * across;
        const ridge =
          0.014 +
          (direction > 0 ? 0.004 : 0) +
          0.0024 * (1 - 4 * across * across);
        const p = profile(t, a, ridge);
        points.setXYZ(i, p.x, p.y, p.z);
      }
      strap.computeVertexNormals();
      gaiter.add(new T.Mesh(strap, harness));
    }
    const knotAngle = sign > 0 ? -0.46 : Math.PI + 0.46;
    const knot = profile(0.79, knotAngle, 0.012);
    for (const dy of [-0.024, 0.014]) {
      const points = Array.from({ length: 41 }, (_, i) =>
        profile(
          0.79 + dy + 0.025 * Math.sin((i * Math.PI) / 20),
          knotAngle + (i * Math.PI) / 20,
          0.013,
        ),
      );
      fasten(points, 0.0038);
    }
    for (const dir of [-1, 1]) {
      const tail = [
        knot.clone(),
        knot.clone().add(new T.Vector3(sign * 0.014, 0.008, dir * 0.022)),
        knot.clone().add(new T.Vector3(sign * 0.017, -0.014, dir * 0.026)),
        knot.clone().add(new T.Vector3(sign * 0.009, -0.016, dir * 0.005)),
        knot.clone().add(new T.Vector3(sign * 0.012, -0.054, dir * 0.018)),
      ];
      fasten(tail, 0.004);
    }
    gaiter.traverse((o) => {
      if (o instanceof T.Mesh) o.castShadow = o.receiveShadow = true;
    });
    root.add(gaiter);
    shin.attach(gaiter);
  }
}
