# Atomization Criteria Contract

## Responsibility

This reference defines the small durable criteria document approved before source discovery and atom writing. Criteria record how documentation decisions are made; they are not a preliminary domain model, source inventory, or execution ledger.

## Criteria Document

The default path is:

```text
<doc-root>/project/atomization-criteria.md
```

After the docs root is confirmed and the user accepts the limited draft write action, create or update this file as the first managed-docs write when criteria are needed. Record user-stated documentation goals, prohibitions, durable exceptions, and unresolved decisions. Do not copy illustrative project examples from skill references.

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
- when independent product decisions, ownership, verification, conflict, or change boundaries require separate atoms, and when related behavior stays together
- decision-depth rules: preserve product, business, contract, operational, verification, dependency, and unresolved decisions without mirroring source mechanics
- evidence rules: confirmed claims need reachable source or approved requirement evidence; identifiers alone do not prove behavior
- selective identity rules: use stable `atom_key`; assign AIDs only to durable decisions that need independent reference; use graph relationships only for meaningful impact or ownership traversal
- shared writer/reviewer acceptance rules and conditional risk triggers in compact form
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

After criteria approval and docs-scope acceptance, put domain/atom candidates, source evidence, owners, risk triggers, and dispositions in `.stageflow/atomic-docs/requests/<request-id>/inventory.md`, `evidence.md`, or `work-state.json`. Preserve a reviewed durable domain boundary in its domain context atom. Keep a retained project coverage index only when the user explicitly requests it.

An existing approved criteria file that contains the older maps or perspective table remains a valid superset. Do not migrate or delete that content automatically. New criteria and user-approved criteria revisions use the compact contract; unrelated docs work may read the durable rules and ignore legacy discovery/progress sections.

## Criteria Review

The independent criteria reviewer checks only:

- all six compact sections exist and use understandable language
- draft/approved state is accurate
- split/merge, decision depth, selective identity, evidence, and review rules do not contradict one another
- project exceptions and unresolved approval blockers are explicit
- operation-local discovery, candidates, evidence, and progress have not leaked into the durable file
- no unsupported inference, example leakage, migration, deletion, or external action is claimed

Do not inspect the whole project or require domain candidates, atom candidates, perspective rows, source coverage, aggregate dispositions, or graph completeness for criteria PASS. Inspect source only when a user-stated criterion names a specific code boundary and that narrow check is needed to understand the rule.

If review FAILs, revise only the criteria file inside bootstrap scope and rerun the same criteria reviewer until PASS or a user decision is required. PASS means ready for user review, not user approval.
