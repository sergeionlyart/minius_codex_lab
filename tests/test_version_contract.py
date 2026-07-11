from __future__ import annotations

import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_package_manifest_is_the_canonical_version_source() -> None:
    manifest = json.loads((ROOT / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8"))
    version = manifest["version"]
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["version"] == version
    assert manifest["release_asset"] == f"minius_codex_lab-workspace-v{version}.zip"
    assert version in (ROOT / "README.md").read_text(encoding="utf-8")
    assert version in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert (ROOT / "docs" / "releases" / f"v{version}.md").is_file()


def test_python_and_ci_do_not_define_a_second_current_version() -> None:
    for relative in ("scripts/build_release.py", "scripts/validate_workspace.py"):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "CURRENT_VERSION" not in text
        assert "1.0.0-beta." not in text
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "build_release.py --version" not in workflow
