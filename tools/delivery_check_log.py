#!/usr/bin/env python3
"""
在案件目录追加「交底书交付检查记录.md」一条：含记录时间（本地 + UTC）、PASS/WARN/FAIL、交付文件、检查摘要和待补项。
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

DEFAULT_LOG = "交底书交付检查记录.md"

FILE_HEADER = """# 交底书交付检查记录

> 本文件跟随具体案件目录，用于记录每次交底书交付前后的质量门禁结果。请勿把本记录内容复制进交底书正文。

"""


def _format_artifacts(raw: str) -> str:
    items = [item.strip() for item in raw.split(",") if item.strip()]
    if not items:
        return "—"
    return "\n".join(f"- `{item}`" for item in items)


def _value_or_dash(value: str) -> str:
    value = (value or "").strip()
    return value if value else "—"


def build_entry(
    *,
    status: str,
    summary: str,
    pending: str,
    artifacts: str,
    checks: str,
    next_action: str,
) -> str:
    now_local = datetime.now().astimezone()
    now_utc = datetime.now(timezone.utc)

    return f"""## {now_local.strftime("%Y-%m-%d %H:%M:%S")}（本地） · {now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")}（UTC）

**状态**：{status}

**本轮交付文件**：

{_format_artifacts(artifacts)}

**检查摘要**：

{_value_or_dash(summary)}

**待补项**：

{_value_or_dash(pending)}

**关键检查结果**：

{_value_or_dash(checks)}

**下一步建议**：

{_value_or_dash(next_action)}

---

"""


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Append one delivery gate-check entry to case-dir log markdown"
    )
    parser.add_argument(
        "--case-dir",
        type=Path,
        required=True,
        help="案件产出目录（与交底书 .md/.docx 同级，须已存在）",
    )
    parser.add_argument(
        "--status",
        choices=("PASS", "WARN", "FAIL"),
        required=True,
        help="PASS=代理人审稿就绪；WARN=阶段稿有待补项；FAIL=不得作为定稿交付",
    )
    parser.add_argument(
        "--summary",
        default="",
        help="本轮交付检查摘要",
    )
    parser.add_argument(
        "--pending",
        default="",
        help="待补项，多个可用分号或逗号分隔",
    )
    parser.add_argument(
        "--artifacts",
        default="",
        help="本轮交付文件名，多个用英文逗号分隔",
    )
    parser.add_argument(
        "--checks",
        default="",
        help="关键检查结果，如查新等级、区别特征、图示、格式、诚信检查",
    )
    parser.add_argument(
        "--next",
        default="",
        dest="next_action",
        help="下一步建议，如补正式附图、补实验数据、交代理人复核",
    )
    parser.add_argument(
        "--log-name",
        default=DEFAULT_LOG,
        help=f"日志文件名（默认：{DEFAULT_LOG}）",
    )
    args = parser.parse_args(argv)

    case_dir = args.case_dir.expanduser().resolve()
    if not case_dir.is_dir():
        print(f"ERROR: 目录不存在或不是目录: {case_dir}", file=sys.stderr)
        return 2

    log_path = case_dir / args.log_name
    entry = build_entry(
        status=args.status,
        summary=args.summary,
        pending=args.pending,
        artifacts=args.artifacts,
        checks=args.checks,
        next_action=args.next_action,
    )

    if log_path.exists():
        prev = log_path.read_text(encoding="utf-8")
        if prev and not prev.endswith("\n"):
            prev += "\n"
        log_path.write_text(prev + "\n" + entry, encoding="utf-8")
    else:
        log_path.write_text(FILE_HEADER + "\n" + entry, encoding="utf-8")

    print(f"LOG_FILE={log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
