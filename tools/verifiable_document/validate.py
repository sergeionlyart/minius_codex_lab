#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    from .common import (
        ALLOWED_CLAIM_TYPES,
        ALLOWED_CONFIDENCE,
        ALLOWED_INCLUSION_MODES,
        ALLOWED_VERIFICATION_STATUS,
        iter_claims,
        load_json,
        resolve_local_path,
        sha256_file,
        sha256_text,
        write_json,
    )
except ImportError:  # Direct script execution.
    from common import (  # type: ignore[no-redef]
        ALLOWED_CLAIM_TYPES,
        ALLOWED_CONFIDENCE,
        ALLOWED_INCLUSION_MODES,
        ALLOWED_VERIFICATION_STATUS,
        iter_claims,
        load_json,
        resolve_local_path,
        sha256_file,
        sha256_text,
        write_json,
    )


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    path: str
    message: str


def _add(findings: list[Finding], severity: str, code: str, path: str, message: str) -> None:
    findings.append(Finding(severity=severity, code=code, path=path, message=message))


def _nonempty_string(
    value: Any,
    findings: list[Finding],
    path: str,
    *,
    required: bool = True,
) -> bool:
    valid = isinstance(value, str) and bool(value.strip())
    if required and not valid:
        _add(findings, "error", "required_string", path, "Expected a non-empty string.")
    return valid


def _duplicate_values(values: Iterable[str]) -> list[str]:
    counts = Counter(value for value in values if value)
    return sorted(value for value, count in counts.items() if count > 1)


def _looks_like_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _optional_jsonschema_check(spec: dict[str, Any], findings: list[Finding]) -> None:
    try:
        import jsonschema
    except ImportError:
        return

    schema_path = Path(__file__).with_name("schema.json")
    schema = load_json(schema_path)
    validator = jsonschema.Draft202012Validator(schema)
    for error in sorted(validator.iter_errors(spec), key=lambda item: list(item.path)):
        path = "/" + "/".join(str(part) for part in error.absolute_path)
        _add(findings, "error", "json_schema", path or "/", error.message)


def validate_spec(spec: dict[str, Any], spec_path: Path) -> dict[str, Any]:
    findings: list[Finding] = []
    _optional_jsonschema_check(spec, findings)

    if spec.get("schema_version") != "1.0":
        _add(
            findings,
            "error",
            "schema_version",
            "/schema_version",
            "Only schema_version '1.0' is supported.",
        )

    document = spec.get("document")
    if not isinstance(document, dict):
        _add(findings, "error", "document_type", "/document", "Expected an object.")
        document = {}
    for key in ("document_id", "title", "language", "as_of", "classification"):
        _nonempty_string(document.get(key), findings, f"/document/{key}")
    classification = document.get("classification")
    if classification not in {"PUBLIC", "INTERNAL", "PERSONAL", "RESTRICTED"}:
        _add(
            findings,
            "error",
            "classification",
            "/document/classification",
            "Use PUBLIC, INTERNAL, PERSONAL, or RESTRICTED.",
        )
    if classification in {"PERSONAL", "RESTRICTED"}:
        _add(
            findings,
            "warning",
            "sensitive_output",
            "/document/classification",
            "Publication or remote push requires an organization-approved disclosure decision.",
        )

    sections = spec.get("sections")
    if not isinstance(sections, list) or not sections:
        _add(findings, "error", "sections", "/sections", "Expected a non-empty array.")
        sections = []

    section_ids: list[str] = []
    block_ids: list[str] = []
    claim_ids: list[str] = []
    claims: list[dict[str, Any]] = []
    for section_index, section in enumerate(sections):
        section_path = f"/sections/{section_index}"
        if not isinstance(section, dict):
            _add(findings, "error", "section_type", section_path, "Expected an object.")
            continue
        section_id = str(section.get("section_id", ""))
        section_ids.append(section_id)
        _nonempty_string(section.get("section_id"), findings, f"{section_path}/section_id")
        _nonempty_string(section.get("title"), findings, f"{section_path}/title")
        blocks = section.get("blocks")
        if not isinstance(blocks, list):
            _add(findings, "error", "blocks", f"{section_path}/blocks", "Expected an array.")
            continue
        for block_index, block in enumerate(blocks):
            block_path = f"{section_path}/blocks/{block_index}"
            if not isinstance(block, dict):
                _add(findings, "error", "block_type", block_path, "Expected an object.")
                continue
            block_type = block.get("type")
            if block_type not in {"paragraph", "heading", "claim"}:
                _add(
                    findings,
                    "error",
                    "block_kind",
                    f"{block_path}/type",
                    "Use paragraph, heading, or claim.",
                )
            block_id = str(block.get("block_id", ""))
            block_ids.append(block_id)
            _nonempty_string(block.get("block_id"), findings, f"{block_path}/block_id")
            _nonempty_string(block.get("text"), findings, f"{block_path}/text")
            if block_type == "claim":
                claims.append(block)
                claim_id = str(block.get("claim_id", ""))
                claim_ids.append(claim_id)
                _nonempty_string(block.get("claim_id"), findings, f"{block_path}/claim_id")
                if block.get("claim_type") not in ALLOWED_CLAIM_TYPES:
                    _add(
                        findings,
                        "error",
                        "claim_type",
                        f"{block_path}/claim_type",
                        f"Allowed values: {sorted(ALLOWED_CLAIM_TYPES)}.",
                    )
                if not isinstance(block.get("material"), bool):
                    _add(
                        findings,
                        "error",
                        "material_type",
                        f"{block_path}/material",
                        "Expected a boolean.",
                    )
                if block.get("confidence") not in ALLOWED_CONFIDENCE:
                    _add(
                        findings,
                        "error",
                        "confidence",
                        f"{block_path}/confidence",
                        f"Allowed values: {sorted(ALLOWED_CONFIDENCE)}.",
                    )
                for ref_key in ("evidence_refs", "counterevidence_refs"):
                    refs = block.get(ref_key)
                    if not isinstance(refs, list) or not all(
                        isinstance(item, str) and item.strip() for item in refs
                    ):
                        _add(
                            findings,
                            "error",
                            "reference_list",
                            f"{block_path}/{ref_key}",
                            "Expected an array of non-empty unit IDs.",
                        )
                evidence_refs = block.get("evidence_refs", [])
                if block.get("material") is True and not evidence_refs:
                    _add(
                        findings,
                        "error",
                        "material_claim_without_evidence",
                        block_path,
                        "Every material claim must link to at least one exact evidence unit.",
                    )
                if block.get("claim_type") == "assumption" and not block.get("qualification"):
                    _add(
                        findings,
                        "warning",
                        "unqualified_assumption",
                        block_path,
                        "Label the assumption and explain how it will be verified "
                        "or how it affects the result.",
                    )

    for duplicate in _duplicate_values(section_ids):
        _add(findings, "error", "duplicate_section_id", "/sections", duplicate)
    for duplicate in _duplicate_values(block_ids):
        _add(findings, "error", "duplicate_block_id", "/sections", duplicate)
    for duplicate in _duplicate_values(claim_ids):
        _add(findings, "error", "duplicate_claim_id", "/sections", duplicate)

    sources = spec.get("sources")
    if not isinstance(sources, list) or not sources:
        _add(findings, "error", "sources", "/sources", "Expected a non-empty array.")
        sources = []

    source_ids: list[str] = []
    unit_ids: list[str] = []
    units: dict[str, tuple[dict[str, Any], dict[str, Any], str]] = {}
    for source_index, source in enumerate(sources):
        source_path = f"/sources/{source_index}"
        if not isinstance(source, dict):
            _add(findings, "error", "source_type", source_path, "Expected an object.")
            continue
        source_id = str(source.get("source_id", ""))
        source_ids.append(source_id)
        for key in ("source_id", "title", "authority", "type", "jurisdiction", "retrieved_at"):
            _nonempty_string(source.get(key), findings, f"{source_path}/{key}")
        inclusion_mode = source.get("inclusion_mode")
        if inclusion_mode not in ALLOWED_INCLUSION_MODES:
            _add(
                findings,
                "error",
                "inclusion_mode",
                f"{source_path}/inclusion_mode",
                f"Allowed values: {sorted(ALLOWED_INCLUSION_MODES)}.",
            )
        expected_source_hash = source.get("sha256")
        if not isinstance(expected_source_hash, str) or len(expected_source_hash) != 64:
            _add(
                findings,
                "error",
                "source_hash",
                f"{source_path}/sha256",
                "Expected a lowercase SHA-256 hex digest.",
            )
        official_url = source.get("official_url")
        if official_url and (
            not isinstance(official_url, str) or not _looks_like_url(official_url)
        ):
            _add(
                findings,
                "warning",
                "official_url",
                f"{source_path}/official_url",
                "The official URL is not a valid HTTP(S) URL.",
            )
        local_path = source.get("local_path")
        if local_path:
            if not isinstance(local_path, str):
                _add(
                    findings,
                    "error",
                    "local_path_type",
                    f"{source_path}/local_path",
                    "Expected a string.",
                )
            else:
                if Path(local_path).is_absolute():
                    _add(
                        findings,
                        "warning",
                        "absolute_local_path",
                        f"{source_path}/local_path",
                        "Avoid publishing absolute local paths; use a "
                        "repository-relative reference.",
                    )
                resolved_path = resolve_local_path(spec_path, local_path)
                if not resolved_path.exists():
                    _add(
                        findings,
                        "warning",
                        "source_file_missing",
                        f"{source_path}/local_path",
                        f"Source file not found for hash verification: {resolved_path}",
                    )
                elif resolved_path.is_file() and isinstance(expected_source_hash, str):
                    actual_hash = sha256_file(resolved_path)
                    if actual_hash != expected_source_hash:
                        _add(
                            findings,
                            "error",
                            "source_hash_mismatch",
                            f"{source_path}/sha256",
                            f"Recorded {expected_source_hash}; actual {actual_hash}.",
                        )
        units_value = source.get("units")
        if not isinstance(units_value, list) or not units_value:
            _add(
                findings,
                "error",
                "source_units",
                f"{source_path}/units",
                "Expected at least one addressable evidence unit.",
            )
            continue
        for unit_index, unit in enumerate(units_value):
            unit_path = f"{source_path}/units/{unit_index}"
            if not isinstance(unit, dict):
                _add(findings, "error", "unit_type", unit_path, "Expected an object.")
                continue
            unit_id = str(unit.get("unit_id", ""))
            unit_ids.append(unit_id)
            for key in ("unit_id", "locator", "text", "sha256", "verification_status"):
                _nonempty_string(unit.get(key), findings, f"{unit_path}/{key}")
            if unit.get("verification_status") not in ALLOWED_VERIFICATION_STATUS:
                _add(
                    findings,
                    "error",
                    "verification_status",
                    f"{unit_path}/verification_status",
                    f"Allowed values: {sorted(ALLOWED_VERIFICATION_STATUS)}.",
                )
            text = unit.get("text")
            expected_unit_hash = unit.get("sha256")
            if isinstance(text, str) and isinstance(expected_unit_hash, str):
                actual_unit_hash = sha256_text(text)
                if actual_unit_hash != expected_unit_hash:
                    _add(
                        findings,
                        "error",
                        "unit_hash_mismatch",
                        f"{unit_path}/sha256",
                        f"Recorded {expected_unit_hash}; actual {actual_unit_hash}.",
                    )
            if inclusion_mode == "page-image-evidence" and not unit.get("page"):
                _add(
                    findings,
                    "error",
                    "scan_page_missing",
                    unit_path,
                    "Page-image evidence units require a page locator.",
                )
            units[unit_id] = (source, unit, unit_path)

    for duplicate in _duplicate_values(source_ids):
        _add(findings, "error", "duplicate_source_id", "/sources", duplicate)
    for duplicate in _duplicate_values(unit_ids):
        _add(findings, "error", "duplicate_unit_id", "/sources", duplicate)

    used_units: set[str] = set()
    for _, claim in iter_claims(spec):
        claim_id = str(claim.get("claim_id", "<missing>"))
        claim_path = f"/claim/{claim_id}"
        evidence_refs = claim.get("evidence_refs", [])
        counter_refs = claim.get("counterevidence_refs", [])
        if not isinstance(evidence_refs, list):
            evidence_refs = []
        if not isinstance(counter_refs, list):
            counter_refs = []
        if set(evidence_refs) & set(counter_refs):
            _add(
                findings,
                "warning",
                "same_support_and_counterevidence",
                claim_path,
                "The same unit is listed as both supporting and counterevidence.",
            )
        verified_support = 0
        for ref_kind, refs in (("evidence", evidence_refs), ("counterevidence", counter_refs)):
            for ref in refs:
                if not isinstance(ref, str):
                    continue
                used_units.add(ref)
                target = units.get(ref)
                if target is None:
                    _add(
                        findings,
                        "error",
                        "unresolved_evidence_ref",
                        claim_path,
                        f"{ref_kind} reference does not resolve to an exact unit: {ref}",
                    )
                    continue
                _, unit, _ = target
                if ref_kind == "evidence" and unit.get("verification_status") == "human-verified":
                    verified_support += 1
        if claim.get("material") is True and evidence_refs and verified_support == 0:
            _add(
                findings,
                "warning",
                "material_claim_without_human_verified_unit",
                claim_path,
                "No supporting unit is marked human-verified.",
            )

    source_usage: Counter[str] = Counter()
    for unit_id in used_units:
        target = units.get(unit_id)
        if target:
            source_usage[str(target[0].get("source_id", ""))] += 1
    for source_index, source in enumerate(sources):
        if isinstance(source, dict):
            source_id = str(source.get("source_id", ""))
            if source_id and source_usage[source_id] == 0:
                _add(
                    findings,
                    "warning",
                    "unused_source",
                    f"/sources/{source_index}",
                    f"Source {source_id} is present but no claim links to its units.",
                )

    errors = [finding for finding in findings if finding.severity == "error"]
    warnings = [finding for finding in findings if finding.severity == "warning"]
    validated_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return {
        "validator": "minius_codex_lab-verifiable-document/1.0.0-beta.1",
        "validated_at_utc": validated_at,
        "spec_path": str(spec_path),
        "valid": not errors,
        "summary": {
            "errors": len(errors),
            "warnings": len(warnings),
            "sections": len(sections),
            "claims": len(claims),
            "material_claims": sum(1 for claim in claims if claim.get("material") is True),
            "sources": len(sources),
            "evidence_units": len(units),
            "used_evidence_units": len(used_units),
        },
        "findings": [asdict(finding) for finding in findings],
    }


def _format_report(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        (
            f"valid={str(report['valid']).lower()} errors={summary['errors']} "
            f"warnings={summary['warnings']}"
        ),
        (
            f"claims={summary['claims']} material={summary['material_claims']} "
            f"sources={summary['sources']} units={summary['evidence_units']}"
        ),
    ]
    for finding in report["findings"]:
        lines.append(
            f"{finding['severity'].upper():7} {finding['code']}: "
            f"{finding['path']} — {finding['message']}"
        )
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a verifiable legal document JSON spec.")
    parser.add_argument("spec", type=Path, help="Path to the JSON specification.")
    parser.add_argument("--report", type=Path, help="Write a machine-readable validation report.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return a non-zero exit status when warnings are present.",
    )
    parser.add_argument("--json", action="store_true", help="Print the report as JSON.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    spec_path = args.spec.resolve()
    try:
        spec = load_json(spec_path)
        report = validate_spec(spec, spec_path)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2

    if args.report:
        write_json(args.report, report)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(_format_report(report))
    if not report["valid"]:
        return 1
    if args.strict and report["summary"]["warnings"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
