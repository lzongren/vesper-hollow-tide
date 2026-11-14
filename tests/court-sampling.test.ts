import assert from "node:assert/strict";
import test from "node:test";
import { courtSamples } from "../src/court-sampling";

test("selects a shared HDR color and depth sample count, capped at four", () => {
  assert.equal(courtSamples(Int32Array.of(8,4,2),Int32Array.of(2,4,8)),4);
  assert.equal(courtSamples(Int32Array.of(8,4,2),Int32Array.of(2)),2);
  assert.equal(courtSamples(Int32Array.of(4),Int32Array.of(2)),0);
  assert.equal(courtSamples(new Int32Array(),Int32Array.of(4)),0);
});
