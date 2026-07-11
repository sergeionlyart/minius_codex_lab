#!/usr/bin/env python3
"""Build and verify the deterministic public workspace release archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

PROJECT_NAME = "minius_codex_lab"
PACKAGE_NAME = "minius_codex_lab-workspace"
PROJECT_MANIFEST = "PACKAGE_MANIFEST.json"
CHECKSUMS_FILE = "CHECKSUMS.sha256"
MAX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024
ZIP_COMPRESSION = zipfile.ZIP_STORED

EXPECTED_MAPPINGS = (
    ("workspace-template", ""),
    (".agents/skills", ".agents/skills"),
    (".codex/agents", ".codex/agents"),
    ("tools/verifiable_document", "tools/verifiable_document"),
    ("scripts/check_repo_safety.py", "scripts/check_repo_safety.py"),
    ("scripts/validate_workspace.py", "scripts/validate_workspace.py"),
    ("LICENSE", "LICENSE"),
)

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

IGNORED_NAMES = {
    ".DS_Store",
    ".coverage",
    ".git",
    ".github",
    ".bootstrap",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "build",
    "dist",
    "htmlcov",
}
IGNORED_SUFFIXES = {".pyc", ".pyo", ".swp", ".tmp"}
FORBIDDEN_ARCHIVE_PARTS = {".git", ".github", ".bootstrap", "dist"}
FORBIDDEN_CREDENTIAL_NAMES = {
    ".env",
    "auth.json",
    "credentials.json",
    "history.jsonl",
    "secrets.json",
}
FORBIDDEN_CREDENTIAL_SUFFIXES = {".jks", ".key", ".kdbx", ".p12", ".pem", ".pfx"}
ARCHIVE_SUFFIXES = {".7z", ".bz2", ".gz", ".rar", ".tar", ".tgz", ".xz", ".zip"}
ESSENTIAL_FILES = {
    ".codex/config.toml",
    ".codex/hooks.json",
    "AGENTS.md",
    "LICENSE",
    "README.md",
    "requirements.txt",
    "docs/CODEX_SMOKE_TEST.md",
    "docs/INSTALL_WINDOWS_POWERSHELL.md",
    "matters/_template/MATTER.md",
    "memory/CURRENT.md",
    "scripts/check_repo_safety.py",
    "scripts/init_workspace.py",
    "scripts/new_matter.py",
    "scripts/run_synthetic_e2e.py",
    "scripts/validate_workspace.py",
    "tools/verifiable_document/README.md",
}


class BuildError(RuntimeError):
    """Raised when a release cannot be built or verified safely."""


@dataclass(frozen=True)
class PayloadFile:
    """A normalized file destined for the workspace archive."""

    source: Path
    target: str
    data: bytes
    mode: int


@dataclass(frozen=True)
class BuildResult:
    """Paths and digest produced by a successful build."""

    archive: Path
    checksum_file: Path
    sbom_file: Path
    sha256: str
    file_count: int
    source_date_epoch: int


def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise BuildError(f"Cannot read JSON object {path}: {error}") from error
    if not isinstance(value, dict):
        raise BuildError(f"JSON root must be an object: {path}")
    return value


def _safe_archive_name(value: str) -> PurePosixPath:
    if not value or value in {".", ".."}:
        raise BuildError(f"Unsafe empty archive path: {value!r}")
    if "\\" in value or "\x00" in value:
        raise BuildError(f"Unsafe archive path separator: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        raise BuildError(f"Archive path escapes its root: {value!r}")
    if path.as_posix() != value or any(part in {"", "."} for part in path.parts):
        raise BuildError(f"Archive path is not normalized: {value!r}")
    if path.parts and re.fullmatch(r"[A-Za-z]:", path.parts[0]):
        raise BuildError(f"Windows drive path is not allowed: {value!r}")
    return path


def _validate_project_manifest(
    manifest: Mapping[str, Any], requested_version: str | None
) -> tuple[str, int]:
    expected_keys = {
        "schema_version",
        "project",
        "package",
        "version",
        "layout",
        "default_source_date_epoch",
        "release_asset",
        "payload_mappings",
    }
    if set(manifest) != expected_keys:
        raise BuildError(
            "Project manifest keys differ from the supported schema: "
            f"{sorted(set(manifest) ^ expected_keys)}"
        )
    if manifest.get("schema_version") != 1:
        raise BuildError("Project manifest schema_version must be 1.")
    if manifest.get("project") != PROJECT_NAME or manifest.get("package") != PACKAGE_NAME:
        raise BuildError("Project/package identifier mismatch in project manifest.")
    if manifest.get("layout") != "workspace-template-overlay":
        raise BuildError("Project manifest layout must be workspace-template-overlay.")
    version = manifest.get("version")
    if not isinstance(version, str) or not re.fullmatch(
        r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?", version
    ):
        raise BuildError("Project manifest contains an invalid semantic version.")
    if requested_version is not None and requested_version != version:
        raise BuildError(
            f"Requested version {requested_version!r} differs from manifest {version!r}."
        )
    expected_asset = f"{PACKAGE_NAME}-v{version}.zip"
    if manifest.get("release_asset") != expected_asset:
        raise BuildError(f"release_asset must be {expected_asset!r}.")
    mappings = manifest.get("payload_mappings")
    if not isinstance(mappings, list):
        raise BuildError("payload_mappings must be an array.")
    normalized_mappings: list[tuple[str, str]] = []
    for index, item in enumerate(mappings):
        if not isinstance(item, dict) or set(item) != {"source", "target"}:
            raise BuildError(f"Invalid payload mapping at index {index}.")
        source = item.get("source")
        target = item.get("target")
        if not isinstance(source, str) or not isinstance(target, str):
            raise BuildError(f"Mapping {index} source/target must be strings.")
        normalized_mappings.append((source, target))
    if tuple(normalized_mappings) != EXPECTED_MAPPINGS:
        raise BuildError("Project manifest payload mappings differ from the fixed allowlist.")
    epoch = manifest.get("default_source_date_epoch")
    if not isinstance(epoch, int) or isinstance(epoch, bool) or epoch < 0:
        raise BuildError("default_source_date_epoch must be a non-negative integer.")
    return version, epoch


def _resolve_epoch(cli_value: int | None, fallback: int) -> int:
    raw_value: int | str = (
        cli_value if cli_value is not None else os.getenv("SOURCE_DATE_EPOCH", fallback)
    )
    try:
        value = int(raw_value)
    except (TypeError, ValueError) as error:
        raise BuildError("SOURCE_DATE_EPOCH must be an integer Unix timestamp.") from error
    value -= value % 2
    timestamp = datetime.fromtimestamp(value, tz=UTC)
    if timestamp.year < 1980 or timestamp.year > 2107:
        raise BuildError("SOURCE_DATE_EPOCH must map to a ZIP-supported year (1980-2107).")
    return value


def _ignored(relative: PurePosixPath) -> bool:
    return bool(set(relative.parts) & IGNORED_NAMES) or relative.suffix.casefold() in (
        IGNORED_SUFFIXES
    )


def _validate_template_path(relative: PurePosixPath) -> None:
    if relative.as_posix() not in WORKSPACE_TEMPLATE_FILES:
        raise BuildError(f"Non-allowlisted workspace-template file: {relative}")


def _is_allowlisted_distribution_path(relative: PurePosixPath) -> bool:
    value = relative.as_posix()
    if value in WORKSPACE_TEMPLATE_FILES | {
        CHECKSUMS_FILE,
        PROJECT_MANIFEST,
        "LICENSE",
        "scripts/check_repo_safety.py",
        "scripts/validate_workspace.py",
    }:
        return True
    if relative.parts[:2] == (".agents", "skills") and len(relative.parts) >= 3:
        return True
    if (
        relative.parts[:2] == (".codex", "agents")
        and len(relative.parts) == 3
        and relative.suffix == ".toml"
    ):
        return True
    return relative.parts[:2] == ("tools", "verifiable_document") and len(relative.parts) >= 3


def _normalized_mode(target: PurePosixPath) -> int:
    if target.parts[:2] == (".codex", "hooks") and target.suffix == ".py":
        return 0o755
    if target.parts and target.parts[0] == "scripts" and target.suffix in {".py", ".sh"}:
        return 0o755
    if target.parts[:2] == ("tools", "verifiable_document") and target.name in {
        "build.py",
        "ingest.py",
        "validate.py",
    }:
        return 0o755
    return 0o644


def _iter_source_files(source: Path) -> Iterable[tuple[Path, PurePosixPath]]:
    if source.is_symlink():
        raise BuildError(f"Symlink source is not allowed: {source}")
    if source.is_file():
        yield source, PurePosixPath(source.name)
        return
    if not source.is_dir():
        raise BuildError(f"Allowlisted source is absent: {source}")
    for candidate in sorted(source.rglob("*"), key=lambda item: item.as_posix()):
        relative = PurePosixPath(candidate.relative_to(source).as_posix())
        if candidate.is_symlink():
            raise BuildError(f"Symlink is not allowed in payload source: {candidate}")
        if _ignored(relative) or candidate.is_dir():
            continue
        if not candidate.is_file():
            raise BuildError(f"Special filesystem object is not allowed: {candidate}")
        yield candidate, relative


def collect_payload(repo_root: Path, manifest: Mapping[str, Any]) -> list[PayloadFile]:
    """Collect payload bytes using only the fixed, manifest-confirmed mapping."""

    _validate_project_manifest(manifest, requested_version=None)
    payload: list[PayloadFile] = []
    target_sources: dict[str, Path] = {}
    casefold_targets: dict[str, str] = {}
    for source_value, target_value in EXPECTED_MAPPINGS:
        source = repo_root / source_value
        source_is_file = source.is_file() and not source.is_symlink()
        for path, relative in _iter_source_files(source):
            if source_is_file:
                target = PurePosixPath(target_value)
            else:
                target = PurePosixPath(target_value) / relative
            target_value_normalized = target.as_posix()
            _safe_archive_name(target_value_normalized)
            if source_value == "workspace-template":
                _validate_template_path(relative)
            if target_value_normalized in {PROJECT_MANIFEST, CHECKSUMS_FILE}:
                raise BuildError(f"Payload source collides with generated integrity file: {path}")
            if target_value_normalized in target_sources:
                raise BuildError(
                    f"Duplicate payload target {target_value_normalized}: "
                    f"{target_sources[target_value_normalized]} and {path}"
                )
            folded = target_value_normalized.casefold()
            if folded in casefold_targets:
                raise BuildError(
                    "Case-insensitive payload collision: "
                    f"{casefold_targets[folded]} and {target_value_normalized}"
                )
            target_sources[target_value_normalized] = path
            casefold_targets[folded] = target_value_normalized
            payload.append(
                PayloadFile(
                    source=path,
                    target=target_value_normalized,
                    data=path.read_bytes(),
                    mode=_normalized_mode(target),
                )
            )
    payload.sort(key=lambda item: item.target)
    names = {item.target for item in payload}
    missing = sorted(ESSENTIAL_FILES - names)
    if missing:
        raise BuildError(f"Release payload is missing essential files: {missing}")
    if not any(name.startswith(".agents/skills/") and name.endswith("/SKILL.md") for name in names):
        raise BuildError("Release payload contains no canonical skills.")
    if not any(name.startswith(".codex/agents/") and name.endswith(".toml") for name in names):
        raise BuildError("Release payload contains no canonical roles.")
    return payload


def _manifest_bytes(payload: Sequence[PayloadFile], version: str, epoch: int) -> bytes:
    generated_at = datetime.fromtimestamp(epoch, tz=UTC).isoformat().replace("+00:00", "Z")
    manifest = {
        "schema_version": 1,
        "package": PACKAGE_NAME,
        "version": version,
        "generated_at_utc": generated_at,
        "layout": "extract-directly-into-workspace-root",
        "files": [
            {
                "path": item.target,
                "size": len(item.data),
                "sha256": sha256_bytes(item.data),
                "mode": f"{item.mode:04o}",
            }
            for item in payload
        ],
    }
    return (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()


def _integrity_payload(
    payload: Sequence[PayloadFile], version: str, epoch: int
) -> list[PayloadFile]:
    manifest_data = _manifest_bytes(payload, version, epoch)
    checksum_items = [(item.target, item.data) for item in payload]
    checksum_items.append((PROJECT_MANIFEST, manifest_data))
    checksum_items.sort(key=lambda item: item[0])
    checksums_data = "".join(
        f"{sha256_bytes(data)}  {name}\n" for name, data in checksum_items
    ).encode()
    return [
        *payload,
        PayloadFile(Path("<generated>"), PROJECT_MANIFEST, manifest_data, 0o644),
        PayloadFile(Path("<generated>"), CHECKSUMS_FILE, checksums_data, 0o644),
    ]


def _zip_datetime(epoch: int) -> tuple[int, int, int, int, int, int]:
    value = datetime.fromtimestamp(epoch, tz=UTC)
    return (value.year, value.month, value.day, value.hour, value.minute, value.second)


def _write_archive(path: Path, files: Sequence[PayloadFile], epoch: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f".{path.name}.tmp")
    if temporary_path.exists():
        temporary_path.unlink()
    try:
        with zipfile.ZipFile(
            temporary_path,
            mode="w",
            compression=ZIP_COMPRESSION,
            allowZip64=True,
            strict_timestamps=True,
        ) as archive:
            for item in sorted(files, key=lambda value: value.target):
                info = zipfile.ZipInfo(item.target, date_time=_zip_datetime(epoch))
                info.create_system = 3
                info.compress_type = ZIP_COMPRESSION
                info.external_attr = (stat.S_IFREG | item.mode) << 16
                archive.writestr(info, item.data)
        temporary_path.replace(path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def _parse_checksum_text(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line_number, line in enumerate(text.splitlines(), start=1):
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if not match:
            raise BuildError(f"Invalid checksum line {line_number}: {line!r}")
        digest, name = match.groups()
        _safe_archive_name(name)
        if name in result:
            raise BuildError(f"Duplicate checksum path: {name}")
        result[name] = digest
    return result


def verify_zip_archive(path: Path, expected_version: str | None = None) -> dict[str, Any]:
    """Verify ZIP safety, normalized metadata, manifest, and checksums."""

    try:
        archive = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as error:
        raise BuildError(f"Cannot open release ZIP {path}: {error}") from error
    with archive:
        infos = archive.infolist()
        names: dict[str, zipfile.ZipInfo] = {}
        casefold_names: dict[str, str] = {}
        timestamp: tuple[int, int, int, int, int, int] | None = None
        total_size = 0
        for info in infos:
            name = info.filename
            _safe_archive_name(name.rstrip("/") if info.is_dir() else name)
            if name in names:
                raise BuildError(f"Duplicate ZIP member: {name}")
            folded = name.casefold()
            if folded in casefold_names:
                raise BuildError(
                    f"Case-insensitive ZIP collision: {casefold_names[folded]} and {name}"
                )
            names[name] = info
            casefold_names[folded] = name
            if info.flag_bits & 0x1:
                raise BuildError(f"Encrypted ZIP member is not allowed: {name}")
            if info.compress_type != ZIP_COMPRESSION:
                raise BuildError(f"Non-canonical ZIP compression on member: {name}")
            unix_mode = (info.external_attr >> 16) & 0xFFFF
            file_type = stat.S_IFMT(unix_mode)
            if file_type not in {0, stat.S_IFREG, stat.S_IFDIR}:
                raise BuildError(f"Symlink or special ZIP member is not allowed: {name}")
            if file_type == stat.S_IFLNK:
                raise BuildError(f"Symlink ZIP member is not allowed: {name}")
            if not info.is_dir() and stat.S_IMODE(unix_mode) not in {0o644, 0o755}:
                raise BuildError(f"Non-normalized permission on ZIP member {name}: {unix_mode:o}")
            if timestamp is None:
                timestamp = info.date_time
            elif info.date_time != timestamp:
                raise BuildError(f"Non-normalized timestamp on ZIP member: {name}")
            total_size += info.file_size
            if total_size > MAX_UNCOMPRESSED_BYTES:
                raise BuildError("Release ZIP exceeds the uncompressed size limit.")
        if list(names) != sorted(names):
            raise BuildError("ZIP members are not in deterministic lexical order.")
        required_integrity = {PROJECT_MANIFEST, CHECKSUMS_FILE}
        if not required_integrity.issubset(names):
            raise BuildError("Release ZIP lacks PACKAGE_MANIFEST.json or CHECKSUMS.sha256.")
        try:
            manifest = json.loads(archive.read(PROJECT_MANIFEST).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise BuildError(f"Invalid release manifest: {error}") from error
        if not isinstance(manifest, dict):
            raise BuildError("Release manifest root must be an object.")
        if manifest.get("schema_version") != 1 or manifest.get("package") != PACKAGE_NAME:
            raise BuildError("Release manifest schema/package mismatch.")
        if manifest.get("layout") != "extract-directly-into-workspace-root":
            raise BuildError("Release manifest layout mismatch.")
        version = manifest.get("version")
        if not isinstance(version, str) or (expected_version and version != expected_version):
            raise BuildError("Release manifest version mismatch.")
        records = manifest.get("files")
        if not isinstance(records, list):
            raise BuildError("Release manifest files must be an array.")
        manifest_names: dict[str, dict[str, Any]] = {}
        for index, record in enumerate(records):
            if not isinstance(record, dict) or set(record) != {
                "path",
                "size",
                "sha256",
                "mode",
            }:
                raise BuildError(f"Invalid release manifest file record at index {index}.")
            name = record.get("path")
            if not isinstance(name, str):
                raise BuildError(f"Manifest path {index} must be a string.")
            _safe_archive_name(name)
            if name in manifest_names:
                raise BuildError(f"Duplicate release manifest path: {name}")
            manifest_names[name] = record
        expected_payload_names = set(names) - required_integrity
        if set(manifest_names) != expected_payload_names:
            missing = sorted(expected_payload_names - set(manifest_names))
            extra = sorted(set(manifest_names) - expected_payload_names)
            raise BuildError(f"Release manifest set mismatch; missing={missing}, extra={extra}")
        for name, record in manifest_names.items():
            data = archive.read(name)
            mode = stat.S_IMODE((names[name].external_attr >> 16) & 0xFFFF)
            if record.get("size") != len(data):
                raise BuildError(f"Release manifest size mismatch: {name}")
            if record.get("sha256") != sha256_bytes(data):
                raise BuildError(f"Release manifest hash mismatch: {name}")
            if record.get("mode") != f"{mode:04o}":
                raise BuildError(f"Release manifest mode mismatch: {name}")
        try:
            checksum_text = archive.read(CHECKSUMS_FILE).decode("utf-8")
        except UnicodeDecodeError as error:
            raise BuildError("CHECKSUMS.sha256 is not UTF-8.") from error
        checksums = _parse_checksum_text(checksum_text)
        expected_checksum_names = set(manifest_names) | {PROJECT_MANIFEST}
        if set(checksums) != expected_checksum_names:
            raise BuildError("CHECKSUMS.sha256 path set differs from the manifest set.")
        for name, expected_digest in checksums.items():
            if sha256_bytes(archive.read(name)) != expected_digest:
                raise BuildError(f"CHECKSUMS.sha256 mismatch: {name}")
    return manifest


def _spdx_id(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9.-]+", "-", value).strip("-.")
    return normalized or "item"


def _runtime_dependencies(repo_root: Path) -> list[tuple[str, str]]:
    path = repo_root / "workspace-template/requirements.txt"
    dependencies: list[tuple[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        value = line.split("#", 1)[0].strip()
        if not value:
            continue
        match = re.fullmatch(r"([A-Za-z0-9_.-]+)(.*)", value)
        if match is None:
            raise BuildError(f"Unsupported runtime dependency declaration: {value!r}")
        name, constraint = match.groups()
        dependencies.append((name, constraint or "NOASSERTION"))
    return sorted(dependencies, key=lambda item: item[0].casefold())


def _write_spdx_sbom(
    repo_root: Path,
    archive: Path,
    manifest: Mapping[str, Any],
    version: str,
    epoch: int,
) -> Path:
    archive_digest = sha256_file(archive)
    package_id = f"SPDXRef-Package-{_spdx_id(PACKAGE_NAME)}"
    records = manifest.get("files")
    if not isinstance(records, list):
        raise BuildError("Cannot create SBOM without release manifest files.")
    files: list[dict[str, Any]] = []
    relationships: list[dict[str, str]] = []
    for record in records:
        if not isinstance(record, dict):
            raise BuildError("Cannot create SBOM from an invalid file record.")
        relative = record.get("path")
        digest = record.get("sha256")
        if not isinstance(relative, str) or not isinstance(digest, str):
            raise BuildError("Cannot create SBOM from an incomplete file record.")
        file_id = f"SPDXRef-File-{_spdx_id(relative)}"
        files.append(
            {
                "SPDXID": file_id,
                "checksums": [{"algorithm": "SHA256", "checksumValue": digest}],
                "copyrightText": "NOASSERTION",
                "fileName": f"./{relative}",
                "licenseConcluded": "NOASSERTION",
                "licenseInfoInFiles": ["NOASSERTION"],
            }
        )
        relationships.append(
            {
                "spdxElementId": package_id,
                "relationshipType": "CONTAINS",
                "relatedSpdxElement": file_id,
            }
        )
    packages: list[dict[str, Any]] = [
        {
            "SPDXID": package_id,
            "checksums": [{"algorithm": "SHA256", "checksumValue": archive_digest}],
            "copyrightText": "NOASSERTION",
            "downloadLocation": (
                f"https://github.com/sergeionlyart/minius_codex_lab/releases/tag/v{version}"
            ),
            "filesAnalyzed": True,
            "licenseConcluded": "Apache-2.0",
            "licenseDeclared": "Apache-2.0",
            "name": PACKAGE_NAME,
            "versionInfo": version,
        }
    ]
    for name, constraint in _runtime_dependencies(repo_root):
        dependency_id = f"SPDXRef-Dependency-{_spdx_id(name)}"
        packages.append(
            {
                "SPDXID": dependency_id,
                "copyrightText": "NOASSERTION",
                "downloadLocation": "NOASSERTION",
                "filesAnalyzed": False,
                "licenseConcluded": "NOASSERTION",
                "licenseDeclared": "NOASSERTION",
                "name": name,
                "versionInfo": constraint,
            }
        )
        relationships.append(
            {
                "spdxElementId": package_id,
                "relationshipType": "DEPENDS_ON",
                "relatedSpdxElement": dependency_id,
            }
        )
    created = datetime.fromtimestamp(epoch, UTC).replace(microsecond=0).isoformat()
    sbom = {
        "SPDXID": "SPDXRef-DOCUMENT",
        "creationInfo": {
            "created": created.replace("+00:00", "Z"),
            "creators": ["Tool: minius_codex_lab deterministic release builder"],
        },
        "dataLicense": "CC0-1.0",
        "documentDescribes": [package_id],
        "documentNamespace": (
            "https://github.com/sergeionlyart/minius_codex_lab/"
            f"releases/tag/v{version}/sbom/{archive_digest}"
        ),
        "files": files,
        "name": f"{PACKAGE_NAME}-{version}",
        "packages": packages,
        "relationships": relationships,
        "spdxVersion": "SPDX-2.3",
    }
    path = archive.with_name(f"{archive.stem}.spdx.json")
    path.write_text(
        json.dumps(sbom, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path


def _validate_distribution_path(relative: PurePosixPath) -> None:
    folded_parts = {part.casefold() for part in relative.parts}
    if folded_parts & FORBIDDEN_ARCHIVE_PARTS:
        raise BuildError(f"Maintainer-only path entered public distribution: {relative}")
    name = relative.name.casefold()
    if name in FORBIDDEN_CREDENTIAL_NAMES or name.startswith(".env."):
        raise BuildError(f"Credential-like file entered public distribution: {relative}")
    if relative.suffix.casefold() in FORBIDDEN_CREDENTIAL_SUFFIXES:
        raise BuildError(f"Credential suffix entered public distribution: {relative}")
    if relative.suffix.casefold() in ARCHIVE_SUFFIXES:
        raise BuildError(f"Nested archive entered public distribution: {relative}")
    if not _is_allowlisted_distribution_path(relative):
        raise BuildError(f"Non-allowlisted path entered public distribution: {relative}")


def _extract_and_check(path: Path, expected_version: str, run_external_checks: bool) -> None:
    verify_zip_archive(path, expected_version=expected_version)
    with tempfile.TemporaryDirectory(prefix="minius-release-extract-") as directory:
        extraction_root = Path(directory) / "workspace"
        extraction_root.mkdir()
        with zipfile.ZipFile(path) as archive:
            expected_names: set[str] = set()
            for info in archive.infolist():
                relative = _safe_archive_name(info.filename)
                if info.is_dir():
                    continue
                destination = extraction_root.joinpath(*relative.parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(archive.read(info))
                os.chmod(destination, stat.S_IMODE((info.external_attr >> 16) & 0xFFFF))
                expected_names.add(relative.as_posix())
        actual_names: set[str] = set()
        for candidate in extraction_root.rglob("*"):
            if candidate.is_symlink():
                raise BuildError(f"Symlink appeared after clean extraction: {candidate}")
            if not candidate.is_file():
                continue
            relative = PurePosixPath(candidate.relative_to(extraction_root).as_posix())
            _validate_distribution_path(relative)
            actual_names.add(relative.as_posix())
        if actual_names != expected_names:
            raise BuildError("Clean extraction file set differs from ZIP members.")
        if run_external_checks:
            _run_runtime_check(
                extraction_root,
                "scripts/validate_workspace.py",
                "--mode",
                "runtime",
                "--root",
                str(extraction_root),
                "--json",
            )
            _run_runtime_check(
                extraction_root,
                "scripts/check_repo_safety.py",
                "--root",
                str(extraction_root),
                "--profile",
                "workspace-local",
                "--json",
            )
            _run_lifecycle_smoke(extraction_root)


def _run_runtime_check(root: Path, script_name: str, *args: str) -> None:
    script = root / script_name
    if not script.is_file():
        raise BuildError(f"Runtime checker is absent after extraction: {script_name}")
    completed = subprocess.run(
        [sys.executable, str(script), *args],
        cwd=root,
        check=False,
        text=True,
        capture_output=True,
        timeout=120,
    )
    if completed.returncode != 0:
        details = completed.stdout.strip() or completed.stderr.strip() or "no diagnostic output"
        raise BuildError(f"Runtime check failed ({script_name}): {details}")


def _run_lifecycle_smoke(root: Path) -> None:
    matter_id = "synthetic-build-check"
    environment = os.environ.copy()
    environment.update(
        {
            "GIT_AUTHOR_NAME": "minius synthetic gate",
            "GIT_AUTHOR_EMAIL": "synthetic-gate@example.invalid",
            "GIT_COMMITTER_NAME": "minius synthetic gate",
            "GIT_COMMITTER_EMAIL": "synthetic-gate@example.invalid",
        }
    )

    def run(label: str, *args: str) -> str:
        completed = subprocess.run(
            args,
            cwd=root,
            check=False,
            text=True,
            capture_output=True,
            timeout=120,
            env=environment,
        )
        if completed.returncode != 0:
            details = completed.stdout.strip() or completed.stderr.strip() or "no output"
            raise BuildError(f"Extracted workspace {label} failed: {details}")
        return completed.stdout

    init_args = (
        sys.executable,
        str(root / "scripts/init_workspace.py"),
        "--memory-mode",
        "local-git",
    )
    run("initialization", *init_args)
    first_commit = run("initial commit lookup", "git", "rev-parse", "HEAD").strip()
    run("idempotent initialization", *init_args)
    if run("initial commit recount", "git", "rev-list", "--count", "HEAD").strip() != "1":
        raise BuildError("Idempotent initialization created an extra commit.")
    if run("branch verification", "git", "branch", "--show-current").strip() != "main":
        raise BuildError("Initialization did not create main as the initial branch.")
    if run("remote verification", "git", "remote").strip():
        raise BuildError("Initialization unexpectedly created a Git remote.")

    run(
        "matter creation",
        sys.executable,
        str(root / "scripts/new_matter.py"),
        "--id",
        matter_id,
        "--title",
        "Synthetic release build check",
        "--classification",
        "PUBLIC",
    )
    matter_file = root / "matters" / matter_id / "MATTER.md"
    if not matter_file.is_file():
        raise BuildError("Lifecycle smoke did not create matters/<id>/MATTER.md.")
    matter_text = matter_file.read_text(encoding="utf-8")
    if (
        matter_id not in matter_text
        or "Synthetic release build check" not in matter_text
        or "PUBLIC" not in matter_text
    ):
        raise BuildError("Lifecycle smoke did not replace required matter placeholders.")
    if "{{MATTER_ID}}" in matter_text or "{{TITLE}}" in matter_text:
        raise BuildError("Lifecycle smoke left required placeholders unresolved.")
    run("matter staging", "git", "add", "--", f"matters/{matter_id}", "memory")
    _run_runtime_check(
        root,
        "scripts/check_repo_safety.py",
        "--profile",
        "workspace-local",
        "--staged",
    )
    run(
        "matter commit",
        "git",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "--no-verify",
        "-m",
        f"matter: initialize {matter_id}",
    )
    start_output = run(
        "session start",
        sys.executable,
        str(root / "scripts/start_session.py"),
        "--slug",
        "release-check",
        "--matter",
        matter_id,
        "--objective",
        "Verify the synthetic release lifecycle",
        "--create-branch",
    )
    session_lines = [line for line in start_output.splitlines() if line.startswith("session:")]
    if len(session_lines) != 1:
        raise BuildError("Lifecycle smoke did not report exactly one session ID.")
    session_id = session_lines[0].split(":", 1)[1].strip()
    run(
        "session finish",
        sys.executable,
        str(root / "scripts/finish_session.py"),
        "--session",
        session_id,
        "--summary",
        "Synthetic lifecycle completed.",
        "--next-action",
        "Discard this temporary workspace.",
        "--tests",
        "Release build lifecycle gate passed.",
    )
    if not (root / "memory/sessions" / f"{session_id}.md").is_file():
        raise BuildError("Lifecycle smoke did not create the session handoff.")
    root_commits = run("initial commit stability", "git", "rev-list", "--max-parents=0", "HEAD")
    if root_commits.strip() != first_commit:
        raise BuildError("Lifecycle smoke lost or replaced the initial commit.")
    _run_runtime_check(
        root,
        "scripts/validate_workspace.py",
        "--mode",
        "operational",
        "--root",
        str(root),
    )
    _run_runtime_check(
        root,
        "scripts/check_repo_safety.py",
        "--profile",
        "workspace-local",
    )
    _run_runtime_check(
        root,
        "scripts/run_synthetic_e2e.py",
        "--out-dir",
        str(root / "matters" / matter_id / "outputs" / "synthetic-e2e"),
    )


def _build_once(
    repo_root: Path,
    output_dir: Path,
    requested_version: str | None,
    source_date_epoch: int | None,
    run_external_checks: bool,
) -> BuildResult:
    project_manifest = _load_json_object(repo_root / PROJECT_MANIFEST)
    version, fallback_epoch = _validate_project_manifest(project_manifest, requested_version)
    epoch = _resolve_epoch(source_date_epoch, fallback_epoch)
    payload = collect_payload(repo_root, project_manifest)
    archive_payload = _integrity_payload(payload, version, epoch)
    archive_path = output_dir / f"{PACKAGE_NAME}-v{version}.zip"
    _write_archive(archive_path, archive_payload, epoch)
    _extract_and_check(archive_path, version, run_external_checks)
    digest = sha256_file(archive_path)
    checksum_path = archive_path.with_name(f"{archive_path.name}.sha256")
    checksum_path.write_text(
        f"{digest}  {archive_path.name}\n",
        encoding="utf-8",
        newline="\n",
    )
    manifest = verify_zip_archive(archive_path, expected_version=version)
    sbom_path = _write_spdx_sbom(repo_root, archive_path, manifest, version, epoch)
    return BuildResult(
        archive=archive_path,
        checksum_file=checksum_path,
        sbom_file=sbom_path,
        sha256=digest,
        file_count=len(payload),
        source_date_epoch=epoch,
    )


def build_release(
    repo_root: Path,
    output_dir: Path,
    version: str | None = None,
    source_date_epoch: int | None = None,
    *,
    check_reproducibility: bool = False,
    run_external_checks: bool = True,
) -> BuildResult:
    """Build a verified release, optionally comparing two independent builds."""

    repo_root = repo_root.resolve()
    output_dir = output_dir.resolve()
    if check_reproducibility:
        with (
            tempfile.TemporaryDirectory(prefix="minius-release-repro-a-") as first_dir,
            tempfile.TemporaryDirectory(prefix="minius-release-repro-b-") as second_dir,
        ):
            first = _build_once(
                repo_root,
                Path(first_dir),
                version,
                source_date_epoch,
                run_external_checks,
            )
            second = _build_once(
                repo_root,
                Path(second_dir),
                version,
                source_date_epoch,
                run_external_checks,
            )
            if (
                first.sha256 != second.sha256
                or first.archive.read_bytes() != second.archive.read_bytes()
                or first.sbom_file.read_bytes() != second.sbom_file.read_bytes()
            ):
                raise BuildError("Two clean builds are not byte-for-byte reproducible.")
            output_dir.mkdir(parents=True, exist_ok=True)
            final_archive = output_dir / first.archive.name
            final_checksum = output_dir / first.checksum_file.name
            final_sbom = output_dir / first.sbom_file.name
            shutil.copyfile(first.archive, final_archive)
            shutil.copyfile(first.checksum_file, final_checksum)
            shutil.copyfile(first.sbom_file, final_sbom)
            return BuildResult(
                archive=final_archive,
                checksum_file=final_checksum,
                sbom_file=final_sbom,
                sha256=first.sha256,
                file_count=first.file_count,
                source_date_epoch=first.source_date_epoch,
            )
    return _build_once(
        repo_root,
        output_dir,
        version,
        source_date_epoch,
        run_external_checks,
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", help="Release version; must equal PACKAGE_MANIFEST.json.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("dist"),
        help="Destination directory (default: dist).",
    )
    parser.add_argument(
        "--source-date-epoch",
        type=int,
        help="Override SOURCE_DATE_EPOCH for this build.",
    )
    parser.add_argument(
        "--check-reproducibility",
        "--check-reproducible",
        action="store_true",
        dest="check_reproducibility",
        help="Build twice in clean directories and require identical ZIP bytes.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = build_release(
            repository_root(),
            args.output_dir,
            args.version,
            args.source_date_epoch,
            check_reproducibility=args.check_reproducibility,
        )
    except (BuildError, OSError, subprocess.SubprocessError, zipfile.BadZipFile) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(f"archive: {result.archive}")
    print(f"checksum: {result.checksum_file}")
    print(f"sbom: {result.sbom_file}")
    print(f"sha256: {result.sha256}")
    print(f"payload_files: {result.file_count}")
    print(f"source_date_epoch: {result.source_date_epoch}")
    if args.check_reproducibility:
        print("reproducibility: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
