# Project Documents And Inventory

## Responsibility

This reference owns when non-atom project documents are created or retained and how operation-local inventory, ownership, and evidence state is produced and retired. `atomic-document-contract.md` owns their structural kind and paths; `source-convention-and-domain-policy.md` owns source-convention content and semantic failure conditions.

## Source Convention Document Flow

When repeated source interpretation conventions would otherwise leak into service logic atoms, propose a separate write scope for `<doc-root>/project/source-convention.md`. It is not part of criteria bootstrap; create or update it only after criteria approval, accepted docs scope, and the Atomic Docs Goal Gate. Apply its content, atom-boundary, and review rules from `source-convention-and-domain-policy.md` rather than defining another source-convention contract here.

## Project Document Workflow

Project documents are non-atom documents. Use:

- `project/project-goal.md` for product purpose, users/callers, success criteria, non-goals, and source-unverifiable project intent recorded as `confirmation_needed`
- `project/project-glossary.md` for ambiguous or shared term meaning, ownership, source of truth, aliases, forbidden conflations, and uncertainty
- `project/source-convention.md` for source interpretation under `source-convention-and-domain-policy.md`
- `project/atomization-criteria.md` for durable documentation criteria, project exceptions, and unresolved approval decisions

Do not give these files atom frontmatter, AIDs, `graph_edges`, or required atom sections unless an explicit accepted migration converts one into an atom.

A service logic inventory is operation-local by default. Keep it under `.stageflow/atomic-docs/requests/<request-id>/inventory.md` or `work-state.json` while writer/reviewer cycles run. Retain `<doc-root>/project/service-logic-inventory.md` only when the accepted scope explicitly asks for a final coverage index.

A retained inventory is a decision-level coverage index, not a progress log or a second copy of every atom. Each behavior aggregate records:

- concise behavior or decision summary
- inspected source identifiers
- candidate or final owning `atom_key`, or explicit gap/`out_of_scope`/not-applicable disposition
- related AIDs and judgment label only when they exist
- risk trigger, rule, state/effect, external contract, or unresolved decision only when applicable

Do not require every inventory row to contain fields for validation, state, persistence, integration, failure, UI, backend, schema, transaction, and recovery. Include a field only when it changes the documented decision, risk, verification, or ownership.

Project document review must fail when a project document directly judges implementation status like an atom, when glossary meaning is too shallow to resolve a real conflict, or when `project-goal.md` treats docs config, baseline/cache paths, reset/delete notes, reviewer logs, or operation status as the service or product goal. A retained project inventory must also FAIL when it is a one-line summary, lacks the behavior-level owner/disposition information required by this reference, or is not synchronized to real `atom_key` and existing AID references. Do not create or advance baseline metadata while the retained inventory is in that state. Source-convention-specific failures come only from `source-convention-and-domain-policy.md`.

## Lightweight Operation Inventory

Only after criteria approval, accepted docs scope, and the Goal handoff, create a lightweight operation inventory grouped by durable domain candidate and meaningful behavior aggregate, not endpoint, class, method, component, or file. This is the first place where source-derived domain and atom candidates are recorded.

For each domain candidate, record the project-native name, tentative path, owned and excluded behavior, adjacent boundary, source evidence, and whether it is accepted for this operation, rejected as broad, or blocked by a concrete ownership decision. Put reviewed durable boundaries in domain context atoms; do not copy this candidate map into criteria.

The minimum row is:

```text
동작/결정 | 잠정/확정 owner | 공유 계약과 참조 도메인 | 소스 근거 | 관련 AID/판정 | 위험 트리거/미해결
```

Each aggregate row identifies its candidate `atom_key` or split proposal in the owner field. Add short notes for consequential rules, state/effects, contracts, or failures only when the writer needs them to avoid losing a decision. The atom is the durable explanation; the inventory is candidate routing and closure state.

One behavior aggregate may cite several source surfaces. Do not create one inventory row per route, controller, service, repository, component, schema, test, or setting when they implement the same decision.

## Ownership And Evidence Prepass

For multi-domain or `initial-baseline` work, run one prepass over accepted behavior aggregates before the first writer. A targeted single-domain operation checks only the target owner and adjacent contracts; it does not perform project-wide ownership discovery.

- identify shared payload, storage, permission, policy, integration, transaction, and glossary source-of-truth owners
- record which domains reference each shared owner and use reference count only as queue-order evidence
- confirm owners whose later change would reopen several bundles
- keep ordinary single-domain owners provisional until their bundle is written and reviewed
- order confirmed shared-owner bundles before direct dependents, then process independent bundles

Do not build a complete semantic graph or freeze every aggregate owner before writing. Uncertain shared ownership remains an explicit blocker; uncertain local ownership may be resolved in its bundle.

Create one operation-local `evidence.md` beside request state and pin it to `source_commit_observed`. For each aggregate, record source entry points and only applicable storage, transaction, integration, schema, setting, and test locations. Writers and reviewers reuse this index to navigate source. Reviewers reopen changed or risk-bearing claims, sample unchanged high-consequence claims, and update the index when evidence changes; they do not rediscover every entry point.

Every meaningful aggregate in accepted scope must close to an owner or explicit disposition before review PASS. If ownership is unclear, record a coverage gap with source evidence and `confirmation_needed`.

The required development-quality reviewer checks aggregate-level closure against source and may identify an omitted aggregate. It must not demand row-level duplication of source mechanics.

After accepted atom docs are written and reviewed, delete or ignore the operation-local inventory unless the user explicitly approved retaining a synced project coverage index.
