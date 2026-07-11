from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from scripts import check_repo_safety as safety


def _write(root: Path, relative: str, content: str = "safe\n") -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _codes(report: dict[str, Any]) -> set[str]:
    return {str(item["code"]) for item in report["findings"]}


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ("git", *args),
        cwd=root,
        check=True,
        capture_output=True,
    )


@pytest.mark.parametrize(
    ("profile", "safe"),
    [
        ("upstream-public", False),
        ("workspace-local", True),
        ("workspace-private", True),
    ],
)
def test_profile_matrix_for_real_matter(tmp_path: Path, profile: str, safe: bool) -> None:
    _write(tmp_path, "matters/2026-001/MATTER.md")

    report = safety.scan_repository(tmp_path, profile)

    assert report["safe"] is safe
    assert ("public_real_matter" in _codes(report)) is (not safe)


@pytest.mark.parametrize(
    "relative",
    [
        "scripts/tool.py",
        "workspace-template/memory/CURRENT.md",
        "workspace-template/matters/AGENTS.md",
        "workspace-template/matters/README.md",
        "workspace-template/matters/_template/MATTER.md",
        "workspace-template/logs/raw/.gitkeep",
        "tests/fixtures/synthetic-case.txt",
    ],
)
def test_upstream_allows_source_seeds_and_synthetic_fixtures(tmp_path: Path, relative: str) -> None:
    _write(tmp_path, relative)

    report = safety.scan_repository(tmp_path, "upstream-public")

    assert report["safe"] is True, report["findings"]


@pytest.mark.parametrize(
    "relative",
    [
        "BOOTSTRAP_CODEX_INSTRUCTION.md",
        "CODEX_MAINTAINER_BOOTSTRAP_MINIUS_CODEX_LAB_RU.md",
        "CODEX_MAINTAINER_BOOTSTRAP_MINIUS_CODEX_LAB_RU.md.sha256",
        "CODEX_SETUP_PROMPT_RU.md",
    ],
)
def test_upstream_blocks_bootstrap_inputs(tmp_path: Path, relative: str) -> None:
    _write(tmp_path, relative)

    report = safety.scan_repository(tmp_path, "upstream-public")

    assert report["safe"] is False
    assert "bootstrap_input" in _codes(report)


@pytest.mark.parametrize(
    "relative",
    [
        "workspace-template/client-case.txt",
        "workspace-template/memory/client-case.md",
        "workspace-template/matters/_template/client-notes.txt",
    ],
)
def test_upstream_blocks_non_allowlisted_workspace_content(tmp_path: Path, relative: str) -> None:
    _write(tmp_path, relative)

    report = safety.scan_repository(tmp_path, "upstream-public")

    assert report["safe"] is False
    assert "non_seed_workspace_content" in _codes(report)


@pytest.mark.parametrize(
    "relative",
    [
        "matters/fixtures/real-client-notes.md",
        "matters/fixtures/synthetic-case.md",
    ],
)
def test_upstream_blocks_non_allowlisted_matter_fixtures(tmp_path: Path, relative: str) -> None:
    _write(tmp_path, relative)

    report = safety.scan_repository(tmp_path, "upstream-public")

    assert report["safe"] is False
    assert "public_real_matter" in _codes(report)


@pytest.mark.parametrize(
    ("content", "expected_code"),
    [
        ("sk-" + "A" * 24, "openai_style_key"),
        ("РНОКПП: " + "1" * 10, "ukrainian_tax_number"),
        ("UA" + "1" * 27, "ukrainian_iban"),
        ("для " + "службового користування", "official_use_marker_uk"),
    ],
)
@pytest.mark.parametrize("profile", safety.PROFILES)
def test_every_profile_blocks_sensitive_content(
    tmp_path: Path, content: str, expected_code: str, profile: str
) -> None:
    _write(tmp_path, "notes/data.txt", content)

    report = safety.scan_repository(tmp_path, profile)

    assert report["safe"] is False
    assert expected_code in _codes(report)


@pytest.mark.skipif(shutil.which("git") is None, reason="Git is required")
def test_staged_scan_reads_index_blob_not_worktree(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-b", "main")
    path = _write(tmp_path, "safe.txt", "sk-" + "B" * 24)
    _git(tmp_path, "add", "--", "safe.txt")
    path.write_text("safe worktree replacement\n", encoding="utf-8")

    report = safety.scan_repository(tmp_path, "workspace-local", staged=True)

    assert report["mode"] == "staged-index"
    assert report["scanned_files"] == 1
    assert "openai_style_key" in _codes(report)


@pytest.mark.skipif(shutil.which("git") is None, reason="Git is required")
def test_full_scan_reads_index_blob_and_worktree(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-b", "main")
    path = _write(tmp_path, "safe.txt", "sk-" + "D" * 24)
    _git(tmp_path, "add", "--", "safe.txt")
    path.write_text("safe worktree replacement\n", encoding="utf-8")

    report = safety.scan_repository(tmp_path, "workspace-local")

    assert report["mode"] == "tracked-and-untracked"
    assert report["scanned_files"] == 1
    assert "openai_style_key" in _codes(report)


@pytest.mark.skipif(shutil.which("git") is None, reason="Git is required")
def test_staged_scan_handles_nul_delimited_odd_filename(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-b", "main")
    relative = "odd\nname.txt"
    path = _write(tmp_path, relative, "sk-" + "C" * 24)
    _git(tmp_path, "add", "--", relative)
    path.write_text("safe worktree replacement\n", encoding="utf-8")

    report = safety.scan_repository(tmp_path, "workspace-local", staged=True)

    assert "openai_style_key" in _codes(report)
    assert any(item["path"] == relative for item in report["findings"])


@pytest.mark.skipif(shutil.which("git") is None, reason="Git is required")
def test_worktree_git_enumeration_failure_blocks(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _git(tmp_path, "init", "-b", "main")
    _write(tmp_path, "safe.txt")
    original_run = safety._run

    def fail_cached(root: Path, *args: str) -> safety.CommandResult:
        if args == ("git", "ls-files", "--cached", "-z"):
            return safety.CommandResult(1)
        return original_run(root, *args)

    monkeypatch.setattr(safety, "_run", fail_cached)

    report = safety.scan_repository(tmp_path, "workspace-local")

    assert report["safe"] is False
    assert "git_file_list_failed" in _codes(report)


@pytest.mark.skipif(shutil.which("git") is None, reason="Git is required")
def test_staged_diff_failure_blocks(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _git(tmp_path, "init", "-b", "main")
    original_run = safety._run

    def fail_diff(root: Path, *args: str) -> safety.CommandResult:
        if args[:4] == ("git", "diff", "--cached", "--name-only"):
            return safety.CommandResult(1)
        return original_run(root, *args)

    monkeypatch.setattr(safety, "_run", fail_diff)

    report = safety.scan_repository(tmp_path, "workspace-local", staged=True)

    assert report["safe"] is False
    assert "staged_file_list_failed" in _codes(report)


@pytest.mark.skipif(shutil.which("git") is None, reason="Git is required")
def test_staged_cat_file_failure_blocks(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _git(tmp_path, "init", "-b", "main")
    _write(tmp_path, "safe.txt")
    _git(tmp_path, "add", "--", "safe.txt")
    original_run = safety._run

    def fail_cat_file(root: Path, *args: str) -> safety.CommandResult:
        if args[:3] == ("git", "cat-file", "-s"):
            return safety.CommandResult(1)
        return original_run(root, *args)

    monkeypatch.setattr(safety, "_run", fail_cat_file)

    report = safety.scan_repository(tmp_path, "workspace-local", staged=True)

    assert report["safe"] is False
    assert "unreadable_file" in _codes(report)


@pytest.mark.parametrize(
    ("value", "safe"),
    [
        ("normal/path.txt", True),
        ("odd\nname.txt", True),
        ("../outside.txt", False),
        ("nested/../../outside.txt", False),
        ("/absolute.txt", False),
        (r"..\outside.txt", False),
    ],
)
def test_repository_path_validation(value: str, safe: bool) -> None:
    assert safety._safe_relative(value) is safe


def _remote_runner(
    *,
    owner: str = "alice",
    name: str = safety.UPSTREAM_REPOSITORY,
    visibility: str = "PUBLIC",
    is_private: bool = False,
    authenticated_owner: str = "alice",
    fetch_url: str | None = None,
    push_url: str | None = None,
) -> Any:
    fetch = fetch_url or f"https://github.com/{owner}/{name}.git"
    push = push_url or f"git@github.com:{owner}/{name}.git"

    def run(_root: Path, *args: str) -> safety.CommandResult:
        if args == ("git", "rev-parse", "--show-toplevel"):
            return safety.CommandResult(0, os.fsencode(str(_root.resolve()) + "\n"))
        if args == ("git", "remote"):
            return safety.CommandResult(0, b"origin\n")
        if args == ("git", "remote", "get-url", "--all", "origin"):
            return safety.CommandResult(0, os.fsencode(fetch + "\n"))
        if args == ("git", "remote", "get-url", "--push", "--all", "origin"):
            return safety.CommandResult(0, os.fsencode(push + "\n"))
        if args == ("gh", "api", "user", "--jq", ".login"):
            return safety.CommandResult(0, os.fsencode(authenticated_owner + "\n"))
        if args[:3] == ("gh", "repo", "view"):
            metadata = {
                "name": name,
                "nameWithOwner": f"{owner}/{name}",
                "visibility": visibility,
                "url": f"https://github.com/{owner}/{name}",
                "isPrivate": is_private,
            }
            return safety.CommandResult(0, json.dumps(metadata).encode())
        raise AssertionError(f"unexpected command: {args!r}")

    return run


def test_upstream_remote_metadata_is_verified(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(safety, "_run", _remote_runner())
    findings: list[safety.Finding] = []

    remote = safety._check_remote(tmp_path, "upstream-public", findings)

    assert findings == []
    assert remote["verified"] is True
    assert remote["owner"] == "alice"
    assert remote["name"] == safety.UPSTREAM_REPOSITORY
    assert remote["visibility"] == "PUBLIC"


def test_upstream_remote_rejects_unverified_owner(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        safety,
        "_run",
        _remote_runner(owner="bob", authenticated_owner="alice"),
    )
    findings: list[safety.Finding] = []

    remote = safety._check_remote(tmp_path, "upstream-public", findings)

    assert remote["verified"] is False
    assert "remote_owner_mismatch" in {item.code for item in findings}


def test_workspace_private_requires_private_visibility(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        safety,
        "_run",
        _remote_runner(name="workspace", visibility="PRIVATE", is_private=True),
    )
    findings: list[safety.Finding] = []

    remote = safety._check_remote(tmp_path, "workspace-private", findings)

    assert findings == []
    assert remote["verified"] is True


def test_workspace_local_allows_missing_remote(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def no_remote(_root: Path, *args: str) -> safety.CommandResult:
        if args == ("git", "rev-parse", "--show-toplevel"):
            return safety.CommandResult(0, os.fsencode(str(_root.resolve()) + "\n"))
        if args == ("git", "remote"):
            return safety.CommandResult(0, b"")
        raise AssertionError(f"unexpected command: {args!r}")

    monkeypatch.setattr(safety, "_run", no_remote)
    findings: list[safety.Finding] = []

    remote = safety._check_remote(tmp_path, "workspace-local", findings)

    assert findings == []
    assert remote["required"] is False
    assert remote["present"] is False


def test_remote_credentials_are_blocked_and_fully_redacted(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    token = "secret-userinfo"
    fetch_url = f"https://{token}@github.com/alice/{safety.UPSTREAM_REPOSITORY}.git?key=value"
    monkeypatch.setattr(
        safety,
        "_run",
        _remote_runner(fetch_url=fetch_url),
    )
    findings: list[safety.Finding] = []

    remote = safety._check_remote(tmp_path, "upstream-public", findings)

    assert "credential_in_remote_url" in {item.code for item in findings}
    assert token not in json.dumps(remote)
    assert "key=value" not in json.dumps(remote)


def test_mismatched_push_url_is_blocked(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        safety,
        "_run",
        _remote_runner(push_url="git@github.com:mallory/other.git"),
    )
    findings: list[safety.Finding] = []

    safety._check_remote(tmp_path, "upstream-public", findings)

    assert "remote_url_mismatch" in {item.code for item in findings}


@pytest.mark.parametrize(
    "fetch_url",
    [
        "file://github.com/alice/minius_codex_lab.git",
        "http://github.com/alice/minius_codex_lab.git",
        "https://github.com:444/alice/minius_codex_lab.git",
        "ssh://bob@github.com/alice/minius_codex_lab.git",
    ],
)
def test_unsupported_remote_transport_is_blocked(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    fetch_url: str,
) -> None:
    monkeypatch.setattr(safety, "_run", _remote_runner(fetch_url=fetch_url))
    findings: list[safety.Finding] = []

    remote = safety._check_remote(tmp_path, "upstream-public", findings)

    assert remote["verified"] is False
    assert "remote_identity_unverified" in {item.code for item in findings}
    assert remote["fetch_urls"] == ["[invalid-or-unsupported-remote]"]


def test_supported_ssh_remote_is_verified(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        safety,
        "_run",
        _remote_runner(
            fetch_url="ssh://git@github.com/alice/minius_codex_lab.git",
        ),
    )
    findings: list[safety.Finding] = []

    remote = safety._check_remote(tmp_path, "upstream-public", findings)

    assert findings == []
    assert remote["verified"] is True


def test_invalid_remote_path_is_fully_redacted() -> None:
    value = "file://github.com/alice/do-not-disclose"

    redacted = safety._redact_remote_url(value)

    assert redacted == "[invalid-or-unsupported-remote]"
    assert "do-not-disclose" not in redacted


def test_workspace_private_cli_checks_remote_automatically(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(tmp_path, "README.md")

    exit_code = safety.main(["--root", str(tmp_path), "--profile", "workspace-private", "--json"])
    report = json.loads(capsys.readouterr().out)

    assert exit_code == safety.EXIT_BLOCKED
    assert report["remote"]["requested"] is True
    assert "remote_requires_git_root" in _codes(report)


def test_symlink_is_blocked(tmp_path: Path) -> None:
    target = _write(tmp_path, "target.txt")
    (tmp_path / "link.txt").symlink_to(target)

    report = safety.scan_repository(tmp_path, "workspace-local")

    assert "symlink_entry" in _codes(report)


def test_binary_file_is_blocked(tmp_path: Path) -> None:
    (tmp_path / "binary.dat").write_bytes(b"text\x00binary")

    report = safety.scan_repository(tmp_path, "workspace-local")

    assert "binary_file" in _codes(report)


def test_large_file_is_blocked_without_reading_content(tmp_path: Path) -> None:
    path = tmp_path / "large.txt"
    with path.open("wb") as stream:
        stream.truncate(safety.MAX_SCAN_BYTES + 1)

    report = safety.scan_repository(tmp_path, "workspace-local")

    assert "large_file" in _codes(report)


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFO is not supported")
def test_special_file_is_blocked_without_opening_it(tmp_path: Path) -> None:
    os.mkfifo(tmp_path / "pipe")

    report = safety.scan_repository(tmp_path, "workspace-local")

    assert "special_file" in _codes(report)


def test_unreadable_candidate_fails_closed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _write(tmp_path, "unreadable.txt")
    original = safety._read_worktree_candidate

    def unreadable(root: Path, relative: str) -> safety.Candidate:
        if relative == "unreadable.txt":
            return safety.Candidate(relative=relative, kind="unreadable")
        return original(root, relative)

    monkeypatch.setattr(safety, "_read_worktree_candidate", unreadable)

    report = safety.scan_repository(tmp_path, "workspace-local")

    assert "unreadable_file" in _codes(report)


def test_json_report_and_exit_codes_are_stable(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(tmp_path, "safe.txt")
    exit_code = safety.main(["--root", str(tmp_path), "--profile", "workspace-local", "--json"])
    report = json.loads(capsys.readouterr().out)

    assert exit_code == safety.EXIT_SAFE
    assert report["exit_code"] == safety.EXIT_SAFE
    assert report["schema_version"] == 1

    _write(tmp_path, ".env", "value")
    exit_code = safety.main(["--root", str(tmp_path), "--profile", "workspace-local", "--json"])
    report = json.loads(capsys.readouterr().out)

    assert exit_code == safety.EXIT_BLOCKED
    assert report["exit_code"] == safety.EXIT_BLOCKED
