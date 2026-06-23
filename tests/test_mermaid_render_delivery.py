"""mermaid_render should not allow failed diagrams into final DOCX."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import mermaid_render  # noqa: E402


def test_main_stops_docx_generation_when_mermaid_render_fails(monkeypatch, tmp_path: Path) -> None:
    src = tmp_path / "draft.md"
    out = tmp_path / "一种测试方法及系统_20260619000000.md"
    src.write_text("```mermaid\nflowchart TB\nA --> B\n```\n", encoding="utf-8")

    monkeypatch.setattr(mermaid_render, "_find_mmdc_invocation", lambda: (["mmdc"], False))

    def fail_render(*args, **kwargs):
        raise RuntimeError("mmdc failed for test")

    monkeypatch.setattr(mermaid_render, "_render_one_mermaid", fail_render)
    called = {"docx": False}

    def fake_try_write_docx(*args, **kwargs):
        called["docx"] = True
        return True

    monkeypatch.setattr(mermaid_render, "try_write_docx", fake_try_write_docx)

    code = mermaid_render.main(["-i", str(src), "-o", str(out)])

    assert code == 1
    assert not called["docx"]
    assert out.exists()
    assert "```mermaid" in out.read_text(encoding="utf-8")


def test_main_passes_rendered_mermaid_count_to_docx_qa(monkeypatch, tmp_path: Path) -> None:
    src = tmp_path / "draft.md"
    out = tmp_path / "一种测试方法及系统_20260619000001.md"
    src.write_text("```mermaid\nflowchart TB\nA --> B\n```\n", encoding="utf-8")

    monkeypatch.setattr(mermaid_render, "_find_mmdc_invocation", lambda: (["mmdc"], False))

    def ok_render(_source, png_path: Path, *args, **kwargs):
        png_path.parent.mkdir(parents=True, exist_ok=True)
        png_path.write_bytes(
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
            b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
            b"\x1f\x15\xc4\x89\x00\x00\x00\x00IEND\xaeB`\x82"
        )

    monkeypatch.setattr(mermaid_render, "_render_one_mermaid", ok_render)
    captured = {}

    def fake_try_write_docx(_out_md, _docx_out, *, min_media_count=0):
        captured["min_media_count"] = min_media_count
        return True

    monkeypatch.setattr(mermaid_render, "try_write_docx", fake_try_write_docx)

    code = mermaid_render.main(["-i", str(src), "-o", str(out)])

    assert code == 0
    assert captured["min_media_count"] == 1
    assert "![图示 1](mermaid_figures/fig_001.png)" in out.read_text(encoding="utf-8")


def test_existing_hidden_mermaid_comment_is_normalized_to_visible_image(monkeypatch, tmp_path: Path) -> None:
    src = tmp_path / "draft.md"
    out = tmp_path / "一种测试方法及系统_20260619000002.md"
    src.write_text(
        "```mermaid\nflowchart TB\nA --> B\n```\n<!-- ![图示 1](mermaid_figures/fig_001.png) -->\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(mermaid_render, "_find_mmdc_invocation", lambda: (["mmdc"], False))

    def fail_if_called(*args, **kwargs):
        raise AssertionError("existing rendered figure should not be re-rendered")

    monkeypatch.setattr(mermaid_render, "_render_one_mermaid", fail_if_called)
    monkeypatch.setattr(mermaid_render, "try_write_docx", lambda *args, **kwargs: True)

    code = mermaid_render.main(["-i", str(src), "-o", str(out)])

    text = out.read_text(encoding="utf-8")
    assert code == 0
    assert "![图示 1](mermaid_figures/fig_001.png)" in text
    assert "<!-- ![图示 1]" not in text
