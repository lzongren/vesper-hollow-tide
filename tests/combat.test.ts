import test from "node:test";
import assert from "node:assert/strict";
import {
  Combat,
  BOSSES,
  inSector,
  type Input,
  type Action,
} from "../src/combat.ts";
import { parseSave } from "../src/save.ts";
const neutral: Input = { move: { x: 0, z: 0 }, locked: true };
const advance = (g: Combat, t: number, input = neutral) => {
  for (let i = 0; i < Math.ceil(t * 120); i++) g.step(1 / 120, input);
};
const ready = (index = 0) => {
  const g = new Combat(index);
  advance(g, 2.5);
  g.boss.state = "recover";
  g.boss.timer = 0;
  g.boss.duration = 100;
  return g;
};
test("three bosses have distinct ranged patterns and readable windups", () => {
  assert.equal(BOSSES.length, 3);
  assert.equal(new Set(BOSSES.map((b) => b.attacks[1].shape)).size, 3);
  for (const b of BOSSES)
    for (const a of b.attacks) {
      assert.ok(a.windup >= 0.8);
      assert.ok(a.recovery >= 0.8);
    }
});
test("intro protects player and transitions exactly once", () => {
  const g = new Combat();
  g.hurt(50);
  assert.equal(g.player.hp, 100);
  assert.equal(g.startAction("light", { x: 0, z: 0 }), false);
  advance(g, 2.5);
  assert.equal(g.mode, "combat");
});
test("attacks consume stamina once, hit once, and do not hit behind", () => {
  const g = ready();
  g.player.z = 0;
  g.boss.z = -2;
  g.player.facing = Math.PI;
  g.startAction("light", { x: 0, z: 0 });
  advance(g, 0.5);
  assert.equal(g.boss.hp, g.spec.hp - 24);
  assert.ok(g.player.stamina < 84);
  assert.ok(inSector({ x: 0, z: 0 }, { x: 0, z: 2 }, 0, 3, 2));
  assert.ok(!inSector({ x: 0, z: 0 }, { x: 0, z: -2 }, 0, 3, 2));
});
test("insufficient stamina rejects action without overspending", () => {
  const g = ready();
  g.player.stamina = 12;
  assert.equal(g.startAction("dodge", { x: 1, z: 0 }), false);
  assert.equal(g.player.stamina, 12);
  assert.equal(g.player.action, "idle");
});
test("dodge invulnerability has start and end boundaries", () => {
  const g = ready();
  g.startAction("dodge", { x: 1, z: 0 });
  assert.equal(g.invincible, false);
  advance(g, 0.1);
  assert.equal(g.invincible, true);
  g.hurt(30);
  assert.equal(g.player.hp, 100);
  advance(g, 0.3);
  assert.equal(g.invincible, false);
  g.hurt(30);
  assert.equal(g.player.hp, 70);
});
test("timed parry prevents damage, restores stamina, and two parries stagger", () => {
  const g = ready();
  g.player.facing = Math.PI;
  g.player.stamina = 60;
  g.startAction("parry", { x: 0, z: 0 });
  advance(g, 0.1);
  g.hurt(24, true);
  assert.equal(g.player.hp, 100);
  assert.equal(g.parries, 1);
  assert.equal(g.boss.posture, 55);
  advance(g, 0.65);
  g.startAction("parry", { x: 0, z: 0 });
  advance(g, 0.1);
  g.hurt(24, true);
  assert.equal(g.boss.state, "stagger");
  assert.equal(g.parries, 2);
});
test("red attacks cannot be parried and late parries fail", () => {
  const g = ready();
  g.player.facing = Math.PI;
  g.startAction("parry", { x: 0, z: 0 });
  advance(g, 0.1);
  g.hurt(30, false);
  assert.equal(g.player.hp, 70);
  const late = ready();
  late.startAction("parry", { x: 0, z: 0 });
  advance(late, 0.4);
  late.hurt(30, true);
  assert.equal(late.player.hp, 70);
});
test("heavy riposte rewards posture break and exits stagger", () => {
  const g = ready();
  g.player.z = 0;
  g.boss.z = -2;
  g.player.facing = Math.PI;
  g.stagger();
  g.startAction("heavy", { x: 0, z: 0 });
  advance(g, 0.6);
  assert.equal(g.boss.hp, g.spec.hp - 130);
  assert.equal(g.boss.state, "recover");
});
test("healing consumes a vial, takes time, caps at maximum; damage interrupts", () => {
  const g = ready();
  g.player.hp = 70;
  assert.equal(g.startAction("heal", { x: 0, z: 0 }), true);
  assert.equal(g.player.flasks, 2);
  advance(g, 0.5);
  assert.equal(g.player.hp, 70);
  advance(g, 0.4);
  assert.equal(g.player.hp, 100);
  const interrupted = ready();
  interrupted.player.hp = 50;
  interrupted.startAction("heal", { x: 0, z: 0 });
  advance(interrupted, 0.3);
  interrupted.hurt(10);
  advance(interrupted, 1);
  assert.equal(interrupted.player.hp, 40);
  assert.equal(interrupted.player.flasks, 2);
});
test("rally health is recoverable briefly and then decays", () => {
  const g = ready();
  g.player.z = 0;
  g.boss.z = -2;
  g.player.facing = Math.PI;
  g.hurt(30);
  assert.equal(g.player.rally, 21);
  advance(g, 0.4);
  g.startAction("light", { x: 0, z: 0 });
  advance(g, 0.2);
  assert.ok(g.player.hp > 70);
  advance(g, 5);
  assert.equal(g.player.rally, 0);
});
test("all three bosses change phase once and clear old hazards", () => {
  for (let i = 0; i < 3; i++) {
    const g = ready(i);
    g.boss.hp = g.spec.hp * 0.49;
    advance(g, 0.1);
    assert.equal(g.boss.phase, 2);
    assert.equal(g.boss.state, "phase");
    assert.equal(g.hazards.length, 0);
    advance(g, 2.4);
    assert.notEqual(g.boss.state, "phase");
  }
});
test("fan, ring, and eruption attacks create bounded hazards", () => {
  for (let i = 0; i < 3; i++) {
    const g = ready(i);
    g.beginAttack(i === 0 ? 2 : 1);
    advance(g, 1.6);
    if (i > 0) assert.ok(g.hazards.length > 0);
    assert.ok(g.hazards.length < 15);
  }
  const g = ready(2);
  g.beginAttack(2);
  advance(g, 1.4);
  assert.equal(g.hazards.length, 5);
  assert.ok(g.hazards.every((h) => h.delay >= 1.35));
});
test("arena boundary contains dodges and boss charges", () => {
  const g = ready();
  g.player.x = 11.5;
  g.startAction("dodge", { x: 1, z: 1 });
  advance(g, 0.4);
  assert.ok(Math.hypot(g.player.x, g.player.z) <= g.arenaRadius - 0.49);
});
test("death and victory are terminal and cannot deal further damage", () => {
  const dead = ready();
  dead.hurt(200);
  assert.equal(dead.mode, "dead");
  assert.equal(dead.startAction("heal", { x: 0, z: 0 }), false);
  advance(dead, 5);
  assert.equal(dead.player.hp, 0);
  const won = ready();
  won.player.z = 0;
  won.boss.z = -2;
  won.player.facing = Math.PI;
  won.boss.hp = 1;
  won.boss.phaseTriggered = true;
  won.startAction("heavy", { x: 0, z: 0 });
  advance(won, 0.6);
  assert.equal(won.mode, "won");
  const hp = won.player.hp;
  won.hurt(200);
  assert.equal(won.player.hp, hp);
});
test("Pilgrim difficulty reduces damage and grants more vials", () => {
  const g = new Combat(0, "pilgrim");
  advance(g, 2.5);
  g.hurt(50);
  assert.equal(g.player.hp, 70);
  assert.equal(g.player.flasks, 5);
});
test("bounded dt prevents tab-resume tunneling", () => {
  const g = ready();
  const z = g.player.z;
  g.step(60, { ...neutral, move: { x: 0, z: 1 } });
  assert.ok(g.player.z - z < 0.2);
});
test("save parser accepts valid state and rejects malformed or obsolete saves", () => {
  assert.equal(parseSave("{").difficulty, "penitent");
  assert.deepEqual(
    parseSave('{"version":5,"cleared":[true,true,true]}').cleared,
    [false, false, false],
  );
  const s = parseSave(
    JSON.stringify({
      version: 1,
      cleared: [true, 1, false],
      attempts: [-1, 4, "5"],
      volume: 5,
      best: [-5, 90, "a"],
      quality: "low",
      difficulty: "pilgrim",
    }),
  );
  assert.deepEqual(s.cleared, [true, false, false]);
  assert.deepEqual(s.attempts, [0, 4, 0]);
  assert.equal(s.volume, 1);
  assert.deepEqual(s.best, [null, 90, null]);
  assert.equal(s.difficulty, "pilgrim");
});
// Reproduce real play using only public player input: no HP editing or damage cheats.
for (const difficulty of ["pilgrim", "penitent"] as const)
  for (let bossIndex = 0; bossIndex < 3; bossIndex++)
    test(`boss ${bossIndex + 1} is beatable on ${difficulty} through authored player actions`, () => {
      const g = new Combat(bossIndex, difficulty);
      let elapsed = 0;
      while (g.mode !== "won" && g.mode !== "dead" && elapsed < 240) {
        const p = g.player,
          b = g.boss,
          d = Math.hypot(b.x - p.x, b.z - p.z);
        const dir = {
          x: (b.x - p.x) / Math.max(d, 0.01),
          z: (b.z - p.z) / Math.max(d, 0.01),
        };
        let action: Action | undefined;
        let move = { x: 0, z: 0 };
        if (g.mode === "combat") {
          if (p.hp < 55 && p.flasks && b.state === "recover" && d > 5)
            action = "heal";
          else if (
            b.state === "windup" &&
            b.duration - b.timer < 0.15 &&
            g.attack.parryable &&
            d < g.attack.range
          )
            action = "parry";
          else if (b.state === "windup" && b.duration - b.timer < 0.12) {
            action = "dodge";
            move = dir;
          } else if (
            g.hazards.some(
              (h) =>
                (h.type === "ring" &&
                  h.age >= h.delay &&
                  Math.abs(Math.hypot(p.x - h.x, p.z - h.z) - h.radius) <
                    1.1) ||
                (h.type === "feather" &&
                  Math.hypot(p.x - h.x, p.z - h.z) < 1.8) ||
                (h.type === "eruption" &&
                  h.delay - h.age < 0.18 &&
                  Math.hypot(p.x - h.x, p.z - h.z) < h.radius + 0.2),
            )
          ) {
            action = "dodge";
            move = dir;
          } else if (b.state === "stagger") {
            if (d > 2.8) move = dir;
            else action = "heavy";
          } else if (b.state === "recover" || b.state === "approach") {
            if (d > 2.8) move = dir;
            else if (p.stamina >= 45) action = "light";
          } else if (b.state === "windup" && d > 3.5) move = dir;
        }
        g.step(1 / 120, { move, action, locked: true });
        g.drainEvents();
        elapsed += 1 / 120;
      }
      assert.equal(
        g.mode,
        "won",
        `boss=${bossIndex}, state=${g.mode}, hp=${g.player.hp}, bossHP=${g.boss.hp}, time=${elapsed}`,
      );
    });
