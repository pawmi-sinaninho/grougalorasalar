import type { FrontendCaptureInput } from "./types";

export interface CanvasImage {
  canvas: HTMLCanvasElement | OffscreenCanvas;
  ctx: CanvasRenderingContext2D | OffscreenCanvasRenderingContext2D;
  width: number;
  height: number;
}

export async function inputToImageBitmap(input: FrontendCaptureInput): Promise<ImageBitmap> {
  if (input.imageBitmap) return input.imageBitmap;

  if (input.blob) {
    return await createImageBitmap(input.blob);
  }

  if (input.file) {
    return await createImageBitmap(input.file);
  }

  if (input.dataUrl) {
    const response = await fetch(input.dataUrl);
    const blob = await response.blob();
    return await createImageBitmap(blob);
  }

  throw new Error("No screenshot input was provided.");
}

export function imageBitmapToCanvas(bitmap: ImageBitmap): CanvasImage {
  const hasOffscreen = typeof OffscreenCanvas !== "undefined";
  const canvas = hasOffscreen
    ? new OffscreenCanvas(bitmap.width, bitmap.height)
    : Object.assign(document.createElement("canvas"), { width: bitmap.width, height: bitmap.height });

  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  if (!ctx) throw new Error("Could not create 2D canvas context.");
  ctx.drawImage(bitmap, 0, 0);

  return { canvas, ctx, width: bitmap.width, height: bitmap.height };
}

export function getImageData(canvasImage: CanvasImage): ImageData {
  return canvasImage.ctx.getImageData(0, 0, canvasImage.width, canvasImage.height);
}
