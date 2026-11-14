import * as T from "three";
import type { Hazard } from "./combat";

/** Eight vents can coexist in the awakened cast. Keep their lights in the
 * shrine throughout the encounter so the ignition cannot change shader variants. */
export class CinderLights extends T.Group {
  private sources = Array.from({ length: 8 }, () => new T.PointLight(0xffab69, 0, 9.5, 2));

  constructor() {
    super();
    this.add(...this.sources);
  }

  update(hazards: readonly Hazard[]) {
    let slot = 0;
    for (const h of hazards) {
      if (h.type !== "eruption" || slot >= this.sources.length) continue;
      const lamp = this.sources[slot++];
      const age = h.age - h.delay;
      const duration = h.life - h.delay;
      const rise = T.MathUtils.smoothstep(age, 0, .15);
      const fade = 1 - T.MathUtils.smoothstep(age, duration - .26, duration);
      const flicker = 1 + .07 * Math.sin(age * 18 + h.id) + .035 * Math.sin(age * 31 - h.id);
      lamp.position.set(h.x, .36 + .88 * rise * fade, h.z);
      lamp.intensity = 43 * rise * fade * flicker;
    }
    for (; slot < this.sources.length; slot++) this.sources[slot].intensity = 0;
  }
}


/** Curved sheets grow from separate vents and curl around a common updraft.
 * Surface coordinates follow the tongues, so turning the camera keeps parallax. */
export class CinderFire extends T.Mesh<T.BufferGeometry, T.ShaderMaterial> {
  constructor(seed: number) {
    const positions: number[] = [], uvs: number[] = [], axes: number[] = [], indices: number[] = [];
    for (let i = 0; i < 16; i++) {
      const angle = 2.39996 * i + seed, ring = Math.sqrt((i + .5) / 16);
      const cx = .69 * ring * Math.cos(angle), cz = .69 * ring * Math.sin(angle);
      const yaw = angle + .6, height = (2.1 + 1.6 * Math.sin(i * 9.1 + seed) ** 2) * (1 - .47 * ring);
      const start = positions.length / 3;
      for (let row = 0; row <= 14; row++) {
        const h = row / 14, bend = Math.sin(h * 4 + angle) * h;
        const width = (.11 + .11 * (1 - ring)) * (1 + .32 * Math.sin(h * 6)) * (1 - .93 * h);
        for (let col = 0; col < 3; col++) {
          const u = col - 1;
          positions.push(cx * (1 - .57 * h) + .18 * bend + u * width * Math.cos(yaw),
            .018 + height * h, cz * (1 - .57 * h) + .13 * h * h + u * width * Math.sin(yaw) + (1-u*u)*width*.34);
          uvs.push(col / 2, h);
          axes.push(angle);
        }
        if (row < 14) for (let col = 0; col < 2; col++) {
          const v = start + row * 3 + col;
          indices.push(v, v + 1, v + 3, v + 1, v + 4, v + 3);
        }
      }
    }
    // A charred bed and glowing fissures join the feet of the individual vents.
    const bed = positions.length / 3;
    for (const [x, z] of [[-1,-1],[-1,1],[1,1],[1,-1]]) {
      positions.push(x, .005, z);
      uvs.push(.5 + x*.5, .5 + z*.5);
      axes.push(-1);
    }
    indices.push(bed, bed+1, bed+2, bed, bed+2, bed+3);
    const geometry = new T.BufferGeometry();
    geometry.setAttribute("position", new T.Float32BufferAttribute(positions, 3));
    geometry.setAttribute("uv", new T.Float32BufferAttribute(uvs, 2));
    geometry.setAttribute("axis", new T.Float32BufferAttribute(axes, 1));
    geometry.setIndex(indices);
    const material = new T.ShaderMaterial({
      transparent: true, side: T.DoubleSide, forceSinglePass: true, depthWrite: false,
      uniforms: { age: { value: 0 }, life: { value: .85 } },
      vertexShader: /* glsl */ `
        uniform float age, life; attribute float axis;
        varying vec2 vUv; varying float phase;
        void main() {
          vUv=uv; phase=axis;
          float rise=smoothstep(0.,.15,age);
          float fall=smoothstep(life-.34,life,age);
          vec3 p=position;
          p.y *= (.20+.80*rise)*(1.-.32*fall);
          p.y += uv.y*fall*.28;
          p.xz += uv.y*uv.y*vec2(sin(axis+uv.y*6.-age*9.),cos(axis-uv.y*3.+age*6.))*.17;
          if (axis < 0.) p=position;
          gl_Position=projectionMatrix*modelViewMatrix*vec4(p,1.);
        }`,
      fragmentShader: /* glsl */ `
        uniform float age, life; varying vec2 vUv; varying float phase;
        void main() {
          float rise=smoothstep(0.,.06,age), fade=1.-smoothstep(life-.26,life,age);
          vec3 ember; float alpha;
          if(phase<0.) {
            vec2 q=vUv*2.-1.;
            float r=length(q);
            float grain=sin(q.x*33.+2.3*sin(q.y*17.))*sin(q.y*28.+q.x*8.);
            float veins=pow(1.-abs(grain),10.);
            float mask=1.-smoothstep(.47,.85,r+.06*grain);
            float pulse=.73+.20*sin(r*16.-age*9.);
            ember=mix(vec3(.13,.038,.014),vec3(1.28,.27,.024),veins*pulse);
            alpha=mask*rise*fade*.72;
          } else {
          float h=vUv.y, across=vUv.x*2.-1.;
          float curl=sin(h*12.-age*13.+phase)*.23+sin(h*22.-age*18.+phase*1.7)*.11;
          float core=1.-abs(across+curl*h);
          float heat=core*(1.-.58*h)+.12*sin(h*15.-age*17.+phase);
          float lace=smoothstep(.12,.60,core) * (1.-smoothstep(.65,1.,h+.12*sin(phase+age*7.)));
          float whorl=sin(h*25.-age*18.+phase+across*7.)*sin(h*34.-age*15.+across*9.);
          lace*=smoothstep(-.93,-.25,whorl+1.35*(1.-h)*core);
          alpha=lace*rise*fade*(.38+.57*core)*smoothstep(0.,.10,h);
          ember=mix(vec3(.38,.028,.006),vec3(1.9,.47,.073),smoothstep(.18,.76,heat));
          ember=mix(ember,vec3(2.6,1.58,.67),smoothstep(.73,1.08,heat)*(1.-h));
          }
          if(alpha<.016)discard;
          gl_FragColor=vec4(ember,alpha);
          #include <tonemapping_fragment>
          #include <colorspace_fragment>
        }`,
    });
    super(geometry, material);
    this.name = "eruption";
    this.visible = false;
  }
  burn(age: number, duration: number) {
    this.visible = age >= 0;
    this.material.uniforms.age.value = Math.max(0, age);
    this.material.uniforms.life.value = duration;
  }
}
