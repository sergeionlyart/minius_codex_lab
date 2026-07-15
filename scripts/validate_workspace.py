#!/usr/bin/env python3
"""Validate the public upstream or an extracted runtime workspace."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import tomllib
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any

PROJECT_NAME = "minius_codex_lab"
PACKAGE_NAME = "minius_codex_lab-workspace"
EXPECTED_MAPPINGS = (
    ("workspace-template", ""),
    (".agents/skills", ".agents/skills"),
    (".codex/agents", ".codex/agents"),
    ("tools/verifiable_document", "tools/verifiable_document"),
    ("scripts/check_repo_safety.py", "scripts/check_repo_safety.py"),
    ("scripts/validate_workspace.py", "scripts/validate_workspace.py"),
    ("LICENSE", "LICENSE"),
)

UPSTREAM_REQUIRED_PATHS = (
    ".agents/skills",
    ".codex/agents",
    ".codex/config.toml",
    ".github/ISSUE_TEMPLATE/bug.yml",
    ".github/ISSUE_TEMPLATE/config.yml",
    ".github/ISSUE_TEMPLATE/feature.yml",
    ".github/ISSUE_TEMPLATE/skill-proposal.yml",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/dependabot.yml",
    ".github/workflows/ci.yml",
    ".github/workflows/release.yml",
    ".gitignore",
    "AGENTS.md",
    "ARCHITECTURE.md",
    "CHANGELOG.md",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "GOVERNANCE.md",
    "LICENSE",
    "PACKAGE_MANIFEST.json",
    "README.md",
    "ROADMAP.md",
    "SECURITY.md",
    "SUPPORT.md",
    "docs/COMPATIBILITY.md",
    "docs/DEVELOPMENT.md",
    "docs/PROVENANCE.md",
    "docs/PUBLIC_REPOSITORY_MODEL.md",
    "docs/RELEASING.md",
    "docs/THREAT_MODEL.md",
    "pyproject.toml",
    "scripts/build_release.py",
    "scripts/check_repo_safety.py",
    "scripts/codex_runtime_probe.py",
    "scripts/validate_workspace.py",
    "tests",
    "tools/verifiable_document",
    "workspace-template/.codex/config.toml",
    "workspace-template/.codex/hooks.json",
    "workspace-template/AGENTS.md",
    "workspace-template/README.md",
    "workspace-template/requirements.txt",
    "workspace-template/docs/CODEX_SMOKE_TEST.md",
    "workspace-template/docs/INSTALL_WINDOWS_POWERSHELL.md",
    "workspace-template/matters/_template/MATTER.md",
    "workspace-template/memory/CURRENT.md",
    "workspace-template/scripts/init_workspace.py",
    "workspace-template/scripts/new_matter.py",
    "workspace-template/scripts/run_synthetic_e2e.py",
)

RUNTIME_REQUIRED_PATHS = (
    ".agents/skills",
    ".codex/agents",
    ".codex/config.toml",
    ".codex/hooks.json",
    "AGENTS.md",
    "CHECKSUMS.sha256",
    "LICENSE",
    "PACKAGE_MANIFEST.json",
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
)

SKILL_CONTRACT_MARKERS = (
    "job-to-be-done",
    "inputs",
    "outputs",
    "evidence and safety",
    "stop conditions",
    "acceptance test",
)
ROLE_CONTRACT_MARKERS = ("allowed actions", "prohibited actions", "handoff")
READ_ONLY_ROLES = {
    "case_law_analyst",
    "eu_law_analyst",
    "evidence_auditor",
    "policy_impact_analyst",
    "privacy_reviewer",
    "ua_law_researcher",
}
EXPECTED_SKILL_NAMES = {
    "case-law-analysis",
    "eu-acquis-analysis",
    "format-monitoring-report",
    "legal-drafting",
    "legal-monitoring",
    "legal-qa-audit",
    "matter-intake",
    "quantitative-impact-analysis",
    "redaction-and-disclosure",
    "session-memory-handoff",
    "source-provenance",
    "ukrainian-legal-research",
    "verifiable-legal-document",
}
EXPECTED_ROLE_NAMES = {
    "case_law_analyst",
    "document_engineer",
    "eu_law_analyst",
    "evidence_auditor",
    "legal_coordinator",
    "legal_drafter",
    "policy_impact_analyst",
    "privacy_reviewer",
    "quantitative_analyst",
    "ua_law_researcher",
}
EXCLUDED_SCAN_PARTS = {
    ".bootstrap",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tmp",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "venv",
}
EXCLUDED_SCAN_PATHS = {
    "CODEX_MAINTAINER_BOOTSTRAP_MINIUS_CODEX_LAB_RU.md",
    "CODEX_MAINTAINER_BOOTSTRAP_MINIUS_CODEX_LAB_RU.md.sha256",
    "CODEX_SETUP_PROMPT_RU.md",
}


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    path: str
    message: str


def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _add(findings: list[Finding], code: str, path: str, message: str) -> None:
    findings.append(Finding("error", code, path, message))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_relative(value: str) -> bool:
    if not value or value in {".", ".."} or "\\" in value or "\x00" in value:
        return False
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        return False
    return not (path.parts and re.fullmatch(r"[A-Za-z]:", path.parts[0]))


def _iter_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        try:
            relative = path.relative_to(root)
        except ValueError:
            continue
        if set(relative.parts) & EXCLUDED_SCAN_PARTS or relative.as_posix() in EXCLUDED_SCAN_PATHS:
            continue
        if path.is_file():
            yield path


def _load_json(path: Path, findings: list[Finding]) -> Any:
    relative = path.as_posix()
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        _add(findings, "invalid_json", relative, str(error))
        return None


def _load_toml(path: Path, findings: list[Finding]) -> dict[str, Any] | None:
    relative = path.as_posix()
    try:
        with path.open("rb") as stream:
            value = tomllib.load(stream)
    except (OSError, tomllib.TOMLDecodeError) as error:
        _add(findings, "invalid_toml", relative, str(error))
        return None
    if not isinstance(value, dict):
        _add(findings, "invalid_toml", relative, "TOML root must be a table.")
        return None
    return value


def _load_yaml(path: Path, findings: list[Finding]) -> Any:
    relative = path.as_posix()
    try:
        import yaml
    except ImportError:
        _add(
            findings,
            "yaml_dependency_missing",
            relative,
            "Install the declared PyYAML development dependency.",
        )
        return None
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as error:
        _add(findings, "invalid_yaml", relative, str(error))
        return None


def _validate_markdown(path: Path, relative: str, findings: list[Finding]) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        _add(findings, "invalid_markdown", relative, str(error))
        return
    if text and not text.endswith("\n"):
        _add(findings, "markdown_final_newline", relative, "Markdown must end with a newline.")
    active_fence: tuple[str, int, int] | None = None
    for line_number, line in enumerate(text.splitlines(), 1):
        match = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if match is None:
            continue
        marker = match.group(1)
        if active_fence is None:
            active_fence = (marker[0], len(marker), line_number)
        elif marker[0] == active_fence[0] and len(marker) >= active_fence[1]:
            active_fence = None
    if active_fence is not None:
        _add(
            findings,
            "markdown_unclosed_fence",
            relative,
            f"Code fence opened on line {active_fence[2]} is not closed.",
        )


def _read_frontmatter(path: Path) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("Missing opening YAML frontmatter delimiter.")
    try:
        end = next(index for index, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration as error:
        raise ValueError("Missing closing YAML frontmatter delimiter.") from error
    source = "\n".join(lines[1:end]) + "\n"
    try:
        import yaml
    except ImportError as error:
        raise ValueError("Install the declared PyYAML dependency.") from error
    try:
        node = yaml.compose(source, Loader=yaml.SafeLoader)
        value = yaml.safe_load(source)
    except yaml.YAMLError as error:
        raise ValueError(f"Invalid YAML frontmatter: {error}") from error
    if not isinstance(node, yaml.MappingNode) or not isinstance(value, dict):
        raise ValueError("YAML frontmatter root must be a mapping.")
    seen: set[str] = set()
    for key_node, _ in node.value:
        if not isinstance(key_node, yaml.ScalarNode) or key_node.tag != "tag:yaml.org,2002:str":
            raise ValueError("Frontmatter keys must be plain strings; merges are not allowed.")
        key = key_node.value
        if key in seen:
            raise ValueError(f"Duplicate frontmatter key: {key}")
        seen.add(key)
    result: dict[str, str] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not isinstance(item, str) or not item.strip():
            raise ValueError("Frontmatter keys and values must be non-empty strings.")
        result[key] = item.strip()
    return result


def _declared_version(root: Path, findings: list[Finding]) -> str:
    path = root / "PACKAGE_MANIFEST.json"
    if not path.is_file():
        return ""
    value = _load_json(path, findings)
    version = value.get("version") if isinstance(value, dict) else None
    if not isinstance(version, str) or not re.fullmatch(
        r"[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z][0-9A-Za-z.-]*)?",
        version,
    ):
        _add(
            findings,
            "manifest_version",
            "PACKAGE_MANIFEST.json",
            "version must be a supported semantic-version string.",
        )
        return ""
    return version


def _validate_required_paths(root: Path, mode: str, findings: list[Finding]) -> None:
    required = UPSTREAM_REQUIRED_PATHS if mode == "upstream" else RUNTIME_REQUIRED_PATHS
    for relative in required:
        if not (root / relative).exists():
            _add(findings, "missing_path", relative, f"Required {mode} path is absent.")


def _validate_symlinks(root: Path, findings: list[Finding]) -> None:
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if set(relative.parts) & EXCLUDED_SCAN_PARTS:
            continue
        if path.is_symlink():
            _add(
                findings,
                "symlink_not_allowed",
                relative.as_posix(),
                "Public source and runtime payloads must not contain symlinks.",
            )


def _validate_skills(root: Path, findings: list[Finding]) -> int:
    skills_root = root / ".agents/skills"
    if not skills_root.is_dir():
        return 0
    names: list[str] = []
    count = 0
    skill_dirs = sorted(path for path in skills_root.iterdir() if path.is_dir())
    inventory = {path.name for path in skill_dirs}
    if inventory != EXPECTED_SKILL_NAMES:
        _add(
            findings,
            "skill_inventory",
            ".agents/skills",
            f"missing={sorted(EXPECTED_SKILL_NAMES - inventory)}; "
            f"extra={sorted(inventory - EXPECTED_SKILL_NAMES)}",
        )
    for skill_dir in skill_dirs:
        skill_path = skill_dir / "SKILL.md"
        relative = skill_path.relative_to(root).as_posix()
        if not skill_path.is_file():
            _add(findings, "skill_missing_file", relative, "Skill directory lacks SKILL.md.")
            continue
        try:
            frontmatter = _read_frontmatter(skill_path)
            text = skill_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError, ValueError) as error:
            _add(findings, "skill_frontmatter", relative, str(error))
            continue
        if set(frontmatter) != {"name", "description"}:
            _add(
                findings,
                "skill_frontmatter_fields",
                relative,
                "Frontmatter must contain exactly name and description.",
            )
        name = frontmatter.get("name", "")
        description = frontmatter.get("description", "")
        names.append(name)
        if name != skill_dir.name or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
            _add(
                findings,
                "skill_name",
                relative,
                "Skill name must equal its kebab-case directory.",
            )
        if len(description) < 80:
            _add(findings, "skill_description", relative, "Skill description is too short.")
        if not re.search(r"не\s+(?:использ|запуска)|do not use|don't use", description, re.I):
            _add(
                findings,
                "skill_non_trigger",
                relative,
                "Description must state when the skill must not run.",
            )
        contract_match = re.search(r"(?im)^##\s+contract\s*$", text)
        if contract_match is None:
            _add(findings, "skill_contract", relative, "Missing canonical ## Contract section.")
        else:
            contract = text[contract_match.end() :].casefold()
            for marker in SKILL_CONTRACT_MARKERS:
                if marker.casefold() not in contract:
                    _add(
                        findings,
                        "skill_contract_marker",
                        relative,
                        f"Contract is missing marker: {marker}.",
                    )
        for reference in sorted(set(re.findall(r"references/[A-Za-z0-9._/-]+", text))):
            cleaned = reference.rstrip(".,;:)")
            if not (skill_dir / cleaned).is_file():
                _add(
                    findings,
                    "skill_reference_missing",
                    relative,
                    f"Referenced skill resource is absent: {cleaned}.",
                )
        count += 1
    for name in sorted(set(names)):
        if names.count(name) > 1:
            _add(findings, "duplicate_skill", ".agents/skills", f"Duplicate skill name: {name}")
    return count


def _validate_roles(root: Path, findings: list[Finding]) -> int:
    roles_root = root / ".codex/agents"
    if not roles_root.is_dir():
        return 0
    names: list[str] = []
    role_values: dict[str, dict[str, Any]] = {}
    role_paths = sorted(roles_root.glob("*.toml"))
    inventory = {path.stem.replace("-", "_") for path in role_paths}
    if inventory != EXPECTED_ROLE_NAMES:
        _add(
            findings,
            "role_inventory",
            ".codex/agents",
            f"missing={sorted(EXPECTED_ROLE_NAMES - inventory)}; "
            f"extra={sorted(inventory - EXPECTED_ROLE_NAMES)}",
        )
    for role_path in role_paths:
        relative = role_path.relative_to(root).as_posix()
        role = _load_toml(role_path, findings)
        if role is None:
            continue
        for key in ("name", "description", "developer_instructions", "sandbox_mode", "web_search"):
            if not isinstance(role.get(key), str) or not role[key].strip():
                _add(findings, "role_required_field", relative, f"Missing string field: {key}.")
        name = role.get("name", "")
        if not isinstance(name, str):
            continue
        names.append(name)
        role_values[name] = role
        expected_name = role_path.stem.replace("-", "_")
        if name != expected_name or not re.fullmatch(r"[a-z0-9]+(?:_[a-z0-9]+)*", name):
            _add(findings, "role_name", relative, "Role name must match its snake_case filename.")
        description = role.get("description", "")
        if isinstance(description, str) and len(description) < 40:
            _add(findings, "role_description", relative, "Role description is too short.")
        sandbox_mode = role.get("sandbox_mode")
        if sandbox_mode not in {"read-only", "workspace-write"}:
            _add(findings, "role_sandbox_mode", relative, "Unsupported sandbox_mode.")
        if name in READ_ONLY_ROLES and sandbox_mode != "read-only":
            _add(findings, "role_read_only", relative, "Research/audit role must be read-only.")
        if role.get("web_search") not in {"disabled", "indexed", "live"}:
            _add(findings, "role_web_search", relative, "Unsupported web_search mode.")
        instructions = role.get("developer_instructions", "")
        if isinstance(instructions, str):
            folded = instructions.casefold()
            for marker in ROLE_CONTRACT_MARKERS:
                if marker.casefold() not in folded:
                    _add(
                        findings,
                        "role_contract_marker",
                        relative,
                        f"developer_instructions is missing marker: {marker}.",
                    )
    for name in sorted(set(names)):
        if names.count(name) > 1:
            _add(findings, "duplicate_role", ".codex/agents", f"Duplicate role name: {name}")
    coordinator = role_values.get("legal_coordinator", {}).get("developer_instructions", "")
    if coordinator and not re.search(
        r"одн\w*\s+владельц|single\s+(?:explicit\s+)?owner", str(coordinator), re.I
    ):
        _add(
            findings,
            "role_single_owner",
            ".codex/agents/legal-coordinator.toml",
            "Coordinator must require one owner for every shared final file.",
        )
    drafter = role_values.get("legal_drafter")
    if drafter is None or drafter.get("sandbox_mode") != "workspace-write":
        _add(
            findings,
            "role_final_writer",
            ".codex/agents/legal-drafter.toml",
            "A single explicit workspace-write final-text role is required.",
        )
    return len(role_values)


def _validate_hooks(value: Any, relative: str, findings: list[Finding]) -> None:
    if (
        not isinstance(value, dict)
        or set(value) != {"hooks"}
        or not isinstance(value.get("hooks"), dict)
    ):
        _add(findings, "hooks_structure", relative, "hooks.json must contain one hooks object.")
        return
    hooks = value["hooks"]
    if not hooks:
        _add(findings, "hooks_structure", relative, "hooks object must not be empty.")
    for event, matchers in hooks.items():
        if not isinstance(event, str) or not isinstance(matchers, list):
            _add(findings, "hooks_structure", relative, "Hook event must map to an array.")
            continue
        for matcher in matchers:
            if not isinstance(matcher, dict) or not isinstance(matcher.get("hooks"), list):
                _add(findings, "hooks_structure", relative, "Hook matcher lacks hooks array.")
                continue
            for hook in matcher["hooks"]:
                if not isinstance(hook, dict):
                    _add(findings, "hooks_structure", relative, "Hook entry must be an object.")
                    continue
                if hook.get("type") != "command" or not isinstance(hook.get("command"), str):
                    _add(findings, "hooks_structure", relative, "Hook must be a command hook.")
                timeout = hook.get("timeout")
                if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout <= 0:
                    _add(findings, "hooks_structure", relative, "Hook timeout must be positive.")


def _validate_config(value: Mapping[str, Any], relative: str, findings: list[Finding]) -> None:
    if value.get("approval_policy") != "on-request":
        _add(findings, "config_approval", relative, "approval_policy must be on-request.")
    if value.get("sandbox_mode") != "workspace-write":
        _add(findings, "config_sandbox", relative, "sandbox_mode must be workspace-write.")
    sandbox = value.get("sandbox_workspace_write")
    if not isinstance(sandbox, dict) or sandbox.get("network_access") is not False:
        _add(findings, "config_network", relative, "Shell network access must default to false.")
    agents = value.get("agents")
    if not isinstance(agents, dict) or not isinstance(agents.get("max_threads"), int):
        _add(findings, "config_agents", relative, "agents.max_threads must be an integer.")


def _validate_pyproject(
    value: Mapping[str, Any],
    relative: str,
    version: str,
    findings: list[Finding],
) -> None:
    project = value.get("project")
    if not isinstance(project, dict):
        _add(findings, "pyproject_project", relative, "Missing [project] table.")
    elif project.get("name") != PROJECT_NAME or project.get("version") != version:
        _add(
            findings,
            "pyproject_project",
            relative,
            "Project name/version must match the public project manifest.",
        )
    if not isinstance(project, dict) or project.get("requires-python") != ">=3.11":
        _add(findings, "pyproject_python", relative, "project.requires-python must be >=3.11.")
    optional = project.get("optional-dependencies") if isinstance(project, dict) else None
    development = optional.get("dev") if isinstance(optional, dict) else None
    if not isinstance(development, list) or not any(
        isinstance(item, str) and item.casefold().startswith("pyyaml") for item in development
    ):
        _add(
            findings,
            "pyproject_yaml_dependency",
            relative,
            "project.optional-dependencies.dev must declare PyYAML.",
        )
    tool = value.get("tool")
    if not isinstance(tool, dict):
        _add(findings, "pyproject_tools", relative, "pyproject.toml lacks [tool] tables.")
        return
    ruff = tool.get("ruff")
    pytest = tool.get("pytest")
    if not isinstance(ruff, dict) or ruff.get("target-version") != "py311":
        _add(findings, "pyproject_ruff", relative, "Ruff target-version must be py311.")
    if not isinstance(pytest, dict) or not isinstance(pytest.get("ini_options"), dict):
        _add(findings, "pyproject_pytest", relative, "Missing pytest.ini_options.")


def _validate_serialized_files(
    root: Path,
    version: str,
    findings: list[Finding],
) -> tuple[int, int, int]:
    python_count = 0
    yaml_count = 0
    markdown_count = 0
    for path in _iter_files(root):
        relative = path.relative_to(root).as_posix()
        if path.suffix == ".json":
            value = _load_json(path, findings)
            if relative.endswith(".codex/hooks.json") and value is not None:
                _validate_hooks(value, relative, findings)
            if (
                relative == "tools/verifiable_document/schema.json"
                and value is not None
                and (not isinstance(value, dict) or value.get("type") != "object")
            ):
                _add(findings, "document_schema", relative, "Schema root type must be object.")
        elif path.suffix == ".toml":
            value = _load_toml(path, findings)
            if value is None:
                continue
            if relative.endswith(".codex/config.toml"):
                _validate_config(value, relative, findings)
            if relative == "pyproject.toml":
                _validate_pyproject(value, relative, version, findings)
        elif path.suffix.casefold() in {".yaml", ".yml"}:
            yaml_count += 1
            value = _load_yaml(path, findings)
            if value is not None and not isinstance(value, dict):
                _add(findings, "yaml_root", relative, "YAML root must be a mapping.")
        elif path.suffix.casefold() == ".md":
            markdown_count += 1
            _validate_markdown(path, relative, findings)
        elif path.suffix == ".py":
            python_count += 1
            try:
                ast.parse(path.read_text(encoding="utf-8"), filename=relative)
            except (OSError, UnicodeDecodeError, SyntaxError) as error:
                _add(findings, "python_syntax", relative, str(error))
    return python_count, yaml_count, markdown_count


def _validate_project_manifest(root: Path, version: str, findings: list[Finding]) -> None:
    path = root / "PACKAGE_MANIFEST.json"
    if not path.is_file():
        return
    value = _load_json(path, findings)
    if not isinstance(value, dict):
        return
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
    if set(value) != expected_keys:
        _add(findings, "project_manifest_schema", "PACKAGE_MANIFEST.json", "Unexpected keys.")
    expected_scalars = {
        "schema_version": 1,
        "project": PROJECT_NAME,
        "package": PACKAGE_NAME,
        "version": version,
        "layout": "workspace-template-overlay",
        "release_asset": f"{PACKAGE_NAME}-v{version}.zip",
    }
    for key, expected in expected_scalars.items():
        if value.get(key) != expected:
            _add(
                findings,
                "project_manifest_value",
                "PACKAGE_MANIFEST.json",
                f"{key} must equal {expected!r}.",
            )
    epoch = value.get("default_source_date_epoch")
    if not isinstance(epoch, int) or isinstance(epoch, bool) or epoch < 315532800:
        _add(
            findings,
            "project_manifest_epoch",
            "PACKAGE_MANIFEST.json",
            "default_source_date_epoch must be a ZIP-supported Unix timestamp.",
        )
    mappings = value.get("payload_mappings")
    normalized: list[tuple[str, str]] = []
    if isinstance(mappings, list):
        for item in mappings:
            if isinstance(item, dict) and set(item) == {"source", "target"}:
                source = item.get("source")
                target = item.get("target")
                if isinstance(source, str) and isinstance(target, str):
                    normalized.append((source, target))
                    continue
            _add(
                findings,
                "project_manifest_mapping",
                "PACKAGE_MANIFEST.json",
                "Every payload mapping must have string source and target.",
            )
    else:
        _add(
            findings,
            "project_manifest_mapping",
            "PACKAGE_MANIFEST.json",
            "payload_mappings must be an array.",
        )
    if tuple(normalized) != EXPECTED_MAPPINGS:
        _add(
            findings,
            "project_manifest_mapping",
            "PACKAGE_MANIFEST.json",
            "payload_mappings differ from the fixed public allowlist.",
        )


def _parse_checksums(path: Path, findings: list[Finding]) -> dict[str, str]:
    result: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        _add(findings, "checksums_read", "CHECKSUMS.sha256", str(error))
        return result
    for number, line in enumerate(lines, 1):
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if not match:
            _add(findings, "checksum_format", f"CHECKSUMS.sha256:{number}", line)
            continue
        digest, relative = match.groups()
        if not _safe_relative(relative):
            _add(findings, "checksum_path", f"CHECKSUMS.sha256:{number}", relative)
            continue
        if relative in result:
            _add(findings, "checksum_duplicate", "CHECKSUMS.sha256", relative)
        result[relative] = digest
    return result


def _validate_runtime_manifest(root: Path, version: str, findings: list[Finding]) -> int:
    manifest_path = root / "PACKAGE_MANIFEST.json"
    checksum_path = root / "CHECKSUMS.sha256"
    if not manifest_path.is_file() or not checksum_path.is_file():
        return 0
    manifest = _load_json(manifest_path, findings)
    if not isinstance(manifest, dict):
        return 0
    if set(manifest) != {
        "schema_version",
        "package",
        "version",
        "generated_at_utc",
        "layout",
        "files",
    }:
        _add(findings, "runtime_manifest_schema", "PACKAGE_MANIFEST.json", "Unexpected keys.")
    expected = {
        "schema_version": 1,
        "package": PACKAGE_NAME,
        "version": version,
        "layout": "extract-directly-into-workspace-root",
    }
    for key, expected_value in expected.items():
        if manifest.get(key) != expected_value:
            _add(
                findings,
                "runtime_manifest_value",
                "PACKAGE_MANIFEST.json",
                f"{key} must equal {expected_value!r}.",
            )
    records = manifest.get("files")
    if not isinstance(records, list):
        _add(findings, "runtime_manifest_files", "PACKAGE_MANIFEST.json", "files must be an array.")
        return 0
    declared: dict[str, dict[str, Any]] = {}
    for index, record in enumerate(records):
        pointer = f"PACKAGE_MANIFEST.json#/files/{index}"
        if not isinstance(record, dict) or set(record) != {"path", "size", "sha256", "mode"}:
            _add(findings, "runtime_manifest_record", pointer, "Invalid file record.")
            continue
        relative = record.get("path")
        if not isinstance(relative, str) or not _safe_relative(relative):
            _add(findings, "runtime_manifest_path", pointer, str(relative))
            continue
        if relative in declared:
            _add(findings, "runtime_manifest_duplicate", "PACKAGE_MANIFEST.json", relative)
        declared[relative] = record
        path = root / relative
        if not path.is_file() or path.is_symlink():
            _add(findings, "runtime_manifest_missing", relative, "Declared regular file is absent.")
            continue
        if record.get("size") != path.stat().st_size:
            _add(findings, "runtime_manifest_size", relative, "Declared size differs.")
        if record.get("sha256") != _sha256(path):
            _add(findings, "runtime_manifest_hash", relative, "Declared SHA-256 differs.")
        if record.get("mode") not in {"0644", "0755"}:
            _add(
                findings,
                "runtime_manifest_mode",
                relative,
                "Declared mode must be normalized to 0644 or 0755.",
            )
    actual = {
        path.relative_to(root).as_posix()
        for path in _iter_files(root)
        if path.name not in {"PACKAGE_MANIFEST.json", "CHECKSUMS.sha256"}
    }
    if set(declared) != actual:
        _add(
            findings,
            "runtime_manifest_exact_set",
            "PACKAGE_MANIFEST.json",
            f"missing={sorted(actual - set(declared))}; extra={sorted(set(declared) - actual)}",
        )
    checksums = _parse_checksums(checksum_path, findings)
    expected_checksum_paths = set(declared) | {"PACKAGE_MANIFEST.json"}
    if set(checksums) != expected_checksum_paths:
        _add(
            findings,
            "checksum_exact_set",
            "CHECKSUMS.sha256",
            "Checksum paths differ from manifest paths plus PACKAGE_MANIFEST.json.",
        )
    for relative, digest in checksums.items():
        path = root / relative
        if path.is_file() and _sha256(path) != digest:
            _add(findings, "checksum_mismatch", relative, "SHA-256 differs from checksum file.")
    return len(declared)


def _validate_upstream_invariants(root: Path, version: str, findings: list[Finding]) -> None:
    maintainer_agents = root / "AGENTS.md"
    runtime_agents = root / "workspace-template/AGENTS.md"
    if (
        maintainer_agents.is_file()
        and runtime_agents.is_file()
        and maintainer_agents.read_bytes() == runtime_agents.read_bytes()
    ):
        _add(
            findings,
            "agents_not_separated",
            "workspace-template/AGENTS.md",
            "Maintainer and runtime instructions must differ.",
        )
    for relative in ("README.md", "CHANGELOG.md"):
        path = root / relative
        if path.is_file() and version not in path.read_text(encoding="utf-8"):
            _add(findings, "version_not_documented", relative, f"Missing {version}.")
    release_note = root / "docs" / "releases" / f"v{version}.md"
    if not release_note.is_file():
        _add(
            findings,
            "release_notes_missing",
            release_note.relative_to(root).as_posix(),
            "Canonical manifest version requires matching release notes.",
        )
    matters = root / "workspace-template/matters"
    if matters.is_dir():
        allowed = {"_template", "AGENTS.md", "README.md"}
        for child in matters.iterdir():
            if child.name not in allowed:
                _add(
                    findings,
                    "runtime_real_matter",
                    child.relative_to(root).as_posix(),
                    "Only matters/_template may be tracked upstream.",
                )
    sessions = root / "workspace-template/memory/sessions"
    if sessions.is_dir():
        for child in sessions.iterdir():
            if child.name not in {".gitkeep", "README.md"}:
                _add(
                    findings,
                    "runtime_session_memory",
                    child.relative_to(root).as_posix(),
                    "Session memory cannot be tracked upstream.",
                )


def validate_workspace(root: Path, mode: str) -> dict[str, Any]:
    if mode not in {"upstream", "runtime", "operational"}:
        raise ValueError(f"Unsupported validation mode: {mode}")
    root = root.resolve()
    findings: list[Finding] = []
    version = _declared_version(root, findings)
    _validate_required_paths(root, mode, findings)
    _validate_symlinks(root, findings)
    skills = _validate_skills(root, findings)
    roles = _validate_roles(root, findings)
    python_files, yaml_files, markdown_files = _validate_serialized_files(
        root,
        version,
        findings,
    )
    manifest_files = 0
    if mode == "upstream":
        _validate_project_manifest(root, version, findings)
        _validate_upstream_invariants(root, version, findings)
    elif mode == "runtime":
        manifest_files = _validate_runtime_manifest(root, version, findings)
    return {
        "root": str(root),
        "mode": mode,
        "version": version,
        "valid": not findings,
        "metrics": {
            "skills": skills,
            "roles": roles,
            "python_files": python_files,
            "yaml_files": yaml_files,
            "markdown_files": markdown_files,
            "manifest_files": manifest_files,
        },
        "findings": [asdict(finding) for finding in findings],
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=("upstream", "runtime", "operational"),
        default="runtime",
        help=(
            "Validation contract: runtime verifies a pristine release exactly; "
            "operational validates an initialized mutable workspace."
        ),
    )
    parser.add_argument("--root", type=Path, help="Root to validate; defaults to script parent.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable result.")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.root if args.root is not None else repository_root()
    result = validate_workspace(root, args.mode)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        state = "PASS" if result["valid"] else "FAIL"
        print(f"{state}: mode={args.mode} root={result['root']}")
        print(" ".join(f"{key}={value}" for key, value in result["metrics"].items()))
        for finding in result["findings"]:
            print(
                f"{finding['severity'].upper():7} {finding['code']}: "
                f"{finding['path']} — {finding['message']}"
            )
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
