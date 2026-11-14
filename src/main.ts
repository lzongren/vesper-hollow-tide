import "./style.css";
import { Combat, BOSSES, type Action, type Input } from "./combat";
import { Soundscape } from "./audio";
import { loadSave, persist } from "./save";
import type { World } from "./scene";
const $ = <T extends HTMLElement = HTMLElement>(id: string) =>
  document.getElementById(id) as T;
const save = loadSave(),
  audio = new Soundscape();
audio.volume = save.volume;
let world: World | undefined,
  game: Combat | undefined,
  selected = Math.max(
    0,
    save.cleared.findIndex((v) => !v),
  ),
  inGame = false,
  paused = false,
  locked = true,
  resultShown = false,
  modal = "",
  returnModal = "",
  lastFocus: HTMLElement | null = null;
let menuPadButtons: boolean[] = [];
let menuAxis = 0;
let last = 0,
  accumulator = 0,
  messageUntil = 0,
  queued: Action | undefined,
  queueUntil = 0,
  mouse = { x: innerWidth / 2, y: innerHeight / 2 },
  mouseUsed = false,
  touch = { x: 0, z: 0 };
const keys = new Set<string>();
let padButtons: boolean[] = [];
let lastHud = 0;
let lastStep = 0;
const chapterNumbers = ["I", "II", "III"],
  verbs = ["Enter the belfry", "Enter the garden", "Enter the reliquary"];
const clock = (s: number) =>
  `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
function renderChapters() {
  $("chapters").innerHTML = BOSSES.map(
    (b, i) =>
      `<button class="chapter ${i === selected ? "selected" : ""}" data-boss="${i}" aria-pressed="${i === selected}"><span class="chapter-num">${chapterNumbers[i]}</span><span><h3>${b.name}</h3><small>${b.arena}</small><em>${save.cleared[i] ? "VIGIL RELEASED · " + clock(save.best[i] ?? 0) : i === selected ? "SELECTED ENCOUNTER" : "CHALLENGE THIS VIGIL"}</em></span><span class="chapter-arrow">↗</span></button>`,
  ).join("");
  $("begin").innerHTML = `${verbs[selected]} <span>↗</span>`;
  $("progress-label").textContent =
    `${save.cleared.filter(Boolean).length} / 3 RELEASED`;
  document.querySelectorAll<HTMLButtonElement>("[data-boss]").forEach(
    (b) =>
      (b.onclick = () => {
        selected = Number(b.dataset.boss);
        renderChapters();
        document
          .querySelector<HTMLButtonElement>(`[data-boss="${selected}"]`)
          ?.focus();
      }),
  );
}
function clearInput() {
  keys.clear();
  queued = undefined;
  touch = { x: 0, z: 0 };
  padButtons = [];
}
function showModal(id: string) {
  if (!modal) lastFocus = document.activeElement as HTMLElement;
  for (const panel of document.querySelectorAll<HTMLElement>(".panel"))
    panel.hidden = true;
  modal = id;
  $("modal-backdrop").hidden = false;
  $(id).hidden = false;
  $(id).querySelector<HTMLElement>("button,select,input")?.focus();
}
function hideModal() {
  modal = "";
  $("modal-backdrop").hidden = true;
  document
    .querySelectorAll<HTMLElement>(".panel")
    .forEach((p) => (p.hidden = true));
  lastFocus?.focus();
}
function pause() {
  if (!inGame || !game || resultShown) return;
  paused = true;
  clearInput();
  void audio.pause();
  showModal("pause-panel");
}
function resume() {
  if (!inGame) return;
  paused = false;
  hideModal();
  clearInput();
  last = performance.now();
  void audio.resume();
}
function openSettings() {
  returnModal = inGame ? "pause-panel" : "";
  showModal("settings-panel");
}
function openHelp() {
  returnModal = inGame ? "pause-panel" : "";
  showModal("help-panel");
}
function closePanel() {
  if (returnModal) {
    showModal(returnModal);
    returnModal = "";
  } else hideModal();
}
function message(text: string, duration = 1.6) {
  $("combat-message").textContent = text;
  messageUntil = performance.now() + duration * 1000;
  $("combat-message").style.opacity = "1";
}
let startingEncounter = false;
async function begin(index = selected) {
  if (startingEncounter) return;
  startingEncounter = true;
  $("loading").hidden = false;
  hideModal();
  clearInput();
  try {
    if (!world) {
      const { World: WorldClass } = await import("./scene");
      world = new WorldClass($<HTMLCanvasElement>("world"));
      await world.ready;
      world.setQuality(save.quality);
      world.reducedMotion = save.reducedMotion;
    }
    await world.prepareCourt(index);
    game = new Combat(index, save.difficulty);
    selected = index;
    world.setArena(index);
    world.player.root.visible = true;
    world.telegraphKey = "";
    world.cameraInitialized = false;
    world.yaw = 0;
    save.attempts[index]++;
    persist(save);
    inGame = true;
    paused = false;
    resultShown = false;
    locked = true;
    accumulator = 0;
    lastStep = 0;
    last = performance.now();
    $("menu").hidden = true;
    $("hud").hidden = false;
    $("boss-name").textContent = game.spec.name;
    $("boss-epithet").textContent = game.spec.epithet;
    $("intro-chapter").textContent = `VIGIL ${chapterNumbers[index]}`;
    $("intro-arena").textContent = game.spec.arena;
    $("encounter-intro").style.opacity = "1";
    $("difficulty-label").textContent = save.difficulty.toUpperCase();
    $("combat-message").style.opacity = "0";
    messageUntil = 0;
    try {
      await audio.start();
    } catch {
      message("Audio unavailable — the pilgrimage continues in silence.", 3);
    }
    $("loading").hidden = true;
    updateHud();
  } catch (err) {
    $("loading").hidden = true;
    $("error").hidden = false;
    $("error").textContent =
      `The arena could not be opened. Check the connection and WebGL 2 support, then reload. ${err instanceof Error ? err.message : String(err)}`;
    console.error(err);
  } finally {
    startingEncounter = false;
  }
}
function backToMenu() {
  inGame = false;
  paused = false;
  clearInput();
  hideModal();
  $("menu").hidden = false;
  $("hud").hidden = true;
  renderChapters();
  void audio.pause();
  $("begin").focus();
}
function showResult() {
  if (!game || resultShown) return;
  resultShown = true;
  clearInput();
  const won = game.mode === "won";
  if (won) {
    save.cleared[selected] = true;
    const seconds = Math.max(0, game.time - 2.4);
    save.best[selected] = Math.min(save.best[selected] ?? Infinity, seconds);
    if (!persist(save))
      message("Progress could not be saved in this browser.", 5);
  }
  $("result-panel").classList.toggle("death", !won);
  $("result-eyebrow").textContent = won
    ? "THE HOLLOW TIDE FALLS SILENT"
    : "THE SEA REMEMBERS";
  const all = save.cleared.every(Boolean);
  $("result-title").textContent = won
    ? all
      ? "The last bell fades"
      : "Vigil released"
    : "Taken by the tide";
  $("result-copy").textContent = won
    ? all
      ? "Three saints at rest. Dawn belongs to the living."
      : `${game.spec.name} is finally at rest.`
    : game.spec.lesson;
  $("result-stats").innerHTML =
    `<span><b>${clock(Math.max(0, game.time - 2.4))}</b>TIME</span><span><b>${game.parries}</b>PARRIES</span><span><b>${game.hitsTaken}</b>HITS TAKEN</span>`;
  $("retry").innerHTML =
    won && selected < 2
      ? "Continue the pilgrimage <span>↗</span>"
      : won
        ? "Face the vigil again <span>↗</span>"
        : "Rise again <span>↗</span>";
  showModal("result-panel");
}
function updateHud() {
  if (!game) return;
  const p = game.player,
    b = game.boss;
  $("health-bar").style.width = `${p.hp}%`;
  $("rally-bar").style.width = `${p.hp + p.rally}%`;
  $("stamina-bar").style.width = `${p.stamina}%`;
  $("health-value").textContent = `${Math.ceil(p.hp)} / 100`;
  $("stamina-value").textContent = `${Math.floor(p.stamina)} STAMINA`;
  $("flask-count").textContent = String(p.flasks);
  $("boss-health-bar").style.width = `${(100 * b.hp) / game.spec.hp}%`;
  $("posture-bar").style.width = `${b.state === "stagger" ? 100 : b.posture}%`;
  $("phase-label").textContent = b.phase === 1 ? "FIRST VIGIL" : "AWAKENED";
  const a = game.attack;
  $("attack-tell").textContent =
    b.state === "stagger"
      ? "POSTURE BROKEN · HEAVY STRIKE TO RIPOSTE"
      : b.state === "phase"
        ? "THE VIGIL AWAKENS"
        : b.state === "windup"
          ? `${a.name} · ${a.parryable ? "GOLD / PARRY OR DODGE" : "RED / EVADE"}`
          : b.state === "recover"
            ? "AN OPENING. ANSWER."
            : p.stamina < 23
              ? "LOW STAMINA · MAKE SPACE"
              : "Observe. Endure. Answer.";
  $("attack-tell").style.color =
    b.state === "stagger"
      ? "#f4d18b"
      : b.state === "windup"
        ? a.parryable
          ? "#e9c582"
          : "#ee8b79"
        : "#acbdb4";
  $("lock-label").innerHTML =
    `<kbd>TAB</kbd> ${locked ? "Locked on" : "Free aim"}`;
}
function queue(action: Action) {
  if (inGame && !paused && game?.mode === "combat") {
    queued = action;
    queueUntil = performance.now() + 220;
  }
}
const keyMap: Record<string, Action> = {
  KeyJ: "light",
  KeyK: "heavy",
  Space: "dodge",
  KeyQ: "parry",
  KeyE: "heal",
};
window.addEventListener("keydown", (e) => {
  if (e.code === "Tab" && modal) {
    const els = Array.from(
      $(modal).querySelectorAll<HTMLElement>("button,input,select"),
    );
    if (els.length) {
      const i = els.indexOf(document.activeElement as HTMLElement);
      if (e.shiftKey && i <= 0) {
        e.preventDefault();
        els[els.length - 1].focus();
      } else if (!e.shiftKey && i === els.length - 1) {
        e.preventDefault();
        els[0].focus();
      }
    }
    return;
  }
  if (e.code === "Escape") {
    if (e.repeat) return;
    e.preventDefault();
    if (modal === "settings-panel" || modal === "help-panel") closePanel();
    else if (modal === "pause-panel") resume();
    else if (!modal) pause();
    return;
  }
  if (!inGame || paused || modal) return;
  if (
    [
      "Space",
      "Tab",
      "ArrowUp",
      "ArrowDown",
      "ArrowLeft",
      "ArrowRight",
    ].includes(e.code)
  )
    e.preventDefault();
  keys.add(e.code);
  if (e.repeat) return;
  if (e.code === "Tab") locked = !locked;
  if (keyMap[e.code]) queue(keyMap[e.code]);
  if (e.code === "KeyM") {
    audio.toggle();
    $("sound-button").textContent = audio.muted ? "×" : "♪";
  }
});
window.addEventListener("keyup", (e) => keys.delete(e.code));
window.addEventListener("pointermove", (e) => {
  mouse = { x: e.clientX, y: e.clientY };
  mouseUsed = true;
});
$("world").addEventListener("pointerdown", (e) => {
  if (e.pointerType === "touch") return;
  queue(e.button === 2 ? "heavy" : "light");
});
window.addEventListener("contextmenu", (e) => {
  if (inGame) e.preventDefault();
});
window.addEventListener("blur", () => {
  clearInput();
  if (inGame && !paused && !modal) pause();
});
document.addEventListener("visibilitychange", () => {
  if (document.hidden && inGame && !paused && !modal) pause();
});
window.addEventListener("resize", () => world?.resize());
$("begin").onclick = () => void begin();
$("settings-open").onclick = openSettings;
$("how-open").onclick = openHelp;
$("pause-button").onclick = pause;
$("resume").onclick = resume;
$("pause-settings").onclick = openSettings;
$("pause-help").onclick = openHelp;
$("abandon").onclick = backToMenu;
$("result-menu").onclick = backToMenu;
$("retry").onclick = () =>
  void begin(game?.mode === "won" && selected < 2 ? selected + 1 : selected);
$("sound-button").onclick = () => {
  $("sound-button").textContent = audio.toggle() ? "×" : "♪";
};
document
  .querySelectorAll<HTMLButtonElement>(".close-panel")
  .forEach((b) => (b.onclick = closePanel));
$<HTMLSelectElement>("difficulty").value = save.difficulty;
$<HTMLInputElement>("volume").value = String(save.volume * 100);
$<HTMLSelectElement>("quality").value = save.quality;
$<HTMLInputElement>("reduced-motion").checked = save.reducedMotion;
$("difficulty").onchange = () => {
  save.difficulty = $<HTMLSelectElement>("difficulty")
    .value as typeof save.difficulty;
  persist(save);
};
$("volume").oninput = () => {
  save.volume = Number($<HTMLInputElement>("volume").value) / 100;
  audio.setVolume(save.volume);
  persist(save);
};
$("quality").onchange = () => {
  save.quality = $<HTMLSelectElement>("quality").value as typeof save.quality;
  world?.setQuality(save.quality);
  persist(save);
};
$("reduced-motion").onchange = () => {
  save.reducedMotion = $<HTMLInputElement>("reduced-motion").checked;
  if (world) world.reducedMotion = save.reducedMotion;
  persist(save);
};
const stick = $("touch-stick");
let stickPointer = -1;
function moveStick(e: PointerEvent) {
  const rect = stick.getBoundingClientRect(),
    dx = (e.clientX - rect.left - rect.width / 2) / 45,
    dz = (e.clientY - rect.top - rect.height / 2) / 45;
  const len = Math.max(1, Math.hypot(dx, dz));
  touch = { x: dx / len, z: dz / len };
  (stick.firstElementChild as HTMLElement).style.transform =
    `translate(${touch.x * 30}px,${touch.z * 30}px)`;
}
stick.onpointerdown = (e) => {
  stickPointer = e.pointerId;
  stick.setPointerCapture(e.pointerId);
  moveStick(e);
};
stick.onpointermove = (e) => {
  if (e.pointerId === stickPointer) moveStick(e);
};
const stopStick = () => {
  stickPointer = -1;
  touch = { x: 0, z: 0 };
  (stick.firstElementChild as HTMLElement).style.transform = "";
};
stick.onpointerup = stopStick;
stick.onpointercancel = stopStick;
document.querySelectorAll<HTMLButtonElement>("[data-action]").forEach(
  (b) =>
    (b.onpointerdown = (e) => {
      e.preventDefault();
      queue(b.dataset.action as Action);
    }),
);
function getInput(): Input {
  let x =
      (keys.has("KeyD") || keys.has("ArrowRight") ? 1 : 0) -
      (keys.has("KeyA") || keys.has("ArrowLeft") ? 1 : 0) +
      touch.x,
    z =
      (keys.has("KeyS") || keys.has("ArrowDown") ? 1 : 0) -
      (keys.has("KeyW") || keys.has("ArrowUp") ? 1 : 0) +
      touch.z;
  const pad = navigator.getGamepads?.().find((g) => g?.connected);
  if (pad) {
    const dead = (v: number) => (Math.abs(v) < 0.18 ? 0 : v);
    x += dead(pad.axes[0] ?? 0);
    z += dead(pad.axes[1] ?? 0);
    const edge = (n: number) => !!pad.buttons[n]?.pressed && !padButtons[n];
    if (edge(9)) {
      if (paused && modal === "pause-panel") resume();
      else if (!paused) pause();
    }
    if (!paused) {
      if (edge(0)) queue("heal");
      if (edge(1)) queue("dodge");
      if (edge(2) || edge(5)) queue("light");
      if (edge(3) || edge(7)) queue("heavy");
      if (edge(4)) queue("parry");
      if (edge(11)) locked = !locked;
    }
    padButtons = pad.buttons.map((b) => b.pressed);
  }
  if (performance.now() > queueUntil) queued = undefined;
  return {
    move: world ? world.movement({ x, z }) : { x, z },
    aim: !locked && mouseUsed ? world?.aim(mouse.x, mouse.y) : undefined,
    action: queued,
    locked,
  };
}
function menuController() {
  const pad = navigator.getGamepads?.().find((g) => g?.connected);
  if (!pad) return;
  const edge = (i: number) => !!pad.buttons[i]?.pressed && !menuPadButtons[i];
  const direction = pad.buttons[12]?.pressed
    ? -1
    : pad.buttons[13]?.pressed
      ? 1
      : Math.abs(pad.axes[1] ?? 0) > 0.6
        ? Math.sign(pad.axes[1])
        : 0;
  if (direction && direction !== menuAxis) {
    const scope = modal ? $(modal) : $("menu");
    const buttons = Array.from(
      scope.querySelectorAll<HTMLElement>("button,select,input"),
    );
    const current = buttons.indexOf(document.activeElement as HTMLElement);
    buttons[(current + direction + buttons.length) % buttons.length]?.focus();
  }
  if (edge(0)) {
    const active = document.activeElement as HTMLElement;
    if (active.tagName === "BUTTON") active.click();
    else if (!modal && !inGame) void begin();
  }
  if (edge(1)) {
    if (modal === "pause-panel") resume();
    else if (modal === "help-panel" || modal === "settings-panel") closePanel();
  }
  if (edge(9) && modal === "pause-panel") resume();
  menuAxis = direction;
  menuPadButtons = pad.buttons.map((b) => b.pressed);
}
function frame(now: number) {
  requestAnimationFrame(frame);
  const dt = Math.min((now - last) / 1000 || 0.016, 0.05);
  last = now;
  if (!inGame || modal) {
    menuController();
    if (!inGame || paused) return;
  }
  if (!game || !world) return;
  const input = getInput();
  if (paused) return;
  world.moving = Math.hypot(input.move.x, input.move.z) > 0.1;
  accumulator += dt;
  while (accumulator >= 1 / 120) {
    const was = game.player.action;
    game.step(1 / 120, input);
    if (was === "idle" && input.action && game.player.action === input.action) {
      queued = undefined;
      input.action = undefined;
    }
    accumulator -= 1 / 120;
  }
  for (const e of game.drainEvents()) {
    audio.event(e);
    if (
      [
        "swing",
        "slam",
        "hit",
        "hurt",
        "heal",
        "parry",
        "phase",
        "stagger",
        "win",
        "dodge",
      ].includes(e.kind)
    )
      world.burst(e);
    if (e.kind === "parry") message("RITE DEFLECTED");
    if (e.kind === "stagger") message("POSTURE BROKEN", 2);
    if (e.kind === "phase") message("THE VIGIL AWAKENS", 2.3);
    if (e.kind === "hurt") {
      $("damage-flash").style.opacity = ".55";
      setTimeout(() => ($("damage-flash").style.opacity = "0"), 150);
    }
  }
  if (
    world.moving &&
    game.mode === "combat" &&
    game.player.action === "idle" &&
    game.time - lastStep > 0.32
  ) {
    lastStep = game.time;
    audio.event({ kind: "step", x: game.player.x, z: game.player.z });
  }
  audio.update(game.bossIndex, game.boss.phase, game.mode === "combat");
  world.update(game, dt, locked);
  if (now - lastHud > 60) {
    updateHud();
    lastHud = now;
  }
  $("encounter-intro").style.opacity = game.mode === "intro" ? "1" : "0";
  if (now > messageUntil) $("combat-message").style.opacity = "0";
  if ((game.mode === "won" || game.mode === "dead") && game.modeTime > 2.1)
    showResult();
}
renderChapters();
requestAnimationFrame(frame);
$("begin").focus({ preventScroll: true });
// Development-only observability for deterministic browser QA; eliminated by Vite production builds.
if (import.meta.env.DEV)
  Object.defineProperty(window, "__vesper", {
    get: () => ({ game, world, audio, save, paused, inGame }),
  });
