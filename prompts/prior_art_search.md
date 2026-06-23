# 联网检索查新（Step 5）

## 必做时机

生成交底书全文**之前或生成过程中**必须执行；检索结论写入第一章 **1.1 现有技术** 及与本案的**区别论述**。

## 结论边界（交付和内部均须遵守）

- 查新结论仅基于本轮可公开检索到的专利、论文和其它公开文献；不得表述为“绝对没有相同现有技术”。
- 注意专利公开的天然盲区：很多申请自申请日或优先权日起满 18 个月左右才公开，最近未公开申请无法通过公开渠道检索。
- 本步骤输出的是研发早期/交底书撰写前的检索分析，不替代专利代理师或律师的新颖性、创造性、侵权、FTO 或稳定性正式法律意见。
- 不得编造命中文献、公开 URL、申请人、摘要、权利要求内容或检索结论；检索不到就是检索不到，标为 D 或待补检。

## 证据模型（P0，先于结论）

本步骤采用“候选发现 + 稳定来源复核 + 证据状态”的模式。**不得**把任何未打开、不可复核或仅由页面二维码/猜测路径得到的 URL 写成“已核验公开源 URL”。

### 每条命中文献/专利的统一字段

查新笔记、对比表和案件目录证据包至少保留以下字段：

| 字段 | 含义 |
|------|------|
| `publication_number` / `pub_number` | 公开号、公告号或文献标识 |
| `title` | 标题 |
| `abstract` | 摘要或经消化的方案概括；不得编造 |
| `applicant_or_author` | 申请人/作者；未知则写“未核验” |
| `publication_date` | 公开日/发表日；未知则写“未核验” |
| `source_origin` | `cnipa_epub` / `cnipa_pss` / `google_patents` / `espacenet` / `wipo` / `scholar` / `paper` / `commercial_db_yizhuanli` / `commercial_db_gaoshutu` 等 |
| `stable_url` / `link` | **本轮实际打开且著录项匹配**的稳定 URL；未核验时必须为空 |
| `source_hint_url` / `cnipa_qr_or_hint_url` | 可帮助人工定位但未证明稳定可打开的提示 URL |
| `verification_status` | 见下表 |
| `query_trace` | 命中的检索词、数据库、检索时间 |
| `same_points` | 与本案相同/接近点 |
| `distinguishing_points` | 区别点 |
| `usable_distinguishing_features` | 可回写到方案和权利要求布局的真实区别特征 |

### 来源状态

| 状态 | 可否作为稳定证据 | 说明 |
|------|------------------|------|
| `official_pss_verified` | 是 | CNIPA 专利检索及分析系统中已人工/浏览器复核著录项和详情 |
| `official_detail_opened` | 是 | 官方详情页已实际打开并核验标题/公开号/摘要 |
| `official_cnipa_epub_detail_opened` | 是 | CNIPA 公布公告 / EPUB 官方详情页已实际打开并核验标题、公开号、申请号等著录项；不是 PSS 复核 |
| `official_egaz_page_images_archived` | 是 | EGAZ 官方预览页图已归档，可用于人工核对权利要求/说明书图像；不是原始 PDF 下载文本 |
| `official_claims_transcribed_from_page_images` | 是 | 权利要求已从官方页图人工转写并复核；应保留页图路径和转写责任，不等同可复制官方文本 |
| `official_pdf_download_captcha_pending` | 否 | EGAZ / 官方原始 PDF 下载仍受验证码或登录阻断；不得写成已取得原始 PDF |
| `official_pss_blocked_in_current_environment` | 否 | PSS 在当前网络/浏览器/代理环境中被 412、空白页、登录、验证码或 WAF 阻断；不得写成 PSS 已核验 |
| `third_party_verified` | 是 | Google Patents、Espacenet、WIPO、出版社/DOI 等稳定页已打开且著录项匹配 |
| `npl_verified` | 是 | 非专利文献稳定来源已打开且题名/作者/摘要匹配 |
| `cnipa_result_page_parsed` | 否 | 仅从 CNIPA 公布公告结果页解析到候选；可用于发现，不可单独支撑最终结论 |
| `third_party_not_indexed` | 否 | 第三方稳定源暂未收录，常见于很新的 CN 公开 |
| `commercial_db_discovered` | 否 | 壹专利 / 高数图等商业库结果列表发现候选；可用于内部发现，不可作为公开引用 |
| `commercial_db_content_checked` | 否 | 已在商业库详情页读取摘要、著录项、IPC/CPC 或权利要求；可支撑内部对比，不可作为公开引用 |
| `public_source_verified` | 是 | 已由 CNIPA PSS / Google Patents / Espacenet / WIPO 等公开稳定来源核验，可作为公开引用；也可继续使用 `official_pss_verified` / `third_party_verified` 等细分状态 |
| `unverified` | 否 | 未打开或未完成著录项核对 |
| `failed` | 否 | 打开失败、页面不匹配或来源冲突 |

硬规则：

- `http://epub.cnipa.gov.cn/patent/{公开号}`、二维码 title、搜索会话 URL 等只能写入 `source_hint_url` / `cnipa_qr_or_hint_url`，**不得**写入 `stable_url`、`link` 或交底书 1.1 的公开源 URL。
- 壹专利 / 高数图的学校远程访问 URL、搜索会话 URL、详情面板 URL 和截图编号只能写入案件证据包或 `source_hint_url`，**不得**写入 `stable_url`、`link` 或交底书 1.1 的公开源 URL。
- `stable_url` / `link` 只能来自本轮实际打开并核验过的页面。
- 高相关文献若只有 `cnipa_result_page_parsed`、`commercial_db_discovered`、`commercial_db_content_checked`、`unverified`、`failed` 或 `third_party_not_indexed` 状态，必须进入「未核验清单」；若其影响 A/B/C 结论，结论最高只能为 D 或 partial-D，需公开源或人工/CNIPA PSS 复核。

### 案件目录查新证据包（必做）

除非用户明确只要口头探索，每次正式查新应在**用户项目/案件目录**保存或追加以下材料；不要写入 skill 项目目录：

```text
prior_art_dossier.json      # 结构化命中、来源状态、相同点/区别点
prior_art_dossier.md        # 可读版查新证据包
query_log.md                # 检索式、数据库、时间、异常和降级记录
positive_controls.md        # 至少 3 条高相关阳性对照/种子文献
unverified_sources.md       # 未核验、未收录、失败、需人工复核条目
```

若案件目录尚未确定，先在用户指定输出目录下建立本案子目录；不得把验证成果落到 `patent-unveil-review` skill 文件夹。

可用脚本辅助生成/更新证据包：

```bash
python3 ${CLAUDE_SKILL_DIR}/tools/prior_art_dossier.py --case-dir "{案件目录}" --hits "{EPUB_HITS_JSON文件或记录}" --links "{PATENT_LINKS_JSON文件或记录}" --query "检索词1,检索词2" --note "本轮查新说明"
```

脚本只做结构化留档和来源状态整理，不替代 Agent 对相同点、区别点、阳性对照相关性和 A/B/C/D 的实质判断；生成后仍须补写 `same_points`、`distinguishing_points`、`usable_distinguishing_features` 等分析字段。

## 检索渠道（官方优先，多源复核）

### A. 中国专利公布公告（**优先**，官方站点）

1. **站点**：[国家知识产权局 中国专利公布公告](http://epub.cnipa.gov.cn/)（**仅** `epub.cnipa.gov.cn`）。
2. **工具**（本仓库 `tools/`）：**`cnipa_epub_search.py`** —— **一步**完成公布站检索与结果解析（Playwright 过站点 WAF）；结果页 HTML **仅在内存中处理，不落盘**。成功时终端含 **`EPUB_NOTE:`**（ASCII，如 `html_bytes=… disk=0`）与 **`EPUB_HITS_JSON:`** 一行（JSON 数组：标题、公开号、`cnipa_qr_or_hint_url`、`google_patents_url`、`verification_status`、**`abstract`** 等）。
3. **国知局检索词（生成阶段必做，须在拼 Bash 之前完成）**

   - **拆分责任在 Agent**：在**生成/构造命令阶段**，从本案技术方案、专利点或用户主题中归纳 **2～8 个与方案相关度高的检索单位**，**仅用 ASCII 空格分隔**，再写入 `cnipa_epub_search.py` 的参数。每一单位宜为 **有检索意义的语义块**，例如：**专业术语**、**名词短语**、**名动组合（如「批量调度」「异构调度」）**、**业内固定搭配**；**不要**拆成过碎的单字、泛义双字（如单独 `检索`、`增强`、`系统`、`方法` 等泛词），也**不要**把无关联词硬凑成一串。
   - **禁止**把**无空格的一整句长中文**当作**唯一**参数（例如不要：`".../cnipa_epub_search.py" "知识库检索增强大语言模型"`）。长串在公布站单框内易被当作整句 AND，**极易 0 条**。
   - **Agent 执行时**：**每一轮 `Bash` 只传一个**检索单位（一个词块一句参数）；**2～8 个单位须对应 2～8 次**独立调用，**禁止**在一次工具调用里把多个词块同时作为多个 argv 传给 `cnipa_epub_search.py`（脚本虽支持多词单次进程内合并，**仅供本地/人工**；Agent 为控时、降单次 Playwright 链路与 IDE/终端超时风险，**必须**拆进程）。
   - 示意（须按本案替换；**三次调用、每次一词**）：

     ```bash
     python3 …/cnipa_epub_search.py 知识库
     python3 …/cnipa_epub_search.py 检索增强
     python3 …/cnipa_epub_search.py 大语言模型
     ```

   - **脚本不做**自动分词或自动拆长中文；若确需**整句一次** AND 检索，改用 **`cnipa_epub_crawler.py`** 单传一句。

4. **执行方式**（Step 5 在读完本文件后**先尝试**）：

   ```bash
   pip install -r tools/requirements-cnipa.txt
   python -m playwright install chromium
   # Agent：对上一节每个检索单位各执行一次（示例仅展示首轮）
   python3 ${CLAUDE_SKILL_DIR}/tools/cnipa_epub_search.py 词甲
   ```

   - **合并责任在 Agent**：每次调用解析 **stdout** 上**唯一一行** **`EPUB_HITS_JSON:`** 后的 JSON 数组；在推理中按 **`pub_number`** 为主键去重合并（无则 `cnipa_qr_or_hint_url`，再否则可用标题前缀），得到**一份**总表后先进入 `prior_art_dossier`，再做稳定来源复核。
   - **`cnipa_epub_search.py`** 若人工单次传入多词，会按空白拆段、进程内**一段一查**并去重（**stderr** 可出现 **`EPUB_MERGE:`**）；与 Agent **分多次调用**策略无关。
   - 成功时 **stdout 仅一行** **`EPUB_HITS_JSON:`** + JSON 数组（UTF-8，含中文 `abstract`）；**`EPUB_MERGE:`** / **`EPUB_NOTE:`** / **`EPUB_HINT:`** 等在 **stderr** 且为 **ASCII**（减轻 PowerShell 把中文 stderr 当成错误流）。解析命中时请以 **stdout 该行 JSON 为准**，勿因 stderr 或终端编码误判「未命中」而不必要地降级 WebSearch。Windows 乱码与 PowerShell 注意见 **`INSTALL.md`**（`chcp 65001` / `PYTHONUTF8=1`、勿滥用 `2>&1`）。
   - 将 JSON 中的公开号、标题、摘要和 `cnipa_qr_or_hint_url` 写入查新证据包；**不得**把 `cnipa_qr_or_hint_url` 当作已核验公开源 URL 写入 1.1。后续必须用 Google Patents / Espacenet / WIPO / CNIPA PSS 或人工详情页打开结果进行稳定复核。
   - **补检/换源条件**（满足任一则继续执行 B/C/D 渠道并在 `query_log.md` 记录）：命令非 0 退出、超时、无 Playwright、**`EPUB_HITS_JSON` 为空数组**、或条目经人工核对明显与主题无关。

5. **`abstract` 字段（国知局条目，规定必用）**

   若 **`EPUB_HITS_JSON`** 中某项含非空的 **`abstract`**（解析自公布站结果页摘要），对**该条专利**须同时遵守：

   - **必用**：查新笔记、交底书 **1.1** 中对该专利的**技术方案概括、应用场景与局限性分析**，**必须先基于对该 `abstract` 的完整阅读与理解**后再撰写；**禁止**仅凭标题、公开号或 URL **臆造**方案要点或与摘要矛盾的表述。
   - **充分理解**：在写入 1.1 或查新笔记前，Agent 须在**推理过程内**明确：摘要所涉**技术领域、解决什么问题、核心手段/模块、主要效果或流程**；若摘要与标题存在差异，**以摘要为准**概括该技术。
   - **正文呈现**：交底书 1.1 中**不得**大段逐字粘贴官方摘要（避免抄袭与超字数）；应**消化后**用**自己的话**压缩为「方案概括 + 应用 + 缺点/局限」；查新笔记可保留稍长的摘录供自用核对，但须标注来源于公布站摘要。
   - **缺失时**：若某条 JSON **无** `abstract` 或为空（旧版页面 / 表格布局未解析到等），须在查新笔记中注明「该条无摘要字段」，并改用**已核验详情页**或 **Google Patents** 等可核验来源补全理解后再写 1.1，**不得**留空理由含糊带过。

6. **链接与著录**：CNIPA EPUB 脚本输出的 `cnipa_qr_or_hint_url` 只是提示路径；**禁止**写成国知局详情 URL 或稳定公开源。若仅能从公布站得到公开号，优先用 **`patent_link_verify.py`** 或浏览器打开 **Google Patents** 稳定页 `https://patents.google.com/patent/CN…/zh` / `/en` 复核；仍未收录时标记 `third_party_not_indexed` 并列入未核验清单。

### B. Google Patents / Espacenet / WIPO（高相关文献必做复核）

对所有高相关专利、阳性对照和会影响 A/B/C/D 判断的条目，必须尝试至少一个稳定公开来源复核：

1. **Google Patents URL 复核**：优先运行：

   ```bash
   python3 ${CLAUDE_SKILL_DIR}/tools/patent_link_verify.py --input "{EPUB_HITS_JSON或文件路径}"
   ```

   输出 **`PATENT_LINKS_JSON:`**。其中 `verification_status="third_party_verified"` 的条目可把 `link`/`stable_url` 写入查新笔记和 1.1；`third_party_not_indexed`、`failed` 等不得写为已核验 URL。
2. **Espacenet / WIPO / Google Patents 页面检索**：当公开号 URL 未命中时，用标题、申请人、英文同义词、IPC/CPC 检索；能打开并匹配著录项时标为 `third_party_verified`。
3. **新近 CN 公开号**：若 CNIPA EPUB 命中但 Google Patents 等尚未收录，不要删除该候选；标为 `cnipa_result_page_parsed + third_party_not_indexed`，进入未核验清单。若该条影响最终结论，触发人工/CNIPA PSS 复核。

### C. Google 学术与非专利文献（软件/AI 方向必做）

软件、AI、算法、数据处理类案件须检索非专利文献；其它领域视技术来源决定是否执行。

1. **中文文献与学术**：[Google 学术搜索](https://scholar.google.com)（`scholar.google.com`）。
   - 用**中文关键词**、技术方案核心术语、应用场景；可组合 2–3 组查询。
   - 强化「中国」语境时可加：`中国`、`site:.cn`、`专利`、`CN`（与专利号区分使用）等，以实际命中为准。
   - 通过 **WebSearch** 或浏览器可用能力检索 Scholar；结果中优先选用**可打开、与标题/作者匹配**的条目链接。
2. **英文非专利文献**：优先用英文核心术语、英文同义词、模型/算法名、应用场景检索，稳定来源优先 DOI、出版社页、arXiv、会议官网。
3. **关键词构造**：技术方案核心术语、应用场景与方法名称，可组合 2–3 组查询。AI/RAG/LLM 方向至少覆盖：`RAG`、`retrieval augmented generation`、`LLM question answering`、`knowledge graph question answering`、`vector retrieval`、`reranking` 等与本案相关的词。

### D. CNIPA PSS 官方复核（需要时半自动/人工）

当以下情况出现时，须建议或执行 CNIPA 专利检索及分析系统（PSS）复核；如遇登录、验证码、滑块、WAF，不得绕过，标记 `needs_human_auth` 并给出待复核检索式：

- 关键 CNIPA EPUB 命中无法被第三方稳定来源复核，但会影响 A/B/C 结论。
- 多来源标题、摘要、申请人或公开日冲突。
- 用户要求更高标准的正式查新支撑。
- 最终要给 PASS 且核心区别特征高度依赖某几篇近似专利。

国内官方站点访问注意：

- CNIPA PSS、EPUB、EGAZ 等国内官方站点可能被学校 WebVPN、全局 VPN、海外代理、系统代理或内置浏览器链路破坏，典型表现为 `HTTP 412`、空白 DOM、脚本资源缺失、验证码异常或下载接口失败。此时不要把失败解释为“该专利不存在”。
- 若 PSS 在当前环境被阻断，应记录 `official_pss_blocked_in_current_environment`，并建议用户在本机 Chrome/Edge 中关闭全局 VPN/代理，或对 `*.cnipa.gov.cn`、`*.cponline.cnipa.gov.cn` 设置 DIRECT，必要时用国内手机热点直连后人工下载/截图。
- 若 CNIPA EPUB 官方详情页和 EGAZ 官方页图已经取得，可按实际情况记录 `official_cnipa_epub_detail_opened`、`official_egaz_page_images_archived`、`official_claims_transcribed_from_page_images`；但仍不得写成 `official_pss_verified`，也不得把页图重建 PDF 写成验证码下载的原始 PDF。

### E. 商业专利库辅助检索（壹专利 / 高数图）

商业专利库可作为**候选发现、结果聚类、权利要求快速阅读和内部对比**渠道，但不得直接等同公开稳定引用源。只有在公开来源完成复核后，候选才能写入交底书 1.1 的公开引用。

#### E.1 使用边界

- 只在用户已授权且已打开学校远程访问页面、商业库页面或明确要求使用该资源时操作。
- 只做低频、人工监督下的验证和查新辅助；不批量爬取数据库。
- 优先使用平台自身导出功能；没有导出时，只保存必要截图和少量摘要化记录。
- 遇到验证码、风控、登录异常、按钮提交异常或剪贴板/输入桥失败，停止并记录，不绕过。
- 不上传本地敏感文件，不导出超过验证所需的数据。
- 不自行猜测学校资源公网入口；以用户打开的学校远程访问入口或学校数字资源门户入口为准。

#### E.2 证据状态

商业库候选必须使用下列状态之一，直到公开源复核完成：

| 状态 | 用途 | 公开引用 |
|------|------|----------|
| `commercial_db_discovered` | 商业库结果列表发现候选，已记录检索式、命中数、列表字段和截图编号 | 否 |
| `commercial_db_content_checked` | 已在商业库详情页读取摘要、著录项、IPC/CPC、权利要求或说明书要点 | 否 |
| `public_source_verified` | 已用 CNIPA PSS / Google Patents / Espacenet / WIPO 等公开来源核验 | 是 |

#### E.3 壹专利操作规则

- 入口：使用学校远程访问后的壹专利页面，或从学校数字资源门户检索“壹专利”后点“访问地址”进入。
- 已知公开号反查：优先输入**不带 A/B kind code 的公开号主干**，例如用 `CN115360706` 而不是 `CN115360706B`；若主干命中 A/B 多条，再在结果中选择目标文本。
- 主题发现检索：每轮记录检索式、命中数、查看条数、R2/R3 条数、截图编号和异常；正式查新至少抽取前 20 条。
- 字段读取：R2/R3 候选至少读取标题、公开号、公开日、申请人、摘要、IPC/CPC；若可行，读取独立权利要求要点。
- 检索式调优：`源荷储`、`结算价格` 等宽词适合发现，不适合单独结论；`逐小时 能量台账`、`源荷储 结算价格` 等组合词 0 命中时，只能说明该检索式无结果，不能写成“无相关现有技术”。

#### E.4 相关性分级

商业库候选必须标注 R0-R3：

| 等级 | 判定 |
|------|------|
| R3 强相关 | 技术问题、核心步骤、应用场景至少两项重合，可能破坏新颖性或创造性 |
| R2 中相关 | 场景或部分技术手段相似，可作为创造性对比 |
| R1 弱相关 | 只有关键词或领域相关，不能直接作为主对比 |
| R0 无关 | 误命中 |

#### E.5 写入交底书规则

- 交底书 1.1 正文只放公开稳定来源和简明结论。
- 商业库发现但未公开核验的候选，写入 `unverified_sources.md` 或代理人内部备注，表述为“待 CNIPA PSS / 公开源复核”。
- 商业库截图、学校 VPN URL、检索会话 URL 只能作内部证据，不得作为 `stable_url`。

#### E.6 内容核验后的正文回写

用户已授权并打开壹专利/高数图，且本轮问题涉及“中国公开专利文献是否经专利平台查询确认”时，Agent 应主动完成可自动化的低频查询、详情读取和证据落盘，不得笼统回答“留给代理人/用户复核”。若已读取结果行、摘要、著录项/IPC 和权利要求页签，可将该文献标为 `commercial_db_content_checked`，并同步回写交底书 1.1.2、1.1.3 和待补充材料。

推荐 1.1.2 说明句：

```text
下表中国公开专利文献已通过壹专利商业库完成内容核验，核验内容包括检索结果行、摘要、主著录项/IPC 分类号和权利要求页签；商业库会话 URL 仅作为内部查新证据，不作为正式公开引用来源。正式申请文件中的公开引用仍建议以 CNIPA PSS、中国专利公布公告或其他稳定公开来源闭环。
```

推荐表格状态列：

```text
壹专利已完成商业库内容核验；正式公开引用仍建议以 CNIPA PSS、中国专利公布公告或其他稳定公开来源闭环
```

只有在确实尚未完成商业库内容核验时，才写“商业库仅作内部发现或内容检查”。`commercial_db_content_checked` 可以支撑内部查新对比、代理人沟通和区别特征理解，但仍不得伪装成 `public_source_verified` 或正式法律检索意见。

## 分析要求

对检索到的、与方案**高度相关**的现有专利或公开文献逐项概括：

- 专利号 / 文献标识
- 技术方案要点（**若为国知局 JSON 且含 `abstract`，要点须与摘要理解一致**，见上文「`abstract` 必用」）
- 应用场景
- **局限性**
- **来源状态（必填）**：每一条必须写明 `verification_status`。只有 `official_pss_verified`、`official_detail_opened`、`third_party_verified`、`npl_verified` 可写稳定公开 URL；其它状态须写入未核验清单，不得伪装为已核验链接。

### 最小对比表（必做）

对高相关文献至少输出下表，供 Step 3-4 回写和 Step 7 第一章使用：

| 文献 | 相同点 | 不同点 | 可用区别特征 | 对授权影响 | 来源状态 | URL/待复核 |
|------|--------|--------|--------------|------------|----------|------------|
| 公开号/标题 | 与本案相同或接近的技术问题、步骤、结构、模块 | 本案与其不同之处 | 可写入本案方案和权利要求布局的真实区别 | 低/中/高/待确认 | `third_party_verified` 等 | 经核验链接；或“未核验，见 unverified_sources.md” |

“可用区别特征”必须同时满足：

- 来自用户材料、代码、图纸、实验、仿真或可合理推断的技术方案，不得为绕开现有技术而临时编造。
- 能够和“要解决的技术问题”及“技术效果”形成对应关系。
- 不是单纯用途变更、对象替换、字段改名、界面展示变化或商业规则变化，除非其与技术手段协同并产生技术效果。

### 阳性对照 / 种子文献门禁（必做）

正式查新报告必须至少列出 **3 条高相关阳性对照/种子文献**（专利或非专利文献均可，但应优先专利）。每条记录：

```text
pub_number / paper_id
title
applicant_or_author
publication_date
stable_url
verification_status
observed_title
observed_abstract_short
why_relevant
covered_features
verification_time
```

若无法找到 3 条高相关且稳定复核的阳性对照，或阳性对照均未完成稳定来源复核，本轮查新**最高只能给 D**；不得给 A/B。若因领域非常新导致公开文献极少，应在 D 结论中说明检索范围、失败来源和下一步人工/代理人复核建议。

### A/B/C/D 查新决策分级（必做）

在检索总结前给出本案或每个候选方向的等级：

| 等级 | 含义 | 后续动作 |
|------|------|----------|
| A | 未发现相同或实质相同公开方案，区别特征和技术效果初步成立 | 可进入 Step 7；仍须写明检索范围和公开检索局限 |
| B | 存在相似公开方案，但本案可用区别特征清楚，技术效果可强化 | 可进入 Step 7，但第一章、第二章、第四章和第五章须围绕区别特征收紧 |
| C | 高度相似，或主要区别特征弱/不可实施/技术效果不足 | 不应按原方向直接撰写；须改写、缩小为真实区别点或放弃主方向 |
| D | 检索不足、来源不可核验、结果过少/过宽、关键数据库无法访问或判断证据不足 | 不得给出“可授权”式结论；须补检、换检索式或交由代理人/人工复核 |

若不同候选方向等级不同，应逐项列明，不得用一个总评级掩盖高风险方向。

A/B/C/D 还受来源状态约束：

- A/B：必须有足够检索范围、至少 3 条高相关阳性对照、主要高相关文献具备稳定 URL 或官方复核证据；允许少量新近 CNIPA 候选未被第三方收录，但不得影响结论核心。
- C：可以基于稳定来源确认“高度相似”或“区别特征弱”；若高度相似文献仅有未核验候选，不应直接判 C，应判 D/partial-D 并要求复核。
- D：出现以下任一情形即为 D 或 partial-D：关键文献不可核验、只有 CNIPA EPUB 结果页候选、正负样本不足、检索式过窄/过宽、CNIPA/PSS 登录或验证码阻断、稳定来源标题/摘要冲突、无法说明 18 个月公开盲区外的检索覆盖。
- 不得把“某个检索词超时/0 命中”写成“没有相关现有技术”；应记录为该检索词失败或无结果，并换词/换源补检。

### 链接来源与格式（须准确）

| 类型 | 推荐 URL 形式 | 说明 |
|------|----------------|------|
| 美国等专利（公开出版物号） | `https://patents.google.com/patent/US20240118920A1/en` | 将 `US20240118920A1` 替换为实际公开号；以 Google Patents 页面能打开且标题/摘要匹配为准。 |
| 中国专利 | **`https://patents.google.com/patent/CNXXXXXXXXXA/zh`** 或 `/en`；官方 PSS 已复核时可写官方稳定入口/截图编号 | **禁止**把 `http://epub.cnipa.gov.cn/patent/CN...`、二维码 title、会话 URL 写成稳定 URL。Google Patents 未收录的新近公开须列入未核验清单。 |
| CNIPA EPUB 候选 | 不写入稳定 URL；只写 `cnipa_qr_or_hint_url` | 仅表示从官方公布公告结果页解析到候选，不代表详情页已打开。 |
| 学术论文（含 Scholar） | Scholar 条目页、出版社官方页或 **`https://doi.org/10.xxxx/...`** | Scholar 链接若重定向或镜像，以最终可长期解析的 DOI/出版社页为准。 |
| arXiv 预印本 | `https://arxiv.org/abs/2008.09213` | `abs` 页为规范条目页；勿用未经验证的镜像域名冒充官方。 |
| 期刊 / 会议 | 出版社 DOI：`https://doi.org/10.xxxx/...` 或官方摘要页 | 以 DOI 解析后页面与文献一致为准。 |

文末给出：**检索总结**与**本发明与现有技术的本质区别**，与 1.1 结尾及 1.2 缺点呼应。

### 查新后回写（必做）

完成 Step 5 后，必须回到 `patent_points_analyzer.md` 的 Step 3-4 表格，更新：

- 查新风险等级 A/B/C/D。
- 推荐方向是否变化：主推不变、降级、改写、放弃或待补检。
- 可用区别特征：从对比表提炼，不得凭空新增。
- 建议保护策略：保留四客体、收缩为方法+系统、收缩为系统/装置、拆分为两件申请或暂缓；策略必须服从查新结果和材料支撑。
- 是否进入 Step 7：A/B 通常可进入；C 需先改写；D 需先补检或人工复核。

交底书后续章节必须服从该回写结果。若查新后发现主方向风险升高，必须在撰写前调整方向或向用户说明需要补充材料。

## 记录习惯

便于写进交底书：保留专利号、标题、**消化摘要后的**一两句方案概括（有 **`abstract`** 时概括须可追溯至该摘要）；每条另起一行或表格列给出「稳定 URL / 来源状态 / 待复核说明」。避免大段抄袭权利要求或整段粘贴官方摘要。

交底书 **1.1 正文**只放对代理人有用、可复核的稳定来源和简明结论；`query_log.md`、`prior_art_dossier.md`、`unverified_sources.md` 保留完整检索过程、失败来源和未核验候选。若某条文献未核验但必须提醒代理人关注，可写为“另有 CNIPA 公布公告结果页候选 CN...，尚待官方详情页复核”，不得附不可打开链接冒充证据。

### 1.1「检索说明」写法（交付正文，必遵）

写入交底书 **1.1** 开头的「检索说明」时，面向**代理人/审查员**表述，**不要**暴露 Agent 查新流程或本仓库工具实现。

- **须写**：实际使用的**公开数据库或渠道名称**（如「国家知识产权局专利公布公告系统」「Google Patents」「Espacenet」「Google Scholar」）、本案**主要检索词**（与 Step 5 用词一致或概括）；若部分条目经 **Google Patents** 等公开页复核著录项，可一句带过。
- **须诚实说明**：若存在关键未核验候选或第三方未收录新近 CN 文献，1.1 中用简短句子提示“尚待 CNIPA PSS/代理人复核”，不要把 D/partial-D 包装成确定结论。
- **禁止写入 1.1 正文**：脚本/文件名（如 **`cnipa_epub_search.py`**、**`cnipa_epub_crawler.py`**）、「查新优先使用…检索工具」「是否触发 Google 学术降级」、Playwright、WebSearch、Agent、技能仓库名等**内部或流程元信息**。
- **示例（须按本案替换检索词与渠道）**：

  > 检索说明：在**国家知识产权局专利公布公告系统**及 **Google Patents** 中，以「批任务调度」「异构集群调度」「任务队列重排」「负载感知调度」等为检索词进行检索；部分条目的公开文本与著录项以 Google Patents 页面复核。

查新笔记（Agent 内部或对话留档）仍可记录是否调用脚本、是否降级 WebSearch；**上述内容不得原样抄进交底书 1.1**。
