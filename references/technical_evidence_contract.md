# 技术证据合同（生成前置结构化产物）

> 来源：一次测量诊断类案件 16 条代理批注的复盘（提取问题特征，不绑定案情）。共性根因：skill 虽要求写清输入/处理/输出，但**生成正文前没有强制形成一份「技术事实—观测能力—证据职责—决策逻辑」合同**，导致 AI 写出「语言完整、技术跳步」的方案——聚合级数据直接定位到单体内部、标准参考曲线被当成现场实时响应、一种证据包办定位归因决策、正文写「同时满足」流程图画「任一满足」。

## 与方案骨架的关系（避免重复）

- v3.9.0 的**方案骨架**（`disclosure_builder.md`「方案骨架先行」）是最小合同：步骤 ID/输入/操作依据/输出/异常分支/公式/类别，适用于所有主流程案件。
- **测量、诊断、定位、状态识别、多模态证据类案件**（凡输出包含「定位/识别/归因/判定某物理对象状态」且输入为传感/量测数据的），骨架**必须升级为本合同**：在骨架字段之上增加观测层级、可声称精度、基线登记、阈值来源、下游消费者、降级分支和特征分类。
- 模板：**`templates/technical_evidence_contract.yaml`**；落盘于案件目录（如 `技术证据合同_{案件代号}.yaml`），属内部产物，**不入正文**；正文各章节由合同展开。
- 机器校验：`tools/delivery_gate.py` **C12**（须 pyyaml；见下「机器可校验项」）。

## 字段要求与填写规则

| 字段组 | 关键字段 | 规则 |
|---|---|---|
| 粒度等级表 | `meta.granularity_scale`（rank/level） | 由撰写人按本案定义（领域无关），rank 越大越精细；是「声称精度 ≤ 观测精度」校验的标尺 |
| 基线登记 | `baselines[]`：id/kind/source/purpose/valid_scope/update_condition/fallback | kind 四类：`standard`（厂家/标准条件参考）、`historical_clean`（历史洁净）、`post_treatment`（处置后复测）、`healthy_peer`（同类健康统计）。**标准参考基线只能作对比参考且须校正，不得写成现场当前观测**；每条基线写明不可用时的替代方案 |
| 决策条件表 | `decisions[]`：id/logic/condition/output | **单一事实源**：AND/OR 只在此处显式写出；正文、模块说明、流程图、保护点一律引用 D 编号，不得各写一套（防「正文 AND、流程图 OR」漂移） |
| 步骤条目 | `steps[]`：inputs（source 标 raw/derived:Sx/baseline:BLx/external）、observation_rank、output_rank、validity_check、processing、thresholds（含 source）、outputs、consumers、degraded_branch、claim_class | 见下逐条 |

**步骤条目逐条规则**：

1. **观测能力先行**：`output_rank ≤ observation_rank`——先确定能测到什么，再决定能声称什么。聚合级输入只能声称「筛查到聚合组/候选单体+置信度」；唯一定位须先引入更细粒度证据（分段量测、影像、配准数据）并在 inputs 中体现，才允许提升 output_rank。
2. **基线与现场观测分开登记**：凡与基线对比的步骤，inputs 中基线用 `baseline:BLx` 引用登记表，不与当前观测混写；正文措辞区分「参考基线」与「当前现场响应」。
3. **阈值必须有来源**：`thresholds[].source` 非空——实测标定/仿真样本/规格书/行业标准，或显式写「示例值，待现场标定」；禁止无来源的裸数值（与 `disclosure_builder.md` 模糊限定词门禁、C11 联动）。
4. **输出必须被消费**：`consumers` 指向下游步骤或 `terminal`；出现无人消费的输出说明步骤链断裂。
5. **降级分支必填**：缺失、冲突、多候选、低置信度时的处理不能空白——真实数据一定会出现「不能确定」，方案须设计「证据不足/证据冲突/无法唯一定位」的输出（引用 D 编号）。
6. **特征分类决定去向**：`claim_class` 四类——`independent_core` 进独权主线；`dependent` 进从属；**`implementation_param`（采样周期、示例阈值、设备配置等）不得进入独权**，独权上位化为「按照预设周期」「预设阈值」，具体值写实施例/从属（与 §8.1「过窄参数不入独权」同源，此处前移到生成前分类）；`auxiliary_evidence` 是验证手段，不作为区别主线。
7. **物理关系登记来源**：拓扑、配准、映射关系类输入标 `external` 并在 validity_check 写明物理来源（结构版型、连接关系、标定/配准依据），**不得由算法临时臆测**。

## 机器可校验项（C12）与语义项（§8.1）分工

- **C12（确定性，机器）**：必填字段完整性、claim_class/kind 枚举、`output_rank ≤ observation_rank`、`baseline:BLx`/`derived:Sx`/consumers/D 编号引用完整性、thresholds source 非空、输出未消费（WARN）。
- **§8.1（语义，AI/人工）**：标准基线是否被写成现场观测、观测能力是否真正支撑声称（rank 只是自报，语义上还要核对传感配置）、证据职责是否越界（见 `observability_and_multimodal_evidence.md`）、降级分支是否真实可执行。**语义判断不得用正则直接 FAIL**。

## 生成顺序

```text
用户材料 → 技术证据合同（观测能力/基线/决策表/特征分类，发明人确认）
→ 方案骨架各视图展开（3.2/3.3/3.4/第五章）
→ Step 8 自检（§8.1 语义核对）+ delivery_gate C12/C13/C15（机器）
```

合同未固化前不进入正文生成；合同中「待发明人确认」项未清零时交付最高 WARN。
