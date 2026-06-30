from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageStat

from .util import SPELLS


def recognise_spell_bar(image_path: Path) -> dict[str, Any] | None:
    """Read the four-slot spell bar without asking the player to confirm it.

    The verified regression crop uses disabled darkening for zero charges. Exact
    positive counts are intentionally left unknown unless a later calibrated
    numeric cue can support them; availability itself is still authoritative.
    """
    with Image.open(image_path) as source:
        image = source.convert("RGB")
    width, height = image.size
    if width / height > 4.0 or height > 220:
        image = image.crop((round(width * 0.378), round(height * 0.875), round(width * 0.472), round(height * 0.965)))
        width, height = image.size
    if width < 150 or height < 55 or width / height < 1.8:
        return None

    states: dict[str, dict[str, Any]] = {}
    luminances: list[float] = []
    for index, spell in enumerate(SPELLS):
        left = round(width * (index + 0.20) / 4)
        right = round(width * (index + 0.80) / 4)
        top = round(height * 0.18)
        bottom = round(height * 0.78)
        luminance = float(ImageStat.Stat(image.crop((left, top, right, bottom))).mean[0])
        luminances.append(luminance)
        available = luminance >= 75.0
        states[spell] = {
            "availability": "available" if available else "unavailable",
            "value": None if available else 0,
            "confirmed": True,
            "confidence": 0.98,
        }
    return {"spells": states, "slotLuminance": luminances, "confidence": 0.98}
