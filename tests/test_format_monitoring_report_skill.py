from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / ".agents" / "skills" / "format-monitoring-report"
CONTRACT_PATH = SKILL_DIR / "references" / "format-contract.json"
EXPECTED_HEADINGS = (
    "Проблема",
    "Стан нормативно-правового регулювання",
    "Практика реалізації та/або застосування нормативно-правових актів",
    "Результати проведеного опитування",
    "Міжнародний досвід",
    "Науково-дослідні матеріали",
    "Висновки та пропозиції",
)


def _load_contract() -> dict[str, Any]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_contract_has_exact_seven_sections_in_order() -> None:
    contract = _load_contract()
    sections = contract["required_sections"]

    assert [section["order"] for section in sections] == list(range(1, 8))
    assert tuple(section["heading"] for section in sections) == EXPECTED_HEADINGS
    assert len({section["id"] for section in sections}) == 7


def test_contract_preserves_reference_layout_tokens() -> None:
    contract = _load_contract()
    page = contract["page"]
    styles = contract["styles"]

    assert (page["width_twips"], page["height_twips"]) == (11906, 16838)
    assert page["margins_twips"] == {
        "left": 1417,
        "right": 850,
        "top": 850,
        "bottom": 850,
    }
    assert styles["title_band"]["fill"] == "#4F81BD"
    assert styles["title_band"]["font_color"] == "#FFFFFF"
    assert styles["body"]["font"] == "Times New Roman"
    assert styles["body"]["font_size_pt"] == 14
    assert styles["body"]["first_line_indent_twips"] == 567
    assert styles["comparison_table"]["column_widths_twips"] == [
        674,
        4662,
        4519,
    ]


def test_contract_excludes_methodology_and_unapproved_branding() -> None:
    contract = _load_contract()

    assert contract["scope"]["content_generation"] == "excluded"
    assert contract["scope"]["methodology"] == "excluded"
    assert contract["document_rules"]["official_branding"] == ("forbidden_by_default")
    assert contract["document_rules"]["cover_page"] == "absent"
    assert contract["document_rules"]["fixed_page_count"] is False


def test_terminal_table_never_triggers_fabricated_content() -> None:
    terminal = _load_contract()["terminal_component"]

    assert terminal["parent_section"] == "conclusions_and_proposals"
    assert terminal["required_by_template"] is True
    assert terminal["omit_only_when"] == "explicitly_authorized_by_user"
    assert terminal["missing_content_policy"] == "stop_without_fabricating"


def test_skill_contains_no_binary_copy_of_source_document() -> None:
    binary_suffixes = {".doc", ".docx", ".pdf"}

    assert not [
        path
        for path in SKILL_DIR.rglob("*")
        if path.is_file() and path.suffix.lower() in binary_suffixes
    ]
