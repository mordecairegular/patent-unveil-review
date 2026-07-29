## Patent workflow

- For Chinese engineering/software patent mining, search, drafting, attorney-comment revision, or delivery QA, use the `patent-unveil-review` skill.
- Treat the directory containing its `SKILL.md` as `SKILL_ROOT`.
- Keep case outputs from different agents separate with a timestamp and `_codex` producer suffix; do not overwrite Claude or historical outputs.
- Domain rules live in the shared skill. Keep this global instruction as a router, not a second copy of the workflow.
