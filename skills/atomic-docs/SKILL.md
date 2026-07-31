---
name: atomic-docs
description: "Use when the user says atomic-docs, atomic docs, the Stageflow atomic documentation skill, or asks Stageflow to create, update, inspect, refresh, or manage source-based atomic project docs that preserve purpose, boundaries, contracts, implementation context, planned changes, open questions, source evidence, or direct dependency relationships."
---

# Atomic Docs

Maintain a small source-guided documentation set that helps a developer decide and implement changes. Atomic Docs preserves durable purpose, boundaries, contracts, implementation orientation, approved changes, open questions, and source locations. It does not mirror every branch or replace source inspection.

## Permanent Outputs

Atomic Docs owns only:

- `.stageflow/atomic-docs.json`
- `<docs-root>/project/project-goal.md`
- `<docs-root>/project/project-glossary.md` when the project has terms a new developer needs defined
- `<docs-root>/<domain>/*-atom.md`

Do not create any other permanent Atomic Docs output. Atomic Docs also does not create a Goal.

## Core Contract

- Read `.stageflow/atomic-docs.json` and the applicable direct references before writing.
- Use source as the default evidence. Write only context that remains useful after reading the code.
- Support `repository` and `submodule` storage without assuming a fixed docs root.
- Use `project-goal.md` for project-wide purpose, users, success, non-goals, and sources.
- Write project success as project-level outcomes observable by the intended human or system consumers. Keep a technical invariant there only when it is itself a project outcome; otherwise put it in the natural owning Atom.
- Create `project-glossary.md` as a general project glossary for vocabulary a new developer must understand to read the requirements, docs, UI, and API correctly. Include project roles, domain concepts, core entities and relationships, workflows and states, and important project-specific identifiers or acronyms even when a term belongs to only one Atom. Use only `Term` and `Definition`; verify definitions from inspected source without adding ownership, source, evidence, or control columns. Do not turn the glossary into an inventory of implementation types, functions, or fields, and do not invent artificial terms merely to split lifecycle levels.
- Give every Atom one globally unique lower-kebab `atom_key` and required `depends_on`.
- Give every Atom exactly these seven sections: `Purpose`, `Boundaries`, `Contracts`, `Implementation`, `Sources`, `Changes`, and `Open Questions`.
- Keep every section meaningful. Use exact `- 없음` only for empty `Changes` or `Open Questions`.
- Put only behavior, obligations, and invariants that must survive an implementation change in `Contracts`; put useful current mechanics in `Implementation` or omit them. Keep a generic rule with its natural owning Atom instead of copying it across dependents, while preserving each dependent's domain-specific result or additional condition. Do not create a shared Atom solely to deduplicate mechanics.
- Put at least one exact source locator in every `Sources` section: ``<source-name>:<source-root-relative-path>#<symbol>``. Use `primary` for the configured primary source and the configured auxiliary name for auxiliary sources. Do not use line ranges.
- Use `depends_on` only for direct Atom-to-Atom dependencies. Do not maintain a separate graph or general-purpose semantic IDs.
- Record an active Atomic Impl requirement exactly once in `Changes` as `[RID:<atom_key>.<lower-kebab-slug>]`. Atomic Docs alone does not invent RIDs.
- On completed Atomic Impl work, move durable meaning into `Contracts` or `Boundaries`, refresh `Implementation` and `Sources`, and remove the completed RID.
- Use the configured language for prose while preserving fixed English headings, keys, identifiers, and locator syntax.

## Operations

Classify each request as one command:

- `inspect`: read config, managed docs, and relevant source; report findings without writing.
- `update all`: establish or replace the complete managed set from a stable primary-source commit.
- `update changed`: start from `last_full_source_commit`, map changed files to existing Atom locators, and update only the bounded affected set.
- `update targeted`: update user-named Atom keys, domains, or source paths.

For setup, explain the storage mode and write scope in plain language before writing config or managed docs.

For `update all`:

1. Record starting primary-source `HEAD`.
2. Require a reachable commit and a clean tracked primary-source tree, excluding the approved docs/config write set.
3. Inspect the selected source and write the project docs and Atoms.
4. Run structural validation, semantic review, and structural validation again after any correction.
5. Recheck that ending `HEAD` equals starting `HEAD` and the tracked source remains clean.
6. Set `last_full_source_commit`, then validate the final config and docs state.

If any full-update condition fails, restore the previous `last_full_source_commit`, leave the full update incomplete, and report the recovery action.

For `update changed`:

1. Stop if `last_full_source_commit` is null, unreachable, or the tracked primary source is dirty; guide the user to `update all` or an explicit targeted update.
2. Diff the primary source from that commit to current `HEAD`.
3. Map each changed file to exact existing `Sources` locators. Those Atoms are seeds.
4. Add only direct `depends_on` dependencies and direct reverse dependents of the seeds.
5. Inspect changed source for new or unmapped context.
6. Report changed files, seed Atoms, adjacent Atoms, and uninspected boundaries. Never claim complete transitive closure.

Configured auxiliary sources stay pinned to their exact revisions. Do not include their unrelated changes in the primary changed diff; report auxiliary inspection separately.

## Review And Correction

After a write, assign one independent semantic reviewer over the complete managed-docs diff. The reviewer checks:

- development usefulness
- fidelity to source within the selected scope
- clear boundaries and contracts
- valid RID and `depends_on` relationships

The reviewer does not expand beyond the selected documentation questions. If review fails, correct once and have the same reviewer recheck the original findings once. If a material finding remains, stop and ask the user to decide. Do not add another review or handoff.

Run the plugin-bundled validator from `<plugin-root>/scripts/validate_atomic_docs.py`; never search for it in the target project. The final reported validator result must observe every semantic correction and final config write.

## Delete And Merge

Existing Atoms may be deleted or merged only after the user approves the exact source and target `atom_key` list. After approval:

- remove or merge the named files
- repair all `depends_on` references
- repair active RID ownership or impact
- validate and review the resulting docs diff

Use Git for recovery and create no separate recovery artifact. Dropping an uncommitted new candidate needs no permanent state.

## Required References

Read only the references needed for the operation:

- `references/docs-root-and-config.md` for config, storage, source roots, commit stability, and recovery.
- `references/atomic-document-contract.md` for project documents, Atom structure, RIDs, dependencies, and source locators.
- `references/refresh-flow.md` for `inspect`, update scopes, changed mapping, delete/merge, and reporting.
- `references/reviewer-perspectives.md` for the bounded reviewer and one-correction contract.
- `references/validation-contract.md` for structural validation and diagnostics.
- `references/language-policy.md` for prose language.
- `references/stageflow-integration.md` when Atomic Docs is used inside a Stageflow-controlled request.

## Boundaries

- Structural validation does not replace semantic review.
- A useful Atom points to exact source instead of restating source mechanics.
- Record a genuine unresolved product, ownership, or contract decision in `Open Questions`; do not create questions merely because exhaustive behavior was not documented.
- Ask the user only for a material product decision, write authorization not already implied by the request, or exact existing-Atom delete/merge approval.
