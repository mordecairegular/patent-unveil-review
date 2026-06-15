# -*- coding: utf-8 -*-
"""
Build or update a case-level prior-art dossier.

Inputs may be raw JSON arrays or terminal transcripts containing:
- EPUB_HITS_JSON: [...]
- PATENT_LINKS_JSON: [...]

Outputs in the case directory:
- prior_art_dossier.json
- prior_art_dossier.md
- positive_controls.md
- unverified_sources.md
- query_log.md
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VERIFIED_STATUSES = {
    "official_pss_verified",
    "official_detail_opened",
    "third_party_verified",
    "npl_verified",
}


def _ensure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError, TypeError):
            pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read_text(path: str | None) -> str:
    if not path:
        return ""
    return Path(path).read_text(encoding="utf-8-sig")


def _load_jsonish(text: str, prefixes: tuple[str, ...]) -> list[dict[str, Any]]:
    text = text.lstrip("\ufeff").strip()
    if not text:
        return []
    for line in text.splitlines():
        stripped = line.strip()
        for prefix in prefixes:
            if stripped.startswith(prefix):
                text = stripped.split(prefix, 1)[1].strip()
                break
        else:
            continue
        break
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError("expected a JSON array")
    return [x for x in data if isinstance(x, dict)]


def _key(row: dict[str, Any]) -> str:
    pub = row.get("publication_number") or row.get("pub_number")
    if pub:
        return str(pub).replace(" ", "")
    link = row.get("stable_url") or row.get("link") or row.get("source_hint_url") or row.get("cnipa_qr_or_hint_url")
    if link:
        return str(link)
    return str(row.get("title") or row.get("input_title") or "")[:120]


def _load_existing(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"generated_at": None, "query_terms": [], "hits": []}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _normalize_hit(hit: dict[str, Any]) -> dict[str, Any]:
    pub = hit.get("publication_number") or hit.get("pub_number")
    status = hit.get("verification_status") or "unverified"
    raw_url = hit.get("stable_url") or hit.get("link")
    stable_url = raw_url if status in VERIFIED_STATUSES else None
    source_hint_url = hit.get("source_hint_url") or hit.get("cnipa_qr_or_hint_url")
    if not source_hint_url and raw_url and status not in VERIFIED_STATUSES:
        source_hint_url = raw_url
    return {
        "publication_number": pub,
        "title": hit.get("title") or hit.get("input_title"),
        "abstract": hit.get("abstract"),
        "applicant_or_author": hit.get("applicant_or_author") or hit.get("applicant"),
        "publication_date": hit.get("publication_date"),
        "source_origin": hit.get("source_origin") or "cnipa_epub",
        "stable_url": stable_url,
        "link": stable_url,
        "source_hint_url": source_hint_url,
        "google_patents_url": hit.get("google_patents_url"),
        "verification_status": status,
        "query_trace": hit.get("query_trace"),
        "same_points": hit.get("same_points"),
        "distinguishing_points": hit.get("distinguishing_points"),
        "usable_distinguishing_features": hit.get("usable_distinguishing_features"),
        "notes": hit.get("notes"),
    }


def _merge_link_result(hit: dict[str, Any], link_result: dict[str, Any]) -> dict[str, Any]:
    out = dict(hit)
    status = link_result.get("verification_status")
    if status:
        out["third_party_verification_status"] = status
    out["verification_time"] = link_result.get("verification_time") or out.get("verification_time")
    out["observed_title"] = link_result.get("observed_title") or out.get("observed_title")
    out["google_patents_url"] = link_result.get("google_patents_url") or out.get("google_patents_url")
    out["verification_error"] = link_result.get("error") or out.get("verification_error")
    if status in VERIFIED_STATUSES:
        out["verification_status"] = status
        out["stable_url"] = link_result.get("stable_url") or link_result.get("link")
        out["link"] = out["stable_url"]
        out["source_origin"] = "google_patents" if out.get("stable_url") and "patents.google.com" in out["stable_url"] else out.get("source_origin")
    elif not out.get("stable_url"):
        if status == "third_party_not_indexed":
            out["verification_status"] = "third_party_not_indexed"
        elif status == "failed":
            out["verification_status"] = "failed"
    return out


def build_dossier(
    case_dir: Path,
    hits: list[dict[str, Any]],
    link_results: list[dict[str, Any]],
    query_terms: list[str],
    note: str | None,
) -> dict[str, Any]:
    case_dir.mkdir(parents=True, exist_ok=True)
    dossier_path = case_dir / "prior_art_dossier.json"
    existing = _load_existing(dossier_path)

    rows_by_key = {_key(x): x for x in existing.get("hits", []) if _key(x)}
    for hit in hits:
        norm = _normalize_hit(hit)
        rows_by_key[_key(norm)] = {**rows_by_key.get(_key(norm), {}), **norm}

    links_by_key = {_key(x): x for x in link_results if _key(x)}
    for key, result in links_by_key.items():
        base = rows_by_key.get(key) or _normalize_hit(result)
        rows_by_key[key] = _merge_link_result(base, result)

    all_terms = list(dict.fromkeys([*(existing.get("query_terms") or []), *query_terms]))
    dossier = {
        "generated_at": _now(),
        "query_terms": all_terms,
        "note": note or existing.get("note"),
        "hits": sorted(rows_by_key.values(), key=lambda x: (str(x.get("publication_number") or ""), str(x.get("title") or ""))),
    }
    return dossier


def _status(row: dict[str, Any]) -> str:
    return str(row.get("verification_status") or "unverified")


def _md_table(rows: list[dict[str, Any]]) -> str:
    lines = [
        "| 文献 | 标题 | 来源状态 | 稳定 URL / 待复核 | 摘要/备注 |",
        "|------|------|----------|-------------------|-----------|",
    ]
    for row in rows:
        doc_id = row.get("publication_number") or "-"
        title = str(row.get("title") or "-").replace("|", " ")
        status = _status(row)
        url = row.get("stable_url") or row.get("link")
        if not url:
            url = "未核验；见 source_hint_url" if row.get("source_hint_url") else "未核验"
        abstract = str(row.get("abstract") or row.get("notes") or row.get("verification_error") or "").replace("|", " ")
        if len(abstract) > 120:
            abstract = abstract[:117] + "..."
        lines.append(f"| {doc_id} | {title} | `{status}` | {url} | {abstract or '-'} |")
    return "\n".join(lines)


def write_outputs(case_dir: Path, dossier: dict[str, Any], note: str | None) -> None:
    hits = dossier.get("hits", [])
    verified = [x for x in hits if _status(x) in VERIFIED_STATUSES]
    unverified = [x for x in hits if _status(x) not in VERIFIED_STATUSES]
    counts = Counter(_status(x) for x in hits)

    (case_dir / "prior_art_dossier.json").write_text(
        json.dumps(dossier, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    summary = "\n".join(f"- `{k}`: {v}" for k, v in sorted(counts.items())) or "- 无命中"
    md = (
        "# 查新证据包\n\n"
        f"- 生成时间：{dossier['generated_at']}\n"
        f"- 检索词：{', '.join(dossier.get('query_terms') or []) or '未记录'}\n"
        f"- 备注：{note or dossier.get('note') or '无'}\n\n"
        "## 来源状态统计\n\n"
        f"{summary}\n\n"
        "## 命中文献\n\n"
        f"{_md_table(hits)}\n"
    )
    (case_dir / "prior_art_dossier.md").write_text(md, encoding="utf-8")

    pos = (
        "# 阳性对照 / 种子文献候选\n\n"
        "以下为已完成稳定来源复核的候选。是否足以作为“高相关阳性对照”，仍须由 Agent 根据本案技术特征逐项判断；正式查新报告至少需要 3 条高相关阳性对照。\n\n"
        f"{_md_table(verified)}\n"
    )
    (case_dir / "positive_controls.md").write_text(pos, encoding="utf-8")

    unv = (
        "# 未核验来源清单\n\n"
        "下列条目不得作为已核验公开源写入交底书 1.1。若影响 A/B/C 结论，应触发 CNIPA PSS、代理人或人工复核。\n\n"
        f"{_md_table(unverified)}\n"
    )
    (case_dir / "unverified_sources.md").write_text(unv, encoding="utf-8")

    log = (
        "\n\n## 查新记录\n\n"
        f"- 时间：{dossier['generated_at']}\n"
        f"- 检索词：{', '.join(dossier.get('query_terms') or []) or '未记录'}\n"
        f"- 命中数：{len(hits)}\n"
        f"- 已核验：{len(verified)}\n"
        f"- 未核验：{len(unverified)}\n"
        f"- 备注：{note or '无'}\n"
    )
    with (case_dir / "query_log.md").open("a", encoding="utf-8") as f:
        f.write(log)


def _terms_from_args(values: list[str]) -> list[str]:
    terms: list[str] = []
    for value in values:
        terms.extend([x.strip() for x in re.split(r"[,，;；\n]+", value) if x.strip()])
    return terms


def main(argv: list[str] | None = None) -> int:
    _ensure_utf8_stdio()
    parser = argparse.ArgumentParser(description="Build/update case-level prior-art dossier files.")
    parser.add_argument("--case-dir", required=True, help="Project/case directory where dossier files are written.")
    parser.add_argument("--hits", help="JSON array or transcript containing EPUB_HITS_JSON.")
    parser.add_argument("--links", help="JSON array or transcript containing PATENT_LINKS_JSON.")
    parser.add_argument("--query", action="append", default=[], help="Query terms used in this run. Repeatable.")
    parser.add_argument("--note", default=None)
    args = parser.parse_args(argv)

    try:
        hits = _load_jsonish(_read_text(args.hits), ("EPUB_HITS_JSON:",)) if args.hits else []
        link_results = _load_jsonish(_read_text(args.links), ("PATENT_LINKS_JSON:",)) if args.links else []
        terms = _terms_from_args(args.query)
        case_dir = Path(args.case_dir).expanduser().resolve()
        dossier = build_dossier(case_dir, hits, link_results, terms, args.note)
        write_outputs(case_dir, dossier, args.note)
    except Exception as e:
        print("PRIOR_ART_DOSSIER_ERROR:", e, file=sys.stderr)
        return 1

    print(f"PRIOR_ART_DOSSIER: case_dir={case_dir} hits={len(dossier.get('hits', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
