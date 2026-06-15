---
name: patent-unveil-review
description: "面向工程方法、软件系统、数据处理与控制测算类中国发明专利的授权可行性审查与技术交底书生成流程：扫描代码、算法、工程测算工具或方案文档，挖掘候选专利点，按技术问题、区别特征、技术效果、实施支撑和方案成熟度进行初筛，联网查新并回写风险等级，生成可供代理人审稿的交底书。结构/机械类专利仅提供有限辅助，需用户自备工程附图与物理机理依据。Use for engineering-method, software-system, data-processing, control, simulation, or calculation patentability review, prior-art search, disclosure drafting, and iterative attorney-review handoff."
version: "3.0.0"
user-invocable: true
argument-hint: "[可选：项目路径或技术主题关键词]"
allowed-tools: Read, Write, Edit, Grep, Glob, WebSearch, Bash
---

# 工程方法与软件系统类专利授权可行性审查与交底书生成

本技能聚焦 **工程方法、软件系统、数据处理、控制测算、工程仿真/测算工具**类中国发明专利的授权可行性审查：在用户提供代码、算法、工具原型、工程数据、方案文档或论文后，辅助识别具备明确技术问题、区别技术特征、可论证技术效果、实施支撑和方案成熟度的专利方向，并生成**可供代理人审稿**的技术交底书初稿。分步指令在 **`prompts/`**，每步执行前 **`Read`** 对应文件，与步骤的对照见「Prompt 文件映射」。

本技能不替代专利代理师或律师出具正式新颖性、创造性、侵权或 FTO 法律意见；查新结论仅基于本轮可公开检索到的现有技术。

**v2.1 新增**：授权可行性初筛、查新 A/B/C/D 决策分级、查新后回写推荐方向、PASS/WARN/FAIL 代理人审稿门禁，以及案件目录随行的 **`交底书交付检查记录.md`**。

**v2.2 新增**：查新证据模型、来源状态分级、Google Patents 稳定页验证、阳性对照门禁、案件级 `prior_art_dossier` 留档；CNIPA EPUB 结果仅作候选发现，不再把二维码/猜测详情页当作可复核 URL。

**v3.0 变更**：本技能取消此前“软件/结构双模式并列”设计，收缩为工程方法与软件系统类主流程。结构/机械类专利降为**有限辅助模式**：仅在用户已有 CAD/Visio 线稿或标注草图、明确物理机理，以及实验/仿真/标准/工程数据依据时，辅助文字撰写、附图标记一致性和权利要求格式检查；不承诺结构类专利点挖掘、创造性评估或 PASS 级交付。

## 环境与约定

- **语言**：默认与用户语种一致；专利与法律术语采用行业常用表述。
- **适用范围**：工程方法、软件系统、数据处理、控制测算、工程仿真/测算工具类中国发明专利。结构/机械类进入「有限辅助」通道，详见 `prompts/intake.md`。
- **默认保护组合**：方法权利要求 + 系统/装置权利要求 + 电子设备权利要求 + 计算机可读存储介质权利要求；如查新或材料支撑不足，可收缩为方法+系统或单一系统方案。
- **图示定稿（Step 7）**：
  - **主流程**：**3.2**/**3.4** 用 fenced **mermaid**；执行方式、**`mmdc`** 安装与降级规则见下表「交底书定稿交付」行及 **`tools/README.md`**。
  - **结构有限辅助**：附图由用户提供 CAD/Visio 线稿或标注草图；本技能仅辅助文字描述和附图标记一致性检查，不生成结构附图，不输出 PASS。详见 **`references/structural_patent_requirements.md`**。

---

## 触发条件

在用户使用以下任一方式时启用本技能：

- 明确提及：专利挖掘、专利点、技术交底书、交底书、专利交底书、查新、现有技术对比等
- **主流程技术关键词**：工程方法、软件系统、数据处理、AI/算法、控制策略、调度方法、工程测算、仿真评估、识别方法、一致性校核、文档生成与质量校验等
- **结构/机械类材料**：当用户提及装置、连接器、零部件、结构设计、附图标记、剖视图、装配图等时，本技能进入有限辅助模式——提示用户准备附图和物理机理依据，不主动执行结构类专利点挖掘或创造性评估。
- 斜杠或简短指令：如 `/patent-unveil-review`、`/工程方法专利`、`/交底书`
- **迭代模式（按意图识别）**：当用户意图明显是在**已有交底书或上一轮输出**上继续工作（如改章节、补实施例、补材料、修正参数/事实、调整表述等），**无需**用户写出「迭代」等固定词，也**不必**询问是否进入迭代——Agent 应 **`Read`** **`prompts/iteration_context.md`**，再 **`Read`** `prompts/merger.md`（侧重**新材料、扩展合并**）或 `prompts/correction_handler.md`（侧重**纠错、与事实或风格不符**），**严格按该文件开头的「执行门禁」**（优先执行，不可跳过）**做完合并或纠正**，**另存为新文件**：**`{案件名}_{YYYYMMDDHHmmss}.md`** 与同名 **`.docx`**（与首次定稿同一命名规则，见 **`disclosure_builder.md` §7.3 第 5 点**），**不覆盖**旧稿（除非用户明确要求）。**禁止**在迭代意图已成立时默认回到 Step 3–4 专利点全文分析（除非用户明确要求重新挖掘专利点）。对话中**已出现**交底书路径、附件或上文刚交付的草稿时，优先按迭代处理。

---

## 工具与数据来源

按任务选用能力；具体工具名称以当前 Agent 环境为准。

若扫描范围内含 **Word（.docx）** 或 **PowerPoint（.pptx）**，须在 Step 2 纳入阅读前用本仓库 **`docx_to_md.py`** / **`pptx_to_md.py`** 转为 Markdown；依赖 **`pip install -r requirements.txt`**，命令与说明见下表对应行。

### 常见任务与建议方式

| 任务 | 建议方式 |
|------|----------|
| 加载分步指令 | **`Read`** → `${CLAUDE_SKILL_DIR}/prompts/*.md`，见下表 |
| 读代码、设计文档、PDF、图片 | 文件读取工具；大仓库先用搜索/语义检索定位再精读 |
| Word（.docx）→ Markdown + 抽取图片（扫描前） | `Bash` → `python3 ${CLAUDE_SKILL_DIR}/tools/docx_to_md.py --input {path}.docx --output {dir}/{name}.md`；图片默认写入与 `.md` 同级的 `{name}_media/`；需 `pip install -r requirements.txt`（含 mammoth）；复杂版式可改由所内导出 PDF/MD 再扫 |
| PowerPoint（.pptx）→ Markdown + 抽取图片（扫描前） | `Bash` → `python3 ${CLAUDE_SKILL_DIR}/tools/pptx_to_md.py --input {path}.pptx --output {dir}/{name}.md`；默认 `{name}_media/`；需 `pip install -r requirements.txt`（含 python-pptx）；**旧版 .ppt 不支持**，请先另存为 `.pptx`；图表/SmartArt 等若未以图片形状嵌入则可能仅能从备注或另行导出补全 |
| 罗列目录、按名找文件 | 目录列举 / 按文件名搜索 |
| 联网查新（Step 5） | 执行前 **`Read`** `prompts/prior_art_search.md`。**中国专利公布公告**：优先 **`Bash`** 运行 `cnipa_epub_search.py`；**须在生成命令前**归纳 **2～8 个相关度高的语义块**；**执行时须分多次调用**，**每次仅传一个**词块，**自行按 `pub_number` 合并**多轮 `EPUB_HITS_JSON`。CNIPA EPUB 输出默认是 `cnipa_result_page_parsed` 候选，`cnipa_qr_or_hint_url` 不得写作稳定 URL；高相关条目须用 `patent_link_verify.py` / Google Patents / Espacenet / WIPO / CNIPA PSS 复核。案件目录须用 `prior_art_dossier.py` 或等价手工留 `prior_art_dossier.*`、`query_log.md`、`positive_controls.md`、`unverified_sources.md`；异常或证据不足按 D/partial-D，不伪造可授权结论 |
| 交底书定稿交付（**须同时** .md + .docx） | **3.2** 系统框图与 **3.4** 流程图均用 fenced ``mermaid``，**不要** ASCII 文字流程图/框图。定稿执行 **`tools/mermaid_render.py`**：mermaid 转 PNG（失败块保留围栏）后默认生成同名 **.docx**；若 Word 失败，按 stderr 提示手动运行 **`md_to_docx.py`**。详见 **`tools/README.md`** |
| 保存交底书路径 | 写入用户指定路径；未指定时可建议 `./outputs/{案件标识}/`；**凡交付的** `.md` / `.docx` 须为 **`{案件名}_{YYYYMMDDHHmmss}`**（§7.3 第 5 点，**含首次定稿与迭代**），勿默认覆盖旧稿；`outputs/` 整目录默认由 `.gitignore` 忽略 |
| 迭代对话留档 | 每轮 **merger / correction** 交付后，在案件目录追加 **`交底书修订对话记录.md`**（**`tools/iteration_dialog_log.py`** 或等价手工），见 **`prompts/iteration_context.md`** |
| 交付检查留档 | 每次向用户落盘交付 `.md`/`.docx` 后，在案件目录追加 **`交底书交付检查记录.md`**（**`tools/delivery_check_log.py`** 或等价手工），记录 PASS/WARN/FAIL、交付文件、待补项和检查摘要；见 **`disclosure_self_check.md` §8.5** |
| 结构有限辅助附图合规参考 | **`Read`** → `${CLAUDE_SKILL_DIR}/references/structural_patent_requirements.md`，获取 CNIPA 附图规范、结构权利要求格式和部件编号规范；该参考不用于创造性评估 |
| 法规来源索引 | 需要核对法源、版本和适用范围时 **`Read`** → `${CLAUDE_SKILL_DIR}/references/legal_sources.md`；不要把法规全文复制进交底书正文 |

---

## Prompt 文件映射

| 步骤 | 文件 | 用途 |
|------|------|------|
| Step 1 | `prompts/intake.md` | 边界与输入问题 |
| Step 2 | `prompts/project_scan.md` | 项目文档扫描；**须**对 `.docx`/`.pptx` 先转换再读（见该文件「Office 文档」节）；独立图片目录可跳过 |
| Step 3–4 | `prompts/patent_points_analyzer.md` | 候选专利点、融合选定、授权可行性初筛；查新后须回写复核 |
| Step 5 | `prompts/prior_art_search.md` | 联网查新、A/B/C/D 决策分级、可用区别特征提取 |
| Step 6 | `prompts/disclosure_preview.md` | 全文前的摘要预览 |
| Step 7 | `prompts/disclosure_builder.md` + `prompts/template_reference.md` | 交底书结构、脱敏、**符号与公式体例（§7.7）**与图示规范；**mermaid 与 3.4.1 符号/公式范例在 template_reference** |
| Step 8 | `prompts/disclosure_self_check.md` | 内部自检，不写入正文 |
| 迭代 | `prompts/iteration_context.md` | 迭代意图、落盘命名、**修订对话记录 md**（含对话/记录时间） |
| 迭代 | `prompts/merger.md` | 新材料增量合并；**文首含门禁**；输出 `{案件名}_{时间戳}.md`/`.docx` |
| 迭代 | `prompts/correction_handler.md` | 对话纠正；**文首含门禁**；输出 `{案件名}_{时间戳}.md`/`.docx` |
| 参考 | `references/structural_patent_requirements.md` | 结构有限辅助：CNIPA 附图规范、结构权利要求格式、部件编号规范；不用于创造性评估 |
| 参考 | `references/method_system_patent_guide.md` | 工程方法、软件系统、四客体保护组合与常见授权风险参考 |
| 参考 | `references/legal_sources.md` | 专利法、实施细则、审查指南 2023 及 2025 修改决定等法源索引 |

---

## 主流程（执行顺序）

1. **`Read`** `intake.md` → 执行 Step 1  
2. **`Read`** `project_scan.md` → 执行 Step 2  
3. **`Read`** `patent_points_analyzer.md` → 执行 Step 3–4，输出候选点和**查新前授权可行性初筛**  
4. **`Read`** `prior_art_search.md` → 执行 Step 5，形成 A/B/C/D 查新结论；随后**回写 Step 3–4 推荐方向、查新风险和可用区别特征**  
5. **`Read`** `disclosure_preview.md` → 执行 Step 6；用户可跳过  
6. **`Read`** `disclosure_builder.md` 与 **`Read`** `template_reference.md` → 执行 Step 7（**首次交付**的 `.md`/`.docx` 亦须 **`{案件名}_{YYYYMMDDHHmmss}`**，§7.3 第 5 点）；交付对话中**须**按 **`disclosure_builder.md` §7.6** 补充「权利要求偏向点」建议交互（**仅对话**，不入正文）  
7. **`Read`** `disclosure_self_check.md` → 内部执行 Step 8，修订后交付；每次落盘交付须在案件目录追加 **`交底书交付检查记录.md`**  

**禁止**：交底书正文中包含「自检清单」章节；自检仅内部使用。

---

## 迭代模式（摘要）

**启用方式**：根据用户**自然语言意图**判断（见上文「触发条件」），**不要求**固定关键词，**默认不**为「是否迭代」打断用户。

- **补充材料 / 扩展章节**或 **§7.6 第五章权利要求书式强化（用户已声明侧重点）**：`Read` → `iteration_context.md` → `merger.md`；合并结果**另存为**带时间戳的 `.md`/`.docx`（§7.3 第 5 点）；**追加** `交底书修订对话记录.md`（`iteration_dialog_log.py` 或手工）；完成后**必须**输出「合并摘要」留档；若本轮亦为定稿交付，**仍建议**简短附带 §7.6 类引导  
- **指出错误 / 与事实或参数不符**：`Read` → `iteration_context.md` → `correction_handler.md`；纠正结果**另存为**带时间戳的 `.md`/`.docx`；**追加**对话记录；完成后**必须**输出「纠正摘要」留档；定稿交付时**还须**按 **`disclosure_builder.md` §7.6** 附「权利要求偏向点」引导（见 **`correction_handler.md`** 末尾）  

主流程 Step 7→8 的 **`disclosure_self_check.md`** 仍在新稿定稿路径上内部执行。

---

## Agent 自用工作流检查清单

```
□ Step 1 已确认技术方案属于本技能适用范围（工程方法/软件系统/数据处理/控制测算）；结构类已进入有限辅助通道并告知用户限制条件
□ 已按步骤 Read 对应 prompts；Step 2 若目录含 Office，已执行 docx_to_md / pptx_to_md 并读了产出 `.md`
□ 识别到「在已有交底书上修改」类意图时，已 Read `iteration_context.md` 并选用 merger 或 correction_handler（而非从头跑扫描）；交付为**新** `{案件名}_{时间戳}.md`/`.docx`，未无故覆盖旧稿
□ 执行 merger / correction_handler 后，已在对话中输出该文件要求的留档摘要（合并摘要 / 纠正摘要）；案件目录已追加 **`交底书修订对话记录.md`**（或等价日志）
□ Step 3–4 已完成授权可行性初筛；若「区别特征清晰度」「技术效果可论证性」或「方案成熟度」为 0–1 分，未直接推荐为主方向
□ 查新完成且写入 1.1 与区别论述（符合 `prior_art_search.md`：**优先** `tools/cnipa_epub_search.py`，**国知局侧已分多次调用、每轮一词，并已自行合并** `EPUB_HITS_JSON`；**`abstract` 必用且已充分理解后再概括**；CNIPA EPUB 的 `cnipa_qr_or_hint_url` 只作提示，不写成稳定 URL）
□ Step 5 已输出 A/B/C/D 查新结论、最小对比表和「可用区别特征」；高相关文献具备 `verification_status`，已用 `patent_link_verify.py` / 稳定公开页完成必要复核；已回写 Step 3–4 推荐方向
□ 案件目录已生成或追加 `prior_art_dossier.json`/`.md`、`query_log.md`、`positive_controls.md`、`unverified_sources.md`；若阳性对照不足 3 条或关键文献未核验，本轮最高 D/partial-D，交付最高 WARN
□ 除用户明确跳过外，完成摘要预览
□ 主流程交底书已完成脱敏、mermaid（定稿均已渲染为 PNG）、章节引用符合 template_reference；含公式时 **3.4.1 符号表、§7.7 体例**（维度下标、无字母多义、LaTeX 分隔符统一）及 **3.5 符号列同形** 已满足
□ 结构有限辅助案件已按 `disclosure_self_check.md` §8.4 执行专项检查，并明确最高 WARN：正式附图、物理机理、创造性评估须由用户/代理人补足
□ **已交付 .md 与 .docx**，且**文件名符合 §7.3 第 5 点**（**凡交付均含**时间戳后缀）；**正文无**技能/示例仓库类文末脚注
□ 已按 `disclosure_self_check.md` §8.5 给出 PASS/WARN/FAIL；PASS 仅表示「代理人审稿就绪」，不表示可直接提交专利局；案件目录已追加 **`交底书交付检查记录.md`**
□ 定稿类对话已含 **`disclosure_builder.md` §7.6**「权利要求偏向点」建议交互（**不入正文**、**不捏造**未在稿内出现的保护取向）；迭代再走 merger 时见 **`iteration_context.md`** 表格补充行
□ 自检在后台完成，正文无自检清单章节；含公式时已按 **`disclosure_self_check.md` §8.2** 复核**公式正确性与公式逻辑**（有误已在 Step 8 直接改稿）；结构有限辅助案件已按 §8.4 完成专项检查并降级交付
```
