# -*- coding: utf-8 -*-
"""math_render 回归测试（需 matplotlib，缺失时跳过）。

产物一律写入 pytest 的 ``tmp_path``，不写回仓库目录，避免每次运行改写受版本控制的文件。
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

_SOFTMAX_BLOCK = r"P(z_i) = \frac{\exp(z_i / T)}{\sum_j \exp(z_j / T)}"
_INLINE_COMPLEX = r"\sum_{j=1}^{n} w_j \cdot \exp(z_j / T)"
# 交底书常见、matplotlib 需归一化的简写
_INLINE_GE_LE = r"a_{cpu,j} \le 0"
_INLINE_PAREN = r"T_r"
_BLOCK_LOGIC = (
    r"t - t_{last} \ge T_r \quad \land \quad |\sigma_{now} - \sigma_{last}| \ge \Delta s"
)
_SCORE_BLOCK = (
    r"Score(\mathbf{d},\mathbf{p}) = w_{cpu}\cdot d_{cpu}\cdot p_{cpu} + w_{mem}\cdot "
    r"\min\left(1,\frac{p_{mem}}{\max(1,d_{mem})}\right) + w_{io}\cdot(1-p_{io\_busy})\cdot d_{io} "
    r"- \lambda\cdot n_{inflight}\n\tag{1}"
)


PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def test_block_and_inline(tmp_path: Path) -> None:
    pytest.importorskip("matplotlib")
    from math_render import render_markdown_math

    md = (
        f"温度参数 $T$ 下，加权 logits 为 ${_INLINE_COMPLEX}$，"
        f"约束 ${_INLINE_GE_LE}$ 与 \\({_INLINE_PAREN}\\)。\n\n"
        f"$$\n{_SOFTMAX_BLOCK}\n$$\n\n"
        f"$$\n{_BLOCK_LOGIC}\n$$\n\n"
        f"$$\n{_SCORE_BLOCK}\n$$\n"
    )
    new_md, ok, _failed = render_markdown_math(
        md,
        out_md_path=tmp_path / "out.md",
        assets_rel="figs",
    )

    pngs = sorted((tmp_path / "figs").glob("*.png"))
    # 4 个行内公式 + 前 2 个块级公式必须渲染成功。
    assert ok >= 6
    assert len(pngs) == ok
    for png in pngs:
        assert png.read_bytes().startswith(PNG_MAGIC), png.name
        assert f"figs/{png.name}" in new_md


def test_fallback_on_bad_latex(tmp_path: Path) -> None:
    pytest.importorskip("matplotlib")
    from math_render import render_markdown_math

    source = "$$\\notacommand{x}$$\n"
    new_md, ok, failed = render_markdown_math(
        source,
        out_md_path=tmp_path / "bad.md",
        assets_rel="figs",
    )

    assert (ok, failed) == (0, 1)
    assert new_md == source  # 渲染失败时保留原文，不生成图片引用
    assert not list((tmp_path / "figs").glob("*.png"))


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
        test_block_and_inline(Path(a))
        test_fallback_on_bad_latex(Path(b))
    print("ok")
