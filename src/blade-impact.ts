import * as T from "three";
import { markNonOccluding } from "./court-occlusion";
import { jianPoint } from "./pilgrim-jian";

type Sliver = {
  position: T.Vector3;
  velocity: T.Vector3;
  age: number;
  life: number;
  width: number;
  exposure: number;
  drag: number;
  gravity: number;
  color: T.Color;
};

// World-space fragments keep their launch direction as either fighter turns.
// Six vertices give the hot core a tapered head and a thinner cooling tail.
export class BladeImpact extends T.Mesh<T.BufferGeometry, T.ShaderMaterial> {
  private static readonly capacity = 80;
  private readonly pieces: Sliver[] = [];
  private cursor = 0;
  private readonly edge = new T.Vector3();
  private readonly point = new T.Vector3();
  private readonly axis = new T.Vector3();
  private readonly side = new T.Vector3();
  private readonly cameraRay = new T.Vector3();
  private readonly across = new T.Vector3();
  private readonly shoulder = new T.Vector3();
  private readonly previousTip = new T.Vector3();
  private readonly currentTip = new T.Vector3();
  private hasMotion = false;

  constructor() {
    const g = new T.BufferGeometry(),
      vertices = BladeImpact.capacity * 6;
    for (const [name, size] of [
      ["position", 3],
      ["color", 4],
    ] as const)
      g.setAttribute(
        name,
        new T.Float32BufferAttribute(vertices * size, size).setUsage(
          T.DynamicDrawUsage,
        ),
      );
    const profile = new Float32Array(vertices * 2);
    for (let i = 0; i < BladeImpact.capacity; i++)
      profile.set([0, 0.18, 1, 0, 0, -1, 0, 0.18, 0, -1, -1, 0], i * 12);
    g.setAttribute("sparkUV", new T.BufferAttribute(profile, 2));
    super(
      g,
      new T.ShaderMaterial({
        vertexShader: `
          attribute vec4 color;
          attribute vec2 sparkUV;
          varying vec4 tint;
          varying vec2 profile;
          void main(){
            tint=color;
            profile=sparkUV;
            gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);
          }`,
        fragmentShader: `
          varying vec4 tint;
          varying vec2 profile;
          void main(){
            float crossSection=exp(-4.4*profile.x*profile.x);
            float head=smoothstep(-1.,-.13,profile.y);
            gl_FragColor=vec4(tint.rgb,tint.a*crossSection*(.16+.84*head));
            #include <colorspace_fragment>
          }`,
        transparent: true,
        depthWrite: false,
        side: T.DoubleSide,
        blending: T.AdditiveBlending,
        toneMapped: false,
      }),
    );
    for (let i = 0; i < BladeImpact.capacity; i++)
      this.pieces.push({
        position: new T.Vector3(),
        velocity: new T.Vector3(),
        color: new T.Color(),
        age: 1,
        life: 0,
        width: 0,
        exposure: 0,
        drag: 0,
        gravity: 0,
      });
    this.name = "Sword contact fragments";
    this.frustumCulled = false;
    this.clearBursts();
    markNonOccluding(this);
  }

  clearBursts() {
    for (const piece of this.pieces) piece.life = 0;
    this.cursor = 0;
    this.hasMotion = false;
    this.geometry.setDrawRange(0, 0);
    this.visible = false;
  }

  track(weapon: T.Object3D) {
    this.previousTip.copy(this.currentTip);
    weapon.localToWorld(this.currentTip.set(0, jianPoint, 0));
    if (!this.hasMotion) this.previousTip.copy(this.currentTip);
    this.hasMotion = true;
  }

  strike(
    weapon: T.Object3D,
    target: T.Vector3,
    height: number,
    court: number,
    damage: number,
    parry: boolean,
    quiet: boolean,
  ) {
    weapon.localToWorld(this.edge.set(0, 0.24, 0));
    weapon.localToWorld(this.point.set(0, jianPoint, 0));
    this.axis.subVectors(this.point, this.edge);
    this.shoulder
      .set(target.x, target.y + height * 0.48, target.z)
      .sub(this.edge);
    const along = T.MathUtils.clamp(
      this.shoulder.dot(this.axis) / Math.max(this.axis.lengthSq(), 0.001),
      0.13,
      1,
    );
    this.point.copy(this.edge).addScaledVector(this.axis, along);
    // A deep intersection otherwise hides the burst inside the Bellwarden's
    // armoured apron. Keep the blade height and move to its facing surface.
    this.shoulder
      .set(this.edge.x - target.x, 0, this.edge.z - target.z)
      .normalize();
    const distanceToFace =
      (this.point.x - target.x) * this.shoulder.x +
      (this.point.z - target.z) * this.shoulder.z;
    const radius = height * (court === 0 ? 0.225 : 0.12);
    if (!parry && distanceToFace < radius)
      this.point.addScaledVector(this.shoulder, radius - distanceToFace);
    this.side.subVectors(this.currentTip, this.previousTip);
    if (this.side.lengthSq() < 0.0004)
      this.side.set(this.axis.z, 0.18, -this.axis.x);
    this.side.normalize();
    this.across.set(-this.side.z, 0.1, this.side.x).normalize();
    const count = quiet ? 7 : parry ? 31 : damage >= 47 ? 27 : 18;
    const ceramic = court === 1 && !parry,
      cinder = court === 2 && !parry;
    for (let i = 0; i < count; i++) {
      const p = this.pieces[this.cursor++ % this.pieces.length],
        u = Math.random(),
        v = Math.random();
      p.position.copy(this.point);
      p.velocity
        .copy(this.side)
        .multiplyScalar((i % 5 === 0 ? -0.62 : 1) * (1.5 + u * 4.2))
        .addScaledVector(this.across, (v - 0.5) * (parry ? 8.5 : 5.8));
      p.velocity.addScaledVector(this.shoulder, 0.35 + u * 1.1);
      p.velocity.y += (Math.random() - 0.24) * (cinder ? 3.5 : 4.1);
      p.age = 0;
      p.life =
        (0.1 + Math.random() * 0.2) * (cinder ? 1.35 : ceramic ? 0.85 : 1);
      p.width = (ceramic ? 0.012 : 0.006) + 0.009 * u;
      p.exposure = ceramic ? 0.013 : cinder ? 0.028 : 0.043;
      p.gravity = cinder ? 3.8 : ceramic ? 14 : 9.4;
      p.drag = cinder ? 2.7 : 1.35;
      p.color.setHex(
        parry
          ? 0xffe6a1
          : ceramic
            ? i % 3
              ? 0xd4f1e8
              : 0x7fb4ad
            : cinder
              ? i % 3
                ? 0xff651c
                : 0xffb14c
              : i % 4
                ? 0xffad51
                : 0xffe6a6,
      );
      p.color.multiplyScalar(i % 4 === 0 ? 2.5 : 1.55);
    }
  }

  advance(dt: number, eye: T.Vector3) {
    let used = 0;
    const pos = this.geometry.getAttribute("position") as T.BufferAttribute;
    const color = this.geometry.getAttribute("color") as T.BufferAttribute;
    for (const p of this.pieces) {
      if (p.age >= p.life) continue;
      p.age += dt;
      if (p.age >= p.life) continue;
      p.velocity.y -= p.gravity * dt;
      p.velocity.multiplyScalar(Math.exp(-p.drag * dt));
      p.position.addScaledVector(p.velocity, dt);
      const remaining = 1 - p.age / p.life;
      const fade = remaining * remaining;
      this.cameraRay.subVectors(eye, p.position);
      this.side
        .crossVectors(p.velocity, this.cameraRay)
        .normalize()
        .multiplyScalar(p.width * (0.45 + 0.55 * fade));
      this.axis.copy(p.velocity).multiplyScalar(p.exposure);
      const vertex = (offset: number, width: number, alpha: number) => {
        pos.setXYZ(
          used,
          p.position.x + this.axis.x * offset + this.side.x * width,
          p.position.y + this.axis.y * offset + this.side.y * width,
          p.position.z + this.axis.z * offset + this.side.z * width,
        );
        color.setXYZW(
          used,
          p.color.r,
          p.color.g * (0.6 + 0.4 * fade),
          p.color.b * (0.3 + 0.7 * fade),
          alpha * fade,
        );
        used++;
      };
      vertex(0.18, 0, 1);
      vertex(0, 1, 1);
      vertex(-1, 0, 0.12);
      vertex(0.18, 0, 1);
      vertex(-1, 0, 0.12);
      vertex(0, -1, 1);
    }
    this.geometry.setDrawRange(0, used);
    this.visible = used > 0;
    if (used) {
      pos.needsUpdate = true;
      color.needsUpdate = true;
    }
  }
}
