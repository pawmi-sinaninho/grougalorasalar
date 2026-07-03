#!/usr/bin/env python3
"""
Apply the July-2026 Capture-Workflow UI cleanup to the current
pawmi-sinaninho/grougalorasalar repository.

Run from the repository root:
    python apply_capture_ui_update.py

The script intentionally changes only frontend copy/layout and README text.
It does not touch the Python API/solver path.
"""
from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path.cwd()
PAGE = ROOT / "apps" / "web" / "app" / "page.tsx"
CSS = ROOT / "apps" / "web" / "app" / "globals.css"
README = ROOT / "README.md"

HOWTO_JSX = """{!imageUrl && <div className=\"start-grid\"><section className=\"upload\"><div className=\"capture-icon\">▣</div><h2>Capture du début du tour</h2><p>Choisissez la fenêtre Dofus, puis utilisez <strong>Capturer ce tour</strong> à chaque début de tour.</p>{debug && <label>Fixture locale<input aria-label=\"Capture du combat (debug)\" type=\"file\" accept=\"image/png,image/jpeg,image/webp\" disabled={busy} onChange={event => event.target.files?.[0] && begin(event.target.files[0])} /></label>}</section><aside className=\"howto-card\" aria-label=\"Comment utiliser le solveur\"><p className=\"step\">MODE D’EMPLOI</p><h2>Comment l’utiliser</h2><ol><li><strong>Avant le combat :</strong> dans Dofus, ouvrez le menu en haut à droite avec les trois points verticaux, puis choisissez <em>Masquer tous les modules</em>.</li><li><strong>Au début de chaque tour :</strong> sélectionnez la fenêtre Dofus une seule fois si nécessaire, puis cliquez sur <em>Capturer ce tour</em>.</li><li><strong>Ensuite :</strong> exécutez les actions numérotées affichées sur l’image, terminez le tour, puis capturez le tour suivant.</li></ol></aside></div>}"""

LOADING_BANNER_JSX = """{busy && <div className=\"loading-banner\" aria-live=\"polite\"><span className=\"spinner\" aria-hidden=\"true\" /><div><strong>{data ? 'Calcul de la solution…' : 'Analyse de l’arène…'}</strong><small>{stageLabels[progress.stage] ?? 'Traitement en cours'}{debug ? ` · ${Math.round(elapsedMs || progress.elapsedMs)} ms` : ''}</small></div></div>}"""

CSS_APPEND = r'''

/* Capture-workflow cleanup — 2026-07 */
.start-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(320px, 420px);
  gap: 20px;
  align-items: stretch;
}

.capture-icon {
  width: 78px;
  height: 78px;
  display: grid;
  place-items: center;
  margin-bottom: 22px;
  border: 1px solid #bce565;
  border-radius: 20px;
  background: #1d2a20;
  color: #dff8a9;
  font-size: 2.6rem;
  font-weight: 900;
}

.howto-card {
  padding: 28px;
}

.howto-card h2 {
  margin-bottom: 18px;
}

.howto-card ol {
  margin: 0;
  padding-left: 1.35rem;
  display: grid;
  gap: 14px;
}

.howto-card li {
  color: #d6e4dc;
  line-height: 1.45;
}

.howto-card strong {
  color: #eef5f0;
}

.howto-card em {
  color: #dff8a9;
  font-style: normal;
  font-weight: 800;
}

/* The rotating banner above the combat image is now the only standard processing status. */
.analysis-strip {
  display: none !important;
}

.workspace,
.start-grid,
.board-card,
.board-image {
  min-width: 0;
}

.board-image {
  position: relative;
  width: 100%;
  overflow: hidden;
}

.board-image img {
  width: 100%;
  height: auto;
  display: block;
}

.board-image .overlay,
.overlay {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

@media (max-width: 980px) {
  .start-grid,
  .workspace {
    grid-template-columns: 1fr;
  }

  main {
    padding: 18px;
  }
}
'''


def read(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")
    return path.read_text(encoding="utf-8")


def write_if_changed(path: Path, text: str, changed: list[str]) -> None:
    old = read(path)
    if old != text:
        path.write_text(text, encoding="utf-8", newline="\n")
        changed.append(str(path.relative_to(ROOT)))


def replace_all(text: str, old: str, new: str) -> str:
    return text.replace(old, new)


def patch_page(text: str) -> str:
    # Remove the old paste listener entirely. The app now communicates only the window-capture flow.
    text = re.sub(
        r"\n\s*useEffect\(\(\) => \{\s*const paste = \(event: ClipboardEvent\) => \{.*?window\.removeEventListener\('paste', paste\);\s*\}\);\s*",
        "\n",
        text,
        flags=re.S,
    )

    # User-facing copy: remove all Ctrl+V instructions.
    replacements = {
        "Collez la capture du début du tour avec Ctrl+V. Votre action apparaît automatiquement.":
            "Capturez la fenêtre Dofus au début du tour. La solution apparaît automatiquement.",
        "Exécutez les actions, terminez le tour, puis collez la prochaine capture avec Ctrl+V.":
            "Exécutez les actions, terminez le tour, puis cliquez sur Capturer ce tour.",
        "Collez une nouvelle capture complète du début du tour.":
            "Capturez une nouvelle image complète du début du tour.",
        "Utilisez Ctrl+V.":
            "Sélectionnez la fenêtre Dofus, puis capturez le tour.",
        "Réessayez ou utilisez Ctrl+V.":
            "Réessayez après avoir sélectionné la fenêtre Dofus.",
        "capture-collee.png":
            "capture-fenetre.png",
    }
    for old, new in replacements.items():
        text = replace_all(text, old, new)

    # Replace the old initial empty-state card.
    text = re.sub(
        r"\{!imageUrl && <section className=\"upload\"><div className=\"paste-key\">Ctrl\+V</div><h2>Capture d’écran du début du tour</h2><p>Aucune saisie ni confirmation\.</p>(?P<debug>\{debug && <label>Fixture locale<input aria-label=\"Capture du combat \(debug\)\" type=\"file\" accept=\"image/png,image/jpeg,image/webp\" disabled=\{busy\} onChange=\{event => event\.target\.files\?\.\[0\] && begin\(event\.target\.files\[0\]\)\} /></label>\})?</section>\}",
        HOWTO_JSX,
        text,
        flags=re.S,
    )

    # Some current deployments already include capture controls. If they do not, this patch intentionally
    # does not invent new capture APIs. It only adds correct guidance around the existing control.

    # Ensure a single loading banner exists directly after the header. If the deployment already has one,
    # keep it but normalize the wording. Otherwise insert one.
    if 'className="loading-banner"' not in text:
        text = text.replace("</header>", f"</header>\n{LOADING_BANNER_JSX}", 1)
    else:
        text = replace_all(text, "La capture est en cours de traitement.", "Toutes les informations de calcul sont affichées ici.")

    # Remove the old status strip below the combat image.
    text = re.sub(
        r"\n\s*<div className=\"analysis-strip\" aria-live=\"polite\">.*?</div>",
        "",
        text,
        flags=re.S,
    )

    return text


def patch_css(text: str) -> str:
    # Hide old Ctrl+V visual affordance if it survives in cached markup.
    text = re.sub(r"\.paste-key\s*\{[^}]*\}\s*", "", text, flags=re.S)
    if "Capture-workflow cleanup — 2026-07" not in text:
        text = text.rstrip() + CSS_APPEND + "\n"
    return text


def patch_readme(text: str) -> str:
    text = replace_all(text, "Paste a complete screenshot from the start of the round with `Ctrl+V`.", "In Dofus, open the top-right `...` menu and choose `Masquer tous les modules` before starting the fight.")
    text = replace_all(text, "Wait for the numbered recommendation, execute it, finish the round, and paste the next screenshot.", "Choose the Dofus window once, click `Capturer ce tour` at the start of every turn, execute the numbered recommendation, finish the round, and capture the next turn.")
    text = replace_all(text, "The standard route asks for no AP, charge, pillar, glyph, confirmation, or solve-button input.", "The standard route uses the browser window-capture workflow and asks for no AP, charge, pillar, glyph, confirmation, or solve-button input.")
    text = replace_all(text, "Ctrl+V", "Capturer ce tour")
    return text


def main() -> int:
    changed: list[str] = []
    try:
        page = read(PAGE)
        css = read(CSS)
        readme = read(README)
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 2

    new_page = patch_page(page)
    new_css = patch_css(css)
    new_readme = patch_readme(readme)

    write_if_changed(PAGE, new_page, changed)
    write_if_changed(CSS, new_css, changed)
    write_if_changed(README, new_readme, changed)

    page_after = read(PAGE)
    readme_after = read(README)
    remaining_ctrlv = [name for name, text in [(str(PAGE.relative_to(ROOT)), page_after), (str(README.relative_to(ROOT)), readme_after)] if "Ctrl+V" in text]

    print("Changed files:")
    for item in changed or ["(none)"]:
        print(f" - {item}")

    if remaining_ctrlv:
        print("WARNING: Ctrl+V still appears in:")
        for item in remaining_ctrlv:
            print(f" - {item}")
        print("Check whether it is in a test/debug-only context.")
    else:
        print("OK: no Ctrl+V copy remains in page.tsx or README.md")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
