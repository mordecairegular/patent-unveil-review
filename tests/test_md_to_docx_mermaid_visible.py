"""Visible mermaid image references should suppress mermaid source in DOCX."""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

from docx import Document
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import md_to_docx  # noqa: E402
import qa_docx_math  # noqa: E402


def test_visible_mermaid_image_ref_embeds_png_without_source(tmp_path: Path) -> None:
    figures = tmp_path / "mermaid_figures"
    figures.mkdir()
    (figures / "fig_001.png").write_bytes(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
        b"\x1f\x15\xc4\x89\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    md = (
        "```mermaid\n"
        "flowchart LR\n"
        "A --> B\n"
        "```\n"
        "![图示 1](mermaid_figures/fig_001.png)\n"
    )

    doc = md_to_docx.convert_md_to_docx(md, tmp_path)
    out = tmp_path / "out.docx"
    doc.save(out)

    with zipfile.ZipFile(out) as zf:
        xml = zf.read("word/document.xml").decode("utf-8")
        media = [name for name in zf.namelist() if name.startswith("word/media/")]

    assert "flowchart LR" not in xml
    assert media


def test_ordered_lists_do_not_continue_across_sections(tmp_path: Path) -> None:
    md = (
        "## Section A\n\n"
        "1. First item\n"
        "2. Second item\n\n"
        "## Section B\n\n"
        "1. New first item\n"
        "2. New second item\n"
    )

    doc = md_to_docx.convert_md_to_docx(md, tmp_path)
    out = tmp_path / "lists.docx"
    doc.save(out)

    with zipfile.ZipFile(out) as zf:
        xml = zf.read("word/document.xml").decode("utf-8")

    assert "46." not in xml
    assert "<w:numPr>" not in xml
    assert "1. First item" in xml
    assert "1. New first item" in xml
    assert "New first item" in xml


def test_docx_qa_fails_word_auto_numbering(tmp_path: Path) -> None:
    doc = Document()
    p = doc.add_paragraph("Auto-numbered item")
    p._p.get_or_add_pPr().append(
        parse_xml(
            f'<w:numPr {nsdecls("w")}>'
            '<w:ilvl w:val="0"/>'
            '<w:numId w:val="1"/>'
            "</w:numPr>"
        )
    )
    out = tmp_path / "auto-numbering.docx"
    doc.save(out)

    report = qa_docx_math.check_docx_math(out)

    assert not report.passed
    assert report.word_auto_numbering_count == 1
    assert any("automatic numbering" in item for item in report.structural_failures)
