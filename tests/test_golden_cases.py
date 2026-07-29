"""Pure-data validation for the first v3.11 behavior Golden suite.

This test intentionally does not call an LLM.  Manual model regression follows
``tests/golden/runbook.md``; here we only keep the shared case contract valid.
"""

from __future__ import annotations

from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")


GOLDEN_DIR = Path(__file__).resolve().parent / "golden"
CASES_PATH = GOLDEN_DIR / "cases.yaml"
TOPIC_CARD_PATH = Path(__file__).resolve().parent.parent / "templates" / "candidate_topic_card.md"


def test_first_v311_golden_suite_schema() -> None:
    data = yaml.safe_load(CASES_PATH.read_text(encoding="utf-8"))

    assert data["schema_version"] == "1.0"
    assert data["suite_id"] == "patent-unveil-review-v3.11-routing-and-closure"
    assert isinstance(data.get("description"), str) and data["description"].strip()

    cases = data.get("cases")
    assert isinstance(cases, list)
    assert len(cases) == 10
    assert [case["id"] for case in cases] == [f"GC{i:02d}" for i in range(1, 11)]

    allowed_categories = {
        "routing",
        "routing_and_verification",
        "search_language",
        "gate",
        "professional_boundary",
    }
    allowed_gate_statuses = {"not_applicable", "PASS", "WARN", "FAIL", "SKIP"}

    for case in cases:
        assert set(case) == {"id", "title", "category", "stimulus", "expected"}
        assert case["category"] in allowed_categories
        assert isinstance(case["title"], str) and case["title"].strip()

        stimulus = case["stimulus"]
        assert set(stimulus) == {"user", "attachments", "fixture_notes"}
        assert isinstance(stimulus["user"], str) and stimulus["user"].strip()
        assert isinstance(stimulus["attachments"], list)
        assert isinstance(stimulus["fixture_notes"], list)

        expected = case["expected"]
        assert set(expected) == {
            "route",
            "gate",
            "artifacts",
            "required_behaviors",
            "forbidden_behaviors",
        }
        assert isinstance(expected["route"], str) and expected["route"].strip()
        assert isinstance(expected["artifacts"], list)
        assert isinstance(expected["required_behaviors"], list) and expected["required_behaviors"]
        assert isinstance(expected["forbidden_behaviors"], list) and expected["forbidden_behaviors"]

        gate = expected["gate"]
        assert set(gate) == {"id", "expected_status"}
        assert gate["id"] is None or gate["id"] in {"C14", "C16", "C17"}
        assert gate["expected_status"] in allowed_gate_statuses

    expected_gate_cases = {
        "GC07": ("C14", "FAIL"),
        "GC08": ("C17", "FAIL"),
        "GC09": ("C17", "WARN"),
    }
    by_id = {case["id"]: case for case in cases}
    for case_id, (gate_id, status) in expected_gate_cases.items():
        assert by_id[case_id]["expected"]["gate"] == {
            "id": gate_id,
            "expected_status": status,
        }

    for case_id, case in by_id.items():
        if case_id not in expected_gate_cases:
            assert case["expected"]["gate"] == {
                "id": None,
                "expected_status": "not_applicable",
            }


def test_candidate_topic_card_uses_two_dimensional_rating_contract() -> None:
    text = TOPIC_CARD_PATH.read_text(encoding="utf-8")

    for marker in (
        "risk_grade:",
        "evaluation_status:",
        "evaluation_scope:",
        "evaluation_gaps:",
        "旧卡只读兼容",
    ):
        assert marker in text

    assert "A-探针" not in text
    assert "B-探针" not in text
    assert "C/D/未评级" not in text
    assert "旧 `D/partial-D`" in text
