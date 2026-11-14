import type { GameEvent } from "./combat";
/** Original generative score: bowed drones, inharmonic bells, breath and frame drums. */
export class Soundscape {
  context?: AudioContext;
  master?: GainNode;
  music?: GainNode;
  effects?: GainNode;
  reverb?: ConvolverNode;
  volume = 0.55;
  muted = false;
  enabled = false;
  nextBeat = 0;
  beat = 0;
  boss = 0;
  phase = 1;
  running = false;
  async start() {
    if (!this.context) {
      const c = (this.context = new AudioContext());
      this.master = c.createGain();
      this.master.gain.value = this.volume;
      this.master.connect(c.destination);
      const limiter = c.createDynamicsCompressor();
      limiter.threshold.value = -16;
      limiter.knee.value = 12;
      limiter.ratio.value = 5;
      limiter.connect(this.master);
      this.music = c.createGain();
      this.music.gain.value = 0.48;
      this.music.connect(limiter);
      this.effects = c.createGain();
      this.effects.gain.value = 0.7;
      this.effects.connect(limiter);
      this.reverb = c.createConvolver();
      const impulse = c.createBuffer(2, c.sampleRate * 2.7, c.sampleRate);
      for (let ch = 0; ch < 2; ch++) {
        const data = impulse.getChannelData(ch);
        for (let i = 0; i < data.length; i++)
          data[i] =
            (Math.random() * 2 - 1) * Math.pow(1 - i / data.length, 3) * 0.55;
      }
      this.reverb.buffer = impulse;
      const wet = c.createGain();
      wet.gain.value = 0.38;
      this.reverb.connect(wet);
      wet.connect(limiter);
    }
    await this.context.resume();
    this.enabled = true;
    this.running = true;
    this.nextBeat = this.context.currentTime + 0.05;
  }
  setVolume(v: number) {
    this.volume = v;
    if (this.master && this.context)
      this.master.gain.setTargetAtTime(
        this.muted ? 0 : v,
        this.context.currentTime,
        0.08,
      );
  }
  toggle() {
    this.muted = !this.muted;
    this.setVolume(this.volume);
    return this.muted;
  }
  async pause() {
    this.running = false;
    await this.context?.suspend();
  }
  async resume() {
    if (this.context) {
      await this.context.resume();
      this.running = true;
      this.nextBeat = this.context.currentTime + 0.1;
    }
  }
  tone(
    freq: number,
    time: number,
    duration: number,
    volume: number,
    type: OscillatorType = "sine",
    pan = 0,
    music = false,
  ) {
    const c = this.context;
    if (!c || !this.effects || !this.music) return;
    const o = c.createOscillator(),
      g = c.createGain(),
      p = c.createStereoPanner();
    o.type = type;
    o.frequency.value = freq;
    p.pan.value = pan;
    g.gain.setValueAtTime(0.0001, time);
    g.gain.exponentialRampToValueAtTime(volume, time + 0.018);
    g.gain.exponentialRampToValueAtTime(0.0001, time + duration);
    o.connect(g);
    g.connect(p);
    p.connect(music ? this.music : this.effects);
    if (this.reverb) p.connect(this.reverb);
    o.onended = () => {
      o.disconnect();
      g.disconnect();
      p.disconnect();
    };
    o.start(time);
    o.stop(time + duration + 0.05);
  }
  noise(time: number, duration: number, volume: number, freq = 500) {
    const c = this.context;
    if (!c || !this.effects) return;
    const buffer = c.createBuffer(
      1,
      Math.ceil(c.sampleRate * duration),
      c.sampleRate,
    );
    const d = buffer.getChannelData(0);
    for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
    const src = c.createBufferSource(),
      filter = c.createBiquadFilter(),
      g = c.createGain();
    src.buffer = buffer;
    filter.type = "bandpass";
    filter.frequency.value = freq;
    filter.Q.value = 0.7;
    g.gain.setValueAtTime(volume, time);
    g.gain.exponentialRampToValueAtTime(0.0001, time + duration);
    src.connect(filter);
    filter.connect(g);
    g.connect(this.effects);
    src.onended = () => {
      src.disconnect();
      filter.disconnect();
      g.disconnect();
    };
    src.start(time);
    src.stop(time + duration);
  }
  bell(freq: number, t: number, amp = 0.15) {
    [1, 2.76, 5.4, 8.93].forEach((ratio, i) =>
      this.tone(
        freq * ratio,
        t,
        2.8 / (i + 1),
        amp / (i + 1),
        "sine",
        i % 2 ? 0.25 : -0.25,
      ),
    );
  }
  update(boss: number, phase: number, inCombat: boolean) {
    const c = this.context;
    if (!c || !this.running) return;
    this.boss = boss;
    this.phase = phase;
    if (c.currentTime > this.nextBeat + 0.5)
      this.nextBeat = c.currentTime + 0.05;
    if (c.currentTime + 0.16 < this.nextBeat) return;
    const t = this.nextBeat;
    const root = [73.416, 82.407, 65.406][boss];
    const tempo = inCombat ? (phase === 2 ? 0.36 : 0.48) : 0.75;
    this.nextBeat += tempo;
    if (this.beat % 8 === 0) {
      for (const [i, ratio] of [1, 1.5, 2, 2.3784].entries()) {
        this.tone(
          root * ratio * 0.997,
          t,
          tempo * 12,
          0.055,
          "sine",
          -0.6 + i * 0.4,
          true,
        );
        this.tone(
          root * ratio * 1.003,
          t + 0.06,
          tempo * 12,
          0.025,
          "triangle",
          0.6 - i * 0.4,
          true,
        );
      }
    }
    if (this.beat % 4 === 0)
      this.bell(root * (this.beat % 16 === 0 ? 2 : 3), t, 0.05);
    if (inCombat) {
      if (this.beat % 2 === 0) {
        this.tone(49, t, 0.27, 0.3);
        this.tone(92, t, 0.09, 0.12);
        this.noise(t, 0.13, 0.16, 180);
      }
      if (phase === 2 && this.beat % 2 === 1) this.noise(t, 0.09, 0.055, 1800);
      const motif = [0, 7, 12, 10, 7, 3, 2, 7];
      const semitone = motif[Math.floor(this.beat / 2) % motif.length];
      if (this.beat % 2 === 0)
        this.tone(
          root * 4 * Math.pow(2, semitone / 12),
          t,
          0.8,
          0.035,
          "sine",
          Math.sin(this.beat) * 0.65,
          true,
        );
    }
    this.beat++;
  }
  event(e: GameEvent) {
    const c = this.context;
    if (!c || !this.running) return;
    const t = c.currentTime;
    const pan = Math.max(-0.8, Math.min(0.8, e.x / 15));
    switch (e.kind) {
      case "step":
        this.noise(t, 0.065, 0.028, 380);
        this.tone(100, t, 0.065, 0.018, "sine", pan);
        break;
      case "swing":
        this.noise(t, 0.2, 0.15, 1000);
        this.tone(160, t, 0.18, 0.045, "triangle", pan);
        break;
      case "hit":
        this.noise(t, 0.15, 0.38, 850);
        this.tone(78, t, 0.17, 0.26, "triangle", pan);
        this.tone(740, t, 0.15, 0.07, "sine", pan);
        break;
      case "hurt":
        this.tone(44, t, 0.5, 0.3, "triangle");
        this.noise(t, 0.32, 0.26, 240);
        break;
      case "dodge":
        this.noise(t, 0.3, 0.08, 1400);
        break;
      case "parry":
        this.bell(587.3, t, 0.24);
        this.noise(t, 0.08, 0.25, 3000);
        break;
      case "heal":
        [0, 7, 12].forEach((s, i) =>
          this.tone(293.66 * 2 ** (s / 12), t + i * 0.1, 1, 0.1),
        );
        break;
      case "telegraph":
        this.tone(e.value ? 440 : 146.8, t, 0.38, 0.055, "sine", pan);
        break;
      case "slam":
        if (this.boss === 0) {
          // The heavy casting rings past the much shorter sound of the haft impact.
          this.bell(e.value === 1 ? 109.9 : 73.4, t + 0.018, 0.19);
          this.noise(t, 0.055, 0.15, 1840);
        } else if (this.boss === 2) {
          // Bronze rings strike the two rails on release and on the rebound.
          for (const [delay, pitch, gain] of [[.012, 764, .045], [.068, 911, .032], [.143, 812, .023]]) {
            this.tone(pitch, t + delay, .32, gain, "sine", pan);
            this.tone(pitch * 2.68, t + delay, .12, gain * .47, "sine", pan);
          }
        }
        this.tone(36, t, 0.65, 0.3);
        this.noise(t, 0.4, 0.22, 130);
        break;
      case "phase":
        this.bell(73.4, t, 0.28);
        this.noise(t, 1.8, 0.25, 330);
        break;
      case "stagger":
        this.bell(392, t, 0.19);
        break;
      case "win":
        [146.83, 220, 293.66, 349.23].forEach((f, i) =>
          this.bell(f, t + i * 0.35, 0.12),
        );
        break;
      case "death":
        this.tone(55, t, 3, 0.24);
        break;
    }
  }
}
