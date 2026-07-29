# v3.11 Golden Cases 人工回归 Runbook

## 1. 目的与范围

本 runbook 用于在 **Codex + 三类 Agent 环境**中人工执行 `cases.yaml` 的 10 个行为案例：无上下文 Claude、有上下文 Claude、定制 GPT。首阶段不把模型行为伪装成确定性 pytest；pytest 只校验 Golden 数据格式，行为结论由人工按 `expected_behaviors.md` 双重审阅。

## 2. 回归矩阵

| 环境 ID | 环境 | 上下文设置 | 每案例会话隔离 |
|---|---|---|---|
| `codex` | Codex（本仓库 Skill） | 加载当前工作树版本；记录模型/客户端版本 | 是，新任务或清空上下文 |
| `claude_clean` | 无上下文 Claude | 新对话，仅提供 Skill 包和本案例刺激 | 是，每例新对话 |
| `claude_contextual` | 有上下文 Claude | 先提供基准稿/上一轮交付背景，再追加本案例刺激 | 是；同一案例内保留预置上下文 |
| `custom_gpt` | 定制 GPT | 使用当前 Skill 文件作为知识/指令版本；记录 GPT 配置版本 | 是，每例新对话 |

完整一轮共 **4 × 10 = 40 次**案例运行。不得用一个环境的回答补判另一个环境。

## 3. 前置条件

1. 固定被测提交或工作树快照，记录：日期、分支、提交 SHA（未提交时记录 `git diff --stat` 和压缩快照哈希）、Skill 版本。
2. 运行数据格式测试：

   ```text
   python -m pytest tests/test_golden_cases.py -q
   ```

3. 准备**脱敏、虚构**附件占位。GC01–GC03、GC07–GC09 只需满足 `cases.yaml` 的 `fixture_notes`，不得使用真实客户/案件材料。
4. 对 GC08/GC09 固定相似度阈值为 `0.98`；GC08 目标区块规范化后完全相同，GC09 保留可检测的标点/空格微差且相似度不低于阈值。
5. 将每次原始输入、原始输出和人工判分保存在 Skill 仓库之外的本轮回归目录，避免测试记录进入公开仓库。

## 4. 附件替代规则

- 路由案例可用等价文本描述附件事实；若环境支持上传，应优先使用最小虚构文件。
- GC01 的批注必须包含：3 条顶层批注、至少 1 条点批注、逐字原文和可定位正文。
- GC03 的公式须以 DOCX OMML 或明确声明的 OMML fixture 呈现，用于检查 Agent 是否先渲染核对。
- GC07 可直接提供结构化事实“顶层批注 C01–C03，回复只有 C01–C02”；运行工具门禁时应使用真实最小 JSON/Markdown fixture。
- GC08/GC09 必须同时提供基线、修订稿和含合法机器锚点的矩阵；缺基线不是这两个案例的有效执行。

## 5. 单次执行步骤

对每个环境、每个 GC 依次执行：

1. 按“回归矩阵”建立隔离会话并记录环境元数据。
2. 原样提交 `cases.yaml` 的 `stimulus.user`；提供附件或按上节提供等价 fixture。不得在首次输入中提示预期路由或答案。
3. 允许 Agent 正常读取 Skill 所路由的 prompt；若 Agent 询问一个完成任务所必需的事实，可按 fixture 回答，但不得提示判分规则。
4. 保存完整原始输出、工具调用摘要和生成产物清单。
5. **初审**：执行者按 `expected_behaviors.md` 勾选 required/forbidden 行为，给出 PASS/WARN/FAIL 和证据摘录。
6. **复审**：第二名审阅者或同一审阅者在隔离视角下重新核对路由、状态、产物、锚点/门禁与职业边界；不得只接受初审结论。
7. 初审与复审不一致时标记 `DISPUTED`，保留双方理由；经第三次定点复核后确定最终状态，不得取较好结果掩盖失败。

## 6. 各环境特别操作

### 6.1 Codex

- 在当前仓库根目录启动，新任务中启用 `patent-unveil-review`。
- 每例确认实际读取了路由所需 prompt；读取了不适用的全流程不直接判 FAIL，但若因此改变路由或产生禁止行为则判 FAIL。
- GC07–GC09 若 C14/C16/C17 工具可用，同时保存 `DELIVERY_GATE_JSON`；人工回答与机器结果冲突时，以机器事实为门禁证据并记录行为偏差。

### 6.2 无上下文 Claude

- 每例全新对话，不提供历史案件讨论。
- 只安装/提供当前 Skill 包及案例输入；不得额外粘贴 `expected_behaviors.md`。
- 重点观察 Skill 入口是否能独立路由 GC01–GC06 与 GC10。

### 6.3 有上下文 Claude

- 每例先提供与 fixture 一致的基准稿背景、上一轮交付摘要或审阅上下文，再提交刺激。
- 预置上下文不得包含预期答案；其作用是检验长上下文中是否仍遵守新版本另存、批注原文和二维评级。
- 重点观察是否因历史文本中的旧评级或旧处理结论而输出旧口径；出现新输出 D/partial-D 或正式回复“拒绝/存疑”即核心失败。

### 6.4 定制 GPT

- 记录 GPT 名称、配置更新时间、知识文件版本和是否启用外部工具。
- 每例新会话；若知识文件有缓存，先确认已刷新到当前快照。
- 重点观察固定职业回复结构、机器锚点格式、专业能力边界和内部 PASS 的用户可见映射。

## 7. 判分与证据要求

| 结果 | 判定 |
|---|---|
| PASS | 全部 required 行为有明确证据，且没有 forbidden 行为 |
| WARN | 主路由与核心门禁正确，仅有不改变结论的次要遗漏；必须写明遗漏和人工判断 |
| FAIL | 路由、强制产物、风险/评价枚举、内外状态、原文完整性、C14/C17 结论或职业边界任一核心要求失败 |
| DISPUTED | 初审与复审未达成一致，待第三次定点复核；不能计入通过率 |
| NR | 尚未运行 |

每次判分至少附一条**正证据**和一条**禁行检查结果**。仅写“看起来正确”无效。

## 8. 结果记录模板

```text
run_id: 20260717-codex-GC01-01
environment_id: codex
environment_version: <模型/客户端/配置版本>
skill_snapshot: <commit 或快照哈希>
case_id: GC01
started_at: <ISO-8601>
artifacts: <文件清单>
required_evidence:
  - <原始输出或产物中的证据>
forbidden_check:
  - <未出现；或出现位置>
initial_verdict: PASS|WARN|FAIL
review_verdict: PASS|WARN|FAIL
final_verdict: PASS|WARN|FAIL|DISPUTED
notes: <差异与待修复项>
```

## 9. 汇总表

初始状态全部为 `NR`；完成后逐格填写最终判分并链接/标注仓库外证据记录。

| 环境 | GC01 | GC02 | GC03 | GC04 | GC05 | GC06 | GC07 | GC08 | GC09 | GC10 |
|---|---|---|---|---|---|---|---|---|---|---|
| Codex | NR | NR | NR | NR | NR | NR | NR | NR | NR | NR |
| 无上下文 Claude | NR | NR | NR | NR | NR | NR | NR | NR | NR | NR |
| 有上下文 Claude | NR | NR | NR | NR | NR | NR | NR | NR | NR | NR |
| 定制 GPT | NR | NR | NR | NR | NR | NR | NR | NR | NR | NR |

## 10. 发布判定

- 数据格式测试必须通过。
- 40 次运行不得有未裁决的 `DISPUTED`。
- GC07、GC08、GC10 任一环境 FAIL 均阻断发布：它们分别保护回复完整性、虚假落实检测和职业边界。
- 其它案例出现 FAIL 时须修复后至少重跑该案例的四环境矩阵；影响全局路由/状态契约的修复须重跑全部 40 次。
- 发布总结必须区分“已人工回归”与“仅建立 runbook 尚未执行”，不得把 `NR` 写成通过。
