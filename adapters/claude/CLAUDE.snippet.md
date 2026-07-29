## Patent workflow

- For Chinese engineering/software patent mining, search, drafting, attorney-comment revision, or delivery QA, use the `patent-unveil-review` skill.
- Treat the directory containing its `SKILL.md` as `SKILL_ROOT`.
- Keep case outputs from different agents separate with a timestamp and `_claude` producer suffix; do not overwrite Codex or historical outputs.
- Domain rules live in the shared skill. Keep `CLAUDE.md` as a concise router, not a duplicate of the workflow.
