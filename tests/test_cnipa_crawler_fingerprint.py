# -*- coding: utf-8 -*-
"""cnipa_epub_crawler 浏览器特征回归：保留的三项去无头/自动化处理须持续生效。

只访问本机临时 HTTP 服务，不连 CNIPA。无 Playwright 或 Chromium 时跳过。
"""
from __future__ import annotations

import http.server
import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))


def test_crawler_context_hides_headless_and_webdriver_markers() -> None:
    sync_api = pytest.importorskip("playwright.sync_api")
    import cnipa_epub_crawler as crawler

    seen: dict[str, str] = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            seen.update({k.lower(): v for k, v in self.headers.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body>probe</body></html>")

        def log_message(self, *args: object) -> None:
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with sync_api.sync_playwright() as p:
            try:
                browser = crawler._launch_browser(p)
            except Exception as exc:  # Chromium 未安装等
                pytest.skip(f"Chromium unavailable: {exc}")
            try:
                page = crawler._new_context(browser).new_page()
                page.goto(f"http://127.0.0.1:{server.server_address[1]}/")
                webdriver = page.evaluate("navigator.webdriver")
                js_ua = page.evaluate("navigator.userAgent")
                major = browser.version.split(".")[0]
            finally:
                browser.close()
    finally:
        server.shutdown()

    assert webdriver is False
    for ua in (seen["user-agent"], js_ua):
        assert "Headless" not in ua
        assert f"Chrome/{major}." in ua  # 真实版本，不是写死的旧版本
    assert seen.get("accept-language", "").startswith("zh-CN")
