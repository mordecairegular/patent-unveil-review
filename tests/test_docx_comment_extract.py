"""Tests for tools/docx_comment_extract.py (reviewer-comment extraction)."""

from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent.parent / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import docx_comment_extract  # noqa: E402

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W14 = "http://schemas.microsoft.com/office/word/2010/wordml"
W15 = "http://schemas.microsoft.com/office/word/2012/wordml"


def _document_xml() -> str:
    # par0: range comment 0 anchored on "校核台账"
    # par1: point comment 1 (commentReference only, no range)
    # par2: empty paragraph (figure stand-in) carrying point comment 2
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="{W}">
  <w:body>
    <w:p>
      <w:r><w:t>S4，</w:t></w:r>
      <w:commentRangeStart w:id="0"/>
      <w:r><w:t>校核台账</w:t></w:r>
      <w:commentRangeEnd w:id="0"/>
      <w:r><w:commentReference w:id="0"/></w:r>
      <w:r><w:t>并冻结。</w:t></w:r>
    </w:p>
    <w:p>
      <w:r><w:t>S10，排序并输出代表方案。</w:t></w:r>
      <w:r><w:commentReference w:id="1"/></w:r>
    </w:p>
    <w:p>
      <w:r><w:commentReference w:id="2"/></w:r>
    </w:p>
  </w:body>
</w:document>"""


def _comments_xml() -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:comments xmlns:w="{W}" xmlns:w14="{W14}">
  <w:comment w:id="0" w:author="外部专利代理师" w:date="2026-07-13T10:00:00Z">
    <w:p w14:paraId="AAAA0000"><w:r><w:t>具体如何校核台账？约束条件是什么？</w:t></w:r></w:p>
  </w:comment>
  <w:comment w:id="1" w:author="外部专利代理师" w:date="2026-07-13T10:01:00Z">
    <w:p w14:paraId="BBBB0000"><w:r><w:t>各步骤具体如何操作？</w:t></w:r></w:p>
  </w:comment>
  <w:comment w:id="2" w:author="申请人" w:date="2026-07-14T09:00:00Z">
    <w:p w14:paraId="CCCC0000"><w:r><w:t>已补充S4校核条件，见修订稿。</w:t></w:r></w:p>
  </w:comment>
</w:comments>"""


def _comments_extended_xml() -> str:
    # comment 2 is a reply to comment 0; comment 1 marked done
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w15:commentsEx xmlns:w15="{W15}">
  <w15:commentEx w15:paraId="AAAA0000" w15:done="0"/>
  <w15:commentEx w15:paraId="BBBB0000" w15:done="1"/>
  <w15:commentEx w15:paraId="CCCC0000" w15:done="0" w15:paraIdParent="AAAA0000"/>
</w15:commentsEx>"""


def _build_docx(path: Path, *, with_extended: bool = True, with_comments: bool = True) -> Path:
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>',
        )
        zf.writestr("word/document.xml", _document_xml())
        if with_comments:
            zf.writestr("word/comments.xml", _comments_xml())
        if with_extended:
            zf.writestr("word/commentsExtended.xml", _comments_extended_xml())
    return path


def test_range_and_point_comments_extracted_with_anchors(tmp_path: Path) -> None:
    docx = _build_docx(tmp_path / "reviewed.docx")

    comments = docx_comment_extract.extract_comments(docx)

    by_id = {m.docx_id: m for m in comments}
    c0, c1 = by_id["0"], by_id["1"]
    assert c0.kind == "range"
    assert c0.anchor_excerpt == "校核台账"
    assert "S4" in c0.context_paragraph
    assert c1.kind == "point"
    assert "S10" in c1.context_paragraph
    # top-level sequence follows document order, replies excluded
    assert c0.seq == "C01"
    assert c1.seq == "C02"


def test_reply_threading_done_flag_and_figure_fallback(tmp_path: Path) -> None:
    docx = _build_docx(tmp_path / "reviewed.docx")

    comments = docx_comment_extract.extract_comments(docx)

    by_id = {m.docx_id: m for m in comments}
    reply = by_id["2"]
    assert reply.is_reply is True
    assert reply.parent_docx_id == "0"
    assert reply.seq == "C01-R1"
    assert by_id["1"].done is True
    # reply anchored on an empty (figure) paragraph falls back to preceding text
    assert "锚点段落无文字" in reply.context_paragraph
    assert "S10" in reply.context_paragraph
    # output order: parent immediately followed by its reply
    seqs = [m.seq for m in comments]
    assert seqs.index("C01-R1") == seqs.index("C01") + 1


def test_no_comments_xml_returns_empty(tmp_path: Path) -> None:
    docx = _build_docx(tmp_path / "clean.docx", with_comments=False, with_extended=False)

    assert docx_comment_extract.extract_comments(docx) == []


def test_cli_json_and_markdown_output(tmp_path: Path) -> None:
    docx = _build_docx(tmp_path / "reviewed.docx")
    out_md = tmp_path / "comments.md"

    result = subprocess.run(
        [
            sys.executable,
            str(TOOLS_DIR / "docx_comment_extract.py"),
            "--input",
            str(docx),
            "--output",
            str(out_md),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode == 0
    json_line = [
        line for line in result.stdout.splitlines() if line.startswith("COMMENT_EXTRACT_JSON ")
    ][-1]
    payload = json.loads(json_line.split(" ", 1)[1])
    assert payload["comment_count"] == 3
    assert payload["top_level_count"] == 2
    assert payload["reply_count"] == 1
    md_text = out_md.read_text(encoding="utf-8")
    assert "代理批注提取与定位索引" in md_text
    assert "校核台账" in md_text
    # original comment text is kept verbatim in a fenced block
    assert "具体如何校核台账？约束条件是什么？" in md_text
