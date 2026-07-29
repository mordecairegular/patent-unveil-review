# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "SKILL.md"


def _skill_text() -> str:
    return SKILL.read_text(encoding="utf-8")


def test_skill_entrypoint_stays_within_the_v311_context_budget() -> None:
    content = SKILL.read_bytes()

    assert len(content) <= 10 * 1024


def test_skill_frontmatter_contains_only_trigger_metadata() -> None:
    text = _skill_text()
    parts = text.split("---", 2)

    assert len(parts) == 3
    keys = {
        line.split(":", 1)[0].strip()
        for line in parts[1].splitlines()
        if line.strip() and ":" in line
    }
    assert keys == {"name", "description"}


def test_skill_exposes_five_modes_and_all_global_invariants() -> None:
    text = _skill_text()

    for mode in ("mine", "search", "draft", "revise", "full"):
        assert f"`{mode}`" in text
    for number in range(1, 9):
        assert re.search(rf"\*\*G{number}\b", text)


def test_skill_does_not_reaccumulate_version_narratives_or_long_checklist() -> None:
    text = _skill_text()

    assert not re.search(r"\*\*v(?:2|3)\.\d", text)
    assert "Agent 自用工作流检查清单" not in text
    assert "allowed-tools:" not in text
    assert "CHANGELOG.md" in text
