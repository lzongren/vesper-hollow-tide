import type { Difficulty } from "./combat";
export interface Save {
  version: 1;
  cleared: boolean[];
  best: (number | null)[];
  attempts: number[];
  difficulty: Difficulty;
  volume: number;
  quality: "high" | "low";
  reducedMotion: boolean;
}
export const SAVE_KEY = "vesper.hollow-tide.v1";
export function defaults(): Save {
  return {
    version: 1,
    cleared: [false, false, false],
    best: [null, null, null],
    attempts: [0, 0, 0],
    difficulty: "penitent",
    volume: 0.55,
    quality: "high",
    reducedMotion:
      typeof matchMedia !== "undefined" &&
      matchMedia("(prefers-reduced-motion: reduce)").matches,
  };
}
export function parseSave(raw: string | null): Save {
  const base = defaults();
  if (!raw) return base;
  try {
    const data: unknown = JSON.parse(raw);
    if (!data || typeof data !== "object") return base;
    const d = data as Record<string, unknown>;
    if (d.version !== 1) return base;
    if (Array.isArray(d.cleared) && d.cleared.length === 3)
      base.cleared = d.cleared.map((v) => v === true);
    if (Array.isArray(d.best) && d.best.length === 3)
      base.best = d.best.map((v) =>
        typeof v === "number" && Number.isFinite(v) && v > 0 ? v : null,
      );
    if (Array.isArray(d.attempts) && d.attempts.length === 3)
      base.attempts = d.attempts.map((v) =>
        typeof v === "number" && Number.isInteger(v) && v >= 0 ? v : 0,
      );
    if (d.difficulty === "pilgrim") base.difficulty = "pilgrim";
    if (d.quality === "low") base.quality = "low";
    if (typeof d.volume === "number" && Number.isFinite(d.volume))
      base.volume = Math.max(0, Math.min(1, d.volume));
    if (typeof d.reducedMotion === "boolean")
      base.reducedMotion = d.reducedMotion;
    return base;
  } catch {
    return base;
  }
}
export function loadSave(): Save {
  try {
    return parseSave(localStorage.getItem(SAVE_KEY));
  } catch {
    return defaults();
  }
}
export function persist(save: Save) {
  try {
    localStorage.setItem(SAVE_KEY, JSON.stringify(save));
    return true;
  } catch {
    return false;
  }
}
