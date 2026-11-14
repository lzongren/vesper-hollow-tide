import * as T from "three";
import { ShaderPass } from "three/addons/postprocessing/ShaderPass.js";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";

interface LightStudy {
  source: T.Vector3;
  target: T.Vector3;
  key: number;
  intensity: number;
  moon: number;
  sky: number;
  fog: number;
  air: number;
}

const studies: LightStudy[] = [
  {
    source: new T.Vector3(-9.3, 5.75, 4.1),
    target: new T.Vector3(1, 1, -2),
    key: 0xffc58c,
    intensity: 690,
    moon: 0xaacdf6,
    sky: 0xacc3dc,
    fog: 0x1c2932,
    air: 0.055,
  },
  {
    source: new T.Vector3(9.1, 5.75, 4.0),
    target: new T.Vector3(-1.1, 1, -3.5),
    key: 0xc3eadc,
    intensity: 565,
    moon: 0xbdceef,
    sky: 0xb9d3cf,
    fog: 0x213234,
    air: 0.075,
  },
  {
    source: new T.Vector3(-9.6, 5.75, 3.2),
    target: new T.Vector3(0, 0.6, -2),
    key: 0xffa05a,
    intensity: 820,
    moon: 0xb3bddf,
    sky: 0xc4bec7,
    fog: 0x312b2e,
    air: 0.075,
  },
];

/** Integrate two Gaussian volumes between the eye and the first opaque surface.
 * There are no marching steps; the closed-form integral is stable when orbiting. */
function airPass(
  camera: T.PerspectiveCamera,
  depth: T.Texture,
  clock: { value: number },
) {
  const uniforms = {
    tDiffuse: { value: null },
    tDepth: { value: depth },
    unproject: { value: camera.projectionMatrixInverse },
    cameraWorld: { value: camera.matrixWorld },
    clock,
    origin: { value: new T.Vector3() },
    axis: { value: new T.Vector3() },
    tint: { value: new T.Color() },
    amount: { value: 0 },
  };
  const material = new T.ShaderMaterial({
    uniforms,
    depthTest: false,
    depthWrite: false,
    vertexShader: `varying vec2 st;
      void main(){st=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`,
    fragmentShader: `uniform sampler2D tDiffuse,tDepth;
      uniform mat4 unproject,cameraWorld;
      uniform vec3 origin,axis,tint;uniform float clock,amount;varying vec2 st;
      float erfApprox(float x){float a=abs(x);return sign(x)*(1.-1./pow(1.+a*(.278393+a*(.230389+a*(.000972+a*.078108))),4.));}
      float cloud(vec3 eye,vec3 ray,float stop,vec3 center,vec3 dir,float width,float extent) {
        vec3 p=eye-center;
        vec3 q=(p-dir*dot(p,dir))/width+dir*dot(p,dir)/extent;
        vec3 v=(ray-dir*dot(ray,dir))/width+dir*dot(ray,dir)/extent;
        float a=dot(v,v),peak=-dot(q,v)/a;
        float off=dot(q+peak*v,q+peak*v);
        float interval=erfApprox((stop-peak)*sqrt(a))-erfApprox(-peak*sqrt(a));
        return min(1.6,max(0.,.88623*exp(-off)*interval/sqrt(a)/width));
      }
      void main(){
        vec4 color=texture2D(tDiffuse,st);
        vec4 hit=unproject*vec4(st*2.-1.,texture2D(tDepth,st).x*2.-1.,1.);
        vec3 view=hit.xyz/hit.w,eye=cameraWorld[3].xyz,ray=normalize(mat3(cameraWorld)*view);
        float stop=min(80.,length(view));
        float cone=cloud(eye,ray,stop,origin+axis*3.8,axis,1.05,4.7);
        float tail=cloud(eye,ray,stop,origin+axis*9.,axis,1.85,5.5);
        float scatter=amount*(.74*cone+.28*tail)*(.95+.05*sin(clock*.45));
        gl_FragColor=vec4(color.rgb*exp(-scatter*.37)+tint*(1.-exp(-scatter)),color.a);
      }`,
  });
  return new ShaderPass(material);
}

export class CourtLight {
  readonly spot = new T.SpotLight();
  readonly moon = new T.DirectionalLight();
  readonly sky = new T.HemisphereLight(0xffffff, 0x635044, 0.63);
  readonly veil: ShaderPass;
  constructor(
    private scene: T.Scene,
    camera: T.PerspectiveCamera,
    depth: T.Texture,
    clock: { value: number },
  ) {
    this.veil = airPass(camera, depth, clock);
    this.moon.intensity = 1.55;
    this.moon.castShadow = true;
    this.moon.shadow.mapSize.set(2048, 2048);
    Object.assign(this.moon.shadow.camera, {
      left: -22,
      right: 22,
      top: 22,
      bottom: -22,
      near: 1,
      far: 75,
    });
    this.moon.shadow.normalBias = 0.025;
    this.moon.shadow.bias = -0.00014;
    this.spot.angle = 0.99;
    this.spot.penumbra = 0.82;
    this.spot.distance = 35;
    this.spot.castShadow = true;
    this.spot.shadow.mapSize.set(1024, 1024);
    this.spot.shadow.camera.near = 0.45;
    this.spot.shadow.normalBias = 0.025;
    this.spot.shadow.bias = -0.00018;
    scene.add(this.spot, this.spot.target, this.moon, this.sky);
  }
  setCourt(index: number) {
    const s = studies[index];
    this.spot.position.copy(s.source);
    this.spot.target.position.copy(s.target);
    this.spot.color.setHex(s.key);
    this.spot.intensity = s.intensity;
    this.moon.color.setHex(s.moon);
    this.moon.position.set(index === 1 ? -13 : 13, 18, -13);
    this.sky.color.setHex(s.sky);
    this.scene.environmentIntensity = 0.64;
    this.scene.fog = new T.FogExp2(s.fog, index === 1 ? 0.022 : 0.019);
    this.scene.background = new T.Color(s.fog);
    const u = this.veil.uniforms;
    u.origin.value.copy(s.source);
    u.axis.value.subVectors(s.target, s.source).normalize();
    u.tint.value.copy(this.spot.color);
    u.amount.value = s.air;
  }
}

/** An octagonal lamp tower carries the court's key light, with a stone foot,
 * gilt suspension cage, translucent silk and visible light through the lattice. */
export function vigilLamp(
  index: number,
  m: Record<string, T.MeshStandardMaterial>,
) {
  const root = new T.Group(),
    s = studies[index],
    sign = Math.sign(s.source.x);
  const baseX = sign * 13.35,
    extension = s.source.x - baseX;
  root.position.set(baseX, 0, s.source.z);
  const batches = new Map<T.Material, T.BufferGeometry[]>();
  function add(g: T.BufferGeometry, mat: T.Material) {
    if (!batches.has(mat)) batches.set(mat, []);
    batches.get(mat)!.push(g);
  }
  const stone = m.rock,
    wood = m.wood,
    metal = m["censer-bronze"],
    gilt = m.gold;
  function post(
    x: number,
    y: number,
    r: number,
    h: number,
    mat: T.Material,
    r2 = r,
  ) {
    add(new T.CylinderGeometry(r2, r, h, 12).translate(x, y, 0), mat);
  }
  function line(points: number[][], r: number, mat: T.Material) {
    add(
      new T.TubeGeometry(
        new T.CatmullRomCurve3(
          points.map(([x, y, z]) => new T.Vector3(x, y, z)),
        ),
        26,
        r,
        8,
        false,
      ),
      mat,
    );
  }
  post(0, 0.19, 0.91, 0.38, stone, 0.81);
  post(0, 0.53, 0.72, 0.34, stone, 0.56);
  post(0, 1.03, 0.52, 0.66, stone, 0.43);
  post(0, 3.84, 0.28, 5.15, wood, 0.22);
  post(0, 1.43, 0.33, 0.16, gilt);
  post(0, 6.41, 0.3, 0.31, metal);
  line(
    [
      [-extension * 0.24, 6.47, 0],
      [0, 6.64, 0],
      [extension * 0.64, 6.77, 0],
      [extension, 6.95, 0],
    ],
    0.13,
    wood,
  );
  line(
    [
      [0, 4.55, 0],
      [extension * 0.22, 5.68, 0],
      [extension * 0.47, 6.12, 0],
      [extension * 0.7, 6.77, 0],
    ],
    0.11,
    metal,
  );
  for (const y of [1.7, 4.56, 5.05, 6.27]) post(0, y, 0.295, 0.055, gilt);
  const bulb = new T.MeshStandardMaterial({
    color: 0x946140,
    emissive: s.key,
    emissiveIntensity: 2.7,
    roughness: 0.82,
  });
  post(extension, 6.79, 0.027, 0.34, metal);
  post(extension, 6.32, 0.63, 0.36, metal, 0.1);
  post(extension, 6.14, 0.66, 0.06, gilt);
  const lamp = new T.Mesh(
    new T.LatheGeometry(
      [
        [0.25, -0.58],
        [0.42, -0.45],
        [0.52, -0.19],
        [0.53, 0.23],
        [0.39, 0.4],
      ].map(([r, y]) => new T.Vector2(r, y)),
      32,
    ),
    bulb,
  );
  // The emitter at its centre must see beyond the luminous silk.
  lamp.position.set(extension, 5.75, 0);
  root.add(lamp);
  for (let i = 0; i < 12; i++) {
    const a = (i * Math.PI) / 6,
      sn = Math.sin(a),
      cs = Math.cos(a);
    const pts = [
      [0.25, -0.58],
      [0.43, -0.45],
      [0.535, -0.19],
      [0.54, 0.23],
      [0.405, 0.4],
    ];
    line(
      pts.map(([r, y]) => [extension + r * cs, 5.75 + y, r * sn]),
      0.016,
      metal,
    );
  }
  for (const [r, y] of [
    [0.42, 5.3],
    [0.545, 5.64],
    [0.54, 5.95],
    [0.4, 6.15],
  ])
    add(
      new T.TorusGeometry(r, 0.017, 6, 48)
        .rotateX(Math.PI / 2)
        .translate(extension, y, 0),
      gilt,
    );
  post(extension, 5.14, 0.3, 0.09, metal);
  post(extension, 5.04, 0.13, 0.11, gilt, 0.23);
  for (const [mat, parts] of batches) {
    const normalized = parts.map((g) => (g.index ? g.toNonIndexed() : g));
    const piece = new T.Mesh(mergeGeometries(normalized), mat);
    piece.castShadow = piece.receiveShadow = true;
    root.add(piece);
    for (const g of new Set([...parts, ...normalized])) g.dispose();
  }
  return root;
}
