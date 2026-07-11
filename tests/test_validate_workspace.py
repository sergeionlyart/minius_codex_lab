from __future__ import annotations

import hashlib
import json
import stat
import tempfile
import unittest
from pathlib import Path

from scripts import validate_workspace

SOURCE_ROOT = Path(__file__).resolve().parents[1]
SOURCE_VERSION = json.loads((SOURCE_ROOT / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8"))[
    "version"
]

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

SKILL_NAME = "case-law-analysis"


def _skill(name: str) -> str:
    return (
        "---\n"
        f"name: {name}\n"
        "description: >-\n"
        "  Используй этот навык для полностью синтетической проверки: контракт\n"
        "  должен пройти настоящий YAML parser; не используй его для реальной\n"
        "  юридической работы.\n"
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
        "version": SOURCE_VERSION,
        "layout": "workspace-template-overlay",
        "default_source_date_epoch": 1783771200,
        "release_asset": (f"{validate_workspace.PACKAGE_NAME}-v{SOURCE_VERSION}.zip"),
        "payload_mappings": [
            {"source": source, "target": target}
            for source, target in validate_workspace.EXPECTED_MAPPINGS
        ],
    }


def _write_contract_files(root: Path) -> None:
    for name in validate_workspace.EXPECTED_SKILL_NAMES:
        _write(root, f".agents/skills/{name}/SKILL.md", _skill(name))
    for name in validate_workspace.EXPECTED_ROLE_NAMES:
        sandbox = "read-only" if name in validate_workspace.READ_ONLY_ROLES else "workspace-write"
        extra = (
            "Require a single owner for every shared final file."
            if name == "legal_coordinator"
            else ""
        )
        filename = name.replace("_", "-")
        _write(root, f".codex/agents/{filename}.toml", _role(name, sandbox, extra))


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
    _write(root, "README.md", f"Version {SOURCE_VERSION}\n")
    _write(root, "CHANGELOG.md", f"## {SOURCE_VERSION}\n")
    _write(root, f"docs/releases/v{SOURCE_VERSION}.md", f"# Release {SOURCE_VERSION}\n")
    _write(root, ".codex/config.toml", CONFIG)
    _write(root, "workspace-template/.codex/config.toml", CONFIG)
    _write(root, "workspace-template/.codex/hooks.json", json.dumps(HOOKS))
    _write(root, "tools/verifiable_document/schema.json", '{"type": "object"}\n')
    _write(
        root,
        "pyproject.toml",
        f"""\
[project]
name = "minius_codex_lab"
version = "{SOURCE_VERSION}"
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
        "version": SOURCE_VERSION,
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
        skill = self.root / f".agents/skills/{SKILL_NAME}/SKILL.md"
        skill.write_text(
            _skill(SKILL_NAME).replace(
                "- Acceptance test: validator returns no findings.\n",
                "",
            )
        )
        result = validate_workspace.validate_workspace(self.root, "upstream")
        self.assertIn("skill_contract_marker", _codes(result))

    def test_frontmatter_accepts_folded_yaml_with_colon(self) -> None:
        skill = self.root / f".agents/skills/{SKILL_NAME}/SKILL.md"
        frontmatter = validate_workspace._read_frontmatter(skill)
        self.assertEqual(frontmatter["name"], SKILL_NAME)
        self.assertIn("проверки: контракт", frontmatter["description"])

    def test_frontmatter_rejects_unquoted_colon(self) -> None:
        skill = self.root / f".agents/skills/{SKILL_NAME}/SKILL.md"
        text = _skill(SKILL_NAME).replace(
            "description: >-\n"
            "  Используй этот навык для полностью синтетической проверки: контракт\n"
            "  должен пройти настоящий YAML parser; не используй его для реальной\n"
            "  юридической работы.\n",
            "description: Используй для проверки: это невалидный YAML scalar; "
            "не используй для реальной работы.\n",
        )
        skill.write_text(text, encoding="utf-8")
        result = validate_workspace.validate_workspace(self.root, "upstream")
        self.assertIn("skill_frontmatter", _codes(result))

    def test_frontmatter_rejects_duplicate_keys(self) -> None:
        skill = self.root / f".agents/skills/{SKILL_NAME}/SKILL.md"
        text = _skill(SKILL_NAME).replace(
            f"name: {SKILL_NAME}\n",
            f"name: {SKILL_NAME}\nname: {SKILL_NAME}\n",
        )
        skill.write_text(text, encoding="utf-8")
        result = validate_workspace.validate_workspace(self.root, "upstream")
        self.assertIn("skill_frontmatter", _codes(result))

    def test_frontmatter_rejects_non_string_values_and_unsafe_tags(self) -> None:
        skill = self.root / f".agents/skills/{SKILL_NAME}/SKILL.md"
        original = _skill(SKILL_NAME)
        invalid_values = ("42", "true", "null", "[one, two]", "!!python/object:example {}")
        for value in invalid_values:
            with self.subTest(value=value):
                text = original.replace(
                    "description: >-\n"
                    "  Используй этот навык для полностью синтетической проверки: контракт\n"
                    "  должен пройти настоящий YAML parser; не используй его для реальной\n"
                    "  юридической работы.\n",
                    f"description: {value}\n",
                )
                skill.write_text(text, encoding="utf-8")
                result = validate_workspace.validate_workspace(self.root, "upstream")
                self.assertIn("skill_frontmatter", _codes(result))

    def test_skill_inventory_is_exact(self) -> None:
        skill = self.root / ".agents/skills/legal-monitoring/SKILL.md"
        skill.unlink()
        skill.parent.rmdir()
        result = validate_workspace.validate_workspace(self.root, "upstream")
        self.assertIn("skill_inventory", _codes(result))

    def test_runtime_uses_the_same_strict_frontmatter_parser(self) -> None:
        runtime = Path(self.temporary.name) / "runtime-frontmatter"
        runtime.mkdir()
        _create_runtime(runtime)
        skill = runtime / f".agents/skills/{SKILL_NAME}/SKILL.md"
        skill.write_text(
            _skill(SKILL_NAME).replace(
                f"name: {SKILL_NAME}\n",
                f"name: {SKILL_NAME}\nname: {SKILL_NAME}\n",
            ),
            encoding="utf-8",
        )
        _seal_runtime(runtime)
        result = validate_workspace.validate_workspace(runtime, "runtime")
        self.assertIn("skill_frontmatter", _codes(result))

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
            f"Version {SOURCE_VERSION}\n\n```python\n",
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

    def test_runtime_integrity_ignores_virtual_environment(self) -> None:
        runtime = Path(self.temporary.name) / "runtime-venv"
        runtime.mkdir()
        _create_runtime(runtime)
        _write(runtime, ".venv/lib/python3.11/site-packages/probe.py", "synthetic = True\n")
        result = validate_workspace.validate_workspace(runtime, "runtime")
        self.assertTrue(result["valid"], result["findings"])

    def test_operational_mode_allows_expected_mutable_workspace_files(self) -> None:
        runtime = Path(self.temporary.name) / "runtime-operational"
        runtime.mkdir()
        _create_runtime(runtime)
        _write(runtime, "matters/2026-001/MATTER.md", "# Synthetic matter\n")
        _write(runtime, "memory/CURRENT.md", "# Changed operational memory\n")
        result = validate_workspace.validate_workspace(runtime, "operational")
        self.assertTrue(result["valid"], result["findings"])


if __name__ == "__main__":
    unittest.main()
