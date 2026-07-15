"""Regression tests for delivery_gate C12–C15 (two-case attorney-review retro).

All fixtures are desensitized generic examples (aggregate-measurement →
unit-diagnosis scenarios); no real case names, clients, or paths.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

TOOLS_DIR = Path(__file__).resolve().parent.parent / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import delivery_gate  # noqa: E402

yaml = pytest.importorskip("yaml")


def _base_contract() -> dict:
    return {
        "meta": {
            "case": "DEMO",
            "version": 1,
            "granularity_scale": [
                {"rank": 1, "level": "系统级"},
                {"rank": 2, "level": "聚合组级"},
                {"rank": 3, "level": "单体级"},
            ],
        },
        "baselines": [
            {
                "id": "BL1",
                "kind": "historical_clean",
                "source": "试运行期历史正常数据",
                "purpose": "当前观测对比基准",
                "update_condition": "处置后复测合格时更新",
                "fallback": "同类健康统计",
            }
        ],
        "decisions": [
            {"id": "D1", "logic": "AND", "condition": "差值≤同步阈值 且 无阶梯", "output": "均匀衰减类"},
        ],
        "steps": [
            {
                "id": "S1",
                "name": "采集聚合级量测",
                "claim_class": "independent_core",
                "inputs": [{"name": "聚合量测", "source": "raw", "observation_level": "聚合组级"}],
                "observation_rank": 2,
                "output_rank": 2,
                "validity_check": "完整率筛选",
                "processing": "按预设周期采集",
                "thresholds": [{"name": "完整率下限", "value": "示例 95%", "source": "示例值，待现场标定"}],
                "outputs": ["有效量测序列"],
                "consumers": ["S2"],
                "degraded_branch": "完整率不足时输出数据不足标记",
            },
            {
                "id": "S2",
                "name": "对比基线生成候选",
                "claim_class": "independent_core",
                "inputs": [
                    {"name": "有效量测序列", "source": "derived:S1", "observation_level": "聚合组级"},
                    {"name": "洁净基线", "source": "baseline:BL1", "observation_level": "单体级"},
                ],
                "observation_rank": 2,
                "output_rank": 2,
                "validity_check": "换算到同一参考工况",
                "processing": "按 D1 判定并输出候选集",
                "thresholds": [],
                "outputs": ["候选对象及置信度"],
                "consumers": ["terminal"],
                "degraded_branch": "证据冲突时输出待复核",
            },
        ],
    }


def _write_contract(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "技术证据合同_DEMO.yaml"
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


def test_contract_valid_passes(tmp_path: Path) -> None:
    outcome = delivery_gate.check_evidence_contract(_write_contract(tmp_path, _base_contract()))

    assert outcome.fail_items == []
    assert outcome.warn_items == []


def test_contract_claim_beyond_observation_rank_fails(tmp_path: Path) -> None:
    # 负例：聚合级测量（rank 2）却声称单体级唯一定位（rank 3）
    data = _base_contract()
    data["steps"][1]["output_rank"] = 3

    outcome = delivery_gate.check_evidence_contract(_write_contract(tmp_path, data))

    assert any("超过观测精度" in item["issue"] for item in outcome.fail_items)


def test_contract_missing_degraded_branch_and_threshold_source_fail(tmp_path: Path) -> None:
    data = _base_contract()
    data["steps"][1]["degraded_branch"] = ""  # 负例：证据冲突时没有输出分支
    data["steps"][0]["thresholds"] = [{"name": "同步阈值", "value": "3 个百分点", "source": ""}]  # 负例：阈值无来源

    outcome = delivery_gate.check_evidence_contract(_write_contract(tmp_path, data))

    issues = [item["issue"] for item in outcome.fail_items]
    assert any("degraded_branch" in text for text in issues)
    assert any("阈值" in text and "来源" in text for text in issues)


def test_contract_dangling_refs_fail_and_chain_break_warns(tmp_path: Path) -> None:
    data = _base_contract()
    data["steps"][1]["inputs"][1]["source"] = "baseline:BL9"  # 不存在的基线
    data["steps"][1]["inputs"][0]["source"] = "raw"  # S2 不再引用 derived:S1 → 链断裂
    data["steps"][0]["consumers"] = ["S2", "S9"]  # 不存在的下游

    outcome = delivery_gate.check_evidence_contract(_write_contract(tmp_path, data))

    issues = [item["issue"] for item in outcome.fail_items]
    assert any("BL9" in text for text in issues)
    assert any("S9" in text for text in issues)
    assert any("疑似步骤链断裂" in item["issue"] for item in outcome.warn_items)


def test_contract_invalid_claim_class_fails(tmp_path: Path) -> None:
    data = _base_contract()
    data["steps"][0]["claim_class"] = "core"  # 非法枚举

    outcome = delivery_gate.check_evidence_contract(_write_contract(tmp_path, data))

    assert any("claim_class 非法" in item["issue"] for item in outcome.fail_items)


def test_decision_refs_unknown_and_unreferenced_warn(tmp_path: Path) -> None:
    contract = _write_contract(tmp_path, _base_contract())
    md = tmp_path / "body.md"
    # 负例：正文引用 D9（决策表没有）；决策表 D1 未被正文引用
    md.write_text("S3 按 D9 判定是否降级。", encoding="utf-8")

    outcome = delivery_gate.check_decision_refs(md, contract)

    issues = [item["issue"] for item in outcome.warn_items]
    assert any("D9" in text and "不存在" in text for text in issues)
    assert any("D1" in text and "未被正文引用" in text for text in issues)


def test_attorney_reply_missing_entry_fails_then_full_passes(tmp_path: Path) -> None:
    comments = {
        "top_level_count": 3,
        "comments": [
            {"seq": "C01", "is_reply": False},
            {"seq": "C02", "is_reply": False},
            {"seq": "C03", "is_reply": False},
            {"seq": "C01-R1", "is_reply": True},
        ],
    }
    cj = tmp_path / "comments.json"
    cj.write_text(json.dumps(comments, ensure_ascii=False), encoding="utf-8")
    reply = tmp_path / "reply.md"
    # 负例：3 条意见只回复 2 条
    reply.write_text("### C01｜关于术语\n…\n### C02｜关于阈值\n…\n", encoding="utf-8")

    outcome = delivery_gate.check_attorney_reply(cj, reply)
    assert any("缺少" in item["issue"] and "C03" in item["issue"] for item in outcome.fail_items)

    reply.write_text(
        "| C01 | 主题 | 采纳 |\n| C02 | 主题 | 采纳 |\n### C01｜…\n### C02｜…\n### C03｜…\n",
        encoding="utf-8",
    )
    outcome = delivery_gate.check_attorney_reply(cj, reply)
    assert outcome.fail_items == []


def test_impl_params_flagged_in_independent_region_only(tmp_path: Path) -> None:
    md = tmp_path / "body.md"
    md.write_text(
        "\n".join(
            [
                "## 五、本发明的技术关键点和欲保护点是什么？",
                "S1，每 2 小时采集一次聚合级量测数据；",  # 负例：采样周期入独权区
                "S2，按照预设周期进行有效性筛选；",  # 正例：上位表述不受罚
                "（三）从属保护点",
                "（1）所述预设周期为 1 小时至 4 小时。",  # 从属区允许具体值
                "## 六、其它",
                "实施例中采集周期取 2 小时。",  # 第六章不扫描
            ]
        ),
        encoding="utf-8",
    )

    outcome = delivery_gate.check_impl_params_in_claims(md)

    assert outcome.status == "WARN"
    flagged_lines = {item["line"] for item in outcome.warn_items}
    assert flagged_lines == {2}
