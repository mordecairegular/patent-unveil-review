# CHANGELOG — patent-unveil-review

基于 `patent-disclosure-skill` v1.8.9 与 `patent-disclosure-skill-cch` v2.0.0 改造，当前重点转向“授权可行性优先”的专利挖掘、查新、交底书生成与交付留档流程。

---

## v3.12.1 (2026-10-27) - Consistency fixes after the v3.12.0 merge (no new gates)

Patch release. Fixes three places where v3.12.0 contradicted itself; adds no new gate, rating level, or workflow step.

- **Producer filename suffix now passes the delivery gate**: SKILL.md G2 already allowed parallel outputs named `{规范化案件名}_{YYYYMMDDHHmmss}_{producer}`, but `delivery_gate.py` C6 only accepted `_{14 digits}` and downgraded such deliveries to WARN, so they could never reach 代理人审稿就绪. C6 now accepts an optional `_{producer}` (ASCII letters, digits, hyphen). The canonical naming rule (`disclosure_builder.md` §7.3 points 4–5) and the `disclosure_self_check.md` filename item now state the same optional suffix. New test: `test_filename_convention_accepts_optional_producer_suffix`.
- **CNIPA access wording made consistent**: `prior_art_search.md` §A and the `cnipa_epub_search.py` CLI description said "Playwright 过 WAF", contradicting §D/§E.1 ("遇验证码/风控/登录不得绕过"). Both now say the tool waits for the site's own page check to complete in the browser and stops on CAPTCHA, login, rate limiting, or an automation ban. Wording-only; crawler behavior is unchanged.
- **Stale release notes corrected**: removed the v3.12.0 note about a second v3.12.0 lineage to be reconciled — that was resolved on 2026-08-14 (PR #2 merged as v3.12.0; PR #1 closed unmerged). REVISION_LOG Rev.3 test count corrected from 68/68 to the shipped 70/70.
- Tests: 71/71 (70 prior + 1 producer-suffix filename test).

---

## v3.12.0 (2026-08-14) - Absorb v3.11 consolidation onto the v3.10 line + drafting/revision-checklist gaps

Consolidation-focused release on the v3.10.0 base. It folds in the v3.11 "simplification / consistency" line (no separate v3.11.0 entry on this branch) and the maintainer's drafting/revision optimization checklist, and deliberately keeps out the heavier C16/C17 anchor-diff gate machinery. (The parallel v3.12.0 on the `agent/attorney-revision-hardening` branch, PR #1, was closed unmerged on 2026-08-14; this entry is the only v3.12.0.)

- **Protection-object single source of truth**: `references/method_system_patent_guide.md` §三 is the sole authority for the (optional) five protection objects via a machine-readable `protection-objects` block (`default_objects` + `allow_reduction: true`), stated up front as a menu, not a mandate. `tests/test_protection_objects_consistency.py` guards against drift; fixed real four-vs-five-object drift across README/SKILL/PRD/skill-structure/disclosure_preview/prior_art_search/intake/template_reference and added the missing 计算机程序产品 block to the claim template.
- **Slim SKILL.md (204 → 117 lines)**: replace the 15 version-history blocks and the 40-line master checklist with positioning, five intent modes (mine/search/draft/revise/full), global invariants G1–G8, an execution contract, and Prompt/Reference/Tool routing tables; per-stage completion criteria stay in their prompts and `disclosure_self_check.md` §8; version history now lives only in this CHANGELOG. Host-neutral relative tool paths; G2 allows coexisting `_{producer}` outputs and does not force a single "final" doc or file hashes.
- **User-facing delivery labels**: internal PASS/WARN/FAIL map to 代理人审稿就绪 / 阶段稿 / 未达到交付条件.
- **Drafting/revision gaps** (maintainer optimization checklist): background convergence (one core problem → one main effect, no scattered sub-problems/effects); single reproducible embodiment is enough (input → process → output → verifiable conclusion), no stacked parallels; spec↔claims linkage ("changed the claims" ≠ "finished the patent" — keep 发明内容/有益效果/附图说明/实施例 complete and consistent); two revision-delivery modes (AI edits directly, or a Chinese-typeset operation-instruction doc — new `templates/revision_instructions_zh.template.md` with 原文-改为 tables and Word-native formulas); editable vector figures (SVG/PPT, not only PNG) when the recipient must edit; core-canon single source (terms/symbols/keep-drop/baseline numbers fixed once, consistent across spec/claims/drawings); scope discipline (don't force-fit method-irrelevant local material — confirm first).
- **Desensitization completion**: removed the residual real-case formula chain the v3.10.0 pass missed (DOCX-math fixtures, `test_md_to_docx_omml.py`, `template_reference.md`); generic `B_{s,t}^{tot}` energy-state examples kept as OMML/dimension illustration.
- **Fail-closed formula QA** (the one low-bloat gem cherry-picked from the `agent/attorney-revision-hardening` branch): `qa_docx_math.py` now scans OMML-only math text for LaTeX commands silently downgraded to plain text (swallowed backslash — `\sqrt`→`sqrt`, plus `\varphi`/`\tilde`/`\zeta`/…); with a formula manifest, unknown long alphabetic identifiers fail closed, while manifest identifiers and common math abbreviations are allowed. Deliberately NOT taken from that branch (conflict with the anti-bloat goal): the C16/C17 anchor-diff gates, the nine-type anchor taxonomy, multi-source attorney import, the A/B/C/D→grade+status split, and the golden/host-adapter/lesson-writeback infrastructure.
- Tests: 70/70 (63 prior + 5 protection-object consistency + 2 fail-closed formula QA).

---

## v3.10.0 (2026-07-15) - Technical evidence contract + observability/multimodal-evidence gates

Second-wave retrospective on the 16-comment case (identifiers kept out of this public repo). Root cause behind the surface issues ("undefined terms, unclear steps, contradictory conditions"): the skill demanded input/processing/output clarity but never forced a pre-drafting **"technical facts — observation capability — evidence responsibility — decision logic" contract**, so the AI could write "linguistically complete, technically leaping" schemes — aggregate-level measurements claimed to localize inside a unit, a manufacturer standard-condition curve conflated with the live field response, one modality doing screening+localization+attribution+decision at once, body text saying AND while the flowchart drew OR.

- **Technical evidence contract (`templates/technical_evidence_contract.yaml` + `references/technical_evidence_contract.md`)**: measurement/diagnosis/localization/state-identification cases must upgrade the v3.9.0 method skeleton into a full contract — per-step observation level and claimable resolution (user-defined granularity ranks; `output_rank ≤ observation_rank`), baseline registry (four kinds: standard / historical_clean / post_treatment / healthy_peer — a standard reference may only serve as corrected comparison, never as the live observation), threshold provenance (explicit "示例值，待现场标定" allowed; bare numbers not), downstream consumers, degraded branches (missing/conflict/multi-candidate/low-confidence outputs are mandatory design), and claim-class per feature (independent_core / dependent / **implementation_param** — sampling periods, example thresholds, device configs stay out of independent claims / auxiliary_evidence).
- **Observability & multimodal evidence (`references/observability_and_multimodal_evidence.md` + `templates/evidence_responsibility_matrix.md`)**: claim only what the sensing supports; six evidence roles (screening / spatial localization / mechanism attribution / consistency verification / decision / post-treatment recheck) with per-modality "cannot alone prove" and conflict-arbitration columns; no single modality may own the decision — imaging/thermal findings must pass physical-topology + measured-consistency verification before driving actions (also keeps clear of the crowded "image recognition → treatment" route); physical mapping relations must carry a registered source (never algorithm-guessed); post-treatment retest feeds back into judgment confirmation and baseline updates.
- **Decision-logic single source of truth (`templates/decision_table.md` / contract `decisions`)**: AND/OR spelled out once in a decision table with D-ids; body, modules, figures, and claims reference the ids (kills AND/OR drift between prose and flowcharts); fallback branches also get ids instead of scattered "必要时…".
- **Architecture-change re-search trigger (`iteration_context.md` hard gate)**: substantive changes to data sources, dominant evidence modality, localization approach, core decision chain, or the independent-claim mainline require a targeted supplementary prior-art search before finalizing — the old search verdict must not be carried over. (Validated in practice: an image-led route probe was found crowded by a supplementary search and the mainline reverted, with fixed sampling frequency demoted to a routine implementation condition.)
- **Attorney reply matrix (`templates/attorney_response_matrix.md`)**: the R6 reply deliverable now has a fixed format (overall reply + overview table + per-comment sections with 采纳/部分采纳/不采纳/存疑, evidence, and body locations); reply count must equal the attorney's top-level comment count.
- **`delivery_gate.py` C12–C15**: C12 `evidence_contract` (FAIL-level structural validation: required fields, claim-class/baseline-kind enums, `output_rank ≤ observation_rank`, baseline/derived/consumer/decision-id referential integrity, threshold provenance non-empty; chain-break producer→consumer mismatch WARN; auto-discovers `*技术证据合同*.yaml` in the case dir; needs pyyaml — graceful WARN if absent); C13 `decision_refs` (WARN: body D-id references vs contract decision table, both directions); C14 `attorney_reply_consistency` (FAIL on missing replies, given `--comments-json` + `--attorney-reply`); C15 `impl_params_in_claims` (WARN: number+unit tokens inside Chapter-5 independent-claim region, dependent subsections exempt). Semantic judgments (whether sensing truly supports the claim, whether a baseline is misused, whether a modality overreaches) stay in §8.1 — regex does not decide them.
- **Desensitization pass over the working tree before any future commit**: case ids / agency names / case-specific wording removed from the uncommitted v3.9.0 texts (SKILL.md, CHANGELOG, REVISION_LOG, prompts, tests, tools/README, delivery_gate docstring); `templates/patent_formula_manifest.yaml` — which mirrored an unfiled real case's full formula chain — replaced with a generic desensitized example chain (state recursion / bounds / derived / aggregate / weighted inner product / guarded-ratio boundary / feasibility rule, with ε-protection and implementation-param notes). NOTE: the old formula content exists in earlier public git history; surfaced to the owner as a standing risk.
- Tests: 63/63 pass (55 + 8 new desensitized regression tests covering: aggregate-level claim beyond observation rank, missing degraded branch, threshold without provenance, dangling baseline/consumer refs + chain break, invalid claim class, unknown/unreferenced decision ids, 3-comments-2-replies mismatch then full pass, impl-param flagged in independent region only).
- requirements.txt: + pyyaml (optional, C12 only).

---

## v3.9.0 (2026-07-14) - Two-case attorney-review retrospective: generation gates + comment-closure subflow

Distilled from 24 attorney pre-review comments across two real cases (8 + 16 comments; an energy-accounting boundary-calculation method and a measurement-diagnosis method — case identifiers kept out of this public repo). The recurring failure mode: chapters that each look complete but drift apart because they are generated independently, plus "what it does" descriptions without "how it does it", formulas warehoused away from their steps, claim features with no body support ("具体体现在方案中的哪部分？" ×4), undefined self-coined terms, and unquantified fuzzy qualifiers ("近似同步"/"明显大于"/"证据不足"). Problem features extracted, not case specifics.

- **Generation-side gates (`disclosure_builder.md`, four new sections)**:
  - *Method-skeleton-first + tiered step disclosure*: a single step skeleton (id / input / operation+basis / output / exception branch / owning formulas / step class) is fixed BEFORE drafting and is the sole source all views (3.2 system diagram, 3.3 modules, 3.4 flow, Chapter-5 method claims) expand from — views may differ in granularity but must map (prevents the "3.2 vs 3.4 which one governs?" drift). Steps classed CORE / SUPPORTING / COMMON / OPTIONAL: COMMON steps get one-line conventional-means mention, CORE steps must disclose the full constraint list, pass/fail criteria, and failure handling (the attorney's literal ask: detail the unique operations, summarize the routine ones).
  - *Formulas travel with their steps*: manifest gains **`owner_step`**; every key formula must appear in (or be explicitly referenced from) its owning step's 3.4 narrative; the 符号与公式 section is a symbol table + index, never the only place a formula lives; per-variable lineage (external input / prior-step output / defined derived quantity — no parameters appearing from nowhere).
  - *Term definition + data lineage*: self-coined terms ("清洁基线数据"-class) defined at first occurrence (meaning + acquisition/computation + unit); collective terms must not be re-enumerated alongside their members ("基于所述边界函数系数、逐小时自用电量序列…" redundancy); five data tiers (raw / preprocessed / derived feature / intermediate judgment / decision output) never mixed — derived quantities must answer "computed from which step's quantities by what rule".
  - *Fuzzy qualifiers + observability granularity*: fuzzy qualifiers in judgment contexts need one of numeric threshold / relative baseline / compound condition — or an explicit "示例阈值，需按实际数据标定" note (never fabricated calibration); locate/map/identify claims must not exceed what the input granularity supports (string-level I-V curves cannot uniquely locate a cell) — degrade to candidate+confidence wording; 和/或 decision-basis conjunctions consistent across body, figure captions, and claims.
- **Self-check (`disclosure_self_check.md` §8.1 new subsection)**: cross-view consistency (diagram vs flow step count/order/branches; module↔step correspondence) + a **claim-support verification table** — every Chapter-5 key point and dependent claim must answer "which step + which formula + which embodiment supports this"; features mentioned only in 可替代实施方式 or a single passing sentence cannot stay as claims (expand the body or downgrade/remove). §8.2 manifest item now checks `owner_step` completeness.
- **Attorney-comment closure subflow (`prompts/review_comment_closure.md` + `tools/docx_comment_extract.py` + 4 tests)**: extract comments from a reviewed DOCX (range vs point comments, reply threading via `w15:paraIdParent`, done flags, figure-paragraph context fallback) → judge each point comment's effective scope (a comment at the S10 paragraph may target S1–S10) → generate an overlay MD with immutable verbatim comments in `REVIEW_COMMENT_BEGIN/END` markers → triage via correction_handler → `批注处置矩阵.md` (CLOSED/PARTIAL/OPEN per comment) → attorney reply draft consistent with actual edits. Dual source-of-truth check (content MD vs reviewed DOCX) before overlay generation. Validated against both real reviewed DOCX files: 16/16 comments with correct anchors on one case, 7 originals + 7 replies correctly threaded on the other case's reply round.
- **`delivery_gate.py` C11 (`fuzzy_qualifier`, WARN-only)**: machine backstop listing 近似同步 / 明显大于(小于/高于/低于/优于/阶梯/异常) / 基本一致 / 风险较低 / 证据不足 / 必要时 / 视情况 / 适当调整 occurrences for per-occurrence quantification judgment. Same design as C10: surfaces, never decides, never FAIL.
- **Declined** (documented): a full YAML method-graph → chapter generation pipeline and a case-based regression-eval framework (both proposed in the retrospective) — the skeleton requirement is prompt-level for now; a generative middle layer and private eval set are follow-ups, not half-built here.
- Tests: 55/55 pass (50 pre-existing + 4 docx_comment_extract + 1 C11).

---

## v3.8.1 (2026-07-09) - Affirmative-framing gate: keep defensive judgments out of the body

From a user's disclosure-writing experience (wind-speed extrapolation case): defensive/negative judgments — scope-guarding, attorney claim-strategy reminders — narrow the protection surface when they leak into the formal specification body. They belong in the handoff note / review record / prior-art log; the body should carry affirmative technical features and effects. Generalizes the v3.6.2 effect-wording gate (which only covered competitive self-incrimination) into a broader principle.

- **`disclosure_builder.md` 防御性判断与正向表述门禁**: six positive-rewrite patterns — (1) compatible-not-exclusive ("可兼容 X，区别在于…" instead of "本发明不在于 X", which proactively cedes scope); (2) affirmative-additive effect enumeration ("除…外，还提供…") instead of self-weakening disclaimers ("不以…为唯一目标"); (3) product-behavior promise → superordinate technical output ("生成风险提示信息，包括…中的至少一种"); (4) attorney strategy reminders ("存储介质不宜作为区别主线") stay out of the body — body only says "本发明还可通过电子设备/存储介质/计算机程序产品实现"; (5) converge the independent claim but don't self-negate in the spec ("上述模型均可纳入该闭环", not "这些都不是本发明"); (6) abstract independent claim, specific embodiments ("至少两类候选策略" in the claim, the six concrete strategies in embodiments/dependent claims).
- **G7 reconciliation (`disclosure_self_check.md` §8.5)**: the v3.7.1 "pivot the effect mainline to traceability/robustness when magnitude is modest" now specifies the pivot must be *affirmative-additive* ("除…改善外，还提供…"), NOT a disclaimer ("不以…为唯一目标" / "本发明不在于…") — a disclaiming pivot reads as weak effect and a negation cedes scope.
- **§8.3**: attorney claim-strategy meta-comments added to the formal-body cleanliness ban (distinct from the existing tool/process leakage ban — these contain no banned tool-words, so the old scan missed them); new negation/defensive-phrasing scan checklist item.
- **`delivery_gate.py` C10 (`defensive_phrasing`, WARN-only)**: machine backstop that lists occurrences of 不在于 / 不作为 / 不强制 / 不以 / 不宜 / 显著降低 in the delivered `.md` body for per-occurrence judgment (attorney-note → move out, or → rewrite affirmative). Never FAIL — the tokens are not banned, each needs a human call; the gate surfaces, it does not decide. Implements the user's "固定加一道检查" literally.
- Tests: 50/50 pass (+1 for C10).

---

## v3.8.0 (2026-07-09) - Unified machine-checkable delivery gate

Root cause: delivery-quality gates were spread across several tools plus a 60+-item self-check checklist; enforcement depended on the executing agent's diligence, and Codex-drafted disclosures (no interactive session discipline backing them) showed a measurably higher defect-escape rate — undated placeholders shipped in the body, enumerated source-tier counts that didn't sum to their stated total, `long_sparse_direct`-style multi-underscore field labels mangled into OMML subscripts by the existing docx conversion rule, multi-equation blocks compressed into one paragraph. None of these had a machine check; all were "supposed to be caught" by reading a checklist.

- **`tools/delivery_gate.py`**: one command, one `DELIVERY_GATE_JSON` line, exit code 0/1/2 (PASS/WARN/FAIL). Nine checks: C1 wraps `qa_docx_math.py` (formula/formal-text QA, FAIL-level); C2 placeholder scan with an identity-field whitelist (联系人/发明人/申请人 lines carrying "（用户自填）" are not defects, routed to a separate `user_fill` list instead) and table-scoped "若干" detection (WARN); C3 markdown-table count-closure — sums a table's data rows and diffs against a stated 合计/总计/共计 row (WARN); C4 field-label integrity — multi-underscore enum/field labels (≥2 underscores) must survive into the DOCX unmangled, catches both outright loss and OMML-subscript transformation, plus a heuristic flag for suspicious all-lowercase multi-layer-subscript math blocks (FAIL/WARN); C5 red-text run residue and multiple `m:oMath` crammed into one `m:oMathPara` (FAIL/WARN); C6 filename-timestamp convention (WARN); C7 confirmation-checkpoint artifact presence — checkpoint 3 sign-off in `prior_art_dossier.md`, checkpoint 4 preview-confirmation record (or an explicit `--preview-skipped` acknowledgment), plus T0's checkpoints 1/2 when `--entry t0` (WARN); C8 wraps `qa_numeric_reproduce.py` (FAIL); C9 version self-report that reads `.git`/HEAD/reflog directly with no `git` subprocess call, so it resolves correctly from inside a worktree. Auto-appends `交底书交付检查记录.md` via the existing `delivery_check_log` module unless `--no-record`.
- **New**: `templates/preview_confirmation.template.md` (确认点 4 record template, including an explicit skip-acknowledgment section); `tests/test_delivery_gate.py` (7 new tests: whitelist/若干-scope, count-closure pass+mismatch, field-label pass+transformed-fail, red-text-FAIL+multi-math-WARN, filename-mismatch, preview-skip vs missing, full CLI PASS/WARN/FAIL exit-code+JSON round trip).
- **Wired into the main pipeline**: `SKILL.md` 主流程 Step 8 gains a mandatory gate-run sub-step; `disclosure_self_check.md` §8.5 runs the gate before the manual checklist and folds its `DELIVERY_GATE_JSON` output into the existing PASS/WARN/FAIL determination. The gate covers machine-checkable items only — §8's semantic checks (logical closure, claim consistency, formula correctness) are unchanged and still required.
- **Declined** (documented, not silently skipped): patching `md_to_docx.py` to stop OMML-subscripting multi-underscore field labels. `qa_docx_math.py` already flags unconverted bare-underscore identifiers as `bare_subscript_identifier`; a one-sided patch would make correctly-left-as-text field labels trip that check as a false residual. Needs a shared convention between the two tools first — left as a follow-up rather than a half-fix.
- Environment note (Windows Home): building this required discovering that `codex exec --sandbox workspace-write`'s native Windows-Sandbox helper cannot run on Windows Home editions (missing `VmComputeAPI.dll`, an OS-feature gate, not a broken install); `--sandbox danger-full-access` is the working alternative for local Codex dispatch on such machines.
- Tests: 49/49 pass (42 pre-existing + 7 new).

---

## v3.7.1 (2026-07-08) - Review-triage + claim-consistency gates (three-case retrospective)

Prompt-level hardening from a cross-case gap review (two Codex-drafted student disclosures — wind-speed extrapolation, turbulence-matrix imputation — plus the PVSC-001 line and a GPT skill-comparison): recurring failures were external review comments applied without verification, A-route claims with internal contradictions, and template/terminology gaps.

- **External-review triage (`correction_handler.md` step 2)**: comments from GPT / patent attorneys / examiners must be verified item-by-item BEFORE editing — numeric/formula comments recomputed or diffed against the original (a reviewer once proposed a "fix" identical to the original SOC formula — misread); format/symbol/unit comments render-verified (text extraction once fabricated "blank formulas / 50~500 m unit error" against a correct DOCX); prior-art characterizations checked against claim text. Each item marked 采纳 / 拒绝(with evidence) / 存疑; triage table required in the correction summary. User-sovereign local facts exempt.
- **DOCX-review render rule (`iteration_context.md`)**: format-level defect claims about a .docx require a render check (Word/soffice → PDF/page images); plain-text extraction drops OMML/μ and fabricates defects. Without a render channel: no format-defect assertions, only "pending manual Word check" items.
- **A-route claim consistency (`disclosure_self_check.md` §8.1 new subsection + §8.5 gate)**: independent-claim features must not conflict with "optional/non-essential" statements elsewhere (real case: mandatory 物理边界校验 in the independent claim while a dependent note declared it non-essential); per-feature circumvention test (drop-it-and-see; mandatory auxiliary layers → "at least one of" elasticity); over-narrow parameters (specific values / iteration counts / convergence precision) stay in embodiments. B-route §8.4 already had this; A-route now does too.
- **Interlocked-loop test for independent claims (`patent_points_analyzer.md` new hard rule + `disclosure_builder.md` closure bullet)**: claim steps must exhibit explicit parameter coupling (output of step N constrains step N+1), not separable parallel metrics ("compute A, compute B, then select") — parallel-metric claims read as routine metric aggregation. Complements the v3.7.0 integral technical-character test (that one checks the endpoint, this one checks the structure). No fabricating couplings absent from user material.
- **Algorithm well-definedness (§8.2, 3 new checks)**: topological definition order / cyclic dependency (declare initialization + update rule + stopping condition, e.g. the l(t) layering-key case); responsibility split between double-fitted parameter sets (proxy coefficients vs calibration factors); signed circular difference for periodic quantities (0°/360° wrap).
- **Effect-wording vs magnitude (§8.5)**: modest measured improvements must not be called 显著/大幅 even with data — wording matches magnitude; pivot the effect mainline to traceability / robustness / risk control (feature-backed).
- **Computer program product added as 5th subject**: SKILL.md default combo, analyzer tables, `disclosure_builder.md`, `method_system_patent_guide.md` — per the 2023 examination guideline; carrier subjects (device / medium / program product) are coverage tails: never the distinguishing mainline, never in the title.
- **Title anti-stacking (all entries)**: invention titles must not enumerate subjects ("…方法、系统、设备及存储介质" → "…方法及系统"); the ≤25-char rule now applies beyond T0 cases.
- **Fixed disclosure sections (superset structure, no profile system)**: 本发明摘要 (reuses the user-confirmed Step-6 preview; unnumbered, before Chapter 1), and Chapter 6 fixed subsections 可替代实施方式与规避设计防御 / 术语与缩略词表 / 引用文献表 — one structure serving both agent-review and law-firm-template readers.
- **Pre-search terminology**: Step 3–4 pre-search table column renamed to 预查新优先级 (优先查新/备查/待补材料/暂缓); 主推/可发表/窄化备选 reserved for post-search layering only.
- **Step 6 preview default-on (确认点 4)**: 300–500-char preview + confidentiality/facts/protection-direction checklist mandatory unless the user explicitly skips; confirmation lands in `预览确认记录.md`, skips logged in the delivery record.
- **Identity fields are user-filled**: 联系人/发明人/申请人 never agent-filled — "（用户自填）" placeholder is not a delivery defect (listed as user-todo in the delivery record).
- **Field-label vs math-variable rule (SKILL.md)**: multi-underscore enum/field labels (e.g. `long_sparse_direct`) are NOT formulas — must not be converted to OMML subscripts (a real DOCX mangling case); prefer Chinese name + label in parentheses in prose. Tool-level enforcement lands with the v3.8 delivery gate.
- Positioning anchor added to SKILL.md: the skill serves exactly three acceptance goals — sound draft logic, runnable & reviewed MVP support, human-readable deliverable formatting; deep multi-perspective review and legal filing strategy stay external.
- Docs-only change; test suite unchanged (must stay green).

---

## v3.7.0 (2026-07-06) - Substantive-patentability hard gates (from a disclosure re-review)

Four gates that extract the *problem feature* (so the next disclosure of any kind avoids the error), not the specifics of the case they came from.

- **Primary-reference claim-level read (Gap 1)**: closest prior art / R0–R1 / main-comparison references must be read at INDEPENDENT-CLAIM level, not abstract-only — abstracts mislead (e.g. a "measured-samples + features + ML model" method summarized as "builds a math model to predict", which both understates the reference and makes it sound closer). Image-only scans → render page-images and read. New `primary_reference` / `claims_read` evidence fields; `claims_read=no` on the closest reference caps the round at D/partial-D. (`prompts/prior_art_search.md`)
- **Numeric reproducibility gate (Gap 2)**: syntax/OMML QA and the narrative self-check do NOT catch numbers that don't reproduce or a wrong-direction trend claim. Rule: every key quantitative-effect figure/trend must trace to a re-runnable computation — **reuse the user's own executable model when present** (e.g. a project `*.py --test-only`), else build a minimal `numeric_check` spec for the new `tools/qa_numeric_reproduce.py`; numbers must be regenerated, never hand-transcribed. Placed at Step 8 self-check (`disclosure_self_check.md` §8.2 run + §8.5 gate); complements `qa_docx_math.py` (which checks rendering, not values). Tiered by source: (1) reuse user model, (2) encode formulas → tool, (3) **no reproducible source** (experiment/simulation/measurement/external) → the gate does NOT auto-launch a large verification effort or loop: it **stops at a decision point**, proactively asks the user for the needed source materials, and lets the user choose manual re-check vs. marking "provenance-only / pending" at WARN — never fabricating or burying into open-ended work; the invariant is only that no key number ships without a second, independent check. Caught a real case: a correction factor claimed to rise with gap (0.691→0.726) actually falls (0.691→0.645). (`+tools/qa_numeric_reproduce.py`, `+templates/numeric_check.sample.json`, `+tests/test_qa_numeric_reproduce.py`)
- **Integral technical-character test for calc/assessment methods (Gap 3)**: the coarse "solves a technical problem" screen is trivially passed by naming a scenario. Calc/assessment/scoring/prediction claims whose endpoint is "output a result/heatmap/table" from known-formula/natural-law substitution now get an A2.2/A25 + common-knowledge flag and must add (i) physical-quantity acquisition/inference + (ii) a technical action driven by the result, else max WARN. (`prompts/patent_points_analyzer.md`)
- **"Method-about-a-physical-system" hybrid routing (Gap 4)**: an A-route method whose inventiveness depends on a physical device/failure mechanism keeps the method mainline but must retain physical anchors; structural trigger words no longer auto-route to structural limited-assist. (`prompts/intake.md` Q1.5, `patent_points_analyzer.md` Step 4, `SKILL.md` trigger)
- Derived from an independent re-review of a high-altitude PV-connector breakdown-margin disclosure (triangulated with GPT + a Codex `paschen_model.py` recompute). Independent-evaluation note: two reviewer-flagged "defects" — blank formulas / "50~500 m" unit error — were text-extraction artifacts (the DOCX has correct OMML + "μm", confirmed by Word render), and were NOT changed.
- Tests: 42/42 pass (+5 for qa_numeric_reproduce).

---

## v3.6.3 (2026-07-05) - Constraint-infeasibility handling + sim-claim scoping

- **Constraint-infeasibility handling** added to the control-formula gate: control-method constraints (order commitments, safety bounds, resource limits) must specify what happens when the constraint **cannot** be met (infeasibility flag + warning / safe degradation) — must NOT write boundless "保证/一定不违约/必然满足" over-claims (over-strong support, easy to counterexample). Ties into the v3.6.2 safe-degradation framing.
- **Time-series residual/verification**: for horizon quantities (e.g. future-window violation), residual/verification computations should re-evaluate per predicted step and take the extremum, not a single scalar approximation.
- **Sim/measurement absolute-claim scoping**: absolute quantitative statements in the body (100% / 全部场景 / 均为…) must be scoped to "在所述实施例中", not stated as universal conclusions.
- Derived from a second-round GPT patent-review of the PVSC-001 R2 disclosure. (Note: one review point — "SOC formula doesn't use ηd" — was a reviewer misread; the formula already used P_dis/η_d − η_c·P_chg correctly, so it was NOT changed; independent evaluation of review comments matters.)
- Tests: 37/37 pass.

---

## v3.6.2 (2026-07-05) - Technical-effect wording gate + control-formula support

- **Technical-effect wording gate (formal body)**: honesty means no fabrication/overclaim, NOT competitive self-incrimination in the filing text. When sim/measurement shows the method is not-better/worse than prior art in some scenarios, the formal disclosure/spec **must not** write "尚未优于/劣于现有路线 / 工程化待优化 / 某场景更差" (usable as adverse evidence in examination/invalidation); instead **reframe the same fact positively as the method's own robustness/safe-degradation capability** (e.g. residual-risk check + warning → explainability + graceful degradation), keep the full comparative (incl. unfavorable) data in internal review records/evidence pack, and keep only the method's real positive quantitative effects + a validation-stage caveat in the body. Reconciles honesty (internal) with sound patent drafting (formal).
- **Control/scheduling method formula-support gate**: control methods involving state recursion (SOC/temperature/queue) or constraints (order commitments/safety bounds) must give in 第三章 ①state recursion/composition formulas (efficiency, capacity, timestep) and ②quantified constraint expressions (e.g. order-minimum-power = remaining energy / remaining time), so service/order constraints read as technical constraints not management rules — lowers subject-matter risk and satisfies enablement.
- Derived from a real GPT patent-review of the PVSC-001 disclosure (GPT, not Codex, is the heterogeneous reviewer for patent/disclosure content; Codex is for coding tasks).
- Tests: 37/37 pass.

---

## v3.6.1 (2026-07-03) - Disclosure content-quality fixes (Step 6/7)

- **Module description now requires input/processing-basis/output/upstream-downstream** (was "作用与关联关系，非输入输出"): both `disclosure_builder.md` 三、（三）and `template_reference.md`; bans pure-functional "用于识别/判断/优化" descriptions. Aligns Step-7 generation with the implementability discipline used elsewhere.
- **Core-action implementability gate at generation time** (not only Step-8 self-check): Step-7 §third-chapter now demands input / processing-basis / output / exception-handling for every 识别/判断/映射/匹配/选择/优化/调度/预测/评估/归因/修正/校验/排序/分配 action.
- **Prior-art URL rule unified**: formal disclosure 正文 no longer forces per-reference URLs; URLs + source-status live in the evidence pack (consistent with `prior_art_search.md` + `formal_disclosure_cleanliness.md`). Body carries only pub-number/title/direction/closeness/distinction.
- **Numbering tension resolved**: added an internal-reference convention note — `3.4.1 符号表` / `3.5 参数表` are shorthand for 三、（五）符号与公式 / 三、（六）关键技术参数; body uses Chinese numbering only, self-check verifies by content not literal `3.4.1` headings.
- **Step-7 title defaults to the topic card's concise title (≤25 chars)**, not the full technical-route working title — prevents title bloat, ties Step-7 to the T0 double-title rule.
- **DOCX headings now black** (`md_to_docx.py` `_add_heading` overrides Word's default blue Heading-N style color) — matches Chinese disclosure convention; body already black.
- **mermaid A4-fit requirement**: system/flow diagrams must render within one A4 page — prefer `flowchart TB` for >8 nodes, short node labels, `subgraph` layering, ≤~12 nodes/diagram (split into overview + per-module otherwise), visual QA must re-render if overflow/overlap.
- Deferred (per user + reviewer): splitting `disclosure_builder` into content/format/delivery files (architectural, high-risk pre-generation); claim-orientation stays an *optional* Step-6 checklist item (not a forced gate) — publishability-focused cases may have no claim view at MVP time.
- Tests: 37/37 pass.

---

## v3.6.0 (2026-07-03) - T0 candidate pool module: direction-mining front-end

- Added `prompts/candidate_pool.md` (T0): dual-entry candidate pool generation (entry A: project-scan output feeds topic modeling; entry B: cold start from business domain), pipeline of boundary breakdown → technical problem pool → query design → probe-level search → candidate topic cards; gate 1 (project brief incl. application purpose / innovation-magnitude tolerance / narrow-direction allowance) and gate 2 (user final review: business fit, material availability, action feasibility, commercial-rule technicalization).
- Added `templates/candidate_topic_card.md`: dual-title rule (concise ≤25 chars per CNIPA examination-guideline convention + full technical-route working title), must-keep independent-claim features, claim forbidden zones (with publication numbers), stop conditions, qualifier-dependency degree, search-provenance line, claim-skeleton annex.
- Two-tier search formalized in `prior_art_search.md` ("查新分级" table): probe-level (direction triage) vs case-level (topic finalization) share the same evidence model and provenance discipline; probe zero-hit recorded as "not found within probe scope", unsearched channels as "未覆盖", never "未检出".
- Evidence-anchored grading in `patent_points_analyzer.md`: pre-search screening scores are hypothesis scores (probe-ordering only); A/B/C/D only after real search evidence; unprobed directions capped at "unrated (low confidence)". Write-back table gains 是否进独权 / 限定依赖度 / 分层 columns.
- Anti-qualifier-stacking: post-conflict order (redefine problem → switch axis → new mechanism → split → only then narrow), measurable qualifier-dependency (AND-feature count to distinguish from all known close art), three-layer output (主推/可发表/窄化备选), dual-title rule.
- Gate 4 checklist in `disclosure_preview.md`: title length, mainline naturalness, protection-combination preference, confidentiality boundary (details the user does not want published), quantitative-effect softening, embodiment demotion.
- PSS boundary statement in `prior_art_search.md` §D: PSS is CNIPA's official search data source, not an official patentability endorsement; sign-off = user's/agent's internal confirmation of the evidence-based go/no-go conclusion.
- Post-case domain-pack backfill guidance (lexicon, negative-example library, verified-active applicants, cross-case claim forbidden-zone registry); domain-pack contents stay in the user's project directory — never committed to this public repository.
- Codex cross-review fixes (6/6 adopted): gate-2 → Step 3–4 lightweight integration handoff (topic card = candidate-point dossier, no re-mining); `A-探针`/`B-探针` probe-grade suffix separated from case-level A/B gates (positive controls ≥3, source-state); gate-3 minimal sign-off record fields in `prior_art_search.md`; gate-4 explicit skip-release logging; dual entries renamed 材料入口/冷启动入口 (avoid A/B letter collision with search grades); `needs_human_auth` clarified as an operational flag, not a `verification_status` value; user final review confirms business/material boundary only, never re-grades evidence levels.
- Pilot-run fixes (live T0 pilot on a real candidate direction): probe-verification environment-block handling (dual-channel 503 → record environment state, judgment may stand on official result-page abstract, verification carried as a pending item into case-level search); gate-2 rejection disposition codified (shelve with per-question record, asset recycling into sibling topics' dependent-feature candidates, immediate domain-pack backfill restricted to user-confirmed facts — single-case inferences must not be generalized into absolute rules; shelved ≠ deleted, probe evidence is reusable).
- Gates renamed to 确认点 1–4 (avoids awkward "门 N" phrasing; "步骤" was rejected to prevent collision with Step 1–8). Gate-2 fact-class distinction added: user answers are authoritative only for sovereign facts (own business/materials/implementability); general technical claims are leads requiring corroboration (model knowledge + search), with probe-evidence conflicts flagged as tension.
- Problem-reality check added to T0.3 (concurrent with mining, not deferred): every technical problem graded 实证/佐证/未证; targeted verification (model knowledge + ≤1 web search) for unverified problems driving topic cards; probe hits dual-read as both prior-art occupation evidence and problem-reality corroboration (patent background sections as high-density sources); zero-hit dual interpretation — genuine GAP vs pseudo-problem — with "未证 + 0-hit" flagged high-risk, barred from mainline recommendation.

---

## v3.5.0 (2026-07-03) - Search channel resilience and Google Patents XHR fallback

- Added `tools/gp_xhr_search.py`: Google Patents XHR keyword search as a discovery-level channel (`google_xhr_search_result`) to offset the CNIPA EPUB first-page-only (~10 hits/term) coverage limit; single-line `GP_HITS_JSON:` output aligns with `EPUB_HITS_JSON` and feeds `patent_link_verify.py` directly.
- Added `tools/channel_preflight.py`: read-only environment preflight emitting one-line `CHANNEL_STATUS_JSON` (system proxies, Playwright/Chromium, Google Patents page + XHR reachability, EPUB TCP); CNIPA PSS is never probed by script.
- Documented execution-environment rules in Step 5 §D and tools/README: CNIPA-side scripts must run on the user's local machine; cloud-sandbox failures (e.g. Codex cloud egress rejected by the CNIPA WAF) are environment states to record in `query_log.md`, never "no prior art" or "script broken"; Windows curl schannel `CRYPT_E_REVOCATION_OFFLINE` false negatives noted.
- Fixed `cnipa_epub_search.py` argument parsing: `--help` / `-h` now prints usage instead of being submitted to the EPUB site as a literal search term.
- Added `prompts/prior_art_search.md` §A2 (XHR channel usage, politeness limits, EPUB/XHR division of labor) and the `google_xhr_search_result` source state to the evidence tables.
- Added offline tests for `gp_xhr_search.py` payload parsing and the argparse fix.

---

## v3.4.0 (2026-06-23) - Formal disclosure cleanliness gate

- Added `references/formal_disclosure_cleanliness.md` to separate formal disclosure正文 from handoff notes, evidence packages, QA logs, and tool/process instructions.
- Replaced commercial-database “正文推荐口径” with a technical-comparison-only 1.1.2 wording; commercial DB status, session URLs, query logs, and source-state explanations now belong in evidence/handoff artifacts.
- Added `qa_docx_math.py --check-formal-text` and wired it into the formal `mermaid_render.py` DOCX path to catch Word/LaTeX intermediate-draft notes, evidence-package notes, commercial DB status text, Agent/tool names, and script-name residue.
- Updated Step 5, Step 7, Step 8, README, and structure docs so formal `.md` / `.docx` deliverables do not contain self-referential workflow prose.

---

## v3.3.0 (2026-06-23) - Commercial database content-check workflow closure

- Added `references/commercial_patent_db_verification.md` to define when Agent should actively use authorized 壹专利 / 高数图 sessions instead of leaving mechanical checks to the user or patent agent.
- Clarified the boundary between `commercial_db_discovered`, `commercial_db_content_checked`, and `public_source_verified`.
- Added disclosure wording rules for 1.1.2 / 1.1.3 after commercial database content checks are completed.
- Added execution requirements: commercial database content checks must be written to the case evidence package, then reflected in the disclosure and regenerated DOCX.
- Clarified that commercial database session URLs remain internal evidence only and must not be written as stable public citation URLs.

---

## v3.2.0 (2026-06-22) - Cross-case patent workflow lessons

- Added `references/patent_workflow_lessons_ai_friendly.md` for cross-case workflow reuse.
- Added guidance for new candidate pools, commercial database plus public-source search, GPT/Claude planning, engineering support artifacts, WARN/PASS delivery gates, and AI-friendly case directory structure.
- Updated `SKILL.md` navigation so agents can load the workflow reference only when the task needs a complete patent-workflow run.

---

## v3.1.0 (2026-06-20) - Commercial patent database assisted search

- Added commercial patent database evidence states: `commercial_db_discovered`, `commercial_db_content_checked`, and `public_source_verified`.
- Added strict rules for using 壹专利 / 高数图 as discovery and content-check channels only; commercial database session URLs and school VPN URLs must not be written as stable public citation links.
- Added 壹专利 operating guidance based on validation: use publication-number stems such as `CN115360706` instead of `CN115360706B`, record hit counts and screenshots, and read details/claims for R2/R3 candidates when possible.
- Added R0/R1/R2/R3 relevance grading for commercial database candidates.
- Added platform safety boundaries: low-frequency, supervised use only; stop on CAPTCHA, risk-control, login, input, or submission failures; do not bypass access controls or scrape in bulk.
- Clarified that commercial database candidates affecting A/B/C conclusions must be rechecked through CNIPA PSS, Google Patents, Espacenet, WIPO, or another public source before entering disclosure section 1.1.

---

## v3.0.2 (2026-06-19) - DOCX delivery QA hardening

- Extended `qa_docx_math.py` from math-only QA into a DOCX delivery gate: it now reports embedded media count, Consolas/code-style runs, unrendered mermaid source residue, generic LaTeX command residue, and missing expected media.
- Added `md_to_docx.py --min-media-count` and `--allow-code-style` so final delivery can require rendered figures while still allowing diagnostic runs when needed.
- Changed `mermaid_render.py` so a failed mermaid render still writes the Markdown troubleshooting draft but stops Word generation, preventing unrendered `flowchart TB` / mermaid code blocks from entering final DOCX.
- Updated prompts and docs to require Word XML QA for formulas and diagrams, and to record when page-level Word/LibreOffice visual QA is unavailable.
- Added regression tests for unrendered mermaid code blocks and missing expected DOCX media.

---

## v3.0.1 (2026-06-19) - DOCX formula subscript and numbering hardening

- Fixed bare display formula lines such as `E(r) = V_sys / [r · ln(R_socket/R_pin)]` so `md_to_docx.py` upgrades them to block-level editable OMML instead of leaving underscore identifiers as visible text.
- Fixed formulas followed by a standalone numbering line such as `(4)` so the number is folded into the formula block and rendered in the right-hand borderless-table numbering cell.
- Fixed LaTeX parsing so `_` / `^` bind only to the final symbol in a plain run, preventing a full expression prefix from becoming the subscript base.
- Added inline bare-subscript detection for prose next to Chinese text, so `V_sys为...` and `R_pin为...` become OMML subscripts instead of ordinary text.
- Added manifest-driven auto-numbering: `md_to_docx.py --math-manifest` now assigns right-hand equation numbers to untagged display math blocks in manifest order before QA runs.
- Added QA failure pattern `bare_subscript_identifier`; generated DOCX now fails when visible text still contains `V_sys`, `R_pin`, or similar raw underscore identifiers.
- Added regression coverage for the screenshot-style formula line plus standalone number, and for QA rejection of bare underscore variables.

---

## v3.0.0 (2026-06-15) — 收缩为工程方法与软件系统主流程

### 改造动因

结构类专利在实际使用中暴露出附图、空间几何关系、物理机理和实验/仿真支撑不足时难以由 Agent 可靠补齐的问题。本版本主动收缩定位，不再把机械/结构类作为与软件/方法类并列的主模式，而是聚焦工程方法、软件系统、数据处理、控制测算、工程仿真/测算工具类中国发明专利。

### 修改文件清单

| 文件 | 修改类型 | 说明 |
|------|----------|------|
| `SKILL.md` | 重大修改 | version→3.0.0；description、标题、触发条件和检查清单改为工程方法/软件系统主流程；结构类改为有限辅助且最高 WARN |
| `prompts/intake.md` | 重写 | Q1.5 改为 A 主流程 / B 结构有限辅助 / C 不适用分流；新增方案成熟度预检 |
| `prompts/patent_points_analyzer.md` | 增强 | 授权可行性初筛新增「方案成熟度」维度和建议保护组合；Step 5 回写新增保护策略 |
| `prompts/disclosure_builder.md` | 收缩 | 主流程改为工程方法/软件系统；结构类内容降级为附录式有限辅助；新增四客体保护默认提示 |
| `prompts/template_reference.md` | 增强 | 新增「方法 + 系统 + 电子设备 + 存储介质」四客体模板；结构模板改为有限辅助附录 |
| `prompts/disclosure_self_check.md` | 增强 | 结构类专项检查改为有限辅助检查；新增 B 路线最高 WARN、方案成熟度不足最高 WARN 的门禁 |
| `prompts/prior_art_search.md` | 小改 | 查新后回写新增建议保护策略 |
| `references/structural_patent_requirements.md` | 降级说明 | 开头注明仅用于结构有限辅助，不用于创造性评估 |
| `references/method_system_patent_guide.md` | 新建 | 工程方法、软件系统、四客体保护和常见授权风险参考 |
| `README.md` | 更新 | 开头定位、功能表、参考文档和版权归属改为 v3.0 聚焦版；移除旧运行效果截图 |
| `docs/PRD.md` / `docs/skill-structure.md` | 重写 | 改为 v3.0 产品定位和结构说明 |

### 重要边界

- 结构/机械类专利不再作为本技能主赛道；仅在用户已有附图、物理机理和验证依据时提供有限辅助。
- B 路线最高 WARN，不输出 PASS。
- 不新增需要登录、验证码、API key、OAuth 或商业账号的外部工具。
- 查新证据链、CNIPA EPUB、Google Patents 复核、dossier、DOCX 与迭代留档保持稳定。

---

## v2.1.0 (2026-06-07) — 授权可行性优先与交付留档

### 改造动因

用户目标从“一次生成交底书”升级为“围绕高价值专利的完整工作流”：在收到论文、程序、想法等基础材料后，先筛出更可能具备授权基础的方向，再查新、回写区别特征、生成代理人可审稿的交底书，并在多轮修改后保留项目级检查记录。

### 修改文件清单

| 文件 | 修改类型 | 说明 |
|------|----------|------|
| `SKILL.md` | 重大修改 | name→`patent-unveil-review`，version→2.1.0；新增授权可行性初筛、A/B/C/D 查新分级、查新后回写、PASS/WARN/FAIL 门禁和 `交底书交付检查记录.md` |
| `prompts/patent_points_analyzer.md` | 重写 | 新增技术问题、区别特征、技术效果、实施支撑四维评分；区别特征或技术效果 0-1 分时不得直接主推；查新后必须回写 |
| `prompts/prior_art_search.md` | 增强 | 新增公开检索边界、18 个月公开盲区提示、最小对比表、可用区别特征、A/B/C/D 决策和 Step 3-4 回写要求 |
| `prompts/disclosure_builder.md` | 增强 | 新增“现有技术缺点 -> 技术问题 -> 区别特征 -> 作用机理 -> 技术效果 -> 欲保护点”授权论证闭环；强化软件/AI 充分公开和非编造边界 |
| `prompts/disclosure_self_check.md` | 增强 | 新增查新回写、授权闭环、诚信非编造检查；新增 §8.5 代理人审稿门禁和交付检查记录要求 |
| `prompts/iteration_context.md` | 增强 | 迭代交付除 `交底书修订对话记录.md` 外，新增 `交底书交付检查记录.md` |
| `tools/delivery_check_log.py` | 新建 | 在案件目录追加 PASS/WARN/FAIL、交付文件、检查摘要、待补项和下一步建议 |
| `tests/test_delivery_check_log.py` | 新建 | 覆盖交付检查日志创建和缺失目录错误 |
| `tools/README.md` | 增强 | 新增 `delivery_check_log.py` 使用说明 |
| `references/legal_sources.md` | 新建 | 汇总本地法规包和官方公开来源，列出对本 skill 有影响的规则摘要 |
| `README.md` / `INSTALL.md` | 更新 | 同步新 skill 名称、安装路径、触发命令和 v2.1 能力 |

### 重要边界

- PASS 仅表示“代理人审稿就绪”，不表示可直接提交专利局。
- 查新结论仅基于当前可公开检索资料，不替代正式法律意见，也不能覆盖未公开申请。
- `交底书交付检查记录.md` 跟随具体案件目录，不写入 skill 本体，也不写入交底书正文。

---

## v2.0.0 (2026-06-06) — 结构类专利双模式支持

### 改造动因

原 `patent-disclosure-skill` v1.8.9 完全面向软件/算法类专利设计，在实际用于机械/结构类专利（高海拔光伏连接器危险微间隙规避结构）时暴露以下系统性问题：

1. **章节结构不适配**：§3.2 强制 mermaid 系统框图、§3.4 强制 mermaid 流程图，结构类专利需要的是剖面附图+部件编号+状态描述
2. **模板头部不适配**：案件名称模板为「一种XXX方法及系统」，结构类应为「一种XXX结构/装置」
3. **附图指导缺失**：无 CNIPA 附图规范（黑白线稿、编号规则、标记互斥等）
4. **权利要求指导偏软件**：只有「方法/系统」二元指导，无结构特征限定、两段式写法等指导
5. **自检项缺结构专项**：无技术闭环完整性、主实施例收敛性、附图标记一致性、报告式语言清除等检查
6. **脱敏偏软件**：结构类专利通常不需要脱敏业务名称，但需要注意参数来源可靠性

### 修改文件清单

| 文件 | 修改类型 | 说明 |
|------|---------|------|
| `SKILL.md` | 重大修改 | name→patent-disclosure-skill-cch, version→2.0.0, 增加结构类触发词, 增加专利类型路由说明, 工具表增加结构参考文件行, Prompt映射表增加references行, 检查清单增加结构模式项 |
| `prompts/intake.md` | 重大修改 | 增加Q1.5专利技术领域路由问题(软件/结构/混合/待定), Q2增加结构模式补充提示, 增加Q4附图现状(仅结构模式), 汇总增加模式提醒 |
| `prompts/disclosure_builder.md` | 重大修改 | §7.1增加[结构模式]章节结构(3.1概述/3.2附图编号/3.3部件结构/3.4工作状态/3.5结构参数), §7.2增加[结构模式]文档头部模板, §7.4拆分为软件/结构两种图示指导, 新增§7.6a结构模式语言规范与权利要求指导 |
| `prompts/template_reference.md` | 重大修改 | 增加[结构模式]完整模版(§3.1-3.5模版含正反例, §五保护点指导, §六实施方式指导) |
| `prompts/disclosure_self_check.md` | 重大修改 | 增加§8.4结构类专利专项自检(技术闭环完整性/主实施例收敛性/附图标记一致性/语言清洁/权利要求结构检查), 处理原则增加结构模式说明 |
| `references/structural_patent_requirements.md` | **新建** | CNIPA附图规范(线条/编号/引用格式/常见错误), 结构权利要求撰写要则(两段式/特征限定优先级/避免事项/从属策略), 说明书撰写要则(常见问题/WIPO10步法/基础实施例法), 术语表模板 |
| `CHANGELOG.md` | **新建** | 本文件，记录所有修改 |

### 未修改文件（保持原样）

以下文件在结构模式下仍然适用或不涉及，保持原版不变：

- `prompts/prior_art_search.md` — 查新流程通用
- `prompts/patent_points_analyzer.md` — 专利点挖掘通用
- `prompts/iteration_context.md` — 迭代机制通用
- `prompts/merger.md` — 合并流程通用
- `prompts/correction_handler.md` — 纠正流程通用
- `prompts/disclosure_preview.md` — 预览机制通用
- `prompts/project_scan.md` — 项目扫描通用
- `tools/*` — 工具脚本保持不变
- `examples/*` — 教学示例保持不变
- `tests/*` — 测试保持不变

### 改造中发现的具体问题实例

以下问题均来自实际使用原技能撰写光伏连接器专利交底书时遇到的真实问题：

1. **技术闭环缺口**：交底书将「旁路断开」作为主流程必经步骤，但未处理带电断开时的电弧风险转移问题。→ 新增§8.4技术闭环检查项
2. **主实施例发散**：旁路件同时列举5种替代形态（环形弹片/弧形弹片/簧片/导电桥/弹性套），代理人无法抓住核心。→ 新增§8.4收敛性检查项和§3.4收敛要求
3. **报告式语言残留**：「本交底书围绕……进行检索」「实际申请时可由制图人员……」等非技术公开内容。→ 新增§7.6a语言清洁要求和§8.4语言清洁检查项
4. **附图标记不规范**：AI生成图使用「男端」「女端」等非标准术语。→ 新增references/structural_patent_requirements.md附图规范
5. **独权中的功能性限定**：「旁路断开位移大于……」强制要求可选功能。→ 新增§7.6a权利要求指导和§8.4权利要求检查项
6. **参数来源不明**：「间距为0.216 mm」无数据来源。→ 新增§3.5参数来源要求和§8.4参数检查项
