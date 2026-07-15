from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import delivery_gate  # noqa: E402


CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>
"""


def _paragraph(text: str) -> str:
    return f"<w:p><w:r><w:t>{escape(text)}</w:t></w:r></w:p>"


def _red_paragraph(text: str) -> str:
    return (
        '<w:p><w:r><w:rPr><w:color w:val="FF0000"/></w:rPr>'
        f"<w:t>{escape(text)}</w:t></w:r></w:p>"
    )


def _write_docx(path: Path, body_fragments: list[str]) -> Path:
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">'
        "<w:body>"
        + "".join(body_fragments)
        + "</w:body></w:document>"
    )
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("[Content_Types].xml", CONTENT_TYPES)
        zf.writestr("word/document.xml", document_xml)
    return path


def _write_clean_case(case_dir: Path, stem: str = "一种测试方法_20260709120000") -> tuple[Path, Path]:
    case_dir.mkdir(parents=True, exist_ok=True)
    md = case_dir / f"{stem}.md"
    docx = case_dir / f"{stem}.docx"
    md.write_text("正文完整，无占位符。\n", encoding="utf-8")
    _write_docx(docx, [_paragraph("正文完整，无占位符。")])
    prior = case_dir / "prior_art_search"
    prior.mkdir()
    (prior / "prior_art_dossier.md").write_text("确认点 3：签核完成。\n", encoding="utf-8")
    (case_dir / "预览确认记录_20260709.md").write_text("确认点 4：已确认。\n", encoding="utf-8")
    return md, docx


def _delivery_json(stdout: str) -> dict:
    line = [ln for ln in stdout.splitlines() if ln.startswith("DELIVERY_GATE_JSON ")][-1]
    return json.loads(line.removeprefix("DELIVERY_GATE_JSON "))


def test_placeholder_scan_whitelist_and_ruogan_scope(tmp_path: Path) -> None:
    md = tmp_path / "draft.md"
    md.write_text(
        "\n".join(
            [
                "正文中的若干模块不触发。",
                "- **姓名**：[待填写]",
                "| 项 | 数量 |",
                "| --- | --- |",
                "| 设备 | 若干 |",
                "方案待补充。",
                "证据状态：待核（provenance-only: PSS 摘要待复核）。",
            ]
        ),
        encoding="utf-8",
    )
    docx = _write_docx(tmp_path / "draft.docx", [_paragraph("电话：待填写")])

    outcome, user_fill = delivery_gate.scan_placeholders(md, docx)

    assert outcome.status == "WARN"
    tokens = [item.get("token") for item in outcome.warn_items]
    assert "若干" in tokens
    assert "待补充" in tokens
    assert any(item.get("kind") == "provenance_only_pending" for item in outcome.warn_items)
    assert len(user_fill) == 2
    assert all("待填写" in item["content"] for item in user_fill)


def test_count_closure_pass_and_mismatch(tmp_path: Path) -> None:
    md = tmp_path / "counts.md"
    md.write_text(
        "\n".join(
            [
                "| 项 | A | B | 说明 |",
                "| --- | --- | --- | --- |",
                "| x | 1 | 2.5 | alpha |",
                "| y | 2 | 3.5 | beta |",
                "| 合计 | 3 | 6.0 | 跳过 |",
                "",
                "| 项 | A |",
                "| --- | --- |",
                "| x | 1 |",
                "| y | 2 |",
                "| 总计 | 4 |",
            ]
        ),
        encoding="utf-8",
    )

    outcome = delivery_gate.check_count_closure(md)

    assert outcome.status == "WARN"
    assert len(outcome.warn_items) == 1
    assert outcome.warn_items[0]["column"] == "A"
    assert outcome.warn_items[0]["actual"] == 3
    assert outcome.warn_items[0]["expected"] == 4


def test_field_label_integrity_pass_and_transformed_fail(tmp_path: Path) -> None:
    md = tmp_path / "field.md"
    md.write_text("字段 long_sparse_direct 必须原样保留。\n", encoding="utf-8")
    ok_docx = _write_docx(tmp_path / "ok.docx", [_paragraph("字段 long_sparse_direct 原样保留。")])

    ok = delivery_gate.check_field_label_integrity(md, ok_docx)

    assert ok.fail_items == []

    transformed_math = """
    <w:p><m:oMath>
      <m:sSub>
        <m:e>
          <m:sSub>
            <m:e><m:r><m:t>long</m:t></m:r></m:e>
            <m:sub><m:r><m:t>sparse</m:t></m:r></m:sub>
          </m:sSub>
        </m:e>
        <m:sub><m:r><m:t>direct</m:t></m:r></m:sub>
      </m:sSub>
    </m:oMath></w:p>
    """
    bad_docx = _write_docx(tmp_path / "bad.docx", [transformed_math])

    bad = delivery_gate.check_field_label_integrity(md, bad_docx)

    assert bad.status == "FAIL"
    assert bad.fail_items[0]["label"] == "long_sparse_direct"
    assert bad.fail_items[0]["reason"] == "transformed"
    assert bad.warn_items[0]["reason"] == "suspected_field_label_formula"


def test_formula_paragraph_red_text_fail_and_multi_math_warn(tmp_path: Path) -> None:
    multi_math = """
    <w:p><m:oMathPara>
      <m:oMath><m:r><m:t>a</m:t></m:r></m:oMath>
      <m:oMath><m:r><m:t>b</m:t></m:r></m:oMath>
    </m:oMathPara></w:p>
    """
    docx = _write_docx(tmp_path / "formula.docx", [_red_paragraph("render failed"), multi_math])

    outcome = delivery_gate.check_formula_paragraph(docx)

    assert outcome.status == "FAIL"
    assert outcome.fail_items[0]["reason"] == "red_text_residue"
    assert outcome.warn_items[0]["math_count"] == 2


def test_filename_convention_warns_on_bad_name(tmp_path: Path) -> None:
    md = tmp_path / "draft.md"
    docx = tmp_path / "draft_20260709120000.docx"

    outcome = delivery_gate.check_filename_convention(md, docx)

    assert outcome.status == "WARN"
    assert outcome.warn_items[0]["md_matches"] is False
    assert outcome.warn_items[0]["same_stem"] is False


def test_fuzzy_qualifier_scan_flags_unquantified_not_quantified(tmp_path: Path) -> None:
    md = tmp_path / "body.md"
    md.write_text(
        "\n".join(
            [
                "若特征甲和特征乙近似同步下降且曲线无明显阶梯，判定为均匀衰减类。",
                "两者损失率差值不超过 3 个百分点时判定为同步下降。",
                "对于证据不足的情形，输出人工复核提示。",
            ]
        ),
        encoding="utf-8",
    )

    outcome = delivery_gate.check_fuzzy_qualifier(md)

    assert outcome.status == "WARN"
    flagged_lines = {item["line"] for item in outcome.warn_items}
    assert 1 in flagged_lines  # 近似同步 + 明显阶梯
    assert 3 in flagged_lines  # 证据不足
    assert 2 not in flagged_lines  # quantified criterion must not trip the scan
    line1_tokens = {item["token"] for item in outcome.warn_items if item["line"] == 1}
    assert line1_tokens == {"近似同步", "明显阶梯"}


def test_defensive_phrasing_scan_flags_negation_not_affirmative(tmp_path: Path) -> None:
    md = tmp_path / "body.md"
    md.write_text(
        "\n".join(
            [
                "本发明不在于风速预测模型。",
                "本发明可兼容幂律与对数律，区别在于按敏感度调整阈值。",
                "误差显著降低。",
            ]
        ),
        encoding="utf-8",
    )

    outcome = delivery_gate.check_defensive_phrasing(md)

    assert outcome.status == "WARN"
    flagged_lines = {item["line"] for item in outcome.warn_items}
    assert 1 in flagged_lines  # 不在于
    assert 3 in flagged_lines  # 显著降低
    assert 2 not in flagged_lines  # affirmative "区别在于" must not trip the scan


def test_confirmation_artifacts_preview_skipped_allows_checkpoint4(tmp_path: Path) -> None:
    case_dir = tmp_path / "case"
    prior = case_dir / "prior_art_search"
    prior.mkdir(parents=True)
    (prior / "prior_art_dossier.md").write_text("确认点 3：签核完成。", encoding="utf-8")

    missing = delivery_gate.check_confirmation_artifacts(
        case_dir,
        entry="direct",
        t0_dir=case_dir,
        preview_skipped=False,
    )
    skipped = delivery_gate.check_confirmation_artifacts(
        case_dir,
        entry="direct",
        t0_dir=case_dir,
        preview_skipped=True,
    )

    assert missing.status == "WARN"
    assert any(item["checkpoint"] == 4 for item in missing.warn_items)
    assert skipped.status == "PASS"
    assert skipped.info_items[0]["message"] == "预览未经用户确认"


def test_cli_pass_warn_fail_exit_codes_and_json(capsys, tmp_path: Path) -> None:
    pass_case = tmp_path / "pass_case"
    md, docx = _write_clean_case(pass_case)

    code = delivery_gate.main(
        ["--case-dir", str(pass_case), "--md", str(md), "--docx", str(docx), "--no-record"]
    )
    payload = _delivery_json(capsys.readouterr().out)

    assert code == 0
    assert payload["status"] == "PASS"
    assert payload["fails"] == []

    warn_case = tmp_path / "warn_case"
    warn_md, warn_docx = _write_clean_case(warn_case, stem="badname")
    (warn_case / "预览确认记录_20260709.md").unlink()

    code = delivery_gate.main(
        [
            "--case-dir",
            str(warn_case),
            "--md",
            str(warn_md),
            "--docx",
            str(warn_docx),
            "--no-record",
        ]
    )
    payload = _delivery_json(capsys.readouterr().out)

    assert code == 1
    assert payload["status"] == "WARN"
    assert any(item["check"] == "C7" for item in payload["warns"])

    fail_case = tmp_path / "fail_case"
    fail_md, fail_docx = _write_clean_case(fail_case)
    _write_docx(fail_docx, [_red_paragraph("render failed")])

    code = delivery_gate.main(
        [
            "--case-dir",
            str(fail_case),
            "--md",
            str(fail_md),
            "--docx",
            str(fail_docx),
            "--no-record",
        ]
    )
    payload = _delivery_json(capsys.readouterr().out)

    assert code == 2
    assert payload["status"] == "FAIL"
    assert any(item["check"] == "C5" for item in payload["fails"])
