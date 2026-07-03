# -*- coding: utf-8 -*-
"""查新渠道环境预检（Step 5 前可选执行；跨环境排障时必做）。

背景：本技能会在多种执行环境中运行（本机 Claude Code、本机 Codex 桌面 shell、
云端沙箱）。CNIPA 站点带 WAF 且可能直接拒绝数据中心出口 IP；Google 侧连通性依赖
系统代理。**渠道失败是环境状态，不是"无现有技术"，也不代表脚本损坏**——预检结果
应写入案件 ``query_log.md``，Agent 据此选择渠道组合（见 prompts/prior_art_search.md
「渠道不可用时的处理」）。

检查项（全部只读、单次、不触碰任何登录/验证码链路）：

- Python 版本、系统代理（``urllib.request.getproxies()``）
- Playwright 是否可导入、Chromium 是否已安装（不启动浏览器）
- Google Patents 首页 GET 与 XHR 检索接口（极小查询）
- ``epub.cnipa.gov.cn`` TCP 可达性（TCP 通不代表 WAF 放行；EPUB 全链路只能靠
  实际运行 ``cnipa_epub_search.py`` 验证）
- **不探测 CNIPA PSS**：PSS 为登录制官方系统，遇阻仅记录
  ``official_pss_blocked_in_current_environment``，一律人工/浏览器渠道复核。

输出：**stdout 仅一行** ``CHANNEL_STATUS_JSON:`` + JSON 对象；stderr 为 ASCII
``PREFLIGHT_NOTE:``。退出码恒为 0（信息性脚本）。

用法： python tools/channel_preflight.py [--timeout 10]
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import urllib.request
from datetime import datetime, timezone

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"
)


def _ensure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError, TypeError):
            pass


def _short(e: Exception) -> str:
    return ("%s: %s" % (type(e).__name__, e))[:200]


def check_playwright() -> dict:
    try:
        from playwright.sync_api import sync_playwright  # noqa: PLC0415
    except ImportError:
        return {"installed": False, "chromium_present": False}
    try:
        with sync_playwright() as p:
            path = p.chromium.executable_path
            return {
                "installed": True,
                "chromium_present": bool(path) and os.path.exists(path),
            }
    except Exception as e:  # noqa: BLE001
        return {"installed": True, "chromium_present": False, "error": _short(e)}


def check_http(url: str, timeout: float) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return {"ok": resp.status == 200, "http_status": resp.status}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": _short(e)}


def check_google_xhr(timeout: float) -> dict:
    url = "https://patents.google.com/xhr/query?url=q%3Dpatent"
    req = urllib.request.Request(
        url, headers={"User-Agent": UA, "Referer": "https://patents.google.com/"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
            return {"ok": isinstance(data, dict) and "results" in data}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": _short(e)}


def check_tcp(host: str, port: int, timeout: float) -> dict:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return {"ok": True}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": _short(e)}


def main(argv: list[str] | None = None) -> int:
    _ensure_utf8_stdio()
    parser = argparse.ArgumentParser(
        prog="channel_preflight.py", description="Prior-art search channel preflight."
    )
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args(argv)
    t = args.timeout

    playwright = check_playwright()
    google_page = check_http("https://patents.google.com/", t)
    google_xhr = check_google_xhr(t)
    epub_tcp = check_tcp("epub.cnipa.gov.cn", 80, min(t, 6.0))

    google_ok = bool(google_page.get("ok") or google_xhr.get("ok"))
    playwright_ready = bool(playwright.get("installed") and playwright.get("chromium_present"))

    recommended: list[str] = []
    notes: list[str] = []

    if playwright_ready:
        recommended.append("cnipa_epub_search.py (playwright, run to fully verify WAF passage)")
    else:
        notes.append(
            "playwright_or_chromium_missing: pip install -r tools/requirements-cnipa.txt "
            "&& python -m playwright install chromium"
        )
    if google_xhr.get("ok"):
        recommended.append("gp_xhr_search.py (keyword discovery)")
    if google_page.get("ok"):
        recommended.append("patent_link_verify.py / Google Patents detail pages")
    if not google_ok:
        notes.append(
            "google_side_blocked_in_current_environment: fall back to Agent WebSearch "
            "(patents.google.com domain) and server-side page fetch"
        )
    if not epub_tcp.get("ok"):
        notes.append(
            "epub_tcp_unreachable: likely cloud-sandbox or blocked egress; run search "
            "scripts on the user's local machine instead"
        )
    else:
        notes.append("epub_tcp_ok_but_waf_untested: only a real cnipa_epub_search.py run proves passage")
    recommended.append("CNIPA PSS: manual/browser only (never scripted)")

    status = {
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python": sys.version.split()[0],
        "proxies": urllib.request.getproxies(),
        "playwright": playwright,
        "google_page": google_page,
        "google_xhr": google_xhr,
        "epub_tcp": epub_tcp,
        "pss": {"probed": False, "policy": "manual_or_browser_only"},
        "recommended": recommended,
        "notes": notes,
    }

    print(
        "PREFLIGHT_NOTE: google_ok=%s playwright_ready=%s epub_tcp=%s"
        % (google_ok, playwright_ready, bool(epub_tcp.get("ok"))),
        file=sys.stderr,
        flush=True,
    )
    print("CHANNEL_STATUS_JSON:", json.dumps(status, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
