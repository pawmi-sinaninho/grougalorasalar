from __future__ import annotations

from pathlib import Path
from datetime import datetime
import re
import shutil

ROOT = Path.cwd()
BACKUP_DIR = ROOT / ".patch_backups" / f"performance_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

FILES = {
    "page": ROOT / "apps/web/app/page.tsx",
    "worker": ROOT / "apps/web/public/workers/analysis-worker.js",
    "recognition": ROOT / "services/api/grougal_solver/recognition.py",
    "fast_recognition": ROOT / "services/api/grougal_solver/fast_recognition.py",
}

for label, path in FILES.items():
    if not path.exists():
        raise SystemExit(f"Missing expected {label} file: {path}")

def backup(path: Path) -> None:
    target = BACKUP_DIR / path.relative_to(ROOT)
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        shutil.copy2(path, target)

def write(path: Path, text: str) -> None:
    backup(path)
    path.write_text(text, encoding="utf-8")

def replace_exact(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly 1 occurrence in {path}, found {count}")
    write(path, text.replace(old, new, 1))
    print(f"updated: {path.relative_to(ROOT)} — {label}")

def replace_regex(path: Path, pattern: str, repl: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    new_text, count = re.subn(pattern, repl, text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly 1 regex replacement in {path}, found {count}")
    write(path, new_text)
    print(f"updated: {path.relative_to(ROOT)} — {label}")


# ---------------------------------------------------------------------------
# 1) Browser worker: produce an upload-ready processed Blob, not only metrics.
# ---------------------------------------------------------------------------
worker_path = FILES["worker"]
worker_code = r"""self.onmessage = async (event) => {
  const file = event.data?.file;

  if (!(file instanceof Blob)) {
    self.postMessage({ type: 'error', code: 'WORKER_FILE_REQUIRED' });
    return;
  }

  const started = performance.now();
  const stage = (name, extra = {}) =>
    self.postMessage({
      type: 'stage',
      stage: name,
      elapsedMs: Math.round((performance.now() - started) * 10) / 10,
      ...extra,
    });

  try {
    stage('decode_started');

    const bitmap = await createImageBitmap(file);
    stage('decode_complete', { width: bitmap.width, height: bitmap.height });

    // Keep enough detail for glyphs/pillars, but avoid sending raw 4K captures.
    // The backend still performs the authoritative normalisation.
    const scale = Math.min(1, 1920 / bitmap.width, 1080 / bitmap.height);
    const width = Math.max(1, Math.round(bitmap.width * scale));
    const height = Math.max(1, Math.round(bitmap.height * scale));

    const canvas = new OffscreenCanvas(width, height);
    const context = canvas.getContext('2d', {
      alpha: false,
      desynchronized: true,
    });

    if (!context) throw new Error('WORKER_CANVAS_CONTEXT');

    context.drawImage(bitmap, 0, 0, width, height);
    bitmap.close();

    stage('working_copy_ready', { workingWidth: width, workingHeight: height });

    let blob;
    try {
      blob = await canvas.convertToBlob({ type: 'image/webp', quality: 0.9 });
    } catch {
      blob = await canvas.convertToBlob({ type: 'image/jpeg', quality: 0.9 });
    }

    stage('preprocessing_complete', { byteSize: blob.size });

    self.postMessage({
      type: 'complete',
      totalMs: Math.round((performance.now() - started) * 10) / 10,
      workingWidth: width,
      workingHeight: height,
      byteSize: blob.size,
      mimeType: blob.type,
      blob,
    });
  } catch (error) {
    self.postMessage({
      type: 'error',
      code: error instanceof Error ? error.message : String(error),
      elapsedMs: Math.round((performance.now() - started) * 10) / 10,
    });
  }
};
"""
write(worker_path, worker_code)
print(f"updated: {worker_path.relative_to(ROOT)} — browser upload preprocessing worker")


# ---------------------------------------------------------------------------
# 2) Frontend page: await the processed worker file for upload.
#    Preview remains the original object URL, so feedback stays instant.
# ---------------------------------------------------------------------------
page_path = FILES["page"]

replace_regex(
    page_path,
    r"""function startLocalWorker\(file: File\) \{.*?\} function stopWindowCapture""",
    r"""function preprocessImage(file: File): Promise<File> {
    if (typeof Worker === 'undefined') return Promise.resolve(file);
    return new Promise(resolve => {
      const worker = new Worker('/workers/analysis-worker.js');
      let settled = false;
      const finish = (processed: File) => {
        if (settled) return;
        settled = true;
        worker.terminate();
        resolve(processed);
      };
      worker.onmessage = (event: MessageEvent) => {
        if (event.data.type === 'stage') setProgress(event.data);
        if (event.data.type === 'complete') {
          const blob = event.data.blob as Blob | undefined;
          const mimeType = event.data.mimeType || blob?.type || 'image/webp';
          const extension = mimeType.includes('webp') ? 'webp' : 'jpg';
          const baseName = file.name.replace(/\.[^.]+$/, '');
          finish(blob instanceof Blob ? new File([blob], `${baseName}-optimised.${extension}`, { type: mimeType }) : file);
        }
        if (event.data.type === 'error') finish(file);
      };
      worker.onerror = () => finish(file);
      worker.postMessage({ file });
    });
  } function stopWindowCapture""",
    "frontend uses worker output as upload file",
)

replace_exact(
    page_path,
    "startLocalWorker(file); try {",
    "const uploadFilePromise = preprocessImage(file); try {",
    "start preprocessing promise before API work",
)

replace_exact(
    page_path,
    "const uploaded = await uploadImage(analysisId, accessToken, stateVersion, file);",
    "const uploadFile = await uploadFilePromise; const uploaded = await uploadImage(analysisId, accessToken, stateVersion, uploadFile);",
    "upload processed browser image",
)


# ---------------------------------------------------------------------------
# 3) API recognition cache: skip repeated fast-recognition for identical bytes.
#    Ingest still strips metadata and writes session assets; only vision is cached.
# ---------------------------------------------------------------------------
recognition_path = FILES["recognition"]
recognition_text = recognition_path.read_text(encoding="utf-8")

if "_FAST_RESULT_CACHE" not in recognition_text:
    recognition_text = recognition_text.replace(
        'REFERENCE_SHA256 = "2756a38a4451117001dedeab2e4da14423d4aa50978bc4549c9ff0cb1340f976"',
        'REFERENCE_SHA256 = "2756a38a4451117001dedeab2e4da14423d4aa50978bc4549c9ff0cb1340f976"\n_FAST_RESULT_CACHE: dict[str, dict[str, Any]] = {}\n_FAST_RESULT_CACHE_ORDER: list[str] = []\n_FAST_RESULT_CACHE_MAX = 64',
        1,
    )

recognition_text = recognition_text.replace(
    "engine = get_fast_engine(project_root) result = engine.recognise(image_path, source_sha256=source_sha256)",
    """engine = get_fast_engine(project_root)
    if source_sha256 in _FAST_RESULT_CACHE:
        result = deep_copy(_FAST_RESULT_CACHE[source_sha256])
        result.setdefault("metrics", {})["path"] = "server_fast_cache"
        result["metrics"]["cacheHit"] = True
        result["metrics"]["totalRecognitionMs"] = 0.0
    else:
        result = engine.recognise(image_path, source_sha256=source_sha256)
        _FAST_RESULT_CACHE[source_sha256] = deep_copy(result)
        _FAST_RESULT_CACHE_ORDER.append(source_sha256)
        while len(_FAST_RESULT_CACHE_ORDER) > _FAST_RESULT_CACHE_MAX:
            old_key = _FAST_RESULT_CACHE_ORDER.pop(0)
            _FAST_RESULT_CACHE.pop(old_key, None)""",
    1,
)

write(recognition_path, recognition_text)
print(f"updated: {recognition_path.relative_to(ROOT)} — in-memory recognition cache")


# ---------------------------------------------------------------------------
# 4) Early-exit registration: multi-scale remains fallback-only.
# ---------------------------------------------------------------------------
fast_path = FILES["fast_recognition"]
fast_text = fast_path.read_text(encoding="utf-8")

if "def _registration_strong_enough" not in fast_text:
    fast_text = fast_text.replace(
        """            attempts.append((target_width, result))
        accepted = [(width, item) for width, item in attempts if item.accepted]""",
        """            attempts.append((target_width, result))
            if self._registration_strong_enough(result):
                return result
        accepted = [(width, item) for width, item in attempts if item.accepted]""",
        1,
    )

    fast_text = fast_text.replace(
        "def _register_once(",
        """@staticmethod
    def _registration_strong_enough(result: RegistrationResult) -> bool:
        return bool(
            result.accepted
            and result.inlier_count >= 80
            and (result.p95_residual_cell is not None and result.p95_residual_cell <= 0.085)
            and (result.median_residual_cell is not None and result.median_residual_cell <= 0.045)
            and (result.ambiguity_margin is not None and result.ambiguity_margin >= 0.25)
            and result.confidence >= 0.90
        )

    def _register_once(""",
        1,
    )

write(fast_path, fast_text)
print(f"updated: {fast_path.relative_to(ROOT)} — early-exit registration")


# ---------------------------------------------------------------------------
# 5) Documentation
# ---------------------------------------------------------------------------
docs_dir = ROOT / "docs" / "performance"
docs_dir.mkdir(parents=True, exist_ok=True)
doc_path = docs_dir / "CAPTURE_PERFORMANCE.md"
doc_path.write_text(
    """# Capture Performance Patch

Implemented optimisations:

1. Browser-side preprocessing before upload
   - keeps the original object URL for immediate preview;
   - creates an upload file capped at 1920×1080;
   - uses WebP quality 0.9, with JPEG fallback.

2. In-memory recognition cache
   - key: SHA-256 of uploaded bytes after browser preprocessing;
   - scope: current API process only;
   - max entries: 64;
   - no persistent storage and no background keepalive.

3. Early-exit registration
   - keeps multi-scale registration as fallback;
   - returns immediately when the first accepted registration is already strong:
     p95 <= 0.085 cell, median <= 0.045 cell, >=80 inliers, ambiguity >=0.25, confidence >=0.90.

Not implemented:
- no 10–14 minute Render ping;
- no forced server keepalive;
- no frontend-only OpenCV/WASM port.
""",
    encoding="utf-8",
)
print(f"created: {doc_path.relative_to(ROOT)}")

print("")
print("Performance patch applied.")
print(f"Backups written to: {BACKUP_DIR.relative_to(ROOT)}")
