#!/usr/bin/env python3
"""Build and verify the bundled synthetic legal document in HTML and DOCX."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path


class SyntheticGateError(RuntimeError):
    """Raised when the bundled synthetic gate does not pass."""


def _root() -> Path:
    runtime_root = Path(__file__).resolve().parents[1]
    if (runtime_root / "tools/verifiable_document").is_dir():
        return runtime_root
    upstream_root = runtime_root.parent
    if (upstream_root / "tools/verifiable_document").is_dir():
        return upstream_root
    return runtime_root


def _run(root: Path, label: str, *args: str) -> None:
    try:
        completed = subprocess.run(
            args,
            cwd=root,
            check=False,
            text=True,
            capture_output=True,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise SyntheticGateError(f"{label} could not run: {error}") from error
    if completed.returncode != 0:
        details = completed.stdout.strip() or completed.stderr.strip() or "no diagnostic output"
        raise SyntheticGateError(f"{label} failed: {details}")


def _safe_identifier(prefix: str, identifier: str, length: int) -> str:
    digest = hashlib.sha1(
        identifier.encode("utf-8"),
        usedforsecurity=False,
    ).hexdigest()[:length]
    separator = "_" if prefix in {"c", "e"} else "-"
    return f"{prefix}{separator}{digest}"


def _semantic_graph(spec: dict[str, object]) -> dict[str, object]:
    claims: list[dict[str, object]] = []
    sections = spec.get("sections")
    if not isinstance(sections, list):
        raise SyntheticGateError("synthetic spec has no sections")
    for section in sections:
        if not isinstance(section, dict) or not isinstance(section.get("blocks"), list):
            raise SyntheticGateError("synthetic spec contains an invalid section")
        for block in section["blocks"]:
            if isinstance(block, dict) and block.get("type") == "claim":
                claims.append(
                    {
                        "claim_id": block.get("claim_id"),
                        "counterevidence_refs": block.get("counterevidence_refs"),
                        "evidence_refs": block.get("evidence_refs"),
                    }
                )
    sources = spec.get("sources")
    if not isinstance(sources, list):
        raise SyntheticGateError("synthetic spec has no sources")
    source_hashes: dict[str, object] = {}
    unit_hashes: dict[str, object] = {}
    for source in sources:
        if not isinstance(source, dict) or not isinstance(source.get("units"), list):
            raise SyntheticGateError("synthetic spec contains an invalid source")
        source_id = str(source.get("source_id"))
        source_hashes[source_id] = source.get("sha256")
        for unit in source["units"]:
            if not isinstance(unit, dict):
                raise SyntheticGateError("synthetic spec contains an invalid evidence unit")
            unit_hashes[str(unit.get("unit_id"))] = unit.get("sha256")
    claim_ids = [str(claim["claim_id"]) for claim in claims]
    unit_ids = list(unit_hashes)
    return {
        "schema_version": 1,
        "claims": claims,
        "sources": source_hashes,
        "units": unit_hashes,
        "html_anchors": {
            "claims": {claim_id: _safe_identifier("claim", claim_id, 16) for claim_id in claim_ids},
            "evidence": {
                unit_id: _safe_identifier("evidence", unit_id, 16) for unit_id in unit_ids
            },
        },
        "docx_bookmarks": {
            "claims": {claim_id: _safe_identifier("c", claim_id, 24) for claim_id in claim_ids},
            "evidence": {unit_id: _safe_identifier("e", unit_id, 24) for unit_id in unit_ids},
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path(".tmp/synthetic-e2e"),
        help="Ignored output directory (default: .tmp/synthetic-e2e).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = _root()
    spec = root / "tools/verifiable_document/examples/spec.example.json"
    source = root / "tools/verifiable_document/examples/source.example.txt"
    expected_semantic = root / "tools/verifiable_document/examples/semantic.expected.json"
    output = args.out_dir if args.out_dir.is_absolute() else root / args.out_dir
    report = output / "validation.json"
    ingested = output / "source.ingested.json"
    try:
        _run(
            root,
            "synthetic source ingest",
            sys.executable,
            str(root / "tools/verifiable_document/ingest.py"),
            "--input",
            str(source),
            "--output",
            str(ingested),
            "--source-id",
            "SRC-EXAMPLE-001",
            "--title",
            "Навчальне джерело для тестування (не нормативний акт)",
            "--authority",
            "Розробники тестового середовища",
            "--identifier",
            "EXAMPLE-ONLY",
            "--type",
            "synthetic-test-document",
            "--jurisdiction",
            "Not applicable",
            "--date",
            "2026-07-11",
            "--version-date",
            "2026-07-11",
            "--as-of",
            "2026-07-11",
            "--retrieved-at",
            "2026-07-11T00:00:00Z",
            "--inclusion-mode",
            "full",
            "--unit-mode",
            "sentence",
            "--verification-status",
            "human-verified",
            "--reliability",
            "synthetic-fixture",
            "--limitations",
            "Лише технічний приклад; не використовувати як джерело права.",
            "--local-ref",
            "source.example.txt",
        )
        spec_value = json.loads(spec.read_text(encoding="utf-8"))
        ingested_value = json.loads(ingested.read_text(encoding="utf-8"))
        sources = spec_value.get("sources")
        if not isinstance(sources, list) or len(sources) != 1:
            raise SyntheticGateError("synthetic spec must contain exactly one source")
        expected_source = sources[0]
        for key in ("source_id", "sha256", "units"):
            if ingested_value.get(key) != expected_source.get(key):
                raise SyntheticGateError(f"ingested evidence differs from the golden {key}")
        semantic_value = _semantic_graph(spec_value)
        expected_value = json.loads(expected_semantic.read_text(encoding="utf-8"))
        if semantic_value != expected_value:
            raise SyntheticGateError("claim/evidence/link semantic graph differs from golden")
        _run(
            root,
            "strict synthetic validation",
            sys.executable,
            str(root / "tools/verifiable_document/validate.py"),
            str(spec),
            "--strict",
            "--report",
            str(report),
        )
        _run(
            root,
            "synthetic HTML/DOCX build",
            sys.executable,
            str(root / "tools/verifiable_document/build.py"),
            str(spec),
            "--out-dir",
            str(output),
            "--html",
            "--docx",
        )
        build_reports = sorted(output.glob("*.build.json"))
        if len(build_reports) != 1:
            raise SyntheticGateError("expected exactly one build report")
        value = json.loads(build_reports[0].read_text(encoding="utf-8"))
        formats = {item.get("format") for item in value.get("outputs", [])}
        if value.get("valid") is not True or formats != {"html", "docx"}:
            raise SyntheticGateError("build report does not confirm valid HTML and DOCX")
        for item in value["outputs"]:
            path = Path(str(item.get("path", ""))).resolve()
            digest = item.get("sha256")
            if (
                not path.is_relative_to(output.resolve())
                or not path.is_file()
                or not isinstance(digest, str)
                or len(digest) != 64
            ):
                raise SyntheticGateError("build report contains an invalid output record")
            if item.get("format") == "html":
                html = path.read_text(encoding="utf-8")
                anchors = semantic_value["html_anchors"]
                if not isinstance(anchors, dict):
                    raise SyntheticGateError("golden HTML anchors are invalid")
                for group in anchors.values():
                    if not isinstance(group, dict) or any(
                        f'id="{anchor}"' not in html for anchor in group.values()
                    ):
                        raise SyntheticGateError("built HTML omits a golden anchor")
            if item.get("format") == "docx":
                with zipfile.ZipFile(path) as archive:
                    document_xml = archive.read("word/document.xml").decode("utf-8")
                bookmarks = semantic_value["docx_bookmarks"]
                if not isinstance(bookmarks, dict):
                    raise SyntheticGateError("golden DOCX bookmarks are invalid")
                for group in bookmarks.values():
                    if not isinstance(group, dict) or any(
                        f'w:name="{bookmark}"' not in document_xml for bookmark in group.values()
                    ):
                        raise SyntheticGateError("built DOCX omits a golden bookmark")
    except (OSError, json.JSONDecodeError, SyntheticGateError, zipfile.BadZipFile) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(f"PASS: synthetic HTML/DOCX gate; output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
