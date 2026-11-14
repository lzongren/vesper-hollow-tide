import * as T from "three";
function isMesh(o: T.Object3D): o is T.Mesh {
  return (o as T.Mesh).isMesh === true;
}
function isBone(o: T.Object3D): o is T.Bone {
  return (o as T.Bone).isBone === true;
}
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { SSAOPass } from "three/addons/postprocessing/SSAOPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";
import { Combat, angleDiff, type GameEvent, type Vec } from "./combat";
import { ArtLibrary } from "./assets";

const Y = new T.Vector3(0, 1, 0);
const standard = (color: number, metalness = 0, roughness = 0.6) =>
  new T.MeshStandardMaterial({ color, metalness, roughness });
const emissive = (color: number, strength = 2) =>
  new T.MeshStandardMaterial({
    color,
    emissive: color,
    emissiveIntensity: strength,
  });
const random = (seed: number) => {
  let s = seed;
  return () => {
    s = (s * 1664525 + 1013904223) >>> 0;
    return s / 4294967296;
  };
};
function mesh(
  parent: T.Object3D,
  g: T.BufferGeometry,
  m: T.Material,
  x = 0,
  y = 0,
  z = 0,
) {
  const o = new T.Mesh(g, m);
  o.position.set(x, y, z);
  o.castShadow = o.receiveShadow = true;
  parent.add(o);
  return o;
}
function box(
  parent: T.Object3D,
  m: T.Material,
  x: number,
  y: number,
  z: number,
  w: number,
  h: number,
  d: number,
) {
  return mesh(parent, new T.BoxGeometry(w, h, d), m, x, y, z);
}
function cylinder(
  parent: T.Object3D,
  m: T.Material,
  x: number,
  y: number,
  z: number,
  r: number,
  h: number,
  rt = r,
) {
  return mesh(parent, new T.CylinderGeometry(rt, r, h, 24), m, x, y, z);
}
function torus(
  parent: T.Object3D,
  m: T.Material,
  r: number,
  tube: number,
  x = 0,
  y = 0,
  z = 0,
  horizontal = false,
) {
  const o = mesh(parent, new T.TorusGeometry(r, tube, 8, 80), m, x, y, z);
  if (horizontal) o.rotation.x = Math.PI / 2;
  return o;
}
function tube(
  parent: T.Object3D,
  m: T.Material,
  points: T.Vector3[],
  r = 0.04,
) {
  return mesh(
    parent,
    new T.TubeGeometry(new T.CatmullRomCurve3(points), 32, r, 7, false),
    m,
  );
}
function textureCanvas(
  draw: (c: CanvasRenderingContext2D) => void,
  size = 512,
) {
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = size;
  draw(canvas.getContext("2d")!);
  const t = new T.CanvasTexture(canvas);
  t.colorSpace = T.SRGBColorSpace;
  return t;
}
function fabricTexture() {
  return textureCanvas((c) => {
    c.fillStyle = "#7e3030";
    c.fillRect(0, 0, 512, 512);
    for (let i = 0; i < 512; i += 3) {
      c.strokeStyle = i % 2 ? "#a74a4544" : "#34171944";
      c.beginPath();
      c.moveTo(i, 0);
      c.lineTo(i, 512);
      c.stroke();
    }
    c.strokeStyle = "#d8ae6855";
    c.lineWidth = 1.5;
    for (let y = 0; y < 512; y += 64)
      for (let x = 0; x < 512; x += 64) {
        c.beginPath();
        c.ellipse(x + 32, y + 32, 20, 28, Math.PI / 4, 0, Math.PI * 2);
        c.stroke();
        c.beginPath();
        c.arc(x + 32, y + 32, 9, 0, Math.PI * 2);
        c.stroke();
      }
    c.fillStyle = "#d4b075";
    c.fillRect(6, 0, 3, 512);
    c.fillRect(503, 0, 3, 512);
  });
}
function cloth(
  parent: T.Object3D,
  m: T.Material,
  width: number,
  height: number,
  x = 0,
  y = 0,
  z = 0,
) {
  const g = new T.PlaneGeometry(width, height, 24, 30);
  const pos = g.attributes.position;
  for (let i = 0; i < pos.count; i++) {
    const px = pos.getX(i),
      py = pos.getY(i);
    pos.setZ(i, Math.sin(px * 15) * 0.045 + Math.sin(py * 4 + px * 4) * 0.035);
  }
  g.computeVertexNormals();
  const o = mesh(parent, g, m, x, y, z);
  o.userData.base = new Float32Array(pos.array);
  return o;
}
interface Actor {
  root: T.Group;
  model: T.Group;
  bones: Map<string, T.Bone>;
  rest: Map<string, T.Quaternion>;
  robe?: T.Mesh;
  weapon: T.Group;
  kind: number;
  height: number;
  rightHand?: T.Bone;
  halo?: T.Group;
}
interface Effect {
  mesh: T.Mesh;
  velocity: T.Vector3;
  life: number;
  max: number;
  spin: number;
}

export class World {
  readonly ready: Promise<void>;
  art = new ArtLibrary();
  renderer: T.WebGLRenderer;
  scene = new T.Scene();
  camera = new T.PerspectiveCamera(54, 1, 0.1, 200);
  composer: EffectComposer;
  ao: SSAOPass;
  arena = new T.Group();
  decor = new T.Group();
  player: Actor = { root: new T.Group() } as Actor;
  boss: Actor = { root: new T.Group() } as Actor;
  bossIndex = -1;
  telegraphKey = "";
  telegraph = new T.Group();
  hazards = new Map<number, T.Group>();
  lock = new T.Group();
  particles: Effect[] = [];
  trails: Effect[] = [];
  quality = "high";
  reducedMotion = false;
  moving = false;
  time = 0;
  shake = 0;
  ray = new T.Raycaster();
  plane = new T.Plane(Y, 0);
  yaw = 0;
  orbit = 0;
  cameraInitialized = false;
  loaded = false;
  moon: T.DirectionalLight;
  fill: T.PointLight;
  clothMeshes: T.Mesh[] = [];
  flames: T.Mesh[] = [];
  rain: T.Points;
  rainBase: Float32Array;
  fogSheets: T.Mesh[] = [];
  materials: Record<string, T.MeshStandardMaterial> = {};
  constructor(readonly canvas: HTMLCanvasElement) {
    this.renderer = new T.WebGLRenderer({
      canvas,
      antialias: true,
      powerPreference: "high-performance",
    });
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = T.PCFSoftShadowMap;
    this.renderer.toneMapping = T.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.1;
    this.scene.background = new T.Color(0x111d22);
    this.scene.fog = new T.FogExp2(0x19272b, 0.022);
    this.scene.add(new T.HemisphereLight(0xb7d0da, 0x465146, 1.5));
    this.moon = new T.DirectionalLight(0xcbddea, 3.2);
    this.moon.position.set(-12, 20, -15);
    this.moon.castShadow = true;
    this.moon.shadow.mapSize.set(2048, 2048);
    Object.assign(this.moon.shadow.camera, {
      left: -24,
      right: 24,
      top: 24,
      bottom: -24,
      near: 1,
      far: 70,
    });
    this.moon.shadow.normalBias = 0.035;
    this.moon.shadow.bias = -0.00012;
    this.scene.add(this.moon);
    this.fill = new T.PointLight(0xffb36d, 26, 18, 2);
    this.fill.position.set(2, 4, 4);
    this.scene.add(this.fill);
    const portraitLight = new T.DirectionalLight(0xffddb5, 1.5);
    portraitLight.position.set(8, 11, 15);
    this.scene.add(portraitLight);
    this.scene.add(this.arena, this.decor, this.telegraph, this.lock);
    const ring = mesh(
      this.lock,
      new T.TorusGeometry(0.075, 0.008, 6, 24),
      new T.MeshBasicMaterial({ color: 0xffefc5 }),
    );
    ring.rotation.z = Math.PI / 4;
    this.rainBase = new Float32Array(600 * 3);
    const rand = random(53);
    for (let i = 0; i < 600; i++) {
      this.rainBase[i * 3] = (rand() - 0.5) * 80;
      this.rainBase[i * 3 + 1] = rand() * 25;
      this.rainBase[i * 3 + 2] = (rand() - 0.5) * 80;
    }
    const rg = new T.BufferGeometry();
    rg.setAttribute(
      "position",
      new T.BufferAttribute(this.rainBase.slice(), 3),
    );
    this.rain = new T.Points(
      rg,
      new T.PointsMaterial({
        color: 0xd4e8e2,
        size: 0.025,
        opacity: 0.45,
        transparent: true,
        depthWrite: false,
      }),
    );
    this.scene.add(this.rain);
    this.composer = new EffectComposer(this.renderer);
    this.composer.addPass(new RenderPass(this.scene, this.camera));
    this.ao = new SSAOPass(this.scene, this.camera, innerWidth, innerHeight);
    this.ao.kernelRadius = 0.7;
    this.ao.minDistance = 0.005;
    this.ao.maxDistance = 0.2;
    this.composer.addPass(this.ao);
    this.composer.addPass(
      new UnrealBloomPass(
        new T.Vector2(innerWidth, innerHeight),
        0.28,
        0.55,
        1.25,
      ),
    );
    this.composer.addPass(new OutputPass());
    this.ready = this.art.load().then(() => {
      this.scene.environment = this.art.environment!;
      this.scene.environmentIntensity = 1.1;
      this.createMaterials();
      this.player = this.actor(-1);
      this.scene.add(this.player.root);
      this.loaded = true;
      this.setArena(0);
    });
    this.resize();
  }
  createMaterials() {
    this.materials = {
      stone: this.art.material("stone", 16),
      wall: this.art.material("wall", 2),
      rock: this.art.material("rock", 2, 2, 0x7f9189),
      wood: this.art.material("wood", 2, 2, 0xb06c55),
      gold: this.art.material("metal", 2, 2, 0xc8af71),
      roof: this.art.material("rock", 3, 2, 0x586062),
      dark: standard(0x171c1b, 0.4, 0.35),
      ivory: standard(0xd1c9ad, 0.2, 0.35),
      fire: emissive(0xffb553, 3),
      cloth: new T.MeshStandardMaterial({
        color: 0xffffff,
        map: fabricTexture(),
        side: T.DoubleSide,
        roughness: 0.9,
      }),
      moss: standard(0x44523a, 0, 0.95),
    };
  }
  resize() {
    this.camera.aspect = innerWidth / innerHeight;
    this.camera.fov = this.camera.aspect < 1 ? 70 : 54;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(innerWidth, innerHeight);
    this.composer.setSize(innerWidth, innerHeight);
  }
  setQuality(value: string) {
    this.quality = value;
    this.renderer.setPixelRatio(
      value === "low" ? 1 : Math.min(devicePixelRatio, 1.5),
    );
    this.renderer.shadowMap.enabled = value !== "low";
    this.resize();
  }
  clear(group: T.Group) {
    const shared = new Set<T.Material>(Object.values(this.materials));
    const geometries = new Set<T.BufferGeometry>(),
      materials = new Set<T.Material>(),
      textures = new Set<T.Texture>();
    group.traverse((o) => {
      if (isMesh(o)) {
        if (!o.userData.sharedGeometry) geometries.add(o.geometry);
        for (const m of Array.isArray(o.material) ? o.material : [o.material])
          if (!shared.has(m)) materials.add(m);
        if (o.userData.disposeMap)
          textures.add((o.material as T.MeshBasicMaterial).map!);
      }
    });
    geometries.forEach((g) => g.dispose());
    materials.forEach((m) => m.dispose());
    textures.forEach((t) => t.dispose());
    group.clear();
  }
  actor(kind: number): Actor {
    const height = kind < 0 ? 1.9 : kind === 0 ? 3.9 : kind === 1 ? 3.2 : 3.7;
    const model = this.art.model(
      kind < 1 ? "pilgrim" : kind === 1 ? "wraith" : "sorcerer",
      height,
    );
    const root = new T.Group();
    root.add(model);
    const bones = new Map<string, T.Bone>(),
      rest = new Map<string, T.Quaternion>();
    model.traverse((o) => {
      if (isBone(o)) {
        bones.set(o.name, o);
        rest.set(o.name, o.quaternion.clone());
      }
      if (isMesh(o)) {
        const list = Array.isArray(o.material) ? o.material : [o.material];
        for (const m of list) {
          const mm = m as T.MeshStandardMaterial;
          mm.roughness = kind < 1 ? 0.48 : 0.72;
          if (kind === 1) mm.metalness = 0.1;
          mm.envMapIntensity = kind < 1 ? 1.1 : 0.4;
          if (kind === 0) mm.color.setHex(0x9a8873);
          if (kind === 1) mm.color.setHex(0x8dc9c2);
          if (kind === 2) mm.color.setHex(0x9b7c68);
          if (kind > 0) {
            if (kind === 1) {
              mm.emissive.setHex(0x4c716c);
              mm.emissiveIntensity = 0.25;
            }
            mm.onBeforeCompile = (shader) => {
              shader.fragmentShader = shader.fragmentShader.replace(
                "#include <map_fragment>",
                `#include <map_fragment>\n float lum=dot(diffuseColor.rgb, vec3(.299,.587,.114)); diffuseColor.rgb=${kind === 1 ? 'vec3(.18,.23,.22)+vec3(lum)*.9' : 'mix(vec3(lum),diffuseColor.rgb,.3)'};`,
              );
            };
          }
        }
      }
    });
    const weapon = new T.Group();
    root.add(weapon);
    const a: Actor = {
      root,
      model,
      bones,
      rest,
      weapon,
      kind,
      height,
      rightHand: bones.get("RightHand"),
    };
    if (kind < 1) {
      const robe = cloth(
        root,
        this.materials.cloth.clone(),
        kind < 0 ? 0.9 : 1.7,
        kind < 0 ? 1.15 : 2.8,
        0,
        kind < 0 ? 1.18 : 1.7,
        -0.24,
      );
      a.robe = robe;
      const pos = robe.geometry.attributes.position;
      const capeHeight = kind < 0 ? 1.15 : 2.8;
      for (let i = 0; i < pos.count; i++) {
        const w = pos.getY(i) / capeHeight + 0.5;
        pos.setX(i, pos.getX(i) * (1 - 0.38 * w));
        pos.setZ(i, pos.getZ(i) - (1 - w) * 0.18);
        pos.setY(i, pos.getY(i) + Math.cos(pos.getX(i) * 15) * 0.025 * (1 - w));
      }
      robe.userData.base = new Float32Array(pos.array);
      robe.geometry.computeVertexNormals();
      if (kind < 0) {
        // Woven travel hat and layered lacquered mantle give the pilgrim an original silhouette.
        const hat = mesh(
          root,
          new T.ConeGeometry(0.43, 0.19, 64),
          this.materials.wood,
          0,
          1.97,
          0,
        );
        hat.rotation.x = 0.05;
        for (let j = 0; j < 9; j++)
          torus(
            root,
            this.materials.wood,
            0.12 + j * 0.035,
            0.004,
            0,
            2.045 - j * 0.014,
            0,
            true,
          );
        const sword = this.art.model("sword", 1.65);
        sword.position.y = -0.32;
        weapon.add(sword);
        weapon.rotation.x = -0.9;
      } else {
        for (let i = 0; i < 12; i++) {
          const ang = (i / 12) * Math.PI * 2;
          const petal = mesh(
            root,
            new T.ConeGeometry(0.075, 0.8, 12),
            this.materials.gold,
            Math.sin(ang) * 0.4,
            3.98,
            Math.cos(ang) * 0.4,
          );
          petal.rotation.z = -Math.sin(ang) * 0.25;
          petal.rotation.x = Math.cos(ang) * 0.25;
        }
        cylinder(weapon, this.materials.wood, 0, 0.65, 0, 0.07, 2.8);
        this.bell(weapon, 0.64, 0, 1.4, 0);
        const mantle = mesh(
          root,
          new T.SphereGeometry(1, 32, 20, 0, Math.PI * 2, 0, 1.2),
          this.materials.gold,
          0,
          3.05,
          0,
        );
        mantle.scale.set(0.76, 0.32, 0.55);
      }
    }
    if (kind === 1) {
      a.robe = cloth(
        root,
        new T.MeshStandardMaterial({
          color: 0xc4c3b3,
          side: T.DoubleSide,
          transparent: true,
          opacity: 0.72,
          roughness: 0.95,
        }),
        1.5,
        2.2,
        0,
        1.6,
        -0.3,
      );
    }
    if (kind === 2) {
      const halo = new T.Group();
      halo.position.set(0, 3.55, -0.25);
      root.add(halo);
      torus(halo, this.materials.gold, 0.72, 0.025);
      for (let i = 0; i < 12; i++) {
        const ang = (i / 12) * Math.PI * 2;
        mesh(
          halo,
          new T.SphereGeometry(0.035, 12, 8),
          this.materials.fire,
          Math.sin(ang) * 0.72,
          Math.cos(ang) * 0.72,
          0,
        );
      }
      a.halo = halo;
      cylinder(weapon, this.materials.gold, 0, 1, 0, 0.045, 3);
      torus(weapon, this.materials.gold, 0.28, 0.035, 0, 2.4, 0);
    }
    return a;
  }
  bell(parent: T.Object3D, r: number, x: number, y: number, z: number) {
    const casting = this.art.model("tide-bell", 2.03 * r);
    casting.position.set(x, y - 0.15 * r, z);
    parent.add(casting);
    return casting;
  }
  lantern(parent: T.Object3D, x: number, y: number, z: number, red = false) {
    const g = new T.Group();
    g.position.set(x, y, z);
    parent.add(g);
    const mat = new T.MeshStandardMaterial({
      color: red ? 0x9a2821 : 0xc7a167,
      emissive: red ? 0x9b2014 : 0xff982f,
      emissiveIntensity: 1.8,
      roughness: 0.9,
      side: T.DoubleSide,
    });
    mesh(g, new T.SphereGeometry(0.33, 24, 18), mat, 0, 0.6, 0).scale.y = 1.3;
    cylinder(g, this.materials.dark, 0, 0.22, 0, 0.22, 0.07);
    cylinder(g, this.materials.gold, 0, 0.99, 0, 0.22, 0.06);
    for (let i = 0; i < 10; i++) {
      const angle = (i / 10) * Math.PI * 2;
      tube(
        g,
        this.materials.dark,
        [
          new T.Vector3(Math.sin(angle) * 0.17, 0.2, Math.cos(angle) * 0.17),
          new T.Vector3(Math.sin(angle) * 0.335, 0.6, Math.cos(angle) * 0.335),
          new T.Vector3(Math.sin(angle) * 0.17, 1, Math.cos(angle) * 0.17),
        ],
        0.008,
      );
    }
    const flame = mesh(
      g,
      new T.SphereGeometry(0.06, 12, 8),
      this.materials.fire,
      0,
      0.6,
      0,
    );
    flame.scale.y = 2;
    this.flames.push(flame);
    return g;
  }
  roof(parent: T.Object3D, width: number, depth: number, y: number) {
    const g = new T.BufferGeometry(),
      v: number[] = [],
      uv: number[] = [],
      idx: number[] = [];
    const nx = 32,
      nz = 14;
    for (let iz = 0; iz <= nz; iz++)
      for (let ix = 0; ix <= nx; ix++) {
        const x = (ix / nx - 0.5) * width,
          z = (iz / nz - 0.5) * depth;
        const yy =
          y +
          1.8 * (1 - Math.abs(z / (depth / 2))) +
          Math.pow(Math.abs(x / (width / 2)), 7) * 0.65 +
          Math.pow(Math.abs(z / (depth / 2)), 8) * 0.45;
        v.push(x, yy, z);
        uv.push((ix / nx) * 3, (iz / nz) * 2);
      }
    for (let iz = 0; iz < nz; iz++)
      for (let ix = 0; ix < nx; ix++) {
        const a = iz * (nx + 1) + ix;
        idx.push(a, a + nx + 1, a + 1, a + 1, a + nx + 1, a + nx + 2);
      }
    g.setAttribute("position", new T.Float32BufferAttribute(v, 3));
    g.setAttribute("uv", new T.Float32BufferAttribute(uv, 2));
    g.setIndex(idx);
    g.computeVertexNormals();
    const roofMat = this.materials.roof.clone();
    roofMat.side = T.DoubleSide;
    mesh(parent, g, roofMat);
    const ridges: T.BufferGeometry[] = [];
    for (let ix = 0; ix <= 40; ix++) {
      const x = (ix / 40 - 0.5) * width;
      for (const side of [-1, 1]) {
        const pts = [];
        for (let j = 0; j <= 12; j++) {
          const z = (((side * j) / 12) * depth) / 2;
          const yy =
            y +
            1.8 * (1 - Math.abs(z / (depth / 2))) +
            Math.pow(Math.abs(x / (width / 2)), 7) * 0.65 +
            Math.pow(Math.abs(z / (depth / 2)), 8) * 0.45 +
            0.04;
          pts.push(new T.Vector3(x, yy, z));
        }
        ridges.push(
          new T.TubeGeometry(new T.CatmullRomCurve3(pts), 16, 0.025, 5, false),
        );
      }
    }
    mesh(parent, mergeGeometries(ridges), this.materials.roof);
    ridges.forEach((g) => g.dispose());
    tube(
      parent,
      this.materials.gold,
      [
        new T.Vector3(-width * 0.5, y + 2.45, 0),
        new T.Vector3(-width * 0.3, y + 1.8, 0),
        new T.Vector3(width * 0.3, y + 1.8, 0),
        new T.Vector3(width * 0.5, y + 2.45, 0),
      ],
      0.05,
    );
  }
  temple(parent: T.Object3D, x: number, z: number, scale = 1) {
    const g = new T.Group();
    g.position.set(x, 0, z);
    g.scale.setScalar(scale);
    parent.add(g);
    box(g, this.materials.wall, 0, 0.55, 0, 12, 1.1, 7);
    for (let i = 0; i < 5; i++)
      box(
        g,
        this.materials.wall,
        0,
        0.1 + i * 0.12,
        4.3 - i * 0.4,
        6,
        0.2,
        1.6,
      );
    for (const xx of [-5, -2.5, 2.5, 5])
      for (const zz of [-2.6, 2.6]) {
        cylinder(g, this.materials.wood, xx, 3.2, zz, 0.21, 4.8);
        cylinder(g, this.materials.gold, xx, 1.05, zz, 0.32, 0.25);
        for (let j = 0; j < 3; j++)
          box(
            g,
            this.materials.wood,
            xx,
            5.2 + j * 0.17,
            zz,
            0.9 + j * 0.2,
            0.13,
            0.55 + j * 0.2,
          );
      }
    box(g, this.materials.wood, 0, 4.9, 0, 11, 0.3, 6);
    box(g, this.materials.wall, 0, 2.8, -2.7, 10, 3.8, 0.4);
    for (const side of [-1, 1]) {
      for (let i = 0; i < 14; i++)
        box(
          g,
          this.materials.wood,
          side * 3.7,
          2.9,
          -2.44 + (i % 2) * 0.03,
          2.3,
          0.025,
          0.12,
        ).position.y = 1.4 + i * 0.2;
      for (let i = 0; i < 9; i++)
        box(
          g,
          this.materials.wood,
          side * 3.7 - 1.1 + i * 0.27,
          2.8,
          -2.43,
          0.035,
          3,
          0.1,
        );
    }
    this.roof(g, 14, 8, 5.5);
    // Raised clerestory, carved fascia and fretwork make the hall read at combat distance.
    box(g, this.materials.wood, 0, 7.2, 0, 7.8, 1.5, 3.6);
    this.roof(g, 10, 5.5, 7.7);
    for (const side of [-1, 1])
      for (let i = 0; i < 6; i++) {
        const xx = side * (1.4 + i * 0.65);
        box(g, this.materials.gold, xx, 5.08, 3.12, 0.08, 0.18, 0.07);
        const fret = torus(g, this.materials.gold, 0.15, 0.016, xx, 5.35, 3.15);
        fret.scale.y = 0.5;
      }
    for (const xx of [-5, -2.5, 2.5, 5]) {
      tube(
        g,
        this.materials.wood,
        [
          new T.Vector3(xx - 1, 4.85, 2.6),
          new T.Vector3(xx - 0.45, 4.6, 2.6),
          new T.Vector3(xx, 4.1, 2.6),
          new T.Vector3(xx + 0.45, 4.6, 2.6),
          new T.Vector3(xx + 1, 4.85, 2.6),
        ],
        0.075,
      );
    }
    this.bell(g, 1.1, 0, 2.7, 0);
    const sign = box(g, this.materials.dark, 0, 4.7, 3.05, 2.6, 0.65, 0.15);
    for (let i = 0; i < 3; i++)
      torus(sign, this.materials.gold, 0.14, 0.018, -0.7 + i * 0.7, 0, 0.1);
    for (const xx of [-4, -1.5, 1.5, 4]) {
      cylinder(g, this.materials.dark, xx, 4.4, 3, 0.015, 0.8);
      this.lantern(g, xx, 3.2, 3.05, true);
    }
  }
  setArena(index: number) {
    if (!this.loaded || this.bossIndex === index) return;
    this.bossIndex = index;
    this.clear(this.arena);
    this.clear(this.decor);
    this.clothMeshes = [];
    this.flames = [];
    this.fogSheets = [];
    this.scene.remove(this.boss.root);
    this.clear(this.boss.root);
    this.boss = this.actor(index);
    this.scene.add(this.boss.root);
    this.hazards.forEach((g) => {
      this.scene.remove(g);
      this.clear(g);
    });
    this.hazards.clear();
    this.telegraphKey = "";
    this.cameraInitialized = false;
    const colors = [0x23383b, 0x213737, 0x332a29];
    this.scene.fog = new T.FogExp2(colors[index], 0.023);
    this.scene.background = new T.Color(colors[index]);
    this.materials.stone.color.setHex([0xffffff, 0xbdd0bd, 0xaaa398][index]);
    const ground = mesh(
      this.arena,
      new T.PlaneGeometry(120, 120, 128, 128),
      this.materials.stone,
      0,
      -0.06,
      0,
    );
    ground.rotation.x = -Math.PI / 2;
    const ringMat = this.materials.gold.clone();
    ringMat.color.setHex(0x8e7f58);
    torus(this.arena, ringMat, 12.2, 0.025, 0, 0.04, 0, true);
    torus(this.arena, ringMat, 5.3, 0.018, 0, 0.04, 0, true);
    // Hand-laid raised perimeter, with a traversable central court and no chessboard tiling.
    for (let i = 0; i < 48; i++) {
      const a = (i / 48) * Math.PI * 2;
      const block = box(
        this.arena,
        this.materials.wall,
        Math.sin(a) * 13,
        -0.03,
        Math.cos(a) * 13,
        1.8,
        0.35,
        0.6,
      );
      block.rotation.y = a;
    }
    this.temple(this.arena, 0, -23, 1.5);
    for (const side of [-1, 1]) {
      const corridor = new T.Group();
      corridor.position.set(side * 18, 0, -1);
      corridor.rotation.y = Math.PI / 2;
      this.arena.add(corridor);
      for (let i = 0; i < 7; i++) {
        const x = -15 + i * 5;
        cylinder(corridor, this.materials.wood, x, 2.9, 0, 0.22, 5.8);
        box(corridor, this.materials.wood, x, 5.2, 0, 1.2, 0.22, 2);
        if (i % 2 === 0) this.lantern(corridor, x, 3.6, 1.5, true);
      }
      this.roof(corridor, 34, 4.5, 5.7);
      for (let i = 0; i < 5; i++) {
        const z = -13 + i * 6;
        const pillar = new T.Group();
        pillar.position.set(side * 13.8, 0, z);
        this.arena.add(pillar);
        box(pillar, this.materials.wall, 0, 0.3, 0, 1.3, 0.6, 1.3);
        cylinder(pillar, this.materials.wall, 0, 1.2, 0, 0.25, 1.3);
        this.lantern(pillar, 0, 1.7, 0);
        box(pillar, this.materials.roof, 0, 2.85, 0, 0.85, 0.12, 0.85);
      }
    }
    const rng = random(772 + index);
    const mountainMaterial = this.materials.rock.clone();
    mountainMaterial.color.setHex(0x3b5350);
    for (let i = 0; i < 18; i++) {
      const a = (i / 18) * Math.PI * 2,
        r = 65 + rng() * 20;
      const cliff = mesh(
        this.decor,
        new T.IcosahedronGeometry(1, 3),
        mountainMaterial,
        Math.sin(a) * r,
        3,
        Math.cos(a) * r,
      );
      cliff.scale.set(10 + rng() * 8, 10 + rng() * 20, 10 + rng() * 10);
      cliff.castShadow = false;
    }
    const moon = mesh(
      this.decor,
      new T.SphereGeometry(3.5, 48, 32),
      new T.MeshBasicMaterial({ color: 0xd7e3da, fog: false }),
      -32,
      40,
      -90,
    );
    moon.castShadow = moon.receiveShadow = false;
    const rockGeo = new T.IcosahedronGeometry(1, 4);
    const rp = rockGeo.attributes.position;
    for (let i = 0; i < rp.count; i++) {
      const x = rp.getX(i),
        y = rp.getY(i),
        z = rp.getZ(i),
        n =
          1 +
          0.11 * Math.sin(x * 7 + y * 8) * Math.cos(z * 9) +
          0.09 * Math.sin(y * 13 + z * 3);
      rp.setXYZ(i, x * n, y * n, z * n);
    }
    rockGeo.computeVertexNormals();
    const rocks = new T.InstancedMesh(rockGeo, this.materials.rock, 100),
      dummy = new T.Object3D();
    for (let i = 0; i < 100; i++) {
      const a = rng() * Math.PI * 2,
        r = 21 + rng() * 18,
        s = 0.2 + rng() ** 2 * 1.8;
      dummy.position.set(Math.sin(a) * r, s * 0.1 - 0.05, Math.cos(a) * r);
      dummy.scale.set(s, s * 0.7, s * 0.8);
      dummy.rotation.set(rng(), rng() * 6, rng());
      dummy.updateMatrix();
      rocks.setMatrixAt(i, dummy.matrix);
    }
    rocks.castShadow = rocks.receiveShadow = true;
    rocks.userData.ownedGeometry = true;
    this.arena.add(rocks);
    // Phototextured trees frame the court at several distances.
    for (let i = 0; i < 20; i++) {
      const a = i * 2.399,
        r = 27 + rng() * 25;
      const tree = this.art.model(
        i % 4 === 0 ? "dead-tree" : "pine",
        8 + rng() * 10,
      );
      tree.position.set(Math.sin(a) * r, -0.3, Math.cos(a) * r);
      tree.rotation.y = rng() * 6;
      this.decor.add(tree);
    }
    const grassMat = new T.MeshStandardMaterial({
      color: index === 2 ? 0x695941 : 0x596547,
      side: T.DoubleSide,
      roughness: 1,
    });
    const grassGeo = new T.BufferGeometry();
    grassGeo.setAttribute(
      "position",
      new T.Float32BufferAttribute(
        [-0.025, 0, 0, 0.025, 0, 0, 0.012, 0.43, 0.02],
        3,
      ),
    );
    grassGeo.computeVertexNormals();
    const grass = new T.InstancedMesh(grassGeo, grassMat, 1800);
    for (let i = 0; i < 1800; i++) {
      const a = rng() * Math.PI * 2,
        r = 12.8 + rng() * 13;
      dummy.position.set(Math.sin(a) * r, 0.01, Math.cos(a) * r);
      dummy.rotation.set((rng() - 0.5) * 0.4, rng() * 6, (rng() - 0.5) * 0.4);
      dummy.scale.setScalar(0.5 + rng() * 1.7);
      dummy.updateMatrix();
      grass.setMatrixAt(i, dummy.matrix);
    }
    grass.receiveShadow = true;
    this.arena.add(grass);
    for (let i = 0; i < 10; i++) {
      const a = (i / 10) * Math.PI * 2;
      const g = new T.Group();
      g.position.set(i % 2 ? -16 : 16, 0, -18 + Math.floor(i / 2) * 6);
      this.arena.add(g);
      cylinder(g, this.materials.wood, 0, 3.2, 0, 0.045, 6.4);
      const c = cloth(g, this.materials.cloth, 0.65, 2.4, 0.35, 4.7, 0);
      this.clothMeshes.push(c);
    }
    // Warm lantern light against cold moonlit stone; the spaces stay legible in play.
    for (const [x, z] of [
      [-10, -8],
      [10, -8],
      [-10, 8],
      [10, 8],
      [0, -20],
    ]) {
      const light = new T.PointLight(
        index === 1 ? 0xb6d5ab : 0xffa951,
        42,
        15,
        2,
      );
      light.position.set(x, 2.7, z);
      this.arena.add(light);
    }
    const fogTexture = textureCanvas((c) => {
      const g = c.createRadialGradient(256, 256, 5, 256, 256, 250);
      g.addColorStop(0, "#ffffff38");
      g.addColorStop(0.4, "#ffffff18");
      g.addColorStop(1, "#ffffff00");
      c.fillStyle = g;
      c.fillRect(0, 0, 512, 512);
    });
    for (let i = 0; i < 10; i++) {
      const m = new T.MeshBasicMaterial({
        map: fogTexture,
        color: 0xc2d4d4,
        transparent: true,
        opacity: 0.19,
        depthWrite: false,
        side: T.DoubleSide,
      });
      const sheet = mesh(
        this.decor,
        new T.PlaneGeometry(30, 7),
        m,
        (rng() - 0.5) * 50,
        1.5 + rng() * 2,
        -14 - rng() * 20,
      );
      sheet.castShadow = sheet.receiveShadow = false;
      sheet.userData.disposeMap = true;
      sheet.userData.startX = sheet.position.x;
      this.fogSheets.push(sheet);
    }
    // A large carved reliquary silhouette behind the belfry, seen through mist.
    const guardian = this.art.model("pilgrim", 12);
    guardian.position.set(0, 1, -40);
    guardian.traverse((o) => {
      if (isMesh(o)) {
        for (const m of Array.isArray(o.material) ? o.material : [o.material])
          m.dispose();
        o.material = this.materials.wall;
      }
    });
    this.decor.add(guardian);
    if (index === 1) {
      for (let i = 0; i < 70; i++) {
        const a = rng() * 6.28,
          r = 13 + rng() * 15;
        const stalk = cylinder(
          this.arena,
          this.materials.moss,
          Math.sin(a) * r,
          3,
          Math.cos(a) * r,
          0.045,
          6,
        );
        stalk.rotation.z = (rng() - 0.5) * 0.15;
      }
    }
    if (index === 2) {
      for (let i = 0; i < 16; i++) {
        const a = (i / 16) * Math.PI * 2,
          r = 14 + rng() * 3;
        const fire = mesh(
          this.arena,
          new T.ConeGeometry(0.12, 0.9, 12),
          this.materials.fire,
          Math.sin(a) * r,
          0.65,
          Math.cos(a) * r,
        );
        this.flames.push(fire);
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
  movement(v: Vec): Vec {
    return {
      x: v.x * Math.cos(this.yaw) + v.z * Math.sin(this.yaw),
      z: -v.x * Math.sin(this.yaw) + v.z * Math.cos(this.yaw),
    };
  }
  animateActor(
    a: Actor,
    x: number,
    z: number,
    facing: number,
    moving: boolean,
    action: string,
    progress: number,
  ) {
    const t = this.time;
    const root = a.root;
    root.position.set(x, 0, z);
    root.rotation.y += angleDiff(facing, root.rotation.y) * 0.2;
    root.rotation.z = 0;
    root.rotation.x = 0;
    for (const [name, b] of a.bones) b.quaternion.copy(a.rest.get(name)!);
    const rotate = (name: string, x: number, y = 0, z = 0) => {
      const bone = a.bones.get(name);
      if (bone)
        bone.quaternion.multiply(
          new T.Quaternion().setFromEuler(new T.Euler(x, y, z)),
        );
    };
    const walk = moving ? Math.sin(t * 10) : 0;
    rotate("LeftUpLeg", walk * 0.37);
    rotate("RightUpLeg", -walk * 0.37);
    rotate("LeftLeg", Math.max(0, -walk) * 0.55);
    rotate("RightLeg", Math.max(0, walk) * 0.55);
    rotate("Spine", Math.sin(t * 1.8) * 0.015);
    rotate("LeftArm", -0.12 + walk * 0.12, 0, 0.1);
    rotate("RightArm", -0.15 - walk * 0.12, 0, -0.08);
    rotate("RightForeArm", -0.12);
    if (action === "light" || action === "heavy" || action === "active") {
      const swing = Math.sin(Math.min(1, progress) * Math.PI);
      rotate("Spine", 0, -0.5 + swing * 0.85);
      rotate("RightArm", -0.8 - swing * 0.65, 0, -0.55 + swing * 1.2);
      rotate("RightForeArm", -0.3 - swing * 0.4);
    } else if (action === "windup") {
      rotate("RightArm", -progress * 1.8, 0, -0.5);
      rotate("Spine", 0, -progress * 0.4);
    } else if (action === "parry") {
      rotate("RightArm", -1.2, 0, -0.55);
      rotate("RightForeArm", -0.5);
    } else if (action === "heal") {
      rotate("LeftArm", -1.3);
      rotate("LeftForeArm", -1);
    } else if (action === "dodge") {
      root.rotation.x = -Math.sin(progress * Math.PI) * 1.3;
      root.position.y = -0.18;
    } else if (action === "stagger") {
      rotate("Spine", 0.7);
      root.position.y = -0.25;
    } else if (action === "dead") {
      root.rotation.z = -Math.PI / 2;
      root.position.y = 0.2;
    }
    if (a.robe) {
      const pos = a.robe.geometry.attributes.position,
        base = a.robe.userData.base as Float32Array;
      for (let i = 0; i < pos.count; i++) {
        const yy = base[i * 3 + 1],
          weight = 1 - (yy / (a.kind < 0 ? 1.15 : 2.8) + 0.5);
        pos.setZ(
          i,
          base[i * 3 + 2] -
            (moving ? 0.2 : 0) * weight +
            Math.sin(t * 3 + base[i * 3] * 8 + yy * 2) * 0.07 * weight,
        );
      }
      pos.needsUpdate = true;
      a.robe.geometry.computeVertexNormals();
    }
    root.updateMatrixWorld(true);
    if (a.rightHand) {
      const world = a.rightHand.getWorldPosition(new T.Vector3());
      root.worldToLocal(world);
      a.weapon.position.copy(world);
    }
    a.weapon.rotation.set(-0.65, 0, -0.1);
    if (action === "light" || action === "heavy" || action === "active")
      a.weapon.rotation.set(
        -0.6 + Math.sin(progress * Math.PI) * 1.5,
        Math.sin(progress * Math.PI) * 1.8 - 0.9,
        -0.3,
      );
    if (action === "windup") a.weapon.rotation.x = -2.5 * progress;
    if (a.halo) a.halo.rotation.z = t * 0.13;
  }
  burst(e: GameEvent) {
    if (e.kind === "swing" || e.kind === "slam") {
      const actor = e.kind === "swing" ? this.player : this.boss;
      const r = e.kind === "swing" ? (e.value === 2 ? 3 : 2.5) : 3.9;
      const m = mesh(
        this.scene,
        new T.RingGeometry(r - 0.18, r, 64, 1, -Math.PI / 2 - 1.1, 2.2),
        new T.MeshBasicMaterial({
          color: e.kind === "swing" ? 0xc3dad5 : 0xd5a86c,
          transparent: true,
          opacity: 0.35,
          side: T.DoubleSide,
          depthWrite: false,
        }),
        e.x,
        1,
        e.z,
      );
      m.rotation.set(-Math.PI / 2, 0, -actor.root.rotation.y);
      this.trails.push({
        mesh: m,
        velocity: new T.Vector3(),
        life: 0.18,
        max: 0.18,
        spin: 0,
      });
      return;
    }
    const color =
      e.kind === "heal" ? 0xa7d5b4 : e.kind === "hurt" ? 0x8e2420 : 0xf4d09a;
    const count = e.kind === "phase" || e.kind === "win" ? 65 : 20;
    for (let i = 0; i < count; i++) {
      const m = mesh(
        this.scene,
        new T.SphereGeometry(0.015 + Math.random() * 0.018, 4, 3),
        new T.MeshBasicMaterial({ color, transparent: true }),
        e.x,
        0.8 + Math.random(),
        e.z,
      );
      const a = Math.random() * 6.28;
      this.particles.push({
        mesh: m,
        velocity: new T.Vector3(
          Math.sin(a) * (1 + Math.random() * 4),
          2 + Math.random() * 4,
          Math.cos(a) * (1 + Math.random() * 4),
        ),
        life: 0.3 + Math.random() * 0.7,
        max: 1,
        spin: 0,
      });
    }
    if (!this.reducedMotion)
      this.shake = Math.max(
        this.shake,
        e.kind === "hurt" ? 0.13 : e.kind === "phase" ? 0.2 : 0.06,
      );
  }
  update(game: Combat, dt: number, locked: boolean) {
    if (!this.loaded) return;
    this.setArena(game.bossIndex);
    this.time += dt;
    const p = game.player,
      b = game.boss;
    this.animateActor(
      this.player,
      p.x,
      p.z,
      p.facing,
      this.moving && p.action === "idle",
      game.mode === "dead" ? "dead" : p.action,
      p.timer / p.duration,
    );
    this.animateActor(
      this.boss,
      b.x,
      b.z,
      b.facing,
      b.state === "approach" && game.mode === "combat",
      game.mode === "won" ? "dead" : b.state,
      b.timer / b.duration,
    );
    this.player.root.visible = true;
    // A close chase camera frames the combatants rather than displaying a tabletop.
    const dx = b.x - p.x,
      dz = b.z - p.z,
      d = Math.hypot(dx, dz);
    const desired = locked ? Math.atan2(-dx, -dz) : this.orbit;
    this.yaw += angleDiff(desired, this.yaw) * (1 - Math.exp(-dt * 1.8));
    const distance = 7.4 + Math.min(d, 13) * 0.1;
    const target = new T.Vector3(
      p.x + Math.sin(this.yaw) * distance + Math.cos(this.yaw) * 0.85,
      3.6 + Math.min(d, 12) * 0.055,
      p.z + Math.cos(this.yaw) * distance - Math.sin(this.yaw) * 0.85,
    );
    const look = new T.Vector3(
      p.x + (b.x - p.x) * 0.3,
      1.75,
      p.z + (b.z - p.z) * 0.3,
    );
    if (!this.cameraInitialized) {
      this.camera.position.copy(target);
      this.cameraInitialized = true;
    } else this.camera.position.lerp(target, 1 - Math.exp(-dt * 5));
    this.shake = Math.max(0, this.shake - dt * 0.8);
    if (!this.reducedMotion) {
      this.camera.position.x += (Math.random() - 0.5) * this.shake;
      this.camera.position.y += (Math.random() - 0.5) * this.shake;
    }
    this.camera.lookAt(look);
    this.fill.position.set(p.x + 2, 3, p.z + 2);
    this.lock.visible = locked && game.mode === "combat";
    this.lock.position.set(b.x, this.boss.height * 0.7, b.z);
    this.lock.lookAt(this.camera.position);
    this.drawTelegraph(game);
    this.drawHazards(game);
    for (const list of [this.particles, this.trails])
      for (let i = list.length - 1; i >= 0; i--) {
        const e = list[i];
        e.life -= dt;
        e.velocity.y -= dt * 7;
        e.mesh.position.addScaledVector(e.velocity, dt);
        (e.mesh.material as T.MeshBasicMaterial).opacity =
          Math.max(0, e.life / e.max) * 0.7;
        if (e.life <= 0) {
          this.scene.remove(e.mesh);
          e.mesh.geometry.dispose();
          (e.mesh.material as T.Material).dispose();
          list.splice(i, 1);
        }
      }
    for (const c of this.clothMeshes) {
      const pos = c.geometry.attributes.position,
        base = c.userData.base as Float32Array;
      for (let i = 0; i < pos.count; i++)
        pos.setZ(
          i,
          base[i * 3 + 2] +
            Math.sin(this.time * 2 + base[i * 3 + 1] * 2) *
              0.12 *
              (1 - base[i * 3 + 1] / 2.4),
        );
      pos.needsUpdate = true;
    }
    this.flames.forEach((f, i) => {
      f.scale.y = 1.5 + Math.sin(this.time * 7 + i) * 0.3;
    });
    this.fogSheets.forEach((f, i) => {
      f.position.x = f.userData.startX + Math.sin(this.time * 0.035 + i) * 5;
    });
    const rain = this.rain.geometry.attributes.position;
    for (let i = 0; i < rain.count; i++)
      rain.setY(i, (this.rainBase[i * 3 + 1] - this.time * 2.2 + 10000) % 25);
    rain.needsUpdate = true;
    if (this.quality === "low") this.renderer.render(this.scene, this.camera);
    else this.composer.render();
  }
  drawTelegraph(game: Combat) {
    const b = game.boss,
      a = game.attack;
    this.telegraph.visible =
      (b.state === "windup" || b.state === "active") && game.mode === "combat";
    if (!this.telegraph.visible) return;
    const key = `${game.bossIndex}-${b.attack}`;
    if (key !== this.telegraphKey) {
      this.telegraph.traverse((o) => {
        if (isMesh(o)) {
          o.geometry.dispose();
          (o.material as T.Material).dispose();
        }
      });
      this.telegraph.clear();
      this.telegraphKey = key;
      const m = new T.MeshBasicMaterial({
        color: a.parryable ? 0xe7bc74 : 0xc25f49,
        transparent: true,
        opacity: 0.2,
        side: T.DoubleSide,
        depthWrite: false,
      });
      if (a.shape === "sector") {
        const o = mesh(
          this.telegraph,
          new T.RingGeometry(
            0.7,
            a.range,
            64,
            1,
            -Math.PI / 2 - a.arc / 2,
            a.arc,
          ),
          m,
        );
        o.rotation.x = -Math.PI / 2;
      } else if (a.shape === "dash")
        box(this.telegraph, m, 0, 0, a.range / 2, 1.4, 0.01, a.range);
      else {
        const r = a.shape === "circle" ? a.range : 2;
        const o = mesh(this.telegraph, new T.RingGeometry(r - 0.04, r, 80), m);
        o.rotation.x = -Math.PI / 2;
      }
    }
    this.telegraph.position.set(b.x, 0.025, b.z);
    this.telegraph.rotation.y = b.facing;
    this.telegraph.traverse((o) => {
      if (isMesh(o))
        (o.material as T.MeshBasicMaterial).opacity =
          b.state === "active" ? 0.45 : 0.06 + (0.23 * b.timer) / b.duration;
    });
  }
  drawHazards(game: Combat) {
    const ids = new Set(game.hazards.map((h) => h.id));
    for (const [id, g] of this.hazards)
      if (!ids.has(id)) {
        this.scene.remove(g);
        g.traverse((o) => {
          if (isMesh(o)) {
            o.geometry.dispose();
            (o.material as T.Material).dispose();
          }
        });
        this.hazards.delete(id);
      }
    for (const h of game.hazards) {
      let g = this.hazards.get(h.id);
      if (!g) {
        g = new T.Group();
        this.scene.add(g);
        this.hazards.set(h.id, g);
        const m = new T.MeshBasicMaterial({
          color: h.type === "feather" ? 0xd1dfd2 : 0xd98a56,
          transparent: true,
          opacity: 0.7,
          side: T.DoubleSide,
          depthWrite: false,
        });
        if (h.type === "feather") {
          const o = mesh(g, new T.ConeGeometry(0.07, 0.8, 8), m);
          o.rotation.x = Math.PI / 2;
        } else {
          const o = mesh(g, new T.RingGeometry(0.98, 1, 96), m);
          o.rotation.x = -Math.PI / 2;
          if (h.type === "eruption") {
            const fire = mesh(
              g,
              new T.ConeGeometry(0.7, 3, 24),
              m.clone(),
              0,
              1.5,
              0,
            );
            fire.name = "eruption";
          }
        }
      }
      g.position.set(h.x, h.type === "feather" ? 1 : 0.03, h.z);
      g.visible = h.type !== "ring" || h.age >= h.delay;
      if (h.type === "feather") g.rotation.y = Math.atan2(h.vx, h.vz);
      else {
        g.scale.set(h.radius, 1, h.radius);
        if (h.type === "eruption")
          g.getObjectByName("eruption")!.visible = h.age >= h.delay;
      }
    }
  }
}
