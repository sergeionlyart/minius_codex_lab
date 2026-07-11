from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

TOOL_DIR = Path(__file__).resolve().parents[1]
if str(TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(TOOL_DIR))

from build import (  # noqa: E402
    build_docx,
    build_html,
    validate_docx_links,
    validate_html_links,
)
from build import (  # noqa: E402
    main as build_main,
)
from common import load_json, safe_html_id  # noqa: E402
from validate import validate_spec  # noqa: E402


class VerifiableDocumentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.spec_path = TOOL_DIR / "examples" / "spec.example.json"
        cls.spec = load_json(cls.spec_path)

    def test_example_spec_is_valid(self) -> None:
        report = validate_spec(self.spec, self.spec_path)
        self.assertTrue(report["valid"], report["findings"])
        self.assertEqual(report["summary"]["errors"], 0)
        self.assertEqual(report["summary"]["warnings"], 0)

    def test_html_contains_resolvable_internal_links(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "example.html"
            build_html(self.spec, output)
            self.assertEqual(validate_html_links(output), [])
            text = output.read_text(encoding="utf-8")
            self.assertIn("CLM-EX-001", text)
            self.assertIn("SRC-EXAMPLE-001-U0001", text)
            self.assertIn("data-unit-id", text)

    @unittest.skipUnless(importlib.util.find_spec("docx"), "python-docx is not installed")
    def test_docx_contains_resolvable_internal_links(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "example.docx"
            build_docx(self.spec, output)
            self.assertTrue(output.is_file())
            self.assertEqual(validate_docx_links(output), [])

    def test_tampered_unit_hash_is_rejected(self) -> None:
        spec = copy.deepcopy(self.spec)
        spec["sources"][0]["units"][0]["text"] += " tampered"
        report = validate_spec(spec, self.spec_path)
        codes = {finding["code"] for finding in report["findings"]}
        self.assertFalse(report["valid"])
        self.assertIn("unit_hash_mismatch", codes)

    def test_material_claim_without_evidence_is_rejected(self) -> None:
        spec = copy.deepcopy(self.spec)
        spec["sections"][0]["blocks"][1]["evidence_refs"] = []
        report = validate_spec(spec, self.spec_path)
        codes = {finding["code"] for finding in report["findings"]}
        self.assertFalse(report["valid"])
        self.assertIn("material_claim_without_evidence", codes)

    def test_unresolved_evidence_reference_is_rejected(self) -> None:
        spec = copy.deepcopy(self.spec)
        spec["sections"][0]["blocks"][1]["evidence_refs"] = ["MISSING-U0001"]
        report = validate_spec(spec, self.spec_path)
        codes = {finding["code"] for finding in report["findings"]}
        self.assertFalse(report["valid"])
        self.assertIn("unresolved_evidence_ref", codes)

    def test_example_source_file_hash_is_bound(self) -> None:
        source = self.spec["sources"][0]
        self.assertEqual(source["local_path"], "source.example.txt")
        report = validate_spec(json.loads(json.dumps(self.spec)), self.spec_path)
        codes = {finding["code"] for finding in report["findings"]}
        self.assertNotIn("source_hash_mismatch", codes)

    def test_changed_source_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.example.txt"
            source.write_text("tampered synthetic source\n", encoding="utf-8")
            spec_path = root / "spec.json"
            spec_path.write_text(json.dumps(self.spec), encoding="utf-8")
            report = validate_spec(copy.deepcopy(self.spec), spec_path)
            codes = {finding["code"] for finding in report["findings"]}
            self.assertFalse(report["valid"])
            self.assertIn("source_hash_mismatch", codes)

    def test_absolute_local_path_is_rejected(self) -> None:
        spec = copy.deepcopy(self.spec)
        spec["sources"][0]["local_path"] = "/private/synthetic/source.txt"
        report = validate_spec(spec, self.spec_path)
        codes = {finding["code"] for finding in report["findings"]}
        self.assertFalse(report["valid"])
        self.assertIn("absolute_local_path", codes)

    def test_unverified_page_image_evidence_is_rejected(self) -> None:
        spec = copy.deepcopy(self.spec)
        source = spec["sources"][0]
        source["inclusion_mode"] = "page-image-evidence"
        for unit in source["units"]:
            unit["page"] = 1
            unit["verification_status"] = "needs-human-verification"
        report = validate_spec(spec, self.spec_path)
        codes = {finding["code"] for finding in report["findings"]}
        self.assertFalse(report["valid"])
        self.assertIn("scan_human_verification_required", codes)
        self.assertIn("material_claim_without_human_verified_unit", codes)

    def test_broken_html_anchor_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "broken.html"
            build_html(self.spec, output)
            text = output.read_text(encoding="utf-8")
            text = text.replace(
                f'id="{safe_html_id("evidence", "SRC-EXAMPLE-001-U0001")}"',
                'id="removed-SRC-EXAMPLE-001-U0001"',
                1,
            )
            output.write_text(text, encoding="utf-8")
            self.assertIn(
                safe_html_id("evidence", "SRC-EXAMPLE-001-U0001"),
                validate_html_links(output),
            )

    def test_broken_docx_bookmark_is_detected(self) -> None:
        namespace = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        xml = (
            f'<w:document xmlns:w="{namespace}"><w:body><w:p>'
            '<w:hyperlink w:anchor="missing_bookmark"/></w:p></w:body></w:document>'
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "broken.docx"
            with zipfile.ZipFile(output, "w") as archive:
                archive.writestr("word/document.xml", xml)
            self.assertEqual(validate_docx_links(output), ["missing_bookmark"])

    def test_build_blocks_warnings_unless_explicitly_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = copy.deepcopy(self.spec)
            spec["document"]["classification"] = "PERSONAL"
            (root / "source.example.txt").write_bytes(
                (TOOL_DIR / "examples/source.example.txt").read_bytes()
            )
            spec_path = root / "spec.json"
            spec_path.write_text(json.dumps(spec), encoding="utf-8")
            output = root / "output"
            self.assertEqual(build_main([str(spec_path), "--out-dir", str(output)]), 1)
            self.assertEqual(
                build_main(
                    [
                        str(spec_path),
                        "--out-dir",
                        str(output),
                        "--allow-warnings",
                    ]
                ),
                0,
            )


if __name__ == "__main__":
    unittest.main()
