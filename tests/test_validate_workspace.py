from __future__ import annotations

import hashlib
import json
import stat
import tempfile
import unittest
from pathlib import Path

from scripts import validate_workspace

DIRECTORY_PATHS = {
    ".agents/skills",
    ".codex/agents",
    "tests",
    "tools/verifiable_document",
}

CONFIG = """\
approval_policy = "on-request"
sandbox_mode = "workspace-write"

[sandbox_workspace_write]
network_access = false

[agents]
max_threads = 2
"""

HOOKS = {
    "hooks": {
        "Stop": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": "python3 .codex/hooks/stop.py",
                        "timeout": 10,
                    }
                ]
            }
        ]
    }
}

SKILL = (
    "---\n"
    "name: example-skill\n"
    "description: Используй этот навык для полностью синтетической проверки "
    "контракта; не используй его для реальной юридической работы.\n"
    "---\n\n"
    "# Example\n\n"
    "## Contract\n\n"
    "- Job-to-be-done: validate a fixture.\n"
    "- Inputs: synthetic files.\n"
    "- Outputs: validation result.\n"
    "- Evidence and safety: synthetic evidence only.\n"
    "- Stop conditions: stop on malformed input.\n"
    "- Acceptance test: validator returns no findings.\n"
)


def _role(name: str, sandbox: str, extra: str = "") -> str:
    description = f"Role {name} with one narrow responsibility and an explicit handoff contract."
    return f'''\
name = "{name}"
description = "{description}"
sandbox_mode = "{sandbox}"
web_search = "disabled"
developer_instructions = """
Allowed actions: inspect the assigned synthetic inputs.
Prohibited actions: do not exceed the assigned responsibility.
Handoff: return findings, evidence, limitations, and the next action.
{extra}
"""
'''


def _write(root: Path, relative: str, content: str = "fixture\n") -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def _manifest() -> dict[str, object]:
    return {
        "schema_version": 1,
        "project": validate_workspace.PROJECT_NAME,
        "package": validate_workspace.PACKAGE_NAME,
        "version": validate_workspace.CURRENT_VERSION,
        "layout": "workspace-template-overlay",
        "default_source_date_epoch": 1783771200,
        "release_asset": (
            f"{validate_workspace.PACKAGE_NAME}-v{validate_workspace.CURRENT_VERSION}.zip"
        ),
        "payload_mappings": [
            {"source": source, "target": target}
            for source, target in validate_workspace.EXPECTED_MAPPINGS
        ],
    }


def _write_contract_files(root: Path) -> None:
    _write(root, ".agents/skills/example-skill/SKILL.md", SKILL)
    _write(
        root,
        ".codex/agents/legal-coordinator.toml",
        _role(
            "legal_coordinator",
            "workspace-write",
            "Require a single owner for every shared final file.",
        ),
    )
    _write(root, ".codex/agents/legal-drafter.toml", _role("legal_drafter", "workspace-write"))
    _write(root, ".codex/agents/ua-law-researcher.toml", _role("ua_law_researcher", "read-only"))


def _create_upstream(root: Path) -> None:
    for relative in validate_workspace.UPSTREAM_REQUIRED_PATHS:
        if relative in DIRECTORY_PATHS:
            (root / relative).mkdir(parents=True, exist_ok=True)
        elif Path(relative).suffix == ".yml":
            _write(root, relative, "{}\n")
        else:
            _write(root, relative)
    _write(root, "AGENTS.md", "maintainer instructions\n")
    _write(root, "workspace-template/AGENTS.md", "runtime instructions\n")
    _write(root, "README.md", f"Version {validate_workspace.CURRENT_VERSION}\n")
    _write(root, "CHANGELOG.md", f"## {validate_workspace.CURRENT_VERSION}\n")
    _write(root, ".codex/config.toml", CONFIG)
    _write(root, "workspace-template/.codex/config.toml", CONFIG)
    _write(root, "workspace-template/.codex/hooks.json", json.dumps(HOOKS))
    _write(root, "tools/verifiable_document/schema.json", '{"type": "object"}\n')
    _write(
        root,
        "pyproject.toml",
        """\
[project]
name = "minius_codex_lab"
version = "1.0.0-beta.1"
requires-python = ">=3.11"

[project.optional-dependencies]
dev = ["PyYAML>=6.0.2,<7"]

[tool.ruff]
target-version = "py311"

[tool.pytest.ini_options]
testpaths = ["tests"]
""",
    )
    _write_contract_files(root)
    (root / "PACKAGE_MANIFEST.json").write_text(
        json.dumps(_manifest(), indent=2) + "\n",
        encoding="utf-8",
    )


def _create_runtime(root: Path) -> None:
    for relative in validate_workspace.RUNTIME_REQUIRED_PATHS:
        if relative in DIRECTORY_PATHS:
            (root / relative).mkdir(parents=True, exist_ok=True)
        elif relative not in {"PACKAGE_MANIFEST.json", "CHECKSUMS.sha256"}:
            _write(root, relative)
    _write(root, ".codex/config.toml", CONFIG)
    _write(root, ".codex/hooks.json", json.dumps(HOOKS))
    _write_contract_files(root)
    _seal_runtime(root)


def _seal_runtime(root: Path) -> None:
    payload = sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.name not in {"PACKAGE_MANIFEST.json", "CHECKSUMS.sha256"}
    )
    records: list[dict[str, object]] = []
    for path in payload:
        data = path.read_bytes()
        records.append(
            {
                "path": path.relative_to(root).as_posix(),
                "size": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "mode": f"{stat.S_IMODE(path.stat().st_mode):04o}",
            }
        )
    manifest = {
        "schema_version": 1,
        "package": validate_workspace.PACKAGE_NAME,
        "version": validate_workspace.CURRENT_VERSION,
        "generated_at_utc": "2026-07-11T12:00:00Z",
        "layout": "extract-directly-into-workspace-root",
        "files": records,
    }
    manifest_path = root / "PACKAGE_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    checksum_paths = [*payload, manifest_path]
    checksum_paths.sort(key=lambda path: path.relative_to(root).as_posix())
    checksum_text = "".join(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(root).as_posix()}\n"
        for path in checksum_paths
    )
    _write(root, "CHECKSUMS.sha256", checksum_text)


def _codes(result: dict[str, object]) -> set[str]:
    findings = result["findings"]
    assert isinstance(findings, list)
    return {str(finding["code"]) for finding in findings}


class ValidateWorkspaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="minius-validator-test-")
        self.root = Path(self.temporary.name) / "repo"
        self.root.mkdir()
        _create_upstream(self.root)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_valid_upstream_contract(self) -> None:
        result = validate_workspace.validate_workspace(self.root, "upstream")
        self.assertTrue(result["valid"], result["findings"])

    def test_missing_skill_contract_marker_is_reported(self) -> None:
        skill = self.root / ".agents/skills/example-skill/SKILL.md"
        skill.write_text(SKILL.replace("- Acceptance test: validator returns no findings.\n", ""))
        result = validate_workspace.validate_workspace(self.root, "upstream")
        self.assertIn("skill_contract_marker", _codes(result))

    def test_missing_role_contract_marker_and_read_only_violation_are_reported(self) -> None:
        role_path = self.root / ".codex/agents/ua-law-researcher.toml"
        text = _role("ua_law_researcher", "workspace-write").replace("Allowed actions", "Scope")
        role_path.write_text(text, encoding="utf-8")
        result = validate_workspace.validate_workspace(self.root, "upstream")
        self.assertTrue({"role_contract_marker", "role_read_only"}.issubset(_codes(result)))

    def test_json_and_toml_structure_errors_are_reported(self) -> None:
        _write(self.root, "workspace-template/.codex/hooks.json", "[]\n")
        _write(self.root, ".codex/config.toml", "[broken\n")
        result = validate_workspace.validate_workspace(self.root, "upstream")
        self.assertTrue({"hooks_structure", "invalid_toml"}.issubset(_codes(result)))

    def test_yaml_and_markdown_errors_are_reported(self) -> None:
        _write(self.root, ".github/workflows/ci.yml", "[unterminated\n")
        _write(
            self.root,
            "README.md",
            f"Version {validate_workspace.CURRENT_VERSION}\n\n```python\n",
        )
        result = validate_workspace.validate_workspace(self.root, "upstream")
        self.assertTrue({"invalid_yaml", "markdown_unclosed_fence"}.issubset(_codes(result)))

    def test_project_manifest_must_equal_the_fixed_allowlist(self) -> None:
        manifest = _manifest()
        mappings = manifest["payload_mappings"]
        assert isinstance(mappings, list)
        mappings.append({"source": ".", "target": ""})
        (self.root / "PACKAGE_MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
        result = validate_workspace.validate_workspace(self.root, "upstream")
        self.assertIn("project_manifest_mapping", _codes(result))

    def test_runtime_manifest_requires_the_exact_file_set(self) -> None:
        runtime = Path(self.temporary.name) / "runtime"
        runtime.mkdir()
        _create_runtime(runtime)
        valid = validate_workspace.validate_workspace(runtime, "runtime")
        self.assertTrue(valid["valid"], valid["findings"])

        _write(runtime, "unexpected.txt", "not declared\n")
        invalid = validate_workspace.validate_workspace(runtime, "runtime")
        self.assertIn("runtime_manifest_exact_set", _codes(invalid))


if __name__ == "__main__":
    unittest.main()
