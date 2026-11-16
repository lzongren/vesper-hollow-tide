import * as T from "three";
import type { Combat } from "./combat";
import { DASH_SPEED, DASH_REACH, SWEEP_MARGIN, SLAM_MARGIN } from "./combat";

/** World-space parameters shared by all three paving materials. */
export class GroundRite {
  pose = { value: new T.Vector4() };
  extent = { value: new T.Vector4() };
  charge = { value: 0 };

  update(game: Combat) {
    const b = game.boss, a = game.attack;
    if (game.mode !== "combat" || (b.state !== "windup" && b.state !== "active")) {
      this.charge.value = 0;
      return;
    }
    this.pose.value.set(b.x, b.z, Math.sin(b.facing), Math.cos(b.facing));
    let radius = 2, halfAngle = Math.PI, shape = 0;
    if (a.shape === "sector") {
      radius = a.range + SWEEP_MARGIN;
      halfAngle = a.arc / 2;
      shape = 1;
    } else if (a.shape === "circle") {
      radius = a.range + SLAM_MARGIN;
    } else if (a.shape === "dash") {
      // Remaining travel and the contact radius form a swept capsule.
      radius = DASH_SPEED * Math.max(0, a.active - (b.state === "active" ? b.timer : 0));
      shape = 2;
    }
    this.extent.value.set(radius, shape === 2 ? DASH_REACH : halfAngle, shape, a.parryable ? 1 : 0);
    this.charge.value = b.state === "active" ? 1 : 0.18 + 0.82 * Math.min(1, b.timer / b.duration);
  }
}

// Distances are in court metres. Keep an unbroken lip at the hit boundary;
// finer echoes break on dry stone and travel outwards through standing water.
export const riteSurface = /* glsl */ `
uniform vec4 ritePose, riteExtent;
uniform float riteCharge;
vec3 waterWriting(vec2 p, float pool, vec3 albedo) {
  if (riteCharge <= 0.) return vec3(0.);
  vec2 d = p - ritePose.xy;
  vec2 local = vec2(dot(d,vec2(ritePose.w,-ritePose.z)),dot(d,ritePose.zw));
  float radius = length(d);
  float inside = riteExtent.x - radius;
  float travel = radius;
  if (riteExtent.z == 1.) {
    vec2 side = vec2(sin(riteExtent.y),cos(riteExtent.y));
    vec2 folded = vec2(abs(local.x),local.y);
    float sideGap = side.x*folded.y-side.y*folded.x;
    float sideDistance = length(folded-side*clamp(dot(folded,side),0.,riteExtent.x));
    inside = min(inside,sign(sideGap)*sideDistance);
  } else if (riteExtent.z == 2.) {
    inside = riteExtent.y-length(local-vec2(0.,clamp(local.y,0.,riteExtent.x)));
    travel = max(local.y,0.);
  }
  float aa = clamp(fwidth(inside),.006,.07);
  if (inside < -2.*aa || inside > 1.1) return vec3(0.);
  float lip = 1.-smoothstep(.011,.035+aa,abs(inside));
  float noise = poolNoise(p*8.7);
  float veins = smoothstep(.20,.77,noise + .12*sin(p.y*22.+p.x*9.));
  float waves = .5+.5*cos(29.*inside + .6*sin(travel*6.) + 11.*riteCharge);
  float echo = pow(waves,4.) * exp(-4.8*max(0.,inside))
             * smoothstep(.015,.10,inside) * (.18+.82*pool);
  float mineral = clamp(dot(albedo,vec3(.28,.55,.17))*2.6,.20,1.);
  float energy = lip*(.24+.32*veins+.24*mineral) + echo*(.20+.72*veins);
  vec3 tint = mix(vec3(1.34,.18,.055),vec3(1.15,.63,.23),riteExtent.w);
  return tint*energy*(.48+.85*riteCharge);
}
`;
