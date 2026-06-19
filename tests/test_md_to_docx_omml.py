"""md_to_docx should emit editable Word equations, not formula images/code text."""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from md_to_docx import convert_md_to_docx  # noqa: E402


def _document_xml(doc, tmp_path: Path) -> str:
    out = tmp_path / "out.docx"
    doc.save(out)
    with zipfile.ZipFile(out) as zf:
        return zf.read("word/document.xml").decode("utf-8")


def test_code_wrapped_math_symbol_becomes_omml(tmp_path: Path) -> None:
    doc = convert_md_to_docx(
        "符号 `B_{s,t}^{tot}` 表示时段 t 内场站 s 的总储能量。",
        base_dir=tmp_path,
    )
    xml = _document_xml(doc, tmp_path)

    assert "<m:oMath" in xml
    assert "Consolas" not in xml
    assert "B_{s,t}^{tot}" not in xml


def test_block_math_with_legacy_png_comment_skips_formula_image(tmp_path: Path) -> None:
    math_dir = tmp_path / "math_figures"
    math_dir.mkdir()
    (math_dir / "eq_001.png").write_bytes(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
        b"\x1f\x15\xc4\x89\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    md = (
        "\\[\n"
        "B_{s,t}^{tot} = B_{s,t}^{ch} + B_{s,t}^{dis} \\tag{1}\n"
        "\\]\n"
        "<!-- ![公式](math_figures/eq_001.png) -->\n"
    )

    doc = convert_md_to_docx(md, base_dir=tmp_path)
    xml = _document_xml(doc, tmp_path)

    assert "<m:oMath" in xml
    assert "word/media" not in xml
    assert "eq_001.png" not in xml
