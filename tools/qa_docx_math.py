#!/usr/bin/env python3
"""QA gate for Word DOCX delivery output.

The check is intentionally XML-level: generated disclosures must not merely
look plausible in Word, they must avoid leftover LaTeX/code-style fragments and
must use editable OMML structures for common formula constructs. It also catches
common delivery failures such as unrendered mermaid source entering the DOCX.
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

REGEX_FAIL_PATTERNS = [
    (
        "bare_subscript_identifier",
        re.compile(r"\b[A-Za-z][A-Za-z0-9]*_[A-Za-z0-9]+(?:_[A-Za-z0-9]+)*\b"),
    ),
    (
        "latex_command_residue",
        re.compile(r"\\[A-Za-z]+"),
    ),
    (
        "mermaid_source_residue",
        re.compile(
            r"\b(?:flowchart|graph)\s+(?:TB|BT|LR|RL|TD)\b"
            r"|^\s*(?:sequenceDiagram|stateDiagram|stateDiagram-v2|classDiagram|erDiagram|gantt|journey|mindmap)\b",
            re.MULTILINE,
        ),
    ),
]

FORMAL_TEXT_FAIL_PATTERNS = [
    "Word 交底书",
    "标准 LaTeX 源",
    "LaTeX 源写入中间稿",
    "中间稿",
    "公式编号作为正文标签管理",
    "DOCX QA",
    "案件证据包",
    "详细检索记录",
    "阳性对照",
    "来源状态已另行",
    "交底书正文仅摘录",
    "不堆列第三方检索平台",
    "商业库会话 URL",
    "学校 VPN",
    "session URL",
    "壹专利已完成商业库内容核验",
    "壹专利商业库完成内容核验",
    "正式公开引用仍建议",
    "稳定公开来源闭环",
    "商业库仅作内部发现",
    "query_log",
    "prior_art_dossier",
    "positive_controls",
    "unverified_sources",
    "commercial_db_discovered",
    "commercial_db_content_checked",
    "public_source_verified",
    "qa_docx_math.py",
    "md_to_docx.py",
    "mermaid_render.py",
    "cnipa_epub_search.py",
    "patent_link_verify.py",
]

FORMAL_REGEX_FAIL_PATTERNS = [
    (
        "formal_word_latex_process_note",
        re.compile(
            r"为避免.*Word.*公式残片|以下公式.*LaTeX.*中间稿|在\s*Word\s*中转换为可编辑公式"
        ),
    ),
    (
        "formal_evidence_package_note",
        re.compile(r"详细检索记录.*阳性对照.*来源状态|案件证据包|交接说明|交付检查记录"),
    ),
    (
        "agent_or_tool_process_residue",
        re.compile(r"\b(?:Agent|Codex|Claude|WebSearch|Playwright)\b"),
    ),
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
    media_count: int
    code_style_count: int
    word_auto_numbering_count: int
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


def _media_parts(docx_path: Path) -> list[str]:
    try:
        with zipfile.ZipFile(docx_path) as zf:
            return sorted(
                name
                for name in zf.namelist()
                if name.startswith("word/media/") and not name.endswith("/")
            )
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


def _scan_suspicious_text(
    visible_text: str,
    *,
    allow_dollar: bool,
    check_formal_text: bool,
) -> list[dict[str, str | int]]:
    patterns = list(FAIL_PATTERNS)
    if not allow_dollar:
        patterns.append("$")
    if check_formal_text:
        patterns.extend(FORMAL_TEXT_FAIL_PATTERNS)
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
    regex_patterns = list(REGEX_FAIL_PATTERNS)
    if check_formal_text:
        regex_patterns.extend(FORMAL_REGEX_FAIL_PATTERNS)
    for label, regex in regex_patterns:
        matches = list(regex.finditer(visible_text))
        if matches:
            first = matches[0]
            start = max(0, first.start() - 24)
            end = min(len(visible_text), first.end() + 24)
            failures.append(
                {
                    "pattern": label,
                    "count": len(matches),
                    "context": visible_text[start:end],
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
    normalized: list[ManifestFormula] = []
    for formula in formulas:
        if not formula.number and formula.id and re.fullmatch(r"[0-9]+[a-z]?", formula.id.strip()):
            formula.number = formula.id.strip()
        if formula.latex or formula.number:
            normalized.append(formula)
    return normalized


def _equation_numbers(root: ET.Element, visible_text: str, *, allow_text_fallback: bool) -> list[str]:
    numbers: list[str] = []
    for row in root.findall(".//w:tr", NS):
        cells = row.findall("./w:tc", NS)
        if len(cells) != 2:
            continue
        left, right = cells
        if not left.findall(".//m:oMath", NS):
            continue
        right_text = "".join(node.text or "" for node in right.findall(".//w:t", NS)).strip()
        match = re.fullmatch(r"\(([0-9]+[a-z]?)\)", right_text)
        if match:
            numbers.append(match.group(1))
    if numbers:
        return numbers
    if not allow_text_fallback:
        return []
    return re.findall(r"\(([0-9]+[a-z]?)\)", visible_text)


def check_docx_math(
    docx_path: str | Path,
    *,
    manifest_path: str | Path | None = None,
    allow_dollar: bool = False,
    allow_code_style: bool = False,
    min_media_count: int = 0,
    check_formal_text: bool = False,
) -> MathQaReport:
    docx = Path(docx_path)
    xml = _read_document_xml(docx)
    root = ET.fromstring(xml)
    texts = _visible_texts(root)
    visible_text = "\n".join(texts)
    media_count = len(_media_parts(docx))
    code_style_count = xml.count("Consolas")
    word_auto_numbering_count = len(root.findall(".//w:numPr", NS))

    failed_patterns = _scan_suspicious_text(
        visible_text,
        allow_dollar=allow_dollar,
        check_formal_text=check_formal_text,
    )
    formulas = _parse_manifest(Path(manifest_path) if manifest_path else None)
    expected_numbers = [
        f.number
        for f in formulas
        if f.display and f.number is not None and f.number.strip()
    ]
    found_numbers = _equation_numbers(root, visible_text, allow_text_fallback=not expected_numbers)
    missing_numbers = [n for n in expected_numbers if n not in found_numbers]
    duplicate_numbers = sorted({n for n in found_numbers if found_numbers.count(n) > 1})

    has_fraction = "<m:f" in xml
    has_script = any(tag in xml for tag in ("<m:sSub", "<m:sSup", "<m:sSubSup"))
    structural_failures: list[str] = []
    if any(r"\frac" in f.latex for f in formulas) and not has_fraction:
        structural_failures.append("manifest contains \\frac but DOCX has no <m:f> OMML fraction")
    if any(("_" in f.latex or "^" in f.latex) for f in formulas) and not has_script:
        structural_failures.append("manifest contains subscripts/superscripts but DOCX has no OMML script structure")
    if min_media_count and media_count < min_media_count:
        structural_failures.append(
            f"DOCX media count {media_count} is below required minimum {min_media_count}"
        )
    if code_style_count and not allow_code_style:
        structural_failures.append(
            "DOCX contains Consolas/code-style runs; final disclosures must not contain mermaid/code leftovers"
        )
    if word_auto_numbering_count:
        structural_failures.append(
            "DOCX contains Word automatic numbering (<w:numPr>); final disclosures must use literal local list markers to avoid cross-section numbering"
        )

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
        media_count=media_count,
        code_style_count=code_style_count,
        word_auto_numbering_count=word_auto_numbering_count,
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
        f"media_count: {report.media_count}",
        f"code_style_count: {report.code_style_count}",
        f"word_auto_numbering_count: {report.word_auto_numbering_count}",
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
    parser.add_argument(
        "--allow-code-style",
        action="store_true",
        help="Do not fail on Consolas/code-style runs; use only for diagnostics, not final delivery",
    )
    parser.add_argument(
        "--min-media-count",
        type=int,
        default=0,
        metavar="N",
        help="Require at least N embedded word/media files, useful after mermaid rendering",
    )
    parser.add_argument(
        "--check-formal-text",
        action="store_true",
        help="Fail on process/handoff/evidence-package text that must not appear in formal disclosure正文",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON report")
    args = parser.parse_args(argv)

    try:
        report = check_docx_math(
            args.docx,
            manifest_path=args.manifest,
            allow_dollar=args.allow_dollar,
            allow_code_style=args.allow_code_style,
            min_media_count=max(args.min_media_count, 0),
            check_formal_text=args.check_formal_text,
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
