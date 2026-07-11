#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

SLUG_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
MATTER_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}")


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _run(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=root,
        check=check,
        text=True,
        capture_output=True,
    )


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def _git_root(root: Path) -> Path | None:
    result = _run(root, "git", "rev-parse", "--show-toplevel", check=False)
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip()).resolve()


def _current_branch(root: Path) -> str:
    result = _run(root, "git", "branch", "--show-current", check=False)
    return result.stdout.strip() or "DETACHED"


def _is_clean(root: Path) -> bool:
    result = _run(root, "git", "status", "--porcelain", check=False)
    return result.returncode == 0 and not result.stdout.strip()


def _branch_exists(root: Path, branch: str) -> bool:
    result = _run(
        root,
        "git",
        "show-ref",
        "--verify",
        "--quiet",
        f"refs/heads/{branch}",
        check=False,
    )
    return result.returncode == 0


def _matter_classification(matter_file: Path) -> str | None:
    if not matter_file.is_file():
        return None
    text = matter_file.read_text(encoding="utf-8")
    match = re.search(r"^- \*\*Data classification:\*\*\s*(\S+)", text, flags=re.MULTILINE)
    return match.group(1) if match else None


def _replace_template(path: Path, values: dict[str, str]) -> None:
    text = path.read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace(f"{{{{{key}}}}}", value)
    path.write_text(text, encoding="utf-8", newline="\n")


def _yaml_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _add_active_session(index_path: Path, record: str, timestamp: str) -> None:
    text = index_path.read_text(encoding="utf-8")
    text = re.sub(r"^updated_at_utc:.*$", f"updated_at_utc: {timestamp}", text, flags=re.MULTILINE)
    if re.search(r"^active_sessions:\s*\[\]\s*$", text, flags=re.MULTILINE):
        text = re.sub(
            r"^active_sessions:\s*\[\]\s*$",
            f"active_sessions:\n  - {_yaml_quote(record)}",
            text,
            flags=re.MULTILINE,
        )
    else:
        match = re.search(r"^active_sessions:\s*$", text, flags=re.MULTILINE)
        if not match:
            text += f"\nactive_sessions:\n  - {_yaml_quote(record)}\n"
        elif record not in text:
            insert_at = match.end()
            text = text[:insert_at] + f"\n  - {_yaml_quote(record)}" + text[insert_at:]
    index_path.write_text(text, encoding="utf-8", newline="\n")


def _add_current_session(current_path: Path, entry: str) -> None:
    text = current_path.read_text(encoding="utf-8")
    pattern = r"(## Активные ветки/worktrees\n\n)(.*?)(\n\n## )"
    match = re.search(pattern, text, flags=re.DOTALL)
    if not match:
        text += f"\n\n## Активные ветки/worktrees\n\n{entry}\n"
    else:
        body = match.group(2).strip()
        if body == "Не установлено.":
            body = entry
        elif entry not in body:
            body = f"{body}\n{entry}"
        text = text[: match.start(2)] + body + text[match.end(2) :]
    current_path.write_text(text, encoding="utf-8", newline="\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start a traceable legal research session.")
    parser.add_argument(
        "--slug",
        required=True,
        help="Lowercase session slug, for example case-law-review.",
    )
    parser.add_argument("--matter", required=True, dest="matter_id")
    parser.add_argument("--objective", default="Уточнить цель в session log.")
    parser.add_argument(
        "--classification",
        choices=("PUBLIC", "INTERNAL", "PERSONAL", "RESTRICTED"),
        help="Defaults to the matter classification, then INTERNAL.",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--create-branch",
        action="store_true",
        help="Create and switch the current clean worktree to session/YYYYMMDD-<slug>.",
    )
    group.add_argument(
        "--worktree",
        type=Path,
        help="Create a separate Git worktree and branch at this path.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    slug = args.slug.strip().lower()
    matter_id = args.matter_id.strip()
    if not SLUG_PATTERN.fullmatch(slug):
        print("ERROR: slug must match [a-z0-9][a-z0-9-]{0,63}.", file=sys.stderr)
        return 2
    if not MATTER_PATTERN.fullmatch(matter_id):
        print("ERROR: invalid matter ID.", file=sys.stderr)
        return 2

    original_root = _root()
    git_root = _git_root(original_root)
    if git_root is None or git_root != original_root:
        print("ERROR: run from a Git-initialized workspace root.", file=sys.stderr)
        return 2
    matter_file = original_root / "matters" / matter_id / "MATTER.md"
    if not matter_file.is_file():
        print(f"ERROR: matter not found: {matter_file}", file=sys.stderr)
        return 2

    now = _utc_now()
    date_token = now.strftime("%Y%m%d")
    timestamp = now.isoformat().replace("+00:00", "Z")
    session_id = f"{now.strftime('%Y%m%dT%H%M%SZ')}--{slug}"
    branch = f"session/{date_token}-{slug}"
    work_root = original_root

    try:
        if args.create_branch:
            if not _is_clean(original_root):
                print(
                    "ERROR: current worktree is not clean. Commit the initialized "
                    "matter or use a new worktree from a committed base.",
                    file=sys.stderr,
                )
                return 1
            if _branch_exists(original_root, branch):
                print(f"ERROR: branch already exists: {branch}", file=sys.stderr)
                return 1
            _run(original_root, "git", "switch", "-c", branch)
        elif args.worktree:
            if not _is_clean(original_root):
                print(
                    "ERROR: source worktree is not clean; a new worktree would omit "
                    "uncommitted state.",
                    file=sys.stderr,
                )
                return 1
            tracked = _run(
                original_root,
                "git",
                "ls-files",
                "--error-unmatch",
                f"matters/{matter_id}/MATTER.md",
                check=False,
            )
            if tracked.returncode != 0:
                print(
                    "ERROR: matter is not committed. Commit it before creating a "
                    "parallel worktree.",
                    file=sys.stderr,
                )
                return 1
            if _branch_exists(original_root, branch):
                print(f"ERROR: branch already exists: {branch}", file=sys.stderr)
                return 1
            target = args.worktree.expanduser().resolve()
            if target.exists():
                print(f"ERROR: worktree target already exists: {target}", file=sys.stderr)
                return 1
            _run(original_root, "git", "worktree", "add", "-b", branch, str(target), "HEAD")
            work_root = target
        else:
            branch = _current_branch(original_root)
    except (OSError, subprocess.CalledProcessError) as error:
        details = (
            error.stderr.strip() if isinstance(error, subprocess.CalledProcessError) else str(error)
        )
        print(f"ERROR: unable to prepare Git session: {details}", file=sys.stderr)
        return 2

    classification = (
        args.classification
        or _matter_classification(work_root / "matters" / matter_id / "MATTER.md")
        or "INTERNAL"
    )
    session_path = work_root / "memory/sessions" / f"{session_id}.md"
    template_path = work_root / "memory/templates/session.md"
    try:
        session_path.parent.mkdir(parents=True, exist_ok=True)
        session_path.write_text(template_path.read_text(encoding="utf-8"), encoding="utf-8")
        _replace_template(
            session_path,
            {
                "SESSION_ID": session_id,
                "STARTED_AT": timestamp,
                "BRANCH": branch,
                "WORKTREE": str(work_root),
                "MATTER_ID": matter_id,
                "CLASSIFICATION": classification,
                "OBJECTIVE": args.objective.strip(),
            },
        )
        relative_session = session_path.relative_to(work_root).as_posix()
        record = f"{session_id}|{branch}|{matter_id}|{relative_session}"
        _add_active_session(work_root / "memory/index.yaml", record, timestamp)
        current_entry = f"- `{session_id}` — `{branch}` — `{work_root}` — matter `{matter_id}`"
        _add_current_session(work_root / "memory/CURRENT.md", current_entry)
    except OSError as error:
        print(f"ERROR: unable to write session memory: {error}", file=sys.stderr)
        return 2

    print(f"session: {session_id}")
    print(f"branch: {branch}")
    print(f"worktree: {work_root}")
    print(f"session log: {session_path}")
    print(f"classification: {classification}")
    if branch in {"main", "master", "DETACHED"}:
        print("WARNING: session is not isolated on a session/* branch.")
    print(f"recommended first commit: memory: start session {slug}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
