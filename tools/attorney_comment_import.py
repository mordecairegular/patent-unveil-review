#!/usr/bin/env python3
"""Import attorney comments supplied as plain text into the canonical schema.

The importer deliberately preserves the source text.  It only splits comments
when the source contains explicit item markers.  Unnumbered prose is one
top-level comment unless ``--split-paragraphs`` is explicitly requested.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


SOURCE_TYPES = {
    "pasted_text",
    "text_file",
    "message_export",
    "user_paraphrase",
    "ocr_source",
    "structured_table",
}

ITEM_RE = re.compile(
    r"^\s*(?:"
    r"(?P<cid>C\d{1,3})\s*[.、:：\-|]\s*"
    r"|(?P<num>\d{1,3})\s*[.、:：]\s*"
    r"|[（(](?P<paren>\d{1,3})[）)]\s*"
    r"|[【\[](?P<bracket>\d{1,3})[】\]]\s*"
    r"|意见\s*(?P<label>\d{1,3})\s*[.、:：]\s*"
    r")(?P<body>.*)$",
    re.I,
)


@dataclass(frozen=True)
class ImportedComment:
    seq: str
    text: str
    start_line: int
    end_line: int


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


def split_comments(text: str, *, split_paragraphs: bool = False) -> tuple[list[ImportedComment], str]:
    """Return comments and the counting basis.

    Explicit markers are authoritative.  Otherwise the source is a single
    comment, unless the caller explicitly opts into paragraph splitting.
    """
    lines = text.splitlines()
    starts: list[tuple[int, re.Match[str]]] = []
    for index, line in enumerate(lines):
        match = ITEM_RE.match(line)
        if match:
            starts.append((index, match))

    comments: list[ImportedComment] = []
    if starts:
        prefix = "\n".join(lines[: starts[0][0]]).strip()
        for position, (start, match) in enumerate(starts):
            end = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
            body_lines = [match.group("body"), *lines[start + 1 : end]]
            body = "\n".join(body_lines).strip()
            if position == 0 and prefix:
                body = f"{prefix}\n{body}".strip()
            if body:
                comments.append(
                    ImportedComment(
                        seq=f"C{len(comments) + 1:02d}",
                        text=body,
                        start_line=start + 1,
                        end_line=end,
                    )
                )
        return comments, "explicit_item_markers"

    if split_paragraphs:
        start: int | None = None
        for index in range(len(lines) + 1):
            line = lines[index] if index < len(lines) else ""
            if line.strip() and start is None:
                start = index
            if start is not None and (not line.strip() or index == len(lines)):
                body = "\n".join(lines[start:index]).strip()
                if not body:
                    start = None
                    continue
                start_line = start + 1
                end_line = index
                comments.append(
                    ImportedComment(
                        seq=f"C{len(comments) + 1:02d}",
                        text=body,
                        start_line=start_line,
                        end_line=end_line,
                    )
                )
                start = None
        return comments, "paragraph_blocks"

    body = text.strip()
    if body:
        start_line = next(
            (index for index, line in enumerate(lines, start=1) if line.strip()),
            1,
        )
        end_line = len(lines)
        comments.append(ImportedComment("C01", body, start_line, end_line))
    return comments, "single_unstructured_source"


def build_payload(
    input_path: Path,
    *,
    source_type: str,
    producer: str,
    split_paragraphs: bool = False,
) -> dict[str, object]:
    raw_bytes = input_path.read_bytes()
    text = raw_bytes.decode("utf-8-sig")
    comments, count_basis = split_comments(text, split_paragraphs=split_paragraphs)
    verbatim_status = (
        "source_exact"
        if source_type in {"pasted_text", "text_file", "message_export", "structured_table"}
        else "transcribed_or_paraphrased"
    )
    count_status = (
        "verified"
        if count_basis == "explicit_item_markers"
        and source_type not in {"user_paraphrase", "ocr_source"}
        else "provisional"
    )
    return {
        "schema_version": "1.0",
        "tool": "attorney_comment_import",
        "producer": producer,
        "source": {
            "type": source_type,
            "file": str(input_path),
            "sha256": _sha256_bytes(raw_bytes),
            "verbatim_status": verbatim_status,
        },
        "comment_count": len(comments),
        "top_level_count": len(comments),
        "reply_count": 0,
        "count": {
            "top_level": len(comments),
            "replies": 0,
            "basis": count_basis,
            "status": count_status,
        },
        "comments": [
            {
                "seq": comment.seq,
                "source_native_id": None,
                "author": None,
                "date": None,
                "kind": "text",
                "is_reply": False,
                "parent_docx_id": None,
                "done": False,
                "anchor_excerpt": "",
                "context_paragraph": "",
                "paragraph_index": None,
                "text": comment.text,
                "text_sha256": _sha256_bytes(comment.text.encode("utf-8")),
                "source_locator": {
                    "type": "line_range",
                    "value": f"L{comment.start_line}-L{comment.end_line}",
                },
                "target_confirmation": "needs_human",
                "subrequirements": [],
            }
            for comment in comments
        ],
    }


def render_markdown(payload: dict[str, object]) -> str:
    source = payload["source"]
    count = payload["count"]
    assert isinstance(source, dict) and isinstance(count, dict)
    lines = [
        "# 代理意见原文包",
        "",
        f"- 来源类型：`{source['type']}`",
        f"- 来源文件：`{Path(str(source['file'])).name}`",
        f"- 原文状态：`{source['verbatim_status']}`",
        f"- 条数口径：`{count['basis']}` / `{count['status']}`",
        "- 说明：下列文字按输入源保留；若来源为转述、OCR 或未编号文本，"
        "条数与目标位置须人工确认，不能把临时拆分当作代理人原始编号。",
        "",
    ]
    for comment in payload["comments"]:  # type: ignore[index]
        assert isinstance(comment, dict)
        lines.extend(
            [
                f"## {comment['seq']}",
                "",
                f"- 来源位置：`{comment['source_locator']['value']}`",  # type: ignore[index]
                f"- 目标确认：`{comment['target_confirmation']}`",
                "- 代理意见原文：",
                "",
                "```text",
                str(comment["text"]),
                "```",
                "",
            ]
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        description="Import attorney comments from text into the canonical JSON schema."
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--source-type", required=True, choices=sorted(SOURCE_TYPES))
    parser.add_argument("--producer", default="unspecified")
    parser.add_argument("--output-json", required=True, type=Path)
    parser.add_argument("--output-md", type=Path)
    parser.add_argument(
        "--split-paragraphs",
        action="store_true",
        help="Treat blank-line separated blocks as provisional comments.",
    )
    args = parser.parse_args(argv)

    if not args.input.is_file():
        print(f"ERROR: input not found: {args.input}", file=sys.stderr)
        return 2
    try:
        payload = build_payload(
            args.input,
            source_type=args.source_type,
            producer=args.producer,
            split_paragraphs=args.split_paragraphs,
        )
    except (OSError, UnicodeError) as exc:
        print(f"ERROR: cannot import {args.input.name}: {exc}", file=sys.stderr)
        return 2

    _atomic_write(
        args.output_json,
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    )
    if args.output_md:
        _atomic_write(args.output_md, render_markdown(payload))
    print("COMMENT_EXTRACT_JSON " + json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
