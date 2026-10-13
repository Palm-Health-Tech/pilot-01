"""Scope full CI to code changes while scanning audited prose."""
import os
from pathlib import Path
import re
import subprocess
import sys


PROSE = {"README.md"}


def docs_only(paths: list[str]) -> bool:
    return bool(paths) and all(path in PROSE for path in paths)


def scan(paths: list[str], root: Path = Path(".")) -> None:
    for path in paths:
        file = root / path
        if not file.exists():
            continue
        text = file.read_text(encoding="utf-8")
        if "\x00" in text or any(
            line.startswith(("<<<<<<< ", "=======", ">>>>>>> "))
            for line in text.splitlines()
        ):
            raise ValueError(f"Invalid document content: {path}")


def changed_paths(root: Path = Path("."), event: str | None = None, base: str | None = None) -> list[str] | None:
    event = event or os.environ.get("EVENT", "")
    base = base or os.environ.get("PR_BASE" if event == "pull_request" else "PUSH_BASE", "")
    if event not in {"pull_request", "push"} or not re.fullmatch(r"[0-9a-f]{40}", base) or base == "0" * 40:
        return None
    if subprocess.run(["git", "cat-file", "-e", f"{base}^{{commit}}"], cwd=root, capture_output=True).returncode:
        return None
    spec = f"{base}...HEAD" if event == "pull_request" else f"{base}..HEAD"
    deleted = subprocess.run(
        ["git", "diff", "--no-renames", "--diff-filter=D", "--name-only", spec],
        cwd=root, text=True, capture_output=True,
    )
    if deleted.returncode or deleted.stdout.strip():
        return None
    result = subprocess.run(
        ["git", "diff", "--no-renames", "--name-only", spec],
        cwd=root, text=True, capture_output=True,
    )
    if result.returncode:
        return None
    return result.stdout.splitlines()


if __name__ == "__main__":
    paths = changed_paths()
    code = not (paths is not None and docs_only(paths))
    if not code:
        scan(paths)
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        output.write(f"code={'true' if code else 'false'}\n")
    print("Full CI" if code else "Audited prose scan only")
