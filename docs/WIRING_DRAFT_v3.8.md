# v3.8 delivery_gate 接线草稿

> 本文件仅供协调者复核后改写到 `SKILL.md` 与 `prompts/disclosure_self_check.md` §8.5；本次不直接修改二者。

## 建议写入 SKILL.md 的交付入口

交底书定稿交付前，必须以 `tools/delivery_gate.py` 作为唯一机器门禁入口：

```text
python tools/delivery_gate.py --case-dir <案件目录> --md <交付.md> --docx <交付.docx> [--manifest <formula_manifest.yaml>] [--numeric-spec <numeric_check.json>]
```

- `FAIL`：不得作为定稿交付，必须修复后重跑。
- `WARN`：可作为阶段稿或带待补项交付，必须在交付检查记录中保留待补项和用户自填清单。
- `PASS`：仅表示机器可校验项已通过，可进入代理人审稿复核；不表示可直接提交专利局。

## 建议写入 disclosure_self_check.md §8.5 的门禁步骤

1. 确认 `.md` 与 `.docx` 同时存在，文件名符合 `{案件名}_{YYYYMMDDHHmmss}`；多 Agent 并行时可追加 `_{producer}`。
2. 确认确认点 3 签核产物、确认点 4 预览确认记录已落盘；如用户明确跳过确认点 4，运行 gate 时传入 `--preview-skipped`。
3. 运行 `tools/delivery_gate.py`，含公式清单时传入 `--manifest`，含关键数值复核时传入 `--numeric-spec`。
4. 以 `DELIVERY_GATE_JSON` 最后一行为准记录状态；非 `FAIL` 才能进入交付对话。
5. 不得把交付检查记录、gate 输出、工具说明或自检清单复制进交底书正文。
