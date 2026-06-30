from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from .arena import project_cell, reference_transform


SPELL_LABEL = {
    "indecision": "I",
    "reflection": "R",
    "repulsion": "J",
    "attraction": "A",
}


def render_annotated(
    project_root: Path,
    source: Path,
    destination: Path,
    turn_state: dict[str, Any],
    recommendation: dict[str, Any] | None,
    *,
    registration: dict[str, Any] | None = None,
) -> None:
    image = Image.open(source).convert("RGB")
    draw = ImageDraw.Draw(image)
    transform = reference_transform(project_root)
    font = ImageFont.load_default(size=max(14, image.width // 100))
    small = ImageFont.load_default(size=max(11, image.width // 140))

    def project(cell: dict[str, int]) -> tuple[float, float]:
        if registration and registration.get("originImage") and registration.get("basisXImage") and registration.get("basisYImage"):
            origin = registration["originImage"]
            basis_x = registration["basisXImage"]
            basis_y = registration["basisYImage"]
            return (
                origin["x"] + cell["x"] * basis_x["x"] + cell["y"] * basis_y["x"],
                origin["y"] + cell["x"] * basis_x["y"] + cell["y"] * basis_y["y"],
            )
        return project_cell(transform, cell, image.size)

    for pillar in turn_state.get("pillars", []):
        x, y = project(pillar["cell"])
        radius = max(10, image.width // 110)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), outline="white", width=max(2, image.width // 800))
        draw.text((x - radius / 2, y - radius / 2), SPELL_LABEL.get(pillar["spellType"], "?"), font=small, fill="white")

    player = turn_state.get("player", {}).get("current")
    if player:
        x, y = project(player)
        size = max(13, image.width // 90)
        draw.polygon([(x, y - size), (x + size, y), (x, y + size), (x - size, y)], outline="cyan", width=max(3, image.width // 650))

    if recommendation:
        previous = player
        for action in recommendation.get("actions", []):
            target = action.get("targetCell")
            if target:
                tx, ty = project(target)
                radius = max(16, image.width // 75)
                draw.ellipse((tx - radius, ty - radius, tx + radius, ty + radius), outline="yellow", width=max(4, image.width // 500))
                draw.text((tx - radius / 3, ty - radius / 2), str(action["order"]), font=font, fill="yellow")
            destination_cell = action.get("destinationCell")
            if previous and destination_cell:
                x1, y1 = project(previous)
                x2, y2 = project(destination_cell)
                draw.line((x1, y1, x2, y2), fill="yellow", width=max(3, image.width // 600))
                previous = destination_cell
        final = recommendation.get("expected", {}).get("finalCell")
        if final:
            fx, fy = project(final)
            radius = max(18, image.width // 65)
            draw.ellipse((fx - radius, fy - radius, fx + radius, fy + radius), outline="lime", width=max(4, image.width // 450))

    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, format="PNG", compress_level=1)
