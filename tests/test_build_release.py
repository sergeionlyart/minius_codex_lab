from __future__ import annotations

import json
import stat
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path

from scripts import build_release, check_repo_safety

SOURCE_ROOT = Path(__file__).resolve().parents[1]
SOURCE_VERSION = json.loads((SOURCE_ROOT / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8"))[
    "version"
]


def _write(root: Path, relative: str, content: str = "fixture\n") -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def _project_manifest() -> dict[str, object]:
    return {
        "schema_version": 1,
        "project": build_release.PROJECT_NAME,
        "package": build_release.PACKAGE_NAME,
        "version": SOURCE_VERSION,
        "layout": "workspace-template-overlay",
        "default_source_date_epoch": 1783771200,
        "release_asset": (f"{build_release.PACKAGE_NAME}-v{SOURCE_VERSION}.zip"),
        "payload_mappings": [
            {"source": source, "target": target}
            for source, target in build_release.EXPECTED_MAPPINGS
        ],
    }


def _create_repository(root: Path) -> None:
    _write(root, "AGENTS.md", "maintainer instructions\n")
    _write(root, "BOOTSTRAP_CODEX_INSTRUCTION.md", "must not ship\n")
    _write(root, ".bootstrap/input/secret.txt", "must not ship\n")
    _write(root, "dist/old.zip", "must not ship\n")
    _write(root, "LICENSE", "Apache License 2.0 fixture\n")
    _write(root, "workspace-template/AGENTS.md", "runtime instructions\n")
    _write(root, "workspace-template/README.md", "runtime readme\n")
    _write(root, "workspace-template/requirements.txt", "PyYAML>=6.0.2,<7\n")
    _write(root, "workspace-template/docs/CODEX_SMOKE_TEST.md", "synthetic smoke test\n")
    _write(
        root,
        "workspace-template/docs/INSTALL_WINDOWS_POWERSHELL.md",
        "synthetic Windows instructions\n",
    )
    _write(root, "workspace-template/.codex/config.toml", "sandbox_mode = 'workspace-write'\n")
    _write(root, "workspace-template/.codex/hooks.json", '{"hooks": {}}\n')
    _write(root, "workspace-template/matters/_template/MATTER.md", "{{MATTER_ID}} {{TITLE}}\n")
    _write(root, "workspace-template/memory/CURRENT.md", "No active matter.\n")
    _write(
        root,
        "workspace-template/scripts/init_workspace.py",
        "#!/usr/bin/env python3\nprint('fixture')\n",
    )
    _write(
        root,
        "workspace-template/scripts/new_matter.py",
        "#!/usr/bin/env python3\nprint('fixture')\n",
    )
    _write(
        root,
        "workspace-template/scripts/run_synthetic_e2e.py",
        "#!/usr/bin/env python3\nprint('fixture')\n",
    )
    _write(root, ".agents/skills/example/SKILL.md", "---\nname: example\ndescription: test\n---\n")
    _write(
        root,
        ".codex/agents/example.toml",
        'name = "example"\ndescription = "test"\n',
    )
    _write(root, "tools/verifiable_document/README.md", "tool\n")
    _write(root, "scripts/check_repo_safety.py", "#!/usr/bin/env python3\n")
    _write(root, "scripts/validate_workspace.py", "#!/usr/bin/env python3\n")
    (root / "PACKAGE_MANIFEST.json").write_text(
        json.dumps(_project_manifest(), indent=2) + "\n",
        encoding="utf-8",
    )


def _zip_info(name: str, mode: int = stat.S_IFREG | 0o644) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, (2026, 7, 11, 12, 0, 0))
    info.create_system = 3
    info.external_attr = mode << 16
    return info


class BuildReleaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="minius-build-test-")
        self.root = Path(self.temporary.name) / "repo"
        self.root.mkdir()
        _create_repository(self.root)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def build(self, output_name: str = "dist") -> build_release.BuildResult:
        return build_release.build_release(
            self.root,
            self.root / output_name,
            SOURCE_VERSION,
            1783771200,
            run_external_checks=False,
        )

    def test_runtime_agents_overlay_and_maintainer_inputs_are_excluded(self) -> None:
        result = self.build()
        with zipfile.ZipFile(result.archive) as archive:
            names = set(archive.namelist())
            self.assertEqual(archive.read("AGENTS.md"), b"runtime instructions\n")
            self.assertIn("scripts/check_repo_safety.py", names)
            self.assertIn("scripts/validate_workspace.py", names)
            self.assertNotIn("scripts/build_release.py", names)
            self.assertNotIn("BOOTSTRAP_CODEX_INSTRUCTION.md", names)
            self.assertFalse(any(name.startswith(".bootstrap/") for name in names))
            self.assertFalse(any(name.startswith("dist/") for name in names))
            self.assertNotEqual(archive.read("AGENTS.md"), (self.root / "AGENTS.md").read_bytes())

    def test_embedded_manifest_and_checksums_describe_the_exact_set(self) -> None:
        result = self.build()
        manifest = build_release.verify_zip_archive(result.archive, expected_version=SOURCE_VERSION)
        with zipfile.ZipFile(result.archive) as archive:
            names = set(archive.namelist())
            declared = {record["path"] for record in manifest["files"]}
            self.assertEqual(
                declared,
                names - {build_release.PROJECT_MANIFEST, build_release.CHECKSUMS_FILE},
            )
            checksums = build_release._parse_checksum_text(  # noqa: SLF001
                archive.read(build_release.CHECKSUMS_FILE).decode("utf-8")
            )
            self.assertEqual(set(checksums), declared | {build_release.PROJECT_MANIFEST})
        expected_sha_line = f"{result.sha256}  {result.archive.name}\n"
        self.assertEqual(result.checksum_file.read_text(encoding="utf-8"), expected_sha_line)

    def test_deterministic_spdx_sbom_describes_payload_and_dependencies(self) -> None:
        result = self.build()
        sbom = json.loads(result.sbom_file.read_text(encoding="utf-8"))
        self.assertEqual(sbom["spdxVersion"], "SPDX-2.3")
        self.assertEqual(sbom["dataLicense"], "CC0-1.0")
        project = next(
            package for package in sbom["packages"] if package["name"] == build_release.PACKAGE_NAME
        )
        self.assertEqual(project["versionInfo"], SOURCE_VERSION)
        self.assertEqual(project["checksums"][0]["checksumValue"], result.sha256)
        dependency_names = {package["name"] for package in sbom["packages"]} - {
            build_release.PACKAGE_NAME
        }
        self.assertEqual(dependency_names, {"PyYAML"})
        with zipfile.ZipFile(result.archive) as archive:
            payload_names = set(archive.namelist()) - {
                build_release.PROJECT_MANIFEST,
                build_release.CHECKSUMS_FILE,
            }
        self.assertEqual(
            {item["fileName"].removeprefix("./") for item in sbom["files"]},
            payload_names,
        )

    def test_permissions_and_timestamps_are_normalized(self) -> None:
        result = self.build()
        expected_timestamp = (2026, 7, 11, 12, 0, 0)
        with zipfile.ZipFile(result.archive) as archive:
            for info in archive.infolist():
                self.assertEqual(info.date_time, expected_timestamp)
                mode = stat.S_IMODE((info.external_attr >> 16) & 0xFFFF)
                self.assertIn(mode, {0o644, 0o755})

    def test_two_clean_builds_are_byte_for_byte_reproducible(self) -> None:
        first = self.build("first")
        second = self.build("second")
        self.assertEqual(first.sha256, second.sha256)
        self.assertEqual(first.archive.read_bytes(), second.archive.read_bytes())
        self.assertEqual(first.sbom_file.read_bytes(), second.sbom_file.read_bytes())

        checked = build_release.build_release(
            self.root,
            self.root / "checked",
            SOURCE_VERSION,
            1783771200,
            check_reproducibility=True,
            run_external_checks=False,
        )
        self.assertEqual(first.sha256, checked.sha256)
        self.assertEqual(first.sbom_file.read_bytes(), checked.sbom_file.read_bytes())

    def test_zip_safety_rejects_traversal_duplicate_and_symlink(self) -> None:
        cases = ("traversal", "duplicate", "symlink")
        for case in cases:
            with self.subTest(case=case):
                path = self.root / f"{case}.zip"
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", UserWarning)
                    with zipfile.ZipFile(path, "w") as archive:
                        if case == "traversal":
                            archive.writestr(_zip_info("../escape.txt"), b"bad")
                        elif case == "duplicate":
                            archive.writestr(_zip_info("same.txt"), b"first")
                            archive.writestr(_zip_info("same.txt"), b"second")
                        else:
                            archive.writestr(
                                _zip_info("link", stat.S_IFLNK | 0o777),
                                b"target",
                            )
                with self.assertRaises(build_release.BuildError):
                    build_release.verify_zip_archive(path)

    def test_payload_source_symlink_is_rejected(self) -> None:
        link = self.root / "workspace-template/symlink"
        try:
            link.symlink_to(self.root / "LICENSE")
        except OSError as error:
            self.skipTest(f"symlinks unavailable: {error}")
        with self.assertRaises(build_release.BuildError):
            self.build()

    def test_non_allowlisted_workspace_template_file_is_rejected(self) -> None:
        for relative in (
            "workspace-template/client-case.txt",
            "workspace-template/matters/_template/client-notes.txt",
        ):
            with self.subTest(relative=relative):
                _write(self.root, relative)
                with self.assertRaises(build_release.BuildError):
                    self.build()
                (self.root / relative).unlink()

    def test_builder_and_safety_scanner_template_allowlists_match(self) -> None:
        self.assertEqual(
            build_release.WORKSPACE_TEMPLATE_FILES,
            check_repo_safety.WORKSPACE_TEMPLATE_FILES,
        )

    def test_repository_template_matches_the_explicit_allowlist(self) -> None:
        template_root = Path(__file__).resolve().parents[1] / "workspace-template"
        actual = {
            path.relative_to(template_root).as_posix()
            for path in template_root.rglob("*")
            if path.is_file()
            and not build_release._ignored(  # noqa: SLF001
                Path(path.relative_to(template_root).as_posix())
            )
        }
        self.assertEqual(actual, build_release.WORKSPACE_TEMPLATE_FILES)


if __name__ == "__main__":
    unittest.main()
