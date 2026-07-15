---
name: patent-unveil-review
description: "面向工程方法、软件系统、数据处理与控制测算类中国发明专利的授权可行性审查与技术交底书生成流程：支持从业务领域或已有工作基础生成候选主题池（T0 方向挖掘：探针级查新、候选主题卡、主题终审），扫描代码、算法、工程测算工具或方案文档，挖掘候选专利点，按技术问题、区别特征、技术效果、实施支撑和方案成熟度进行初筛，联网查新并回写风险等级，生成可供代理人审稿的交底书。结构/机械类专利仅提供有限辅助，需用户自备工程附图与物理机理依据。Use for patent direction mining and candidate pool generation, engineering-method, software-system, data-processing, control, simulation, or calculation patentability review, prior-art search, disclosure drafting, and iterative attorney-review handoff."
allowed-tools: Read, Write, Edit, Grep, Glob, WebSearch, Bash
---

# 工程方法与软件系统类专利授权可行性审查与交底书生成

本技能聚焦 **工程方法、软件系统、数据处理、控制测算、工程仿真/测算工具**类中国发明专利的授权可行性审查：在用户提供代码、算法、工具原型、工程数据、方案文档或论文后，辅助识别具备明确技术问题、区别技术特征、可论证技术效果、实施支撑和方案成熟度的专利方向，并生成**可供代理人审稿**的技术交底书初稿。分步指令在 **`prompts/`**，每步执行前 **`Read`** 对应文件，与步骤的对照见「Prompt 文件映射」。

本技能不替代专利代理师或律师出具正式新颖性、创造性、侵权或 FTO 法律意见；查新结论仅基于本轮可公开检索到的现有技术。

**定位锚（三条验收目标，功能扩展准入滤网）**：本技能只为三件事服务——①交底书初稿**基础逻辑靠谱**（权利要求一致、联动闭环成立、算法良定义、数值可复现）；②支撑交底书的 **MVP/仿真正确编写、可运行并通过复核**；③交付给人看的 **`.md`/`.docx` 排版与格式合理**。深度多视角评审、法律申请策略等由外部 agent/skill 或代理人承担，不内置；新增功能须先说明服务于哪一条，否则不进本技能。

**v2.1 新增**：授权可行性初筛、查新 A/B/C/D 决策分级、查新后回写推荐方向、PASS/WARN/FAIL 代理人审稿门禁，以及案件目录随行的 **`交底书交付检查记录.md`**。

**v2.2 新增**：查新证据模型、来源状态分级、Google Patents 稳定页验证、阳性对照门禁、案件级 `prior_art_dossier` 留档；CNIPA EPUB 结果仅作候选发现，不再把二维码/猜测详情页当作可复核 URL。

**v3.0 变更**：本技能取消此前“软件/结构双模式并列”设计，收缩为工程方法与软件系统类主流程。结构/机械类专利降为**有限辅助模式**：仅在用户已有 CAD/Visio 线稿或标注草图、明确物理机理，以及实验/仿真/标准/工程数据依据时，辅助文字撰写、附图标记一致性和权利要求格式检查；不承诺结构类专利点挖掘、创造性评估或 PASS 级交付。

**v3.1 新增**：商业专利库辅助查新规则。壹专利 / 高数图可作为候选发现与内容检查渠道，记录为 `commercial_db_discovered` 或 `commercial_db_content_checked`；写入交底书公开引用前仍须通过 CNIPA PSS、Google Patents、Espacenet、WIPO 等公开来源形成 `public_source_verified` / 既有稳定来源状态。壹专利反查公开号时优先使用不带 A/B kind code 的公开号主干，并按 R0-R3 标注相关性。

**v3.2 新增**：跨案件 AI 友好工作流沉淀。新候选池启动、商业库+公开源查新、GPT/Claude 策划、工程基础目标、交底书 WARN/PASS 门禁和案件目录文档结构，参考 **`references/patent_workflow_lessons_ai_friendly.md`**。

**v3.3 新增**：商业专利库内容核验闭环。用户已授权并打开壹专利/高数图时，Agent 应主动完成可自动化的低频查询、详情读取、证据落盘和交底书回写，不得笼统把机械核验留给用户或代理人；商业库 URL 仍不得作为公开稳定引用。详见 **`references/commercial_patent_db_verification.md`**。

**v3.4 新增**：正式交底书正文清洁门禁。Word/LaTeX 中间稿、DOCX QA、案件证据包、商业库核验状态、检索过程、Agent/脚本名等流程说明只能写入交接说明、交付检查记录或证据包，不得进入正式 `.md` / `.docx` 正文。详见 **`references/formal_disclosure_cleanliness.md`**。

**v3.5 新增**：查新渠道环境自适应与 Google Patents XHR 补充检索。`tools/channel_preflight.py` 环境预检（一行 `CHANNEL_STATUS_JSON`，记入 `query_log.md`）；`tools/gp_xhr_search.py` 补 CNIPA EPUB「仅首页 ~10 条/词」覆盖短板（发现级 `google_xhr_search_result`）。CNIPA 侧脚本须在用户本机执行，云沙箱阻断属环境状态而非查新结论；`cnipa_epub_search.py` 已支持 `--help` 等标准参数。详见 **`prompts/prior_art_search.md` §A2**。

**v3.6 新增**：**T0 候选池生成模块**（`prompts/candidate_pool.md` + `templates/candidate_topic_card.md`）——从业务领域/已有工作基础挖掘发明方向的可选前置模块，双入口（材料扫描产出 / 冷启动业务方向）逻辑汇合。核心机制：**两级查新**（探针级/案件级，见 `prior_art_search.md`「查新分级」）与**评分证据锚定**（A/B/C/D 只能在真实检索后给出，查新前初筛分仅为"假说分"）；**反定语膨胀与换主轴优先**处理顺序、**限定依赖度**可测定义（区分所需 AND 特征数）、主推/可发表/窄化备选**三层输出**、**双题名制**（≤25 字简洁题名，审查指南锚点）。**四个人工确认点**：确认点 1 主题边界卡（含申请目的/创新幅度/窄化允许）→ 确认点 2 候选主题终审 → 确认点 3 查新证据复核（人工签核；PSS 官方源核验为条件子项，边界声明见 `prior_art_search.md` §D）→ 确认点 4 交底书预览确认（含保密边界，见 `disclosure_preview.md`）。案后领域包回填指引（领域包内容留用户项目目录，不入本仓库）。

**v3.7.0 新增**：四项“实质可专利性”硬门禁（源自一次交底书独立复审的复盘，**提取问题特征而非绑定具体案情**）：①**最接近现有技术须核读独立权利要求原文**（摘要不足、易被误导），影像件渲染页图核读，`claims_read=no` 最高 D（`prompts/prior_art_search.md`）；②**数值可复现门禁**——凡关键量化效果（具体数值/趋势）须经第二次独立核对：能重算的优先复用用户自有模型、否则用 `tools/qa_numeric_reproduce.py` 核对稿值与趋势方向；**无可重算来源（实验/仿真/实测）时设决策点**——主动向用户索取背景/资料并由其决定展开人工核对或标“待核”按 WARN，**不默认启动大核验、不空转、不臆造**；落在 Step 8 自检（`prompts/disclosure_self_check.md` §8.2 执行 + §8.5 门禁）；③**测算/评估类客体整体技术性测试**——“输出评估结果/图表”的纯计算独权须补“物理量获取手段 + 技术性动作”，否则标客体风险（`prompts/patent_points_analyzer.md`）；④**“测算某物理系统”混合型**——方法主线但创造性依赖物理机理时保留物理锚点，结构词不强制转 B 路线（`prompts/intake.md` Q1.5）。

**v3.7.1 新增**：评审与权利要求可靠性门禁（跨案复盘，提取问题特征而非绑定案情）：①**外部审稿意见分诊**——GPT/代理人/审查员意见须逐条核实后再采纳，标【采纳/拒绝（附证据）/存疑】，纠正摘要含分诊表（`prompts/correction_handler.md`）；②**评审输入为 DOCX 须渲染核对**——纯文本提取会把正常 OMML/μ 读成“公式空白/单位错”假缺陷（`prompts/iteration_context.md`）；③**A 路线权利要求一致性**——独权必要特征与“可选/非必要”声明零冲突、逐特征规避测试、过窄参数不入独权（`disclosure_self_check.md` §8.1）；④**独权联动闭环检查**——步骤间须显式参数耦合，防“指标并列”式独权（`patent_points_analyzer.md`＋`disclosure_builder.md`）；⑤算法良定义三查（循环依赖/双重拟合分界/周期量圆周统计，§8.2）；⑥效果幅度-措辞匹配（幅度温和禁“显著”）；⑦默认保护组合补**计算机程序产品**（五客体）＋发明名称不堆客体；⑧交底书固定栏目（本发明摘要、可替代实施方式与规避设计、术语与缩略词表、引用文献表）；⑨查新前用“预查新优先级”术语；⑩Step 6 预览默认必做；⑪联系人/发明人等身份字段一律留用户自填。定位锚三条见本文件开头。

**v3.8.0 新增**：**统一机器交付门禁 `tools/delivery_gate.py`**——把此前散落在多个脚本与自检清单里的机器可校验项收敛为一条命令、一个 `DELIVERY_GATE_JSON` 输出：C1 复用 `qa_docx_math.py` 做公式/正文清洁 QA；C2 占位符扫描（含身份字段白名单，`（用户自填）`不算缺陷）；C3 表格合计闭合；C4 字段标签完整性（专治 `long_sparse_direct` 类多下划线标签被误转 OMML 下标）；C5 红字残留/多式挤同段；C6 文件命名规范；C7 确认点 3/4（及 T0 的确认点 1/2）产物存在性；C8 复用 `qa_numeric_reproduce.py` 做数值复现；C9 版本自报（不调用 git 命令，worktree 内同样可用）。定稿交付前必跑，`FAIL` 不得交付；语义类检查（逻辑闭环、权利要求一致性等）仍由 §8 与人工/Agent 完成，gate 不替代。

**v3.8.1 新增**：**防御性判断与正向表述门禁**（跨案经验）——防御性/否定式判断（防独权写偏、客体主线取舍等**代理人策略提示**）属交接说明/审稿记录，**不进正式正文主叙事**；正文用正向技术特征与效果。六条正向改写：兼容而非排除（"可兼容 X，区别在于…"）、效果加法式列举（"除…外还提供…"，不用免责式）、产品承诺改上位技术输出、代理人策略提示不入正文、独权收敛但说明书不自我否定、独权抽象实施例具体。生成时见 `disclosure_builder.md`「防御性判断与正向表述门禁」；Step 8 见 `disclosure_self_check.md` §8.3 否定式表述扫描；`delivery_gate.py` 增 **C10** 机器兜底（WARN 列出 `不在于/不作为/不强制/不以/不宜/显著降低` 供逐处判定归属，**非 FAIL**）。

**v3.9.0 新增**：**两案代理批注复盘门禁 + 代理批注闭环子流程**（源自两件真实案件预审批注〔8 条 + 16 条〕的共性提炼，提取问题特征而非绑定案情；案件标识不入本公开仓库）。①**生成侧四门禁**（`disclosure_builder.md`）：**方案骨架先行与步骤分级公开**（统一步骤骨架为各视图唯一真源，防 3.2/3.4 流程漂移；CORE 详述/COMMON 简述，校核类步骤须给全约束清单与通过/不通过判定）、**公式随步走**（manifest 增 `owner_step`，公式须在归属步骤中出现或被引用，符号与公式节仅作索引）、**术语定义与数据血缘**（自造词首现即定义；集合术语不与成员重复并列；原始/预处理/派生/判断/决策五层不混写）、**模糊限定词与观测粒度**（判定语境模糊词量化三选一或标注示例阈值待标定；输出粒度不得超出输入数据支撑，超出降级为「候选＋置信度」；判定依据「和/或」全文一致）。②**自检侧**（`disclosure_self_check.md` §8.1 新小节）：框图-流程图-模块-保护点跨视图对照 + **保护支撑核对表**——第五章每条关键点/从属保护点逐条回答「具体体现在方案中的哪部分」（步骤+公式+实施例），答不出即补正文或降级删除。③**代理批注闭环子流程**（`prompts/review_comment_closure.md` + `tools/docx_comment_extract.py`）：审阅 DOCX 批注提取（范围/点批注分类、回复线程 `paraIdParent`、已解决标记）→ 点批注作用范围判断 → overlay 标注版（`REVIEW_COMMENT_BEGIN/END`，批注原文不可变）→ 接 `correction_handler.md` 分诊 → `批注处置矩阵.md`（CLOSED/PARTIAL/OPEN）→ 代理意见回复稿；双真源核对（正文 MD vs 审阅 DOCX）。④`delivery_gate.py` 增 **C11** 模糊限定词机器兜底（WARN 列出 `近似同步/明显大于/证据不足/必要时` 等供逐处判定，非 FAIL）。

**v3.10.0 新增**：**技术证据合同 + 可观测性/多模态证据门禁**（第二轮 16 条代理批注复盘：根因是生成正文前未强制形成「技术事实—观测能力—证据职责—决策逻辑」合同，导致聚合级量测被写成可定位单体内部、标准参考基线混作现场观测、单一证据包办定位归因决策、正文 AND 流程图 OR）。①**技术证据合同**（`templates/technical_evidence_contract.yaml` + `references/technical_evidence_contract.md`）：测量/诊断/定位/状态识别类案件的方案骨架**必须**升级为完整合同——观测层级与可声称精度（`output_rank ≤ observation_rank`）、基线登记（standard/historical_clean/post_treatment/healthy_peer 四类）、阈值来源、下游消费者、降级分支、特征分类（independent_core/dependent/implementation_param/auxiliary_evidence，**实施参数不入独权**）；②**可观测性与多模态证据职责**（`references/observability_and_multimodal_evidence.md` + `templates/evidence_responsibility_matrix.md`）：一种证据不得包办筛查+定位+归因+决策，影像/热像须经物理拓扑与实测一致性验证才进决策，处置后复测回写基线闭环；③**决策逻辑单一事实源**（`templates/decision_table.md`）：AND/OR 只在决策表显式写出，各视图引用 D 编号；④**架构变化补充查新触发器**（`iteration_context.md`）：数据来源/证据模态/定位方式/决策链/独权主线实质变化时不得沿用旧查新结论；⑤**代理回复矩阵**（`templates/attorney_response_matrix.md`）：回复条数=原批注条数；⑥`delivery_gate.py` 增 **C12**（证据合同结构校验，FAIL 级：字段完整/枚举/精度 rank/引用完整性/阈值来源）、**C13**（决策编号引用一致性，WARN）、**C14**（代理意见回复数量核对，FAIL）、**C15**（独权区实施参数扫描，WARN）；C12 需 pyyaml。语义判断（观测能力是否真支撑、基线是否混用、职责是否越界）仍留 §8.1，不以正则代替。

## 环境与约定

- **语言**：默认与用户语种一致；专利与法律术语采用行业常用表述。
- **适用范围**：工程方法、软件系统、数据处理、控制测算、工程仿真/测算工具类中国发明专利。结构/机械类进入「有限辅助」通道，详见 `prompts/intake.md`。
- **默认保护组合**：方法权利要求 + 系统/装置权利要求 + 电子设备权利要求 + 计算机可读存储介质权利要求 + **计算机程序产品权利要求**（2023 版审查指南明确客体，在线分发/云端部署场景尤宜保留）；如查新或材料支撑不足，可收缩为方法+系统或单一系统方案。设备/介质/程序产品为覆盖面客体（尾部保护），不作为区别现有技术的主线，**不进入发明名称**（题名规则见 `disclosure_builder.md`）。
- **图示定稿（Step 7）**：
  - **主流程**：**3.2**/**3.4** 用 fenced **mermaid**；执行方式、**`mmdc`** 安装与降级规则见下表「交底书定稿交付」行及 **`tools/README.md`**。
  - **结构有限辅助**：附图由用户提供 CAD/Visio 线稿或标注草图；本技能仅辅助文字描述和附图标记一致性检查，不生成结构附图，不输出 PASS。详见 **`references/structural_patent_requirements.md`**。

---

## 触发条件

在用户使用以下任一方式时启用本技能：

- 明确提及：专利挖掘、专利点、技术交底书、交底书、专利交底书、查新、现有技术对比等
- **方向挖掘/候选池类**：用户提及专利方向挖掘、候选池、GAP 发现、主题筛选/主题选定，且尚无选定主题时——**`Read`** **`prompts/candidate_pool.md`** 执行 **T0**（含确认点 1/确认点 2 与探针级查新）；用户已有明确主题与材料时跳过 T0
- **主流程技术关键词**：工程方法、软件系统、数据处理、AI/算法、控制策略、调度方法、工程测算、仿真评估、识别方法、一致性校核、文档生成与质量校验等
- **结构/机械类材料**：当用户提及装置、连接器、零部件、结构设计、附图标记、剖视图、装配图等时，先判断**核心创新是“结构本体”还是“测算/评估某结构的方法”**：前者进入有限辅助模式（提示备附图与物理机理依据，不做结构类专利点挖掘或创造性评估）；后者属“混合型”，仍走方法主线并保留物理锚点（见 `prompts/intake.md` Q1.5、`prompts/patent_points_analyzer.md`「整体技术性测试」），**不**因结构词自动降为有限辅助。
- 斜杠或简短指令：如 `/patent-unveil-review`、`/工程方法专利`、`/交底书`
- **迭代模式（按意图识别）**：当用户意图明显是在**已有交底书或上一轮输出**上继续工作（如改章节、补实施例、补材料、修正参数/事实、调整表述等），**无需**用户写出「迭代」等固定词，也**不必**询问是否进入迭代——Agent 应 **`Read`** **`prompts/iteration_context.md`**，再 **`Read`** `prompts/merger.md`（侧重**新材料、扩展合并**）或 `prompts/correction_handler.md`（侧重**纠错、与事实或风格不符**）；输入为**带批注的审阅 DOCX** 或用户要求提取/逐条处理/回复代理意见时，先 **`Read`** `prompts/review_comment_closure.md`（批注提取+锚点+overlay）再接 correction_handler，**严格按该文件开头的「执行门禁」**（优先执行，不可跳过）**做完合并或纠正**，**另存为新文件**：**`{案件名}_{YYYYMMDDHHmmss}.md`** 与同名 **`.docx`**（与首次定稿同一命名规则，见 **`disclosure_builder.md` §7.3 第 5 点**），**不覆盖**旧稿（除非用户明确要求）。**禁止**在迭代意图已成立时默认回到 Step 3–4 专利点全文分析（除非用户明确要求重新挖掘专利点）。对话中**已出现**交底书路径、附件或上文刚交付的草稿时，优先按迭代处理。

---

## 工具与数据来源

按任务选用能力；具体工具名称以当前 Agent 环境为准。

若扫描范围内含 **Word（.docx）** 或 **PowerPoint（.pptx）**，须在 Step 2 纳入阅读前用本仓库 **`docx_to_md.py`** / **`pptx_to_md.py`** 转为 Markdown；依赖 **`pip install -r requirements.txt`**，命令与说明见下表对应行。

### 数学公式、图示与 Word QA 硬约束

涉及关键公式、符号表或量纲推导的交底书，须先建立公式清单（可复制 **`templates/patent_formula_manifest.yaml`**），字段至少含 `id`、`number`、`title`、`latex`、`display`、`dimension_check`；正文只引用清单中的公式，不得临场自由拼写关键公式。公式源必须是合法 LaTeX：希腊字母写 `\eta`、`\pi`、`\Phi`，正体文本下标写 `\mathrm{}`，分式写 `\frac{...}{...}`，求和写 `\sum_{t=1}^{T}`。若源稿中出现整行裸公式（例如 `V_sys / ln(R_socket/R_pin)`）或下一行单独编号 `(4)`，`md_to_docx.py` 必须升级为块级 OMML 公式并用右侧编号结构排版；正文解释中的 `V_sys`、`R_pin` 等裸下划线**数学变量**也必须转为 OMML 下标，不得作为普通文本残留。**例外（字段/枚举标签）**：`long_sparse_direct` 类多下划线英文字段标签**不是公式**，禁止转为下标、斜体或其它公式化处理（否则 Word 中被截断变形）；生成正文时此类标签优先用中文名称并在括号内附标签原文。`.docx` 交付前必须运行 **`tools/qa_docx_math.py`**（`md_to_docx.py` 默认已执行）；若发现 `frac{`、`mathrm{`、`\(`、`\)`、`$`、`bare_subscript_identifier` 等残留或 manifest 编号/OMML 结构不一致，本轮不得作为定稿交付。
当使用 `md_to_docx.py --math-manifest <manifest.yaml>` 时，转换阶段须按 manifest 中 `display` 公式顺序为未显式 `\tag{}` 的块级公式自动补右侧编号；这不是单纯 QA 参数，而是排版编号来源。

DOCX 交付不得只看生成命令退出码。`qa_docx_math.py` 是 Word XML 级交付门禁：除公式外，还会检查未渲染 mermaid 源码（如 `flowchart TB`）、Consolas/代码样式残留、嵌入媒体数量不足等问题。主流程系统框图与流程图若有任一 mermaid 块渲染失败，`mermaid_render.py` 只写出 Markdown 排障稿，不得继续生成定稿 Word。若当前环境有 Word/LibreOffice，可额外导出 PDF/页面图做视觉 QA；若无，应在 `交底书交付检查记录.md` 中声明未做页面级视觉 QA，并建议人工打开 Word 复核图示缩放、表格换行和公式视觉效果。

正式交底书正文不得包含流程自述或工具说明，例如“以下公式均以标准 LaTeX 源写入中间稿”“详细检索记录已另行保存在案件证据包中”“壹专利已完成商业库内容核验；正式公开引用仍建议……”等。上述内容只允许进入交接说明、交付检查记录或查新证据包；定稿 DOCX 须通过 `qa_docx_math.py --check-formal-text`。

含**关键量化效果**（具体数值/趋势）的交底书，Step 8 自检须做**数值二次核对**：能重算的用 **`tools/qa_numeric_reproduce.py`** 或复用用户自有模型（稿值＝算值、趋势方向一致）；无可重算来源（实验/仿真/实测）的按 §8.2 三层**决策点**处理（向用户索取资料 / 标“待核”按 WARN，不闷头展开或空转）。`qa_docx_math.py` 只查公式排版/OMML、**不查数值对错**，二者互补。详见 `prompts/disclosure_self_check.md` §8.2/§8.5。

### 常见任务与建议方式

| 任务 | 建议方式 |
|------|----------|
| 加载分步指令 | **`Read`** → `${CLAUDE_SKILL_DIR}/prompts/*.md`，见下表 |
| 方向挖掘 / 候选池生成（T0） | **`Read`** → `${CLAUDE_SKILL_DIR}/prompts/candidate_pool.md`；双入口汇合，确认点 1 主题边界卡确认后做探针级查新，按 `templates/candidate_topic_card.md` 出 3–5 张主题卡，确认点 2 终审后进入案件级查新 |
| 新候选池启动 / 复用完整专利工作流 | **`Read`** → `${CLAUDE_SKILL_DIR}/references/patent_workflow_lessons_ai_friendly.md`；按“证据闭环、方向闭环、工程支撑闭环、交付闭环”建立案件目录、查新证据包、GPT 咨询请求、工程产物和交底书门禁 |
| 壹专利 / 高数图内容核验与技术对比回写 | **`Read`** → `${CLAUDE_SKILL_DIR}/references/commercial_patent_db_verification.md`；已授权打开商业库时主动完成 `commercial_db_content_checked` 证据，但商业库状态、URL 和核验过程只写入证据包/交接说明/交付检查记录；交底书 1.1.2/1.1.3 只回写技术对比事实 |
| 读代码、设计文档、PDF、图片 | 文件读取工具；大仓库先用搜索/语义检索定位再精读 |
| Word（.docx）→ Markdown + 抽取图片（扫描前） | `Bash` → `python3 ${CLAUDE_SKILL_DIR}/tools/docx_to_md.py --input {path}.docx --output {dir}/{name}.md`；图片默认写入与 `.md` 同级的 `{name}_media/`；需 `pip install -r requirements.txt`（含 mammoth）；复杂版式可改由所内导出 PDF/MD 再扫 |
| PowerPoint（.pptx）→ Markdown + 抽取图片（扫描前） | `Bash` → `python3 ${CLAUDE_SKILL_DIR}/tools/pptx_to_md.py --input {path}.pptx --output {dir}/{name}.md`；默认 `{name}_media/`；需 `pip install -r requirements.txt`（含 python-pptx）；**旧版 .ppt 不支持**，请先另存为 `.pptx`；图表/SmartArt 等若未以图片形状嵌入则可能仅能从备注或另行导出补全 |
| 罗列目录、按名找文件 | 目录列举 / 按文件名搜索 |
| 联网查新（Step 5） | 执行前 **`Read`** `prompts/prior_art_search.md`。**中国专利公布公告**：优先 **`Bash`** 运行 `cnipa_epub_search.py`；**须在生成命令前**归纳 **2～8 个相关度高的语义块**；**执行时须分多次调用**，**每次仅传一个**词块，**自行按 `pub_number` 合并**多轮 `EPUB_HITS_JSON`。CNIPA EPUB 输出默认是 `cnipa_result_page_parsed` 候选，`cnipa_qr_or_hint_url` 不得写作稳定 URL；高相关条目须用 `patent_link_verify.py` / Google Patents / Espacenet / WIPO / CNIPA PSS 复核。若用户已授权并打开学校远程访问页面，可将壹专利 / 高数图作为商业库发现和内容检查渠道，但只能标 `commercial_db_discovered` / `commercial_db_content_checked`，不得直接作为公开引用。案件目录须用 `prior_art_dossier.py` 或等价手工留 `prior_art_dossier.*`、`query_log.md`、`positive_controls.md`、`unverified_sources.md`；异常或证据不足按 D/partial-D，不伪造可授权结论。环境不确定或 EPUB 失败时先跑 **`tools/channel_preflight.py`**（`CHANNEL_STATUS_JSON` 记入 `query_log.md`）；覆盖补强/环境降级用 **`tools/gp_xhr_search.py`**（发现级 `google_xhr_search_result`，高相关须复核）；渠道失败记**环境状态**，不得写成检索无结果 |
| 交底书定稿交付（**须同时** .md + .docx） | **3.2** 系统框图与 **3.4** 流程图均用 fenced ``mermaid``，**不要** ASCII 文字流程图/框图。定稿执行 **`tools/mermaid_render.py`**：mermaid 转 PNG，所有块成功后默认生成同名 **.docx**；若任一块失败，只保留 Markdown 排障稿，**不得**生成定稿 Word。**公式与符号在 Word 中必须为可编辑 OMML，不得用公式图片或代码样式**，如 `B_{s,t}^{tot}` 应写成公式而不是反引号代码；含关键公式时先建 formula manifest，并在 Word 生成后执行 **`tools/qa_docx_math.py <docx> --manifest <manifest.yaml> --check-formal-text`**（`mermaid_render.py` 默认执行正式正文清洁 QA）；QA 会检查公式残留、未渲染 mermaid、Consolas 代码样式、嵌入媒体数量和流程说明残留，失败不得交付。详见 **`tools/README.md`** |
| 保存交底书路径 | 写入用户指定路径；未指定时可建议 `./outputs/{案件标识}/`；**凡交付的** `.md` / `.docx` 须为 **`{案件名}_{YYYYMMDDHHmmss}`**（§7.3 第 5 点，**含首次定稿与迭代**），勿默认覆盖旧稿；`outputs/` 整目录默认由 `.gitignore` 忽略 |
| 代理批注 DOCX 提取与闭环 | **`Read`** → `${CLAUDE_SKILL_DIR}/prompts/review_comment_closure.md`；先 **`Bash`** 运行 `python3 ${CLAUDE_SKILL_DIR}/tools/docx_comment_extract.py --input "{审阅版.docx}" --output "{案件目录}/批注提取_{YYYYMMDD}.md"`（末行 `COMMENT_EXTRACT_JSON`；范围/点批注分类、回复线程、已解决标记），再做点批注作用范围判断、overlay 标注版、分诊改稿、`批注处置矩阵.md` 与代理意见回复稿 |
| 迭代对话留档 | 每轮 **merger / correction** 交付后，在案件目录追加 **`交底书修订对话记录.md`**（**`tools/iteration_dialog_log.py`** 或等价手工），见 **`prompts/iteration_context.md`** |
| 交付检查留档 | 每次向用户落盘交付 `.md`/`.docx` 后，在案件目录追加 **`交底书交付检查记录.md`**（**`tools/delivery_check_log.py`** 或等价手工），记录 PASS/WARN/FAIL、交付文件、待补项和检查摘要；见 **`disclosure_self_check.md` §8.5** |
| 交付前统一机器门禁（v3.8.0，C10 v3.8.1，C11 v3.9.0，C12–C15 v3.10.0） | **`Bash`** 运行 `python tools/delivery_gate.py --case-dir <案件目录> --md <交付.md> --docx <交付.docx>`；一条命令覆盖 docx 公式/正文清洁 QA、占位符扫描（含身份字段白名单）、表格合计闭合、字段标签完整性、公式段落残留、命名规范、确认点产物存在性、数值复现（传 `--numeric-spec` 时）、版本自报、否定式/防御性表述扫描（C10，WARN）、模糊限定词扫描（C11，WARN）、**技术证据合同结构校验**（C12，FAIL 级，自动发现案件目录 `*技术证据合同*.yaml` 或传 `--evidence-contract`，需 pyyaml）、**决策编号引用一致性**（C13，WARN）、**代理意见回复数量核对**（C14，FAIL，传 `--comments-json` + `--attorney-reply` 时）与**独权区实施参数扫描**（C15，WARN），自动追加 `交底书交付检查记录.md`；`DELIVERY_GATE_JSON` 最后一行为准，`FAIL` 不得交付 |
| 结构有限辅助附图合规参考 | **`Read`** → `${CLAUDE_SKILL_DIR}/references/structural_patent_requirements.md`，获取 CNIPA 附图规范、结构权利要求格式和部件编号规范；该参考不用于创造性评估 |
| 法规来源索引 | 需要核对法源、版本和适用范围时 **`Read`** → `${CLAUDE_SKILL_DIR}/references/legal_sources.md`；不要把法规全文复制进交底书正文 |

---

## Prompt 文件映射

| 步骤 | 文件 | 用途 |
|------|------|------|
| T0（可选前置） | `prompts/candidate_pool.md` | 候选池生成：双入口（材料入口/冷启动入口）、确认点 1 主题边界卡、探针级查新、确认点 2 主题终审、案后领域包回填；**逻辑汇合点——材料入口下在 Step 2 之后执行** |
| T0 模板 | `templates/candidate_topic_card.md` | 候选主题卡字段模板（双题名、独权禁区、暂停条件、限定依赖度、检索溯源、权利要求骨架附件） |
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
| 迭代 | `prompts/review_comment_closure.md` | 代理批注闭环：DOCX 批注提取（`tools/docx_comment_extract.py`）、点批注作用范围判断、overlay 标注版、批注处置矩阵、代理意见回复稿；分诊与改稿仍走 correction_handler |
| 参考 | `references/structural_patent_requirements.md` | 结构有限辅助：CNIPA 附图规范、结构权利要求格式、部件编号规范；不用于创造性评估 |
| 参考 | `references/method_system_patent_guide.md` | 工程方法、软件系统、四客体保护组合与常见授权风险参考 |
| 参考 | `references/legal_sources.md` | 专利法、实施细则、审查指南 2023 及 2025 修改决定等法源索引 |
| 参考 | `references/patent_workflow_lessons_ai_friendly.md` | 跨案件专利工作流沉淀：候选池启动、证据分级、GPT/Claude 协作、工程基础、WARN/PASS 交付和 AI 友好文档结构 |
| 参考 | `references/commercial_patent_db_verification.md` | 商业专利库内容核验：壹专利/高数图操作边界、来源状态、正文与交接说明分离、代理人确认边界 |
| 参考 | `references/formal_disclosure_cleanliness.md` | 正式交底书正文清洁：流程说明、工具说明、证据状态和交接提示不得进入正文 |
| 参考 | `references/technical_evidence_contract.md` | 技术证据合同：字段规则、与方案骨架的关系、机器/语义分工；模板 `templates/technical_evidence_contract.yaml` |
| 参考 | `references/observability_and_multimodal_evidence.md` | 可观测性原则、基线分类学、多模态证据职责矩阵、处置后复测闭环、架构变化补充查新；模板 `templates/evidence_responsibility_matrix.md`、`templates/decision_table.md`、`templates/attorney_response_matrix.md` |

---

## 主流程（执行顺序）

0. **（仅方向挖掘类任务）** **`Read`** `candidate_pool.md` → 执行 T0：材料入口先走 Step 1–2 再汇入，冷启动入口 Step 1 后直接进入；经确认点 1 边界卡确认、探针级查新、确认点 2 终审选定主题后，**由 Step 3–4 做轻量整合**（主题卡为输入，不重复挖掘），再进入 Step 5 案件级查新。用户已有明确主题与材料时跳过本步  
1. **`Read`** `intake.md` → 执行 Step 1  
2. **`Read`** `project_scan.md` → 执行 Step 2  
3. **`Read`** `patent_points_analyzer.md` → 执行 Step 3–4，输出候选点和**查新前授权可行性初筛**  
4. **`Read`** `prior_art_search.md` → 执行 Step 5，形成 A/B/C/D 查新结论；随后**回写 Step 3–4 推荐方向、查新风险和可用区别特征**  
5. **`Read`** `disclosure_preview.md` → 执行 Step 6（**确认点 4，默认必做**：输出 300–500 字预览＋保密边界/关键事实/保护方向确认清单，确认结果落案件目录 `预览确认记录.md`）；仅用户**明确表示跳过**时方可略过，并在交付检查记录注明「预览未经用户确认」  
6. **`Read`** `disclosure_builder.md` 与 **`Read`** `template_reference.md` → 执行 Step 7（**首次交付**的 `.md`/`.docx` 亦须 **`{案件名}_{YYYYMMDDHHmmss}`**，§7.3 第 5 点）；交付对话中**须**按 **`disclosure_builder.md` §7.6** 补充「权利要求偏向点」建议交互（**仅对话**，不入正文）  
7. **`Read`** `disclosure_self_check.md` → 内部执行 Step 8，修订后交付；每次落盘交付须在案件目录追加 **`交底书交付检查记录.md`**
8. **交付前必跑门禁**：以 **`tools/delivery_gate.py`** 作为定稿交付的**唯一机器门禁入口**（`python tools/delivery_gate.py --case-dir <案件目录> --md <交付.md> --docx <交付.docx>`，含公式清单/关键数值复核时加 `--manifest`/`--numeric-spec`，用户明确跳过确认点 4 时加 `--preview-skipped`）；以其输出的 **`DELIVERY_GATE_JSON`** 最后一行为准，`FAIL` 不得交付，`WARN` 须把待补项与用户自填清单一并写入回复和交付检查记录，`PASS` 仅表示机器可校验项通过，不表示可直接提交专利局。该工具只覆盖占位符/计数闭合/字段标签/公式段落残留/命名规范/确认点产物存在性/版本自报等**机器可校验**项，§8 的语义类检查（逻辑闭环、权利要求一致性、公式正确性等）仍须人工/Agent 完成，二者互补不互相替代。

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
□ 新候选池或“按上次完整流程走”类任务，已 Read `references/patent_workflow_lessons_ai_friendly.md`，并建立证据闭环、方向闭环、工程支撑闭环和交付闭环
□ 用户已授权打开壹专利/高数图且本轮涉及商业库核验时，已 Read `references/commercial_patent_db_verification.md`，主动完成低频检索、详情读取和证据落盘；商业库状态、URL 和核验过程已写入证据包/交接说明/交付检查记录，交底书 1.1.2/1.1.3 只回写技术对比事实
□ 已按步骤 Read 对应 prompts；Step 2 若目录含 Office，已执行 docx_to_md / pptx_to_md 并读了产出 `.md`
□ 识别到「在已有交底书上修改」类意图时，已 Read `iteration_context.md` 并选用 merger 或 correction_handler（而非从头跑扫描）；交付为**新** `{案件名}_{时间戳}.md`/`.docx`，未无故覆盖旧稿
□ 执行 merger / correction_handler 后，已在对话中输出该文件要求的留档摘要（合并摘要 / 纠正摘要）；案件目录已追加 **`交底书修订对话记录.md`**（或等价日志）
□ 方向挖掘类任务已走 T0（`candidate_pool.md`）：确认点 1 主题边界卡经用户确认（含申请目的/创新幅度/窄化允许）；所有 A/B/C/D 等级均有真实检索依据（探针级或案件级），无「模型自评 GAP」；未探针方向仅标「未评级（低置信）」；技术问题已做实在性分级（实证/佐证/未证），「未证」+0 命中的方向未作主推
□ 候选主题卡符合 `templates/candidate_topic_card.md`：带检索溯源（未跑渠道记「未覆盖」，未写成「未检出」）；简洁题名 ≤25 字；窄化备选方向已声明保护范围偏窄；独权禁区均附公开号
□ 确认点 2 主题终审已完成（业务贴合/资料可得/关键动作真实性/商业动作技术化）并落档主题卡；终审未改判证据等级；未过确认点 2 的方向未进入案件级查新或交底书
□ 案件级查新后确认点 3 签核记录已落档（签核人/等级/证据包完整性/PSS 状态/未核验条目影响/结论，见 `prior_art_search.md`「确认点 3」节）；未核验条目影响结论时未解除暂停条件；签核未完成未进 Step 7 定稿路径
□ Step 3–4 已完成授权可行性初筛；若「区别特征清晰度」「技术效果可论证性」或「方案成熟度」为 0–1 分，未直接推荐为主方向；查新前初筛分仅作「假说分」使用，未单独作为推荐依据
□ 查新完成且写入 1.1 与区别论述（符合 `prior_art_search.md`：**优先** `tools/cnipa_epub_search.py`，**国知局侧已分多次调用、每轮一词，并已自行合并** `EPUB_HITS_JSON`；**`abstract` 必用且已充分理解后再概括**；CNIPA EPUB 的 `cnipa_qr_or_hint_url` 只作提示，不写成稳定 URL）
□ 渠道异常或新环境首跑时，已运行 `channel_preflight.py` 并把环境状态记入 `query_log.md`；EPUB 覆盖不足或环境阻断时已用 `gp_xhr_search.py` 补检（命中仅作发现级候选）
□ Step 5 已输出 A/B/C/D 查新结论、最小对比表和「可用区别特征」；高相关文献具备 `verification_status`，商业库候选仅标 `commercial_db_discovered` / `commercial_db_content_checked`，写入交底书公开引用前已用 `patent_link_verify.py` / 稳定公开页 / 官方源完成必要复核；已回写 Step 3–4 推荐方向
□ 案件目录已生成或追加 `prior_art_dossier.json`/`.md`、`query_log.md`、`positive_controls.md`、`unverified_sources.md`；若阳性对照不足 3 条或关键文献未核验，本轮最高 D/partial-D，交付最高 WARN
□ 除用户明确跳过外，完成摘要预览（确认点 4），确认结果已落案件目录 `预览确认记录.md`；用户跳过时已在交付检查记录注明
□ 主流程交底书已完成脱敏、mermaid（定稿均已渲染为 PNG 且 DOCX media 数量满足预期）、章节引用符合 template_reference；含公式时 **3.4.1 符号表、formula manifest、§7.7 体例**（维度下标、无字母多义、LaTeX 分隔符统一）、**Word 可编辑 OMML 公式**（无公式图片、无代码样式符号）、**`qa_docx_math.py --check-formal-text` PASS** 及 **3.5 符号列同形** 已满足；若无法做 Word/LibreOffice 页面级视觉 QA，已写入交付检查记录
□ 最接近现有技术/R0–R1 主对比已**核读独立权利要求原文**（`claims_read=yes`；影像件已渲染页图核读）；仅摘要级时查新最高 D，未据摘要臆断区别特征
□ 含关键量化效果的交底书关键数值已**独立二次核对**：可重算的（`qa_numeric_reproduce.py`/用户模型）稿值＝算值、方向一致且不符已改稿；无可重算来源的已在**决策点**向用户说明并按其决定处理（补料人工核对 / 标“待核”WARN），未闷头展开或空转
□ 测算/评估/计算类候选已做**整体技术性测试**：独权是否落到“物理量获取 + 技术性动作”，纯“算→输出图表”独权已标客体风险并给加固要求
□ “测算某物理系统”混合型未被结构词误导：仍走方法主线且保留物理锚点，未产出脱离物理过程的纯计算独权
□ 结构有限辅助案件已按 `disclosure_self_check.md` §8.4 执行专项检查，并明确最高 WARN：正式附图、物理机理、创造性评估须由用户/代理人补足
□ **已交付 .md 与 .docx**，且**文件名符合 §7.3 第 5 点**（**凡交付均含**时间戳后缀）；**正文无**技能/示例仓库类文末脚注，也无 Word/LaTeX 中间稿、案件证据包、商业库状态、检索过程或工具 QA 说明
□ 已按 `disclosure_self_check.md` §8.5 给出 PASS/WARN/FAIL；PASS 仅表示「代理人审稿就绪」，不表示可直接提交专利局；案件目录已追加 **`交底书交付检查记录.md`**
□ 定稿类对话已含 **`disclosure_builder.md` §7.6**「权利要求偏向点」建议交互（**不入正文**、**不捏造**未在稿内出现的保护取向）；迭代再走 merger 时见 **`iteration_context.md`** 表格补充行
□ 自检在后台完成，正文无自检清单章节；含公式时已按 **`disclosure_self_check.md` §8.2** 复核**公式正确性与公式逻辑**（有误已在 Step 8 直接改稿）；结构有限辅助案件已按 §8.4 完成专项检查并降级交付
□ 迭代纠错时外部意见（GPT/代理人/审查员）已逐条**分诊**（采纳/拒绝附证据/存疑，见 `correction_handler.md`），未盲改；评审对象为 .docx 时格式类结论基于**渲染核对**而非纯文本提取
□ 输入为带批注审阅 DOCX 时已走 `review_comment_closure.md`：批注经 `docx_comment_extract.py` 提取（原文逐字、含锚点与点批注标识），点批注已做作用范围判断，overlay 标注版与 `批注处置矩阵.md` 已落档，全部条目有 CLOSED/PARTIAL/OPEN 状态；「哪部分」类批注在正文无支撑时已补正文或降级保护点，未仅加解释敷衍
□ 生成新稿前已固化**方案骨架**（步骤 ID/输入/操作依据/输出/异常分支/类别，落案件目录），3.2/3.3/3.4/第五章各视图由同一骨架展开；步骤已分级（CORE 详述含约束清单与通过判定，COMMON 简述）；manifest 公式均有 `owner_step` 且在归属步骤中出现或被引用
□ 测量/诊断/定位/状态识别类案件已把骨架升级为**技术证据合同**（`templates/technical_evidence_contract.yaml`，C12 校验通过）：观测层级与声称精度匹配、基线四类登记且标准参考未混作现场观测、阈值有来源、降级分支完整、实施参数未入独权（C15 已逐处判定）；多模态并用已填证据职责矩阵，单一证据未包办筛查+定位+归因+决策；多条件判定有决策表 D 编号且各视图引用一致（C13）
□ 迭代中数据来源/证据模态/定位方式/核心决策链/独权主线发生实质变化时，已执行补充查新并回写等级（`iteration_context.md` 触发器），未沿用旧查新结论定稿；代理意见回复稿条数=原批注条数（C14 通过）
□ 已完成 §8.1「跨视图一致性与保护支撑核对」：框图-流程图-模块-保护点对照通过；第五章每条关键点/从属保护点能答出「具体体现在方案中的哪部分」（步骤+公式+实施例）；自造词首现已定义、集合术语无重复并列；模糊限定词已量化或标注示例阈值待标定（C11 WARN 已逐处判定）；「定位/映射」类主张粒度未超出输入数据支撑
□ A 路线独权已过**权利要求一致性与联动闭环**检查（`disclosure_self_check.md` §8.1）：无「独权必要 vs 从属非必要」冲突、无可拆分指标并列独权、过窄参数未入独权
□ 交底书含**本发明摘要**与第六章固定栏目（可替代实施方式与规避设计、术语与缩略词表、引用文献表）；联系人/发明人等身份字段保留「（用户自填）」，未代填或编造
□ **`tools/delivery_gate.py` 已运行且非 FAIL**（v3.8.0）：`DELIVERY_GATE_JSON` 已读取，WARN 项与用户自填清单已写入回复和交付检查记录；gate 只覆盖机器可校验项，不替代本清单的语义类检查
```
