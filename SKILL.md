---
name: patent-unveil-review
description: "面向工程方法、软件系统、数据处理、控制与工程测算类中国发明专利的证据型工作流。用于挖掘候选方向、检索和核验现有技术、生成代理人审稿用技术交底书，以及合并材料、纠正事实或按代理批注修订既有交底书；也用于核验公式、数值、MVP、图示和修订证据闭环。结构或机械类仅在已有附图、物理机理与验证依据时提供有限辅助。Use for patent direction mining, prior-art search, Chinese invention disclosure drafting, attorney-comment revision, and delivery QA for engineering methods and software systems."
---

# 工程方法与软件系统类专利交底工作流

## 定位与能力边界

目标：使技术问题、区别特征、效果、实施方案和保护点闭环；使 MVP、公式与关键数值可复核；交付便于代理人继续审稿。不得把输出表述为法律意见、FTO 或授权保证。

结构/机械类仅在已有附图、物理机理和验证依据时提供有限辅助，见 `prompts/intake.md` 与 `references/structural_patent_requirements.md`。具体修改、代理意见或事实纠正进入 `revise`。

将当前 `SKILL.md` 所在目录记为 `SKILL_ROOT`。核心流程不要依赖宿主专用变量；运行命令时用当前宿主解析出的绝对 Skill 根目录替换示例路径。

## 任务路由

先按用户真实意图选择一个模式。已有明确主题、已有稿件或带批注 DOCX 时，不要无理由退回方向挖掘。

| 模式 | 触发意图 | 首要入口 | 必要路径 |
|---|---|---|---|
| `mine` | 从业务、项目、代码或材料中寻找可申请方向 | `prompts/candidate_pool.md` | intake；材料入口先 scan，再做候选池、探针检索和主题终审 |
| `search` | 已有明确方案，只做现有技术检索或证据复核 | `prompts/prior_art_search.md` | 建立查询记录、证据包、逐方向评级与签核记录 |
| `draft` | 已有明确方案，生成技术交底书 | `prompts/intake.md` | intake → scan → analyzer → search → preview → builder → self-check |
| `revise` | 补充材料、纠正事实/公式/表述或处理代理意见 | `prompts/iteration_context.md` | 分派至 merger、correction；代理意见无论来自批注 DOCX、粘贴文字、消息导出、转述或 OCR，均先走 comment closure |
| `full` | 从方向挖掘一直做到正式交付 | `prompts/candidate_pool.md` | T0 主题终审后进入完整 `draft` 路径 |

路由完成后，先完整读取该阶段指定的 prompt，再执行；不要一次加载与当前模式无关的全部资源。

## 全局不变量

- **G1 不编造**：不得编造技术事实、参数、实验或仿真数据、检索命中、来源状态和法律结论；资料不足时明确写待补、待核或暂不评级。
- **G2 新版另存、产线可并存**：交付加时间戳；并行时加 producer。除非用户要求，不覆盖或强制唯一，由用户选择。
- **G3 失败即状态**：检索失败、渠道阻断、零命中或来源未核验只能表述为渠道或证据状态，不得表述为不存在现有技术。
- **G4 正文清洁**：自检过程、Agent 推理、提示词、脚本、来源状态、工作流和 QA 说明不得进入正式交底书正文。
- **G5 双格式交付**：正式交底书同时保存 Markdown 和 DOCX；DOCX 中公式保持可编辑，图示完成渲染。
- **G6 FAIL 阻断**：`delivery_gate.py` 的最终状态为 `FAIL` 时，不得标记为交付完成。
- **G7 迭代不重跑**：迭代任务不得无理由重跑候选池、方向挖掘和完整主流程；只有技术主线实质变化或用户明确要求时才补充分析或查新。
- **G8 代理意见可追溯**：代理意见原文及其来源、作者、编号、锚点和回复关系不得被改写、合并或丢失。来源是转述、OCR 或临时拆分时必须显式标记，不得冒充 DOCX 原始批注。
- **G9 每轮吸收经验**：每次代理意见修订结束时，追加一份轻量经验回写；区分案件事实、可复用规则和可自动化测试。只有去标识化且经复核的通用经验才进入 Skill 规则或回归夹具。

## 执行契约

1. 先识别模式和现有产物，再读取对应 prompt 的 `Purpose / Inputs / Outputs / Must / Must not / Completion criteria` 或等价局部契约。
2. 把 G1–G9 作为所有 prompt 的共同上位规则；阶段细节以对应资源为准。
3. 需要保护客体口径时，完整读取 `references/method_system_patent_guide.md` §三。该处 `protection-objects` 标记块是默认可选保护客体的唯一权威来源；根据技术方案、材料支撑、软件交付方式、查新结果和申请策略允许收缩。
4. 按下表加载法源、结构、证据合同、多模态或商业库 reference；法源以 `references/legal_sources.md` 当前索引为准。
5. 交付前先执行阶段语义自检，再运行统一机器门禁；机器门禁只核验可结构化项目，不替代专业判断。

## Prompt 映射

| 阶段或意图 | 必读文件 | 产出或作用 |
|---|---|---|
| T0 候选池 | `prompts/candidate_pool.md` | 主题边界卡、探针检索、候选主题卡、主题终审 |
| Step 1 边界录入 | `prompts/intake.md` | 路线、技术主题、成熟度与材料边界 |
| Step 2 项目扫描 | `prompts/project_scan.md` | 代码、Office、关键图片和方案证据清单 |
| Step 3–4 候选分析 | `prompts/patent_points_analyzer.md` | 候选点、技术性与授权可行性初筛、查新后回写 |
| Step 5 查新 | `prompts/prior_art_search.md` | 证据包、风险等级与评价状态、区别特征、确认点 3 |
| Step 6 预览 | `prompts/disclosure_preview.md` | 摘要、事实与保护方向确认点 4 |
| Step 7 定稿 | `prompts/disclosure_builder.md`、`prompts/template_reference.md` | 正文、方案骨架、图示、公式、Markdown 与 DOCX |
| Step 8 自检 | `prompts/disclosure_self_check.md` | 语义、支撑、数值、公式、跨视图与交付状态自检 |
| 迭代分派 | `prompts/iteration_context.md` | 选择合并、纠错或代理批注闭环，维护版本与记录 |
| 新材料合并 | `prompts/merger.md` | 增量合并并另存新稿 |
| 事实或表达纠错 | `prompts/correction_handler.md` | 核实意见、修改正文、输出纠正摘要 |
| 代理意见 | `prompts/review_comment_closure.md` | 冻结来源、提取/导入原文、恢复作用范围、处置矩阵、修订、逐条回复与经验回写 |

## Reference 与模板路由

| 需要判断的事项 | 读取资源 |
|---|---|
| 默认保护客体与方法/系统写法 | `references/method_system_patent_guide.md` |
| 当前法源、版本与适用范围 | `references/legal_sources.md` |
| 结构类有限辅助 | `references/structural_patent_requirements.md` |
| 商业专利库核验 | `references/commercial_patent_db_verification.md` |
| 正式正文清洁 | `references/formal_disclosure_cleanliness.md` |
| 跨案件完整工作流 | `references/patent_workflow_lessons_ai_friendly.md` |
| 测量、诊断、定位或状态识别 | `references/technical_evidence_contract.md` 与 `templates/technical_evidence_contract.yaml` |
| 多模态证据、观测粒度和决策逻辑 | `references/observability_and_multimodal_evidence.md`、`templates/evidence_responsibility_matrix.md`、`templates/decision_table.md` |
| 候选主题卡 | `templates/candidate_topic_card.md` |
| 代理回复结构 | `templates/attorney_response_matrix.md` |
| 代理意见规范数据结构 | `templates/attorney_comments.schema.json` |
| 代理意见修订经验回写 | `templates/attorney_revision_lessons.md` |

## 工具入口

先阅读 `tools/README.md` 中对应工具的输入、依赖、标准输出和失败语义。

| 任务 | 工具 |
|---|---|
| Word / PowerPoint 转 Markdown | `tools/docx_to_md.py`、`tools/pptx_to_md.py` |
| CNIPA 与补充检索 | `tools/channel_preflight.py`、`tools/cnipa_epub_search.py`、`tools/gp_xhr_search.py`、`tools/patent_link_verify.py` |
| 查新证据包 | `tools/prior_art_dossier.py` |
| Mermaid、DOCX 与公式 QA | `tools/mermaid_render.py`、`tools/md_to_docx.py`、`tools/qa_docx_math.py` |
| 数值复现 | `tools/qa_numeric_reproduce.py` |
| 代理意见提取/导入 | `tools/docx_comment_extract.py`（批注 DOCX）、`tools/attorney_comment_import.py`（文字、消息导出、转述、OCR） |
| 修订与交付记录 | `tools/iteration_dialog_log.py`、`tools/delivery_check_log.py` |
| 统一交付门禁 | `tools/delivery_gate.py` |

## 交付门禁

正式交底书使用 `{规范化案件名}_{YYYYMMDDHHmmss}.md` 与同名 `.docx`；多 Agent 并行时使用 `{规范化案件名}_{YYYYMMDDHHmmss}_{producer}`。文件哈希可用于来源证据或复现，但不是交底书发布的强制条件。先完成 `prompts/disclosure_self_check.md` 的语义检查，再从 Skill 根目录运行：

```text
python tools/delivery_gate.py --case-dir <案件目录> --md <交付.md> --docx <交付.docx>
```

按案件需要补充公式清单、数值规格、证据合同、确认点或批注参数。代理意见修订应同时提供处置矩阵、回复稿、修订根目录以及可用的基线稿或基线目录，使 C16 检查机器锚点可解析性、C17 检查声称修改与实际差异；缺少基线时按工具输出记录 WARN 或 SKIP，不伪造通过。

读取末行 `DELIVERY_GATE_JSON` 并遵守：

| 内部状态 | 用户可见文本 | 动作 |
|---|---|---|
| `PASS` | 代理人审稿就绪 | 说明该状态不代表可直接提交或保证授权 |
| `WARN` | 阶段稿，存在待补项 | 列明待补项、未覆盖检查和人工复核事项 |
| `FAIL` | 未达到交付条件 | 修复后重跑，不作为定稿交付 |

交付更新检查记录；修订更新对话记录；代理意见轮次另做经验回写。记录不进入正文。

宿主差异只写入 `adapters/codex/` 与 `adapters/claude/`，不得复制专利判断逻辑。

版本历史见 `CHANGELOG.md`。
