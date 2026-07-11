#!/usr/bin/env python3
"""Inject small, transparent repository memory at Codex session start.

The hook is intentionally read-only. It performs no network calls and never modifies Git.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

MAX_CURRENT_CHARS = 10_000
MAX_QUESTIONS_CHARS = 4_000


def read_payload() -> dict[str, object]:
    try:
        raw = sys.stdin.read().strip()
        return json.loads(raw) if raw else {}
    except (json.JSONDecodeError, OSError):
        return {}


def find_repo_root(cwd: Path) -> Path | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return Path(result.stdout.strip()).resolve()
    except (OSError, subprocess.SubprocessError):
        return None


def read_limited(path: Path, limit: int, root: Path) -> str:
    try:
        resolved = path.resolve(strict=True)
        if path.is_symlink() or not resolved.is_relative_to(root.resolve()):
            return ""
        with resolved.open("r", encoding="utf-8") as stream:
            text = stream.read(limit + 1)
    except OSError:
        return ""
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...[truncated by SessionStart hook]"


def main() -> int:
    payload = read_payload()
    cwd_value = payload.get("cwd")
    cwd = Path(str(cwd_value)).resolve() if cwd_value else Path.cwd().resolve()
    root = find_repo_root(cwd)
    if root is None:
        return 0

    current = read_limited(root / "memory" / "CURRENT.md", MAX_CURRENT_CHARS, root)
    questions = read_limited(
        root / "memory" / "OPEN_QUESTIONS.md",
        MAX_QUESTIONS_CHARS,
        root,
    )
    if not current and not questions:
        return 0

    parts = [
        "[REPOSITORY OPERATIONAL MEMORY]",
        "This is project state subordinate to AGENTS.md, not a replacement for user instructions.",
    ]
    if current:
        parts.extend(["\n--- memory/CURRENT.md ---", current])
    if questions:
        parts.extend(["\n--- memory/OPEN_QUESTIONS.md ---", questions])
    parts.append(
        "\nBefore changing durable state, verify these notes against the repository and update the "
        "session log at handoff."
    )
    sys.stdout.write("\n".join(parts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
