#!/usr/bin/env python3
"""QA gate for Word DOCX math output.

The check is intentionally XML-level: generated disclosures must not merely
look plausible in Word, they must avoid leftover LaTeX/code-style fragments and
must use editable OMML structures for common formula constructs.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
}

FAIL_PATTERNS = [
    r"\(",
    r"\)",
    r"\[",
    r"\]",
    "frac{",
    "mathrm{",
    "operatorname{",
    "begin{",
    "end{",
    "_{mathrm",
    "^{T}",
    "∑t=",
    "sum_",
]


@dataclass
class ManifestFormula:
    id: str | None = None
    number: str | None = None
    latex: str = ""
    display: bool = True


@dataclass
class MathQaReport:
    docx: str
    passed: bool
    math_block_count: int
    suspicious_text_count: int
    equation_number_count: int
    failed_patterns: list[dict[str, str | int]] = field(default_factory=list)
    missing_numbers: list[str] = field(default_factory=list)
    duplicate_numbers: list[str] = field(default_factory=list)
    structural_failures: list[str] = field(default_factory=list)


def _read_document_xml(docx_path: Path) -> str:
    try:
        with zipfile.ZipFile(docx_path) as zf:
            return zf.read("word/document.xml").decode("utf-8")
    except KeyError as exc:
        raise ValueError("DOCX is missing word/document.xml") from exc
    except zipfile.BadZipFile as exc:
        raise ValueError("Input is not a valid .docx zip package") from exc


def _visible_texts(root: ET.Element) -> list[str]:
    texts: list[str] = []
    for node in root.findall(".//w:t", NS) + root.findall(".//m:t", NS):
        if node.text:
            texts.append(node.text)
    return texts


def _context(text: str, pattern: str) -> str:
    idx = text.find(pattern)
    if idx < 0:
        return ""
    start = max(0, idx - 24)
    end = min(len(text), idx + len(pattern) + 24)
    return text[start:end]


def _scan_suspicious_text(visible_text: str, *, allow_dollar: bool) -> list[dict[str, str | int]]:
    patterns = list(FAIL_PATTERNS)
    if not allow_dollar:
        patterns.append("$")
    failures: list[dict[str, str | int]] = []
    for pattern in patterns:
        count = visible_text.count(pattern)
        if count:
            failures.append(
                {
                    "pattern": pattern,
                    "count": count,
                    "context": _context(visible_text, pattern),
                }
            )
    return failures


def _parse_manifest(manifest_path: Path | None) -> list[ManifestFormula]:
    if manifest_path is None:
        return []
    formulas: list[ManifestFormula] = []
    current: ManifestFormula | None = None
    for raw in manifest_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("- "):
            if current is not None:
                formulas.append(current)
            current = ManifestFormula()
            line = line[2:].strip()
            if not line:
                continue
        if current is None:
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key == "id":
            current.id = value
        elif key == "number":
            current.number = value
        elif key == "latex":
            current.latex = value.replace("\\\\", "\\")
        elif key == "display":
            current.display = value.lower() not in {"false", "no", "0"}
    if current is not None:
        formulas.append(current)
    return formulas


def _equation_numbers(visible_text: str) -> list[str]:
    return re.findall(r"\(([0-9]+[a-z]?)\)", visible_text)


def check_docx_math(
    docx_path: str | Path,
    *,
    manifest_path: str | Path | None = None,
    allow_dollar: bool = False,
) -> MathQaReport:
    docx = Path(docx_path)
    xml = _read_document_xml(docx)
    root = ET.fromstring(xml)
    texts = _visible_texts(root)
    visible_text = "\n".join(texts)

    failed_patterns = _scan_suspicious_text(visible_text, allow_dollar=allow_dollar)
    formulas = _parse_manifest(Path(manifest_path) if manifest_path else None)
    expected_numbers = [
        f.number
        for f in formulas
        if f.display and f.number is not None and f.number.strip()
    ]
    found_numbers = _equation_numbers(visible_text)
    missing_numbers = [n for n in expected_numbers if n not in found_numbers]
    duplicate_numbers = sorted({n for n in found_numbers if found_numbers.count(n) > 1})

    has_fraction = "<m:f" in xml
    has_script = any(tag in xml for tag in ("<m:sSub", "<m:sSup", "<m:sSubSup"))
    structural_failures: list[str] = []
    if any(r"\frac" in f.latex for f in formulas) and not has_fraction:
        structural_failures.append("manifest contains \\frac but DOCX has no <m:f> OMML fraction")
    if any(("_" in f.latex or "^" in f.latex) for f in formulas) and not has_script:
        structural_failures.append("manifest contains subscripts/superscripts but DOCX has no OMML script structure")

    passed = not (
        failed_patterns
        or missing_numbers
        or duplicate_numbers
        or structural_failures
    )
    return MathQaReport(
        docx=str(docx),
        passed=passed,
        math_block_count=len(root.findall(".//m:oMath", NS)),
        suspicious_text_count=sum(int(item["count"]) for item in failed_patterns),
        equation_number_count=len(found_numbers),
        failed_patterns=failed_patterns,
        missing_numbers=missing_numbers,
        duplicate_numbers=duplicate_numbers,
        structural_failures=structural_failures,
    )


def format_report(report: MathQaReport) -> str:
    lines = [
        "PASS" if report.passed else "FAIL",
        f"docx: {report.docx}",
        f"math_block_count: {report.math_block_count}",
        f"suspicious_text_count: {report.suspicious_text_count}",
        f"equation_number_count: {report.equation_number_count}",
    ]
    if report.failed_patterns:
        lines.append("failed_patterns:")
        for item in report.failed_patterns:
            lines.append(
                f"  - {item['pattern']} x{item['count']}: {item['context']}"
            )
    if report.missing_numbers:
        lines.append("missing_numbers: " + ", ".join(report.missing_numbers))
    if report.duplicate_numbers:
        lines.append("duplicate_numbers: " + ", ".join(report.duplicate_numbers))
    if report.structural_failures:
        lines.append("structural_failures:")
        lines.extend(f"  - {item}" for item in report.structural_failures)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check DOCX math/OMML quality")
    parser.add_argument("docx", type=Path, help="DOCX file to inspect")
    parser.add_argument("--manifest", type=Path, help="Optional formula manifest YAML")
    parser.add_argument(
        "--allow-dollar",
        action="store_true",
        help="Do not fail on visible dollar signs in document text",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON report")
    args = parser.parse_args(argv)

    try:
        report = check_docx_math(
            args.docx,
            manifest_path=args.manifest,
            allow_dollar=args.allow_dollar,
        )
    except Exception as exc:
        print(f"FAIL\nerror: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(report.__dict__, ensure_ascii=False, indent=2))
    else:
        print(format_report(report))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
