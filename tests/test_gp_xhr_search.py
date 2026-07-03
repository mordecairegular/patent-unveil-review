from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import cnipa_epub_search  # noqa: E402
import gp_xhr_search  # noqa: E402


def test_hits_from_parses_xhr_payload() -> None:
    data = {
        "results": {
            "total_num_results": 2,
            "cluster": [
                {
                    "result": [
                        {
                            "patent": {
                                "title": " 一种测试方法 ",
                                "publication_number": "CN123456789A",
                                "snippet": "摘要内容",
                                "assignee": "某公司",
                                "inventor": "张三",
                                "filing_date": "2025-01-01",
                                "publication_date": "2025-06-01",
                                "grant_date": "",
                            }
                        },
                        {"patent": {"title": "无公开号条目", "publication_number": "", "snippet": ""}},
                    ]
                }
            ],
        }
    }
    hits, total = gp_xhr_search.hits_from(data)
    assert total == 2
    assert len(hits) == 2
    assert hits[0]["pub_number"] == "CN123456789A"
    assert hits[0]["title"] == "一种测试方法"
    assert hits[0]["google_patents_url"] == "https://patents.google.com/patent/CN123456789A/zh"
    assert hits[0]["verification_status"] == "google_xhr_search_result"
    assert hits[0]["source_origin"] == "google_patents_xhr"
    assert hits[1]["pub_number"] is None
    assert hits[1]["google_patents_url"] is None


def test_hits_from_handles_empty_payload() -> None:
    assert gp_xhr_search.hits_from({}) == ([], None)


def test_gp_xhr_search_requires_query() -> None:
    with pytest.raises(SystemExit) as excinfo:
        gp_xhr_search.main([])
    assert excinfo.value.code == 2


def test_cnipa_epub_search_help_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    # --help 必须被识别为帮助选项，而不是被当作检索词提交到公布站
    with pytest.raises(SystemExit) as excinfo:
        cnipa_epub_search.main(["--help"])
    assert excinfo.value.code == 0
    assert "usage" in capsys.readouterr().out.lower()


def test_cnipa_epub_search_no_terms_returns_2() -> None:
    assert cnipa_epub_search.main([]) == 2
