/** Wait for the already submitted opening view without blocking the UI thread.
 * Effects, reflection targets and shadow shaders are first used by a real draw. */
export async function waitForOpeningDraw(gl: WebGL2RenderingContext) {
  const fence = gl.fenceSync(gl.SYNC_GPU_COMMANDS_COMPLETE, 0);
  if (!fence) throw Error("The opening view could not be submitted to the GPU");
  try {
    gl.flush();
    for (;;) {
      const result = gl.clientWaitSync(fence, 0, 0);
      if (result === gl.ALREADY_SIGNALED || result === gl.CONDITION_SATISFIED)
        return;
      if (result === gl.WAIT_FAILED || gl.isContextLost())
        throw Error("WebGL lost the opening view");
      await new Promise<void>((resolve) => setTimeout(resolve, 12));
    }
  } finally {
    gl.deleteSync(fence);
  }
}
