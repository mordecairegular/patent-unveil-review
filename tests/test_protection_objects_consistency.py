from __future__ import annotations

import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
CANON = ROOT / "references" / "method_system_patent_guide.md"
CANON_POINTER = "method_system_patent_guide.md"
START_MARKER = "<!-- protection-objects:start -->"
END_MARKER = "<!-- protection-objects:end -->"
EXPECTED_OBJECTS = [
    "method",
    "system_or_device",
    "electronic_device",
    "computer_readable_storage_medium",
    "computer_program_product",
]

ACTIVE_FILES = (ROOT / "SKILL.md", ROOT / "README.md", ROOT / "docs" / "PRD.md", ROOT / "docs" / "skill-structure.md")
ACTIVE_TREES = (ROOT / "prompts", ROOT / "references", ROOT / "templates")
HISTORICAL_DIR_NAMES = {"archive", "archives", "history", "historical", "legacy"}


def _active_markdown_files() -> list[Path]:
    files = [path for path in ACTIVE_FILES if path.exists()]
    for tree in ACTIVE_TREES:
        files.extend(
            path
            for path in tree.rglob("*.md")
            if not ({part.lower() for part in path.relative_to(ROOT).parts} & HISTORICAL_DIR_NAMES)
        )
    return sorted(set(files))


def _line_hits(path: Path, token: str) -> list[str]:
    return [
        f"{path.relative_to(ROOT)}:{line_no}: {line.strip()}"
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
        if token in line
    ]


def test_protection_objects_canon_is_parseable_and_complete() -> None:
    text = CANON.read_text(encoding="utf-8")
    assert text.count(START_MARKER) == 1
    assert text.count(END_MARKER) == 1
    assert "唯一权威来源" in text

    match = re.search(
        rf"{re.escape(START_MARKER)}\s*```yaml\s*(.*?)\s*```\s*{re.escape(END_MARKER)}",
        text,
        flags=re.DOTALL,
    )
    assert match is not None, "protection-objects canon must be a fenced YAML block between markers"

    policy = yaml.safe_load(match.group(1))
    assert policy == {"default_objects": EXPECTED_OBJECTS, "allow_reduction": True}


def test_machine_readable_policy_exists_only_in_the_canon() -> None:
    violations: list[str] = []
    for path in _active_markdown_files():
        if path == CANON:
            continue
        text = path.read_text(encoding="utf-8")
        if START_MARKER in text or END_MARKER in text or "default_objects:" in text:
            violations.append(str(path.relative_to(ROOT)))

    assert not violations, "duplicate protection-object policy blocks: " + ", ".join(violations)


def test_active_documents_do_not_restore_the_four_object_default() -> None:
    hits = [hit for path in _active_markdown_files() for hit in _line_hits(path, "四客体")]
    assert not hits, "legacy four-object wording remains in active documents:\n" + "\n".join(hits)


def test_default_storage_medium_context_also_includes_program_product() -> None:
    violations: list[str] = []
    context_tokens = ("默认", "保护组合", "保护客体", "保护思路")

    for path in _active_markdown_files():
        lines = path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            if "存储介质" not in line or not any(token in line for token in context_tokens):
                continue
            context = "\n".join(lines[max(0, index - 3) : index + 4])
            if "计算机程序产品" not in context:
                violations.append(f"{path.relative_to(ROOT)}:{index + 1}: {line.strip()}")

    assert not violations, "default combinations omit computer program product:\n" + "\n".join(violations)


def test_other_authority_statements_point_to_the_canon() -> None:
    violations: list[str] = []
    for path in _active_markdown_files():
        if path == CANON:
            continue
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            declares_authority = "唯一权威" in line and ("保护客体" in line or "保护组合" in line)
            if declares_authority and (CANON_POINTER not in line or "§三" not in line):
                violations.append(f"{path.relative_to(ROOT)}:{line_no}: {line.strip()}")

    assert not violations, "protection-object authority statements do not point to the canon:\n" + "\n".join(violations)
