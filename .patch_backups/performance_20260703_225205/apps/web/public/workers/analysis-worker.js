self.onmessage = async (event) => {
  const file = event.data?.file;
  if (!(file instanceof Blob)) {
    self.postMessage({ type: 'error', code: 'WORKER_FILE_REQUIRED' });
    return;
  }

  const started = performance.now();
  const stage = (name, extra = {}) => self.postMessage({
    type: 'stage',
    stage: name,
    elapsedMs: Math.round((performance.now() - started) * 10) / 10,
    ...extra
  });

  try {
    stage('decode_started');
    const bitmap = await createImageBitmap(file);
    stage('decode_complete', { width: bitmap.width, height: bitmap.height });

    const scale = Math.min(1, 1280 / bitmap.width, 900 / bitmap.height);
    const width = Math.max(1, Math.round(bitmap.width * scale));
    const height = Math.max(1, Math.round(bitmap.height * scale));
    const canvas = new OffscreenCanvas(width, height);
    const context = canvas.getContext('2d', { alpha: false, desynchronized: true });
    if (!context) throw new Error('WORKER_CANVAS_CONTEXT');
    context.drawImage(bitmap, 0, 0, width, height);
    bitmap.close();
    stage('working_copy_ready', { workingWidth: width, workingHeight: height });

    const blob = await canvas.convertToBlob({ type: 'image/webp', quality: 0.86 });
    stage('preprocessing_complete', { byteSize: blob.size });
    self.postMessage({
      type: 'complete',
      totalMs: Math.round((performance.now() - started) * 10) / 10,
      workingWidth: width,
      workingHeight: height,
      byteSize: blob.size
    });
  } catch (error) {
    self.postMessage({
      type: 'error',
      code: error instanceof Error ? error.message : String(error),
      elapsedMs: Math.round((performance.now() - started) * 10) / 10
    });
  }
};
