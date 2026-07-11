#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import UTC, date, datetime
from pathlib import Path

MATTER_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}")


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _replace_placeholders(directory: Path, values: dict[str, str]) -> None:
    for path in directory.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {
            ".md",
            ".csv",
            ".txt",
            ".json",
            ".yaml",
        }:
            continue
        text = path.read_text(encoding="utf-8")
        for key, value in values.items():
            text = text.replace(f"{{{{{key}}}}}", value)
        path.write_text(text, encoding="utf-8", newline="\n")


def _update_index(index_path: Path, matter_id: str, timestamp: str) -> None:
    text = index_path.read_text(encoding="utf-8")
    text = re.sub(r"^updated_at_utc:.*$", f"updated_at_utc: {timestamp}", text, flags=re.MULTILINE)
    text = re.sub(r"^active_matter:.*$", f'active_matter: "{matter_id}"', text, flags=re.MULTILINE)
    index_path.write_text(text, encoding="utf-8", newline="\n")


def _update_current(current_path: Path, matter_id: str, title: str, timestamp: str) -> None:
    text = current_path.read_text(encoding="utf-8")
    entry = f"- `{matter_id}` — {title} (intake; activated {timestamp})"
    pattern = r"(## Активные дела\n\n)(.*?)(\n\n## )"
    match = re.search(pattern, text, flags=re.DOTALL)
    if not match:
        text += f"\n\n## Активные дела\n\n{entry}\n"
    else:
        body = match.group(2).strip()
        if body == "Нет.":
            body = entry
        elif f"`{matter_id}`" not in body:
            body = f"{body}\n{entry}"
        text = text[: match.start(2)] + body + text[match.end(2) :]
    current_path.write_text(text, encoding="utf-8", newline="\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a new legal matter from the repository template."
    )
    parser.add_argument("--id", required=True, dest="matter_id")
    parser.add_argument("--title", required=True)
    parser.add_argument(
        "--classification",
        choices=("PUBLIC", "INTERNAL", "PERSONAL", "RESTRICTED"),
        default="INTERNAL",
    )
    parser.add_argument("--workflow-level", choices=("L0", "L1", "L2", "L3", "TBD"), default="TBD")
    parser.add_argument("--jurisdiction", default="Ukraine")
    parser.add_argument("--as-of", default=date.today().isoformat())
    parser.add_argument("--language", default="uk")
    parser.add_argument("--deadline", default="уточнить")
    parser.add_argument(
        "--no-activate",
        action="store_true",
        help="Do not update memory/index.yaml and memory/CURRENT.md.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    matter_id = args.matter_id.strip()
    if not MATTER_ID_PATTERN.fullmatch(matter_id) or matter_id in {"_template", ".", ".."}:
        print(
            "ERROR: matter ID must use letters, digits, dot, underscore, or hyphen only.",
            file=sys.stderr,
        )
        return 2
    if not args.title.strip():
        print("ERROR: title must not be empty.", file=sys.stderr)
        return 2

    root = _root()
    template = root / "matters/_template"
    target = root / "matters" / matter_id
    if not template.is_dir():
        print(f"ERROR: matter template is missing: {template}", file=sys.stderr)
        return 2
    if target.exists():
        print(f"ERROR: matter already exists: {target}", file=sys.stderr)
        return 1

    timestamp = _utc_now()
    try:
        shutil.copytree(template, target)
        _replace_placeholders(
            target,
            {
                "MATTER_ID": matter_id,
                "TITLE": args.title.strip(),
                "CREATED_AT": timestamp,
                "CLASSIFICATION": args.classification,
                "WORKFLOW_LEVEL": args.workflow_level,
                "JURISDICTION": args.jurisdiction,
                "AS_OF": args.as_of,
                "LANGUAGE": args.language,
                "DEADLINE": args.deadline,
            },
        )
        if not args.no_activate:
            _update_index(root / "memory/index.yaml", matter_id, timestamp)
            _update_current(root / "memory/CURRENT.md", matter_id, args.title.strip(), timestamp)
    except OSError as error:
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
        print(f"ERROR: {error}", file=sys.stderr)
        return 2

    print(f"created matter: {target}")
    print(f"classification: {args.classification}; workflow level: {args.workflow_level}")
    if args.classification in {"PERSONAL", "RESTRICTED"}:
        print(
            "NOTICE: external search, export, and remote push require a separate "
            "disclosure decision."
        )
    print(f"recommended commit: matter: initialize {matter_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
