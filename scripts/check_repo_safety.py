#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlsplit

EXIT_SAFE = 0
EXIT_BLOCKED = 1
EXIT_USAGE = 2

PROFILES = ("upstream-public", "workspace-local", "workspace-private")
UPSTREAM_REPOSITORY = "minius_codex_lab"
MAX_SCAN_BYTES = 5 * 1024 * 1024
COMMAND_TIMEOUT_SECONDS = 15

PROHIBITED_PATH_PARTS = {
    "restricted",
    "personal-data",
    "personal_data",
    "vault",
    "state-secret",
    "state_secret",
    "dsk",
}
PROHIBITED_FILENAMES = {
    ".env",
    ".netrc",
    ".npmrc",
    ".pypirc",
    "auth.json",
    "credentials.json",
    "secrets.json",
    "history.jsonl",
}
ALLOWED_ENV_EXAMPLES = {".env.example", ".env.sample"}
BOOTSTRAP_INPUT_FILENAMES = {
    "bootstrap_codex_instruction.md",
    "codex_maintainer_bootstrap_minius_codex_lab_ru.md",
    "codex_maintainer_bootstrap_minius_codex_lab_ru.md.sha256",
    "codex_setup_prompt_ru.md",
}
PROHIBITED_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".jks", ".kdbx"}
ARCHIVE_SUFFIXES = (
    ".zip",
    ".7z",
    ".rar",
    ".tar",
    ".tar.gz",
    ".tgz",
    ".gz",
    ".bz2",
    ".xz",
    ".whl",
)
PLACEHOLDER_FILENAMES = {".gitkeep", "README.md"}
PUBLIC_SCRATCH_ROOTS = {
    ".bootstrap",
    ".setup-backup",
    ".setup-staging",
    "build",
    "dist",
    "release-inputs",
    "release_inputs",
}
PUBLIC_RUNTIME_ROOTS = {"artifacts", "logs", "memory", "outputs"}
PUBLIC_SYNTHETIC_FILES: frozenset[str] = frozenset()
IGNORED_LOCAL_PATH_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tmp",
    ".venv",
    "__pycache__",
    "venv",
}
WORKSPACE_TEMPLATE_FILES = frozenset(
    {
        ".codex/config.toml",
        ".codex/hooks.json",
        ".codex/hooks/session_start_memory.py",
        ".codex/hooks/stop_git_guard.py",
        ".codex/rules/default.rules",
        ".gitattributes",
        ".gitignore",
        ".worktreeinclude",
        "AGENTS.md",
        "README.md",
        "SECURITY.md",
        "artifacts/README.md",
        "docs/GIT_WORKFLOW.md",
        "docs/CODEX_SMOKE_TEST.md",
        "docs/INSTALL_WINDOWS_POWERSHELL.md",
        "docs/LEGAL_SOURCE_HIERARCHY.md",
        "docs/LEGAL_WORKFLOW_LEVELS.md",
        "docs/OPENAI_CODEX_ARCHITECTURE_NOTES.md",
        "docs/ROLE_MAP.md",
        "docs/SKILL_MAP.md",
        "docs/SOURCE_DOCUMENT_ANALYSIS.md",
        "docs/STAGE2_MEMORY_OPTIONS.md",
        "docs/VERIFIABLE_DOCUMENT_SPEC.md",
        "logs/curated/README.md",
        "logs/raw/.gitkeep",
        "logs/raw/README.md",
        "matters/AGENTS.md",
        "matters/README.md",
        "matters/_template/MATTER.md",
        "matters/_template/PLAN.md",
        "matters/_template/data/.gitkeep",
        "matters/_template/drafts/.gitkeep",
        "matters/_template/evidence/CLAIMS.csv",
        "matters/_template/evidence/CONFLICTS.csv",
        "matters/_template/evidence/MISSING_DATA.csv",
        "matters/_template/outputs/.gitkeep",
        "matters/_template/research/.gitkeep",
        "matters/_template/reviews/.gitkeep",
        "matters/_template/sources/README.md",
        "matters/_template/sources/REGISTER.csv",
        "memory/CURRENT.md",
        "memory/DECISIONS.md",
        "memory/GLOSSARY.md",
        "memory/OPEN_QUESTIONS.md",
        "memory/README.md",
        "memory/SOURCE_POLICY.md",
        "memory/decisions/ADR-0001-repository-memory.md",
        "memory/decisions/ADR-0002-web-search-mode.md",
        "memory/decisions/ADR-0003-verifiable-document.md",
        "memory/index.yaml",
        "memory/sessions/.gitkeep",
        "memory/templates/decision.md",
        "memory/templates/handoff.md",
        "memory/templates/matter-brief.md",
        "memory/templates/session.md",
        "requirements.txt",
        "scripts/finish_session.py",
        "scripts/init_workspace.py",
        "scripts/new_matter.py",
        "scripts/run_synthetic_e2e.py",
        "scripts/start_session.py",
    }
)
POLICY_TEXT_PATHS = {
    "AGENTS.md",
    "README.md",
    "SECURITY.md",
    "scripts/check_repo_safety.py",
    "workspace-template/AGENTS.md",
    "workspace-template/README.md",
    "workspace-template/SECURITY.md",
}

SECRET_PATTERNS = (
    ("private_key", re.compile("-----BEGIN " + "(?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("openai_style_key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("github_fine_grained_token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b")),
    (
        "jwt",
        re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    ),
)
CLASSIFICATION_PATTERNS = (
    ("state_secret_marker_uk", re.compile(r"державн(?:а|ої)\s+таємниц", re.IGNORECASE)),
    (
        "state_secret_marker_ru",
        re.compile(r"государственн(?:ая|ой|ую)\s+тайн", re.IGNORECASE),
    ),
    ("secret_marker_uk", re.compile(r"\b(?:цілком\s+таємно|таємно)\b", re.IGNORECASE)),
    (
        "official_use_marker_uk",
        re.compile(r"для\s+службового\s+користування", re.IGNORECASE),
    ),
    (
        "official_use_marker_ru",
        re.compile(r"для\s+служебного\s+пользования", re.IGNORECASE),
    ),
)
PII_PATTERNS = (
    (
        "ukrainian_tax_number",
        re.compile(r"\b(?:РНОКПП|ІПН|ИНН)\D{0,20}\d{10}\b", re.IGNORECASE),
    ),
    ("ukrainian_iban", re.compile(r"\bUA\d{27}\b")),
)


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    path: str
    message: str


@dataclass(frozen=True)
class Candidate:
    relative: str
    kind: str
    size: int | None = None
    data: bytes | None = None


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: bytes = b""


@dataclass(frozen=True)
class RemoteIdentity:
    host: str
    owner: str
    name: str


def _default_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _run(root: Path, *args: str) -> CommandResult:
    try:
        result = subprocess.run(
            args,
            cwd=root,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return CommandResult(returncode=127)
    return CommandResult(returncode=result.returncode, stdout=result.stdout)


def _decode(value: bytes) -> str:
    return os.fsdecode(value)


def _nul_values(value: bytes) -> list[bytes]:
    return [item for item in value.split(b"\0") if item]


def _line_values(value: bytes) -> list[str]:
    return [_decode(item).strip() for item in value.splitlines() if item.strip()]


def _safe_relative(value: str) -> bool:
    path = PurePosixPath(value)
    return (
        bool(value)
        and value != "."
        and not path.is_absolute()
        and ".." not in path.parts
        and "\\" not in value
        and "\x00" not in value
    )


def _exact_git_root(root: Path) -> bool:
    result = _run(root, "git", "rev-parse", "--show-toplevel")
    if result.returncode != 0:
        return False
    value = _decode(result.stdout).strip()
    if not value:
        return False
    try:
        return Path(value).resolve() == root.resolve()
    except OSError:
        return False


def _read_worktree_candidate(root: Path, relative: str) -> Candidate:
    path = root / relative
    try:
        metadata = path.lstat()
    except OSError:
        return Candidate(relative=relative, kind="unreadable")
    if stat.S_ISLNK(metadata.st_mode):
        return Candidate(relative=relative, kind="symlink", size=metadata.st_size)
    if not stat.S_ISREG(metadata.st_mode):
        return Candidate(relative=relative, kind="special", size=metadata.st_size)
    if metadata.st_size > MAX_SCAN_BYTES:
        return Candidate(relative=relative, kind="regular", size=metadata.st_size)
    descriptor: int | None = None
    try:
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (
            metadata.st_dev,
            metadata.st_ino,
        ):
            return Candidate(relative=relative, kind="unreadable", size=opened.st_size)
        with os.fdopen(descriptor, "rb") as stream:
            descriptor = None
            data = stream.read(MAX_SCAN_BYTES + 1)
    except OSError:
        return Candidate(relative=relative, kind="unreadable", size=metadata.st_size)
    finally:
        if descriptor is not None:
            os.close(descriptor)
    return Candidate(relative=relative, kind="regular", size=len(data), data=data)


def _filesystem_candidates(root: Path) -> list[Candidate]:
    candidates: list[Candidate] = []
    for path in root.rglob("*"):
        relative_path = path.relative_to(root)
        if set(relative_path.parts) & IGNORED_LOCAL_PATH_PARTS:
            continue
        try:
            if stat.S_ISDIR(path.lstat().st_mode):
                continue
        except OSError:
            pass
        candidates.append(_read_worktree_candidate(root, relative_path.as_posix()))
    return sorted(candidates, key=lambda item: item.relative)


def _worktree_candidates(root: Path, findings: list[Finding]) -> list[Candidate]:
    if not _exact_git_root(root):
        return _filesystem_candidates(root)
    cached = _run(root, "git", "ls-files", "--cached", "-z")
    untracked = _run(root, "git", "ls-files", "--others", "--exclude-standard", "-z")
    if cached.returncode != 0 or untracked.returncode != 0:
        findings.append(
            Finding(
                "blocker",
                "git_file_list_failed",
                ".",
                "Git file enumeration failed; scan cannot continue safely.",
            )
        )
    candidates: list[Candidate] = []
    cached_values = set(_nul_values(cached.stdout)) if cached.returncode == 0 else set()
    untracked_values = set(_nul_values(untracked.stdout)) if untracked.returncode == 0 else set()
    for raw_value in sorted(cached_values | untracked_values):
        relative = _decode(raw_value)
        if not _safe_relative(relative):
            findings.append(
                Finding("blocker", "unsafe_repository_path", relative, "Unsafe repository path.")
            )
            continue
        if raw_value in cached_values:
            index_candidate = _index_candidate(root, relative, raw_value)
            candidates.append(index_candidate)
            worktree_candidate = _read_worktree_candidate(root, relative)
            if worktree_candidate != index_candidate:
                candidates.append(worktree_candidate)
        else:
            candidates.append(_read_worktree_candidate(root, relative))
    return candidates


def _index_candidate(root: Path, relative: str, raw_relative: bytes) -> Candidate:
    entry = _run(
        root,
        "git",
        "--literal-pathspecs",
        "ls-files",
        "--stage",
        "-z",
        "--",
        relative,
    )
    records = _nul_values(entry.stdout) if entry.returncode == 0 else []
    if len(records) != 1 or b"\t" not in records[0]:
        return Candidate(relative=relative, kind="unreadable")
    header, recorded_path = records[0].split(b"\t", 1)
    fields = header.split()
    if len(fields) != 3 or fields[2] != b"0" or recorded_path != raw_relative:
        return Candidate(relative=relative, kind="unreadable")
    mode, object_id, _ = fields
    if mode == b"120000":
        return Candidate(relative=relative, kind="symlink")
    if mode not in {b"100644", b"100755"}:
        return Candidate(relative=relative, kind="special")
    size_result = _run(root, "git", "cat-file", "-s", _decode(object_id))
    try:
        size = int(size_result.stdout.strip()) if size_result.returncode == 0 else -1
    except ValueError:
        size = -1
    if size < 0:
        return Candidate(relative=relative, kind="unreadable")
    if size > MAX_SCAN_BYTES:
        return Candidate(relative=relative, kind="regular", size=size)
    blob = _run(root, "git", "cat-file", "blob", _decode(object_id))
    if blob.returncode != 0 or len(blob.stdout) != size:
        return Candidate(relative=relative, kind="unreadable", size=size)
    return Candidate(relative=relative, kind="regular", size=size, data=blob.stdout)


def _staged_candidates(root: Path, findings: list[Finding]) -> list[Candidate]:
    if not _exact_git_root(root):
        findings.append(
            Finding(
                "blocker",
                "staged_requires_git_root",
                ".",
                "Staged scanning requires --root to be the exact Git worktree root.",
            )
        )
        return []
    result = _run(
        root,
        "git",
        "diff",
        "--cached",
        "--name-only",
        "-z",
        "--diff-filter=ACMRTU",
        "--no-ext-diff",
        "--no-textconv",
    )
    if result.returncode != 0:
        findings.append(
            Finding(
                "blocker",
                "staged_file_list_failed",
                ".",
                "Staged file enumeration failed; scan cannot continue safely.",
            )
        )
        return []
    candidates: list[Candidate] = []
    for raw_relative in sorted(set(_nul_values(result.stdout))):
        relative = _decode(raw_relative)
        if not _safe_relative(relative):
            findings.append(
                Finding("blocker", "unsafe_repository_path", relative, "Unsafe repository path.")
            )
            continue
        candidates.append(_index_candidate(root, relative, raw_relative))
    return candidates


def _is_synthetic_path(parts: tuple[str, ...]) -> bool:
    return PurePosixPath(*parts).as_posix() in PUBLIC_SYNTHETIC_FILES


def _is_workspace_seed(parts: tuple[str, ...]) -> bool:
    if not parts or parts[0].casefold() != "workspace-template":
        return False
    relative = PurePosixPath(*parts[1:]).as_posix()
    return relative in WORKSPACE_TEMPLATE_FILES


def _path_findings(relative: str, profile: str) -> list[Finding]:
    findings: list[Finding] = []
    path = PurePosixPath(relative)
    parts = path.parts
    folded = tuple(part.casefold() for part in parts)
    name = path.name.casefold()
    suffix = path.suffix.casefold()
    if set(folded) & PROHIBITED_PATH_PARTS:
        findings.append(
            Finding(
                "blocker",
                "prohibited_data_path",
                relative,
                "Path denotes data that this scanner never approves for repository storage.",
            )
        )
    if name in PROHIBITED_FILENAMES or (
        name.startswith(".env.") and name not in ALLOWED_ENV_EXAMPLES
    ):
        findings.append(
            Finding("blocker", "credential_filename", relative, "Credential-like filename.")
        )
    if suffix in PROHIBITED_SUFFIXES:
        findings.append(
            Finding("blocker", "credential_extension", relative, "Sensitive file extension.")
        )
    if any(name.endswith(item) for item in ARCHIVE_SUFFIXES) or any(
        name.endswith(f"{item}.sha256") for item in ARCHIVE_SUFFIXES
    ):
        findings.append(
            Finding(
                "blocker",
                "archive_or_release_input",
                relative,
                "Opaque archive or release input is not approved by the source scanner.",
            )
        )
    if "logs" in folded and path.name not in PLACEHOLDER_FILENAMES:
        findings.append(
            Finding("blocker", "runtime_log", relative, "Runtime logs are not repository-safe.")
        )
    if profile != "upstream-public":
        return findings
    if name in BOOTSTRAP_INPUT_FILENAMES:
        findings.append(
            Finding(
                "blocker",
                "bootstrap_input",
                relative,
                "Bootstrap instructions and integrity inputs must stay outside Git history.",
            )
        )
    synthetic = _is_synthetic_path(parts)
    workspace_seed = _is_workspace_seed(parts)
    if folded and folded[0] in PUBLIC_SCRATCH_ROOTS:
        findings.append(
            Finding(
                "blocker",
                "public_release_input",
                relative,
                "Staging, build, backup, and release-input paths are not canonical source.",
            )
        )
    if name in {".ds_store", "thumbs.db"} or name.startswith("~$"):
        findings.append(
            Finding("blocker", "generated_local_file", relative, "Generated local file.")
        )
    if (
        folded
        and folded[0] == "matters"
        and not synthetic
        and (len(folded) < 2 or folded[1] != "_template")
    ):
        findings.append(
            Finding(
                "blocker",
                "public_real_matter",
                relative,
                "Real matter data is not public source.",
            )
        )
    if folded and folded[0] in PUBLIC_RUNTIME_ROOTS and not synthetic:
        findings.append(
            Finding(
                "blocker",
                "public_runtime_state",
                relative,
                "Runtime memory, logs, artifacts, or outputs are not public source.",
            )
        )
    if folded and folded[0] == "workspace-template" and not workspace_seed:
        findings.append(
            Finding(
                "blocker",
                "non_seed_workspace_content",
                relative,
                "Only workspace-template seeds and synthetic fixtures are public.",
            )
        )
    if not synthetic and not workspace_seed and set(folded) & {"artifacts", "outputs"}:
        findings.append(
            Finding(
                "blocker",
                "public_generated_output",
                relative,
                "Generated artifacts and outputs are not canonical public source.",
            )
        )
    return findings


def _policy_marker_allowed(relative: str) -> bool:
    return relative in POLICY_TEXT_PATHS


def _content_findings(candidate: Candidate) -> list[Finding]:
    relative = candidate.relative
    if candidate.kind == "symlink":
        return [Finding("blocker", "symlink_entry", relative, "Symlink entries are not scanned.")]
    if candidate.kind == "special":
        return [
            Finding("blocker", "special_file", relative, "Only regular files are repository-safe.")
        ]
    if candidate.kind != "regular":
        return [Finding("blocker", "unreadable_file", relative, "File could not be read safely.")]
    if candidate.size is None or candidate.size > MAX_SCAN_BYTES:
        return [
            Finding(
                "blocker",
                "large_file",
                relative,
                f"File exceeds the {MAX_SCAN_BYTES}-byte scan limit.",
            )
        ]
    if candidate.data is None:
        return [Finding("blocker", "unreadable_file", relative, "File content is unavailable.")]
    data = candidate.data
    if b"\x00" in data or any(byte < 32 and byte not in {9, 10, 13} for byte in data):
        return [Finding("blocker", "binary_file", relative, "Binary content is not approved.")]
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return [Finding("blocker", "non_utf8_file", relative, "Non-UTF-8 content is opaque.")]
    findings: list[Finding] = []
    if text.startswith("version https://git-lfs.github.com/spec/v1"):
        findings.append(
            Finding(
                "blocker",
                "git_lfs_pointer",
                relative,
                "Git LFS content is opaque to this scan.",
            )
        )
    for code, pattern in SECRET_PATTERNS:
        if pattern.search(text):
            findings.append(
                Finding("blocker", code, relative, "High-confidence credential pattern found.")
            )
    if not _policy_marker_allowed(relative):
        for code, pattern in CLASSIFICATION_PATTERNS:
            if pattern.search(text):
                findings.append(
                    Finding("blocker", code, relative, "Restricted-information marker found.")
                )
    for code, pattern in PII_PATTERNS:
        if pattern.search(text):
            findings.append(Finding("blocker", code, relative, "Personal-data pattern found."))
    return findings


def _redact_remote_url(value: str) -> str:
    identity = _remote_identity(value.strip())
    if identity is None:
        return "[invalid-or-unsupported-remote]"
    return f"{identity.host}/{identity.owner}/{identity.name}"


def _remote_has_credentials(value: str) -> bool:
    if "://" in value:
        try:
            parsed = urlsplit(value)
            port = parsed.port
        except ValueError:
            return True
        scheme = parsed.scheme.casefold()
        if scheme == "https":
            return bool(
                parsed.username
                or parsed.password
                or parsed.query
                or parsed.fragment
                or port not in {None, 443}
            )
        if scheme == "ssh":
            return bool(
                (parsed.username or "").casefold() != "git"
                or parsed.password
                or parsed.query
                or parsed.fragment
                or port not in {None, 22}
            )
        return True
    match = re.fullmatch(r"(?:(?P<user>[^@/:]+)@)?(?P<host>[^:]+):(?P<path>.+)", value)
    return bool(match is None or (match.group("user") or "git").casefold() != "git")


def _remote_identity(value: str) -> RemoteIdentity | None:
    if "://" in value:
        try:
            parsed = urlsplit(value)
            port = parsed.port
        except ValueError:
            return None
        scheme = parsed.scheme.casefold()
        if scheme == "https":
            if parsed.username or parsed.password or port not in {None, 443}:
                return None
        elif scheme == "ssh":
            if (
                (parsed.username or "").casefold() != "git"
                or parsed.password
                or port not in {None, 22}
            ):
                return None
        else:
            return None
        host = (parsed.hostname or "").casefold()
        path = parsed.path.strip("/")
    else:
        match = re.fullmatch(r"(?:(?P<user>[^@/:]+)@)?(?P<host>[^:]+):(?P<path>.+)", value)
        if not match:
            return None
        if (match.group("user") or "git").casefold() != "git":
            return None
        host = match.group("host").casefold()
        path = match.group("path").strip("/")
    components = path.split("/")
    if host != "github.com" or len(components) != 2 or not all(components):
        return None
    owner, name = components
    if name.endswith(".git"):
        name = name[:-4]
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})", owner):
        return None
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,100}", name):
        return None
    return RemoteIdentity(host=host, owner=owner, name=name)


def _remote_result(profile: str) -> dict[str, Any]:
    return {
        "requested": True,
        "required": profile != "workspace-local",
        "present": False,
        "verified": False,
        "owner": None,
        "name": None,
        "visibility": None,
        "url": None,
        "fetch_urls": [],
        "push_urls": [],
    }


def _check_remote(root: Path, profile: str, findings: list[Finding]) -> dict[str, Any]:
    result = _remote_result(profile)
    start_count = len(findings)
    if not _exact_git_root(root):
        findings.append(
            Finding(
                "blocker",
                "remote_requires_git_root",
                "origin",
                "Remote verification requires the exact Git worktree root.",
            )
        )
        return result
    remotes = _run(root, "git", "remote")
    if remotes.returncode != 0:
        findings.append(
            Finding("blocker", "remote_list_failed", "origin", "Git remotes could not be read.")
        )
        return result
    if "origin" not in _line_values(remotes.stdout):
        if profile != "workspace-local":
            findings.append(
                Finding("blocker", "origin_missing", "origin", "Required origin remote is absent.")
            )
        return result
    result["present"] = True
    fetch = _run(root, "git", "remote", "get-url", "--all", "origin")
    push = _run(root, "git", "remote", "get-url", "--push", "--all", "origin")
    fetch_urls = _line_values(fetch.stdout) if fetch.returncode == 0 else []
    push_urls = _line_values(push.stdout) if push.returncode == 0 else []
    result["fetch_urls"] = [_redact_remote_url(value) for value in fetch_urls]
    result["push_urls"] = [_redact_remote_url(value) for value in push_urls]
    if not fetch_urls or not push_urls:
        findings.append(
            Finding(
                "blocker",
                "remote_url_unavailable",
                "origin",
                "Fetch and push URLs must both be available.",
            )
        )
        return result
    all_urls = fetch_urls + push_urls
    if any(_remote_has_credentials(value) for value in all_urls):
        findings.append(
            Finding(
                "blocker",
                "credential_in_remote_url",
                "origin",
                "Remote URL contains userinfo, parameters, or credential-like data.",
            )
        )
    identities = [_remote_identity(value) for value in all_urls]
    if any(identity is None for identity in identities):
        findings.append(
            Finding(
                "blocker",
                "remote_identity_unverified",
                "origin",
                "Every fetch and push URL must identify one GitHub owner/repository.",
            )
        )
        return result
    concrete = [identity for identity in identities if identity is not None]
    first = concrete[0]
    if any(
        (item.host, item.owner.casefold(), item.name)
        != (first.host, first.owner.casefold(), first.name)
        for item in concrete[1:]
    ):
        findings.append(
            Finding(
                "blocker",
                "remote_url_mismatch",
                "origin",
                "Fetch and push URLs do not identify the same repository.",
            )
        )
        return result
    result.update(
        {
            "owner": first.owner,
            "name": first.name,
            "url": _redact_remote_url(fetch_urls[0]),
        }
    )
    expected_owner = first.owner
    expected_name = first.name
    if profile == "upstream-public":
        expected_name = UPSTREAM_REPOSITORY
        authenticated = _run(root, "gh", "api", "user", "--jq", ".login")
        login = _decode(authenticated.stdout).strip() if authenticated.returncode == 0 else ""
        if not login:
            findings.append(
                Finding(
                    "blocker",
                    "github_owner_unverified",
                    "origin",
                    "Authenticated GitHub owner could not be verified.",
                )
            )
            return result
        expected_owner = login
        if first.owner.casefold() != login.casefold():
            findings.append(
                Finding(
                    "blocker",
                    "remote_owner_mismatch",
                    "origin",
                    "Remote owner differs from the authenticated GitHub owner.",
                )
            )
    if first.name != expected_name:
        findings.append(
            Finding(
                "blocker",
                "remote_name_mismatch",
                "origin",
                f"Expected repository name {expected_name!r}.",
            )
        )
    target = f"{first.owner}/{first.name}"
    view = _run(
        root,
        "gh",
        "repo",
        "view",
        target,
        "--json",
        "name,nameWithOwner,visibility,url,isPrivate",
    )
    if view.returncode != 0:
        findings.append(
            Finding(
                "blocker",
                "remote_metadata_unverified",
                "origin",
                "GitHub repository metadata could not be verified.",
            )
        )
        return result
    try:
        metadata = json.loads(view.stdout)
    except (UnicodeDecodeError, json.JSONDecodeError):
        findings.append(
            Finding("blocker", "remote_metadata_invalid", "origin", "Invalid GitHub metadata.")
        )
        return result
    if not isinstance(metadata, dict):
        findings.append(
            Finding("blocker", "remote_metadata_invalid", "origin", "Invalid GitHub metadata.")
        )
        return result
    name = metadata.get("name")
    name_with_owner = metadata.get("nameWithOwner")
    visibility = str(metadata.get("visibility", "")).upper()
    is_private = metadata.get("isPrivate")
    metadata_url = metadata.get("url")
    result.update({"name": name, "visibility": visibility})
    if isinstance(metadata_url, str):
        result["url"] = _redact_remote_url(metadata_url)
    expected_full_name = f"{expected_owner}/{expected_name}"
    if (
        not isinstance(name_with_owner, str)
        or name_with_owner.casefold() != expected_full_name.casefold()
    ):
        findings.append(
            Finding(
                "blocker",
                "remote_owner_or_name_mismatch",
                "origin",
                "GitHub metadata does not match the expected owner/repository.",
            )
        )
    if name != expected_name:
        findings.append(
            Finding("blocker", "remote_name_mismatch", "origin", "GitHub name is unexpected.")
        )
    if profile == "upstream-public" and (visibility != "PUBLIC" or is_private is not False):
        findings.append(
            Finding("blocker", "remote_not_public", "origin", "Upstream remote is not PUBLIC.")
        )
    if profile == "workspace-private" and (visibility != "PRIVATE" or is_private is not True):
        findings.append(
            Finding("blocker", "remote_not_private", "origin", "Workspace remote is not PRIVATE.")
        )
    result["verified"] = len(findings) == start_count
    return result


def scan_repository(
    root: Path,
    profile: str,
    *,
    staged: bool = False,
    check_remote: bool = False,
) -> dict[str, Any]:
    findings: list[Finding] = []
    candidates = (
        _staged_candidates(root, findings) if staged else _worktree_candidates(root, findings)
    )
    for candidate in candidates:
        findings.extend(_path_findings(candidate.relative, profile))
        findings.extend(_content_findings(candidate))
    remote: dict[str, Any] = {"requested": False, "verified": False}
    if check_remote:
        remote = _check_remote(root, profile, findings)
    findings = sorted(
        set(findings),
        key=lambda item: (item.path, item.code, item.message),
    )
    blockers = [finding for finding in findings if finding.severity == "blocker"]
    warnings = [finding for finding in findings if finding.severity == "warning"]
    exit_code = EXIT_BLOCKED if blockers else EXIT_SAFE
    return {
        "schema_version": 1,
        "profile": profile,
        "root": str(root),
        "mode": "staged-index" if staged else "tracked-and-untracked",
        "scanned_files": len({candidate.relative for candidate in candidates}),
        "safe": not blockers,
        "exit_code": exit_code,
        "summary": {"blockers": len(blockers), "warnings": len(warnings)},
        "remote": remote,
        "findings": [asdict(finding) for finding in findings],
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scan repository content under an explicit publication/storage profile."
    )
    parser.add_argument(
        "--profile",
        choices=PROFILES,
        default="workspace-local",
        help="Safety policy profile (default: workspace-local).",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=_default_root(),
        help="Exact repository/workspace root to scan.",
    )
    parser.add_argument(
        "--staged",
        action="store_true",
        help="Read staged paths and blobs from the Git index, never from the worktree.",
    )
    parser.add_argument(
        "--check-remote",
        action="store_true",
        help=(
            "Verify origin fetch/push URLs and provider metadata; this is automatic "
            "for workspace-private."
        ),
    )
    parser.add_argument("--json", action="store_true", help="Print the stable JSON report.")
    return parser.parse_args(argv)


def _print_report(report: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return
    state = "PASS" if report["safe"] else "BLOCK"
    summary = report["summary"]
    print(
        f"{state}: profile={report['profile']} scanned={report['scanned_files']} "
        f"blockers={summary['blockers']} warnings={summary['warnings']}"
    )
    for finding in report["findings"]:
        path = json.dumps(finding["path"], ensure_ascii=False)
        print(f"{finding['severity'].upper():7} {finding['code']}: {path} — {finding['message']}")
    remote = report["remote"]
    if remote.get("requested"):
        print(
            f"remote present={remote.get('present')} verified={remote.get('verified')} "
            f"owner={remote.get('owner')} name={remote.get('name')} "
            f"visibility={remote.get('visibility')} url={remote.get('url')}"
        )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    effective_check_remote = args.check_remote or args.profile == "workspace-private"
    try:
        root = args.root.expanduser().resolve(strict=True)
    except OSError:
        report = {
            "schema_version": 1,
            "profile": args.profile,
            "root": str(args.root),
            "mode": "staged-index" if args.staged else "tracked-and-untracked",
            "scanned_files": 0,
            "safe": False,
            "exit_code": EXIT_USAGE,
            "summary": {"blockers": 1, "warnings": 0},
            "remote": {"requested": effective_check_remote, "verified": False},
            "findings": [
                asdict(
                    Finding(
                        "blocker",
                        "root_unavailable",
                        str(args.root),
                        "Scan root does not exist or cannot be resolved.",
                    )
                )
            ],
        }
        _print_report(report, args.json)
        return EXIT_USAGE
    if not root.is_dir():
        report = {
            "schema_version": 1,
            "profile": args.profile,
            "root": str(root),
            "mode": "staged-index" if args.staged else "tracked-and-untracked",
            "scanned_files": 0,
            "safe": False,
            "exit_code": EXIT_USAGE,
            "summary": {"blockers": 1, "warnings": 0},
            "remote": {"requested": effective_check_remote, "verified": False},
            "findings": [
                asdict(
                    Finding(
                        "blocker",
                        "root_not_directory",
                        str(root),
                        "Root is not a directory.",
                    )
                )
            ],
        }
        _print_report(report, args.json)
        return EXIT_USAGE
    report = scan_repository(
        root,
        args.profile,
        staged=args.staged,
        check_remote=effective_check_remote,
    )
    _print_report(report, args.json)
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
