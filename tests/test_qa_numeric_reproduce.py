from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import qa_numeric_reproduce as qnr  # noqa: E402

# Paschen + standard-atmosphere model shared by the fixtures below.
_BASE = {
    "constants": {"A": 11250, "B": 273750, "gse": 0.01},
    "definitions": [
        "C = log(1 + 1/gse)",
        "P(h) = 101.325*(1 - 2.25577e-5*h)**5.25588",
        "Vb(h,d) = B*P(h)*d/(log(A*P(h)*d) - log(C))",
        "Ka(h,d) = Vb(h,d)/Vb(0,d)",
    ],
}


def _write(tmp_path: Path, spec: dict) -> Path:
    p = tmp_path / "spec.json"
    p.write_text(json.dumps(spec), encoding="utf-8")
    return p


def test_value_check_reproduces_good_number(tmp_path: Path) -> None:
    spec = dict(_BASE)
    spec["value_checks"] = [
        {"name": "Vb@4500,100um", "expr": "Vb(4500,100e-6)", "expect": 598, "tol_rel": 0.01}
    ]
    assert qnr.main([str(_write(tmp_path, spec))]) == 0


def test_claim_check_flags_nonreproducing_number(tmp_path: Path) -> None:
    # Draft states Ka(4500,500um)=0.726; the model gives ~0.645 -> must FAIL.
    spec = dict(_BASE)
    spec["claim_checks"] = [
        {"name": "draft 0.726", "expr": "Ka(4500,500e-6)", "stated": 0.726, "tol_rel": 0.02}
    ]
    assert qnr.main([str(_write(tmp_path, spec))]) == 1


def test_monotonic_check_catches_wrong_direction(tmp_path: Path) -> None:
    # Draft claims Ka rises with gap; real trend falls -> must FAIL.
    spec = dict(_BASE)
    spec["monotonic_checks"] = [
        {"name": "rises?", "expr": "Ka(4500,d)", "var": "d",
         "sweep": [50e-6, 100e-6, 500e-6], "direction": "increasing"}
    ]
    assert qnr.main([str(_write(tmp_path, spec))]) == 1
    # The true direction passes.
    spec["monotonic_checks"][0]["direction"] = "decreasing"
    assert qnr.main([str(_write(tmp_path, spec))]) == 0


def test_unsafe_expression_rejected(tmp_path: Path) -> None:
    spec = dict(_BASE)
    spec["value_checks"] = [
        {"name": "evil", "expr": "().__class__", "expect": 0}
    ]
    assert qnr.main([str(_write(tmp_path, spec))]) == 1


def test_run_returns_structured_results() -> None:
    spec = dict(_BASE)
    spec["value_checks"] = [
        {"name": "ok", "expr": "Vb(0,100e-6)", "expect": 865, "tol_rel": 0.01}
    ]
    ok, results = qnr.run(spec)
    assert ok is True
    assert results[0]["kind"] == "value"
