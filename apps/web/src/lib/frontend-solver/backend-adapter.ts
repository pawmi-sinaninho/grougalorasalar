import { createStageTimer } from "./timing";
import type { FrontendCaptureInput, FrontendSolveResult } from "./types";

export interface BackendSolveOptions {
  endpoint?: string;
  fieldName?: string;
  extraFormFields?: Record<string, string>;
  headers?: Record<string, string>;
}

async function inputToBlob(input: FrontendCaptureInput): Promise<Blob> {
  if (input.blob) return input.blob;
  if (input.file) return input.file;

  if (input.dataUrl) {
    const response = await fetch(input.dataUrl);
    return await response.blob();
  }

  if (input.imageBitmap) {
    const canvas = document.createElement("canvas");
    canvas.width = input.imageBitmap.width;
    canvas.height = input.imageBitmap.height;
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("Could not create canvas for backend fallback.");
    ctx.drawImage(input.imageBitmap, 0, 0);
    return await new Promise<Blob>((resolve, reject) => {
      canvas.toBlob((blob) => {
        if (blob) resolve(blob);
        else reject(new Error("Could not convert canvas to blob."));
      }, "image/png");
    });
  }

  throw new Error("No screenshot input was provided for backend fallback.");
}

function getDefaultBackendEndpoint(): string | undefined {
  return (
    process.env.NEXT_PUBLIC_SOLVER_API_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    process.env.NEXT_PUBLIC_BACKEND_URL ||
    undefined
  );
}

function normalizeBackendResponse(raw: unknown, timings_ms: FrontendSolveResult["timings_ms"]): FrontendSolveResult {
  const rawRecord = raw && typeof raw === "object" ? (raw as Record<string, unknown>) : {};
  const ok = Boolean(rawRecord.ok ?? rawRecord.success ?? rawRecord.solution ?? rawRecord.actions);

  return {
    ok,
    source: "backend",
    status: ok ? "solved" : "warning",
    message: typeof rawRecord.message === "string" ? rawRecord.message : undefined,
    actions: Array.isArray(rawRecord.actions) ? (rawRecord.actions as FrontendSolveResult["actions"]) : undefined,
    warnings: [
      {
        code: "backend_fallback_used",
        message: "Legacy backend fallback was used. This path is not the frontend-only target architecture.",
      },
    ],
    debug: {
      notes: ["Raw backend response is available in result.raw."],
    },
    timings_ms,
    raw,
  };
}

export async function solveScreenshotBackend(
  input: FrontendCaptureInput,
  options: BackendSolveOptions = {},
): Promise<FrontendSolveResult> {
  const timer = createStageTimer();
  const endpoint = options.endpoint ?? getDefaultBackendEndpoint();

  if (!endpoint) {
    return {
      ok: false,
      source: "backend",
      status: "rejected",
      message: "Backend endpoint is not configured. Set NEXT_PUBLIC_SOLVER_API_URL/NEXT_PUBLIC_API_URL/NEXT_PUBLIC_BACKEND_URL or stay in frontend mode.",
      warnings: [],
      debug: { reason: "unknown" },
      timings_ms: timer.finish(),
    };
  }

  try {
    const blob = await timer.measureAsync("backend_prepare_ms", () => inputToBlob(input));
    const formData = new FormData();
    formData.append(options.fieldName ?? "file", blob, "capture.png");

    for (const [key, value] of Object.entries(options.extraFormFields ?? {})) {
      formData.append(key, value);
    }

    const response = await timer.measureAsync("backend_fetch_ms", () =>
      fetch(endpoint, {
        method: "POST",
        body: formData,
        headers: options.headers,
      }),
    );

    const contentType = response.headers.get("content-type") ?? "";
    const raw = contentType.includes("application/json") ? await response.json() : await response.text();
    const timings = timer.finish();

    if (!response.ok) {
      return {
        ok: false,
        source: "backend",
        status: "rejected",
        message: `Backend request failed with HTTP ${response.status}.`,
        warnings: [
          {
            code: "backend_fallback_used",
            message: "Legacy backend fallback failed.",
          },
        ],
        debug: { reason: "unknown" },
        timings_ms: timings,
        raw,
      };
    }

    return normalizeBackendResponse(raw, timings);
  } catch (error) {
    return {
      ok: false,
      source: "backend",
      status: "rejected",
      message: error instanceof Error ? error.message : "Unknown backend fallback error.",
      warnings: [
        {
          code: "backend_fallback_used",
          message: "Legacy backend fallback threw an exception.",
        },
      ],
      debug: { reason: "unknown" },
      timings_ms: timer.finish(),
    };
  }
}
