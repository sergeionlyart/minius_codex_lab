from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

ALLOWED_CLAIM_TYPES = {
    "fact",
    "legal_proposition",
    "numeric",
    "quotation",
    "interpretation",
    "assumption",
    "recommendation",
}
ALLOWED_CONFIDENCE = {"high", "medium", "low", "not_assessed"}
ALLOWED_INCLUSION_MODES = {"full", "evidence-pack", "page-image-evidence"}
ALLOWED_VERIFICATION_STATUS = {
    "human-verified",
    "machine-extracted",
    "needs-human-verification",
    "not-applicable",
}


def normalize_text(value: str) -> str:
    """Normalize whitespace without changing substantive characters."""
    return re.sub(r"\s+", " ", value).strip()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(normalize_text(value).encode("utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def iter_claims(spec: dict[str, Any]) -> Iterator[tuple[dict[str, Any], dict[str, Any]]]:
    for section in spec.get("sections", []):
        if not isinstance(section, dict):
            continue
        for block in section.get("blocks", []):
            if isinstance(block, dict) and block.get("type") == "claim":
                yield section, block


def source_index(spec: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(source.get("source_id")): source
        for source in spec.get("sources", [])
        if isinstance(source, dict) and source.get("source_id")
    }


def unit_index(spec: dict[str, Any]) -> dict[str, tuple[dict[str, Any], dict[str, Any]]]:
    result: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for source in spec.get("sources", []):
        if not isinstance(source, dict):
            continue
        for unit in source.get("units", []):
            if isinstance(unit, dict) and unit.get("unit_id"):
                result[str(unit["unit_id"])] = (source, unit)
    return result


def safe_html_id(prefix: str, identifier: str) -> str:
    digest = hashlib.sha1(identifier.encode("utf-8"), usedforsecurity=False).hexdigest()[:16]
    return f"{prefix}-{digest}"


def safe_word_bookmark(prefix: str, identifier: str) -> str:
    """Return a valid, deterministic Word bookmark name (<= 40 characters)."""
    digest = hashlib.sha1(identifier.encode("utf-8"), usedforsecurity=False).hexdigest()[:24]
    return f"{prefix}_{digest}"[:40]


def resolve_local_path(spec_path: Path, raw_path: str) -> Path:
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate
    return (spec_path.parent / candidate).resolve()
