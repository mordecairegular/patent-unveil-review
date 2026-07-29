from __future__ import annotations

import json
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

import delivery_gate  # noqa: E402


MATRIX_HEADER = (
    "| 批注编号 | 代理意见原文 | 意见理解 | 内部判断 | 对外状态 | 修改说明 | "
    "人类可读位置 | 机器锚点 | 是否影响 MVP/计算 | 联动检查 | 最终状态 |"
)
MATRIX_DIVIDER = "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"


def _write_matrix(path: Path, rows: list[dict[str, str]]) -> Path:
    body = [MATRIX_HEADER, MATRIX_DIVIDER]
    for row in rows:
        status = row.get("status", "已落实")
        default_final = {
            "已落实": "CLOSED",
            "部分落实": "PARTIAL",
            "待补充材料后落实": "OPEN",
            "暂未落实": "OPEN",
        }.get(status, "CLOSED")
        cells = [
            row.get("id", ""),
            row.get("opinion", "原意见"),
            row.get("understanding", "意见理解"),
            row.get("internal", "采纳"),
            status,
            row.get("change", "已修改"),
            row.get("location", "第三章"),
            row.get("anchors", ""),
            row.get("mvp", "否"),
            row.get("linked", "正文"),
            row.get("final", default_final),
        ]
        body.append("| " + " | ".join(cells) + " |")
    path.write_text("\n".join(body) + "\n", encoding="utf-8")
    return path


def _write_reply(path: Path, rows: list[dict[str, str]]) -> Path:
    blocks: list[str] = []
    for row in rows:
        blocks.extend(
            [
                f"### {row['id']}｜测试意见",
                "**代理意见**：原意见",
                "**意见理解**：意见理解",
                f"**处理结果**：{row.get('reply_status', row.get('status', '已落实'))}",
                f"**具体处理**：{row.get('change', '已修改')}",
                f"**修改位置**：{row.get('location', '第三章')}",
                f"**机器锚点**：{row.get('reply_anchors', row.get('anchors', ''))}",
                "**联动影响**：正文",
                f"**尚待确认**：{row.get('pending', '无')}",
                "",
            ]
        )
    path.write_text("\n".join(blocks), encoding="utf-8")
    return path


def test_c16_resolves_all_namespaces_and_semicolon_lists(tmp_path: Path) -> None:
    revision = tmp_path / "revision.md"
    revision.write_text(
        "\n".join(
            [
                "## 3.2 技术方案",
                "S4，计算候选结果。",
                "| D3 | AND | 输出通过 |",
                r"E = A + B \tag{2}",
                "图2 系统框图",
                "保护点3：使用所述候选结果。",
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "model.py").write_text("print('changed')\n", encoding="utf-8")
    (tmp_path / "notes.md").write_text("changed\n", encoding="utf-8")
    anchors = (
        "STEP:S4; DECISION:D3; EQ:2; FIG:2; KP:3; SECTION:3.2; "
        "MVP:tools/model.py; FILE:notes.md"
    )
    rows = [{"id": "C01", "anchors": anchors}]
    matrix = _write_matrix(tmp_path / "matrix.md", rows)
    reply = _write_reply(tmp_path / "reply.md", rows)

    outcome = delivery_gate.check_reply_anchors_resolvable(
        reply, matrix, revision, tmp_path
    )

    assert outcome.status == "PASS", outcome.fail_items
    assert outcome.fail_items == []
    assert outcome.warn_items == []


def test_c16_fails_missing_invalid_nonexistent_and_false_delete(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.md"
    baseline.write_text("S4，原步骤。\n保护点3：仍需保留。\n", encoding="utf-8")
    revision = tmp_path / "revision.md"
    revision.write_text("S4，修订步骤。\n保护点3：仍需保留。\n", encoding="utf-8")
    rows = [
        {"id": "C01", "anchors": ""},
        {"id": "C02", "anchors": "STEP:s4"},
        {"id": "C03", "anchors": "STEP:S9"},
        {"id": "C04", "anchors": "FILE:missing.txt"},
        {"id": "C05", "anchors": "DELETE:KP:9"},
        {"id": "C06", "anchors": "DELETE:KP:3"},
    ]
    matrix = _write_matrix(tmp_path / "matrix.md", rows)
    reply = _write_reply(tmp_path / "reply.md", rows)

    outcome = delivery_gate.check_reply_anchors_resolvable(
        reply,
        matrix,
        revision,
        tmp_path,
        baseline_md=baseline,
        baseline_root=tmp_path,
    )

    reasons = {item["reason"] for item in outcome.fail_items}
    assert "missing_machine_anchor" in reasons
    assert "invalid_anchor" in reasons
    assert "anchor_not_found" in reasons
    assert "file_not_found" in reasons
    assert "delete_target_missing_in_baseline" in reasons
    assert "delete_target_still_exists" in reasons


def test_c16_exempt_statuses_need_reasons(tmp_path: Path) -> None:
    revision = tmp_path / "revision.md"
    revision.write_text("正文\n", encoding="utf-8")
    rows = [
        {"id": "C01", "status": "待补充材料后落实", "change": "等待实验数据", "anchors": ""},
        {"id": "C02", "status": "暂未落实", "change": "方案待代理人确认", "anchors": ""},
        {"id": "C03", "status": "已落实", "change": "仅确认事实且无需修改文稿", "anchors": ""},
        {"id": "C04", "status": "暂未落实", "change": "", "location": "", "anchors": ""},
    ]
    matrix = _write_matrix(tmp_path / "matrix.md", rows)
    reply = _write_reply(tmp_path / "reply.md", rows)

    outcome = delivery_gate.check_reply_anchors_resolvable(
        reply, matrix, revision, tmp_path
    )

    missing_reason = [
        item for item in outcome.fail_items if item["reason"] == "exemption_reason_missing"
    ]
    assert {item["comment"] for item in missing_reason} == {"C04"}
    assert not any(
        item.get("comment") in {"C01", "C02", "C03"}
        and item["reason"] == "missing_machine_anchor"
        for item in outcome.fail_items
    )


def test_c16_reply_matrix_anchor_mismatch_fails_and_ambiguity_warns(tmp_path: Path) -> None:
    revision = tmp_path / "revision.md"
    revision.write_text("S4，第一处。\n\nS4，第二处。\n图2 系统框图。\n", encoding="utf-8")
    rows = [
        {"id": "C01", "anchors": "STEP:S4", "reply_anchors": "STEP:S4; FIG:2"},
        {"id": "C02", "anchors": "", "location": "页眉中的版本文字"},
    ]
    matrix = _write_matrix(tmp_path / "matrix.md", rows)
    reply = _write_reply(tmp_path / "reply.md", rows)

    outcome = delivery_gate.check_reply_anchors_resolvable(
        reply, matrix, revision, tmp_path
    )

    assert any(item["reason"] == "reply_matrix_anchor_mismatch" for item in outcome.fail_items)
    assert any(item["reason"] == "ambiguous_anchor" for item in outcome.warn_items)
    assert any(item["reason"] == "unsupported_word_part" for item in outcome.warn_items)


def test_c16_allows_external_reply_to_hide_matrix_backed_anchors(tmp_path: Path) -> None:
    revision = tmp_path / "revision.md"
    revision.write_text("S4，已修订步骤。\n", encoding="utf-8")
    rows = [{"id": "C01", "anchors": "STEP:S4", "reply_anchors": ""}]
    matrix = _write_matrix(tmp_path / "matrix.md", rows)
    reply = _write_reply(tmp_path / "reply.md", rows)

    outcome = delivery_gate.check_reply_anchors_resolvable(
        reply, matrix, revision, tmp_path
    )

    assert outcome.status == "PASS", outcome.fail_items


def test_c16_requires_matrix_when_revision_inputs_are_present(tmp_path: Path) -> None:
    revision = tmp_path / "revision.md"
    revision.write_text("S4，已修订步骤。\n", encoding="utf-8")
    reply = _write_reply(
        tmp_path / "reply.md", [{"id": "C01", "anchors": "STEP:S4"}]
    )

    outcome = delivery_gate.check_reply_anchors_resolvable(
        reply, None, revision, tmp_path
    )

    assert outcome.status == "FAIL"
    assert outcome.fail_items[0]["reason"] == "missing_input"


def test_c16_rejects_reply_status_drift_and_invalid_final_status(tmp_path: Path) -> None:
    revision = tmp_path / "revision.md"
    revision.write_text("S4，已修订步骤。\n", encoding="utf-8")
    rows = [
        {
            "id": "C01",
            "status": "已落实",
            "reply_status": "部分落实",
            "anchors": "STEP:S4",
            "final": "OPEN",
        }
    ]
    matrix = _write_matrix(tmp_path / "matrix.md", rows)
    reply = _write_reply(tmp_path / "reply.md", rows)

    outcome = delivery_gate.check_reply_anchors_resolvable(
        reply, matrix, revision, tmp_path
    )

    reasons = {item["reason"] for item in outcome.fail_items}
    assert "reply_matrix_status_mismatch" in reasons
    assert "final_status_mismatch" in reasons


def test_c16_requires_mvp_anchor_and_linked_check_when_impact_is_yes(
    tmp_path: Path,
) -> None:
    revision = tmp_path / "revision.md"
    revision.write_text("S4，已修订步骤。\n", encoding="utf-8")
    rows = [{"id": "C01", "anchors": "STEP:S4", "mvp": "是", "linked": "正文"}]
    matrix = _write_matrix(tmp_path / "matrix.md", rows)
    reply = _write_reply(tmp_path / "reply.md", rows)

    outcome = delivery_gate.check_reply_anchors_resolvable(
        reply, matrix, revision, tmp_path
    )

    reasons = {item["reason"] for item in outcome.fail_items}
    assert {"mvp_anchor_missing", "mvp_linked_check_missing"} <= reasons


def test_c16_does_not_prefix_match_equation_numbers(tmp_path: Path) -> None:
    revision = tmp_path / "revision.md"
    revision.write_text("公式20给出最终结果。\n公式2.1给出中间结果。\n", encoding="utf-8")
    rows = [{"id": "C01", "anchors": "EQ:2"}]
    matrix = _write_matrix(tmp_path / "matrix.md", rows)
    reply = _write_reply(tmp_path / "reply.md", rows)

    outcome = delivery_gate.check_reply_anchors_resolvable(
        reply, matrix, revision, tmp_path
    )

    assert any(item["reason"] == "anchor_not_found" for item in outcome.fail_items)


def test_anchor_resolver_rejects_explicit_hierarchical_prefix_matches() -> None:
    cases = [
        ("EQ", "2", "2.1"),
        ("FIG", "2", "2.1"),
        ("KP", "1", "1.2"),
        ("SECTION", "5", "5.2"),
        ("STEP", "S4", "S4.2"),
        ("DECISION", "D3", "D3.1"),
    ]
    for namespace, short, longer in cases:
        anchor = delivery_gate.RevisionAnchor(namespace, short)
        assert delivery_gate._find_anchor_blocks(
            f"{namespace}:{longer} 这是另一个层级对象。",
            anchor,
        ) == []


def test_anchor_resolver_rejects_prose_hierarchical_prefix_matches() -> None:
    cases = [
        ("EQ", "2", "公式2.1给出另一公式。"),
        ("FIG", "2", "图2.1示出局部结构。"),
        ("KP", "1", "保护点1.2是从属层级。"),
        ("SECTION", "5", "## 5.2 另一小节"),
        ("STEP", "S4", "S4.2，执行子步骤。"),
        ("DECISION", "D3", "| D3.1 | AND | 子判定 |"),
    ]
    for namespace, short, text in cases:
        anchor = delivery_gate.RevisionAnchor(namespace, short)
        assert delivery_gate._find_anchor_blocks(text, anchor) == []


def test_c16_fallback_match_warns_instead_of_clean_pass(tmp_path: Path) -> None:
    revision = tmp_path / "revision.md"
    revision.write_text("正文中提到步骤 S4 的处理，但没有稳定标题。\n", encoding="utf-8")
    rows = [{"id": "C01", "anchors": "STEP:S4"}]
    matrix = _write_matrix(tmp_path / "matrix.md", rows)
    reply = _write_reply(tmp_path / "reply.md", rows)

    outcome = delivery_gate.check_reply_anchors_resolvable(
        reply, matrix, revision, tmp_path
    )

    assert outcome.status == "WARN"
    assert any(
        item["reason"] == "fallback_anchor_match" for item in outcome.warn_items
    )


def test_c17_fallback_match_is_uncertain_not_pass(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.md"
    revision = tmp_path / "revision.md"
    baseline.write_text("正文中提到步骤 S4 的旧处理。\n", encoding="utf-8")
    revision.write_text("正文中提到步骤 S4 的新处理。\n", encoding="utf-8")
    matrix = _write_matrix(
        tmp_path / "matrix.md", [{"id": "C01", "anchors": "STEP:S4"}]
    )

    outcome = delivery_gate.check_claimed_changes_have_diff(
        matrix,
        revision,
        tmp_path,
        baseline_md=baseline,
        baseline_root=tmp_path,
    )

    assert outcome.status == "WARN"
    assert outcome.warn_items[0]["reason"] == "mapping_uncertain"
    assert "fallback" in outcome.warn_items[0]["details"][0]


def test_c17_without_baseline_warns_instead_of_failing(tmp_path: Path) -> None:
    revision = tmp_path / "revision.md"
    revision.write_text("S4，修订步骤。\n", encoding="utf-8")
    matrix = _write_matrix(tmp_path / "matrix.md", [{"id": "C01", "anchors": "STEP:S4"}])

    outcome = delivery_gate.check_claimed_changes_have_diff(
        matrix, revision, tmp_path
    )

    assert outcome.status == "WARN"
    assert outcome.warn_items[0]["reason"] == "baseline_missing"
    assert outcome.fail_items == []


def test_c17_accepts_explicit_baseline_with_real_timestamped_names(tmp_path: Path) -> None:
    baseline_root = tmp_path / "baseline"
    revision_root = tmp_path / "revision"
    baseline_root.mkdir()
    revision_root.mkdir()
    baseline = baseline_root / "技术交底书_20260726190113_codex.md"
    revision = revision_root / "技术交底书_20260729101530_codex.md"
    baseline.write_text("S4，按固定阈值输出单一结果。\n", encoding="utf-8")
    revision.write_text("S4，融合多源数据并输出候选集。\n", encoding="utf-8")
    matrix = _write_matrix(
        tmp_path / "matrix.md", [{"id": "C01", "anchors": "STEP:S4"}]
    )

    outcome = delivery_gate.check_claimed_changes_have_diff(
        matrix,
        revision,
        revision_root,
        baseline_md=baseline,
        baseline_root=baseline_root,
    )

    assert outcome.status == "PASS"
    assert outcome.info_items[0]["reason"] == "change_detected"


def test_c17_normalization_equivalent_content_fails(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.md"
    baseline.write_text("S4，计算 **阈值**\u200b A。\n", encoding="utf-8")
    revision = tmp_path / "revision.md"
    revision.write_text("S４,  计算阈值 A.\n", encoding="utf-8")
    matrix = _write_matrix(tmp_path / "matrix.md", [{"id": "C01", "anchors": "STEP:S4"}])

    outcome = delivery_gate.check_claimed_changes_have_diff(
        matrix,
        revision,
        tmp_path,
        baseline_md=baseline,
        baseline_root=tmp_path,
    )

    assert outcome.status == "FAIL"
    assert outcome.fail_items[0]["reason"] == "no_detectable_diff"
    assert outcome.fail_items[0]["similarity"] == 1.0


def test_c17_near_change_warns_and_threshold_is_configurable(tmp_path: Path) -> None:
    common = "候选结果" * 80
    baseline = tmp_path / "baseline.md"
    baseline.write_text(f"S4，{common}。\n", encoding="utf-8")
    revision = tmp_path / "revision.md"
    revision.write_text(f"S4；{common}。\n", encoding="utf-8")
    matrix = _write_matrix(tmp_path / "matrix.md", [{"id": "C01", "anchors": "STEP:S4"}])

    default_outcome = delivery_gate.check_claimed_changes_have_diff(
        matrix, revision, tmp_path, baseline_md=baseline, baseline_root=tmp_path
    )
    strict_outcome = delivery_gate.check_claimed_changes_have_diff(
        matrix,
        revision,
        tmp_path,
        baseline_md=baseline,
        baseline_root=tmp_path,
        similarity_threshold=0.9999,
    )

    assert default_outcome.status == "WARN"
    assert default_outcome.warn_items[0]["reason"] == "high_similarity"
    assert strict_outcome.status == "PASS"


def test_c17_clear_text_change_passes(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.md"
    baseline.write_text("S4，按固定阈值输出单一结果。\n", encoding="utf-8")
    revision = tmp_path / "revision.md"
    revision.write_text("S4，融合三路传感数据并在冲突时输出候选集与置信度。\n", encoding="utf-8")
    matrix = _write_matrix(tmp_path / "matrix.md", [{"id": "C01", "anchors": "STEP:S4"}])

    outcome = delivery_gate.check_claimed_changes_have_diff(
        matrix, revision, tmp_path, baseline_md=baseline, baseline_root=tmp_path
    )

    assert outcome.status == "PASS"
    assert outcome.info_items[0]["reason"] == "change_detected"


def test_c17_does_not_hide_unchanged_anchor_behind_changed_anchor(
    tmp_path: Path,
) -> None:
    baseline = tmp_path / "baseline.md"
    baseline.write_text(
        "S4，按固定阈值输出单一结果。\n\n图2 系统框图。\n",
        encoding="utf-8",
    )
    revision = tmp_path / "revision.md"
    revision.write_text(
        "S4，融合三路数据并输出置信度。\n\n图2 系统框图。\n",
        encoding="utf-8",
    )
    matrix = _write_matrix(
        tmp_path / "matrix.md",
        [{"id": "C01", "anchors": "STEP:S4; FIG:2"}],
    )

    outcome = delivery_gate.check_claimed_changes_have_diff(
        matrix, revision, tmp_path, baseline_md=baseline, baseline_root=tmp_path
    )

    assert outcome.status == "FAIL"
    assert outcome.fail_items[0]["anchors"] == ["FIG:2"]
    assert outcome.fail_items[0]["changed_anchors"] == ["STEP:S4"]


def test_c17_does_not_normalise_source_code_whitespace(tmp_path: Path) -> None:
    baseline_root = tmp_path / "baseline_root"
    revision_root = tmp_path / "revision_root"
    baseline_root.mkdir()
    revision_root.mkdir()
    baseline_md = baseline_root / "draft.md"
    revision_md = revision_root / "draft.md"
    baseline_md.write_text("正文\n", encoding="utf-8")
    revision_md.write_text("正文\n", encoding="utf-8")
    (baseline_root / "model.py").write_text(
        "if ready:\n    run()\n", encoding="utf-8"
    )
    (revision_root / "model.py").write_text(
        "if ready:\n        run()\n", encoding="utf-8"
    )
    matrix = _write_matrix(
        tmp_path / "matrix.md",
        [
            {
                "id": "C01",
                "anchors": "MVP:model.py",
                "mvp": "是",
                "linked": "MVP/计算",
            }
        ],
    )

    outcome = delivery_gate.check_claimed_changes_have_diff(
        matrix,
        revision_md,
        revision_root,
        baseline_md=baseline_md,
        baseline_root=baseline_root,
    )

    assert outcome.status == "PASS"
    assert outcome.info_items[0]["reason"] == "change_detected"


def test_c17_renumbered_anchor_mapping_warns(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.md"
    baseline.write_text("S4，原步骤。\n", encoding="utf-8")
    revision = tmp_path / "revision.md"
    revision.write_text("S5，修订后的步骤。\n", encoding="utf-8")
    matrix = _write_matrix(
        tmp_path / "matrix.md",
        [{"id": "C01", "anchors": "STEP:S5", "change": "步骤整体重编号后修改"}],
    )

    outcome = delivery_gate.check_claimed_changes_have_diff(
        matrix, revision, tmp_path, baseline_md=baseline, baseline_root=tmp_path
    )

    assert outcome.status == "WARN"
    assert outcome.warn_items[0]["reason"] == "mapping_uncertain"


def test_c17_file_hash_text_comparison_and_delete_semantics(tmp_path: Path) -> None:
    baseline_root = tmp_path / "baseline_root"
    revision_root = tmp_path / "revision_root"
    baseline_root.mkdir()
    revision_root.mkdir()
    baseline_md = baseline_root / "draft.md"
    revision_md = revision_root / "draft.md"
    baseline_md.write_text("正文\n", encoding="utf-8")
    revision_md.write_text("正文\n", encoding="utf-8")
    (baseline_root / "model.txt").write_text("same\n", encoding="utf-8")
    (revision_root / "model.txt").write_text("same\n", encoding="utf-8")
    (baseline_root / "obsolete.txt").write_text("remove me\n", encoding="utf-8")
    rows = [
        {"id": "C01", "anchors": "FILE:model.txt"},
        {"id": "C02", "anchors": "DELETE:FILE:obsolete.txt"},
    ]
    matrix = _write_matrix(tmp_path / "matrix.md", rows)

    same = delivery_gate.check_claimed_changes_have_diff(
        matrix,
        revision_md,
        revision_root,
        baseline_md=baseline_md,
        baseline_root=baseline_root,
    )
    (revision_root / "model.txt").write_text("materially changed\n", encoding="utf-8")
    changed = delivery_gate.check_claimed_changes_have_diff(
        matrix,
        revision_md,
        revision_root,
        baseline_md=baseline_md,
        baseline_root=baseline_root,
    )

    assert any(item["comment"] == "C01" for item in same.fail_items)
    assert any(item["comment"] == "C02" for item in same.info_items)
    assert changed.status == "PASS"
    assert {item["comment"] for item in changed.info_items} == {"C01", "C02"}


def test_cli_adds_c16_c17_to_json_and_total_status(capsys, tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.md"
    baseline.write_text("S4，原步骤。\n", encoding="utf-8")
    revision = tmp_path / "revision.md"
    revision.write_text("S4，融合三路数据并输出置信度。\n", encoding="utf-8")
    rows = [{"id": "C01", "anchors": "STEP:S4"}]
    matrix = _write_matrix(tmp_path / "matrix.md", rows)
    reply = _write_reply(tmp_path / "reply.md", rows)
    argv = [
        "--case-dir",
        str(tmp_path),
        "--md",
        str(revision),
        "--docx",
        str(tmp_path / "unused.docx"),
        "--attorney-reply",
        str(reply),
        "--revision-matrix",
        str(matrix),
        "--revision-root",
        str(tmp_path),
        "--baseline-md",
        str(baseline),
        "--baseline-root",
        str(tmp_path),
        "--no-record",
    ]
    for check_id in delivery_gate.CHECK_IDS[:-2]:
        argv.extend(["--skip", check_id])

    code = delivery_gate.main(argv)
    output = capsys.readouterr().out
    line = [item for item in output.splitlines() if item.startswith("DELIVERY_GATE_JSON ")][-1]
    payload = json.loads(line.removeprefix("DELIVERY_GATE_JSON "))

    assert code == 0
    assert payload["status"] == "PASS"
    assert {entry["check"] for entry in payload["info"]} == {"C16", "C17"}
