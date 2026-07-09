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
import io
import json
import re
import sys
import zipfile
from pathlib import Path
from typing import Any, Iterable, Sequence
from xml.etree import ElementTree as ET

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
}

CHECK_IDS = ("C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10")

PLACEHOLDER_RE = re.compile(r"待填|待补充|待确认|待核|TODO|TBD|\[待填写\]|【待填写】", re.I)
USER_FILL_LINE_RE = re.compile(
    r"^\s*[-*]?\s*\*{0,2}(姓名|电话|邮箱|技术联系人|发明人|申请人)"
)
USER_FILL_MARKER_RE = re.compile(r"（用户自填）|\[待填写\]|待填写")
FIELD_LABEL_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+){2,}\b")
FILENAME_RE = re.compile(r"^.+_\d{14}\.(md|docx)$", re.I)
NUMERIC_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")
DEFENSIVE_PHRASE_RE = re.compile(r"不在于|不作为|不强制|不以|不宜|显著降低")


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
