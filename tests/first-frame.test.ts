import assert from "node:assert/strict";
import test from "node:test";
import { waitForOpeningDraw } from "../src/first-frame";

function context(results: number[], lost = false) {
  const calls: string[] = [];
  const fence = {};
  const gl = {
    SYNC_GPU_COMMANDS_COMPLETE: 0x9117,
    ALREADY_SIGNALED: 0x911a,
    CONDITION_SATISFIED: 0x911c,
    WAIT_FAILED: 0x911d,
    fenceSync: () => fence,
    flush: () => calls.push("flush"),
    clientWaitSync(sync: object, flags: number, timeout: number) {
      assert.equal(sync, fence);
      assert.equal(flags, 0);
      assert.equal(timeout, 0);
      calls.push("poll");
      return results.shift()!;
    },
    isContextLost: () => lost,
    deleteSync(sync: object) {
      assert.equal(sync, fence);
      calls.push("delete");
    },
  };
  return { gl: gl as unknown as WebGL2RenderingContext, calls };
}

test("opening draw yields on timeout and releases its fence after GPU completion", async () => {
  const { gl, calls } = context([0x911b, 0x911c]);
  const opening = waitForOpeningDraw(gl);
  assert.deepEqual(calls, ["flush", "poll"]);
  await opening;
  assert.deepEqual(calls, ["flush", "poll", "poll", "delete"]);
});

test("failed waits and lost contexts release the opening fence", async () => {
  for (const sample of [context([0x911d]), context([0x911b], true)]) {
    await assert.rejects(waitForOpeningDraw(sample.gl));
    assert.deepEqual(sample.calls, ["flush", "poll", "delete"]);
  }
});
