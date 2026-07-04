#!/usr/bin/env python3
# Hotfix for apply_recommendation_perf_patch_v2.py side effects.
#
# Fixes:
# 1) services/api/grougal_solver/solver.py:
#    - removes misplaced "from .solver_perf import solver_memoize"
#    - reinserts it safely after the module docstring and __future__ imports
#
# 2) apps/web/lib/perfFetch.ts or apps/web/src/lib/perfFetch.ts:
#    - fixes FormDataEntryValue narrowing so TypeScript no longer reads value.size on strings
#
# Run from repository root:
#     py repair_perf_patch_v2.py

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path.cwd()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def skip_module_docstring(lines: list[str], i: int) -> int:
    n = len(lines)

    # shebang / encoding / leading comments / blanks
    while i < n and (
        lines[i].strip() == ""
        or lines[i].startswith("#!")
        or re.match(r"#.*coding[:=]\s*[-\w.]+", lines[i])
    ):
        i += 1

    if i >= n:
        return i

    stripped = lines[i].lstrip()
    quote = None
    triple_double = '"' * 3
    triple_single = "'" * 3

    if stripped.startswith(triple_double):
        quote = triple_double
    elif stripped.startswith(triple_single):
        quote = triple_single

    if not quote:
        return i

    # One-line docstring
    rest = stripped[len(quote):]
    if quote in rest:
        return i + 1

    i += 1
    while i < n:
        if quote in lines[i]:
            return i + 1
        i += 1
    return i


def skip_future_imports(lines: list[str], i: int) -> int:
    n = len(lines)

    while i < n and lines[i].strip() == "":
        i += 1

    while i < n and lines[i].lstrip().startswith("from __future__ import "):
        # handle rare parenthesized/multiline future import
        paren_balance = lines[i].count("(") - lines[i].count(")")
        i += 1
        while paren_balance > 0 and i < n:
            paren_balance += lines[i].count("(") - lines[i].count(")")
            i += 1
        while i < n and lines[i].strip() == "":
            i += 1

    return i


def repair_solver_import() -> bool:
    path = ROOT / "services" / "api" / "grougal_solver" / "solver.py"
    if not path.exists():
        print(f"[skip] missing {path}")
        return False

    original = read_text(path)
    lines = original.splitlines(keepends=True)

    # Remove every existing misplaced import line.
    import_line_pattern = re.compile(r"^\s*from\s+\.solver_perf\s+import\s+solver_memoize\s*(?:#.*)?\r?\n?$")
    cleaned_lines = [line for line in lines if not import_line_pattern.match(line)]

    insert_at = skip_future_imports(cleaned_lines, skip_module_docstring(cleaned_lines, 0))
    cleaned_lines.insert(insert_at, "from .solver_perf import solver_memoize\n")

    fixed = "".join(cleaned_lines)
    if fixed != original:
        write_text(path, fixed)
        print(f"[fixed] safe solver_memoize import in {path}")
        return True

    print(f"[ok] solver_memoize import already safe in {path}")
    return False


def repair_perf_fetch() -> bool:
    candidates = [
        ROOT / "apps" / "web" / "lib" / "perfFetch.ts",
        ROOT / "apps" / "web" / "src" / "lib" / "perfFetch.ts",
    ]
    changed = False

    for path in candidates:
        if not path.exists():
            continue

        original = read_text(path)
        text = original

        # Exact broken one-liner from the generated patch.
        broken = 'body.forEach((value, key) => pairs.push(`${key}=${typeof value === "string" ? value : value.name}:${value.size}`));'
        fixed = '''body.forEach((value, key) => {
      if (typeof value === "string") {
        pairs.push(`${key}=${value}`);
      } else {
        pairs.push(`${key}=${value.name}:${value.size}`);
      }
    });'''
        text = text.replace(broken, fixed)

        # More tolerant regex variant, in case formatting changed slightly.
        text = re.sub(
            r'''body\.forEach\(\(value,\s*key\)\s*=>\s*pairs\.push\(`\$\{key\}=\$\{typeof value === ["']string["'] \? value : value\.name\}:\$\{value\.size\}`\)\);''',
            fixed,
            text,
        )

        if text != original:
            write_text(path, text)
            print(f"[fixed] FormDataEntryValue narrowing in {path}")
            changed = True
        else:
            print(f"[ok/skip] no broken FormData line found in {path}")

    if not any(path.exists() for path in candidates):
        print("[skip] no perfFetch.ts found under apps/web/lib or apps/web/src/lib")

    return changed


def run_check(cmd: list[str], cwd: Path) -> None:
    try:
        print(f"[check] {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True)
        if result.returncode == 0:
            print("[check-ok]")
        else:
            print("[check-failed]")
            if result.stdout:
                print(result.stdout[-4000:])
            if result.stderr:
                print(result.stderr[-4000:])
    except Exception as exc:
        print(f"[check-skip] {cmd}: {exc}")


def main() -> int:
    expected = ROOT / "services" / "api" / "grougal_solver"
    if not expected.exists():
        print("[error] Run this from the repository root. Expected services/api/grougal_solver")
        return 2

    repair_solver_import()
    repair_perf_fetch()

    # Lightweight syntax check for the repaired Python file.
    solver = ROOT / "services" / "api" / "grougal_solver" / "solver.py"
    if solver.exists():
        run_check([sys.executable, "-m", "py_compile", str(solver)], ROOT)

    print("\nNext commands:")
    print("  cd services\\api")
    print("  python -m pytest -q")
    print("  cd ..\\..\\apps\\web")
    print("  npm run typecheck")
    print("  npm run build")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
