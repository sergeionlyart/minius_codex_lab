#!/usr/bin/env python3
"""Initialize a pristine release workspace as a safe standalone Git repository."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

MEMORY_MODES = ("untracked", "local-git", "private-approved")
MUTABLE_UNTRACKED_PATHS = {
    "memory/CURRENT.md",
    "memory/DECISIONS.md",
    "memory/OPEN_QUESTIONS.md",
    "memory/index.yaml",
}
BRANCH_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,127}")
BEGIN_MEMORY_MODE = "# BEGIN MINIUS MEMORY MODE"
END_MEMORY_MODE = "# END MINIUS MEMORY MODE"


class InitializationError(RuntimeError):
    """Raised when initialization cannot continue safely."""


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _run(
    root: Path,
    *args: str,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            args,
            cwd=root,
            check=False,
            text=True,
            capture_output=True,
            timeout=120,
            env=env,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise InitializationError(f"Cannot run {args[0]!r}: {error}") from error


def _require_success(
    completed: subprocess.CompletedProcess[str],
    label: str,
) -> None:
    if completed.returncode == 0:
        return
    details = completed.stderr.strip() or completed.stdout.strip() or "no diagnostic output"
    raise InitializationError(f"{label} failed: {details}")


def _git_root(root: Path) -> Path | None:
    completed = _run(root, "git", "rev-parse", "--show-toplevel")
    if completed.returncode != 0 or not completed.stdout.strip():
        return None
    return Path(completed.stdout.strip()).resolve()


def _has_head(root: Path) -> bool:
    return _run(root, "git", "rev-parse", "--verify", "HEAD").returncode == 0


def _config(root: Path, key: str) -> str:
    completed = _run(root, "git", "config", "--local", "--get", key)
    return completed.stdout.strip() if completed.returncode == 0 else ""


def _run_checker(root: Path, script: str, *args: str) -> None:
    path = root / script
    if not path.is_file():
        raise InitializationError(f"Required checker is missing: {script}")
    completed = _run(root, sys.executable, str(path), *args)
    _require_success(completed, script)


def _load_manifest(root: Path) -> tuple[str, list[str]]:
    path = root / "PACKAGE_MANIFEST.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise InitializationError(f"Cannot read PACKAGE_MANIFEST.json: {error}") from error
    if not isinstance(value, dict) or not isinstance(value.get("version"), str):
        raise InitializationError("PACKAGE_MANIFEST.json lacks a string version.")
    records = value.get("files")
    if not isinstance(records, list):
        raise InitializationError("PACKAGE_MANIFEST.json lacks the runtime files array.")
    paths: list[str] = []
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("path"), str):
            raise InitializationError("PACKAGE_MANIFEST.json contains an invalid file record.")
        paths.append(record["path"])
    if len(paths) != len(set(paths)):
        raise InitializationError("PACKAGE_MANIFEST.json contains duplicate paths.")
    return value["version"], sorted(paths)


def _validate_identity_value(value: str, label: str) -> str:
    normalized = value.strip()
    if not normalized or "\n" in value or "\r" in value or "\x00" in value:
        raise InitializationError(f"{label} must be a non-empty single-line value.")
    return normalized


def _configure_identity(root: Path, name: str | None, email: str | None) -> None:
    if (name is None) != (email is None):
        raise InitializationError("Provide --git-name and --git-email together.")
    if name is not None and email is not None:
        safe_name = _validate_identity_value(name, "--git-name")
        safe_email = _validate_identity_value(email, "--git-email")
        _require_success(
            _run(root, "git", "config", "--local", "user.name", safe_name),
            "setting local Git user.name",
        )
        _require_success(
            _run(root, "git", "config", "--local", "user.email", safe_email),
            "setting local Git user.email",
        )
    configured_name = _run(root, "git", "config", "user.name").stdout.strip()
    configured_email = _run(root, "git", "config", "user.email").stdout.strip()
    environment_name = os.environ.get("GIT_AUTHOR_NAME", "").strip()
    environment_email = os.environ.get("GIT_AUTHOR_EMAIL", "").strip()
    if not ((configured_name and configured_email) or (environment_name and environment_email)):
        raise InitializationError(
            "Git author identity is missing. Re-run with both --git-name and --git-email, "
            "or configure them with git config before initialization."
        )


def _memory_mode_block(mode: str) -> str:
    return (
        f"\n{BEGIN_MEMORY_MODE}: {mode}\n"
        "# This explicit local choice tracks real matters and mutable operational memory.\n"
        "!matters/**\n"
        "!memory/CURRENT.md\n"
        "!memory/DECISIONS.md\n"
        "!memory/OPEN_QUESTIONS.md\n"
        "!memory/index.yaml\n"
        "!memory/sessions/**\n"
        f"{END_MEMORY_MODE}: {mode}\n"
    )


def _apply_memory_mode(root: Path, mode: str) -> None:
    if mode == "untracked":
        return
    path = root / ".gitignore"
    text = path.read_text(encoding="utf-8")
    if BEGIN_MEMORY_MODE in text or END_MEMORY_MODE in text:
        raise InitializationError(".gitignore already contains a memory-mode block.")
    path.write_text(text.rstrip() + "\n" + _memory_mode_block(mode), encoding="utf-8", newline="\n")


def _stage_release_files(root: Path, paths: list[str], mode: str) -> None:
    selected = paths
    if mode == "untracked":
        selected = [path for path in paths if path not in MUTABLE_UNTRACKED_PATHS]
    selected.extend(["CHECKSUMS.sha256", "PACKAGE_MANIFEST.json"])
    missing = [path for path in selected if not (root / path).is_file()]
    if missing:
        raise InitializationError(f"Manifest-declared files are missing: {missing}")
    _require_success(
        _run(root, "git", "add", "--", *sorted(set(selected))),
        "staging manifest-declared files",
    )


def _check_no_remote(root: Path) -> None:
    completed = _run(root, "git", "remote")
    _require_success(completed, "listing Git remotes")
    if completed.stdout.strip():
        raise InitializationError("Initialization never changes an existing Git remote.")


def _finish_existing(root: Path, mode: str, version: str) -> int:
    if _config(root, "minius.initialized") != "true":
        raise InitializationError("Existing Git history was not created by init_workspace.py.")
    recorded_mode = _config(root, "minius.memoryMode")
    recorded_version = _config(root, "minius.workspaceVersion")
    if recorded_mode != mode:
        raise InitializationError(
            f"Workspace already uses memory mode {recorded_mode!r}; requested {mode!r}."
        )
    if recorded_version != version:
        raise InitializationError(
            f"Workspace was initialized from {recorded_version!r}; use an upgrade procedure "
            f"for release {version!r}."
        )
    _run_checker(
        root,
        "scripts/validate_workspace.py",
        "--mode",
        "operational",
        "--root",
        str(root),
    )
    _run_checker(root, "scripts/check_repo_safety.py", "--profile", "workspace-local")
    status = _run(root, "git", "status", "--porcelain")
    _require_success(status, "checking Git status")
    if status.stdout.strip():
        raise InitializationError("Initialized workspace has uncommitted non-ignored changes.")
    print(f"already initialized: {root}")
    print(f"memory mode: {mode}; release: {version}; no Git state was changed")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--memory-mode",
        choices=MEMORY_MODES,
        default="untracked",
        help="How real matters and mutable memory enter Git (default: untracked).",
    )
    parser.add_argument("--main-branch", default="main")
    parser.add_argument("--git-name", help="Optional repository-local author name.")
    parser.add_argument("--git-email", help="Optional repository-local author email.")
    parser.add_argument(
        "--acknowledge-private-approved",
        action="store_true",
        help="Required acknowledgment for private-approved mode; no remote is created.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = _root()
    try:
        if sys.version_info < (3, 11):  # noqa: UP036 - explicit user-facing preflight
            raise InitializationError("Python 3.11 or newer is required.")
        if shutil.which("git") is None:
            raise InitializationError("Git is required and was not found on PATH.")
        if not BRANCH_PATTERN.fullmatch(args.main_branch) or ".." in args.main_branch:
            raise InitializationError("--main-branch is not a safe Git branch name.")
        if args.memory_mode == "private-approved" and not args.acknowledge_private_approved:
            raise InitializationError(
                "private-approved requires --acknowledge-private-approved. A private remote "
                "still requires organizational approval and a separate safety check."
            )

        version, manifest_paths = _load_manifest(root)
        existing_root = _git_root(root)
        if existing_root is not None and existing_root != root:
            raise InitializationError(
                f"Workspace is inside another Git repository: {existing_root}. "
                "Move it to a standalone directory before initialization."
            )
        if existing_root == root and _has_head(root):
            return _finish_existing(root, args.memory_mode, version)

        _run_checker(
            root,
            "scripts/validate_workspace.py",
            "--mode",
            "runtime",
            "--root",
            str(root),
        )
        _run_checker(root, "scripts/check_repo_safety.py", "--profile", "workspace-local")

        if existing_root is None:
            with tempfile.TemporaryDirectory(prefix="minius-empty-git-template-") as template:
                _require_success(
                    _run(
                        root,
                        "git",
                        "init",
                        "--template",
                        template,
                        "-b",
                        args.main_branch,
                    ),
                    "initializing standalone Git repository",
                )
        else:
            _require_success(
                _run(root, "git", "symbolic-ref", "HEAD", f"refs/heads/{args.main_branch}"),
                "setting the initial branch",
            )
        _check_no_remote(root)
        _configure_identity(root, args.git_name, args.git_email)
        _apply_memory_mode(root, args.memory_mode)
        _stage_release_files(root, manifest_paths, args.memory_mode)
        _run_checker(
            root,
            "scripts/check_repo_safety.py",
            "--profile",
            "workspace-local",
            "--staged",
        )
        _require_success(_run(root, "git", "diff", "--cached", "--check"), "git diff --check")

        with tempfile.TemporaryDirectory(prefix="minius-disabled-git-hooks-") as hooks:
            completed = _run(
                root,
                "git",
                "-c",
                f"core.hooksPath={hooks}",
                "-c",
                "commit.gpgsign=false",
                "commit",
                "--no-verify",
                "-m",
                f"ops: initialize minius workspace {version}",
            )
        _require_success(completed, "creating the initial commit")
        commit = _run(root, "git", "rev-parse", "HEAD")
        _require_success(commit, "reading the initial commit")
        for key, value in (
            ("minius.initialized", "true"),
            ("minius.memoryMode", args.memory_mode),
            ("minius.workspaceVersion", version),
            ("minius.initialCommit", commit.stdout.strip()),
        ):
            _require_success(
                _run(root, "git", "config", "--local", key, value),
                f"recording {key}",
            )
        _run_checker(
            root,
            "scripts/validate_workspace.py",
            "--mode",
            "operational",
            "--root",
            str(root),
        )
        _run_checker(root, "scripts/check_repo_safety.py", "--profile", "workspace-local")
        status = _run(root, "git", "status", "--porcelain")
        _require_success(status, "checking final Git status")
        if status.stdout.strip():
            raise InitializationError("Initialization left uncommitted non-ignored changes.")
    except InitializationError as error:
        print(f"BLOCKED: {error}", file=sys.stderr)
        return 1

    print(f"initialized: {root}")
    print(f"initial commit: {commit.stdout.strip()}")
    print(f"memory mode: {args.memory_mode}; remote: none")
    print("Next: review AGENTS.md, SECURITY.md, .codex/config.toml, hooks, and rules.")
    print(
        "Then start Codex, approve project trust only after review, and inspect /hooks and /skills."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
