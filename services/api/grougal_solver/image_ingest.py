from __future__ import annotations

import hashlib
import io
import time
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps, UnidentifiedImageError


class UploadRejected(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def normalise_image(raw: bytes, destination: Path) -> dict[str, Any]:
    total_started = time.perf_counter()
    if len(raw) > 30 * 1024 * 1024:
        raise UploadRejected("API-FILE-TOO-LARGE", "Upload exceeds 30 MiB")

    decode_started = time.perf_counter()
    try:
        image = Image.open(io.BytesIO(raw))
        source_format = image.format
        image.load()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise UploadRejected("API-FILE-DECODE", "Image cannot be decoded") from exc
    decode_ms = _ms(decode_started)

    if getattr(image, "is_animated", False):
        raise UploadRejected("API-FILE-ANIMATED", "Animated images are unsupported")
    if source_format not in {"PNG", "JPEG", "WEBP"}:
        raise UploadRejected("API-FILE-FORMAT", "Only PNG, JPEG and WebP are supported")
    width, height = image.size
    if width < 1280 or height < 720:
        raise UploadRejected("API-FILE-DIMENSIONS", "Minimum dimensions are 1280×720")
    if width * height > 33_200_000:
        raise UploadRejected("API-FILE-PIXELS", "Image exceeds the pixel limit")

    orient_started = time.perf_counter()
    image = ImageOps.exif_transpose(image).convert("RGB")
    orient_ms = _ms(orient_started)
    destination.mkdir(parents=True, exist_ok=True)

    working_started = time.perf_counter()
    working_image = image.copy()
    working_image.thumbnail((1280, 900), Image.Resampling.BILINEAR)
    working = destination / "working.webp"
    working_image.save(working, format="WEBP", quality=86, method=2)
    working_ms = _ms(working_started)

    thumbnail_started = time.perf_counter()
    thumbnail_image = working_image.copy()
    thumbnail_image.thumbnail((960, 540), Image.Resampling.BILINEAR)
    thumbnail = destination / "thumbnail.webp"
    thumbnail_image.save(thumbnail, format="WEBP", quality=80, method=2)
    thumbnail_ms = _ms(thumbnail_started)

    normalise_started = time.perf_counter()
    normalised = destination / "normalised.png"
    # Re-encoding strips metadata. compress_level=1 avoids the previous multi-second
    # optimisation pass while retaining a lossless annotated-output source.
    image.save(normalised, format="PNG", compress_level=1)
    normalise_ms = _ms(normalise_started)

    return {
        "width": image.width,
        "height": image.height,
        "workingWidth": working_image.width,
        "workingHeight": working_image.height,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "normalised": str(normalised),
        "working": str(working),
        "thumbnail": str(thumbnail),
        "metrics": {
            "decodeMs": decode_ms,
            "orientationAndRgbMs": orient_ms,
            "workingCopyMs": working_ms,
            "thumbnailMs": thumbnail_ms,
            "safeNormalisedWriteMs": normalise_ms,
            "totalIngestMs": _ms(total_started),
        },
    }


def _ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000.0, 3)
