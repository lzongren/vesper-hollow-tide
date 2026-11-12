/** Deterministic fixed-step combat; independent of rendering and browser APIs. */
export type Vec = { x: number; z: number };
export type Action =
  | "idle"
  | "light"
  | "heavy"
  | "dodge"
  | "parry"
  | "heal"
  | "hurt";
export type Mode = "intro" | "combat" | "dead" | "won";
export type Difficulty = "pilgrim" | "penitent";
export type EventKind =
  | "swing"
  | "hit"
  | "hurt"
  | "dodge"
  | "parry"
  | "heal"
  | "telegraph"
  | "slam"
  | "phase"
  | "stagger"
  | "win"
  | "death"
  | "step";
export interface GameEvent {
  kind: EventKind;
  x: number;
  z: number;
  value?: number;
}
export interface Input {
  move: Vec;
  aim?: Vec;
  action?: Action;
  locked: boolean;
}
export interface Attack {
  name: string;
  shape: "sector" | "circle" | "dash" | "fan" | "ring" | "eruption";
  windup: number;
  active: number;
  recovery: number;
  damage: number;
  range: number;
  arc: number;
  parryable: boolean;
}
export interface BossSpec {
  name: string;
  epithet: string;
  arena: string;
  lesson: string;
  lore: string;
  color: string;
  hp: number;
  speed: number;
  attacks: Attack[];
}
const sweep: Attack = {
  name: "Censer sweep",
  shape: "sector",
  windup: 1.05,
  active: 0.28,
  recovery: 1.05,
  damage: 24,
  range: 4.1,
  arc: 2.5,
  parryable: true,
};
export const BOSSES: BossSpec[] = [
  {
    name: "The Bellwarden",
    epithet: "Keeper of the last toll",
    arena: "The Drowned Belfry",
    lesson: "Read the swing. Step through the bell.",
    lore: "He rang the bell until the sea answered. Now he keeps vigil for a congregation that will never return.",
    color: "#d5a970",
    hp: 620,
    speed: 2.5,
    attacks: [
      sweep,
      {
        ...sweep,
        name: "Grave toll",
        shape: "circle",
        windup: 1.5,
        active: 0.35,
        recovery: 1.55,
        damage: 34,
        range: 4.7,
        parryable: false,
      },
      {
        ...sweep,
        name: "Procession",
        shape: "dash",
        windup: 1.1,
        active: 0.48,
        recovery: 1.2,
        damage: 27,
        range: 10,
        arc: 0.9,
      },
    ],
  },
  {
    name: "The Veiled Heron",
    epithet: "Bride of the white water",
    arena: "The Garden of Veils",
    lesson: "Close the distance. Let the feathers pass.",
    lore: "Her wedding veil became a thousand wings. Beneath the silk, something still remembers the shape of a human heart.",
    color: "#94d9cf",
    hp: 720,
    speed: 3.3,
    attacks: [
      {
        ...sweep,
        name: "Silken crescent",
        windup: 0.8,
        recovery: 0.85,
        range: 3.5,
        arc: 2.1,
        damage: 21,
      },
      {
        ...sweep,
        name: "Feather litany",
        shape: "fan",
        windup: 1.2,
        active: 0.18,
        recovery: 1.25,
        range: 16,
        damage: 18,
        parryable: false,
      },
      {
        ...sweep,
        name: "Wings of mourning",
        shape: "dash",
        windup: 1,
        active: 0.42,
        recovery: 1.15,
        range: 11,
        damage: 28,
        arc: 0.7,
      },
    ],
  },
  {
    name: "Saint of Cinders",
    epithet: "The prayer that would not die",
    arena: "The Ashen Reliquary",
    lesson: "Watch the floor. Punish the final prayer.",
    lore: "When the monastery burned, its abbot asked the flames to leave his people. The flames accepted everything else.",
    color: "#ef9078",
    hp: 860,
    speed: 2.3,
    attacks: [
      {
        ...sweep,
        name: "Ashen benediction",
        windup: 1.1,
        range: 4.5,
        damage: 27,
      },
      {
        ...sweep,
        name: "Circle of absolution",
        shape: "ring",
        windup: 1.4,
        active: 0.25,
        recovery: 1.5,
        range: 14,
        damage: 25,
        parryable: false,
      },
      {
        ...sweep,
        name: "Falling prayers",
        shape: "eruption",
        windup: 1.3,
        active: 0.2,
        recovery: 1.65,
        range: 14,
        damage: 30,
        parryable: false,
      },
    ],
  },
];
export interface Player extends Vec {
  hp: number;
  stamina: number;
  facing: number;
  action: Action;
  timer: number;
  duration: number;
  dealt: boolean;
  flasks: number;
  rally: number;
  rallyTime: number;
  invuln: number;
  regenDelay: number;
  combo: number;
  comboTime: number;
  dodgeDir: Vec;
}
export interface Boss extends Vec {
  hp: number;
  facing: number;
  state: "approach" | "windup" | "active" | "recover" | "stagger" | "phase";
  timer: number;
  duration: number;
  phase: 1 | 2;
  attack: number;
  cycle: number;
  hit: boolean;
  posture: number;
  phaseTriggered: boolean;
  dashDir: Vec;
  comboLeft: number;
}
export interface Hazard extends Vec {
  id: number;
  type: "feather" | "ring" | "eruption";
  vx: number;
  vz: number;
  life: number;
  age: number;
  delay: number;
  radius: number;
  damage: number;
  hit: boolean;
}
export const clamp = (n: number, a: number, b: number) =>
  Math.max(a, Math.min(b, n));
export const distance = (a: Vec, b: Vec) => Math.hypot(a.x - b.x, a.z - b.z);
export const angleTo = (a: Vec, b: Vec) => Math.atan2(b.x - a.x, b.z - a.z);
export const angleDiff = (a: number, b: number) =>
  Math.atan2(Math.sin(a - b), Math.cos(a - b));
export function inSector(
  origin: Vec,
  target: Vec,
  facing: number,
  range: number,
  arc: number,
) {
  return (
    distance(origin, target) <= range + 0.32 &&
    Math.abs(angleDiff(angleTo(origin, target), facing)) <= arc / 2
  );
}
export class Combat {
  readonly spec: BossSpec;
  player: Player;
  boss: Boss;
  mode: Mode = "intro";
  time = 0;
  modeTime = 0;
  events: GameEvent[] = [];
  hazards: Hazard[] = [];
  nextHazard = 0;
  hitsTaken = 0;
  parries = 0;
  damageDealt = 0;
  arenaRadius = 12.3;
  constructor(
    readonly bossIndex = 0,
    readonly difficulty: Difficulty = "penitent",
  ) {
    this.spec = BOSSES[bossIndex];
    this.player = {
      x: 0,
      z: 7,
      hp: 100,
      stamina: 100,
      facing: Math.PI,
      action: "idle",
      timer: 0,
      duration: 0,
      dealt: false,
      flasks: difficulty === "pilgrim" ? 5 : 3,
      rally: 0,
      rallyTime: 0,
      invuln: 0,
      regenDelay: 0,
      combo: 0,
      comboTime: 0,
      dodgeDir: { x: 0, z: 1 },
    };
    this.boss = {
      x: 0,
      z: -3,
      hp: this.spec.hp,
      facing: 0,
      state: "approach",
      timer: 0,
      duration: 0,
      phase: 1,
      attack: 0,
      cycle: 0,
      hit: false,
      posture: 0,
      phaseTriggered: false,
      dashDir: { x: 0, z: 1 },
      comboLeft: 0,
    };
  }
  event(kind: EventKind, at: Vec, value?: number) {
    this.events.push({ kind, x: at.x, z: at.z, value });
  }
  get attack() {
    return this.spec.attacks[this.boss.attack];
  }
  get invincible() {
    const p = this.player;
    return (
      p.invuln > 0 ||
      (p.action === "dodge" && p.timer >= 0.035 && p.timer <= 0.34)
    );
  }
  get parrying() {
    return (
      this.player.action === "parry" &&
      this.player.timer >= 0.025 &&
      this.player.timer <= (this.difficulty === "pilgrim" ? 0.32 : 0.23)
    );
  }
  get damageScale() {
    return this.difficulty === "pilgrim" ? 0.6 : 1;
  }
  startAction(action: Action, move: Vec): boolean {
    const p = this.player;
    if (
      this.mode !== "combat" ||
      p.action !== "idle" ||
      action === "idle" ||
      action === "hurt"
    )
      return false;
    const costs: Record<Action, number> = {
      idle: 0,
      light: 17,
      heavy: 32,
      dodge: 23,
      parry: 12,
      heal: 0,
      hurt: 0,
    };
    if (
      p.stamina < costs[action] ||
      (action === "heal" && (p.flasks <= 0 || p.hp >= 100))
    )
      return false;
    p.stamina -= costs[action];
    p.regenDelay = 0.65;
    p.action = action;
    p.timer = 0;
    p.dealt = false;
    p.duration = {
      idle: 0,
      light: 0.43,
      heavy: 0.88,
      dodge: 0.47,
      parry: 0.58,
      heal: 1.12,
      hurt: 0.3,
    }[action];
    if (action === "dodge") {
      const len = Math.hypot(move.x, move.z);
      p.dodgeDir =
        len > 0.1
          ? { x: move.x / len, z: move.z / len }
          : { x: Math.sin(p.facing), z: Math.cos(p.facing) };
      this.event("dodge", p);
    }
    if (action === "heal") p.flasks--;
    if (action === "light" || action === "heavy") {
      p.combo = p.comboTime > 0 ? (p.combo + 1) % 3 : 0;
      p.comboTime = 1.2;
      this.event("swing", p, action === "heavy" ? 2 : 1);
    }
    return true;
  }
  step(dt: number, input: Input) {
    dt = clamp(dt, 0, 1 / 30);
    this.time += dt;
    this.modeTime += dt;
    if (this.mode === "intro") {
      if (this.modeTime > 2.4) {
        this.mode = "combat";
        this.modeTime = 0;
      }
      return;
    }
    if (this.mode !== "combat") return;
    const p = this.player,
      b = this.boss;
    p.invuln = Math.max(0, p.invuln - dt);
    p.regenDelay = Math.max(0, p.regenDelay - dt);
    p.comboTime -= dt;
    p.rallyTime -= dt;
    if (p.rallyTime <= 0) p.rally = Math.max(0, p.rally - dt * 25);
    if (p.regenDelay <= 0 && p.action === "idle")
      p.stamina = Math.min(
        100,
        p.stamina + dt * (this.difficulty === "pilgrim" ? 33 : 27),
      );
    const ml = Math.hypot(input.move.x, input.move.z);
    const move = {
      x: input.move.x / Math.max(1, ml),
      z: input.move.z / Math.max(1, ml),
    };
    if (p.action === "idle") {
      if (input.locked) p.facing = angleTo(p, b);
      else if (input.aim) p.facing = angleTo(p, input.aim);
      else if (ml > 0.1) p.facing = Math.atan2(move.x, move.z);
      if (input.action) this.startAction(input.action, move);
    }
    p.timer += dt;
    if (p.action === "idle") {
      p.x += move.x * 5.2 * dt;
      p.z += move.z * 5.2 * dt;
    }
    if (p.action === "dodge" && p.timer < 0.32) {
      p.x += p.dodgeDir.x * 14 * dt;
      p.z += p.dodgeDir.z * 14 * dt;
    }
    if (p.action === "light" || p.action === "heavy") {
      const impact = p.action === "light" ? 0.14 : 0.46;
      if (p.timer < impact) {
        p.x += Math.sin(p.facing) * 1.2 * dt;
        p.z += Math.cos(p.facing) * 1.2 * dt;
      }
      if (p.timer >= impact && !p.dealt) {
        p.dealt = true;
        this.hitBoss(p.action === "heavy");
      }
    }
    if (p.action === "heal" && p.timer >= 0.76 && !p.dealt) {
      p.dealt = true;
      p.hp = Math.min(100, p.hp + 48);
      p.rally = 0;
      this.event("heal", p);
    }
    if (p.action !== "idle" && p.timer >= p.duration) p.action = "idle";
    this.constrain(p, 0.5);
    this.updateBoss(dt);
    this.updateHazards(dt);
    // Solid bodies separate gently; attacks still use their authored reach.
    const d = distance(p, b),
      minD = this.bossIndex === 0 ? 1.5 : 1.2;
    if (d < minD && d > 0.001) {
      const s = (minD - d) * 0.5;
      p.x += ((p.x - b.x) / d) * s;
      p.z += ((p.z - b.z) / d) * s;
      this.constrain(p, 0.5);
    }
  }
  constrain(v: Vec, margin: number) {
    const d = Math.hypot(v.x, v.z);
    if (d > this.arenaRadius - margin) {
      v.x *= (this.arenaRadius - margin) / d;
      v.z *= (this.arenaRadius - margin) / d;
    }
  }
  hitBoss(heavy: boolean) {
    const p = this.player,
      b = this.boss;
    if (b.state === "phase" || !inSector(p, b, p.facing, heavy ? 3.6 : 3, 2.25))
      return;
    const riposte = b.state === "stagger" && heavy;
    const damage = riposte ? 130 : heavy ? 47 : 24 + p.combo * 4;
    b.hp = Math.max(0, b.hp - damage);
    this.damageDealt += damage;
    b.posture += heavy ? 29 : 12;
    const regained = Math.min(p.rally, damage * 0.55);
    p.hp = Math.min(100, p.hp + regained);
    p.rally -= regained;
    this.event("hit", b, damage);
    if (b.hp <= 0) {
      this.mode = "won";
      this.modeTime = 0;
      this.hazards = [];
      this.event("win", b);
      return;
    }
    if (riposte) {
      b.posture = 0;
      b.state = "recover";
      b.timer = 0;
      b.duration = 1.3;
    } else if (b.posture >= 100 && b.state !== "stagger") this.stagger();
  }
  stagger() {
    const b = this.boss;
    b.state = "stagger";
    b.timer = 0;
    b.duration = 3.4;
    b.posture = 0;
    this.event("stagger", b);
  }
  hurt(damage: number, parryable = false) {
    if (this.mode !== "combat" || this.invincible) return;
    const p = this.player;
    if (
      parryable &&
      this.parrying &&
      Math.abs(angleDiff(p.facing, angleTo(p, this.boss))) < 1.6
    ) {
      p.stamina = Math.min(100, p.stamina + 24);
      p.invuln = 0.3;
      this.boss.posture += 55;
      this.parries++;
      this.event("parry", p);
      if (this.boss.posture >= 100) this.stagger();
      else {
        this.boss.state = "recover";
        this.boss.timer = 0;
        this.boss.duration = 1.3;
      }
      return;
    }
    const dealt = damage * this.damageScale;
    p.hp = Math.max(0, p.hp - dealt);
    p.rally = Math.min(100 - p.hp, p.rally + dealt * 0.7);
    p.rallyTime = 4;
    p.invuln = 0.6;
    p.action = "hurt";
    p.timer = 0;
    p.duration = 0.3;
    this.hitsTaken++;
    this.event("hurt", p, dealt);
    if (p.hp <= 0) {
      this.mode = "dead";
      this.modeTime = 0;
      this.event("death", p);
    }
  }
  beginAttack(index: number) {
    const b = this.boss;
    b.attack = index;
    b.state = "windup";
    b.timer = 0;
    b.duration = this.attack.windup * (b.phase === 2 ? 0.82 : 1);
    b.facing = angleTo(b, this.player);
    b.hit = false;
    this.event("telegraph", b, this.attack.parryable ? 1 : 0);
  }
  updateBoss(dt: number) {
    if (this.mode !== "combat") return;
    const b = this.boss,
      p = this.player;
    b.timer += dt;
    if (!b.phaseTriggered && b.hp <= this.spec.hp * 0.5) {
      b.phaseTriggered = true;
      b.phase = 2;
      b.state = "phase";
      b.timer = 0;
      b.duration = 2.2;
      b.posture = 0;
      this.hazards = [];
      this.event("phase", b);
      return;
    }
    if (b.state === "phase") {
      if (b.timer >= b.duration) {
        b.state = "approach";
        b.timer = 0;
      }
      return;
    }
    if (b.state === "stagger") {
      if (b.timer > b.duration) {
        b.state = "recover";
        b.timer = 0;
        b.duration = 0.7;
      }
      return;
    }
    if (b.state === "approach") {
      b.facing = angleTo(b, p);
      const d = distance(b, p);
      const farAttack = b.cycle % 3 !== 0;
      if (d > 2.9) {
        b.x += Math.sin(b.facing) * this.spec.speed * dt;
        b.z += Math.cos(b.facing) * this.spec.speed * dt;
      }
      if (b.timer > 0.6 && (d < 3.9 || (farAttack && d < 11) || b.timer > 3)) {
        const idx = d > 6 ? 1 + (b.cycle % 2) : b.cycle % 3;
        b.cycle++;
        b.comboLeft = b.phase === 2 ? 1 : 0;
        this.beginAttack(idx);
      }
      this.constrain(b, 1.5);
      return;
    }
    if (b.state === "windup") {
      if (b.timer < b.duration * 0.56) b.facing = angleTo(b, p);
      if (b.timer >= b.duration) {
        b.state = "active";
        b.timer = 0;
        b.duration = this.attack.active;
        b.dashDir = { x: Math.sin(b.facing), z: Math.cos(b.facing) };
        this.emitAttack();
      }
      return;
    }
    if (b.state === "active") {
      const a = this.attack;
      if (a.shape === "dash") {
        b.x += b.dashDir.x * 20 * dt;
        b.z += b.dashDir.z * 20 * dt;
        this.constrain(b, 1);
      }
      if (!b.hit) {
        const hit =
          a.shape === "circle"
            ? distance(b, p) < a.range + 0.3
            : a.shape === "dash"
              ? distance(b, p) < 1.8
              : a.shape === "sector"
                ? inSector(b, p, b.facing, a.range, a.arc)
                : false;
        if (hit) {
          b.hit = true;
          this.hurt(a.damage, a.parryable);
        }
      }
      if (b.state === "active" && b.timer >= b.duration) {
        b.state = "recover";
        b.timer = 0;
        b.duration = a.recovery * (b.phase === 2 ? 0.85 : 1);
      }
      return;
    }
    if (b.state === "recover" && b.timer >= b.duration) {
      if (b.comboLeft > 0) {
        b.comboLeft--;
        this.beginAttack((b.attack + 1) % 3);
      } else {
        b.state = "approach";
        b.timer = 0;
      }
    }
  }
  emitAttack() {
    const b = this.boss,
      a = this.attack;
    this.event("slam", b, a.shape === "sector" ? 1 : 2);
    const add = (h: Omit<Hazard, "id" | "age" | "hit">) =>
      this.hazards.push({ ...h, id: this.nextHazard++, age: 0, hit: false });
    if (a.shape === "fan") {
      const count = b.phase === 2 ? 11 : 7;
      for (let i = 0; i < count; i++) {
        const theta = b.facing + (i - (count - 1) / 2) * 0.19;
        add({
          type: "feather",
          x: b.x + Math.sin(theta),
          z: b.z + Math.cos(theta),
          vx: Math.sin(theta) * 7.2,
          vz: Math.cos(theta) * 7.2,
          life: 4,
          delay: 0,
          radius: 0.3,
          damage: a.damage,
        });
      }
    }
    if (a.shape === "ring")
      for (let i = 0; i < (b.phase === 2 ? 2 : 1); i++)
        add({
          type: "ring",
          x: b.x,
          z: b.z,
          vx: 0,
          vz: 0,
          life: 3.6 + i * 0.7,
          delay: i * 0.7,
          radius: 0.5,
          damage: a.damage,
        });
    if (a.shape === "eruption") {
      const targets = [{ x: this.player.x, z: this.player.z }];
      for (let i = 0; i < (b.phase === 2 ? 7 : 4); i++) {
        const theta = i * 2.399 + b.cycle;
        targets.push({ x: Math.sin(theta) * 7, z: Math.cos(theta) * 7 });
      }
      for (const [i, t] of targets.entries())
        add({
          type: "eruption",
          ...t,
          vx: 0,
          vz: 0,
          life: 2.2 + i * 0.12,
          delay: 1.35 + i * 0.12,
          radius: 2,
          damage: a.damage,
        });
    }
  }
  updateHazards(dt: number) {
    for (const h of this.hazards) {
      h.age += dt;
      if (h.age < h.delay) continue;
      if (h.type === "feather") {
        h.x += h.vx * dt;
        h.z += h.vz * dt;
      }
      if (h.type === "ring") h.radius = 0.5 + (h.age - h.delay) * 5.4;
      const d = distance(h, this.player);
      const hit =
        h.type === "ring"
          ? Math.abs(d - h.radius) < 0.46
          : h.type === "feather"
            ? d < 0.65
            : d < h.radius;
      if (!h.hit && hit) {
        h.hit = true;
        this.hurt(h.damage);
      }
    }
    this.hazards = this.hazards.filter(
      (h) => h.age < h.life && Math.hypot(h.x, h.z) < 30,
    );
  }
  drainEvents() {
    const events = this.events;
    this.events = [];
    return events;
  }
}
