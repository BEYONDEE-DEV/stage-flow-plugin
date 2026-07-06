# Project Documents And Inventory

## Source Convention Document Flow

When the user asks for a separate source convention format, or when repeated source interpretation conventions would otherwise be mixed into service logic atoms, propose a separate write scope for `<doc-root>/project/source-convention.md`.

The source convention document is not part of the pre-approval criteria bootstrap scope. The first bootstrap scope remains limited to `.stageflow/atomic-docs.json` when needed and `<doc-root>/project/atomization-criteria.md`. Do not create `project/source-convention.md` during criteria bootstrap or before criteria approval.

For normal docs generation, create or update `project/source-convention.md` only after the criteria document is approved, the accepted docs write scope includes the source convention document, and the Atomic Docs Goal Gate is satisfied. Use it as source interpretation context, not as service behavior evidence.

The document should separate non-runtime code style from runtime-impacting conventions. Formatting, naming, package placement, layer placement, import ordering, and similar non-runtime conventions belong in `project/source-convention.md` and should not be written as service logic atom behavior. Runtime-impacting conventions such as transaction activation, validation activation, authorization wiring, error response mapping, lock ordering, persistence ordering, or framework wiring may be summarized in `project/source-convention.md`, but the relevant service logic atom must still record the natural-language behavior and source evidence before any service judgment label is considered supported.

Reviewer subagents must fail or request correction when a service logic atom mixes in simple code convention, source folder taxonomy, formatting, naming, import order, or layer-placement notes as if they were runtime behavior. If a runtime-impacting convention appears only in `project/source-convention.md` and is missing from the relevant service logic atom, record a coverage gap or `confirmation_needed` rather than treating the convention document as enough for `bug_or_regression`, `missing_required_behavior`, `matches_confirmed_intent`, `unapproved_implemented_behavior`, or `out_of_scope_behavior`.

## Project Document Workflow

Project documents are non-atom documents. Use `project/project-goal.md`, `project/project-glossary.md`, `project/service-logic-inventory.md`, `project/source-convention.md`, and `project/atomization-criteria.md` for project-level control, context, terminology, inventory, and source interpretation. Do not give these files frontmatter `atom_key`, AID values, `graph_edges`, or required atom sections unless an explicit accepted migration converts a specific file into an atom.

`project/project-goal.md` must describe the service or product purpose, target users or callers, success criteria, non-goals, and `confirmation_needed` project intent. It must not describe docs-root config, baseline metadata paths, plugin cache paths, reset/delete logs, reviewer-agent logs, or current operation status as if they were service goals.

`project/project-glossary.md` must describe core terms with structured fields for meaning, owning domain, actor/system action, source of truth, stored vs computed, related rules/status, aliases, forbidden conflations, and uncertainty. A one-line glossary entry does not make derived behavior judgment-ready.

`project/service-logic-inventory.md` must remain a behavior-level input for writers and reviewers. Each inventory item must include source identifiers, conditions/branches, validation/guard, state transition, persistence side effect, external call, error/recovery, basis, owning atom_key, related AID, and judgment label when applicable. It must also expose reconstruction-critical fields when relevant: entry/screen/route or API/job entry, data contract/payload, authorization/permission, validation/refusal/defaulting, state persistence, transaction or idempotency behavior, external integration/event/job behavior, failure/retry/recovery, UI basic design/state presentation, and backend service/DB/DTO behavior that changes runtime meaning. If the inventory is missing those fields or only contains one-line summaries, do not record source-baseline metadata and do not present the docs as judgment-ready.

`project/source-convention.md` may help interpret source structure, but runtime-impacting conventions must link to a related service logic atom_key and AID or to a coverage gap. The source convention document alone cannot make a service behavior `matches_confirmed_intent`, `bug_or_regression`, `missing_required_behavior`, `unapproved_implemented_behavior`, or `out_of_scope_behavior`.

Project document review must fail when a project document directly judges implementation status like a service logic atom, when it relies on atom-only metadata as required structure, when glossary terms are one-line-only, when inventory items are too shallow to support writer/reviewer work, or when runtime-impacting source conventions have no atom_key/AID or coverage-gap linkage.

## Service Logic Inventory

When documenting source behavior, create a service logic inventory before drafting domain atoms. The inventory is behavior-oriented, not method-oriented: group source observations by meaningful runtime behavior rather than by endpoint, controller, service class, method, or file.

For each inventory item, record the inspected source identifiers, the natural-language behavior, conditions and branches, validation or permission checks, state transitions, persistence side effects, integration calls, emitted events, error handling, recovery behavior, inferred or confirmed basis, candidate owning atom key, candidate or assigned AID, and judgment label when applicable. Include reconstruction-critical fields such as entry/screen/route or API/job entry, data contract/payload, authorization/permission, validation/refusal/defaulting, state persistence, transaction or idempotency behavior, external integration/event/job behavior, failure/retry/recovery, UI basic design/state presentation, and backend service/DB/DTO behavior when they affect implementation.

Map every meaningful application, service, and domain logic item to an owning atom before claiming docs coverage. If ownership is unclear, record a coverage gap with source evidence and `confirmation_needed`; do not treat unmapped source behavior as healthy or covered.

Domain atom drafting must use the service logic inventory as input. A domain atom is incomplete when it only lists source files, endpoints, controllers, service classes, or method names without explaining the behavior in natural language.

A service logic inventory that only summarizes source files or behaviors in one line is not sufficient input for domain atom drafting, reviewer PASS, Goal completion, or baseline metadata update; it also cannot support an implementation-reconstruction-ready scope.
