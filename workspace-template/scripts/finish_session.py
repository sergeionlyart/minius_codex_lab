#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _utc_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=root,
        check=False,
        text=True,
        capture_output=True,
    )


def _workspace_mode(root: Path) -> str | None:
    git_root = _run(root, "git", "rev-parse", "--show-toplevel")
    initialized = _run(root, "git", "config", "--local", "--get", "minius.initialized")
    mode = _run(root, "git", "config", "--local", "--get", "minius.memoryMode")
    if (
        git_root.returncode != 0
        or Path(git_root.stdout.strip()).resolve() != root.resolve()
        or initialized.stdout.strip() != "true"
    ):
        return None
    value = mode.stdout.strip()
    return value if value in {"untracked", "local-git", "private-approved"} else None


def _find_session(root: Path, query: str) -> Path:
    sessions_root = (root / "memory/sessions").resolve()
    direct = Path(query)
    if direct.is_file():
        candidate = direct.resolve()
        if sessions_root not in candidate.parents or candidate.suffix != ".md":
            raise ValueError("Session path must be a Markdown file under memory/sessions.")
        return candidate
    if not direct.is_absolute() and (root / direct).is_file():
        candidate = (root / direct).resolve()
        if sessions_root not in candidate.parents or candidate.suffix != ".md":
            raise ValueError("Session path must be a Markdown file under memory/sessions.")
        return candidate
    candidates = sorted(path for path in sessions_root.glob("*.md") if query in path.name)
    if len(candidates) != 1:
        names = ", ".join(path.name for path in candidates) or "none"
        raise ValueError(f"Session query must resolve uniquely; matches: {names}")
    return candidates[0].resolve()


def _replace_line(text: str, label: str, value: str) -> str:
    pattern = rf"^(- \*\*{re.escape(label)}:\*\*)[ \t]*[^\r\n]*$"
    if re.search(pattern, text, flags=re.MULTILINE):
        return re.sub(pattern, rf"\1 {value}", text, flags=re.MULTILINE)
    return text


def _replace_section(text: str, heading: str, body: str) -> str:
    pattern = rf"(^## {re.escape(heading)}\n\n)(.*?)(?=\n## |\Z)"
    match = re.search(pattern, text, flags=re.MULTILINE | re.DOTALL)
    if match:
        replacement = match.group(1) + body.strip() + "\n"
        return text[: match.start()] + replacement + text[match.end() :]
    return text.rstrip() + f"\n\n## {heading}\n\n{body.strip()}\n"


def _remove_active_session(index_path: Path, session_id: str, timestamp: str) -> None:
    text = index_path.read_text(encoding="utf-8")
    text = re.sub(r"^updated_at_utc:.*$", f"updated_at_utc: {timestamp}", text, flags=re.MULTILINE)
    lines = text.splitlines()
    output: list[str] = []
    in_active = False
    active_count = 0
    for line in lines:
        if line.startswith("active_sessions:"):
            in_active = True
            output.append("active_sessions:")
            continue
        if in_active and line and not line.startswith(" "):
            in_active = False
        if in_active and line.startswith("  - "):
            if session_id in line:
                continue
            active_count += 1
        output.append(line)
    if active_count == 0:
        output = ["active_sessions: []" if line == "active_sessions:" else line for line in output]
    index_path.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")


def _update_current(
    current_path: Path,
    session_id: str,
    summary: str,
    next_action: str,
    timestamp: str,
) -> None:
    text = current_path.read_text(encoding="utf-8")
    pattern = r"(## Активные ветки/worktrees\n\n)(.*?)(\n\n## )"
    match = re.search(pattern, text, flags=re.DOTALL)
    if match:
        lines = [line for line in match.group(2).splitlines() if session_id not in line]
        body = "\n".join(line for line in lines if line.strip()).strip() or "Не установлено."
        text = text[: match.start(2)] + body + text[match.end(2) :]
    handoff = (
        f"- **Session:** `{session_id}`\n"
        f"- **Completed (UTC):** {timestamp}\n"
        f"- **Summary:** {summary}\n"
        f"- **Next action:** {next_action}"
    )
    text = _replace_section(text, "Последний handoff", handoff)
    current_path.write_text(text, encoding="utf-8", newline="\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Close a session and write a durable handoff.")
    parser.add_argument(
        "--session",
        required=True,
        help="Session ID, unique filename fragment, or path.",
    )
    parser.add_argument("--summary", required=True)
    parser.add_argument("--next-action", required=True)
    parser.add_argument("--risks", default="Нет новых; проверить журнал и open questions.")
    parser.add_argument("--tests", default="Не указаны.")
    parser.add_argument(
        "--no-current-update",
        action="store_true",
        help="Do not promote the latest handoff into memory/CURRENT.md.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = _root()
    memory_mode = _workspace_mode(root)
    if memory_mode is None:
        print(
            "ERROR: initialize this release with scripts/init_workspace.py first.",
            file=sys.stderr,
        )
        return 2
    try:
        session_path = _find_session(root, args.session)
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    if root not in session_path.parents:
        print("ERROR: session file is outside the workspace.", file=sys.stderr)
        return 2

    timestamp = _utc_timestamp()
    status = _run(root, "git", "status", "--short", "--branch")
    diff_stat = _run(root, "git", "diff", "--stat")
    cached_stat = _run(root, "git", "diff", "--cached", "--stat")
    git_snapshot = "\n".join(
        [
            "```text",
            (status.stdout or status.stderr).strip() or "git status unavailable",
            "",
            "Unstaged diff stat:",
            diff_stat.stdout.strip() or "none",
            "",
            "Staged diff stat:",
            cached_stat.stdout.strip() or "none",
            "```",
        ]
    )

    try:
        text = session_path.read_text(encoding="utf-8")
        session_id_match = re.search(r"^# Session:\s*(.+)$", text, flags=re.MULTILINE)
        session_id = session_id_match.group(1).strip() if session_id_match else session_path.stem
        text = _replace_line(text, "Ended (UTC)", timestamp)
        text = _replace_section(text, "Work performed", args.summary)
        text = _replace_section(text, "Tests/validation", f"{args.tests}\n\n{git_snapshot}")
        text = _replace_section(text, "Risks and unresolved questions", args.risks)
        text = _replace_section(text, "Handoff / next action", args.next_action)
        session_path.write_text(text, encoding="utf-8", newline="\n")
        _remove_active_session(root / "memory/index.yaml", session_id, timestamp)
        if not args.no_current_update:
            _update_current(
                root / "memory/CURRENT.md",
                session_id,
                args.summary.strip(),
                args.next_action.strip(),
                timestamp,
            )
    except OSError as error:
        print(f"ERROR: unable to update session memory: {error}", file=sys.stderr)
        return 2

    print(f"closed session: {session_id}")
    print(f"session log: {session_path}")
    print("No commit or push was executed.")
    if memory_mode == "untracked":
        print("Git mode: untracked; session handoff remains local and ignored.")
    else:
        print("After classification review, create only applicable explicit commits:")
        print("  source:/research:/evidence:/draft:/review:/artifact: <work package>")
        print(f"  memory: close session {session_id}")
        print("Review git status, stage named paths, and run tests before committing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
