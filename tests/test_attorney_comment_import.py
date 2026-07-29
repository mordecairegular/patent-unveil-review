from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

import attorney_comment_import  # noqa: E402


def test_explicit_numbered_text_preserves_verbatim_items(tmp_path: Path) -> None:
    source = tmp_path / "代理意见.txt"
    source.write_text(
        "总体说明：请逐条处理。\n"
        "1. 请解释变量 P 的来源。\n补充说明仍属于第一条。\n"
        "2、请区分设备侧与并网点边界。\n",
        encoding="utf-8",
    )

    payload = attorney_comment_import.build_payload(
        source,
        source_type="text_file",
        producer="claude",
    )

    assert payload["count"]["status"] == "verified"
    assert payload["count"]["basis"] == "explicit_item_markers"
    assert payload["top_level_count"] == 2
    comments = payload["comments"]
    assert comments[0]["seq"] == "C01"
    assert "总体说明" in comments[0]["text"]
    assert "补充说明仍属于第一条" in comments[0]["text"]
    assert comments[1]["text"] == "请区分设备侧与并网点边界。"
    assert comments[0]["target_confirmation"] == "needs_human"


def test_unnumbered_text_is_one_provisional_comment_by_default(tmp_path: Path) -> None:
    source = tmp_path / "粘贴意见.txt"
    original = "请补充公式来源。\n\n同时说明边界条件。"
    source.write_text(original, encoding="utf-8")

    payload = attorney_comment_import.build_payload(
        source,
        source_type="pasted_text",
        producer="codex",
    )

    assert payload["top_level_count"] == 1
    assert payload["count"]["status"] == "provisional"
    # The canonical JSON preserves the source file's actual CRLF/LF bytes.
    assert payload["comments"][0]["text"] == source.read_bytes().decode("utf-8").strip()


def test_paraphrase_is_labeled_and_cli_writes_canonical_outputs(tmp_path: Path) -> None:
    source = tmp_path / "转述.txt"
    source.write_text("C1：代理人认为要补实施例。", encoding="utf-8")
    out_json = tmp_path / "comments.json"
    out_md = tmp_path / "comments.md"

    result = subprocess.run(
        [
            sys.executable,
            str(TOOLS / "attorney_comment_import.py"),
            "--input",
            str(source),
            "--source-type",
            "user_paraphrase",
            "--producer",
            "codex",
            "--output-json",
            str(out_json),
            "--output-md",
            str(out_md),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert payload["source"]["verbatim_status"] == "transcribed_or_paraphrased"
    assert payload["count"]["status"] == "provisional"
    assert "不能把临时拆分当作代理人原始编号" in out_md.read_text(encoding="utf-8")
