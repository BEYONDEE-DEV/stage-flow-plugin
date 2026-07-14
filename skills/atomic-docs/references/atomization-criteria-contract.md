# Atomization Criteria Contract

## Responsibility

This reference is the normative owner of the small durable criteria document, including its structure, allowed content, evidence boundary, and review failure conditions. `criteria-flow.md` owns when the draft, review cycle, and user handoff occur.

## Criteria Document

The default path is:

```text
<doc-root>/project/atomization-criteria.md
```

At this path, record user-stated documentation goals, prohibitions, durable exceptions, and unresolved decisions. Do not copy illustrative project examples from skill references. The bootstrap timing and first-write sequence are defined in `criteria-flow.md`.

The criteria document is not an atom. It does not use atom frontmatter, AIDs, `graph_edges`, or the required atom sections.

For new or explicitly revised Korean criteria, use exactly these visible sections:

- `목적과 승인 상태`
- `문서 저장 위치와 적용 범위`
- `도메인과 문서 분리 기준`
- `문서 깊이와 식별 기준`
- `작성과 검토 기준`
- `프로젝트 예외와 미해결 결정`

Explain internal identifiers in plain language before names such as `atom_key`, AID, `target_key`, or judgment labels. While draft, record `승인 상태: 초안, 사용자 승인 대기`. After approval, record `승인 상태: 사용자 승인 완료` and remove obsolete approval-waiting notes.

## Durable Content

Keep only rules that remain useful across operations:

- what the docs are for and what source or operation scope they may cover
- how durable domain ownership differs from a broad category, source folder, screen, task group, or generic catch-all
- when distinct durable purpose, ownership, shared-contract, navigation, conflict, or change-impact boundaries require separate atoms, and when related context stays together
- context-depth rules: preserve high-value purpose, business/operational rules, contracts, non-obvious constraints, source anchors, dependencies, and unresolved decisions without creating a complete product-behavior specification
- evidence rules: current-contract claims need reachable source evidence, desired changes need approved requirement evidence, and identifiers alone do not prove behavior; user approval absence alone does not turn a source-established contract into a Gap
- selective identity rules: use stable `atom_key`; assign AIDs only to durable decisions that need independent reference; use graph relationships only for meaningful impact or ownership traversal
- shared writer/reviewer acceptance rules, context selection signals, explicit permission to leave ordinary details in source, and conditional risk triggers in compact form
- selected documentation language, user-specific prohibitions, project-specific durable exceptions, and decisions that still block approval

Do not copy the complete skill reference contracts into criteria. One clear project-facing rule may point to the active Atomic Docs contract for mechanical schema details.

## Operation-Local Content

Do not put any of the following in durable criteria:

- candidate or approved domain maps
- atom candidate or split-proposal maps
- perspective result tables or source-feature inventories
- current behavior-aggregate dispositions
- source evidence indexes or inspected-file lists
- bundle queues, agent identities, reviewer results, Goal status, baseline readiness, cache paths, or current-run progress
- subagent instruction sheets or repeated judgment-label catalogs

After criteria approval and docs-scope acceptance, put selected domain/context candidates, source evidence, owners, risk triggers, and queue state in `.stageflow/atomic-docs/requests/<request-id>/inventory.md`, `evidence.md`, or `work-state.json`. Preserve a reviewed durable domain boundary in its domain context atom. Keep a retained project context index only when the user explicitly requests it.

An existing approved criteria file that contains the older maps or perspective table remains a valid superset. Do not migrate or delete that content automatically. New criteria and user-approved criteria revisions use the compact contract; unrelated docs work may read the durable rules and ignore legacy discovery/progress sections.

## Criteria Review

The independent criteria reviewer checks only:

- all six compact sections exist and use understandable language
- draft/approved state is accurate
- split/merge, context depth, selective identity, evidence, and review rules do not contradict one another or turn general Atomic Docs into a product-behavior specification
- project exceptions and unresolved approval blockers are explicit
- operation-local discovery, candidates, evidence, and progress have not leaked into the durable file
- no unsupported inference, example leakage, migration, deletion, or external action is claimed

Do not inspect the whole project or require domain candidates, atom candidates, perspective rows, source coverage, aggregate dispositions, or graph completeness for criteria PASS. Inspect source only when a user-stated criterion names a specific code boundary and that narrow check is needed to understand the rule.

Any violation of these checks is criteria-review FAIL. PASS means the criteria are structurally ready for user review, not user approval. Revision cycles and approval handoff follow `criteria-flow.md`.
