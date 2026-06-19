<div align="center">

# patent-unveil-review

> 面向**工程方法、软件系统、数据处理与控制测算**类中国发明专利：从项目代码、算法、工程工具或方案文档到**代理人审稿就绪的技术交底书**。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![Node.js](https://img.shields.io/badge/Node.js-mermaid%2Fmmdc-339933.svg)](https://nodejs.org/)
[![AgentSkills](https://img.shields.io/badge/AgentSkills-Standard-green)](https://agentskills.io)

<br>

有工程工具、算法流程或测算代码，但**专利点还没梳**？<br>
交底书要**系统框图、流程图、公式和四客体保护思路**，还要**代理人能直接改的 Word**？<br>
定稿之后还要**多轮补材料、纠错**，并希望**文件修改追溯**？<br>
国知局公布站检索，期望 **次次爬成功、精准检索**？

**本 Skill 按 AgentSkills 约定编排全流程，`SKILL.md` + `prompts/` 分步可读可迭代。**

[功能特性](#功能特性) · [安装](#安装) · [Codex 快速安装](CODEX_INSTALL.md) · [使用](#使用) · [项目结构](#项目结构) · [示例](#示例) · [参考文档](#参考文档) · [详细安装说明](INSTALL.md) · [技能入口](SKILL.md)

</div>

---

## 功能特性

> **适用范围**：工程方法、软件系统、数据处理、控制测算、工程仿真/测算工具类中国发明专利。结构/机械类仅提供有限辅助：需用户自备工程附图与物理机理依据，最高 WARN，不承诺创造性评估。

<!-- 使用 HTML 表格：GitHub 上 Markdown 管道表会因右侧长路径/URL 把左列挤窄导致中文换行 -->
<table>
<colgroup>
<col width="1%">
<col>
</colgroup>
<thead>
<tr><th align="left" nowrap width="1%">能力</th><th align="left">说明</th></tr>
</thead>
<tbody>
<tr><td nowrap width="1%"><strong>项目扫描</strong></td><td>按优先级读文档 / 代码；<code>.docx</code> / <code>.pptx</code> 先转 Markdown 再扫（见 <code>prompts/project_scan.md</code>）</td></tr>
<tr><td nowrap width="1%"><strong>专利点</strong></td><td>候选点讨论与融合，并按技术问题、区别特征、技术效果、实施支撑和方案成熟度做授权可行性初筛（<code>patent_points_analyzer.md</code>）</td></tr>
<tr><td nowrap width="1%"><strong>查新</strong></td><td><strong>优先</strong> <a href="http://epub.cnipa.gov.cn/">国知局 · 中国专利公布公告</a>（<code>tools/cnipa_epub_search.py</code>）；异常或无果时降级 WebSearch（Google 学术 / Patents）。输出 A/B/C/D 风险等级、可用区别特征，并回写推荐方向（<code>prior_art_search.md</code>）</td></tr>
<tr><td nowrap width="1%"><strong>交底书成稿</strong></td><td>脱敏模版 + <strong>mermaid</strong> 系统框图与流程图；默认按方法 + 系统/装置 + 电子设备 + 存储介质组织保护点；<code>mermaid_render.py</code> → PNG，默认再出 <strong>.docx</strong>；公式写为 Word 可编辑 OMML，并由 <code>qa_docx_math.py</code> 做残留 LaTeX 与编号检查</td></tr>
<tr><td nowrap width="1%"><strong>交付命名</strong></td><td>凡落盘交付：<code>{案件名}_{YYYYMMDDHHmmss}.md</code> 与同名 <code>.docx</code>（<code>disclosure_builder.md</code> §7.3）</td></tr>
<tr><td nowrap width="1%"><strong>自检</strong></td><td>逻辑闭环、公式与参数一致、诚信非编造、PASS/WARN/FAIL 代理人审稿门禁（<code>disclosure_self_check.md</code>，不写入正文）</td></tr>
<tr><td nowrap width="1%"><strong>迭代</strong></td><td><strong>合并</strong> / <strong>纠正</strong> 另存新文件；<code>交底书修订对话记录.md</code> 逐条追加（<code>iteration_context.md</code>、<code>iteration_dialog_log.py</code>）</td></tr>
<tr><td nowrap width="1%"><strong>交付留档</strong></td><td>每次交付在案件目录追加 <code>交底书交付检查记录.md</code>，记录状态、文件、待补项和检查摘要（<code>delivery_check_log.py</code>）</td></tr>
</tbody>
</table>

**Office 抽取**：`.docx` / `.pptx` 先用本仓库 `docx_to_md.py` / `pptx_to_md.py` 转为 Markdown 再扫描（见 `SKILL.md`）。

**Python 依赖（分文件）**：
- **基础（Office / 交底书转换）**：根目录 [`requirements.txt`](requirements.txt) — `pip install -r requirements.txt`
- **查新（国知局公布公告站，可选）**：[`tools/requirements-cnipa.txt`](tools/requirements-cnipa.txt) — `pip install -r tools/requirements-cnipa.txt`，再执行 `python -m playwright install chromium`  
  不装亦可：Step 5 将按 `prior_art_search.md` 仅用 **WebSearch** 降级。详见 [INSTALL.md](INSTALL.md)、[tools/README.md](tools/README.md)。

---

## 安装

### Codex

将完整的 `patent-unveil-review` 文件夹放到 Codex skills 目录，确保 `SKILL.md` 位于技能文件夹根级：

| 系统 | 推荐路径 |
|------|----------|
| Windows | `%USERPROFILE%\.codex\skills\patent-unveil-review\` |
| macOS / Linux | `~/.codex/skills/patent-unveil-review/` |

若拿到的是 zip 包，直接解压到 `~/.codex/skills/` 下即可；安装后重启 Codex 或开启新线程，再用「工程方法专利挖掘」「技术交底书」「查新」或 `patent-unveil-review` 触发。详见 [CODEX_INSTALL.md](CODEX_INSTALL.md)。

### Claude Code

> 请在 **git 仓库根目录** 或全局 skills 路径下放置本目录，使 `SKILL.md` 位于技能文件夹根级（与 [INSTALL.md](INSTALL.md) 一致）。

```bash
# 示例：安装到当前项目的 skills 目录
mkdir -p .claude/skills
git clone <本仓库 URL> .claude/skills/patent-unveil-review
```

### Cursor

将本仓库完整内容放到 Cursor 约定的 skills 路径（见 [INSTALL.md](INSTALL.md) 表格），重启后在 **Settings → Rules** 中确认技能已被发现。

### 依赖

```bash
# 基础（Office 转换、交底书相关 Python 包）
pip install -r requirements.txt
```

```bash
# 可选：国知局查新（epub.cnipa.gov.cn）
pip install -r tools/requirements-cnipa.txt
python -m playwright install chromium
```

图示定稿另需 **Node.js**；在 `tools/` 下执行 `npm install` 或使用 `npx mmdc`（详见 [tools/README.md](tools/README.md)）。

---

## 使用

在 Agent 中用自然语言描述需求即可，例如：

- 专利挖掘、专利点、**技术交底书**、查新、现有技术对比  
- 斜杠指令（视宿主配置）：如 `/patent-unveil-review`、`/交底书`

建议同时说明 **项目路径** 或 **技术主题**（与 `SKILL.md` 中 `argument-hint` 一致）。主流程最适合工程测算工具、软件系统、数据处理流程、控制策略、识别方法等；纯结构/机械方案会进入有限辅助通道。  
**查新（Step 5）** 会优先通过 [中国专利公布公告](http://epub.cnipa.gov.cn/) 检索中国专利公开信息，再按需补充其他来源；流程见 `prompts/prior_art_search.md`。  
在**已有交底书文件**上补充材料或纠错时，无需说「迭代」——技能会按 `merger.md` / `correction_handler.md` 处理；细则见 [SKILL.md](SKILL.md)。

---

## 项目结构

本仓库遵循 [AgentSkills](https://agentskills.io)，根目录即一个 skill：

```
patent-unveil-review/
├── SKILL.md                    # 入口：触发条件、工具表、步骤与 prompts 引用
├── prompts/                    # 分步模板（Agent Read 后遵循）
│   ├── intake.md
│   ├── project_scan.md
│   ├── patent_points_analyzer.md
│   ├── prior_art_search.md
│   ├── disclosure_preview.md
│   ├── disclosure_builder.md
│   ├── disclosure_self_check.md
│   ├── iteration_context.md
│   ├── merger.md
│   ├── correction_handler.md
│   └── template_reference.md
├── tools/                      # mermaid_render、md_to_docx、docx_to_md、pptx_to_md；国知局 cnipa_epub_*；iteration_dialog_log、delivery_check_log 等
├── docs/                       # PRD、仓库结构说明
├── examples/                   # 原材料示例（如 example_batch_job_scheduler/knowledge/）
├── references/                 # 工程方法/软件系统参考、结构有限辅助参考、法规来源索引
├── requirements.txt
├── LICENSE
├── INSTALL.md
└── .gitignore
```

---

## 示例

虚构扫描原材料见 [examples/README.md](examples/README.md)（如 `examples/example_batch_job_scheduler/knowledge/`）。  
专利点、查新笔记、交底书等**完整产物**由流程生成到本地 **`outputs/{案件标识}/`**。

## 参考文档

- [技能入口与 Agent 流程](SKILL.md)（触发条件、`prompts/` 映射、工具表）
- [详细安装说明](INSTALL.md)（Claude Code / Cursor 路径）
- [图示与转换脚本](tools/README.md)（mermaid / mmdc、Word 导出、国知局 epub 查新工具）
- [示例案件与原材料说明](examples/README.md)
- [产品流程与目录约定](docs/PRD.md)
- [工程结构说明](docs/skill-structure.md)
- [工程方法与软件系统类专利撰写参考](references/method_system_patent_guide.md)
- [交底书模版细则](prompts/template_reference.md)

---

<div align="center">

MIT License © [mordecairegular](https://github.com/mordecairegular)  
Based on patent-disclosure-skill by [handsomestWei](https://github.com/handsomestWei/).

</div>
