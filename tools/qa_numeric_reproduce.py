#!/usr/bin/env python3
"""qa_numeric_reproduce.py — numeric reproducibility gate for disclosures.

Recomputes a disclosure's worked-example numbers from its OWN formulas and
diffs them against the values written in the draft. Catches the failure mode
that ``qa_docx_math.py`` (syntax/OMML) and the Step-8 self-check (narrative
consistency) do NOT catch: numbers that simply don't reproduce, or a stated
trend whose direction is wrong.

Motivating case: a disclosure claimed an altitude-correction factor rose with
gap (Ka: 0.691 -> 0.726) while its own Paschen + standard-atmosphere formulas
give a falling trend (0.691 -> 0.645). Syntax QA passed; the numbers were wrong.

Spec file (JSON by default; YAML accepted if PyYAML is installed):

    {
      "constants":   {"A": 11250, "B": 273750, "gse": 0.01},
      "definitions": [
        "C = log(1 + 1/gse)",
        "P(h) = 101.325*(1 - 2.25577e-5*h)**5.25588",
        "Vb(h,d) = B*P(h)*d/(log(A*P(h)*d) - log(C))",
        "Ka(h,d) = Vb(h,d)/Vb(0,d)"
      ],
      "value_checks": [
        {"name": "Vb@4500,100um", "expr": "Vb(4500,100e-6)", "expect": 598, "tol_rel": 0.01}
      ],
      "monotonic_checks": [
        {"name": "Ka vs gap @5500 falls", "expr": "Ka(5500,d)", "var": "d",
         "sweep": [50e-6,100e-6,200e-6,500e-6], "direction": "decreasing"}
      ],
      "claim_checks": [
        {"name": "draft says Ka(4500,500um)=0.726", "expr": "Ka(4500,500e-6)",
         "stated": 0.726, "tol_rel": 0.02}
      ]
    }

- value_checks:     computed expr must match `expect` (independent recompute).
- monotonic_checks: expr must be monotonic in the given direction across `sweep`
                    (catches wrong-direction trend claims).
- claim_checks:     computed expr vs the number `stated` in the draft
                    (catches "the draft prints a number the math doesn't give").

Exit 0 = all checks pass; 1 = any FAIL or spec error. Emits one machine line
``NUMERIC_QA_JSON:`` plus a human-readable summary.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Callable

# Safe evaluation namespace: math only, no builtins, no attribute access needed.
_SAFE_FUNCS: dict[str, Any] = {
    "log": math.log, "ln": math.log, "log10": math.log10, "log2": math.log2,
    "exp": math.exp, "sqrt": math.sqrt, "pow": math.pow, "fabs": math.fabs,
    "sin": math.sin, "cos": math.cos, "tan": math.tan, "atan": math.atan,
    "floor": math.floor, "ceil": math.ceil, "abs": abs, "min": min, "max": max,
    "pi": math.pi, "e": math.e,
}

_DEF_RE = re.compile(r"^\s*([A-Za-z_]\w*)\s*(?:\(([^)]*)\))?\s*=\s*(.+)$", re.S)
_ATTR_RE = re.compile(r"\.\s*[A-Za-z_]")  # forbid attribute access in expressions


class SpecError(Exception):
    pass


def _safe_eval(expr: str, namespace: dict[str, Any]) -> float:
    if "__" in expr or _ATTR_RE.search(expr):
        raise SpecError(f"unsafe expression rejected: {expr!r}")
    try:
        return eval(expr, {"__builtins__": {}}, namespace)  # noqa: S307 (restricted)
    except SpecError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise SpecError(f"failed to evaluate {expr!r}: {exc}") from exc


def _make_function(args: list[str], body: str, ns: dict[str, Any]) -> Callable[..., float]:
    def fn(*values: float) -> float:
        if len(values) != len(args):
            raise SpecError(f"function expected {len(args)} args, got {len(values)}")
        local = dict(ns)
        local.update(dict(zip(args, values)))
        return _safe_eval(body, local)

    return fn


def build_namespace(spec: dict[str, Any]) -> dict[str, Any]:
    ns: dict[str, Any] = dict(_SAFE_FUNCS)
    for name, value in (spec.get("constants") or {}).items():
        ns[str(name)] = float(value)
    for raw in spec.get("definitions") or []:
        m = _DEF_RE.match(str(raw))
        if not m:
            raise SpecError(f"cannot parse definition: {raw!r}")
        name, arglist, body = m.group(1), m.group(2), m.group(3)
        if arglist is None:  # scalar definition, e.g. "C = log(1+1/gse)"
            ns[name] = _safe_eval(body, ns)
        else:
            args = [a.strip() for a in arglist.split(",") if a.strip()]
            ns[name] = _make_function(args, body, ns)
    return ns


def _close(got: float, ref: float, tol_rel: float, tol_abs: float) -> bool:
    if math.isnan(got) or math.isnan(ref):
        return False
    return abs(got - ref) <= max(tol_abs, tol_rel * abs(ref))


def _run_value_checks(spec: dict[str, Any], ns: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for chk in spec.get("value_checks") or []:
        got = _safe_eval(str(chk["expr"]), ns)
        ref = float(chk["expect"])
        ok = _close(got, ref, float(chk.get("tol_rel", 0.0)), float(chk.get("tol_abs", 0.0)))
        out.append({"kind": "value", "name": chk.get("name", chk["expr"]),
                    "expr": chk["expr"], "computed": got, "expected": ref, "pass": ok})
    return out


def _run_claim_checks(spec: dict[str, Any], ns: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for chk in spec.get("claim_checks") or []:
        got = _safe_eval(str(chk["expr"]), ns)
        ref = float(chk["stated"])
        ok = _close(got, ref, float(chk.get("tol_rel", 0.0)), float(chk.get("tol_abs", 0.0)))
        out.append({"kind": "claim", "name": chk.get("name", chk["expr"]),
                    "expr": chk["expr"], "computed": got, "stated_in_draft": ref, "pass": ok})
    return out


def _run_monotonic_checks(spec: dict[str, Any], ns: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for chk in spec.get("monotonic_checks") or []:
        var = str(chk["var"])
        sweep = [float(v) for v in chk["sweep"]]
        direction = str(chk["direction"]).lower()
        vals = []
        for v in sweep:
            local = dict(ns)
            local[var] = v
            vals.append(_safe_eval(str(chk["expr"]), local))
        diffs = [b - a for a, b in zip(vals, vals[1:])]
        if direction in ("increasing", "strictly_increasing", "up"):
            ok = all(d > 0 for d in diffs)
        elif direction in ("decreasing", "strictly_decreasing", "down"):
            ok = all(d < 0 for d in diffs)
        elif direction in ("non_decreasing", "nondecreasing"):
            ok = all(d >= 0 for d in diffs)
        elif direction in ("non_increasing", "nonincreasing"):
            ok = all(d <= 0 for d in diffs)
        else:
            raise SpecError(f"unknown direction: {direction!r}")
        out.append({"kind": "monotonic", "name": chk.get("name", chk["expr"]),
                    "expr": chk["expr"], "var": var, "sweep": sweep,
                    "values": vals, "direction": direction, "pass": ok})
    return out


def load_spec(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".yaml", ".yml"):
        try:
            import yaml  # type: ignore
        except ModuleNotFoundError as exc:
            raise SpecError(
                "YAML spec needs PyYAML (pip install pyyaml) or convert the spec to JSON"
            ) from exc
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    if not isinstance(data, dict):
        raise SpecError("spec root must be a mapping/object")
    return data


def run(spec: dict[str, Any]) -> tuple[bool, list[dict[str, Any]]]:
    ns = build_namespace(spec)
    results = (_run_value_checks(spec, ns)
               + _run_monotonic_checks(spec, ns)
               + _run_claim_checks(spec, ns))
    passed = all(r["pass"] for r in results)
    return passed, results


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Numeric reproducibility gate for disclosures.")
    ap.add_argument("spec", help="path to numeric-check spec (.json / .yaml)")
    args = ap.parse_args(argv)

    try:
        spec = load_spec(Path(args.spec))
        ok, results = run(spec)
    except (SpecError, OSError, json.JSONDecodeError) as exc:
        print("NUMERIC_QA_JSON:" + json.dumps({"pass": False, "error": str(exc)}, ensure_ascii=False))
        print(f"FAIL: {exc}")
        return 1

    n_fail = sum(1 for r in results if not r["pass"])
    print("NUMERIC_QA_JSON:" + json.dumps(
        {"pass": ok, "n_checks": len(results), "n_fail": n_fail, "results": results},
        ensure_ascii=False))
    for r in results:
        flag = "PASS" if r["pass"] else "FAIL"
        if r["kind"] == "value":
            print(f"  [{flag}] value  {r['name']}: computed={r['computed']:.6g} expect={r['expected']:.6g}")
        elif r["kind"] == "claim":
            print(f"  [{flag}] claim  {r['name']}: draft={r['stated_in_draft']:.6g} computed={r['computed']:.6g}")
        else:
            seq = " -> ".join(f"{v:.4g}" for v in r["values"])
            print(f"  [{flag}] trend  {r['name']} ({r['direction']}): {seq}")
    print(f"{'PASS' if ok else 'FAIL'}: {len(results) - n_fail}/{len(results)} numeric checks passed")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
