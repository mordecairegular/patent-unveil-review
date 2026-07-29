#!/usr/bin/env python3
"""Extract reviewer comments (批注) from a reviewed .docx with anchor positions.

Reads word/comments.xml (comment id / author / date / text) and word/document.xml
(anchor location), classifies each comment as:

- ``range``  — a normal comment anchored to a text range (commentRangeStart/End
  wrapping non-empty text); the anchored text is reported as ``anchor_excerpt``.
- ``point``  — a point comment (reference without a text range, or a range that
  wraps no visible text, e.g. anchored on a figure paragraph or a paragraph
  mark); the containing paragraph's text is reported as context instead.
- ``unanchored`` — present in comments.xml but no reference found in the body.

Point comments are the ones that historically lose their meaning when comments
are exported as a flat list ("此处体现在方案中的哪部分？" without an anchor is
unusable) — this tool preserves the containing paragraph so the effective scope
can be judged downstream (see prompts/review_comment_closure.md).

Reply threads: when word/commentsExtended.xml is present, replies (回复批注)
are linked to their parent via ``w15:paraIdParent`` and numbered ``C01-R1``
instead of consuming top-level sequence numbers; ``w15:done`` (已解决) is
reported per comment. This keeps the attorney's original comments separable
from the applicant's replies in a 回复-round DOCX.

Outputs:
- canonical JSON file (``--json-output``), recommended as downstream truth;
- optional Markdown listing (``--output``): 批注定位索引 table + per-comment
  blocks with the original comment text verbatim (never rewritten or merged);
- final line ``COMMENT_EXTRACT_JSON {...}`` for machine consumption.

Usage:
  python3 tools/docx_comment_extract.py --input reviewed.docx \
    --json-output comments.json [--output comments.md]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W14_NS = "http://schemas.microsoft.com/office/word/2010/wordml"
W15_NS = "http://schemas.microsoft.com/office/word/2012/wordml"


def _w(tag: str) -> str:
    return f"{{{W_NS}}}{tag}"


EXCERPT_LIMIT = 120
CONTEXT_LIMIT = 200


@dataclass
class CommentMeta:
    docx_id: str
    author: str
    date: str
    text: str
    kind: str = "unanchored"
    anchor_excerpt: str = ""
    context_paragraph: str = ""
    paragraph_index: int | None = None
    seq: str = ""
    para_id: str = ""  # w14:paraId of the comment's last paragraph (identity key)
    is_reply: bool = False
    parent_docx_id: str | None = None
    done: bool = False


@dataclass
class _RangeState:
    parts: list[str] = field(default_factory=list)
    start_par_idx: int = 0


def _clip(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        newline="\n",
        delete=False,
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    ) as handle:
        handle.write(text)
        temp_path = Path(handle.name)
    temp_path.replace(path)


def parse_comments_xml(data: bytes) -> list[CommentMeta]:
    """Return comment metadata in comments.xml order (text kept verbatim)."""
    root = ET.fromstring(data)
    out: list[CommentMeta] = []
    para_id_attr = f"{{{W14_NS}}}paraId"
    for comment in root.iter(_w("comment")):
        cid = comment.attrib.get(_w("id"), "")
        author = comment.attrib.get(_w("author"), "")
        date = comment.attrib.get(_w("date"), "")
        paras: list[str] = []
        last_para_id = ""
        for par in comment.iter(_w("p")):
            paras.append("".join(t.text or "" for t in par.iter(_w("t"))))
            last_para_id = par.attrib.get(para_id_attr, last_para_id)
        out.append(
            CommentMeta(
                docx_id=cid,
                author=author,
                date=date,
                text="\n".join(paras).strip(),
                para_id=last_para_id,
            )
        )
    return out


def parse_comments_extended_xml(data: bytes) -> dict[str, dict[str, str]]:
    """Return paraId -> {"parent": paraIdParent or "", "done": "0"/"1"}."""
    root = ET.fromstring(data)
    out: dict[str, dict[str, str]] = {}
    for ex in root.iter(f"{{{W15_NS}}}commentEx"):
        para_id = ex.attrib.get(f"{{{W15_NS}}}paraId", "")
        if not para_id:
            continue
        out[para_id] = {
            "parent": ex.attrib.get(f"{{{W15_NS}}}paraIdParent", ""),
            "done": ex.attrib.get(f"{{{W15_NS}}}done", "0"),
        }
    return out


def parse_document_anchors(
    data: bytes,
) -> tuple[list[str], dict[str, dict[str, object]], dict[str, int]]:
    """Walk document.xml once; return (paragraphs, ranges, point_refs).

    ranges: comment id -> {"anchor": str, "start_par_idx": int}
    point_refs: comment id -> paragraph index (reference seen without a range)
    """
    paragraphs: list[str] = []
    cur_parts: list[str] = []
    active: dict[str, _RangeState] = {}
    ranges: dict[str, dict[str, object]] = {}
    point_refs: dict[str, int] = {}

    for event, elem in ET.iterparse(BytesIO(data), events=("start", "end")):
        tag = elem.tag
        if event == "start":
            if tag == _w("commentRangeStart"):
                cid = elem.attrib.get(_w("id"), "")
                active[cid] = _RangeState(start_par_idx=len(paragraphs))
            elif tag == _w("commentRangeEnd"):
                cid = elem.attrib.get(_w("id"), "")
                state = active.pop(cid, None)
                if state is not None:
                    ranges[cid] = {
                        "anchor": "".join(state.parts),
                        "start_par_idx": state.start_par_idx,
                    }
            continue
        # end events
        if tag == _w("t"):
            text = elem.text or ""
            cur_parts.append(text)
            for state in active.values():
                state.parts.append(text)
        elif tag == _w("commentReference"):
            cid = elem.attrib.get(_w("id"), "")
            if cid not in ranges and cid not in active:
                point_refs[cid] = len(paragraphs)
        elif tag == _w("p"):
            paragraphs.append("".join(cur_parts))
            cur_parts = []
            elem.clear()

    # ranges never closed (malformed doc): treat what was collected as anchor
    for cid, state in active.items():
        ranges.setdefault(
            cid, {"anchor": "".join(state.parts), "start_par_idx": state.start_par_idx}
        )
    return paragraphs, ranges, point_refs


def extract_comments(docx_path: Path) -> list[CommentMeta]:
    with zipfile.ZipFile(docx_path) as zf:
        names = set(zf.namelist())
        if "word/comments.xml" not in names:
            return []
        comments = parse_comments_xml(zf.read("word/comments.xml"))
        extended: dict[str, dict[str, str]] = {}
        if "word/commentsExtended.xml" in names:
            extended = parse_comments_extended_xml(zf.read("word/commentsExtended.xml"))
        if "word/document.xml" in names:
            paragraphs, ranges, point_refs = parse_document_anchors(
                zf.read("word/document.xml")
            )
        else:
            paragraphs, ranges, point_refs = [], {}, {}

    # Reply threading + resolved status (commentsExtended.xml).
    para_to_comment = {m.para_id: m for m in comments if m.para_id}
    for meta in comments:
        ex = extended.get(meta.para_id)
        if not ex:
            continue
        meta.done = ex["done"] == "1"
        parent_para = ex["parent"]
        if parent_para:
            meta.is_reply = True
            parent = para_to_comment.get(parent_para)
            meta.parent_docx_id = parent.docx_id if parent else None

    def _context(par_idx: int) -> str:
        if not (0 <= par_idx < len(paragraphs)):
            return ""
        text = paragraphs[par_idx].strip()
        if text:
            return _clip(text, CONTEXT_LIMIT)
        # Anchor paragraph carries no text (e.g. a figure): fall back to the
        # nearest preceding non-empty paragraph so the comment stays locatable.
        for prev in range(par_idx - 1, -1, -1):
            prev_text = paragraphs[prev].strip()
            if prev_text:
                return f"（锚点段落无文字，其前文为）{_clip(prev_text, CONTEXT_LIMIT)}"
        return ""

    for meta in comments:
        cid = meta.docx_id
        if cid in ranges:
            anchor = str(ranges[cid]["anchor"])
            par_idx = int(ranges[cid]["start_par_idx"])  # type: ignore[arg-type]
            meta.paragraph_index = par_idx
            meta.context_paragraph = _context(par_idx)
            if anchor.strip():
                meta.kind = "range"
                meta.anchor_excerpt = _clip(anchor, EXCERPT_LIMIT)
            else:
                meta.kind = "point"
        elif cid in point_refs:
            par_idx = point_refs[cid]
            meta.kind = "point"
            meta.paragraph_index = par_idx
            meta.context_paragraph = _context(par_idx)
        else:
            meta.kind = "unanchored"

    # Sequence numbers: top-level comments get C01.. in document order (anchor
    # paragraph position, falling back to numeric comment id); replies attach
    # to their parent as C01-R1, C01-R2 ... and do not consume top-level seq.
    def _order_key(meta: CommentMeta) -> tuple[int, int]:
        par = meta.paragraph_index if meta.paragraph_index is not None else 10**9
        try:
            cid_num = int(meta.docx_id)
        except ValueError:
            cid_num = 10**9
        return (par, cid_num)

    top_level = sorted((m for m in comments if not m.is_reply), key=_order_key)
    for seq, meta in enumerate(top_level, start=1):
        meta.seq = f"C{seq:02d}"
    by_id = {m.docx_id: m for m in comments}
    reply_counters: dict[str, int] = {}
    for meta in sorted((m for m in comments if m.is_reply), key=_order_key):
        parent = by_id.get(meta.parent_docx_id or "")
        base = parent.seq if parent and parent.seq else "C00"
        reply_counters[base] = reply_counters.get(base, 0) + 1
        meta.seq = f"{base}-R{reply_counters[base]}"

    # Output order: each top-level comment followed by its replies.
    ordered: list[CommentMeta] = []
    for meta in top_level:
        ordered.append(meta)
        ordered.extend(
            r
            for r in sorted((m for m in comments if m.is_reply), key=_order_key)
            if r.parent_docx_id == meta.docx_id
        )
    orphan_replies = [m for m in comments if m.is_reply and m not in ordered]
    ordered.extend(sorted(orphan_replies, key=_order_key))
    return ordered


KIND_LABEL = {"range": "范围批注", "point": "点批注", "unanchored": "未定位"}


def render_markdown(docx_path: Path, comments: list[CommentMeta]) -> str:
    top_count = sum(1 for m in comments if not m.is_reply)
    reply_count = len(comments) - top_count
    lines: list[str] = []
    lines.append("# 代理批注提取与定位索引")
    lines.append("")
    lines.append(f"- 来源文件：`{docx_path.name}`")
    lines.append(f"- 批注总数：{len(comments)}（原批注 {top_count} 条，回复 {reply_count} 条）")
    lines.append(
        "- 说明：批注原文逐字摘录、不改写不合并；「点批注」无文字锚定范围，"
        "仅给出所在段落摘录，其**作用范围须人工/Agent 判断**"
        "（可能针对整节，见 `prompts/review_comment_closure.md` R2）。"
    )
    lines.append("")
    lines.append("| 编号 | DOCX批注ID | 作者 | 类型 | 已解决 | 锚定文字 / 所在段落摘录 |")
    lines.append("|---|---|---|---|---|---|")
    for m in comments:
        anchor = m.anchor_excerpt if m.kind == "range" else m.context_paragraph
        anchor = _clip(anchor, 60).replace("|", "\\|") or "（无）"
        kind = "回复" if m.is_reply else KIND_LABEL.get(m.kind, m.kind)
        done = "是" if m.done else "否"
        lines.append(f"| {m.seq} | {m.docx_id} | {m.author} | {kind} | {done} | {anchor} |")
    lines.append("")
    for m in comments:
        title_kind = "回复批注" if m.is_reply else "批注"
        lines.append(f"## {m.seq}（DOCX{title_kind}ID {m.docx_id}｜{m.author}｜{m.date}）")
        lines.append("")
        if m.is_reply:
            lines.append(f"- 回复对象：DOCX批注ID {m.parent_docx_id or '未知'}")
        lines.append(f"- 类型：{KIND_LABEL.get(m.kind, m.kind)}")
        if m.kind == "range":
            lines.append(f"- 锚定文字：{m.anchor_excerpt}")
        if m.context_paragraph:
            lines.append(f"- 所在段落摘录：{m.context_paragraph}")
        lines.append(f"- 已解决标记：{'是' if m.done else '否'}")
        lines.append("- 批注原文：")
        lines.append("")
        lines.append("```text")
        lines.append(m.text)
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


def build_payload(
    docx_path: Path,
    comments: list[CommentMeta],
    *,
    producer: str,
) -> dict[str, object]:
    source_bytes = docx_path.read_bytes()
    top_level_count = sum(1 for m in comments if not m.is_reply)
    reply_count = sum(1 for m in comments if m.is_reply)
    return {
        "schema_version": "1.0",
        "tool": "docx_comment_extract",
        "producer": producer,
        "source": {
            "type": "reviewed_docx",
            "file": str(docx_path),
            "sha256": _sha256_bytes(source_bytes),
            "verbatim_status": "source_exact",
        },
        # Legacy summary keys remain for C14 and existing case files.
        "input": str(docx_path),
        "comment_count": len(comments),
        "top_level_count": top_level_count,
        "reply_count": reply_count,
        "count": {
            "top_level": top_level_count,
            "replies": reply_count,
            "basis": "docx_comment_threads",
            "status": "verified",
        },
        "comments": [
            {
                "seq": m.seq,
                "source_native_id": m.docx_id,
                "docx_id": m.docx_id,
                "author": m.author,
                "date": m.date,
                "kind": m.kind,
                "is_reply": m.is_reply,
                "parent_docx_id": m.parent_docx_id,
                "done": m.done,
                "anchor_excerpt": m.anchor_excerpt,
                "context_paragraph": m.context_paragraph,
                "paragraph_index": m.paragraph_index,
                "text": m.text,
                "text_sha256": _sha256_bytes(m.text.encode("utf-8")),
                "source_locator": {
                    "type": "docx_comment",
                    "value": m.docx_id,
                    "paragraph_index": m.paragraph_index,
                },
                "target_confirmation": (
                    "range_exact" if m.kind == "range" else "needs_human"
                ),
                "subrequirements": [],
            }
            for m in comments
        ],
    }


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows console defaults to GBK
    parser = argparse.ArgumentParser(
        description="Extract reviewer comments from a reviewed .docx with anchors."
    )
    parser.add_argument("--input", required=True, help="reviewed .docx path")
    parser.add_argument(
        "--output", help="optional Markdown listing path (批注定位索引)"
    )
    parser.add_argument(
        "--json-output",
        help="canonical JSON output path (recommended for downstream gates)",
    )
    parser.add_argument(
        "--producer",
        default="unspecified",
        help="producer label such as codex, claude, human, or unspecified",
    )
    args = parser.parse_args(argv)

    docx_path = Path(args.input)
    if not docx_path.is_file():
        print(f"ERROR: input not found: {docx_path}", file=sys.stderr)
        return 2
    try:
        comments = extract_comments(docx_path)
    except (zipfile.BadZipFile, ET.ParseError, KeyError, OSError) as exc:
        print(f"ERROR: cannot parse {docx_path.name}: {exc}", file=sys.stderr)
        return 2

    if args.output:
        out_path = Path(args.output)
        _atomic_write(out_path, render_markdown(docx_path, comments))
        print(f"markdown written: {out_path}")

    payload = build_payload(docx_path, comments, producer=args.producer)
    if args.json_output:
        json_path = Path(args.json_output)
        _atomic_write(
            json_path,
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        )
        print(f"json written: {json_path}")
    print("COMMENT_EXTRACT_JSON " + json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
