---
name: patent-unveil-review
description: "面向工程方法、软件系统、数据处理、控制与工程测算类中国发明专利的证据型工作流：挖掘候选方向、检索并核验现有技术、生成可供代理人审稿的技术交底书，以及合并材料、纠正事实或按代理批注修订既有交底书；交付前对公式、数值、图示与正文清洁做统一机器门禁。结构/机械类仅在已有附图、物理机理与验证依据时提供有限辅助。Use for patent direction mining, prior-art search, Chinese invention disclosure drafting, attorney-comment revision, and delivery QA for engineering methods and software systems."
allowed-tools: Read, Write, Edit, Grep, Glob, WebSearch, Bash
---

# 工程方法与软件系统类专利交底工作流

## 定位与能力边界

目标：使技术问题、区别特征、技术效果、实施方案与保护点闭环；使 MVP、公式与关键数值可复核；交付便于代理人继续审稿。**不**替代专利代理师/律师的新颖性、创造性、侵权或 FTO 法律意见；查新结论仅基于本轮可公开检索到的现有技术，不得表述为授权保证。

本技能只服务三件事，并以此作为功能扩展的准入滤网：①交底书初稿**基础逻辑靠谱**（权利要求一致、联动闭环成立、算法良定义、数值可复现）；②支撑交底书的 **MVP/仿真可运行并通过复核**；③交付的 **`.md`/`.docx` 排版格式合理**。深度多视角评审、法律申请策略由外部 agent/代理人承担，不内置。

结构/机械类仅在用户已有 CAD/Visio 线稿或标注草图、明确物理机理，以及实验/仿真/标准/工程数据依据时提供**有限辅助**（文字撰写、附图标记一致性、权利要求格式检查），不承诺结构类专利点挖掘、创造性评估或 PASS 级交付。涉及装置/结构词时先判断核心创新是「结构本体」还是「测算/评估某结构的方法」：后者仍走方法主线并保留物理锚点，不因结构词自动降为有限辅助。详见 `prompts/intake.md`（Q1.5）与 `references/structural_patent_requirements.md`。

## 任务路由（先按用户真实意图选一个模式）

已有明确主题、已有稿件或带批注 DOCX 时，**不要**无理由退回方向挖掘。

| 模式 | 触发意图 | 首要入口 | 路径 |
|---|---|---|---|
| `mine` | 从业务、项目、代码或材料中寻找可申请方向 | `prompts/candidate_pool.md` | T0：intake（材料入口先 scan）→ 确认点 1 边界卡 → 探针检索 → 候选主题卡 → 确认点 2 终审 |
| `search` | 已有明确方案，只做现有技术检索或证据复核 | `prompts/prior_art_search.md` | 查询记录、证据包、逐方向风险等级与确认点 3 签核 |
| `draft` | 已有明确方案，生成技术交底书 | `prompts/intake.md` | intake → project_scan → patent_points_analyzer → prior_art_search → disclosure_preview（确认点 4）→ disclosure_builder(+template_reference) → disclosure_self_check |
| `revise` | 补充材料、纠正事实/公式/表述或处理代理意见 | `prompts/iteration_context.md` | 分派 merger（新材料合并）/ correction_handler（纠错）；带批注 DOCX 先走 review_comment_closure |
| `full` | 从方向挖掘一直做到正式交付 | `prompts/candidate_pool.md` | T0 终审后进入完整 `draft` 路径 |

**触发关键词**（任一即启用）：专利挖掘 / 专利点 / 技术交底书 / 交底书 / 查新 / 现有技术对比 / 候选池 / 方向挖掘；工程方法、软件系统、数据处理、AI 算法、控制策略、调度、工程测算、仿真评估、识别方法、一致性校核等；或 `/patent-unveil-review`。**迭代按意图识别**：只要用户明显在已有交底书/上一轮输出上改章节、补材料、修正参数或处理代理意见，即进入 `revise`，无需固定关键词，也不必追问是否迭代。

路由后先完整 `Read` 该阶段指定的 prompt 再执行；不要一次加载与当前模式无关的全部资源。

## 全局不变量（G1–G8，所有 prompt 的共同上位规则）

- **G1 不编造**：不得编造技术事实、参数、实验/仿真数据、检索命中、来源状态与法律结论；资料不足时明确写待补、待核或暂不评级。
- **G2 新版另存、可并存**：交付加时间戳 `{规范化案件名}_{YYYYMMDDHHmmss}`，**不覆盖**旧稿（除非用户明确要求）；多来源并行时加 `_{producer}` 区分，由用户选用，不强制唯一「终稿」，也不把文件哈希作为发布强制条件。
- **G3 失败即状态**：检索失败、渠道阻断、零命中或来源未核验只能表述为**渠道/证据状态**，不得表述为「不存在现有技术」。
- **G4 正文清洁**：自检过程、Agent 推理、提示词、脚本名、来源状态、检索过程与 QA 说明**不得**进入正式交底书正文；只写入交接说明/交付检查记录/证据包。见 `references/formal_disclosure_cleanliness.md`。
- **G5 双格式交付**：正式交底书同时保存 Markdown 与 DOCX；DOCX 中公式为可编辑 OMML，图示已渲染。
- **G6 FAIL 阻断**：`tools/delivery_gate.py` 最终状态为 `FAIL` 时不得标记为交付完成。
- **G7 迭代不重跑**：迭代任务不得无理由重跑候选池、方向挖掘或完整主流程；仅技术主线实质变化或用户明确要求时才补充分析/查新。
- **G8 代理意见可追溯**：代理意见原文及其来源、编号、锚点与回复关系不得被改写、合并或丢失；来源为转述或 OCR 时须显式标记，不得冒充 DOCX 原始批注。

## 执行契约

1. 先识别模式与现有产物，再 `Read` 对应 prompt 的用途、输入、输出、Must/Must-not 与完成判据。
2. 把 G1–G8 作为共同上位规则；各阶段细节与逐项自检以对应 prompt 及 `prompts/disclosure_self_check.md` §8 为准，不在本文件重复维护。
3. 需要保护客体口径时先 `Read` `references/method_system_patent_guide.md` §三：其中 `protection-objects` 标记块是**默认可选**保护客体的唯一权威来源，按技术方案、材料支撑、软件交付方式、查新结果与申请策略**允许收缩**（五客体是菜单、非强制凑满）。
4. 交付前先做阶段语义自检（§8），再跑统一机器门禁；门禁只核验可结构化项，不替代专业判断。

## Prompt 映射

| 阶段 / 意图 | 必读文件 | 产出或作用 |
|---|---|---|
| T0 候选池 | `prompts/candidate_pool.md`（模板 `templates/candidate_topic_card.md`）| 主题边界卡、探针检索、候选主题卡、主题终审（确认点 1/2）|
| Step 1 边界录入 | `prompts/intake.md` | 路线、技术主题、成熟度与材料边界 |
| Step 2 项目扫描 | `prompts/project_scan.md` | 代码、Office（先转 md）、关键图片与方案证据清单 |
| Step 3–4 候选分析 | `prompts/patent_points_analyzer.md` | 候选点、技术性与授权可行性初筛、查新后回写 |
| Step 5 查新 | `prompts/prior_art_search.md` | 证据包、风险等级与评价状态、区别特征、确认点 3 |
| Step 6 预览 | `prompts/disclosure_preview.md` | 摘要预览、事实与保护方向确认点 4（默认必做）|
| Step 7 定稿 | `prompts/disclosure_builder.md` + `prompts/template_reference.md` | 正文、方案骨架、图示、公式、Markdown 与 DOCX |
| Step 8 自检 | `prompts/disclosure_self_check.md` | 语义、支撑、数值、公式、跨视图与交付状态自检 |
| 迭代分派 | `prompts/iteration_context.md` | 选择合并/纠错/代理批注闭环，维护版本与对话记录 |
| 新材料合并 | `prompts/merger.md` | 增量合并并另存新稿 |
| 事实/表达纠错 | `prompts/correction_handler.md` | 逐条分诊外部意见、修改正文、输出纠正摘要 |
| 代理批注闭环 | `prompts/review_comment_closure.md`（`tools/docx_comment_extract.py`）| 批注提取、作用范围、overlay、处置矩阵（CLOSED/PARTIAL/OPEN）、逐条回复 |

## Reference 与模板路由

| 需要判断的事项 | 读取资源 |
|---|---|
| 默认保护客体与方法/系统写法 | `references/method_system_patent_guide.md`（§三 为唯一权威）|
| 法源、版本与适用范围 | `references/legal_sources.md`（勿把法规全文抄进正文）|
| 结构类有限辅助 | `references/structural_patent_requirements.md` |
| 商业专利库核验 | `references/commercial_patent_db_verification.md` |
| 正式正文清洁 | `references/formal_disclosure_cleanliness.md` |
| 跨案件完整工作流 | `references/patent_workflow_lessons_ai_friendly.md` |
| 测量/诊断/定位/状态识别 | `references/technical_evidence_contract.md`、`templates/technical_evidence_contract.yaml` |
| 多模态证据、观测粒度与决策逻辑 | `references/observability_and_multimodal_evidence.md`、`templates/evidence_responsibility_matrix.md`、`templates/decision_table.md` |
| 候选主题卡 / 代理回复矩阵 / 预览确认 | `templates/candidate_topic_card.md`、`templates/attorney_response_matrix.md`、`templates/preview_confirmation.template.md` |

## 工具入口

先读 `tools/README.md` 了解各工具输入、依赖、标准输出与失败语义；`pip install -r requirements.txt`。命令均从 Skill 根目录以相对路径运行（不依赖宿主专用路径变量）。

| 任务 | 工具 |
|---|---|
| Word/PowerPoint → Markdown（扫描前）| `tools/docx_to_md.py`、`tools/pptx_to_md.py` |
| CNIPA 与补充检索 | `tools/channel_preflight.py`、`tools/cnipa_epub_search.py`、`tools/gp_xhr_search.py`、`tools/patent_link_verify.py` |
| 查新证据包 | `tools/prior_art_dossier.py` |
| Mermaid、DOCX 与公式 QA | `tools/mermaid_render.py`、`tools/md_to_docx.py`、`tools/qa_docx_math.py` |
| 数值复现 | `tools/qa_numeric_reproduce.py` |
| 代理批注提取 | `tools/docx_comment_extract.py` |
| 迭代对话 / 交付检查留档 | `tools/iteration_dialog_log.py`、`tools/delivery_check_log.py` |
| 统一交付门禁 | `tools/delivery_gate.py` |

**公式/图示/Word QA 硬约束**（细则见 `tools/README.md` 与 `prompts/template_reference.md`）：关键公式先建 `templates/patent_formula_manifest.yaml`（字段含 `owner_step`），正文只引用清单公式、不临场重拼；公式源为合法 LaTeX（`\eta`、`\mathrm{}`、`\frac{}{}`、`\sum`）；多下划线英文字段标签不是公式，禁止转下标。`.docx` 交付前必过 `qa_docx_math.py`（公式残留、未渲染 mermaid、代码样式、媒体数量、正式正文流程说明）；任一 mermaid 块渲染失败只保留 Markdown 排障稿、不出定稿 Word。含关键量化效果的稿件按 `disclosure_self_check.md` §8.2 做数值二次核对。

## 交付门禁

正式交底书用 `{规范化案件名}_{YYYYMMDDHHmmss}.md` 与同名 `.docx`（多来源并行加 `_{producer}`）。先完成 `disclosure_self_check.md` §8 语义自检，再从 Skill 根目录运行：

```text
python tools/delivery_gate.py --case-dir <案件目录> --md <交付.md> --docx <交付.docx>
```

按需补 `--manifest`（公式清单）、`--numeric-spec`（数值复现）、`--evidence-contract`（技术证据合同）、`--preview-skipped`（用户明确跳过确认点 4）等参数。读取末行 `DELIVERY_GATE_JSON` 并按下表处理；机器门禁只覆盖可结构化项（占位符、计数闭合、字段标签、公式段落残留、命名规范、确认点产物、数值复现、版本自报等），语义类检查（逻辑闭环、权利要求一致性、公式正确性）仍由 §8 与人工/Agent 完成。

| 内部状态 | 用户可见文本 | 动作 |
|---|---|---|
| `PASS` | 代理人审稿就绪 | 说明该状态不代表可直接提交专利局或保证授权 |
| `WARN` | 阶段稿，存在待补项 | 列明待补项、未覆盖检查与人工复核事项，并写入交付检查记录 |
| `FAIL` | 未达到交付条件 | 修复后重跑，不作为定稿交付 |

每次交付追加 `交底书交付检查记录.md`（`tools/delivery_check_log.py`）；迭代追加 `交底书修订对话记录.md`（`tools/iteration_dialog_log.py`）。记录不进入正文。

版本历史见 `CHANGELOG.md`。
