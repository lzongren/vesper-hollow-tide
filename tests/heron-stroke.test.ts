import assert from "node:assert/strict";
import test from "node:test";
import { BOSSES } from "../src/combat";
import { heronGuards, heronStroke } from "../src/heron-sabres";

test("both Heron wrists stay continuous across contact, follow-through and chained attacks", () => {
  for (const attack of BOSSES[1].attacks)
    for (const side of ["Right", "Left"] as const) {
      const prepare = heronStroke(attack.shape, "windup", side)!;
      const strike = heronStroke(attack.shape, "active", side)!;
      const recover = heronStroke(attack.shape, "recover", side)!;
      assert.deepEqual(prepare[0], heronGuards[side]);
      assert.deepEqual(prepare.at(-1)!.slice(1), strike[0].slice(1));
      assert.deepEqual(strike.at(-1)!.slice(1), recover[0].slice(1));
      assert.deepEqual(recover.at(-1)!.slice(1), heronGuards[side].slice(1));
      for (const keys of [prepare, strike, recover]) {
        assert.equal(keys[0][0], 0);
        assert.equal(keys.at(-1)![0], 1);
        assert.ok(keys.every((k, i) => i === 0 || k[0] > keys[i - 1][0]));
      }
    }
});
