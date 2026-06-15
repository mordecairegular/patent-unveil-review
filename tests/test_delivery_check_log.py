from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import delivery_check_log  # noqa: E402


def test_delivery_check_log_creates_case_log(tmp_path: Path) -> None:
    code = delivery_check_log.main(
        [
            "--case-dir",
            str(tmp_path),
            "--status",
            "WARN",
            "--summary",
            "查新等级 B，区别特征已回写。",
            "--pending",
            "补充正式附图",
            "--artifacts",
            "一种测试方法及系统_20260607120000.md,一种测试方法及系统_20260607120000.docx",
            "--checks",
            "章节完整；技术效果待实验验证。",
            "--next",
            "交代理人复核权利要求布局。",
        ]
    )

    assert code == 0
    log_path = tmp_path / "交底书交付检查记录.md"
    assert log_path.exists()

    text = log_path.read_text(encoding="utf-8")
    assert "# 交底书交付检查记录" in text
    assert "**状态**：WARN" in text
    assert "一种测试方法及系统_20260607120000.md" in text
    assert "补充正式附图" in text
    assert "交代理人复核权利要求布局。" in text


def test_delivery_check_log_rejects_missing_case_dir(tmp_path: Path) -> None:
    missing_dir = tmp_path / "missing"
    code = delivery_check_log.main(
        [
            "--case-dir",
            str(missing_dir),
            "--status",
            "FAIL",
        ]
    )

    assert code == 2
    assert not (missing_dir / "交底书交付检查记录.md").exists()
