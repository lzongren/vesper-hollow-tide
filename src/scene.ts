import * as T from "three";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";
import { Combat, angleDiff, type GameEvent, type Vec } from "./combat";

const mat = (color: number, metalness = 0, roughness = 0.7, emissive = 0) =>
  new T.MeshStandardMaterial({
    color,
    metalness,
    roughness,
    emissive,
    emissiveIntensity: emissive ? 1.5 : 0,
    flatShading: true,
  });
const stone = mat(0x42504e, 0.2),
  dark = mat(0x121b20, 0.55, 0.4),
  gold = mat(0xb59c65, 0.75, 0.3),
  ivory = mat(0xd5d8ce, 0.3, 0.45),
  red = mat(0x732d2b, 0.1),
  glow = mat(0xffbb68, 0, 0.6, 0xff9c42);
const geo = {
  box: new T.BoxGeometry(1, 1, 1),
  sphere: new T.IcosahedronGeometry(1, 1),
  cylinder: new T.CylinderGeometry(1, 1, 1, 10),
  cone: new T.ConeGeometry(1, 1, 8),
};
function mesh(
  g: T.BufferGeometry,
  m: T.Material,
  parent: T.Object3D,
  pos: number[] = [0, 0, 0],
  scale: number[] = [1, 1, 1],
) {
  const o = new T.Mesh(g, m);
  o.position.set(pos[0], pos[1], pos[2]);
  o.scale.set(scale[0], scale[1], scale[2]);
  o.castShadow = true;
  o.receiveShadow = true;
  parent.add(o);
  return o;
}
function box(
  p: T.Object3D,
  m: T.Material,
  x: number,
  y: number,
  z: number,
  sx: number,
  sy: number,
  sz: number,
) {
  return mesh(geo.box, m, p, [x, y, z], [sx, sy, sz]);
}
function sphere(
  p: T.Object3D,
  m: T.Material,
  x: number,
  y: number,
  z: number,
  sx: number,
  sy: number,
  sz: number,
) {
  return mesh(geo.sphere, m, p, [x, y, z], [sx, sy, sz]);
}
function cylinder(
  p: T.Object3D,
  m: T.Material,
  x: number,
  y: number,
  z: number,
  r: number,
  h: number,
) {
  return mesh(geo.cylinder, m, p, [x, y, z], [r, h, r]);
}
function ring(
  p: T.Object3D,
  m: T.Material,
  r: number,
  tube: number,
  y: number,
) {
  const rmesh = mesh(new T.TorusGeometry(r, tube, 6, 80), m, p, [0, y, 0]);
  rmesh.rotation.x = Math.PI / 2;
  return rmesh;
}
function limb(
  parent: T.Object3D,
  m: T.Material,
  x: number,
  y: number,
  z: number,
  w: number,
  h: number,
) {
  const pivot = new T.Group();
  pivot.position.set(x, y, z);
  parent.add(pivot);
  box(pivot, m, 0, -h / 2, 0, w, h, w);
  return pivot;
}
function blade(parent: T.Object3D, len: number, m = ivory) {
  const g = new T.Group();
  parent.add(g);
  const b = mesh(
    new T.ConeGeometry(0.12, len, 4),
    m,
    g,
    [0, len / 2, 0],
    [0.7, 1, 1.1],
  );
  b.rotation.y = Math.PI / 4;
  box(g, gold, 0, 0, 0, 0.52, 0.09, 0.12);
  cylinder(g, dark, 0, -0.2, 0, 0.07, 0.35);
  return g;
}
function stoneTexture() {
  const c = document.createElement("canvas");
  c.width = c.height = 256;
  const ctx = c.getContext("2d")!;
  let seed = 5827;
  const rand = () => {
    seed = (seed * 1664525 + 1013904223) >>> 0;
    return seed / 4294967296;
  };
  ctx.fillStyle = "#c6cbc0";
  ctx.fillRect(0, 0, 256, 256);
  for (let i = 0; i < 7000; i++) {
    const v = 110 + Math.floor(rand() * 110);
    ctx.fillStyle = `rgba(${v},${v},${v},.14)`;
    ctx.fillRect(rand() * 256, rand() * 256, 1 + rand() * 3, 1 + rand() * 3);
  }
  for (let i = 0; i < 7; i++) {
    let x = rand() * 256,
      y = rand() * 256;
    ctx.beginPath();
    ctx.moveTo(x, y);
    for (let j = 0; j < 6; j++) {
      x += (rand() - 0.5) * 40;
      y += rand() * 20;
      ctx.lineTo(x, y);
    }
    ctx.strokeStyle = "#56696355";
    ctx.lineWidth = 0.7;
    ctx.stroke();
  }
  ctx.strokeStyle = "#e4e4cb77";
  ctx.lineWidth = 2;
  ctx.strokeRect(3, 3, 250, 250);
  const t = new T.CanvasTexture(c);
  t.colorSpace = T.SRGBColorSpace;
  t.anisotropy = 4;
  return t;
}
interface Rig {
  root: T.Group;
  body: T.Group;
  left: T.Group;
  right: T.Group;
  legL: T.Group;
  legR: T.Group;
  cape: T.Mesh;
  weapon: T.Group;
  wings: T.Group[];
}
function character(kind: number): Rig {
  const root = new T.Group(),
    body = new T.Group();
  root.add(body);
  const isPlayer = kind < 0;
  const cloth = isPlayer
    ? red
    : kind === 1
      ? ivory
      : kind === 2
        ? mat(0x592722)
        : dark;
  const bodyMat = isPlayer
    ? dark
    : kind === 0
      ? mat(0x394544, 0.75, 0.35)
      : cloth;
  sphere(body, bodyMat, 0, 1.45, 0, 0.43, 0.62, 0.26);
  box(body, gold, 0, 1.2, 0, 0.57, 0.1, 0.4);
  const skirt = mesh(
    new T.ConeGeometry(0.62, 1, 7, 1, true),
    cloth,
    body,
    [0, 0.83, 0],
  );
  skirt.rotation.z = Math.PI;
  skirt.material = new T.MeshStandardMaterial({
    color: (cloth as T.MeshStandardMaterial).color,
    side: T.DoubleSide,
    flatShading: true,
  });
  const head = sphere(
    body,
    isPlayer ? dark : cloth,
    0,
    2.18,
    0,
    0.29,
    0.37,
    0.29,
  );
  head.rotation.x = -0.12;
  sphere(body, ivory, 0, 2.15, 0.235, 0.19, 0.24, 0.055);
  box(body, dark, 0, 2.2, 0.29, 0.24, 0.035, 0.025);
  const eyeMat = mat(
    isPlayer ? 0x97ebe0 : 0xffc477,
    0,
    0.5,
    isPlayer ? 0x48bcb2 : 0xffa34c,
  );
  sphere(body, eyeMat, 0, 2.2, 0.32, 0.065, 0.022, 0.015);
  const left = limb(body, bodyMat, -0.49, 1.84, 0, 0.19, 0.72),
    right = limb(body, bodyMat, 0.49, 1.84, 0, 0.19, 0.72);
  sphere(body, gold, -0.44, 1.83, 0, 0.23, 0.12, 0.27);
  sphere(body, gold, 0.44, 1.83, 0, 0.23, 0.12, 0.27);
  const legL = limb(body, dark, -0.21, 0.74, 0, 0.23, 0.7),
    legR = limb(body, dark, 0.21, 0.74, 0, 0.23, 0.7);
  box(legL, dark, 0, -0.65, 0.1, 0.25, 0.2, 0.4);
  box(legR, dark, 0, -0.65, 0.1, 0.25, 0.2, 0.4);
  const cape = mesh(
    new T.ConeGeometry(0.62, 1.8, 5, 1, true, 0, Math.PI),
    cloth,
    body,
    [0, 1.2, -0.17],
  );
  cape.rotation.x = 0.18;
  cape.rotation.y = Math.PI;
  cape.material = new T.MeshStandardMaterial({
    color: cloth.color,
    side: T.DoubleSide,
    flatShading: true,
  });
  const weapon = new T.Group();
  right.add(weapon);
  weapon.position.set(0, -0.6, 0.05);
  weapon.rotation.x = -0.4;
  const wings: T.Group[] = [];
  if (isPlayer) {
    const s = blade(weapon, 1.65);
    s.rotation.x = -0.75;
    const scarf = box(body, red, -0.1, 1.95, -0.55, 0.17, 0.12, 1.3);
    scarf.rotation.z = 0.15;
  }
  if (kind === 0) {
    root.scale.setScalar(1.55);
    body.scale.x = 1.25;
    body.scale.z = 1.2;
    const helm = mesh(
      new T.ConeGeometry(0.46, 0.8, 6),
      gold,
      body,
      [0, 2.49, 0],
    );
    helm.rotation.y = Math.PI / 6;
    for (const side of [-1, 1]) {
      const horn = mesh(new T.ConeGeometry(0.09, 0.9, 5), ivory, body, [
        side * 0.42,
        2.65,
        0,
      ]);
      horn.rotation.z = -side * 0.5;
    }
    cylinder(weapon, gold, 0, 0.25, 0, 0.07, 2.5);
    const bell = mesh(
      new T.CylinderGeometry(0.35, 0.8, 0.9, 12, 1, true),
      gold,
      weapon,
      [0, 1.35, 0],
    );
    bell.rotation.x = 0.18;
    ring(weapon, gold, 0.78, 0.07, 0.9);
    sphere(weapon, glow, 0, 1.02, 0, 0.16, 0.2, 0.16);
    for (let j = 0; j < 5; j++)
      box(body, gold, (j - 2) * 0.13, 1.56, 0.285, 0.04, 0.7, 0.04);
  }
  if (kind === 1) {
    root.scale.setScalar(1.35);
    for (const side of [-1, 1]) {
      const wing = new T.Group();
      wing.position.set(side * 0.35, 1.8, -0.12);
      body.add(wing);
      wings.push(wing);
      for (let i = 0; i < 10; i++) {
        const feather = mesh(
          new T.ConeGeometry(0.17, 1.1 + i * 0.085, 4),
          i % 2 ? ivory : mat(0x829f9c, 0.25),
          wing,
          [side * (0.2 + i * 0.17), -0.1 - i * 0.07, -i * 0.065],
        );
        feather.rotation.z = side * (0.75 + i * 0.035);
        feather.rotation.x = -0.28;
      }
    }
    const s = blade(weapon, 2);
    s.rotation.x = -1.1;
    const off = blade(left, 1.3);
    off.position.y = -0.68;
    off.rotation.x = -1.8;
    const crown = mesh(
      new T.TorusGeometry(0.38, 0.025, 5, 48),
      gold,
      body,
      [0, 2.6, 0],
    );
    crown.rotation.x = Math.PI / 2;
    for (let i = 0; i < 6; i++) {
      const a = (i * Math.PI) / 3;
      const petal = mesh(new T.ConeGeometry(0.09, 0.7, 4), ivory, body, [
        Math.sin(a) * 0.32,
        2.7,
        Math.cos(a) * 0.32,
      ]);
      petal.rotation.z = -Math.sin(a) * 0.35;
    }
  }
  if (kind === 2) {
    root.scale.setScalar(1.55);
    body.scale.y = 1.15;
    const halo = mesh(
      new T.TorusGeometry(0.65, 0.035, 7, 64),
      glow,
      body,
      [0, 2.6, -0.25],
    );
    halo.rotation.z = 0.2;
    for (let i = 0; i < 9; i++) {
      const a = (i / 9) * Math.PI * 2;
      sphere(
        body,
        glow,
        Math.sin(a) * 0.78,
        2.6 + Math.cos(a) * 0.78,
        -0.25,
        0.055,
        0.055,
        0.055,
      );
    }
    cylinder(weapon, gold, 0, 0.65, 0, 0.07, 3.1);
    const top = mesh(
      new T.TorusGeometry(0.33, 0.04, 7, 32),
      gold,
      weapon,
      [0, 2.25, 0],
    );
    sphere(top, glow, 0, 0, 0, 0.12, 0.2, 0.12);
    for (let i = 0; i < 8; i++) {
      const a = (i / 8) * Math.PI * 2;
      const strip = box(
        body,
        i % 2 ? gold : red,
        Math.sin(a) * 0.55,
        0.85,
        Math.cos(a) * 0.55,
        0.1,
        1.65,
        0.055,
      );
      strip.rotation.x = Math.cos(a) * 0.18;
      strip.rotation.z = -Math.sin(a) * 0.18;
    }
  }
  return { root, body, left, right, legL, legR, cape, weapon, wings };
}
interface Particle {
  mesh: T.Mesh;
  velocity: T.Vector3;
  life: number;
  max: number;
}
export class World {
  renderer: T.WebGLRenderer;
  scene = new T.Scene();
  camera = new T.PerspectiveCamera(42, 1, 0.1, 150);
  composer: EffectComposer;
  arena = new T.Group();
  player = character(-1);
  boss = character(0);
  bossIndex = -1;
  ambient: T.HemisphereLight;
  moon: T.DirectionalLight;
  fill: T.PointLight;
  particles: Particle[] = [];
  hazards = new Map<number, T.Group>();
  telegraph = new T.Group();
  slash = new T.Group();
  lock = new T.Group();
  ash: T.Points;
  water: T.Mesh;
  quality = "high";
  reducedMotion = false;
  shake = 0;
  ray = new T.Raycaster();
  plane = new T.Plane(new T.Vector3(0, 1, 0), 0);
  time = 0;
  paused = false;
  stoneMap = stoneTexture();
  trails: { mesh: T.Mesh; life: number; max: number }[] = [];
  constructor(readonly canvas: HTMLCanvasElement) {
    this.renderer = new T.WebGLRenderer({
      canvas,
      antialias: true,
      powerPreference: "high-performance",
    });
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 1.6));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = T.PCFSoftShadowMap;
    this.renderer.toneMapping = T.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.25;
    this.scene.background = new T.Color(0x0b161c);
    this.scene.fog = new T.FogExp2(0x15252c, 0.024);
    this.ambient = new T.HemisphereLight(0xc6e0e4, 0x44504b, 2.7);
    this.scene.add(this.ambient);
    this.moon = new T.DirectionalLight(0xc2e8ef, 3.4);
    this.moon.position.set(-8, 18, -8);
    this.moon.castShadow = true;
    this.moon.shadow.mapSize.set(2048, 2048);
    Object.assign(this.moon.shadow.camera, {
      left: -19,
      right: 19,
      top: 19,
      bottom: -19,
      far: 65,
    });
    this.moon.shadow.bias = -0.0004;
    this.scene.add(this.moon);
    this.fill = new T.PointLight(0xfeb36e, 80, 35, 2);
    this.fill.position.set(3, 6, 6);
    this.scene.add(this.fill);
    for (const x of [-9, 9]) {
      const lamp = new T.PointLight(0xf0a65e, 65, 17, 2);
      lamp.position.set(x, 3, -6);
      this.scene.add(lamp);
    }
    this.water = mesh(
      new T.PlaneGeometry(220, 220, 1, 1),
      new T.MeshStandardMaterial({
        color: 0x1c373e,
        metalness: 0.8,
        roughness: 0.25,
      }),
      this.scene,
      [0, -0.4, 0],
    );
    this.water.rotation.x = -Math.PI / 2;
    this.scene.add(
      this.arena,
      this.player.root,
      this.boss.root,
      this.telegraph,
      this.slash,
      this.lock,
    );
    const lockMat = new T.MeshBasicMaterial({
      color: 0xf2e0ae,
      transparent: true,
      opacity: 0.9,
    });
    const lm = mesh(new T.TorusGeometry(0.25, 0.018, 4, 4), lockMat, this.lock);
    lm.rotation.z = Math.PI / 4;
    const positions = new Float32Array(420 * 3);
    for (let i = 0; i < 420; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 50;
      positions[i * 3 + 1] = Math.random() * 15;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 50;
    }
    const ag = new T.BufferGeometry();
    ag.setAttribute("position", new T.BufferAttribute(positions, 3));
    this.ash = new T.Points(
      ag,
      new T.PointsMaterial({
        color: 0xa8c0b8,
        size: 0.045,
        transparent: true,
        opacity: 0.65,
        depthWrite: false,
      }),
    );
    this.scene.add(this.ash);
    this.composer = new EffectComposer(this.renderer);
    this.composer.addPass(new RenderPass(this.scene, this.camera));
    this.composer.addPass(
      new UnrealBloomPass(new T.Vector2(800, 600), 0.38, 0.6, 1.05),
    );
    this.composer.addPass(new OutputPass());
    this.resize();
    this.setArena(0);
  }
  resize() {
    const w = innerWidth,
      h = innerHeight;
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(w, h);
    this.composer.setSize(w, h);
  }
  setQuality(value: string) {
    this.quality = value;
    this.renderer.setPixelRatio(
      value === "low" ? 1 : Math.min(devicePixelRatio, 1.6),
    );
    this.renderer.shadowMap.enabled = value !== "low";
    this.resize();
  }
  clear(group: T.Group) {
    const geometries = new Set<T.BufferGeometry>(),
      materials = new Set<T.Material>();
    group.traverse((o) => {
      if (o instanceof T.Mesh) {
        if (!Object.values(geo).includes(o.geometry))
          geometries.add(o.geometry);
        for (const m of Array.isArray(o.material) ? o.material : [o.material])
          if (
            ![stone, dark, gold, ivory, red, glow].some(
              (shared) => shared === m,
            )
          )
            materials.add(m);
      }
    });
    geometries.forEach((g) => g.dispose());
    materials.forEach((m) => m.dispose());
    group.clear();
  }
  setArena(index: number) {
    if (this.bossIndex === index) return;
    this.bossIndex = index;
    this.clear(this.arena);
    this.scene.remove(this.boss.root);
    this.clear(this.boss.root);
    this.boss = character(index);
    this.scene.add(this.boss.root);
    this.hazards.forEach((g) => {
      this.scene.remove(g);
      this.clear(g);
    });
    this.hazards.clear();
    this.scene.fog = new T.FogExp2(
      [0x15252c, 0x172b30, 0x241c24][index],
      0.025,
    );
    this.scene.background = new T.Color([0x0b161c, 0x0b1b22, 0x1b131c][index]);
    this.fill.color.setHex([0xffb66e, 0x89ffde, 0xff7344][index]);
    const floorMat = mat([0x87968b, 0x839e93, 0x9c9188][index], 0.25, 0.58);
    floorMat.map = this.stoneMap;
    floorMat.bumpMap = this.stoneMap;
    floorMat.bumpScale = 0.055;
    cylinder(this.arena, stone, 0, -0.34, 0, 13, 0.65);
    const tileGeo = new T.BoxGeometry(1.38, 0.1, 1.38);
    const tiles = new T.InstancedMesh(tileGeo, floorMat, 300);
    let n = 0;
    const dummy = new T.Object3D();
    for (let x = -8; x <= 8; x++)
      for (let z = -8; z <= 8; z++) {
        if (Math.hypot(x, z) > 8.3) continue;
        dummy.position.set(
          x * 1.5,
          0.035 + Math.sin(x * 11 + z * 7) * 0.012,
          z * 1.5,
        );
        dummy.rotation.y = Math.sin(x * z) * 0.015;
        dummy.updateMatrix();
        tiles.setMatrixAt(n, dummy.matrix);
        tiles.setColorAt(
          n,
          new T.Color().setHSL(
            0.48,
            0.055,
            0.38 + (0.5 + 0.5 * Math.sin(x * 32 + z * 23)) * 0.15,
          ),
        );
        n++;
      }
    tiles.count = n;
    tiles.receiveShadow = true;
    this.arena.add(tiles);
    ring(this.arena, gold, 12.4, 0.045, 0.13);
    ring(this.arena, gold, 11.8, 0.025, 0.13);
    ring(this.arena, gold, 5.4, 0.025, 0.13);
    ring(this.arena, gold, 2.4, 0.02, 0.13);
    for (let i = 0; i < 64; i++) {
      const a = (i / 64) * Math.PI * 2;
      const mark = box(
        this.arena,
        gold,
        Math.sin(a) * 11.5,
        0.14,
        Math.cos(a) * 11.5,
        0.025,
        0.015,
        i % 4 === 0 ? 0.35 : 0.15,
      );
      mark.rotation.y = a;
    }
    for (let i = 0; i < 34; i++) {
      const a = i * 2.399,
        r = 12.7 + (i % 3) * 0.4;
      const rubble = sphere(
        this.arena,
        stone,
        Math.sin(a) * r,
        0.12,
        Math.cos(a) * r,
        0.15 + (i % 3) * 0.1,
        0.12,
        0.25,
      );
      rubble.rotation.y = a;
    }
    const waterMat = new T.MeshStandardMaterial({
      color: 0x5c7f7a,
      metalness: 0.9,
      roughness: 0.15,
      transparent: true,
      opacity: 0.24,
      depthWrite: false,
    });
    for (let i = 0; i < 12; i++) {
      const a = i * 2.4,
        r = 3 + (i % 4) * 2;
      const pool = mesh(
        new T.CircleGeometry(0.7 + (i % 3) * 0.25, 18),
        waterMat,
        this.arena,
        [Math.sin(a) * r, 0.11, Math.cos(a) * r],
        [1, 0.5, 1],
      );
      pool.rotation.x = -Math.PI / 2;
      pool.rotation.z = a;
    }
    for (let i = 0; i < 12; i++) {
      const a = (i / 12) * Math.PI * 2;
      const rune = box(
        this.arena,
        gold,
        Math.sin(a) * 5.4,
        0.14,
        Math.cos(a) * 5.4,
        0.13,
        0.015,
        0.7,
      );
      rune.rotation.y = a + 0.4;
    }
    // Silhouette architecture is kept outside the playable disc.
    for (let i = 0; i < 12; i++) {
      const a = (i / 12) * Math.PI * 2,
        x = Math.sin(a) * 14,
        z = Math.cos(a) * 14;
      const pillar = new T.Group();
      pillar.position.set(x, 0, z);
      pillar.rotation.y = a;
      this.arena.add(pillar);
      const h = z > 6 ? 2.3 : 6.5;
      box(pillar, stone, 0, 0.18, 0, 1.5, 0.36, 1.5);
      cylinder(pillar, stone, 0, h / 2, 0, 0.48, h);
      cylinder(pillar, gold, 0, h - 0.2, 0, 0.53, 0.13);
      box(pillar, stone, 0, h, 0, 1.2, 0.25, 1.2);
      if (z < 6) {
        mesh(new T.ConeGeometry(0.75, 1.2, 4), dark, pillar, [0, h + 0.7, 0]);
        const banner = box(
          pillar,
          index === 1 ? ivory : red,
          0.62,
          h - 1.6,
          0.15,
          0.85,
          2.6,
          0.045,
        );
        banner.rotation.z = -0.1;
        box(pillar, gold, 0.62, h - 1.6, 0.18, 0.035, 2, 0.02);
      }
      const lantern = new T.Group();
      lantern.position.set(x * 0.87, 0.15, z * 0.87);
      this.arena.add(lantern);
      cylinder(lantern, dark, 0, 0.32, 0, 0.38, 0.6);
      sphere(lantern, glow, 0, 0.7, 0, 0.18, 0.32, 0.18);
      for (let j = 0; j < 3; j++) {
        const cx = x * 0.8 + Math.cos(a) * j * 0.22,
          cz = z * 0.8 - Math.sin(a) * j * 0.22;
        cylinder(this.arena, ivory, cx, 0.25, cz, 0.07, 0.4 + j * 0.09);
        sphere(this.arena, glow, cx, 0.5 + j * 0.09, cz, 0.035, 0.09, 0.035);
      }
    }
    // Rear sanctum arch and its hanging bell.
    const arch = new T.Group();
    arch.position.set(0, 0, -16.5);
    this.arena.add(arch);
    box(arch, stone, -4, 4.2, 0, 1.3, 8.4, 1.4);
    box(arch, stone, 4, 4.2, 0, 1.3, 8.4, 1.4);
    const top = mesh(
      new T.TorusGeometry(4, 0.65, 6, 32, Math.PI),
      stone,
      arch,
      [0, 8.2, 0],
    );
    top.rotation.z = 0;
    for (let i = -1; i <= 1; i += 2) {
      mesh(new T.ConeGeometry(1.1, 2, 4), dark, arch, [i * 4, 9.3, 0]);
    }
    cylinder(arch, gold, 0, 8.6, 0, 0.07, 4);
    mesh(
      new T.CylinderGeometry(0.65, 1.35, 1.7, 16, 1, true),
      gold,
      arch,
      [0, 6.2, 0],
    );
    sphere(arch, glow, 0, 5.8, 0, 0.16, 0.25, 0.16);
    // Broken silhouettes at the edge of the water.
    for (let i = 0; i < 22; i++) {
      const a = i * 2.399,
        r = 21 + (i % 4) * 3;
      const x = Math.sin(a) * r,
        z = Math.cos(a) * r;
      const h = 4 + (i % 6);
      box(this.arena, dark, x, h / 2 - 0.5, z, 1.4, h, 1.7);
      mesh(new T.ConeGeometry(1.3, 2, 4), dark, this.arena, [x, h + 0.5, z]);
    }
    if (index === 1) {
      for (const side of [-1, 1])
        for (let i = 0; i < 4; i++) {
          const x = side * (12 + i * 0.7),
            z = -10 + i * 5;
          const trunk = new T.Group();
          trunk.position.set(x, 0, z);
          this.arena.add(trunk);
          const b = cylinder(trunk, dark, 0, 2.2, 0, 0.14, 4.5);
          b.rotation.z = side * 0.25;
          for (let j = 0; j < 5; j++) {
            const branch = cylinder(
              trunk,
              ivory,
              side * (j * 0.3),
              2.5 + j * 0.35,
              0,
              0.045,
              2.5,
            );
            branch.rotation.z = side * (0.8 + j * 0.1);
          }
          sphere(trunk, mat(0x688c85), 0, 4.8, 0, 1.3, 0.35, 0.8);
        }
    }
    if (index === 2) {
      for (let i = 0; i < 7; i++) {
        const a = (i / 7) * Math.PI * 2;
        const g = new T.Group();
        g.position.set(Math.sin(a) * 14, 4, Math.cos(a) * 14);
        this.arena.add(g);
        mesh(new T.TorusGeometry(0.9, 0.025, 6, 48), glow, g);
      }
    }
  }
  aim(clientX: number, clientY: number): Vec | undefined {
    this.ray.setFromCamera(
      new T.Vector2(
        (clientX / innerWidth) * 2 - 1,
        (-clientY / innerHeight) * 2 + 1,
      ),
      this.camera,
    );
    const v = new T.Vector3();
    return this.ray.ray.intersectPlane(this.plane, v)
      ? { x: v.x, z: v.z }
      : undefined;
  }
  burst(event: GameEvent) {
    const color =
      event.kind === "heal"
        ? 0x8cebd2
        : event.kind === "hurt"
          ? 0xc94d47
          : event.kind === "parry"
            ? 0xffecba
            : 0xffc87c;
    if (event.kind === "swing" || event.kind === "slam") {
      const from = event.kind === "swing" ? this.player.root : this.boss.root;
      const radius =
        event.kind === "swing" ? (event.value === 2 ? 3.2 : 2.6) : 4;
      const arc = event.kind === "swing" ? 2.2 : 2.7;
      const g = new T.RingGeometry(
        radius - 0.45,
        radius,
        40,
        1,
        -Math.PI / 2 - arc / 2,
        arc,
      );
      const m = new T.Mesh(
        g,
        new T.MeshBasicMaterial({
          color: event.kind === "swing" ? 0xc6ece0 : 0xefba76,
          transparent: true,
          opacity: 0.65,
          side: T.DoubleSide,
          depthWrite: false,
        }),
      );
      m.rotation.set(-Math.PI / 2, 0, -from.rotation.y);
      m.position.set(event.x, 0.9, event.z);
      this.scene.add(m);
      this.trails.push({ mesh: m, life: 0.22, max: 0.22 });
      return;
    }
    const count =
      event.kind === "phase" || event.kind === "win"
        ? 65
        : event.kind === "dodge"
          ? 6
          : 18;
    for (let i = 0; i < count; i++) {
      const m = new T.Mesh(
        geo.sphere,
        new T.MeshBasicMaterial({ color, transparent: true }),
      );
      m.position.set(event.x, 0.9 + Math.random(), event.z);
      m.scale.setScalar(0.025 + Math.random() * 0.055);
      this.scene.add(m);
      const a = Math.random() * Math.PI * 2;
      const v = new T.Vector3(
        Math.sin(a) * (2 + Math.random() * 4),
        2 + Math.random() * 4,
        Math.cos(a) * (2 + Math.random() * 4),
      );
      this.particles.push({
        mesh: m,
        velocity: v,
        life: 0.4 + Math.random() * 0.6,
        max: 1,
      });
    }
    if (!this.reducedMotion)
      this.shake = Math.max(
        this.shake,
        event.kind === "hurt"
          ? 0.2
          : event.kind === "phase"
            ? 0.28
            : event.kind === "parry"
              ? 0.15
              : 0.08,
      );
  }
  animateRig(
    rig: Rig,
    x: number,
    z: number,
    facing: number,
    moving: boolean,
    time: number,
    action: string,
    progress: number,
  ) {
    rig.root.position.set(x, 0, z);
    rig.root.rotation.y += angleDiff(facing, rig.root.rotation.y) * 0.4;
    const gait = moving ? Math.sin(time * 12) * 0.5 : 0;
    rig.legL.rotation.x = gait;
    rig.legR.rotation.x = -gait;
    rig.left.rotation.x = -gait * 0.5;
    rig.right.rotation.x = gait * 0.5;
    rig.right.rotation.z = -0.15;
    rig.body.position.y = moving
      ? Math.abs(Math.sin(time * 12)) * 0.04
      : Math.sin(time * 2) * 0.025;
    rig.body.rotation.set(0, 0, 0);
    rig.root.rotation.z = 0;
    rig.cape.rotation.x = 0.2 + Math.sin(time * 3) * 0.07 + (moving ? 0.22 : 0);
    rig.wings.forEach(
      (w, i) =>
        (w.rotation.z = (i === 0 ? -1 : 1) * (0.1 + Math.sin(time * 3) * 0.14)),
    );
    if (action === "light" || action === "heavy" || action === "active") {
      const s = Math.sin(Math.min(1, progress) * Math.PI);
      rig.body.rotation.y = -0.6 + s * 1.4;
      rig.right.rotation.x = -1.3;
      rig.right.rotation.z = -1.2 + s * 2.6;
      rig.left.rotation.x = -0.4;
    } else if (action === "dodge") {
      rig.body.rotation.x = progress < 0.7 ? -0.8 : 0;
      rig.body.position.y = -0.2;
      rig.cape.rotation.x = 0.8;
    } else if (action === "parry") {
      rig.right.rotation.x = -1.7;
      rig.right.rotation.z = -0.7;
    } else if (action === "heal") {
      rig.left.rotation.x = -2.1;
    } else if (action === "windup") {
      rig.right.rotation.x = -2.4 * progress;
      rig.body.rotation.y = -progress * 0.7;
    } else if (action === "stagger") {
      rig.body.rotation.x = 0.6;
      rig.body.position.y = -0.4;
    } else if (action === "dead") {
      rig.root.rotation.z = -Math.PI / 2;
      rig.root.position.y = 0.4;
    }
  }
  update(game: Combat, dt: number, locked: boolean) {
    this.setArena(game.bossIndex);
    this.time += dt;
    const p = game.player,
      b = game.boss;
    this.animateRig(
      this.player,
      p.x,
      p.z,
      p.facing,
      p.action === "idle" && this.moving,
      this.time,
      game.mode === "dead" ? "dead" : p.action,
      p.timer / p.duration,
    );
    this.animateRig(
      this.boss,
      b.x,
      b.z,
      b.facing,
      b.state === "approach" && game.mode === "combat",
      this.time,
      game.mode === "won" ? "dead" : b.state,
      b.timer / b.duration,
    );
    this.player.root.visible = !(
      p.invuln > 0 && Math.sin(this.time * 45) > 0.7
    );
    const center = new T.Vector3((p.x + b.x) * 0.18, 0, (p.z + b.z) * 0.16);
    const camDist = innerWidth / innerHeight < 1.2 ? 35 : 29;
    const target = new T.Vector3(
      center.x,
      camDist * 0.68,
      center.z + camDist * 0.8,
    );
    this.camera.position.lerp(target, 1 - Math.exp(-dt * 3));
    if (this.camera.position.length() < 1) this.camera.position.copy(target);
    this.shake = Math.max(0, this.shake - dt * 0.8);
    if (this.shake && !this.reducedMotion) {
      this.camera.position.x += (Math.random() - 0.5) * this.shake;
      this.camera.position.y += (Math.random() - 0.5) * this.shake;
    }
    this.camera.lookAt(center.x, 0.4, center.z - 1.2);
    this.lock.visible = locked && game.mode === "combat";
    this.lock.position.set(b.x, game.bossIndex === 0 ? 4.7 : 4.1, b.z);
    this.lock.lookAt(this.camera.position);
    this.drawTelegraph(game);
    this.drawHazards(game);
    for (let i = this.particles.length - 1; i >= 0; i--) {
      const e = this.particles[i];
      e.life -= dt;
      e.velocity.y -= dt * 8;
      e.mesh.position.addScaledVector(e.velocity, dt);
      (e.mesh.material as T.MeshBasicMaterial).opacity = Math.max(
        0,
        e.life / e.max,
      );
      if (e.life <= 0) {
        this.scene.remove(e.mesh);
        (e.mesh.material as T.Material).dispose();
        this.particles.splice(i, 1);
      }
    }
    for (let i = this.trails.length - 1; i >= 0; i--) {
      const t = this.trails[i];
      t.life -= dt;
      (t.mesh.material as T.MeshBasicMaterial).opacity =
        Math.max(0, t.life / t.max) * 0.65;
      t.mesh.scale.multiplyScalar(1 + dt * 0.8);
      if (t.life <= 0) {
        this.scene.remove(t.mesh);
        t.mesh.geometry.dispose();
        (t.mesh.material as T.Material).dispose();
        this.trails.splice(i, 1);
      }
    }
    this.ash.rotation.y = this.time * 0.015;
    this.ash.position.y = (-this.time * 0.08) % 10;
    this.water.position.y = -0.4 + Math.sin(this.time * 0.8) * 0.025;
    if (this.quality === "low") this.renderer.render(this.scene, this.camera);
    else this.composer.render();
  }
  moving = false;
  telegraphKey = "";
  drawTelegraph(game: Combat) {
    const b = game.boss,
      a = game.attack,
      show =
        (b.state === "windup" || b.state === "active") &&
        game.mode === "combat";
    this.telegraph.visible = show;
    if (!show) return;
    const key = `${game.bossIndex}-${b.attack}`;
    if (key !== this.telegraphKey) {
      this.clear(this.telegraph);
      this.telegraphKey = key;
      const m = new T.MeshBasicMaterial({
        color: a.parryable ? 0xe8ba73 : 0xe66662,
        transparent: true,
        opacity: 0.2,
        side: T.DoubleSide,
        depthWrite: false,
      });
      if (a.shape === "sector") {
        const s = mesh(
          new T.CircleGeometry(a.range, 48, -a.arc / 2 - Math.PI / 2, a.arc),
          m,
          this.telegraph,
        );
        s.rotation.x = -Math.PI / 2;
      } else if (a.shape === "dash") {
        box(this.telegraph, m, 0, 0, a.range / 2, 1.5, 0.01, a.range);
      } else {
        const r = a.shape === "circle" ? a.range : 2.2;
        const s = mesh(new T.RingGeometry(r - 0.12, r, 64), m, this.telegraph);
        s.rotation.x = -Math.PI / 2;
        const inner = mesh(
          new T.CircleGeometry(r, 48),
          m.clone(),
          this.telegraph,
        );
        inner.rotation.x = -Math.PI / 2;
        (inner.material as T.MeshBasicMaterial).opacity = 0.07;
      }
    }
    this.telegraph.position.set(b.x, 0.18, b.z);
    this.telegraph.rotation.y = b.facing;
    this.telegraph.traverse((o) => {
      if (o instanceof T.Mesh)
        (o.material as T.MeshBasicMaterial).opacity =
          b.state === "active" ? 0.5 : 0.1 + 0.22 * (b.timer / b.duration);
    });
  }
  drawHazards(game: Combat) {
    const ids = new Set(game.hazards.map((h) => h.id));
    for (const [id, g] of this.hazards)
      if (!ids.has(id)) {
        this.scene.remove(g);
        this.clear(g);
        this.hazards.delete(id);
      }
    for (const h of game.hazards) {
      let g = this.hazards.get(h.id);
      if (!g) {
        g = new T.Group();
        this.scene.add(g);
        this.hazards.set(h.id, g);
        const m = new T.MeshBasicMaterial({
          color: h.type === "feather" ? 0x9aeee3 : 0xec7655,
          transparent: true,
          opacity: 0.75,
          side: T.DoubleSide,
          depthWrite: false,
        });
        if (h.type === "feather") {
          const f = mesh(new T.ConeGeometry(0.12, 1, 4), m, g);
          f.rotation.x = Math.PI / 2;
        } else {
          const r = mesh(new T.RingGeometry(0.94, 1, 80), m, g);
          r.rotation.x = -Math.PI / 2;
          if (h.type === "eruption") {
            const pillar = mesh(
              new T.ConeGeometry(1, 1, 12),
              m.clone(),
              g,
              [0, 0, 0],
            );
            pillar.name = "pillar";
          }
        }
      }
      g.position.set(h.x, h.type === "feather" ? 1 : 0.2, h.z);
      g.visible = h.type !== "ring" || h.age >= h.delay;
      if (h.type === "feather") g.rotation.y = Math.atan2(h.vx, h.vz);
      else {
        g.scale.set(h.radius, 1, h.radius);
        if (h.type === "eruption") {
          const m = g.getObjectByName("pillar")!;
          m.visible = h.age >= h.delay;
          m.scale.y = 3;
          m.position.y = 1.5;
        }
      }
    }
  }
}
