from __future__ import annotations

from pathlib import Path
from datetime import datetime
import re
import shutil

ROOT = Path.cwd()
BACKUP_DIR = ROOT / ".patch_backups" / f"safe_backend_perf_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

FAST = ROOT / "services/api/grougal_solver/fast_recognition.py"
if not FAST.exists():
    raise SystemExit(f"Missing expected file: {FAST}")

def backup(path: Path) -> None:
    target = BACKUP_DIR / path.relative_to(ROOT)
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        shutil.copy2(path, target)

def save(path: Path, text: str) -> None:
    backup(path)
    path.write_text(text, encoding="utf-8")

def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly 1 occurrence, found {count}")
    print(f"patched: {label}")
    return text.replace(old, new, 1)

def regex_once(text: str, pattern: str, repl: str, label: str) -> str:
    new_text, count = re.subn(pattern, repl, text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly 1 regex replacement, found {count}")
    print(f"patched: {label}")
    return new_text

text = FAST.read_text(encoding="utf-8")
original = text

# 1) Do not build fixture fingerprints by default.
#    They are useful for fixture demos/tests, but expensive and unnecessary live.
text = replace_once(
    text,
    """        self._fixture_fingerprints: list[tuple[dict[str, Any], np.ndarray]] = []
        self._build_fixture_fingerprints()
        self.initialisation_ms = _ms(started)""",
    """        self._fixture_fingerprints: list[tuple[dict[str, Any], np.ndarray]] = []
        self.fixture_fingerprints_enabled = os.getenv("GROUGAL_ENABLE_FIXTURE_FINGERPRINTS") == "1"
        if self.fixture_fingerprints_enabled:
            self._build_fixture_fingerprints()
        self.initialisation_ms = _ms(started)""",
    "make fixture fingerprint preload opt-in",
)

# 2) Match exact fixture hashes only by default; skip generic fingerprint scan live.
text = replace_once(
    text,
    """        if source_sha256 and source_sha256 in self._fixture_by_hash:
            return self._fixture_by_hash[source_sha256], 0.0, 1.0
        fingerprint = self._fingerprint(canonical)""",
    """        if source_sha256 and source_sha256 in self._fixture_by_hash:
            return self._fixture_by_hash[source_sha256], 0.0, 1.0
        if not self.fixture_fingerprints_enabled:
            return None, None, None
        fingerprint = self._fingerprint(canonical)""",
    "skip live fixture fingerprint matching",
)

# 3) Add early-exit registration.
#    Multi-scale remains as fallback, but no longer always runs every width.
if "_registration_strong_enough" not in text:
    text = replace_once(
        text,
        """            attempts.append((target_width, result))
        accepted = [(width, item) for width, item in attempts if item.accepted]""",
        """            attempts.append((target_width, result))
            if self._registration_strong_enough(result):
                return result
        accepted = [(width, item) for width, item in attempts if item.accepted]""",
        "early-exit successful registration",
    )

    text = replace_once(
        text,
        """    def _register_once(
        self,
        image: np.ndarray,""",
        """    @staticmethod
    def _registration_strong_enough(result: RegistrationResult) -> bool:
        return bool(
            result.accepted
            and result.inlier_count >= 80
            and (result.p95_residual_cell is not None and result.p95_residual_cell <= 0.085)
            and (result.median_residual_cell is not None and result.median_residual_cell <= 0.045)
            and (result.ambiguity_margin is not None and result.ambiguity_margin >= 0.25)
            and result.confidence >= 0.90
        )

    def _register_once(
        self,
        image: np.ndarray,""",
        "add strong registration predicate",
    )
else:
    print("skip: early-exit already present")

# 4) Add metrics so you can see whether fixture fingerprints were disabled.
text = replace_once(
    text,
    """"templatesReloaded": False,
            },
        }""",
    """"templatesReloaded": False,
                "fixtureFingerprintsEnabled": self.fixture_fingerprints_enabled,
                "engineInitialisationMs": self.initialisation_ms,
            },
        }""",
    "add performance metrics to successful recognition",
)

text = replace_once(
    text,
    """"templatesReloaded": False,
                },
            }""",
    """"templatesReloaded": False,
                    "fixtureFingerprintsEnabled": self.fixture_fingerprints_enabled,
                    "engineInitialisationMs": self.initialisation_ms,
                },
            }""",
    "add performance metrics to registration fallback",
)

if text != original:
    save(FAST, text)
    print("")
    print("Safe backend performance patch applied.")
    print(f"Backups written to: {BACKUP_DIR.relative_to(ROOT)}")
else:
    print("No changes needed.")
