export function getFirstImageFileFromClipboardEvent(event: ClipboardEvent): File | null {
  const items = event.clipboardData?.items;
  if (!items) return null;

  for (const item of Array.from(items)) {
    if (!item.type.startsWith("image/")) continue;
    const file = item.getAsFile();
    if (file) return file;
  }

  return null;
}

export function getFirstImageFileFromDragEvent(event: DragEvent): File | null {
  const files = event.dataTransfer?.files;
  if (!files?.length) return null;

  for (const file of Array.from(files)) {
    if (file.type.startsWith("image/")) return file;
  }

  return null;
}

export function isImageFile(file: File | Blob | null | undefined): boolean {
  return Boolean(file?.type?.startsWith("image/"));
}
