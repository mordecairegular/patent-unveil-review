# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from cnipa_epub_parse import hits_to_jsonable, parse_search_result_html
from patent_link_verify import load_hits, verify_hit
from prior_art_dossier import build_dossier
from prior_art_dossier import main as dossier_main


def test_cnipa_epub_hint_url_is_not_promoted_to_link() -> None:
    html = """
    <html><body><div class="overview-default">
      <div class="item">
        <h1 class="title">一种知识图谱问答方法</h1>
        <div class="qrcode" title="http://epub.cnipa.gov.cn/patent/CN117033608A"></div>
        <dl>
          <dt>申请公布号：</dt><dd>CN117033608A</dd>
          <dt>摘要：</dt><dd>本发明公开了一种知识图谱问答方法。</dd>
        </dl>
      </div>
    </div></body></html>
    """

    rows = hits_to_jsonable(parse_search_result_html(html))

    assert len(rows) == 1
    row = rows[0]
    assert row["pub_number"] == "CN117033608A"
    assert row["link"] is None
    assert row["cnipa_qr_or_hint_url"] == "http://epub.cnipa.gov.cn/patent/CN117033608A"
    assert row["google_patents_url"] == "https://patents.google.com/patent/CN117033608A/zh"
    assert row["verification_status"] == "cnipa_result_page_parsed"
    assert row["source_origin"] == "cnipa_epub"


def test_verify_hit_promotes_matching_google_patents_page() -> None:
    def fake_fetcher(url: str, timeout: float) -> tuple[int | None, str, str | None]:
        return (
            200,
            """
            <html>
              <title>CN117033608A - 一种知识图谱问答方法 - Google Patents</title>
              <body>CN117033608A 一种知识图谱问答方法</body>
            </html>
            """,
            None,
        )

    result = verify_hit(
        {
            "pub_number": "CN117033608A",
            "title": "一种知识图谱问答方法",
            "source_origin": "cnipa_epub",
            "cnipa_qr_or_hint_url": "http://epub.cnipa.gov.cn/patent/CN117033608A",
        },
        fetcher=fake_fetcher,
    )

    assert result.verification_status == "third_party_verified"
    assert result.link == "https://patents.google.com/patent/CN117033608A/zh"
    assert result.stable_url == result.link
    assert result.matched_by == "publication_number"


def test_verify_hit_keeps_404_as_not_indexed() -> None:
    def fake_fetcher(url: str, timeout: float) -> tuple[int | None, str, str | None]:
        return 404, "<html><title>Not Found</title></html>", "HTTPError: 404"

    result = verify_hit({"pub_number": "CN122152969A", "title": "一种测试方法"}, fetcher=fake_fetcher)

    assert result.verification_status == "third_party_not_indexed"
    assert result.link is None
    assert result.stable_url is None


def test_load_hits_accepts_epub_transcript() -> None:
    hits = load_hits('EPUB_HITS_JSON: [{"pub_number":"CN117033608A","title":"测试"}]\n')

    assert hits == [{"pub_number": "CN117033608A", "title": "测试"}]


def test_load_hits_accepts_utf8_bom() -> None:
    hits = load_hits('\ufeff[{"pub_number":"CN117033608A","title":"测试"}]\n')

    assert hits == [{"pub_number": "CN117033608A", "title": "测试"}]


def test_prior_art_dossier_writes_case_files(tmp_path: Path) -> None:
    hits_file = tmp_path / "hits.txt"
    links_file = tmp_path / "links.txt"
    case_dir = tmp_path / "case"
    stable_url = "https://patents.google.com/patent/CN117033608A/zh"

    hits_file.write_text(
        'EPUB_HITS_JSON: [{"pub_number":"CN117033608A","title":"一种知识图谱问答方法",'
        '"cnipa_qr_or_hint_url":"http://epub.cnipa.gov.cn/patent/CN117033608A",'
        '"google_patents_url":"https://patents.google.com/patent/CN117033608A/zh",'
        '"verification_status":"cnipa_result_page_parsed","abstract":"本发明公开了一种知识图谱问答方法。"}]',
        encoding="utf-8",
    )
    links_file.write_text(
        'PATENT_LINKS_JSON: [{"publication_number":"CN117033608A","input_title":"一种知识图谱问答方法",'
        f'"stable_url":"{stable_url}","link":"{stable_url}",'
        '"verification_status":"third_party_verified","observed_title":"CN117033608A - Google Patents"}]',
        encoding="utf-8",
    )

    rc = dossier_main(
        [
            "--case-dir",
            str(case_dir),
            "--hits",
            str(hits_file),
            "--links",
            str(links_file),
            "--query",
            "知识图谱,问答方法",
            "--note",
            "pytest",
        ]
    )

    assert rc == 0
    expected = {
        "prior_art_dossier.json",
        "prior_art_dossier.md",
        "positive_controls.md",
        "unverified_sources.md",
        "query_log.md",
    }
    assert expected == {p.name for p in case_dir.iterdir()}

    dossier = (case_dir / "prior_art_dossier.json").read_text(encoding="utf-8")
    assert '"verification_status": "third_party_verified"' in dossier
    assert stable_url in dossier
    assert "知识图谱" in (case_dir / "query_log.md").read_text(encoding="utf-8")


def test_prior_art_dossier_treats_legacy_epub_link_as_hint(tmp_path: Path) -> None:
    legacy_url = "http://epub.cnipa.gov.cn/patent/CN117033608A"

    dossier = build_dossier(
        tmp_path,
        [
            {
                "pub_number": "CN117033608A",
                "title": "一种知识图谱问答方法",
                "link": legacy_url,
                "verification_status": "cnipa_result_page_parsed",
            }
        ],
        [],
        [],
        None,
    )

    row = dossier["hits"][0]
    assert row["stable_url"] is None
    assert row["link"] is None
    assert row["source_hint_url"] == legacy_url
