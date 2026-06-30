from __future__ import annotations

import io
from pathlib import Path

from PIL import Image

from grougal_solver.image_ingest import UploadRejected, normalise_image
from grougal_solver.session_store import SessionStore


def test_small_image_is_rejected(tmp_path: Path) -> None:
    image = Image.new("RGB", (640, 480))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    try:
        normalise_image(buffer.getvalue(), tmp_path)
    except UploadRejected as exc:
        assert exc.code == "API-FILE-DIMENSIONS"
    else:
        raise AssertionError("small image accepted")


def test_delete_removes_every_session_byte(tmp_path: Path) -> None:
    store = SessionStore(tmp_path / "sessions")
    document, token = store.create("fr")
    asset = store.asset_path(document["analysisId"], "normalised.png")
    asset.parent.mkdir(parents=True, exist_ok=True)
    asset.write_bytes(b"secret-image")
    store.delete(document["analysisId"], token)
    assert not (tmp_path / "sessions" / document["analysisId"]).exists()
