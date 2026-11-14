import * as T from "three";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";

type Palette = Record<string, T.MeshStandardMaterial>;

/** Twin open handles and three splayed feet frame the silhouette of a ding. */
export function incenseVessel(m: Palette) {
  const vessel = new T.Group();
  const bronze: T.BufferGeometry[] = [],
    gilt: T.BufferGeometry[] = [];
  const body = new T.LatheGeometry(
    [
      [0, 0.36],
      [0.33, 0.37],
      [0.52, 0.46],
      [0.67, 0.65],
      [0.7, 0.81],
      [0.65, 0.94],
      [0.67, 1.01],
      [0.75, 1.025],
      [0.754, 1.065],
      [0.69, 1.075],
      [0.59, 0.94],
      [0.49, 0.68],
      [0, 0.62],
    ].map(([r, y]) => new T.Vector2(r, y)),
    64,
  );
  bronze.push(body);
  function cord(
    batch: T.BufferGeometry[],
    path: number[][],
    r: number,
    steps = 28,
  ) {
    const spline = new T.CatmullRomCurve3(
      path.map(([x, y, z]) => new T.Vector3(x, y, z)),
    );
    batch.push(new T.TubeGeometry(spline, steps, r, 8, false));
  }
  for (const sign of [-1, 1]) {
    const outline = [
      [0.58, 0.76],
      [0.83, 0.88],
      [0.93, 1.15],
      [1.01, 1.32],
      [0.92, 1.43],
      [0.76, 1.4],
      [0.71, 1.27],
      [0.73, 1.06],
    ];
    cord(
      bronze,
      outline.map(([x, y]) => [x * sign, y, 0]),
      0.073,
    );
    cord(
      gilt,
      outline.map(([x, y]) => [x * sign, y, 0.066]),
      0.014,
    );
  }
  for (let i = 0; i < 3; i++) {
    const a = (i * 2 * Math.PI) / 3;
    cord(
      bronze,
      [
        [0.41, 0.49],
        [0.52, 0.32],
        [0.49, 0.14],
        [0.54, 0.045],
      ].map(([r, y]) => [Math.sin(a) * r, y, Math.cos(a) * r]),
      0.092,
    );
  }
  for (let i = 0; i < 16; i++) {
    const a = (i / 16) * Math.PI * 2;
    const spiral = Array.from({ length: 21 }, (_, j) => {
      const t = j / 20,
        theta = t * Math.PI * 2.3,
        spread = (1 - t) * 0.12;
      const y = 0.8 + Math.sin(theta) * spread,
        angle = a + Math.cos(theta) * spread * 1.4;
      const r = 0.708 - (y - 0.8) ** 2 * 2.4;
      return [Math.sin(angle) * r, y, Math.cos(angle) * r];
    });
    cord(gilt, spiral, 0.014, 20);
  }
  for (const [y, r] of [
    [0.56, 0.611],
    [0.95, 0.658],
    [1.05, 0.751],
  ]) {
    gilt.push(
      new T.TorusGeometry(r, 0.013, 7, 64)
        .rotateX(Math.PI / 2)
        .translate(0, y, 0),
    );
  }
  function batch(parts: T.BufferGeometry[], mat: T.Material) {
    const mesh = new T.Mesh(mergeGeometries(parts), mat);
    mesh.castShadow = mesh.receiveShadow = true;
    vessel.add(mesh);
    parts.forEach((g) => g.dispose());
  }
  batch(bronze, m["censer-bronze"]);
  batch(gilt, m.gold);
  const ash = new T.Mesh(new T.CylinderGeometry(0.59, 0.55, 0.04, 48), m.rock);
  ash.position.y = 0.945;
  vessel.add(ash);
  for (let i = 0; i < 3; i++) {
    const stalk = new T.Group();
    stalk.position.set((i - 1) * 0.093, 0.95, i === 1 ? -0.06 : 0.06);
    stalk.rotation.z = (i - 1) * -0.1;
    const stick = new T.Mesh(
      new T.CylinderGeometry(0.011, 0.014, 0.76, 8),
      m.wood,
    );
    stick.position.y = 0.38;
    const ember = new T.Mesh(new T.SphereGeometry(0.014, 8, 6), m.fire);
    ember.position.y = 0.766;
    stalk.add(stick, ember);
    vessel.add(stalk);
  }
  return vessel;
}

/** Two noise fields bend and tear the plume as it cools away from the sticks. */
export function incenseSmoke(time: { value: number }, seed: number) {
  const material = new T.ShaderMaterial({
    uniforms: { time, seed: { value: seed } },
    transparent: true,
    depthWrite: false,
    side: T.DoubleSide,
    vertexShader: `varying vec2 vUv;
    void main(){vUv=uv;vec4 origin=modelViewMatrix*vec4(0.,0.,0.,1.);
    vec2 size=vec2(length(modelMatrix[0].xyz),length(modelMatrix[1].xyz));
    origin.xy+=position.xy*size;gl_Position=projectionMatrix*origin;}`,
    fragmentShader: `uniform float time,seed; varying vec2 vUv;
    float noise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);
      vec4 n=sin(vec4(0.,1.,57.,58.)+i.x+57.*i.y)*43758.54;
      return mix(mix(fract(n.x),fract(n.y),f.x),mix(fract(n.z),fract(n.w),f.x),f.y);}
    void main(){float y=vUv.y,x=vUv.x-.50,t=time*.29+seed;
      float curl=noise(vec2(y*3.1-t,seed))*2.-1.;
      x-=y*(curl*.22+.13*sin(7.*y-t));
      float w=.012+.15*y;
      float fine=noise(vec2(x*18.+t,y*11.-2.*t));
      float alpha=exp(-pow(x/w,2.))*(.3+.7*fine)*(1.-smoothstep(.34,1.,y))*smoothstep(0.,.035,y);
      gl_FragColor=vec4(mix(vec3(.26,.30,.31),vec3(.73,.69,.57),fine),.40*alpha);
      #include <tonemapping_fragment>
      #include <colorspace_fragment>
    }`,
  });
  const g = new T.PlaneGeometry(2.1, 3.6).translate(0, 1.8, 0);
  const mesh = new T.Mesh(g, material);
  mesh.frustumCulled = false;
  return mesh;
}
