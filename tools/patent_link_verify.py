# -*- coding: utf-8 -*-
"""
Verify stable public patent URLs for hits produced by cnipa_epub_search.py.

Input can be a JSON array, or terminal output containing one line prefixed with
`EPUB_HITS_JSON:`. Output is one stdout line prefixed with `PATENT_LINKS_JSON:`.

This script deliberately treats CNIPA EPUB /patent/{publication_number} URLs as
hints, not verified public URLs. It only promotes a URL to `link`/`stable_url`
after the page was opened and matched to the same publication number or title.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"
)


@dataclass
class LinkVerification:
    publication_number: str | None
    input_title: str | None
    source_origin: str | None
    source_hint_url: str | None
    google_patents_url: str | None
    stable_url: str | None
    link: str | None
    verification_status: str
    http_status: int | None
    opened_status: str
    observed_title: str | None
    matched_by: str | None
    verification_time: str
    error_type: str | None = None
    error: str | None = None


def _ensure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError, TypeError):
            pass


def _read_payload(input_path: str | None) -> str:
    if input_path:
        return Path(input_path).read_text(encoding="utf-8-sig")
    return sys.stdin.read()


def load_hits(payload: str) -> list[dict[str, Any]]:
    """Load a hit array from raw JSON or an EPUB_HITS_JSON terminal transcript."""
    payload = payload.lstrip("\ufeff").strip()
    if not payload:
        return []
    for line in payload.splitlines():
        if line.strip().startswith("EPUB_HITS_JSON:"):
            payload = line.split("EPUB_HITS_JSON:", 1)[1].strip()
            break
    data = json.loads(payload)
    if not isinstance(data, list):
        raise ValueError("input JSON must be an array")
    return [x for x in data if isinstance(x, dict)]


def google_patents_candidates(pub_number: str | None, preferred_url: str | None = None) -> list[str]:
    if not pub_number:
        return [preferred_url] if preferred_url else []
    pub = pub_number.strip().replace(" ", "")
    if not re.match(r"^(CN|US|EP|WO)\w+", pub, flags=re.IGNORECASE):
        return [preferred_url] if preferred_url else []

    langs = ["zh", "en"] if pub.upper().startswith("CN") else ["en"]
    urls = [f"https://patents.google.com/patent/{pub}/{lang}" for lang in langs]
    if preferred_url and preferred_url not in urls:
        urls.insert(0, preferred_url)
    return urls


def _fetch_url(url: str, timeout: float) -> tuple[int | None, str, str | None]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(1_000_000)
            charset = resp.headers.get_content_charset() or "utf-8"
            return resp.status, raw.decode(charset, errors="replace"), None
    except urllib.error.HTTPError as e:
        try:
            raw = e.read(200_000)
            text = raw.decode(e.headers.get_content_charset() or "utf-8", errors="replace")
        except Exception:
            text = ""
        return e.code, text, f"HTTPError: {e.code}"
    except urllib.error.URLError as e:
        return None, "", f"URLError: {e.reason}"
    except TimeoutError as e:
        return None, "", f"TimeoutError: {e}"


Fetcher = Callable[[str, float], tuple[int | None, str, str | None]]


def _extract_title(page_text: str) -> str | None:
    m = re.search(r"<title[^>]*>(.*?)</title>", page_text, flags=re.I | re.S)
    if not m:
        return None
    title = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", m.group(1)))).strip()
    return title or None


def _compact(s: str | None) -> str:
    if not s:
        return ""
    return re.sub(r"\s+", "", html.unescape(s)).lower()


def _title_token_match(input_title: str | None, page_text: str) -> bool:
    compact_title = _compact(input_title)
    compact_page = _compact(page_text)
    if len(compact_title) < 8 or not compact_page:
        return False
    if compact_title in compact_page:
        return True
    tokens = [t for t in re.split(r"[\s,，。；;、:：()\[\]（）]+", input_title or "") if len(t) >= 3]
    if not tokens:
        return False
    matched = sum(1 for t in tokens if _compact(t) and _compact(t) in compact_page)
    return matched >= max(1, min(3, len(tokens)))


def verify_hit(hit: dict[str, Any], timeout: float = 15.0, fetcher: Fetcher = _fetch_url) -> LinkVerification:
    pub_number = hit.get("pub_number") or hit.get("publication_number")
    input_title = hit.get("title")
    source_hint_url = hit.get("cnipa_qr_or_hint_url") or hit.get("source_hint_url")
    preferred_google_url = hit.get("google_patents_url")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    last_status: int | None = None
    last_error: str | None = None
    last_title: str | None = None

    for url in google_patents_candidates(pub_number, preferred_google_url):
        status, page_text, error = fetcher(url, timeout)
        last_status, last_error = status, error
        last_title = _extract_title(page_text)

        if status == 404:
            continue
        if status != 200 or not page_text:
            continue

        compact_page = _compact(page_text)
        pub_match = bool(pub_number and _compact(pub_number) in compact_page)
        title_match = _title_token_match(input_title, page_text)
        if pub_match or title_match:
            return LinkVerification(
                publication_number=pub_number,
                input_title=input_title,
                source_origin=hit.get("source_origin"),
                source_hint_url=source_hint_url,
                google_patents_url=url,
                stable_url=url,
                link=url,
                verification_status="third_party_verified",
                http_status=status,
                opened_status="opened",
                observed_title=last_title,
                matched_by="publication_number" if pub_match else "title",
                verification_time=now,
            )
        last_error = "opened page but publication number/title did not match"

    status_name = "third_party_not_indexed" if last_status == 404 else "failed"
    return LinkVerification(
        publication_number=pub_number,
        input_title=input_title,
        source_origin=hit.get("source_origin"),
        source_hint_url=source_hint_url,
        google_patents_url=preferred_google_url,
        stable_url=None,
        link=None,
        verification_status=status_name,
        http_status=last_status,
        opened_status="not_verified",
        observed_title=last_title,
        matched_by=None,
        verification_time=now,
        error_type="google_patents_not_indexed" if last_status == 404 else "verification_failed",
        error=last_error,
    )


def verify_hits(hits: list[dict[str, Any]], timeout: float = 15.0, limit: int | None = None) -> list[dict[str, Any]]:
    rows = []
    selected = hits[:limit] if limit else hits
    for hit in selected:
        rows.append(asdict(verify_hit(hit, timeout=timeout)))
    return rows


def main(argv: list[str] | None = None) -> int:
    _ensure_utf8_stdio()
    parser = argparse.ArgumentParser(description="Verify stable Google Patents URLs for EPUB hits.")
    parser.add_argument("--input", "-i", help="Path to JSON array or transcript containing EPUB_HITS_JSON.")
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args(argv)

    try:
        hits = load_hits(_read_payload(args.input))
        rows = verify_hits(hits, timeout=args.timeout, limit=args.limit)
    except Exception as e:
        print("PATENT_LINK_VERIFY_ERROR:", e, file=sys.stderr)
        return 1

    print("PATENT_LINKS_JSON:", json.dumps(rows, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
