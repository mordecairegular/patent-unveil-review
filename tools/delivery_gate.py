#!/usr/bin/env python3
"""Unified delivery gate for patent disclosure handoff artifacts.

The gate is intentionally read-only for the checked disclosure files. It reuses
existing QA tools for DOCX math/formal-text checks and numeric reproduction,
then appends the case-level delivery check log unless ``--no-record`` is used.
"""
from __future__ import annotations

import argparse
import contextlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
import difflib
import hashlib
import io
import json
import re
import sys
import unicodedata
import zipfile
from pathlib import Path
from typing import Any, Iterable, Sequence
from xml.etree import ElementTree as ET

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
}

CHECK_IDS = (
    "C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10", "C11",
    "C12", "C13", "C14", "C15", "C16", "C17",
)

PLACEHOLDER_RE = re.compile(r"待填|待补充|待确认|待核|TODO|TBD|\[待填写\]|【待填写】", re.I)
USER_FILL_LINE_RE = re.compile(
    r"^\s*[-*]?\s*\*{0,2}(姓名|电话|邮箱|技术联系人|发明人|申请人)"
)
USER_FILL_MARKER_RE = re.compile(r"（用户自填）|\[待填写\]|待填写")
FIELD_LABEL_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+){2,}\b")
FILENAME_RE = re.compile(r"^.+_\d{14}(?:_[A-Za-z0-9-]+)?\.(md|docx)$", re.I)
NUMERIC_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")
DEFENSIVE_PHRASE_RE = re.compile(r"不在于|不作为|不强制|不以|不宜|显著降低")
# 高信号模糊限定词（判定语境常被代理人追问“具体数值/条件是什么”）；
# 词非禁用，逐处判定：给阈值/相对基准/组合判定条件，或注明示例阈值待标定。
FUZZY_QUALIFIER_RE = re.compile(
    r"近似同步|近似相[同等]|基本(?:相同|一致|同步)|大致相同"
    r"|明显(?:大于|小于|高于|低于|优于|阶梯|异常)"
    r"|风险较[低高]|证据不足|必要时|视情况|适当(?:调整|放宽|收紧)"
)


@dataclass
class CheckOutcome:
    check: str
    name: str
    fail_items: list[dict[str, Any]] = field(default_factory=list)
    warn_items: list[dict[str, Any]] = field(default_factory=list)
    info_items: list[dict[str, Any]] = field(default_factory=list)

    @property
    def status(self) -> str:
        if self.fail_items:
            return "FAIL"
        if self.warn_items:
            return "WARN"
        return "PASS"

    def log_line(self) -> str:
        if self.fail_items:
            noun = _plural(len(self.fail_items), "failure")
            return f"[{self.check}] FAIL: {len(self.fail_items)} {noun}"
        if self.warn_items:
            noun = _plural(len(self.warn_items), "warning")
            return f"[{self.check}] WARN: {len(self.warn_items)} {noun}"
        if self.info_items:
            return f"[{self.check}] PASS: {self.name} ({len(self.info_items)} info)"
        return f"[{self.check}] PASS: {self.name}"


def _plural(count: int, singular: str) -> str:
    return singular if count == 1 else singular + "s"


def _safe_text(value: Any, *, limit: int = 280) -> str:
    text = str(value).replace("\r", " ").replace("\n", " ").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _read_docx_xml(docx_path: Path) -> str:
    try:
        with zipfile.ZipFile(docx_path) as zf:
            return zf.read("word/document.xml").decode("utf-8")
    except KeyError as exc:
        raise ValueError(f"DOCX is missing word/document.xml: {docx_path}") from exc
    except zipfile.BadZipFile as exc:
        raise ValueError(f"Input is not a valid .docx zip package: {docx_path}") from exc


def _docx_root(docx_path: Path) -> ET.Element:
    return ET.fromstring(_read_docx_xml(docx_path))


def _element_text(element: ET.Element) -> str:
    parts: list[str] = []
    for node in element.findall(".//w:t", NS) + element.findall(".//m:t", NS):
        if node.text:
            parts.append(node.text)
    return "".join(parts)


def extract_docx_paragraph_texts(docx_path: Path) -> list[str]:
    root = _docx_root(docx_path)
    lines: list[str] = []
    for para in root.findall(".//w:p", NS):
        text = _element_text(para)
        if text.strip():
            lines.append(text)
    if not lines:
        text = extract_docx_visible_text(docx_path)
        return [text] if text else []
    return lines


def extract_docx_visible_text(docx_path: Path) -> str:
    root = _docx_root(docx_path)
    parts: list[str] = []
    for node in root.findall(".//w:t", NS) + root.findall(".//m:t", NS):
        if node.text:
            parts.append(node.text)
    return "\n".join(parts)


def run_docx_math_qa(docx_path: Path, manifest_path: Path | None) -> CheckOutcome:
    outcome = CheckOutcome("C1", "docx_math_qa")
    try:
        from qa_docx_math import check_docx_math

        report = check_docx_math(
            docx_path,
            manifest_path=manifest_path,
            check_formal_text=True,
        )
    except Exception as exc:  # noqa: BLE001 - gate must report, not crash
        outcome.fail_items.append({"error": str(exc)})
        return outcome

    if report.passed:
        outcome.info_items.append(
            {
                "math_block_count": report.math_block_count,
                "media_count": report.media_count,
                "equation_number_count": report.equation_number_count,
            }
        )
        return outcome

    item: dict[str, Any] = {
        "math_block_count": report.math_block_count,
        "media_count": report.media_count,
        "suspicious_text_count": report.suspicious_text_count,
    }
    if report.failed_patterns:
        item["failed_patterns"] = report.failed_patterns
    if report.missing_numbers:
        item["missing_numbers"] = report.missing_numbers
    if report.duplicate_numbers:
        item["duplicate_numbers"] = report.duplicate_numbers
    if report.structural_failures:
        item["structural_failures"] = report.structural_failures
    outcome.fail_items.append(item)
    return outcome


def _load_extra_whitelists(path: Path | None) -> list[re.Pattern[str]]:
    if path is None:
        return []
    patterns: list[re.Pattern[str]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        patterns.append(re.compile(line))
    return patterns


def _is_extra_whitelisted(line: str, patterns: Iterable[re.Pattern[str]]) -> bool:
    return any(pattern.search(line) for pattern in patterns)


def _scan_placeholder_lines(
    *,
    label: str,
    lines: Sequence[str],
    scan_table_ruogan: bool,
    extra_whitelist: Sequence[re.Pattern[str]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    defects: list[dict[str, Any]] = []
    user_fill: list[dict[str, Any]] = []
    notes: list[dict[str, Any]] = []

    for line_no, raw in enumerate(lines, start=1):
        line = raw.rstrip("\n")
        if _is_extra_whitelisted(line, extra_whitelist):
            continue

        is_user_fill = bool(USER_FILL_LINE_RE.match(line) and USER_FILL_MARKER_RE.search(line))
        matches = list(PLACEHOLDER_RE.finditer(line))

        if is_user_fill and matches:
            user_fill.append({"file": label, "line": line_no, "content": _safe_text(line)})
            continue

        for match in matches:
            token = match.group(0)
            if token.startswith("待核") and "待核（provenance-only" in line:
                notes.append(
                    {
                        "file": label,
                        "line": line_no,
                        "kind": "provenance_only_pending",
                        "content": _safe_text(line),
                    }
                )
                continue
            defects.append(
                {
                    "file": label,
                    "line": line_no,
                    "token": token,
                    "content": _safe_text(line),
                }
            )

        stripped = line.strip()
        if scan_table_ruogan and "若干" in line and stripped.startswith("|") and "|" in stripped[1:]:
            defects.append(
                {
                    "file": label,
                    "line": line_no,
                    "token": "若干",
                    "content": _safe_text(line),
                }
            )

    return defects, user_fill, notes


def scan_placeholders(
    md_path: Path,
    docx_path: Path,
    *,
    whitelist_file: Path | None = None,
) -> tuple[CheckOutcome, list[dict[str, Any]]]:
    outcome = CheckOutcome("C2", "placeholder_scan")
    extra_whitelist = _load_extra_whitelists(whitelist_file)
    user_fill: list[dict[str, Any]] = []

    md_lines = md_path.read_text(encoding="utf-8").splitlines()
    md_defects, md_user_fill, md_notes = _scan_placeholder_lines(
        label=md_path.name,
        lines=md_lines,
        scan_table_ruogan=True,
        extra_whitelist=extra_whitelist,
    )
    docx_lines = extract_docx_paragraph_texts(docx_path)
    docx_defects, docx_user_fill, docx_notes = _scan_placeholder_lines(
        label=docx_path.name,
        lines=docx_lines,
        scan_table_ruogan=False,
        extra_whitelist=extra_whitelist,
    )

    outcome.warn_items.extend(md_defects + docx_defects + md_notes + docx_notes)
    user_fill.extend(md_user_fill + docx_user_fill)
    return outcome, user_fill


def _is_separator_row(cells: Sequence[str]) -> bool:
    if not cells:
        return False
    return all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells)


def _split_table_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def _iter_markdown_tables(lines: Sequence[str]) -> Iterable[tuple[int, list[list[str]]]]:
    start: int | None = None
    rows: list[list[str]] = []
    for idx, line in enumerate(lines, start=1):
        if "|" in line and line.strip():
            if start is None:
                start = idx
                rows = []
            rows.append(_split_table_row(line))
        else:
            if start is not None and len(rows) >= 2:
                yield start, rows
            start = None
            rows = []
    if start is not None and len(rows) >= 2:
        yield start, rows


def _parse_number(cell: str) -> tuple[float, bool] | None:
    text = cell.strip().replace(",", "")
    if not NUMERIC_RE.fullmatch(text):
        return None
    is_int = re.fullmatch(r"[+-]?\d+", text) is not None
    return float(text), is_int


def _close_number(actual: float, expected: float, *, integer_exact: bool) -> bool:
    if integer_exact:
        return int(actual) == int(expected)
    tolerance = max(1e-12, 1e-6 * abs(expected))
    return abs(actual - expected) <= tolerance


def check_count_closure(md_path: Path) -> CheckOutcome:
    outcome = CheckOutcome("C3", "count_closure")
    lines = md_path.read_text(encoding="utf-8").splitlines()

    for table_start, raw_rows in _iter_markdown_tables(lines):
        rows = [row for row in raw_rows if not _is_separator_row(row)]
        if len(rows) < 2:
            continue
        header = rows[0]
        body = rows[1:]
        width = max(len(row) for row in rows)
        padded_header = header + [""] * (width - len(header))
        total_rows = [
            (offset, row + [""] * (width - len(row)))
            for offset, row in enumerate(body, start=1)
            if row and row[0].strip() in {"合计", "总计", "共计"}
        ]
        if not total_rows:
            continue
        data_rows = [
            row + [""] * (width - len(row))
            for row in body
            if not (row and row[0].strip() in {"合计", "总计", "共计"})
        ]
        for body_offset, total_row in total_rows:
            total_line = table_start + body_offset + (
                1 if len(raw_rows) > 1 and _is_separator_row(raw_rows[1]) else 0
            )
            for col_idx in range(1, width):
                values: list[float] = []
                integer_exact = True
                numeric_column = True
                for row in data_rows:
                    parsed = _parse_number(row[col_idx] if col_idx < len(row) else "")
                    if parsed is None:
                        numeric_column = False
                        break
                    value, is_int = parsed
                    values.append(value)
                    integer_exact = integer_exact and is_int
                if not numeric_column or not values:
                    continue
                total_parsed = _parse_number(total_row[col_idx])
                if total_parsed is None:
                    continue
                actual = sum(values)
                expected, total_is_int = total_parsed
                integer_exact = integer_exact and total_is_int
                if not _close_number(actual, expected, integer_exact=integer_exact):
                    outcome.warn_items.append(
                        {
                            "table_line": table_start,
                            "total_line": total_line,
                            "column": padded_header[col_idx] or f"col_{col_idx + 1}",
                            "expected": expected,
                            "actual": actual,
                        }
                    )
    return outcome


def check_field_label_integrity(md_path: Path, docx_path: Path) -> CheckOutcome:
    outcome = CheckOutcome("C4", "field_label_integrity")
    md_text = md_path.read_text(encoding="utf-8")
    docx_text = extract_docx_visible_text(docx_path)
    labels: dict[str, int] = {}
    for line_no, line in enumerate(md_text.splitlines(), start=1):
        for match in FIELD_LABEL_RE.finditer(line):
            labels.setdefault(match.group(0), line_no)

    compact_docx = docx_text.replace("\n", "")
    for label, line_no in labels.items():
        if label in docx_text:
            continue
        transformed = label.replace("_", "") in compact_docx
        outcome.fail_items.append(
            {
                "label": label,
                "line": line_no,
                "reason": "transformed" if transformed else "missing",
            }
        )

    try:
        root = _docx_root(docx_path)
    except Exception as exc:  # noqa: BLE001
        outcome.fail_items.append({"error": str(exc)})
        return outcome

    for idx, math in enumerate(root.findall(".//m:oMath", NS), start=1):
        text = _element_text(math).replace(" ", "")
        sub_count = len(math.findall(".//m:sSub", NS))
        if (
            sub_count >= 2
            and len(text) >= 12
            and text.isascii()
            and text.isalpha()
            and text.islower()
        ):
            outcome.warn_items.append(
                {
                    "math_index": idx,
                    "text": text,
                    "subscript_layers": sub_count,
                    "reason": "suspected_field_label_formula",
                }
            )
    return outcome


def check_formula_paragraph(docx_path: Path) -> CheckOutcome:
    outcome = CheckOutcome("C5", "formula_paragraph")
    root = _docx_root(docx_path)

    for run_idx, run in enumerate(root.findall(".//w:r", NS), start=1):
        for color in run.findall(".//w:color", NS):
            value = (
                color.attrib.get(f"{{{NS['w']}}}val")
                or color.attrib.get("val")
                or ""
            ).strip()
            if value.lower() in {"ff0000", "red", "#ff0000"}:
                outcome.fail_items.append(
                    {"run": run_idx, "reason": "red_text_residue", "color": value}
                )

    for para_idx, para in enumerate(root.findall(".//m:oMathPara", NS), start=1):
        count = len(para.findall(".//m:oMath", NS))
        if count > 1:
            outcome.warn_items.append(
                {
                    "math_paragraph": para_idx,
                    "math_count": count,
                    "reason": "multiple_omath_in_one_paragraph",
                }
            )
    return outcome


def check_filename_convention(md_path: Path, docx_path: Path) -> CheckOutcome:
    outcome = CheckOutcome("C6", "filename_convention")
    md_ok = bool(FILENAME_RE.fullmatch(md_path.name))
    docx_ok = bool(FILENAME_RE.fullmatch(docx_path.name))
    same_stem = md_path.stem == docx_path.stem
    if not (md_ok and docx_ok and same_stem):
        outcome.warn_items.append(
            {
                "md": md_path.name,
                "docx": docx_path.name,
                "md_matches": md_ok,
                "docx_matches": docx_ok,
                "same_stem": same_stem,
            }
        )
    return outcome


def check_confirmation_artifacts(
    case_dir: Path,
    *,
    entry: str,
    t0_dir: Path,
    preview_skipped: bool,
) -> CheckOutcome:
    outcome = CheckOutcome("C7", "confirmation_artifacts")

    dossier = case_dir / "prior_art_search" / "prior_art_dossier.md"
    if not dossier.is_file():
        outcome.warn_items.append({"checkpoint": 3, "message": "确认点3未见落盘产物"})
    else:
        text = dossier.read_text(encoding="utf-8", errors="replace")
        if "确认点 3" not in text and "签核" not in text:
            outcome.warn_items.append(
                {"checkpoint": 3, "message": "确认点3产物未见确认点 3/签核"}
            )

    preview_records = sorted(case_dir.glob("预览确认记录*.md"))
    if preview_records:
        outcome.info_items.append(
            {"checkpoint": 4, "artifact": preview_records[0].name}
        )
    elif preview_skipped:
        outcome.info_items.append(
            {"checkpoint": 4, "message": "预览未经用户确认"}
        )
    else:
        outcome.warn_items.append({"checkpoint": 4, "message": "确认点4未见落盘产物"})

    if entry == "t0":
        if not any(t0_dir.glob("*边界卡*.md")):
            outcome.warn_items.append({"checkpoint": 1, "message": "确认点1未见落盘产物"})
        if not any(t0_dir.glob("*主题卡*.md")):
            outcome.warn_items.append({"checkpoint": 2, "message": "确认点2未见落盘产物"})

    return outcome


def run_numeric_reproduce(numeric_spec: Path | None) -> CheckOutcome:
    outcome = CheckOutcome("C8", "numeric_reproduce")
    if numeric_spec is None:
        outcome.info_items.append({"status": "not_applicable"})
        return outcome

    try:
        from qa_numeric_reproduce import load_spec, run

        spec = load_spec(numeric_spec)
        passed, results = run(spec)
    except Exception as exc:  # noqa: BLE001
        outcome.fail_items.append({"error": str(exc)})
        return outcome

    if passed:
        outcome.info_items.append({"n_checks": len(results)})
    else:
        failed = [item for item in results if not item.get("pass")]
        outcome.fail_items.append({"n_fail": len(failed), "failed": failed})
    return outcome


def _read_first_changelog_version(root: Path) -> str:
    changelog = root / "CHANGELOG.md"
    if not changelog.is_file():
        return "unknown"
    for line in changelog.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("## v"):
            return line.strip()
    return "unknown"


def _resolve_gitdir(root: Path) -> Path | None:
    marker = root / ".git"
    try:
        if marker.is_dir():
            return marker
        if marker.is_file():
            text = marker.read_text(encoding="utf-8", errors="replace").strip()
            if text.lower().startswith("gitdir:"):
                raw = text.split(":", 1)[1].strip()
                path = Path(raw)
                if not path.is_absolute():
                    path = (root / path).resolve()
                return path
    except OSError:
        return None
    return None


def _read_git_file_version(root: Path) -> str:
    """Best-effort git version without invoking any git command."""
    gitdir = _resolve_gitdir(root)
    if gitdir is None:
        return "unknown"
    try:
        head = (gitdir / "HEAD").read_text(encoding="utf-8", errors="replace").strip()
        common = gitdir
        common_file = gitdir / "commondir"
        if common_file.is_file():
            raw_common = common_file.read_text(encoding="utf-8", errors="replace").strip()
            common_path = Path(raw_common)
            common = common_path if common_path.is_absolute() else (gitdir / common_path).resolve()

        ref_rel: str | None = None
        if head.startswith("ref:"):
            ref_rel = head.split(":", 1)[1].strip()
            ref_path = common / ref_rel
            commit = ref_path.read_text(encoding="utf-8", errors="replace").strip()
        else:
            commit = head
        short = commit[:7] if re.fullmatch(r"[0-9a-fA-F]{40}", commit) else "unknown"

        log_candidates = []
        if ref_rel:
            log_candidates.append(common / "logs" / ref_rel)
        log_candidates.append(gitdir / "logs" / "HEAD")
        date = "unknown"
        for log_path in log_candidates:
            if not log_path.is_file():
                continue
            lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
            if not lines:
                continue
            fields = lines[-1].split()
            if len(fields) >= 5 and fields[4].lstrip("-+").isdigit():
                timestamp = int(fields[4])
                date = datetime.fromtimestamp(timestamp, timezone.utc).strftime("%Y-%m-%d")
                break
        if short == "unknown":
            return "unknown"
        return f"{short}_{date}" if date != "unknown" else short
    except OSError:
        return "unknown"


def version_report(root: Path) -> CheckOutcome:
    outcome = CheckOutcome("C9", "version_report")
    outcome.info_items.append(
        {
            "version": _read_git_file_version(root),
            "changelog": _read_first_changelog_version(root),
        }
    )
    return outcome


def check_defensive_phrasing(md_path: Path) -> CheckOutcome:
    """WARN-level scan: surface negation/defensive phrasing for human judgment.

    These tokens are not banned; each occurrence must be judged — an
    attorney-facing reminder belongs in the handoff note, a genuine technical
    feature should be rewritten as an affirmative limitation. Never FAIL.
    """
    outcome = CheckOutcome("C10", "defensive_phrasing")
    for line_no, raw in enumerate(
        md_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        for match in DEFENSIVE_PHRASE_RE.finditer(raw):
            outcome.warn_items.append(
                {
                    "file": md_path.name,
                    "line": line_no,
                    "token": match.group(0),
                    "content": _safe_text(raw),
                    "hint": "判定归属：代理人提示→交接说明；技术特征→改正向限定",
                }
            )
    return outcome


def check_fuzzy_qualifier(md_path: Path) -> CheckOutcome:
    """WARN-level scan: surface fuzzy qualifiers for quantification judgment.

    From a two-case attorney-review retrospective: phrases
    like 近似同步 / 明显大于 / 证据不足 / 必要时 draw "请给出具体数值范围/
    判定条件" comments when left unquantified. Each occurrence needs one of:
    a numeric threshold/range, a relative baseline, or a compound condition —
    or an explicit "示例阈值，需按实际数据标定" note. Never FAIL.
    """
    outcome = CheckOutcome("C11", "fuzzy_qualifier")
    for line_no, raw in enumerate(
        md_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        for match in FUZZY_QUALIFIER_RE.finditer(raw):
            outcome.warn_items.append(
                {
                    "file": md_path.name,
                    "line": line_no,
                    "token": match.group(0),
                    "content": _safe_text(raw),
                    "hint": "量化三选一：数值阈值/相对基准/组合判定条件；或注明示例阈值待标定（见 disclosure_builder.md 模糊限定词门禁）",
                }
            )
    return outcome


CLAIM_CLASS_ENUM = {"independent_core", "dependent", "implementation_param", "auxiliary_evidence"}
BASELINE_KIND_ENUM = {"standard", "historical_clean", "post_treatment", "healthy_peer"}
STEP_REQUIRED_FIELDS = ("id", "name", "claim_class", "inputs", "processing", "outputs", "consumers", "degraded_branch")
BASELINE_REQUIRED_FIELDS = ("id", "kind", "source", "purpose", "update_condition")
DECISION_REF_RE = re.compile(r"\bD\d{1,3}\b")
# 实施参数（数字+单位）扫描；年份/式号/步骤号不含下列单位故不受影响
IMPL_PARAM_UNIT_RE = re.compile(
    r"\d+(?:\.\d+)?\s*(?:小时|分钟|毫秒|个百分点|%|℃|°C|W/m[²2]|kWh|kW\b|MW\b|MHz|Hz|元/kWh|mm\b|μm|nm\b)"
)


def discover_evidence_contract(case_dir: Path) -> Path | None:
    for pattern in ("*技术证据合同*.yaml", "*技术证据合同*.yml", "*evidence_contract*.yaml", "*evidence_contract*.yml"):
        matches = sorted(case_dir.glob(pattern))
        if matches:
            return matches[-1]
    return None


def _load_contract(contract_path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        import yaml  # type: ignore
    except ImportError:
        return None, "pyyaml 未安装：pip install pyyaml 后重跑 C12"
    try:
        data = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - report parse failure as gate item
        return None, f"证据合同解析失败：{exc}"
    if not isinstance(data, dict):
        return None, "证据合同顶层须为映射（meta/baselines/decisions/steps）"
    return data, None


def check_evidence_contract(contract_path: Path | None) -> CheckOutcome:
    """C12: structural validation of the technical evidence contract (FAIL-level).

    Deterministic checks only — semantic judgments (e.g. whether a standard
    baseline is misused as a live observation) stay in §8.1. Skips (info) when
    no contract file exists: not every case requires one.
    """
    outcome = CheckOutcome("C12", "evidence_contract")
    if contract_path is None:
        outcome.info_items.append({"note": "未发现技术证据合同文件，跳过（测量/诊断类案件应提供）"})
        return outcome
    data, err = _load_contract(contract_path)
    if err:
        target = outcome.warn_items if "pyyaml" in err else outcome.fail_items
        target.append({"file": contract_path.name, "issue": err})
        return outcome

    baselines = data.get("baselines") or []
    decisions = data.get("decisions") or []
    steps = data.get("steps") or []
    baseline_ids = {str(b.get("id")) for b in baselines if isinstance(b, dict)}
    decision_ids = {str(d.get("id")) for d in decisions if isinstance(d, dict)}
    step_ids = {str(s.get("id")) for s in steps if isinstance(s, dict)}

    def fail(issue: str, **extra: Any) -> None:
        outcome.fail_items.append({"file": contract_path.name, "issue": issue, **extra})

    def warn(issue: str, **extra: Any) -> None:
        outcome.warn_items.append({"file": contract_path.name, "issue": issue, **extra})

    for b in baselines:
        if not isinstance(b, dict):
            fail("baselines 条目须为映射")
            continue
        bid = str(b.get("id", "?"))
        for field_name in BASELINE_REQUIRED_FIELDS:
            if not str(b.get(field_name) or "").strip():
                fail(f"基线 {bid} 缺少必填字段 {field_name}")
        kind = str(b.get("kind") or "")
        if kind and kind not in BASELINE_KIND_ENUM:
            fail(f"基线 {bid} 的 kind 非法：{kind}", allowed=sorted(BASELINE_KIND_ENUM))

    if not steps:
        fail("steps 为空：证据合同至少须包含一个步骤条目")

    # 预收集每个步骤 inputs 中的 derived: 引用，供 consumers 链路核对（与遍历顺序无关）
    derived_inputs: dict[str, set[str]] = {}
    for s in steps:
        if isinstance(s, dict):
            sid = str(s.get("id", "?"))
            for inp in s.get("inputs") or []:
                if isinstance(inp, dict):
                    source = str(inp.get("source") or "")
                    if source.startswith("derived:"):
                        derived_inputs.setdefault(sid, set()).add(source.split(":", 1)[1])

    for s in steps:
        if not isinstance(s, dict):
            fail("steps 条目须为映射")
            continue
        sid = str(s.get("id", "?"))
        for field_name in STEP_REQUIRED_FIELDS:
            value = s.get(field_name)
            if value is None or (isinstance(value, (str, list)) and not value):
                fail(f"步骤 {sid} 缺少必填字段 {field_name}")
        claim_class = str(s.get("claim_class") or "")
        if claim_class and claim_class not in CLAIM_CLASS_ENUM:
            fail(f"步骤 {sid} 的 claim_class 非法：{claim_class}", allowed=sorted(CLAIM_CLASS_ENUM))
        # 观测能力 vs 声称精度（rank 越大越精细）
        obs_rank, out_rank = s.get("observation_rank"), s.get("output_rank")
        if (obs_rank is None) != (out_rank is None):
            warn(f"步骤 {sid} 只填写了 observation_rank/output_rank 之一，无法校验声称精度")
        elif obs_rank is not None and out_rank is not None:
            try:
                if float(out_rank) > float(obs_rank):
                    fail(
                        f"步骤 {sid} 声称输出精度（rank {out_rank}）超过观测精度（rank {obs_rank}）",
                        hint="降级为候选+置信度，或在 inputs 中补充更细粒度证据",
                    )
            except (TypeError, ValueError):
                fail(f"步骤 {sid} 的 observation_rank/output_rank 须为数值")
        # 输入引用完整性
        for inp in s.get("inputs") or []:
            if not isinstance(inp, dict):
                continue
            source = str(inp.get("source") or "")
            if source.startswith("baseline:"):
                ref = source.split(":", 1)[1]
                if ref not in baseline_ids:
                    fail(f"步骤 {sid} 引用了不存在的基线 {ref}")
            elif source.startswith("derived:"):
                ref = source.split(":", 1)[1]
                if ref not in step_ids:
                    fail(f"步骤 {sid} 引用了不存在的前序步骤 {ref}")
        # 阈值来源
        for th in s.get("thresholds") or []:
            if isinstance(th, dict) and not str(th.get("source") or "").strip():
                fail(f"步骤 {sid} 的阈值「{th.get('name', '?')}」缺少来源（可写「示例值，待现场标定」）")
        # 决策编号引用
        for text_field in ("processing", "degraded_branch"):
            for ref in DECISION_REF_RE.findall(str(s.get(text_field) or "")):
                if decision_ids and ref not in decision_ids:
                    fail(f"步骤 {sid} 的 {text_field} 引用了决策表中不存在的 {ref}")
        # 下游消费者引用
        for consumer in s.get("consumers") or []:
            consumer = str(consumer)
            if consumer == "terminal":
                continue
            if consumer not in step_ids:
                fail(f"步骤 {sid} 的 consumers 引用了不存在的步骤 {consumer}")
            elif sid not in derived_inputs.get(consumer, set()):
                # producer declares consumer, but consumer's inputs never reference producer
                warn(
                    f"步骤 {sid} 声明下游为 {consumer}，但 {consumer} 的 inputs 未引用 derived:{sid}（疑似步骤链断裂）"
                )
    return outcome


def check_decision_refs(md_path: Path, contract_path: Path | None) -> CheckOutcome:
    """C13: decision-id single source of truth (WARN-level).

    Body D-id references must exist in the contract's decision table; table
    entries should be referenced at least once. WARN not FAIL: a bare "D1"
    token in prose may have unrelated meaning — each hit needs a human call.
    """
    outcome = CheckOutcome("C13", "decision_refs")
    if contract_path is None:
        outcome.info_items.append({"note": "无证据合同/决策表，跳过决策编号核对"})
        return outcome
    data, err = _load_contract(contract_path)
    if err or not data:
        outcome.info_items.append({"note": f"决策表不可读，跳过：{err}"})
        return outcome
    decision_ids = {str(d.get("id")) for d in (data.get("decisions") or []) if isinstance(d, dict)}
    if not decision_ids:
        outcome.info_items.append({"note": "证据合同未定义 decisions，跳过"})
        return outcome
    body = md_path.read_text(encoding="utf-8")
    referenced = set(DECISION_REF_RE.findall(body))
    for unknown in sorted(referenced - decision_ids):
        outcome.warn_items.append(
            {"file": md_path.name, "issue": f"正文引用了决策表中不存在的编号 {unknown}", "hint": "核对是否为决策引用漂移或普通符号撞名"}
        )
    for unused in sorted(decision_ids - referenced):
        outcome.warn_items.append(
            {"file": md_path.name, "issue": f"决策表条目 {unused} 未被正文引用", "hint": "正文各视图应引用统一决策编号，防 AND/OR 漂移"}
        )
    return outcome


def check_attorney_reply(comments_json: Path | None, reply_path: Path | None) -> CheckOutcome:
    """C14: attorney reply completeness — reply entries must cover every
    top-level attorney comment (FAIL on mismatch). Skips unless both files given.
    """
    outcome = CheckOutcome("C14", "attorney_reply_consistency")
    if comments_json is None or reply_path is None:
        outcome.info_items.append({"note": "未提供 --comments-json/--attorney-reply，跳过"})
        return outcome
    raw = comments_json.read_text(encoding="utf-8").strip()
    if "COMMENT_EXTRACT_JSON" in raw:
        raw = raw.rsplit("COMMENT_EXTRACT_JSON", 1)[1].strip()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        outcome.fail_items.append({"file": comments_json.name, "issue": f"批注 JSON 解析失败：{exc}"})
        return outcome
    canonical = bool(payload.get("schema_version"))
    if canonical:
        source = payload.get("source")
        count = payload.get("count")
        if not isinstance(source, dict) or not {
            "type",
            "file",
            "sha256",
            "verbatim_status",
        } <= set(source):
            outcome.fail_items.append(
                {
                    "file": comments_json.name,
                    "reason": "canonical_source_invalid",
                    "issue": "规范批注 JSON 缺少完整 source 溯源字段",
                }
            )
        if not isinstance(count, dict) or not {
            "top_level",
            "replies",
            "basis",
            "status",
        } <= set(count):
            outcome.fail_items.append(
                {
                    "file": comments_json.name,
                    "reason": "canonical_count_invalid",
                    "issue": "规范批注 JSON 缺少完整 count 口径字段",
                }
            )
        elif count.get("status") != "verified":
            outcome.warn_items.append(
                {
                    "file": comments_json.name,
                    "reason": "comment_count_provisional",
                    "basis": count.get("basis"),
                    "issue": "代理意见条数为暂定口径，须由用户确认后再对外称完整覆盖",
                }
            )
        for index, comment in enumerate(payload.get("comments", []), start=1):
            if not isinstance(comment, dict) or not {
                "seq",
                "text",
                "text_sha256",
                "source_locator",
                "target_confirmation",
                "subrequirements",
            } <= set(comment):
                outcome.fail_items.append(
                    {
                        "file": comments_json.name,
                        "reason": "canonical_comment_invalid",
                        "item": index,
                        "issue": "规范批注条目缺少原文、定位或确认状态字段",
                    }
                )
    top_level = [
        c
        for c in payload.get("comments", [])
        if isinstance(c, dict) and not c.get("is_reply")
    ]
    expected = {str(c.get("seq") or "").upper() for c in top_level if c.get("seq")}
    if not expected:
        count_block = payload.get("count")
        declared = (
            count_block.get("top_level", 0)
            if isinstance(count_block, dict)
            else payload.get("top_level_count", 0)
        )
        expected = {f"C{i:02d}" for i in range(1, int(declared) + 1)}
    count_block = payload.get("count")
    declared_top_level = (
        int(count_block.get("top_level", 0))
        if isinstance(count_block, dict)
        else int(payload.get("top_level_count", 0))
    )
    if declared_top_level and declared_top_level != len(top_level):
        outcome.fail_items.append(
            {
                "file": comments_json.name,
                "reason": "comment_count_mismatch",
                "declared": declared_top_level,
                "parsed": len(top_level),
                "issue": "批注条数声明与 comments 列表不一致",
            }
        )
    reply_text = reply_path.read_text(encoding="utf-8")
    found: set[str] = set()
    for match in re.finditer(r"^(?:#{2,4}\s*|\|\s*)C(\d{1,3})\b", reply_text, re.M):
        found.add(f"C{int(match.group(1)):02d}")
    missing = sorted(expected - found)
    extra = sorted(found - expected)
    if missing:
        outcome.fail_items.append(
            {
                "file": reply_path.name,
                "issue": f"代理意见 {len(expected)} 条，回复缺少 {len(missing)} 条：{','.join(missing)}",
            }
        )
    if extra:
        outcome.warn_items.append(
            {"file": reply_path.name, "issue": f"回复中出现批注清单外的编号：{','.join(extra)}"}
        )
    if not missing:
        outcome.info_items.append({"note": f"回复覆盖全部 {len(expected)} 条代理意见"})
    return outcome


def check_impl_params_in_claims(md_path: Path) -> CheckOutcome:
    """C15: implementation parameters (number+unit) inside the independent-claim
    region of Chapter 5 (WARN-level). Dependent-claim subsections are exempt —
    concrete values belong there or in embodiments.
    """
    outcome = CheckOutcome("C15", "impl_params_in_claims")
    lines = md_path.read_text(encoding="utf-8").splitlines()
    in_ch5 = False
    in_dependent = False
    for line_no, raw in enumerate(lines, start=1):
        stripped = raw.strip()
        if re.match(r"^#{0,4}\s*五、", stripped):
            in_ch5, in_dependent = True, False
            continue
        if re.match(r"^#{0,4}\s*六、", stripped):
            break
        if not in_ch5:
            continue
        if "从属" in stripped and (stripped.startswith("#") or re.match(r"^[（(]?[一二三四五六七八九十\d]", stripped)):
            in_dependent = True
            continue
        if in_dependent:
            continue
        for match in IMPL_PARAM_UNIT_RE.finditer(raw):
            outcome.warn_items.append(
                {
                    "file": md_path.name,
                    "line": line_no,
                    "token": match.group(0),
                    "content": _safe_text(raw),
                    "hint": "实施参数疑入独权区：独权改「预设周期/预设阈值」，具体数值移实施例或从属保护点",
                }
            )
    return outcome


REVISION_MATRIX_FIELDS = (
    "批注编号",
    "代理意见原文",
    "意见理解",
    "内部判断",
    "对外状态",
    "修改说明",
    "人类可读位置",
    "机器锚点",
    "是否影响 MVP/计算",
    "联动检查",
    "最终状态",
)
REVISION_MATRIX_FIELD_ALIASES = {"MVP/计算影响": "是否影响 MVP/计算"}
IMPLEMENTED_REPLY_STATUSES = {"已落实", "部分落实"}
EXEMPT_REPLY_STATUSES = {
    "待补充材料后落实",
    "暂未落实",
}
ALLOWED_REPLY_STATUSES = IMPLEMENTED_REPLY_STATUSES | EXEMPT_REPLY_STATUSES
FINAL_STATUS_BY_REPLY_STATUS = {
    "已落实": "CLOSED",
    "部分落实": "PARTIAL",
    "待补充材料后落实": "OPEN",
    "暂未落实": "OPEN",
}
MVP_IMPACT_VALUES = {"是", "否", "待判断"}
ANCHOR_NAMESPACES = {"STEP", "DECISION", "EQ", "FIG", "KP", "SECTION", "MVP", "FILE"}
WORD_PART_RE = re.compile(r"页眉|页脚|脚注|尾注|文本框|批注气泡|Word\s*XML|XML\s*部件", re.I)
UNCERTAIN_MAPPING_RE = re.compile(r"重排|重编号|改编号|迁移|拆分|合并|移至|移到|编号调整")
ZERO_WIDTH_RE = re.compile(r"[\u200b-\u200f\u202a-\u202e\u2060\ufeff]")
EMPTY_MARKERS = {"", "-", "—", "–", "无", "暂无", "不适用", "n/a", "none"}
# Only prose-like files receive presentation normalisation.  Source code and
# structured data are hash-compared because whitespace and punctuation may be
# semantically meaningful there.
PROSE_TEXT_SUFFIXES = {".md", ".rst", ".txt"}


@dataclass(frozen=True)
class RevisionAnchor:
    namespace: str
    value: str

    @property
    def label(self) -> str:
        return f"{self.namespace}:{self.value}"

    @property
    def is_delete(self) -> bool:
        return self.namespace == "DELETE"


@dataclass
class RevisionMatrixRow:
    comment: str
    status: str
    change: str
    location: str
    anchor_text: str
    mvp_impact: str
    linked_checks: str
    final_status: str


@dataclass(frozen=True)
class AnchorBlock:
    line: int
    text: str
    matched_by: str


@dataclass(frozen=True)
class DiffEvidence:
    anchor: str
    category: str
    similarity: float | None = None
    detail: str | None = None


def _normalise_comment_id(value: str) -> str:
    match = re.fullmatch(r"C\s*0*(\d{1,3})", value.strip(), re.I)
    if not match:
        return value.strip().upper()
    return f"C{int(match.group(1)):02d}"


def _split_markdown_row(line: str) -> list[str] | None:
    stripped = line.strip()
    if not stripped.startswith("|"):
        return None
    stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    cells = re.split(r"(?<!\\)\|", stripped)
    return [cell.replace(r"\|", "|").strip() for cell in cells]


def _is_markdown_divider(cells: Sequence[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells)


def _parse_revision_matrix(path: Path) -> tuple[list[RevisionMatrixRow], list[str]]:
    errors: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        return [], [f"修订矩阵不可读：{exc}"]

    header_index: int | None = None
    headers: list[str] = []
    for index, line in enumerate(lines):
        cells = _split_markdown_row(line)
        if cells and "批注编号" in cells and "机器锚点" in cells:
            header_index = index
            raw_headers = [re.sub(r"[*_`]", "", cell).strip() for cell in cells]
            headers = [REVISION_MATRIX_FIELD_ALIASES.get(cell, cell) for cell in raw_headers]
            break
    if header_index is None:
        return [], ["未找到含“批注编号”和“机器锚点”的修订矩阵表"]

    missing = [field for field in REVISION_MATRIX_FIELDS if field not in headers]
    if missing:
        errors.append("修订矩阵缺少字段：" + "、".join(missing))
    rows: list[RevisionMatrixRow] = []
    for line in lines[header_index + 1 :]:
        if not line.strip():
            if rows:
                break
            continue
        cells = _split_markdown_row(line)
        if cells is None:
            if rows:
                break
            continue
        if _is_markdown_divider(cells):
            continue
        if len(cells) != len(headers):
            errors.append(f"修订矩阵列数不一致：期望 {len(headers)}，实际 {len(cells)}")
            continue
        data = dict(zip(headers, cells))
        comment = _normalise_comment_id(data.get("批注编号", ""))
        if not re.fullmatch(r"C\d{2,3}", comment):
            errors.append(f"非法批注编号：{data.get('批注编号', '')}")
            continue
        rows.append(
            RevisionMatrixRow(
                comment=comment,
                status=data.get("对外状态", "").strip(),
                change=data.get("修改说明", "").strip(),
                location=data.get("人类可读位置", "").strip(),
                anchor_text=data.get("机器锚点", "").strip(),
                mvp_impact=data.get("是否影响 MVP/计算", "").strip(),
                linked_checks=data.get("联动检查", "").strip(),
                final_status=data.get("最终状态", "").strip().upper(),
            )
        )
    if not rows:
        errors.append("修订矩阵没有可解析的批注行")
    return rows, errors


def _parse_attorney_reply(path: Path) -> tuple[dict[str, dict[str, str]], list[str]]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return {}, [f"代理回复不可读：{exc}"]
    heading_re = re.compile(r"^#{2,6}\s*(C\d{1,3})\s*[｜|]", re.M | re.I)
    matches = list(heading_re.finditer(text))
    if not matches:
        return {}, ["代理回复未找到“### C01｜…”固定块"]
    entries: dict[str, dict[str, str]] = {}
    errors: list[str] = []
    field_re = re.compile(
        r"^[ \t]*(?:[-+][ \t]+)?(?:\*\*)?([^*：:\n]+?)(?:\*\*)?[ \t]*[：:][ \t]*(.*?)[ \t]*$",
        re.M,
    )
    for index, match in enumerate(matches):
        comment = _normalise_comment_id(match.group(1))
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[match.end() : end]
        fields = {name.strip(): value.strip() for name, value in field_re.findall(block)}
        if comment in entries:
            errors.append(f"代理回复出现重复编号：{comment}")
        entries[comment] = fields
    return entries, errors


def _is_meaningful(value: str) -> bool:
    cleaned = value.strip().strip("`*_ ").lower()
    return cleaned not in EMPTY_MARKERS


def _is_no_change_exemption(status: str, change: str) -> bool:
    if status in EXEMPT_REPLY_STATUSES:
        return True
    combined = f"{status} {change}"
    return "仅确认事实" in combined and "无需修改" in combined


def _parse_direct_anchor(token: str) -> tuple[RevisionAnchor | None, str | None]:
    match = re.fullmatch(r"(STEP|DECISION|EQ|FIG|KP|SECTION|MVP|FILE):(.+)", token)
    if not match:
        return None, "锚点须使用受支持的大写命名空间"
    namespace, value = match.group(1), match.group(2).strip()
    if namespace == "STEP" and not re.fullmatch(r"S\d{1,4}", value):
        return None, "STEP 编号须形如 S4"
    if namespace == "DECISION" and not re.fullmatch(r"D\d{1,4}", value):
        return None, "DECISION 编号须形如 D3"
    if namespace in {"EQ", "FIG", "KP"} and not re.fullmatch(r"\d{1,4}(?:\.\d+)?", value):
        return None, f"{namespace} 编号须为数字"
    if namespace == "SECTION" and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", value):
        return None, "SECTION 须为编号或 ASCII 稳定 ID"
    if namespace in {"MVP", "FILE"}:
        posix = value.replace("\\", "/")
        parts = posix.split("/")
        if (
            not value
            or posix.startswith("/")
            or re.match(r"^[A-Za-z]:", posix)
            or any(part in {"", ".", ".."} for part in parts)
        ):
            return None, f"{namespace} 须为不越界的相对路径"
    return RevisionAnchor(namespace, value), None


def _parse_anchor_list(raw: str) -> tuple[list[RevisionAnchor], list[dict[str, str]]]:
    value = raw.strip().strip("` ")
    if value.lower() in EMPTY_MARKERS:
        return [], []
    anchors: list[RevisionAnchor] = []
    errors: list[dict[str, str]] = []
    for original in value.split(";"):
        token = original.strip().strip("` ")
        if not token:
            errors.append({"anchor": original, "issue": "分号之间存在空锚点"})
            continue
        if token.startswith("DELETE:"):
            nested = token.removeprefix("DELETE:")
            target, err = _parse_direct_anchor(nested)
            if err or target is None:
                errors.append({"anchor": token, "issue": f"DELETE 目标非法：{err}"})
                continue
            anchors.append(RevisionAnchor("DELETE", target.label))
            continue
        anchor, err = _parse_direct_anchor(token)
        if err or anchor is None:
            errors.append({"anchor": token, "issue": err or "非法锚点"})
            continue
        anchors.append(anchor)
    return anchors, errors


def _delete_target(anchor: RevisionAnchor) -> RevisionAnchor:
    target, err = _parse_direct_anchor(anchor.value)
    if err or target is None:  # guarded by _parse_anchor_list
        raise ValueError(f"invalid DELETE target: {anchor.value}")
    return target


def _normalise_for_search(text: str) -> str:
    return ZERO_WIDTH_RE.sub("", unicodedata.normalize("NFKC", text))


def _strong_anchor_pattern(anchor: RevisionAnchor) -> re.Pattern[str]:
    value = re.escape(anchor.value)
    explicit = (
        rf"(?<![A-Za-z0-9._-]){anchor.namespace}:{value}"
        rf"(?![A-Za-z0-9._-])"
    )
    if anchor.namespace == "STEP":
        pattern = rf"(?:{explicit}|^\s*(?:#{{1,6}}\s*)?(?:[-+*]\s*)?(?:\*\*)?{value}(?=$|[\s、,:：;|）)]))"
    elif anchor.namespace == "DECISION":
        pattern = rf"(?:{explicit}|^\s*(?:#{{1,6}}\s*)?(?:[-+*]\s*)?(?:\*\*)?\|?\s*{value}(?=$|[\s、,:：;|）)]))"
    elif anchor.namespace == "EQ":
        pattern = rf"(?:{explicit}|\\tag\s*\{{\s*{value}\s*\}}|^\s*(?:公式|方程|式)\s*[(\[]?\s*{value}(?![\d.])\s*[)\]]?|^\s*[(]\s*{value}\s*[)]\s*$)"
    elif anchor.namespace == "FIG":
        pattern = rf"(?:{explicit}|^\s*(?:#{{1,6}}\s*)?(?:[-+*]\s*)?(?:\*\*)?(?:附图|图)\s*{value}(?![\d.])|!\[[^\]]*(?:附图|图)\s*{value}(?![\d.]))"
    elif anchor.namespace == "KP":
        pattern = rf"(?:{explicit}|^\s*(?:#{{1,6}}\s*)?(?:[-+*]\s*)?(?:\*\*)?(?:保护点|权利要求)\s*{value}(?![\d.]))"
    else:  # SECTION
        pattern = rf"(?:{explicit}|^\s*#{{1,6}}\s*(?:第\s*)?{value}(?=$|[\s、:：]))"
    return re.compile(pattern, re.M | re.I)


def _fallback_anchor_pattern(anchor: RevisionAnchor) -> re.Pattern[str]:
    value = re.escape(anchor.value)
    if anchor.namespace in {"STEP", "DECISION"}:
        pattern = rf"(?<![A-Za-z0-9._-]){value}(?![A-Za-z0-9._-])"
    elif anchor.namespace == "EQ":
        pattern = rf"(?:公式|方程|式|tag)\D{{0,8}}{value}(?![\d.])"
    elif anchor.namespace == "FIG":
        pattern = rf"(?:附图|图)\s*{value}(?![\d.])"
    elif anchor.namespace == "KP":
        pattern = rf"(?:保护点|权利要求)\s*{value}(?![\d.])"
    else:
        pattern = rf"(?<![A-Za-z0-9.]){value}(?![A-Za-z0-9.])"
    return re.compile(pattern, re.I)


def _block_from_line(lines: Sequence[str], index: int, anchor: RevisionAnchor) -> str:
    current = lines[index]
    if anchor.namespace == "SECTION":
        heading = re.match(r"^(\s*)(#{1,6})\s+", current)
        if heading:
            level = len(heading.group(2))
            end = index + 1
            while end < len(lines):
                next_heading = re.match(r"^\s*(#{1,6})\s+", lines[end])
                if next_heading and len(next_heading.group(1)) <= level:
                    break
                end += 1
            return "\n".join(lines[index:end]).strip()
    if current.lstrip().startswith("|"):
        return current.strip()

    start = index
    if anchor.namespace == "EQ" and re.fullmatch(r"\s*\(\s*\d+(?:\.\d+)?\s*\)\s*", current):
        if index > 0 and lines[index - 1].strip():
            start = index - 1
    end = index + 1
    while end < len(lines):
        candidate = lines[end]
        if not candidate.strip() or re.match(r"^\s*#{1,6}\s+", candidate):
            break
        if re.match(
            r"^\s*(?:[-+*]\s*)?(?:\*\*)?(?:S\d+|D\d+|(?:附图|图)\s*\d+|保护点\s*\d+)",
            _normalise_for_search(candidate),
            re.I,
        ):
            break
        end += 1
    return "\n".join(lines[start:end]).strip()


def _find_anchor_blocks(text: str, anchor: RevisionAnchor) -> list[AnchorBlock]:
    if anchor.namespace not in ANCHOR_NAMESPACES - {"MVP", "FILE"}:
        return []
    lines = text.splitlines()
    normalised_lines = [_normalise_for_search(line) for line in lines]
    strong = _strong_anchor_pattern(anchor)
    indices = [index for index, line in enumerate(normalised_lines) if strong.search(line)]
    matched_by = "strong"
    if not indices:
        fallback = _fallback_anchor_pattern(anchor)
        indices = [index for index, line in enumerate(normalised_lines) if fallback.search(line)]
        matched_by = "fallback"
    return [
        AnchorBlock(index + 1, _block_from_line(lines, index, anchor), matched_by)
        for index in indices
    ]


def _resolve_relative_file(root: Path, value: str) -> Path | None:
    parts = value.replace("\\", "/").split("/")
    if any(part in {"", ".", ".."} for part in parts):
        return None
    root_resolved = root.expanduser().resolve()
    candidate = root_resolved.joinpath(*parts).resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError:
        return None
    return candidate


def _infer_baseline_md(
    revision_md: Path,
    revision_root: Path,
    baseline_root: Path | None,
) -> Path | None:
    """Resolve the baseline Markdown by the revision file's relative path."""
    if baseline_root is None:
        return None
    try:
        relative = revision_md.expanduser().resolve().relative_to(
            revision_root.expanduser().resolve()
        )
    except ValueError:
        return None
    candidate = _resolve_relative_file(baseline_root, relative.as_posix())
    return candidate if candidate and candidate.is_file() else None


def _unsupported_word_location(*values: str) -> bool:
    return bool(WORD_PART_RE.search(" ".join(values)))


def _add_invalid_anchor_items(
    outcome: CheckOutcome,
    *,
    comment: str,
    source: str,
    errors: Sequence[dict[str, str]],
) -> None:
    for error in errors:
        outcome.fail_items.append(
            {
                "comment": comment,
                "source": source,
                "anchor": error.get("anchor", ""),
                "reason": "invalid_anchor",
                "issue": error.get("issue", "非法机器锚点"),
            }
        )


def _warn_fallback_anchor(
    outcome: CheckOutcome,
    *,
    comment: str,
    anchor: RevisionAnchor,
    blocks: Sequence[AnchorBlock],
    source: str,
) -> None:
    fallback_blocks = [block for block in blocks if block.matched_by == "fallback"]
    if not fallback_blocks:
        return
    outcome.warn_items.append(
        {
            "comment": comment,
            "anchor": anchor.label,
            "source": source,
            "reason": "fallback_anchor_match",
            "lines": [block.line for block in fallback_blocks],
            "issue": "锚点仅由宽松回退规则定位；须人工确认其确为代理意见所指对象",
        }
    )


def check_reply_anchors_resolvable(
    attorney_reply: Path | None,
    revision_matrix: Path | None,
    revision_md: Path | None,
    revision_root: Path | None,
    *,
    baseline_md: Path | None = None,
    baseline_root: Path | None = None,
) -> CheckOutcome:
    """C16: validate recorded revision anchors and object existence.

    This check is deliberately structural. Resolving an anchor proves neither
    that the edit is professionally sufficient nor that it answers counsel.
    """
    outcome = CheckOutcome("C16", "reply_anchors_resolvable")
    if revision_matrix is None:
        if attorney_reply is None and baseline_md is None and baseline_root is None:
            outcome.info_items.append({"note": "未提供修订闭环参数，跳过修订锚点门禁"})
        else:
            outcome.fail_items.append(
                {
                    "reason": "missing_input",
                    "issue": "已提供代理回复或基线，但缺少 --revision-matrix",
                }
            )
        return outcome
    required = {
        "attorney_reply": attorney_reply,
        "revision_md": revision_md,
        "revision_root": revision_root,
    }
    missing_inputs = [name for name, value in required.items() if value is None]
    if missing_inputs:
        outcome.fail_items.append(
            {
                "reason": "missing_input",
                "issue": "C16 缺少输入：" + ", ".join(missing_inputs),
            }
        )
        return outcome
    assert attorney_reply is not None and revision_md is not None and revision_root is not None
    for label, path in (
        ("attorney_reply", attorney_reply),
        ("revision_matrix", revision_matrix),
        ("revision_md", revision_md),
    ):
        if not path.is_file():
            outcome.fail_items.append(
                {"reason": "input_not_found", "input": label, "file": str(path)}
            )
    if outcome.fail_items:
        return outcome

    rows, matrix_errors = _parse_revision_matrix(revision_matrix)
    replies, reply_errors = _parse_attorney_reply(attorney_reply)
    for issue in matrix_errors:
        outcome.fail_items.append(
            {"reason": "revision_matrix_invalid", "file": revision_matrix.name, "issue": issue}
        )
    for issue in reply_errors:
        outcome.fail_items.append(
            {"reason": "attorney_reply_invalid", "file": attorney_reply.name, "issue": issue}
        )
    if not rows:
        return outcome

    duplicate_comments = {
        row.comment for row in rows if sum(item.comment == row.comment for item in rows) > 1
    }
    for comment in sorted(duplicate_comments):
        outcome.warn_items.append(
            {"comment": comment, "reason": "duplicate_matrix_row", "issue": "修订矩阵编号重复，定位可能歧义"}
        )
    matrix_comments = {row.comment for row in rows}
    for comment in sorted(set(replies) - matrix_comments):
        outcome.fail_items.append(
            {
                "comment": comment,
                "reason": "matrix_entry_missing",
                "issue": "代理回复有批注块，但修订矩阵无对应记录",
            }
        )

    revision_text = revision_md.read_text(encoding="utf-8")
    effective_baseline_md = (
        baseline_md
        if baseline_md and baseline_md.is_file()
        else _infer_baseline_md(revision_md, revision_root, baseline_root)
    )
    baseline_text = (
        effective_baseline_md.read_text(encoding="utf-8")
        if effective_baseline_md
        else None
    )
    effective_baseline_root = baseline_root or (
        effective_baseline_md.parent if effective_baseline_md else None
    )

    for row in rows:
        matrix_anchors, matrix_anchor_errors = _parse_anchor_list(row.anchor_text)
        _add_invalid_anchor_items(
            outcome,
            comment=row.comment,
            source="revision_matrix",
            errors=matrix_anchor_errors,
        )
        reply_fields = replies.get(row.comment)
        if reply_fields is None:
            outcome.fail_items.append(
                {
                    "comment": row.comment,
                    "reason": "reply_entry_missing",
                    "issue": "修订矩阵有记录，但代理回复无对应固定块",
                }
            )
            reply_anchors: list[RevisionAnchor] = []
            reply_status = ""
        else:
            reply_status = reply_fields.get("处理结果", "").strip()
            reply_anchors, reply_anchor_errors = _parse_anchor_list(
                reply_fields.get("机器锚点", "")
            )
            _add_invalid_anchor_items(
                outcome,
                comment=row.comment,
                source="attorney_reply",
                errors=reply_anchor_errors,
            )
            missing_in_matrix = sorted(
                {anchor.label for anchor in reply_anchors}
                - {anchor.label for anchor in matrix_anchors}
            )
            if missing_in_matrix:
                outcome.fail_items.append(
                    {
                        "comment": row.comment,
                        "reason": "reply_matrix_anchor_mismatch",
                        "anchors": missing_in_matrix,
                        "issue": "代理回复声明的修改位置未全部登记到修订矩阵",
                    }
                )

        exempt = _is_no_change_exemption(row.status, row.change)
        implemented = row.status in IMPLEMENTED_REPLY_STATUSES and not exempt
        unsupported = _unsupported_word_location(
            row.location,
            row.change,
            reply_fields.get("修改位置", "") if reply_fields else "",
        )
        if row.status not in ALLOWED_REPLY_STATUSES:
            outcome.fail_items.append(
                {
                    "comment": row.comment,
                    "reason": "invalid_external_status",
                    "status": row.status,
                    "issue": "对外状态不在修订闭环允许值中",
                }
            )
        expected_final_status = FINAL_STATUS_BY_REPLY_STATUS.get(row.status)
        if row.final_status not in {"CLOSED", "PARTIAL", "OPEN"}:
            outcome.fail_items.append(
                {
                    "comment": row.comment,
                    "reason": "invalid_final_status",
                    "status": row.final_status,
                    "issue": "最终状态只允许 CLOSED/PARTIAL/OPEN",
                }
            )
        elif expected_final_status and row.final_status != expected_final_status:
            outcome.fail_items.append(
                {
                    "comment": row.comment,
                    "reason": "final_status_mismatch",
                    "external_status": row.status,
                    "final_status": row.final_status,
                    "expected": expected_final_status,
                    "issue": "对外状态与最终闭环状态不一致",
                }
            )
        if row.mvp_impact not in MVP_IMPACT_VALUES:
            outcome.fail_items.append(
                {
                    "comment": row.comment,
                    "reason": "invalid_mvp_impact",
                    "value": row.mvp_impact,
                    "issue": "是否影响 MVP/计算只允许 是/否/待判断",
                }
            )
        elif row.mvp_impact == "是":
            has_mvp_anchor = any(
                (_delete_target(anchor) if anchor.is_delete else anchor).namespace == "MVP"
                for anchor in matrix_anchors
            )
            if not has_mvp_anchor:
                outcome.fail_items.append(
                    {
                        "comment": row.comment,
                        "reason": "mvp_anchor_missing",
                        "issue": "MVP/计算影响为“是”时至少登记一个 MVP: 机器锚点",
                    }
                )
            if "MVP" not in row.linked_checks and "计算" not in row.linked_checks:
                outcome.fail_items.append(
                    {
                        "comment": row.comment,
                        "reason": "mvp_linked_check_missing",
                        "issue": "MVP/计算影响为“是”时联动检查须包含 MVP/计算",
                    }
                )
        if exempt and not _is_meaningful(row.change):
            outcome.fail_items.append(
                {
                    "comment": row.comment,
                    "reason": "exemption_reason_missing",
                    "issue": "豁免机器锚点时必须在修改说明中填写客观原因",
                }
            )
        if implemented and not matrix_anchors:
            if unsupported:
                outcome.warn_items.append(
                    {
                        "comment": row.comment,
                        "reason": "unsupported_word_part",
                        "location": row.location,
                        "issue": "目标位于当前 Markdown 门禁不支持的 Word 部件，请人工复核",
                    }
                )
            else:
                outcome.fail_items.append(
                    {
                        "comment": row.comment,
                        "reason": "missing_machine_anchor",
                        "issue": "已落实或部分落实的意见必须登记机器锚点",
                    }
                )
        if reply_fields is not None:
            reply_exempt = _is_no_change_exemption(
                reply_status, reply_fields.get("具体处理", "")
            )
            if reply_status not in ALLOWED_REPLY_STATUSES:
                outcome.fail_items.append(
                    {
                        "comment": row.comment,
                        "source": "attorney_reply",
                        "reason": "invalid_external_status",
                        "status": reply_status,
                        "issue": "代理回复处理结果只允许四种落实状态",
                    }
                )
            elif reply_status != row.status:
                outcome.fail_items.append(
                    {
                        "comment": row.comment,
                        "reason": "reply_matrix_status_mismatch",
                        "reply_status": reply_status,
                        "matrix_status": row.status,
                        "issue": "代理回复处理结果与修订矩阵对外状态不一致",
                    }
                )
            if (
                reply_status in IMPLEMENTED_REPLY_STATUSES
                and not reply_exempt
                and not reply_anchors
                and not matrix_anchors
            ):
                if not unsupported:
                    outcome.fail_items.append(
                        {
                            "comment": row.comment,
                            "reason": "reply_missing_machine_anchor",
                            "issue": "正式代理回复声称已落实，但机器锚点为空",
                        }
                    )
            elif reply_exempt and not _is_meaningful(reply_fields.get("具体处理", "")):
                outcome.fail_items.append(
                    {
                        "comment": row.comment,
                        "reason": "exemption_reason_missing",
                        "source": "attorney_reply",
                        "issue": "正式代理回复豁免锚点时必须说明原因",
                    }
                )

        for anchor in matrix_anchors:
            target = _delete_target(anchor) if anchor.is_delete else anchor
            if target.namespace in {"MVP", "FILE"}:
                revision_file = _resolve_relative_file(revision_root, target.value)
                if revision_file is None:
                    outcome.fail_items.append(
                        {
                            "comment": row.comment,
                            "anchor": anchor.label,
                            "reason": "invalid_anchor",
                            "issue": "文件锚点越出 revision root",
                        }
                    )
                    continue
                if anchor.is_delete:
                    if effective_baseline_root is None:
                        outcome.fail_items.append(
                            {
                                "comment": row.comment,
                                "anchor": anchor.label,
                                "reason": "delete_baseline_missing",
                                "issue": "DELETE 文件锚点必须提供 baseline root",
                            }
                        )
                        continue
                    baseline_file = _resolve_relative_file(effective_baseline_root, target.value)
                    if baseline_file is None or not baseline_file.is_file():
                        outcome.fail_items.append(
                            {
                                "comment": row.comment,
                                "anchor": anchor.label,
                                "reason": "delete_target_missing_in_baseline",
                                "issue": "DELETE 目标在基线目录中不存在",
                            }
                        )
                    if revision_file.exists():
                        outcome.fail_items.append(
                            {
                                "comment": row.comment,
                                "anchor": anchor.label,
                                "reason": "delete_target_still_exists",
                                "issue": "DELETE 目标在修订目录中仍然存在",
                            }
                        )
                elif not revision_file.is_file():
                    outcome.fail_items.append(
                        {
                            "comment": row.comment,
                            "anchor": anchor.label,
                            "reason": "file_not_found",
                            "file": str(revision_file),
                            "issue": "MVP/FILE 锚点指定的修订文件不存在",
                        }
                    )
                continue

            if anchor.is_delete:
                if baseline_text is None:
                    outcome.fail_items.append(
                        {
                            "comment": row.comment,
                            "anchor": anchor.label,
                            "reason": "delete_baseline_missing",
                            "issue": "DELETE 正文锚点必须提供可读 baseline md",
                        }
                    )
                    continue
                baseline_blocks = _find_anchor_blocks(baseline_text, target)
                revision_blocks = _find_anchor_blocks(revision_text, target)
                _warn_fallback_anchor(
                    outcome,
                    comment=row.comment,
                    anchor=anchor,
                    blocks=baseline_blocks,
                    source="baseline",
                )
                _warn_fallback_anchor(
                    outcome,
                    comment=row.comment,
                    anchor=anchor,
                    blocks=revision_blocks,
                    source="revision",
                )
                if not baseline_blocks:
                    outcome.fail_items.append(
                        {
                            "comment": row.comment,
                            "anchor": anchor.label,
                            "reason": "delete_target_missing_in_baseline",
                            "issue": "DELETE 目标在基线稿中不存在",
                        }
                    )
                elif len(baseline_blocks) > 1:
                    outcome.warn_items.append(
                        {
                            "comment": row.comment,
                            "anchor": anchor.label,
                            "reason": "ambiguous_anchor",
                            "matches": len(baseline_blocks),
                            "issue": "DELETE 目标在基线稿中匹配多个对象，请人工确认",
                        }
                    )
                if revision_blocks:
                    outcome.fail_items.append(
                        {
                            "comment": row.comment,
                            "anchor": anchor.label,
                            "reason": "delete_target_still_exists",
                            "matches": len(revision_blocks),
                            "issue": "DELETE 目标在修订稿中仍然存在",
                        }
                    )
                continue

            blocks = _find_anchor_blocks(revision_text, target)
            _warn_fallback_anchor(
                outcome,
                comment=row.comment,
                anchor=anchor,
                blocks=blocks,
                source="revision",
            )
            if not blocks:
                if unsupported:
                    outcome.warn_items.append(
                        {
                            "comment": row.comment,
                            "anchor": anchor.label,
                            "reason": "unsupported_word_part",
                            "issue": "目标可能位于当前工具不支持的 Word 部件，请人工复核",
                        }
                    )
                elif UNCERTAIN_MAPPING_RE.search(f"{row.location} {row.change}"):
                    outcome.warn_items.append(
                        {
                            "comment": row.comment,
                            "anchor": anchor.label,
                            "reason": "mapping_uncertain",
                            "issue": "章节或编号发生重排，无法稳定定位，请人工复核",
                        }
                    )
                else:
                    outcome.fail_items.append(
                        {
                            "comment": row.comment,
                            "anchor": anchor.label,
                            "reason": "anchor_not_found",
                            "issue": "普通正文锚点在修订稿中不存在",
                        }
                    )
            elif len(blocks) > 1:
                outcome.warn_items.append(
                    {
                        "comment": row.comment,
                        "anchor": anchor.label,
                        "reason": "ambiguous_anchor",
                        "matches": len(blocks),
                        "lines": [block.line for block in blocks],
                        "issue": "锚点定位到多个对象，请人工确认",
                    }
                )

    if not outcome.fail_items and not outcome.warn_items:
        outcome.info_items.append(
            {
                "rows": len(rows),
                "note": "机器锚点均可解析；本检查不判断修改是否充分或是否语义解决代理意见",
            }
        )
    return outcome


def normalise_revision_text(text: str) -> str:
    """Normalise presentation-only variation while retaining technical text."""
    text = ZERO_WIDTH_RE.sub("", unicodedata.normalize("NFKC", text))
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text, flags=re.S)
    text = re.sub(r"__(.+?)__", r"\1", text, flags=re.S)
    text = re.sub(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", r"\1", text)
    text = re.sub(r"(?<![\w_])_([^_\n]+?)_(?![\w_])", r"\1", text)
    punctuation = str.maketrans(
        {
            "，": ",", "。": ".", "：": ":", "；": ";", "！": "!",
            "？": "?", "、": ".", "“": '"', "”": '"', "‘": "'", "’": "'",
        }
    )
    normalised_lines: list[str] = []
    for raw in text.split("\n"):
        line = raw.translate(punctuation)
        line = re.sub(r"^\s*#{1,6}\s*", "", line)
        line = re.sub(r"^\s*[-+]\s+", "", line)
        line = re.sub(r"^\s*\(\s*(\d+)\s*\)\s*[.]?\s*", r"\1. ", line)
        line = re.sub(r"^\s*(\d+)\s*[.)]\s*", r"\1. ", line)
        normalised_lines.append(line.strip())
    text = "".join(line for line in normalised_lines if line)
    text = re.sub(r"\s+", "", text)
    return text.strip()


def _text_similarity(before: str, after: str) -> float:
    return difflib.SequenceMatcher(None, before, after, autojunk=False).ratio()


def _compare_normalised_text(
    anchor: str,
    before: str,
    after: str,
    threshold: float,
) -> DiffEvidence:
    normal_before = normalise_revision_text(before)
    normal_after = normalise_revision_text(after)
    if normal_before == normal_after:
        return DiffEvidence(anchor, "same", 1.0)
    similarity = _text_similarity(normal_before, normal_after)
    if similarity >= threshold:
        return DiffEvidence(anchor, "near", similarity)
    return DiffEvidence(anchor, "changed", similarity)


def _read_prose_file(path: Path) -> str | None:
    if path.suffix.lower() not in PROSE_TEXT_SUFFIXES:
        return None
    try:
        return path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError):
        return None


def _compare_file_anchor(
    anchor: RevisionAnchor,
    revision_root: Path,
    baseline_root: Path | None,
    threshold: float,
) -> DiffEvidence:
    target = _delete_target(anchor) if anchor.is_delete else anchor
    revision_file = _resolve_relative_file(revision_root, target.value)
    baseline_file = _resolve_relative_file(baseline_root, target.value) if baseline_root else None
    if revision_file is None or (baseline_root is not None and baseline_file is None):
        return DiffEvidence(anchor.label, "uncertain", detail="文件锚点越出根目录")
    baseline_exists = bool(baseline_file and baseline_file.is_file())
    revision_exists = revision_file.is_file()
    if anchor.is_delete:
        if baseline_exists and not revision_exists:
            return DiffEvidence(anchor.label, "changed", detail="基线存在且修订版已删除")
        return DiffEvidence(anchor.label, "uncertain", detail="DELETE 存在状态不满足")
    if not baseline_exists and revision_exists:
        return DiffEvidence(anchor.label, "changed", detail="修订版新增文件")
    if baseline_exists and not revision_exists:
        return DiffEvidence(anchor.label, "uncertain", detail="非 DELETE 文件锚点在修订版缺失")
    if not baseline_exists and not revision_exists:
        return DiffEvidence(anchor.label, "uncertain", detail="基线与修订版均无该文件")
    assert baseline_file is not None
    before_hash = hashlib.sha256(baseline_file.read_bytes()).hexdigest()
    after_hash = hashlib.sha256(revision_file.read_bytes()).hexdigest()
    if before_hash == after_hash:
        return DiffEvidence(anchor.label, "same", 1.0, "file hash unchanged")
    before_text = _read_prose_file(baseline_file)
    after_text = _read_prose_file(revision_file)
    if before_text is not None and after_text is not None:
        return _compare_normalised_text(anchor.label, before_text, after_text, threshold)
    return DiffEvidence(anchor.label, "changed", detail="file hash changed")


def check_claimed_changes_have_diff(
    revision_matrix: Path | None,
    revision_md: Path | None,
    revision_root: Path | None,
    *,
    baseline_md: Path | None = None,
    baseline_root: Path | None = None,
    similarity_threshold: float = 0.98,
    revision_requested: bool = False,
) -> CheckOutcome:
    """C17: detect structural change for implemented revision-matrix rows.

    PASS means only that a verifiable change exists. It does not establish that
    the change semantically resolves the attorney comment.
    """
    outcome = CheckOutcome("C17", "claimed_changes_have_diff")
    if revision_matrix is None:
        if revision_requested:
            outcome.fail_items.append(
                {
                    "reason": "missing_input",
                    "issue": "已提供修订闭环参数，但缺少 --revision-matrix",
                }
            )
        else:
            outcome.info_items.append({"note": "未提供修订闭环参数，跳过修订 diff 门禁"})
        return outcome
    if revision_md is None or revision_root is None:
        outcome.warn_items.append(
            {"reason": "revision_input_missing", "issue": "缺少 revision md/root，C17 无法定位修订内容"}
        )
        return outcome
    if not 0.0 <= similarity_threshold <= 1.0:
        outcome.warn_items.append(
            {"reason": "invalid_similarity_threshold", "value": similarity_threshold}
        )
        return outcome
    if baseline_md is None and baseline_root is None:
        outcome.warn_items.append(
            {
                "reason": "baseline_missing",
                "issue": "未提供 baseline md/root，C17 跳过实质 diff 判定",
            }
        )
        return outcome
    if not revision_matrix.is_file() or not revision_md.is_file():
        outcome.warn_items.append(
            {"reason": "revision_input_missing", "issue": "修订矩阵或修订 Markdown 不存在"}
        )
        return outcome

    rows, errors = _parse_revision_matrix(revision_matrix)
    if errors:
        outcome.warn_items.extend(
            {"reason": "revision_matrix_invalid", "issue": error} for error in errors
        )
    if not rows:
        return outcome
    revision_text = revision_md.read_text(encoding="utf-8")
    effective_baseline_md = (
        baseline_md
        if baseline_md and baseline_md.is_file()
        else _infer_baseline_md(revision_md, revision_root, baseline_root)
    )
    baseline_text = (
        effective_baseline_md.read_text(encoding="utf-8")
        if effective_baseline_md
        else None
    )
    effective_baseline_root = baseline_root or (
        effective_baseline_md.parent if effective_baseline_md else None
    )

    for row in rows:
        if row.status not in IMPLEMENTED_REPLY_STATUSES or _is_no_change_exemption(
            row.status, row.change
        ):
            continue
        anchors, anchor_errors = _parse_anchor_list(row.anchor_text)
        if anchor_errors or not anchors:
            outcome.warn_items.append(
                {
                    "comment": row.comment,
                    "reason": "no_resolvable_anchor",
                    "issue": "C16 应先解决机器锚点问题，C17 不作 diff 结论",
                }
            )
            continue
        evidence: list[DiffEvidence] = []
        for anchor in anchors:
            target = _delete_target(anchor) if anchor.is_delete else anchor
            if target.namespace in {"MVP", "FILE"}:
                evidence.append(
                    _compare_file_anchor(
                        anchor,
                        revision_root,
                        effective_baseline_root,
                        similarity_threshold,
                    )
                )
                continue
            if baseline_text is None:
                evidence.append(
                    DiffEvidence(anchor.label, "uncertain", detail="缺少 baseline md")
                )
                continue
            baseline_blocks = _find_anchor_blocks(baseline_text, target)
            revision_blocks = _find_anchor_blocks(revision_text, target)
            if any(
                block.matched_by == "fallback"
                for block in [*baseline_blocks, *revision_blocks]
            ):
                evidence.append(
                    DiffEvidence(
                        anchor.label,
                        "uncertain",
                        detail="锚点至少一侧仅由 fallback 规则定位",
                    )
                )
                continue
            if anchor.is_delete:
                if len(baseline_blocks) == 1 and not revision_blocks:
                    evidence.append(
                        DiffEvidence(anchor.label, "changed", detail="基线存在且修订稿已删除")
                    )
                else:
                    evidence.append(
                        DiffEvidence(anchor.label, "uncertain", detail="DELETE 映射不唯一或删除未成立")
                    )
                continue
            if not baseline_blocks and len(revision_blocks) == 1:
                if UNCERTAIN_MAPPING_RE.search(f"{row.location} {row.change}"):
                    evidence.append(
                        DiffEvidence(anchor.label, "uncertain", detail="编号重排后基线无同名锚点")
                    )
                else:
                    evidence.append(
                        DiffEvidence(anchor.label, "changed", detail="修订稿新增结构化锚点")
                    )
            elif len(baseline_blocks) == 1 and len(revision_blocks) == 1:
                evidence.append(
                    _compare_normalised_text(
                        anchor.label,
                        baseline_blocks[0].text,
                        revision_blocks[0].text,
                        similarity_threshold,
                    )
                )
            else:
                evidence.append(
                    DiffEvidence(
                        anchor.label,
                        "uncertain",
                        detail=(
                            f"baseline matches={len(baseline_blocks)}, "
                            f"revision matches={len(revision_blocks)}"
                        ),
                    )
                )

        changed = [item for item in evidence if item.category == "changed"]
        uncertain = [item for item in evidence if item.category == "uncertain"]
        near = [item for item in evidence if item.category == "near"]
        same = [item for item in evidence if item.category == "same"]
        if same:
            item: dict[str, Any] = {
                "comment": row.comment,
                "reason": "no_detectable_diff",
                "similarity": 1.0,
                "anchors": [entry.anchor for entry in same],
                "issue": "至少一个声称修改的锚点在规范化后完全相同",
            }
            if changed:
                item["changed_anchors"] = [entry.anchor for entry in changed]
            if near:
                item["near_anchors"] = [entry.anchor for entry in near]
            if uncertain:
                item["uncertain_anchors"] = [entry.anchor for entry in uncertain]
            outcome.fail_items.append(item)
        elif uncertain:
            item = {
                "comment": row.comment,
                "reason": "mapping_uncertain",
                "anchors": [entry.anchor for entry in uncertain],
                "details": [entry.detail for entry in uncertain],
                "issue": "无法稳定识别基线与修订区块的对应关系，请人工复核",
            }
            if changed:
                item["changed_anchors"] = [entry.anchor for entry in changed]
            outcome.warn_items.append(item)
        elif near:
            similarity = max(item.similarity or 0.0 for item in near)
            item = {
                "comment": row.comment,
                "reason": "high_similarity",
                "anchors": [entry.anchor for entry in near],
                "similarity": round(similarity, 6),
                "threshold": similarity_threshold,
                "issue": "至少一个对应区块仅发生极小变化，疑似形式性调整，请人工确认",
            }
            if changed:
                item["changed_anchors"] = [entry.anchor for entry in changed]
            outcome.warn_items.append(item)
        elif changed:
            outcome.info_items.append(
                {
                    "comment": row.comment,
                    "reason": "change_detected",
                    "anchors": [item.anchor for item in changed],
                    "note": "仅确认检测到结构变化，不表示语义上已解决代理意见",
                }
            )
        else:
            outcome.fail_items.append(
                {
                    "comment": row.comment,
                    "reason": "no_detectable_diff",
                    "similarity": 1.0,
                    "anchors": [item.anchor for item in evidence],
                    "issue": "声称已修改，但规范化后的对应内容或文件完全相同",
                }
            )
    return outcome


def _max_status(outcomes: Sequence[CheckOutcome]) -> str:
    if any(outcome.fail_items for outcome in outcomes):
        return "FAIL"
    if any(outcome.warn_items for outcome in outcomes):
        return "WARN"
    return "PASS"


def _exit_code(status: str) -> int:
    return {"PASS": 0, "WARN": 1, "FAIL": 2}[status]


def _json_entries(outcomes: Sequence[CheckOutcome], attr: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for outcome in outcomes:
        items = getattr(outcome, attr)
        if items:
            entries.append({"check": outcome.check, "items": items})
    return entries


def _check_summary(outcome: CheckOutcome) -> str:
    if outcome.fail_items:
        return f"{outcome.check} FAIL({len(outcome.fail_items)})"
    if outcome.warn_items:
        return f"{outcome.check} WARN({len(outcome.warn_items)})"
    return f"{outcome.check} PASS"


def _format_pending(warns: list[dict[str, Any]], user_fill: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for warn in warns:
        check = warn.get("check", "?")
        for item in warn.get("items", []):
            lines.append(f"- {check}: {_safe_text(item)}")
    if user_fill:
        lines.append("- 用户自填清单：")
        lines.extend(f"  - {_safe_text(item)}" for item in user_fill)
    return "\n".join(lines)


def append_delivery_record(
    *,
    case_dir: Path,
    status: str,
    outcomes: Sequence[CheckOutcome],
    warns: list[dict[str, Any]],
    user_fill: list[dict[str, Any]],
    md_path: Path,
    docx_path: Path,
    version: str,
) -> Path | None:
    try:
        import delivery_check_log
    except Exception as exc:  # noqa: BLE001
        print(f"[record] WARN: failed to import delivery_check_log: {exc}", file=sys.stderr)
        return None

    summary = (
        f"delivery_gate {status}; "
        + "; ".join(_check_summary(outcome) for outcome in outcomes)
        + f"; version={version}"
    )
    pending = _format_pending(warns, user_fill)
    if not pending:
        pending = "—"
    checks = "\n".join(f"- {_check_summary(outcome)}" for outcome in outcomes)
    if status == "FAIL":
        next_action = "修复 FAIL 项后重新运行 delivery_gate。"
    elif status == "WARN":
        next_action = "补齐 WARN 项和用户自填项后交代理人复核。"
    else:
        next_action = "可进入代理人审稿复核。"

    with contextlib.redirect_stdout(io.StringIO()):
        code = delivery_check_log.main(
            [
                "--case-dir",
                str(case_dir),
                "--status",
                status,
                "--summary",
                summary,
                "--pending",
                pending,
                "--artifacts",
                f"{md_path.name},{docx_path.name}",
                "--checks",
                checks,
                "--next",
                next_action,
            ]
        )
    if code != 0:
        print(f"[record] WARN: delivery_check_log exited with {code}", file=sys.stderr)
        return None
    return case_dir / "交底书交付检查记录.md"


def run_gate(args: argparse.Namespace) -> tuple[int, dict[str, Any], list[str]]:
    root = Path(__file__).resolve().parents[1]
    case_dir = args.case_dir.expanduser().resolve()
    md_path = args.md.expanduser().resolve()
    docx_path = args.docx.expanduser().resolve()
    manifest_path = args.manifest.expanduser().resolve() if args.manifest else None
    numeric_spec = args.numeric_spec.expanduser().resolve() if args.numeric_spec else None
    t0_dir = (args.t0_dir or case_dir).expanduser().resolve()
    skipped = set(args.skip or [])
    logs: list[str] = []
    outcomes: list[CheckOutcome] = []
    user_fill: list[dict[str, Any]] = []

    def add(outcome: CheckOutcome) -> None:
        outcomes.append(outcome)
        logs.append(outcome.log_line())

    def skip(check_id: str, name: str) -> bool:
        if check_id in skipped:
            logs.append(f"[{check_id}] SKIP: {name}")
            return True
        return False

    if not skip("C1", "docx_math_qa"):
        add(run_docx_math_qa(docx_path, manifest_path))
    if not skip("C2", "placeholder_scan"):
        outcome, fill_items = scan_placeholders(
            md_path,
            docx_path,
            whitelist_file=args.whitelist_file,
        )
        user_fill.extend(fill_items)
        add(outcome)
    if not skip("C3", "count_closure"):
        add(check_count_closure(md_path))
    if not skip("C4", "field_label_integrity"):
        add(check_field_label_integrity(md_path, docx_path))
    if not skip("C5", "formula_paragraph"):
        add(check_formula_paragraph(docx_path))
    if not skip("C6", "filename_convention"):
        add(check_filename_convention(md_path, docx_path))
    if not skip("C7", "confirmation_artifacts"):
        add(
            check_confirmation_artifacts(
                case_dir,
                entry=args.entry,
                t0_dir=t0_dir,
                preview_skipped=args.preview_skipped,
            )
        )
    if not skip("C8", "numeric_reproduce"):
        add(run_numeric_reproduce(numeric_spec))
    if not skip("C9", "version_report"):
        add(version_report(root))
    if not skip("C10", "defensive_phrasing"):
        add(check_defensive_phrasing(md_path))
    if not skip("C11", "fuzzy_qualifier"):
        add(check_fuzzy_qualifier(md_path))
    contract_path = args.evidence_contract or discover_evidence_contract(case_dir)
    if not skip("C12", "evidence_contract"):
        add(check_evidence_contract(contract_path))
    if not skip("C13", "decision_refs"):
        add(check_decision_refs(md_path, contract_path))
    if not skip("C14", "attorney_reply_consistency"):
        add(check_attorney_reply(args.comments_json, args.attorney_reply))
    if not skip("C15", "impl_params_in_claims"):
        add(check_impl_params_in_claims(md_path))
    revision_requested = any(
        (
            args.attorney_reply,
            args.revision_matrix,
            args.revision_root,
            args.baseline_md,
            args.baseline_root,
        )
    )
    c16_outcome: CheckOutcome | None = None
    if not skip("C16", "reply_anchors_resolvable"):
        c16_outcome = check_reply_anchors_resolvable(
            args.attorney_reply,
            args.revision_matrix,
            md_path,
            args.revision_root or md_path.parent,
            baseline_md=args.baseline_md,
            baseline_root=args.baseline_root,
        )
        add(c16_outcome)
    if not skip("C17", "claimed_changes_have_diff"):
        if c16_outcome is not None and c16_outcome.fail_items:
            c17_outcome = CheckOutcome("C17", "claimed_changes_have_diff")
            c17_outcome.warn_items.append(
                {
                    "reason": "not_evaluated",
                    "issue": "C16 未通过，C17 未作 diff 判定，不能记为 PASS",
                }
            )
            add(c17_outcome)
        else:
            add(
                check_claimed_changes_have_diff(
                    args.revision_matrix,
                    md_path,
                    args.revision_root or md_path.parent,
                    baseline_md=args.baseline_md,
                    baseline_root=args.baseline_root,
                    similarity_threshold=args.revision_similarity_threshold,
                    revision_requested=revision_requested,
                )
            )

    status = _max_status(outcomes)
    fails = _json_entries(outcomes, "fail_items")
    warns = _json_entries(outcomes, "warn_items")
    info = _json_entries(outcomes, "info_items")
    version = "unknown"
    for entry in info:
        if entry["check"] == "C9" and entry["items"]:
            version = str(entry["items"][0].get("version", "unknown"))
            break

    record_path = None
    if not args.no_record:
        record_path = append_delivery_record(
            case_dir=case_dir,
            status=status,
            outcomes=outcomes,
            warns=warns,
            user_fill=user_fill,
            md_path=md_path,
            docx_path=docx_path,
            version=version,
        )

    payload = {
        "status": status,
        "fails": fails,
        "warns": warns,
        "info": info,
        "user_fill": user_fill,
        "skipped": sorted(skipped),
        "version": version,
        "md": str(md_path),
        "docx": str(docx_path),
    }
    if record_path is not None:
        payload["record"] = str(record_path)
    return _exit_code(status), payload, logs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Unified delivery gate for disclosure handoff")
    parser.add_argument("--case-dir", type=Path, required=True, help="案件目录")
    parser.add_argument("--md", type=Path, required=True, help="交付 Markdown 文件")
    parser.add_argument("--docx", type=Path, required=True, help="交付 DOCX 文件")
    parser.add_argument("--manifest", type=Path, help="formula manifest YAML")
    parser.add_argument("--numeric-spec", type=Path, help="numeric_check JSON/YAML")
    parser.add_argument("--entry", choices=("direct", "t0"), default="direct")
    parser.add_argument("--t0-dir", type=Path, help="T0 边界卡/主题卡目录")
    parser.add_argument("--preview-skipped", action="store_true", help="用户明确跳过确认点4")
    parser.add_argument("--whitelist-file", type=Path, help="额外占位符白名单正则文件")
    parser.add_argument(
        "--evidence-contract", type=Path,
        help="技术证据合同 YAML（缺省时在案件目录自动发现 *技术证据合同*.yaml）",
    )
    parser.add_argument("--comments-json", type=Path, help="docx_comment_extract 输出的批注 JSON（C14 用）")
    parser.add_argument("--attorney-reply", type=Path, help="代理意见逐条回复 md（C14/C16 用）")
    parser.add_argument("--revision-matrix", type=Path, help="批注处置矩阵 Markdown（C16/C17）")
    parser.add_argument("--revision-root", type=Path, help="修订版 MVP/FILE 相对路径根目录；默认 --md 所在目录")
    parser.add_argument("--baseline-md", type=Path, help="修订前基线 Markdown（C16 DELETE / C17）")
    parser.add_argument("--baseline-root", type=Path, help="基线版 MVP/FILE 相对路径根目录")
    parser.add_argument(
        "--revision-similarity-threshold",
        "--similarity-threshold",
        dest="revision_similarity_threshold",
        type=float,
        default=0.98,
        help="C17 高相似度 WARN 阈值，默认 0.98",
    )
    parser.add_argument("--skip", action="append", choices=CHECK_IDS, default=[])
    parser.add_argument("--no-record", action="store_true", help="不写交付检查记录")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    except Exception:
        pass

    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        code, payload, logs = run_gate(args)
    except Exception as exc:  # noqa: BLE001
        payload = {
            "status": "FAIL",
            "fails": [{"check": "INTERNAL", "items": [{"error": str(exc)}]}],
            "warns": [],
            "user_fill": [],
            "skipped": sorted(args.skip or []),
            "version": "unknown",
            "md": str(args.md),
            "docx": str(args.docx),
        }
        print(f"[INTERNAL] FAIL: {exc}")
        print("DELIVERY_GATE_JSON " + json.dumps(payload, ensure_ascii=True))
        return 2

    for line in logs:
        print(line)
    print("DELIVERY_GATE_JSON " + json.dumps(payload, ensure_ascii=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
