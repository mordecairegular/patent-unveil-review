# 任务规格：tools/delivery_gate.py 统一交付门禁（v3.8.0）

> 委托方：Claude（主协调器）。执行方：Codex。验收方：Claude 复核 + 用户。
> 背景：现有交付门禁散落在多个脚本与 60+ 项 prompt 清单中，执行率依赖执行器自觉，Codex 端缺陷穿透率高（实案：占位符"待填写"随稿交付、"若干格点"未量化且分项不加总、`long_sparse_direct` 字段被公式化截断、分段公式压成一行、确认点被跳过无痕迹）。本工具把全部**机器可校验**门禁收敛为一条命令。

## 1. 目标与边界

- **一条命令**完成全部机器可校验检查，汇总 PASS/WARN/FAIL，自动追加 `交底书交付检查记录.md`，输出一行 `DELIVERY_GATE_JSON`。
- **只读检查 + 写检查记录**：不重新生成 docx、不渲染 mermaid、不联网。
- 执行器无关：Claude Code 与 Codex 用同一命令、同一标准。
- **不做**：深度语义审查（逻辑、创造性判断仍走 prompt 清单与人）；不修改被检文件。

## 2. CLI

```text
python tools/delivery_gate.py --case-dir <案件目录> --md <交付.md> --docx <交付.docx>
    [--manifest <formula_manifest.yaml>]
    [--numeric-spec <numeric_check.json>]
    [--entry direct|t0]            # 默认 direct
    [--t0-dir <候选池目录>]         # entry=t0 时边界卡/主题卡所在目录，默认=case-dir
    [--preview-skipped]            # 用户明确跳过确认点4时传入，记录"预览未经用户确认"
    [--whitelist-file <extra.txt>] # 每行一个正则，追加占位符白名单
    [--skip <check_id>]            # 可多次，跳过指定检查（跳过项记入 JSON 的 skipped）
    [--no-record]                  # 不写交付检查记录（调试用）
```

退出码：**0=PASS，1=WARN，2=FAIL**。任何内部异常按 FAIL 处理并输出可读错误。

## 3. 检查项（check_id 固定）

| id | 名称 | 严重级 | 内容 |
|----|------|--------|------|
| C1 | docx_math_qa | FAIL | 以子进程或 import 调用现有 `tools/qa_docx_math.py`（带 `--check-formal-text`；给了 `--manifest` 则透传）。非 0 → FAIL，摘要并入输出。**不得复制其逻辑**，只复用。 |
| C2 | placeholder_scan | WARN | 对 `.md` 全文与 docx 提取文本扫描占位符：`待填|待补充|待确认|待核|TODO|TBD|\[待填写\]|【待填写】`；`若干` **只在 markdown 表格行内**扫描（正文叙述中的"若干"合法，不报）。**身份字段白名单（内置）**：行首匹配 `^\s*[-*]?\s*\*{0,2}(姓名|电话|邮箱|技术联系人|发明人|申请人)` 的行允许出现 `（用户自填）|\[待填写\]|待填写`，不计缺陷，**汇入 user_fill 清单**（写进交付记录"用户自填清单"）。`待核（provenance-only` 属数值门禁合法状态：记 WARN 备注，不升级。命中非白名单占位符 → WARN 并逐条列出（文件、行号、内容）。 |
| C3 | count_closure | WARN | 解析 `.md` 中的 markdown 表格：若存在首列为 `合计|总计|共计` 的行，对**其余行全为数值**的每一列求和并与合计值比对（容差：整数精确、含小数按 1e-6 相对误差）；不匹配 → WARN，输出表位置、列名、期望/实际。非数值列跳过。 |
| C4 | field_label_integrity | FAIL | 在 `.md` 源中提取**多下划线标签** `\b[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+){2,}\b`（≥2 个下划线，如 `long_sparse_direct`）；每个标签必须在 docx 提取文本中**原样出现**（含全部下划线）。缺失或变形（下划线被吃掉，说明被转成下标/斜体）→ FAIL。另：任一 `m:oMath` 的拼接文本若为纯小写 ASCII 字母、长度 ≥12、无数字与运算符且含 ≥2 层 `m:sSub` → WARN（疑似字段标签被公式化，启发式）。 |
| C5 | formula_paragraph | FAIL/WARN | 解析 `word/document.xml`：① 任一 `w:r` 的 `w:color` 为 `FF0000`（或 `w:val="red"`）→ **FAIL**（渲染报错残留红字）；② 单个 `m:oMathPara` 内含 >1 个 `m:oMath` → **WARN**（多式挤同段，疑似分段公式被压扁），输出段落序号与式数。 |
| C6 | filename_convention | WARN | `--md`/`--docx` 文件名须匹配 `^.+_\d{14}\.(md|docx)$` 且两者主名一致；不符 → WARN。 |
| C7 | confirmation_artifacts | WARN | 确认点产物存在性（G12 轻量版）：**所有入口**——确认点3：`{case-dir}/prior_art_search/prior_art_dossier.md` 存在且内容含 `确认点 3` 或 `签核`；确认点4：`{case-dir}` 下存在 `预览确认记录*.md`，或传了 `--preview-skipped`（此时在记录中写"预览未经用户确认"）。**entry=t0 额外**——`{t0-dir}` 下存在 `*边界卡*.md`（确认点1）与 `*主题卡*.md`（确认点2）。缺失 → WARN，逐项写明"确认点X未见落盘产物"。 |
| C8 | numeric_reproduce | FAIL | 传了 `--numeric-spec` 时调用现有 `tools/qa_numeric_reproduce.py`；非 0 → FAIL。未传：JSON 中记 `"not_applicable"`。 |
| C9 | version_report | 信息 | `git -C <skill根目录> log -1 --format=%h_%cs`（skill 根 = 本脚本所在 tools/ 的父目录）+ CHANGELOG.md 首个 `## v` 行 → 写入 JSON 与交付记录（不判级）。git 不可用时记 `"unknown"`，不报错。 |

汇总规则：任一 FAIL → 总状态 FAIL；无 FAIL 有 WARN → WARN；否则 PASS。`--skip` 跳过的检查不参与汇总但必须列入 `skipped`。

## 4. 输出

1. **stdout**：逐检查一行 ASCII 前缀日志（`[C2] WARN: 3 placeholder(s) ...`），最后一行：
   `DELIVERY_GATE_JSON {"status":"WARN","fails":[],"warns":[{"check":"C2","items":[...]}],"user_fill":[...],"skipped":[],"version":"0f73413_2026-07-08","md":"...","docx":"..."}`
   （`json.dumps(..., ensure_ascii=True)`；启动时 `sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")`，兼容 GBK 控制台。）
2. **交付检查记录**：默认调用现有 `tools/delivery_check_log.py`（子进程或 import）向 `{case-dir}/交底书交付检查记录.md` 追加一条：status、检查摘要（含各检查结论与版本自报）、待补项（warns+user_fill）、artifacts（md/docx 文件名）。

## 5. 新增模板

`templates/preview_confirmation.template.md`（中文文件名版权衡后用 ASCII 文件名，模板首行注明落盘时应命名为 `预览确认记录_{YYYYMMDD}.md`）。字段：案件名称、记录时间（本地+UTC）、预览文本要点（300–500 字预览的摘录或指针）、保密边界确认结果、关键事实确认结果、保护方向确认结果、用户答复摘要、（或）跳过声明。

## 6. 实现约束

- Python ≥ 3.10；**仅用标准库 + 仓库现有依赖**（docx 解析用 `zipfile` + `xml.etree`/正则，参考既有 `tools/qa_docx_math.py` 的做法；不得新增第三方依赖）。
- Windows 路径与中文文件名安全（`pathlib`，打开文件显式 `encoding="utf-8"`，docx 内 XML 按 UTF-8）。
- 复用不复制：C1/C8 调既有工具；追加记录走 `delivery_check_log.py`。
- 代码风格与现有 tools/ 一致；函数级可测试（每个检查一个纯函数，接受路径/文本，返回结构化结果）。

## 7. 测试（pytest，加入 tests/）

`tests/test_delivery_gate.py`，纯本地、不依赖网络/mmdc/Word：

- fixtures：用 `zipfile` 手工构造最小 docx（`[Content_Types].xml` + `word/document.xml`），参考既有测试的构造方式；md 用 tmp_path 写文本。
- 用例至少覆盖：C2 命中+身份白名单放行+`若干`仅表内命中；C3 合计匹配/不匹配；C4 标签完整/被吃下划线→FAIL；C5 红字→FAIL、多式同段→WARN；C6 命名不符；C7 缺预览记录→WARN、`--preview-skipped` 放行；汇总状态与退出码（0/1/2）；`DELIVERY_GATE_JSON` 可被 `json.loads` 解析。
- **既有测试必须全部保持通过**（当前 42 项）。

## 8. 演示（写入 dev log）

在 `outputs/sample_case_v380/`（outputs/ 已被 .gitignore 忽略）构造：
1. 合规样例（干净 md+docx+预览记录）→ 运行 gate → PASS，退出码 0；
2. 缺陷样例（含"待填"占位、合计不符、缺预览记录）→ WARN/FAIL 按规则，退出码正确。
两次运行的 `DELIVERY_GATE_JSON` 原样写入 `outputs/dev_log_v380.txt`。

## 9. 提交纪律（分支 feat/v3.8.0-delivery-gate）

1. **commit 1（必做）**：`tools/delivery_gate.py` + `tests/test_delivery_gate.py` + `templates/preview_confirmation.template.md` + 本规格文件。
2. **commit 2（可选，低风险才做）**：`tools/md_to_docx.py` 防护——多下划线字段标签（≥2 下划线）不做 OMML 下标转换，保持普通文本；须附回归测试。没把握就不做，留待复核后处理。
3. **commit 3（草稿）**：SKILL.md 与 `prompts/disclosure_self_check.md` §8.5 的接线草稿——把"交付前必须跑 delivery_gate 且非 FAIL"写为唯一交付入口。此 commit 仅为草稿供 Claude 复核，允许被改写。
- **禁止 push；禁止改动 main；结束时 `git status` 干净**（outputs/ 忽略件除外）。

## 10. 验收标准（复核时逐条核）

- [ ] `python -m pytest -q` 全绿（既有 42 + 新增）；
- [ ] 演示两例退出码与 JSON 正确，已写入 `outputs/dev_log_v380.txt`；
- [ ] C1–C9 语义与本规格一致；`--skip`/白名单/`--preview-skipped` 生效；
- [ ] 无新依赖；未修改既有工具行为（commit 2 除外且带测试）；
- [ ] 分支提交结构符合 §9。
