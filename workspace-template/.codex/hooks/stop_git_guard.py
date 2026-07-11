#!/usr/bin/env python3
"""Warn about unfinished Git/memory state when a Codex turn stops.

This hook never commits, pushes, blocks a user exit, or changes files.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def read_payload() -> dict[str, object]:
    try:
        raw = sys.stdin.read().strip()
        return json.loads(raw) if raw else {}
    except (json.JSONDecodeError, OSError):
        return {}


def git_output(cwd: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def main() -> int:
    payload = read_payload()
    if payload.get("stop_hook_active"):
        print(json.dumps({"continue": True}))
        return 0

    cwd_value = payload.get("cwd")
    cwd = Path(str(cwd_value)).resolve() if cwd_value else Path.cwd().resolve()
    root_text = git_output(cwd, "rev-parse", "--show-toplevel")
    if not root_text:
        print(json.dumps({"continue": True}))
        return 0

    root = Path(root_text)
    branch = git_output(root, "branch", "--show-current") or "(detached HEAD)"
    status = git_output(root, "status", "--porcelain=v1")
    warnings: list[str] = []

    if status:
        changed_count = len(status.splitlines())
        warnings.append(
            f"Рабочее дерево содержит {changed_count} незакоммиченных изменений. "
            "Перед handoff проверьте diff, обновите журнал сессии и создайте "
            "локальный смысловой commit."
        )
    if branch == "main" and status:
        warnings.append(
            "Изменения сделаны непосредственно в main. Для параллельной исследовательской работы "
            "предпочтительна ветка session/YYYYMMDD-<slug> и отдельный worktree."
        )

    if warnings:
        message = "Git handoff guard: " + " ".join(warnings) + " Push автоматически не выполняется."
        print(json.dumps({"continue": True, "systemMessage": message}, ensure_ascii=False))
    else:
        print(json.dumps({"continue": True}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
