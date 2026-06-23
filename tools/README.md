# tools / 可选脚本

本目录存放**可重复执行的辅助脚本**。技能主流程以 `SKILL.md` 与 `prompts/` 为准；本目录侧重格式转换等可执行工具。

## 国知局公布公告检索（epub.cnipa.gov.cn，Step 5 查新优先）

| 脚本 | 作用 |
|------|------|
| **`cnipa_epub_search.py`** | **（Step 5 优先）** 一步：拉取 + 解析，**不写结果页 HTML 落盘**；**Agent 须按 `prior_art_search.md` 分多次调用、每轮一词并自行合并 JSON**；脚本在**单次命令多词**时也会进程内循环检索并合并（人工/本地便利）；**stdout 仅一行** `EPUB_HITS_JSON:`；stderr 上 `EPUB_*` 为 **ASCII**；UTF-8 / PowerShell 见 **INSTALL.md**。输出默认是 `cnipa_result_page_parsed` 候选，不代表稳定详情页已打开。 |
| **`cnipa_epub_crawler.py`** | 仅 Playwright 拉取并**默认保存**结果页 HTML；stdout 亦含 **`EPUB_HITS_JSON:`**。 |
| **`cnipa_epub_parse.py`** | 仅解析已保存的 HTML：`python tools/cnipa_epub_parse.py path/to/_last_result_xxx.html`；字段含标题、公开号、`cnipa_qr_or_hint_url`、`google_patents_url`、`verification_status`、**`abstract`**（若有）。`link` 只保留给已核验稳定 URL，本解析器默认不填。 |
| **`patent_link_verify.py`** | 读取 JSON 数组或含 `EPUB_HITS_JSON:` 的终端记录，尝试打开 Google Patents `/zh`、`/en` 稳定页，输出 **`PATENT_LINKS_JSON:`**。只有 `verification_status="third_party_verified"` 的条目可把 `link`/`stable_url` 写入查新报告或交底书 1.1。 |
| **`prior_art_dossier.py`** | 在用户案件目录生成/更新 `prior_art_dossier.json`、`prior_art_dossier.md`、`positive_controls.md`、`unverified_sources.md`、`query_log.md`。输入可为 `EPUB_HITS_JSON` / `PATENT_LINKS_JSON` 文件或终端记录；只做留档整理，不替代实质查新判断。 |

依赖：`pip install -r tools/requirements-cnipa.txt` 与 `python -m playwright install chromium`。环境变量见各脚本文件头。默认结果 HTML 落在 **`tools/_last_result_*.html`**（已 `.gitignore`）。

抓取失败、解析无命中或命中未核验时，Agent 按 **`prompts/prior_art_search.md`** 继续执行稳定来源复核与补检（Google Patents / Espacenet / WIPO / Google 学术等）。不得把 `http://epub.cnipa.gov.cn/patent/CN...` 或二维码 title 写成已核验公开源。

---

## Office 文档（Word / PPT）转成可扫描文本

用本仓库 **`docx_to_md.py`**、**`pptx_to_md.py`**（纯 Python + 仓库根目录 `requirements.txt`），见下文各节；与 `SKILL.md`「工具与数据来源」一致。

## mermaid_render.py — mermaid：图示 → PNG + 定稿 Markdown + **默认生成 Word**

将 fenced **mermaid**（`` ```mermaid`` ``）逐块交给 **`mmdc`** 渲染为 PNG；输出 `.md` 中**保留** mermaid 围栏源码，并追加可见 Markdown 图片引用 ``![图示 n](mermaid_figures/…)``，供 Markdown 预览和 **`md_to_docx.py`** 同时显示/嵌入图示（Word **仅**嵌 PNG，不写 mermaid 代码块）。**3.2 系统框图**与 **3.4 流程图**均用 mermaid（`flowchart` / `subgraph` 等），交底书正文**不再**要求单独的文字框图或 PlantUML。

**生图失败降级**：某一围栏 `mmdc` 失败时**不中断 Markdown**——该处**保留**原 `` ```mermaid`` … `` ``` `` 源码；其余块照常出图。若本轮需要 Word，脚本会停止并返回失败，**不会**继续生成含 mermaid 源码或 **Consolas** 代码块的定稿 `.docx`。修正 mermaid 语法或 `mmdc`/Chrome 环境后重跑。

### 依赖：mermaid（须 Node.js + `mmdc`）

| 方式 | 安装 | 说明 |
|------|------|------|
| **本地 npm（推荐）** | **Node.js** + 本目录 `npm install`（见 `package.json`） | 优先使用 `tools/node_modules/.bin/mmdc`，避免每次 npx 拉包 |
| **npx** | 未执行 `npm install` 时由脚本调用 `npx -y @mermaid-js/mermaid-cli mmdc` | 首次可能较慢 |
| **全局 npm** | `npm install -g @mermaid-js/mermaid-cli` | 提供 **PATH** 上的 `mmdc` |

mermaid 脚本按顺序查找：`tools/node_modules/.bin/mmdc` → **PATH** 上的 `mmdc` → `npx`。

生成 Word 仍需：`pip install -r requirements.txt`（与上表无关）。

**npm 推荐（本地 CLI）**：

```bash
cd tools
npm install
```

`package.json` 已包含 **`puppeteer`**（`@mermaid-js/mermaid-cli` 的 peer）。**Puppeteer 23+** 可能不会在 `npm install` 时自动下载浏览器；若自检或 `mmdc` 报错 **Could not find Chrome**，在 **`tools/`** 再执行：

```bash
npx puppeteer browsers install chrome-headless-shell
```

（或按报错提示选用 `chrome` 等；详见 [Puppeteer 文档](https://pptr.dev/)。）

### mermaid CLI 与手动试转

**`mermaid_render.py` 与 11.x 一致**：在 **`mmdc -i <.mmd> -o <.png> -b white`** 基础上默认追加 **`-s 2 -w 1400 -H 1050`**（更高像素密度与视口，系统框图在 Word 中更清晰）。需要再锐化可 **`--mmdc-scale 3`**（PNG 更大）；恢复接近旧版可 **`--mmdc-scale 1 --mmdc-width 800 --mmdc-height 600`**。  
若某处写的是 `npx -y @mermaid-js/mermaid-cli -i …`，**少了子命令 `mmdc`**，参数会错位；正确示例：

```bash
npx -y @mermaid-js/mermaid-cli mmdc -i sample.mmd -o sample.png -b white
```

可自建极简 `sample.mmd`（如一行 `flowchart LR; A-->B`）试转；能出 PNG 则说明 **mmdc + Chrome** 正常，否则按上文安装 **`puppeteer` 浏览器**。

### 用法

```bash
# 写出定稿 .md，并在同目录生成同名 .docx（默认）；-o 须为「案件名_YYYYMMDDHHmmss.md」（见 prompts/disclosure_builder.md §7.3 第 5 点）
python3 tools/mermaid_render.py -i draft.md -o "一种XXX方法及系统_20260408143025.md"

# 指定 .docx 路径（.md 主名仍须含时间戳）
python3 tools/mermaid_render.py -i draft.md -o out/一种XXX方法及系统_20260408143025.md --docx out/一种XXX方法及系统_20260408143025.docx

# 仅 Markdown，不要 Word
python3 tools/mermaid_render.py -i draft.md -o "一种XXX方法及系统_20260408143025.md" --no-docx

# 更高清晰度（可选）
python3 tools/mermaid_render.py -i draft.md -o "…定稿.md" --mmdc-scale 3 --mmdc-width 1600 --mmdc-height 1200

# 指定 mermaid 图片子目录（相对输出 .md）
python3 tools/mermaid_render.py -i draft.md -o out/一种XXX方法及系统_20260408143025.md --assets-dir figures/mermaid
```

**Word 生成或 DOCX QA 失败**（缺依赖、版式报错、公式/图示残留等）时：脚本返回非零退出码；Markdown 可能已经写出，可用于排障，但不得把失败 DOCX 当定稿交付。stderr 会打印 **`md_to_docx.py` 的手动命令**，可在修复环境后重跑。

Windows 上若仅装 Node 未执行 `npm install`，脚本会通过 `npx -y @mermaid-js/mermaid-cli mmdc` 调用（首次可能较慢）。

### 与交底书约定

- 技能要求定稿**同时**交付 **Markdown + Word**，且 **`-o` 主文件名须含 `_{YYYYMMDDHHmmss}`**（`prompts/disclosure_builder.md` §7.3 第 5 点，含首次定稿）；**3.2 系统框图**与 **3.4 流程图**均用 fenced mermaid，**不要** ASCII 文字流程图或框图。
- 交付代理人前：运行 `mermaid_render.py` 一步即可（默认再调 `md_to_docx.py` 并执行 DOCX 交付 QA）；若 mermaid、Word 生成或 QA 失败，命令返回非零，须修正后重跑，不得交付失败 DOCX。

---

## math_render.py — LaTeX 公式 → PNG（旧版兼容）

默认定稿链路**不再**使用本脚本处理公式。`md_to_docx.py` 会将 Markdown 中的 **LaTeX 公式**（``$...$`` / ``\\(...\\)`` 行内；``$$...$$`` / ``\\[...\\]`` 块级）写入 Word 原生 **OMML 可编辑公式**。

本脚本仅作旧版兼容：显式需要图片公式时，可用 **matplotlib mathtext** 渲染为 PNG；**保留 LaTeX 原文**，图片引用写入 HTML 注释 ``<!-- ![...](math_figures/...) -->``（Markdown 预览不显示图）。

**Mermaid 框图**：``mermaid_render.py`` **保留** `` ```mermaid`` 源码，并追加可见 ``![图示 n](mermaid_figures/...)``；旧版隐藏 HTML 注释图示在重跑时会规范为可见图片行。

**mathtext 兼容**：渲染前自动将常见 LaTeX 简写映射为 mathtext 符号（如 ``\ge``→``\geq``、``\le``→``\leq``、``\land``→``\wedge``）；块级式内**换行压成一行**、``\tag{1}`` 转为式末 ``(1)``；仍无法解析的公式保留原文。

**失败降级**：本脚本仅用于旧版图片公式流程。正式链路中公式由 `md_to_docx.py` 写为 OMML，并由 `qa_docx_math.py` 检查；若 DOCX 中残留 LaTeX 命令或代码样式公式，QA 会失败。

**Word 版式**：默认公式为可编辑 OMML，不是图片；**mermaid 框图/流程图**仍按 **5.5×8.2 英寸**上限等比嵌入。只有显式启用旧版 PNG 公式流程时，公式图才会作为图片插入。

### 依赖

```bash
pip install -r requirements.txt   # 含 matplotlib
```

### 用法

```bash
python3 tools/math_render.py -i draft.md -o draft_with_math.md
python3 tools/math_render.py -i draft.md -o out.md --assets-dir math_figures
```

定稿流水线：**``mermaid_render.py`` 默认只渲染 mermaid 图示**，公式保留 Markdown/LaTeX 源码并由 `md_to_docx.py` 写成 Word 可编辑 OMML。若确有旧版兼容需求，可显式传入 ``--math-png`` 生成公式 PNG。

---

## md_to_docx.py — Markdown → Word

将交底书 Markdown 转为 `.docx`，**`#`–`######` 映射为 Word 内置「标题 1」–「标题 9」**，正文为宋体 10.5pt，代码块为 Consolas。定稿交付通常不应包含代码块；若 DOCX QA 检出 Consolas/代码样式，默认判 FAIL，避免未渲染图示或代码式公式进入 Word。

**图示**：定稿应用 **`mermaid_render.py`** 将 mermaid 转为 PNG。本脚本不调用 `mmdc`；若直接用本脚本处理仍含 `` ```mermaid`` 的 Markdown，未渲染源码会按代码块进入 Word，并被默认 DOCX QA 判为 FAIL。

### 依赖

```bash
pip install -r requirements.txt
```

依赖为 `python-docx`（见仓库根目录 `requirements.txt`）。保存 DOCX 后默认运行 `qa_docx_math.py`；正式交付不得使用 `--skip-math-qa` 或 `--allow-code-style`。

### 用法

```bash
python3 tools/md_to_docx.py --input path/to/交底书.md --output path/to/交底书.docx
python3 tools/md_to_docx.py -i path/to/交底书.md -o path/to/交底书.docx --math-manifest templates/patent_formula_manifest.yaml
python3 tools/md_to_docx.py -i path/to/交底书.md -o path/to/交底书.docx --min-media-count 2
```

图片 `![](相对路径.png)`：默认相对 **Markdown 文件所在目录**；也可指定根目录：

```bash
python3 tools/md_to_docx.py -i ./outputs/case/disclosure.md -o ./outputs/case/disclosure.docx --base-dir ./outputs/case
```

**插图**：对 PNG/GIF/JPEG 会读取像素尺寸，在默认 **最大宽 5.5" × 最大高 8.2"** 内**等比缩放**并同时指定 `width`/`height`，避免竖长流程图仅按宽度放大后**高度超出版心**、打印或阅读时像被裁切。可按纸张边距调整，例如：

```bash
python3 tools/md_to_docx.py -i a.md -o a.docx --image-max-width-inches 6 --image-max-height-inches 9
```

在 Claude Code 中可将 `tools` 换为 `${CLAUDE_SKILL_DIR}/tools`。

### 支持的 Markdown 子集

| 元素 | 行为 |
|------|------|
| `#`–`######` | Word 标题 1–9 |
| 段落 | 宋体正文，支持 `**粗体**`、`` `行内代码` ``；反引号内若是 `B_{s,t}^{tot}` 这类数学符号，会按公式处理而不是代码样式；**相邻非空行（中间无空行）各自成段**，「（1）…（2）…」会分行显示 |
| `-` / `*` 列表 | 项目符号列表 |
| `1.` 列表 | 字面局部编号段落（不使用 Word 自动编号，避免跨章节续号） |
| ` ``` ` 围栏 | 等宽代码块 |
| `\| 表格 \|` | 简单表格（Table Grid）；单元格内 ``\\(...\\)``、``$...$``、``<!-- -->`` 及 ``\\|`` 中的 ``|`` **不会**被当作列分隔符 |
| `> ` | 左缩进引用 |
| `---` 等 | 浅色分隔线 |
| `![](path)` | 嵌入图片（路径需存在；默认宽/高上限内等比缩放；公式不走图片，mermaid/普通图才走图片） |
| `$` / `\\(...\\)` / `$$` / `\\[...\\]` LaTeX | 写入 Word 原生 OMML 可编辑公式；若 Markdown 已含旧版公式 PNG 注释，Word 仍优先采用可编辑公式并跳过公式图片 |
| 整行裸公式，如 `E(r) = V_sys / [r · ln(R_socket/R_pin)]`，可带下一行单独 `(5)` | 自动升级为块级 OMML 公式；裸下划线变量转为下标，单独编号转为右侧编号结构 |

块级公式含 `\tag{1}`、行末普通编号 `(1)` 或下一行单独编号 `(1)` 时，`md_to_docx.py` 使用无边框两列表格排版：左列公式居中，右列编号右对齐，不依赖空格对齐。普通 `1.` 有序列表也按字面编号写入普通段落，不进入 Word 自动编号结构。

传入 `--math-manifest` 时，`md_to_docx.py` 会在转换阶段按 manifest 中 `display: true` 公式顺序，为未显式 `\tag{}` 的块级公式自动补右侧编号；随后再用同一个 manifest 做编号缺失/重复 QA。

---

## qa_docx_math.py — DOCX 交付 QA

扫描 `.docx` 内部 `word/document.xml` 的可见文本、OMML 结构、代码样式和 `word/media/` 资源，作为交付前门禁。文件名沿用历史名称，但当前检查范围已经覆盖公式和图示交付问题。

### 检查内容

- `math_block_count`：OMML 公式数量。
- `media_count`：DOCX 内嵌资源数量；`--min-media-count N` 可要求至少嵌入 N 个图示/图片。
- `code_style_count`：检测 DOCX XML 中的 Consolas/代码样式；默认 FAIL，排障时可用 `--allow-code-style` 放行。
- `word_auto_numbering_count`：检测 Word 自动编号结构 `<w:numPr>`；默认 FAIL，避免局部列表跨章节续号。
- `suspicious_text_count` / `failed_patterns`：发现 `frac{`、`mathrm{`、`\(`、`\)`、`\[`、`\]`、`begin{`、`end{`、`$`、裸下划线变量、LaTeX 命令残留，或 `flowchart TB` / `graph TD` 等未渲染 mermaid 源码则 FAIL。
- `equation_number_count`：识别 `(1)`、`(2)` 等编号；传入 manifest 时检查缺失与重复。
- 结构校验：manifest 中含 `\frac` 时要求 DOCX 内存在 `<m:f>`；含上下标时要求存在 OMML script 结构。

### 用法

```bash
python3 tools/qa_docx_math.py outputs/case/交底书.docx
python3 tools/qa_docx_math.py outputs/case/交底书.docx --manifest outputs/case/formula_manifest.yaml
python3 tools/qa_docx_math.py outputs/case/交底书.docx --manifest outputs/case/formula_manifest.yaml --min-media-count 2
python3 tools/qa_docx_math.py outputs/case/交底书.docx --json
```

输出首行为 `PASS` 或 `FAIL`。`FAIL` 时不得交付该 DOCX；先修 Markdown LaTeX、manifest、mermaid 渲染或转换链路后重跑。

**未完整支持**：复杂嵌套列表、HTML 块、脚注、任务列表等。定稿前请运行 **`mermaid_render.py`**；若仅用外部工具导出 PNG，可直接写 `![](...)`，并用 `--min-media-count` 校验 DOCX 内确有图片资源。

### 页面级视觉 QA

XML QA 是必要门禁，但不能替代版式视觉检查。若环境可用 Microsoft Word 或 LibreOffice/soffice，建议导出 PDF 或页面图后抽查图示缩放、表格换行、公式视觉效果；若环境不可用，应在 `交底书交付检查记录.md` 中声明未做页面级视觉 QA，并建议人工打开 Word 复核。

### 版式说明（md_to_docx）

- 不同语言 Word 中「标题 1」显示名可能为「Heading 1」或「标题 1」，样式仍为大纲级别标题，可用导航窗格与目录域。
- 若需所内固定模版（页眉、首页不同），可在本脚本生成后套用单位 `.dotx`，或后续扩展 `python-docx` 打开模版再写入。

---

## iteration_dialog_log.py — 修订对话记录（迭代用）

每轮 **`merger.md` / `correction_handler.md`** 交付后，在**案件目录**追加一条 **`交底书修订对话记录.md`**：含**本地时间与 UTC**、用户说明摘要、本轮交付文件名、合并/纠正摘要摘录。规则见 **`prompts/iteration_context.md`**。

**依赖**：仅标准库。

```bash
python3 tools/iteration_dialog_log.py --case-dir outputs/某案件 --kind merge \
  --user "补充了调度装置资料，合并进第三章" \
  --summary "已扩写 3.4，并更新实施例；未改保护点表述。" \
  --artifacts "一种XXX方法及系统_20260408143025.md,一种XXX方法及系统_20260408143025.docx"
```

- `--kind`：`merge` 或 `correct`。  
- `--log-name`：可选，默认 `交底书修订对话记录.md`；英文环境可改用 `disclosure_revision_log.md`。  
- 无法执行脚本时，由 Agent 按同结构手工追加。

---

## delivery_check_log.py — 交付检查记录（每次交付用）

每次向用户落盘交付 `.md` / `.docx` 后，在**案件目录**追加一条 **`交底书交付检查记录.md`**：含**本地时间与 UTC**、`PASS` / `WARN` / `FAIL`、本轮交付文件、检查摘要、待补项和下一步建议。规则见 **`prompts/disclosure_self_check.md` §8.5** 与 **`prompts/iteration_context.md`**。

**依赖**：仅标准库。

```bash
python3 tools/delivery_check_log.py --case-dir outputs/某案件 --status WARN \
  --summary "查新等级 B，区别特征已回写；章节完整，技术效果需实验补强。" \
  --pending "补充正式附图；补充实验数据或仿真结果" \
  --artifacts "一种XXX方法及系统_20260408143025.md,一种XXX方法及系统_20260408143025.docx" \
  --checks "1.1 URL 已核验；无内部流程残留；图示已渲染。" \
  --next "交代理人复核权利要求布局。"
```

- `--status`：`PASS` 表示代理人审稿就绪；`WARN` 表示阶段稿可交付但有待补项；`FAIL` 表示不得作为定稿交付。  
- `--log-name`：可选，默认 `交底书交付检查记录.md`；英文环境可改用 `disclosure_delivery_check_log.md`。  
- 该文件跟随具体案件目录，不写入技能本体，也不复制进交底书正文。

---

## docx_to_md.py — Word → Markdown + 抽取图片

将 **.docx**（Word / WPS 等另存为 docx）转为 **Markdown**，并把文档内嵌图片落到磁盘，便于 **`Read` 与 Step 2 扫描**（与直接读二进制 .docx 相比更稳）。**Step 2** 对扫描树内**每一个** `.docx` 都应先转换再读产出 `.md`，见 `prompts/project_scan.md`。

### 依赖

与 `md_to_docx` 共用根目录 `requirements.txt`（`python-docx` + **`mammoth`**）。

```bash
pip install -r requirements.txt
```

### 用法

```bash
python3 tools/docx_to_md.py --input path/to/设计说明.docx --output outputs/case/design.md
```

- 默认图片目录：`outputs/case/design_media/`，Markdown 内为相对路径 `![](design_media/img_0001.png)`。
- 自定义图片目录：

```bash
python3 tools/docx_to_md.py -i ./raw/spec.docx -o ./knowledge/spec.md --media-dir ./knowledge/spec_assets
```

转换警告（如部分样式、WMF 图）会输出到 **stderr**，仍可能生成可用 `.md`。

### 局限（mammoth）

- 仅 **`.docx`**（OOXML）；老版 **`.doc`** 不支持。
- **Markdown 输出在 mammoth 侧标记为 deprecated**，复杂排版可能弱于「先导出 HTML 再转 MD」；专利扫描一般足够。若版式崩坏，建议所内 **另存为 PDF 或纯文本** 再扫。
- **WMF/EMF** 等 Windows 图元可能需单独处理（见 [mammoth WMF 配方](https://github.com/mwilliamson/python-mammoth)）。

在 Claude Code 中可将 `tools` 换为 `${CLAUDE_SKILL_DIR}/tools`。Windows 无 `python3` 时用 `python`。

---

## pptx_to_md.py — PowerPoint → Markdown + 抽取图片

将 **.pptx** / **.ppsx** 按**幻灯片页**导出为 Markdown，并抽取幻灯片中的**嵌入位图**（`PICTURE` 形状），便于 **`Read` 与 Step 2 扫描**。**Step 2** 对扫描树内**每一个** `.pptx` 均应先转换再读 `.md`，见 `prompts/project_scan.md`。

### 依赖

根目录 `requirements.txt` 中的 **`python-pptx`**。

```bash
pip install -r requirements.txt
```

### 用法

```bash
python3 tools/pptx_to_md.py --input path/to/评审材料.pptx --output outputs/case/review.md
```

- 默认图片目录：`outputs/case/review_media/`，文件名形如 `slide03_img0001.png`。
- 自定义图片目录：

```bash
python3 tools/pptx_to_md.py -i ./raw/deck.pptx -o ./knowledge/deck.md --media-dir ./knowledge/deck_media
```

每页输出二级标题 `## 第 N 页`，其后为该页形状中的**文本与表格**（简化为管道表）及图片引用；若存在**演讲者备注**，以「**备注**」小节附于该页末尾。

### 局限（python-pptx）

- 仅 **`.pptx` / `.ppsx`**（OOXML）；**`.ppt`** 不支持，请先另存。
- **图表、SmartArt、嵌入 OLE** 等若未以普通图片形状存在，**不会**自动栅格化为 PNG；可先在 PowerPoint 中另存为图片或导出 PDF 作补充材料。
- 文本按形状遍历顺序输出，与视觉阅读顺序可能略有差异。

在 Claude Code 中可将 `tools` 换为 `${CLAUDE_SKILL_DIR}/tools`。Windows 无 `python3` 时用 `python`。

---

## 扩展其它脚本时

- Word / PPT 转换依赖写在 `requirements.txt`。
- 在 `SKILL.md`「工具与数据来源」表中增加一行调用说明。
- 勿将密钥写入仓库；配置使用环境变量或用户主目录。
