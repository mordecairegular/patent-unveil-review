# 仓库结构说明

## 设计原则

- **聚焦主流程**：工程方法、软件系统、数据处理、控制测算、工程仿真/测算工具类发明专利。
- **有限结构辅助**：结构/机械材料只做文字、附图标记和格式辅助，不做专利点挖掘或创造性评估。
- **证据先于结论**：查新结果须有来源状态、稳定 URL 或待复核说明，不能把候选页面当成已核验证据。
- **交付可追溯**：交底书、查新 dossier、交付检查记录和迭代记录随案件目录保存。

## 目录一览

| 路径 | 说明 |
|------|------|
| `SKILL.md` | 入口：适用范围、触发条件、步骤顺序、工具表和自用检查清单 |
| `prompts/intake.md` | Step 1：路线分流、方案成熟度预检、结构有限辅助限制 |
| `prompts/project_scan.md` | Step 2：项目文档与代码扫描，Office 文档先转 Markdown |
| `prompts/patent_points_analyzer.md` | Step 3-4：候选点、授权可行性初筛、方案成熟度与保护组合建议 |
| `prompts/prior_art_search.md` | Step 5：CNIPA EPUB 优先查新、稳定来源复核、A/B/C/D 分级 |
| `prompts/disclosure_builder.md` | Step 7：交底书结构、四客体保护思路、图示和命名规则 |
| `prompts/disclosure_self_check.md` | Step 8：内部自检与 PASS/WARN/FAIL 交付门禁 |
| `prompts/iteration_context.md` | 迭代意图识别、命名、修订记录规则 |
| `prompts/merger.md` | 新材料增量合并 |
| `prompts/correction_handler.md` | 对话纠错与事实修正 |
| `prompts/template_reference.md` | 交底书章节范例、公式/mermaid 体例、四客体模板 |
| `references/method_system_patent_guide.md` | 工程方法与软件系统类专利撰写参考 |
| `references/structural_patent_requirements.md` | 结构有限辅助参考，不用于创造性评估 |
| `references/legal_sources.md` | 法源索引 |
| `tools/` | CNIPA 查新、公开页验证、mermaid/DOCX 转换、dossier、交付日志等脚本 |
| `templates/patent_formula_manifest.yaml` | 关键公式 manifest 模板，用于公式编号、量纲校核和 DOCX 数学 QA |
| `examples/` | 脱敏示例原材料；正式输出应写入用户案件目录 |

## 用户产出约定

推荐路径：

```text
outputs/{案件标识}/
```

凡向用户交付的交底书 `.md` / `.docx` 文件名须为：

```text
{案件名}_{YYYYMMDDHHmmss}.md
{案件名}_{YYYYMMDDHHmmss}.docx
```

首次定稿和迭代稿均适用，不默认覆盖旧稿。
