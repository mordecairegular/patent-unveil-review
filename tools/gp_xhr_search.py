# -*- coding: utf-8 -*-
"""Google Patents XHR 关键词检索（Step 5 补充渠道，见 prompts/prior_art_search.md §A2）。

定位：补 CNIPA EPUB 公布站「仅结果首页 ~10 条/词、无翻页」的覆盖短板；提供按相关度
排序、覆盖全库（中英文、含授权文本）的关键词检索。**发现级渠道**：输出条目一律标
``verification_status = "google_xhr_search_result"``，写入交底书公开引用前仍须经
``patent_link_verify.py`` 或人工打开稳定详情页复核。

- 仅标准库 urllib，自动走系统代理；无 Playwright 依赖。
- **stdout 仅一行** ``GP_HITS_JSON:`` + JSON 数组（UTF-8，字段与 ``EPUB_HITS_JSON``
  对齐：``title`` / ``pub_number`` / ``abstract`` / ``google_patents_url`` /
  ``verification_status`` / ``source_origin`` 等，另含 ``assignee`` 与日期字段）。
- **stderr** 输出 ``GP_NOTE:`` / ``GP_XHR_ERROR:``（ASCII）。
- 礼貌抓取：单次最多 5 页（约 50 条），页间默认间隔 1.5s。该 XHR 为站点前端接口，
  非公开 API，可能变更；失效时按 prior_art_search.md 渠道矩阵回退
  WebSearch(patents.google.com 域限定) + 详情页复核，不得因渠道失效下调查新结论。

用法：
  python tools/gp_xhr_search.py 储能 需量 充电桩
  python tools/gp_xhr_search.py "并网点 越限 协同" --pages 3
  python tools/gp_xhr_search.py solar storage "demand charge" --pages 2 --sleep 2
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"
)
MAX_PAGES = 5  # 礼貌上限：一次最多 5 页（~50 条）


def _ensure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError, TypeError):
            pass


def fetch_page(query: str, page: int, timeout: float) -> dict:
    inner = "q=" + urllib.parse.quote(query)
    if page > 0:
        inner += "&page=%d" % page
    url = "https://patents.google.com/xhr/query?url=" + urllib.parse.quote(inner, safe="")
    req = urllib.request.Request(
        url, headers={"User-Agent": UA, "Referer": "https://patents.google.com/"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def hits_from(data: dict) -> tuple[list[dict], int | None]:
    results = (data or {}).get("results", {}) or {}
    total = results.get("total_num_results")
    out: list[dict] = []
    for cluster in results.get("cluster", []) or []:
        for item in cluster.get("result", []) or []:
            p = item.get("patent") or {}
            pub = (p.get("publication_number") or "").strip() or None
            out.append(
                {
                    "title": (p.get("title") or "").strip(),
                    "pub_number": pub,
                    "assignee": (p.get("assignee") or "").strip() or None,
                    "inventor": (p.get("inventor") or "").strip() or None,
                    "filing_date": p.get("filing_date") or None,
                    "publication_date": p.get("publication_date") or None,
                    "grant_date": p.get("grant_date") or None,
                    "abstract": (p.get("snippet") or "").strip(),
                    "google_patents_url": (
                        "https://patents.google.com/patent/%s/zh" % pub if pub else None
                    ),
                    "verification_status": "google_xhr_search_result",
                    "source_origin": "google_patents_xhr",
                }
            )
    return out, total


def main(argv: list[str] | None = None) -> int:
    _ensure_utf8_stdio()
    parser = argparse.ArgumentParser(
        prog="gp_xhr_search.py",
        description="Google Patents XHR keyword search (discovery-level; verify before citing).",
    )
    parser.add_argument("query", nargs="+", help="检索词（多个参数以空格连接为一条查询）")
    parser.add_argument(
        "--pages", type=int, default=1, help="抓取页数（10 条/页，上限 %d）" % MAX_PAGES
    )
    parser.add_argument("--timeout", type=float, default=25.0)
    parser.add_argument("--sleep", type=float, default=1.5, help="翻页间隔秒数（礼貌抓取）")
    args = parser.parse_args(argv)

    query = " ".join(args.query).strip()
    if not query:
        print("GP_XHR_ERROR: empty query", file=sys.stderr)
        return 2

    pages = max(1, min(args.pages, MAX_PAGES))
    seen: set[str] = set()
    merged: list[dict] = []
    total: int | None = None

    for pg in range(pages):
        try:
            data = fetch_page(query, pg, args.timeout)
        except Exception as e:
            print("GP_XHR_ERROR: page=%d %s" % (pg, e), file=sys.stderr, flush=True)
            if pg == 0:
                return 1
            break
        hits, page_total = hits_from(data)
        total = page_total if page_total is not None else total
        for h in hits:
            key = h.get("pub_number") or (h.get("title") or "")[:120]
            if key and key not in seen:
                seen.add(key)
                merged.append(h)
        if not hits:
            break
        if pg + 1 < pages:
            time.sleep(max(0.0, args.sleep))

    print(
        "GP_NOTE: pages_fetched<=%d merged_hits=%d total_num_results=%s"
        % (pages, len(merged), total),
        file=sys.stderr,
        flush=True,
    )
    # 仅此一行写入 stdout，供管道/Agent 稳定解析（与 EPUB_HITS_JSON 同约定）
    print("GP_HITS_JSON:", json.dumps(merged, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
