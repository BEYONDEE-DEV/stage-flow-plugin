# Project Documents And Inventory

## Source Convention Document Flow

When repeated source interpretation conventions would otherwise leak into service logic atoms, propose a separate write scope for `<doc-root>/project/source-convention.md`.

The source convention document is not part of criteria bootstrap. Create or update it only after criteria approval, accepted docs scope, and the Atomic Docs Goal Gate.

Separate behavior-neutral code style from runtime-impacting conventions. Formatting, naming, package placement, imports, and layer placement belong only in source convention docs. Validation activation, authorization wiring, error mapping, transaction behavior, lock ordering, or persistence ordering may be summarized there, but any resulting product rule or observable contract belongs in the related atom.

Review must fail when an atom treats code taxonomy or formatting as service behavior. If a runtime convention creates a decision or contract and appears only in `source-convention.md`, record a gap instead of treating the convention document as enough for an implementation judgment.

## Project Document Workflow

Project documents are non-atom documents. Use:

- `project/project-goal.md` for product purpose, users/callers, success criteria, non-goals, and unresolved project intent
- `project/project-glossary.md` for ambiguous or shared term meaning, ownership, source of truth, aliases, forbidden conflations, and uncertainty
- `project/source-convention.md` for source interpretation
- `project/atomization-criteria.md` for durable documentation criteria and boundaries

Do not give these files atom frontmatter, AIDs, `graph_edges`, or required atom sections unless an explicit accepted migration converts one into an atom.

A service logic inventory is operation-local by default. Keep it under `.stageflow/atomic-docs/requests/<request-id>/inventory.md` or `work-state.json` while writer/reviewer cycles run. Retain `<doc-root>/project/service-logic-inventory.md` only when the accepted scope explicitly asks for a final coverage index.

A retained inventory is a decision-level coverage index, not a progress log or a second copy of every atom. Each behavior aggregate records:

- concise behavior or decision summary
- inspected source identifiers
- candidate or final owning `atom_key`, or explicit gap/`out_of_scope`/not-applicable disposition
- related AIDs and judgment label only when they exist
- risk trigger, rule, state/effect, external contract, or unresolved decision only when applicable

Do not require every inventory row to contain fields for validation, state, persistence, integration, failure, UI, backend, schema, transaction, and recovery. Include a field only when it changes the documented decision, risk, verification, or ownership.

Project document review must fail when a project document directly judges implementation status like an atom, when glossary meaning is too shallow to resolve a real conflict, when a retained inventory is stale or lacks ownership/disposition, or when a runtime-impacting source convention has no related atom/gap for the decision it changes.

## Lightweight Operation Inventory

Before domain drafting, create a lightweight operation inventory grouped by meaningful behavior aggregate, not endpoint, class, method, component, or file.

The minimum row is:

```text
동작/결정 | 잠정/확정 owner | 공유 계약과 참조 도메인 | 소스 근거 | 관련 AID/판정 | 위험 트리거/미해결
```

Add short notes for consequential rules, state/effects, contracts, or failures only when the writer needs them to avoid losing a decision. The atom is the durable explanation; the inventory is routing and closure state.

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
