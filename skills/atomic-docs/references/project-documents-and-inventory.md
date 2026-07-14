# Project Documents And Inventory

## Responsibility

This reference owns when non-atom project documents are created or retained and how operation-local inventory, ownership, and evidence state is produced and retired. `atomic-document-contract.md` owns their structural kind and paths; `source-convention-and-domain-policy.md` owns source-convention content and semantic failure conditions.

## Source Convention Document Flow

When repeated source interpretation conventions would otherwise leak into service logic atoms, propose a separate write scope for `<doc-root>/project/source-convention.md`. It is not part of criteria bootstrap; create or update it only after combined criteria/domain/scope approval and the Atomic Docs Goal Gate. Apply its content, atom-boundary, and review rules from `source-convention-and-domain-policy.md` rather than defining another source-convention contract here.

## Project Document Workflow

Project documents are non-atom documents. Use:

- `project/project-goal.md` for product purpose, users/callers, success criteria, and non-goals; record `confirmation_needed` only when competing source-unverifiable purpose interpretations block a development judgment
- `project/project-glossary.md` for ambiguous or shared term meaning, ownership, source of truth, aliases, forbidden conflations, and uncertainty
- `project/source-convention.md` for source interpretation under `source-convention-and-domain-policy.md`
- `project/atomization-criteria.md` for durable documentation criteria, project exceptions, and unresolved approval decisions

Do not give these files atom frontmatter, AIDs, `graph_edges`, or required atom sections unless an explicit accepted migration converts one into an atom.

A service logic inventory is operation-local by default. Keep it under `.stageflow/atomic-docs/requests/<request-id>/inventory.md` or `work-state.json` from domain proposal through writer/reviewer cycles. Retain `<doc-root>/project/service-logic-inventory.md` only when the accepted scope explicitly asks for a final implementation-context index.

A retained inventory is a selected implementation-context index, not a behavior-coverage proof, progress log, or second copy of every atom. Each selected context entry records:

- concise reason the context is useful before source inspection or change
- inspected source identifiers
- candidate or final owning `atom_key`
- related AIDs and judgment label only when they exist
- important owner, shared/external contract, non-obvious constraint, risk trigger, or unresolved decision only when applicable

Do not require every inventory row to contain fields for validation, state, persistence, integration, failure, UI, backend, schema, transaction, and recovery. Include a field only when it changes the documented decision, risk, verification, or ownership.

Project document review must fail when a project document directly judges implementation status like an atom, when glossary meaning is too shallow to resolve a real conflict, or when `project-goal.md` treats docs config, baseline/cache paths, reset/delete notes, reviewer logs, or operation status as the service or product goal. A retained project inventory must also FAIL when it is only a source identifier list, lacks the selection reason or important owner/contract context required by this reference, claims exhaustive behavior coverage, or is not synchronized to real `atom_key` and existing AID references. Do not create or advance baseline metadata while the retained inventory is in that state. Source-convention-specific failures come only from `source-convention-and-domain-policy.md`.

## Pre-Approval Domain Proposal

After the user accepts project-wide or targeted bootstrap discovery, but before combined approval and Goal handoff, create a domain-only operation inventory. This is the first place where source-derived domain candidates are recorded; Atom candidates still do not exist.

For each domain candidate, record the project-native name, tentative path, durable responsibility, important excluded capability, adjacent boundary, the smallest representative source locator plus one concise observed-boundary summary, and displayed status. `work-state.json` is authoritative for `candidate|approved|rejected|needs_confirmation`; the inventory status column is a user-review projection that must be synchronized before handoff or resume. Put optional capability aliases and promotion reasons only when naming differs from project language. Do not copy this candidate map into criteria.

Use this compact shape:

```text
도메인 후보 | 책임 | 제외 범위 | 인접 경계 | 대표 소스 근거 | 상태/미해결 질문
```

Do not add `atom_key`, AID, split proposals, behavior rows, detailed fields, payloads, branches, states, failures, tests, methods, risk matrices, or `evidence.md` in this phase. The bootstrap reviewer may reopen adjacent source to judge a boundary, but the proposal persists only the minimum boundary evidence.

## Post-Approval Context Inventory

After combined approval and Goal handoff, expand only approved domains into a lightweight inventory grouped by durable domain and selected implementation-context candidate, not endpoint, class, method, component, or file. Add no observed behavior merely to prove coverage.

The minimum context row is:

```text
맥락 후보 | 선택 판단과 이유 | 잠정/확정 owner | 중요한 계약·제약과 참조 도메인 | 소스 근거 | 관련 AID/판정
```

In `work-state.json`, each candidate records a unique lower-kebab-case `candidate_id`, an exact approved tentative domain path in `domain`, `disposition: write|merge|drop`, and a non-empty `selection_basis`. A `write` candidate records its planned `candidate_atom_keys`; a `merge` candidate records `merge_target_atom_key`; a `drop` candidate creates no atom key. The visible inventory explains these choices in user language. An approved domain may retain only its domain context atom and have no separate behavior candidate. Use the complete machine-readable shape from `validation-contract.md` rather than inventing fields.

Add short notes only for important rules, state/effects, contracts, or failures needed to make the selection decision. The atom is the durable explanation; the inventory is selection and routing state, not behavior closure state. Keep `drop` rows until the operation closes so later source findings do not silently recreate them.

One context candidate may cite several source surfaces. Do not create one inventory row per route, controller, service, repository, component, schema, test, setting, branch, or ordinary behavior.

## Ownership And Evidence Prepass

For multi-domain or `initial-baseline` work, run one prepass over selected shared/high-impact context candidates before the first writer. A targeted single-domain operation checks only the target owner and adjacent contracts; it does not perform project-wide ownership discovery.

- identify shared payload, storage, permission, policy, integration, transaction, and glossary source-of-truth owners
- record which domains reference each shared owner and use reference count only as queue-order evidence
- confirm owners whose later change would reopen several bundles
- keep ordinary single-domain owners provisional until their bundle is written and reviewed
- order confirmed shared-owner bundles before direct dependents, then process independent bundles

Do not build a complete semantic graph or freeze every aggregate owner before writing. Uncertain shared ownership remains an explicit blocker; uncertain local ownership may be resolved in its bundle.

Create one operation-local `evidence.md` beside request state, pin it to `source_commit_observed`, and reuse it as a source-navigation index. Give every candidate one `## <candidate_id>` section. Use constrained plain Markdown: tab characters, fenced or indented code, multiline inline code, and raw HTML-like syntax are not allowed; ordinary inline code must close on the same line. Use the smallest authoritative source locators and one concise relevance statement per row, following the evidence format in `validation-contract.md`. Include `drop` candidates so their exclusion remains auditable until operation close, but pass only active `write` and targeting `merge` sections to the writer. Add storage, transaction, integration, schema, setting, and test locations only when they help judge a selected contract or owner. Do not preserve field lists, parser algorithms, payload mappings, branch sequences, stale-response reproductions, or defect narratives merely because they were inspected. Reviewers reopen source for exact mechanics when a retained claim needs verification.

After these anchors are known, finalize `write|merge|drop`, update the planned Atom keys and queue, and run the selection preflight from `validation-contract.md` before the first writer. A newly discovered candidate repeats this small admission step; it does not expand `evidence.md` into behavior closure.

Every `write` or `merge` candidate must resolve to an owner or an explicit unresolved decision before review PASS. Every `drop` candidate stays outside the write queue with its selection basis. Ordinary source behavior that never became a candidate needs no row or disposition. If a selected high-impact owner remains unclear and that uncertainty would mislead the atom's stated scope, record a gap with source evidence and `confirmation_needed`.

The required context-quality reviewer checks the selected queue and may identify a missing shared/external owner or non-obvious constraint only when its omission would make an atom's stated scope misleading. It must not search for or disposition every source behavior.

After accepted atom docs are written and reviewed, delete or ignore the operation-local inventory unless the user explicitly approved retaining a synced project context index.
