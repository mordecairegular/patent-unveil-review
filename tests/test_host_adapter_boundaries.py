from __future__ import annotations

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_core_files_do_not_depend_on_host_specific_skill_variables() -> None:
    roots = [
        ROOT / "SKILL.md",
        ROOT / "INSTALL.md",
        ROOT / "prompts",
        ROOT / "references",
        ROOT / "templates",
        ROOT / "tools",
    ]
    offenders: list[str] = []
    for entry in roots:
        files = [entry] if entry.is_file() else entry.rglob("*")
        for path in files:
            if not path.is_file() or path.suffix.lower() not in {".md", ".py", ".yaml", ".json"}:
                continue
            if "node_modules" in path.parts:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if "CLAUDE_SKILL_DIR" in text:
                offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []


def test_codex_and_claude_adapters_are_thin_and_share_the_core() -> None:
    codex = yaml.safe_load(
        (ROOT / "adapters" / "codex" / "host-profile.yaml").read_text(encoding="utf-8")
    )
    claude = yaml.safe_load(
        (ROOT / "adapters" / "claude" / "host-profile.yaml").read_text(encoding="utf-8")
    )

    assert codex["producer"] == "codex"
    assert claude["producer"] == "claude"
    assert codex["core_logic_location"] == claude["core_logic_location"]
    assert "do not duplicate" in codex["adapter_rule"]
    assert "do not duplicate" in claude["adapter_rule"]

    codex_snippet = (ROOT / "adapters" / "codex" / "AGENTS.snippet.md").read_text(
        encoding="utf-8"
    )
    claude_snippet = (ROOT / "adapters" / "claude" / "CLAUDE.snippet.md").read_text(
        encoding="utf-8"
    )
    assert len(codex_snippet.splitlines()) <= 20
    assert len(claude_snippet.splitlines()) <= 20
    assert "patent-unveil-review" in codex_snippet
    assert "patent-unveil-review" in claude_snippet


def test_attorney_comment_schema_is_valid_json_and_requires_provenance() -> None:
    schema = json.loads(
        (ROOT / "templates" / "attorney_comments.schema.json").read_text(
            encoding="utf-8"
        )
    )

    assert schema["properties"]["source"]["required"] == [
        "type",
        "file",
        "sha256",
        "verbatim_status",
    ]
    assert "target_confirmation" in schema["properties"]["comments"]["items"]["required"]
