# Source Baseline And Change Plan

## Contents

- [Source Baseline](#source-baseline)
- [Full Refresh](#full-refresh)
- [Targeted Docs Operation](#targeted-docs-operation)
- [Change Plan Requirements](#change-plan-requirements)
- [Inference And Gaps](#inference-and-gaps)

## Source Baseline

Freshness is tracked with one source-code commit hash stored in metadata at the managed docs root. The baseline metadata is outside individual atom files.

The baseline records the last source-code commit hash used for a confirmed docs refresh. The `atomic-docs` skill should compare `git diff <stored-source-hash>..HEAD` or the equivalent source-root diff to prioritize changed source behavior files.

When judging code against docs, first determine whether the relevant source behavior is covered by the stored baseline. If the source behavior is newer than the docs baseline and has not been refreshed, classify the finding as `docs_stale` or include it in the refresh scope before making a stronger judgment.

Baseline metadata may be updated only for the judgment-ready scope that is also implementation-reconstruction-ready and passed the operation-local post-write review. Provisional atoms from `candidate` or `needs_confirmation` domains may be review targets, but they must not be used to claim a project-wide judgment-ready baseline.

In operation summaries, call a scope a judgment-ready and implementation-reconstruction-ready scope only when the post-write gate stored under `.stageflow/atomic-docs/requests/<request-id>/post-write-review.md` or `work-state.json` `post_write_gate` explicitly verifies both judgment readiness and implementation reconstruction readiness.

## Full Refresh

A full refresh is a first-class operation when the user explicitly asks for it.

1. Read the configured docs root and source root.
2. Read the docs-root source commit baseline metadata.
3. If atomization criteria are needed and no approved criteria document exists, create or update the draft criteria document through the file-first flow before domain atom work.
4. After criteria approval and accepted docs write scope, satisfy the Atomic Docs Goal Gate before docs generation work.
5. Inspect changed source behavior files since the stored source commit hash and map baseline diffs to affected atoms through source-to-atom discovery and graph traversal.
6. Ignore tests, settings, schema, build, and auxiliary files by default unless the user requested auxiliary-file reflection.
7. Inspect project, common, and relevant domain context atoms when they exist.
8. Use source-to-atom seed discovery to find likely domain and atom candidates.
9. Build an operation-local service logic inventory for meaningful changed or targeted source behavior.
10. Expand affected scope through atomic graph traversal.
11. Stop graph expansion when related atom files no longer create modification candidates.
12. Present a domain-grouped change plan before writing domain atom docs.
13. Write confirmed updates only after the change plan is accepted.
14. Update the docs-root source commit baseline metadata only after confirmed docs writes for the accepted operation are complete, post-write review passes, and the updated scope is judgment-ready and implementation-reconstruction-ready.

## Targeted Docs Operation

Targeted domain or atom work is also a first-class flow. When targeted work overlaps with full-refresh scope, prioritize the current user-requested target. Put adjacent affected scope in follow-up proposals or `Gaps`.

For domain-level work, update the domain context atom when the domain goal, responsibility, included behavior, excluded behavior, adjacent boundary, or common-promotion rule changes. Update `project/project-glossary.md` when source or user intent changes project-wide terms, aliases, forbidden conflations, or domain-scoped terminology. If legacy `project/project-glossary-atom.md` exists, treat it as migration source material and include the migration/update action in the change plan.

## Change Plan Requirements

A change plan should group by domain and list:

- the limited first write action for draft criteria creation or update at `project/atomization-criteria.md` when criteria are new or changed
- `검토된 Atom화 관점`, including user-visible criteria additions, removals, revisions, approval status, and whether the criteria document is draft or approved
- user-conversation criteria that must be recorded in the criteria document before source-derived atom drafting
- source exploration results that update the criteria document instead of remaining only in the change plan
- Atomic Docs Goal Gate status, including whether `create_goal` was created or an active Goal already covers the accepted docs operation
- project document creation, update, or legacy migration actions, including `project/project-goal.md`, `project/project-glossary.md`, `project/source-convention.md`, and `project/service-logic-inventory.md` only when the user explicitly retains a final coverage index
- atomic-docs operation state updates under `.stageflow/atomic-docs/requests/<request-id>/`, including accepted write scope, bundle queue, temporary inventory/evidence/review paths, and post-write gate status
- source convention document creation or update at `project/source-convention.md` when source interpretation conventions are in scope
- source behavior files inspected
- operation-local service logic inventory items, including natural-language behavior, source identifiers, candidate owning atom key, and coverage gaps
- implementation reconstruction readiness for the accepted scope, including frontend/UI coverage, backend/API/service coverage, and unresolved `confirmation_needed` blockers that prevent docs-only implementation
- AID assignments for new or changed atom meaning lines, and explicit AID migrations when existing IDs cannot be preserved
- affected atom files
- affected atom sections
- judgment labels for review findings, including `matches_confirmed_intent`, `bug_or_regression`, `missing_required_behavior`, `unapproved_implemented_behavior`, `out_of_scope_behavior`, `confirmation_needed`, or `docs_stale`
- related AID values for judgment labels, review findings, coverage gaps, and source evidence mappings whenever the referenced atom lines are known
- new domains, category or domain-path moves, atom splits, atom merges, and split proposals
- atom identity changes, including `atom_key` preservation for moves/renames/splits/merges, legacy slug-derived fallback migrations, and duplicate `atom_key` conflicts
- project goal, project glossary, service logic inventory, source convention, common context, or domain context changes
- core business terms that require glossary or domain atom coverage before derived behavior is treated as covered
- parent business terms missing or underdefined in the glossary, including their source evidence and whether they belong in `Gaps`
- inferred `Intent` or `Rules` that require confirmation
- natural-language `Current Implementation` changes
- `Planned Changes` reconciliation candidates
- `Gaps`, bug candidates, uncertain mappings, rename/merge proposals, and implemented-plan candidates
- graph path corrections, `target_key`/`target_path` consistency, or target-key conflicts
- source-baseline metadata updates and docs-root config writes, including whether the update is limited to a judgment-ready partial scope or a project-wide judgment-ready baseline, and whether that scope is implementation-reconstruction-ready
- unresolved boundary questions that must be accepted before writing confirmed structure

The accepted change plan defines the only paths and write actions allowed for the current docs operation. Do not write atom files, graph corrections, source-baseline metadata, docs-root config, or managed docs root structure before that acceptance.

## Inference And Gaps

The skill may draft `Current Implementation`, `Gaps`, and inferred `Intent` or `Rules` from code. Inferred `Intent` and `Rules` remain inferred until confirmed by the user. Inferred `Intent` or inferred `Rules` alone cannot create confirmed required behavior, confirmed out-of-scope behavior, or `matches_confirmed_intent`; use `confirmation_needed` until the user or approved workflow confirms the basis.

If observed code conflicts with confirmed intent or rules, do not resolve the conflict silently; preserve it as a `bug_or_regression` or another judgment-labeled gap. Do not write a generic gap when the issue is specifically missing required behavior, unapproved implementation, out-of-scope behavior, stale docs, or confirmation-needed uncertainty. Do not classify behavior as healthy only because no related gap exists.

Docs may only judge source behavior against service logic that is actually recorded in natural language. Source behavior absent from the docs is not implicitly correct; record it as a coverage gap, `confirmation_needed`, or `docs_stale` depending on the baseline and evidence. If missing frontend/UI or backend/API/service details would force an implementer to reread source or make arbitrary behavior choices, do not call the scope implementation-reconstruction-ready; record the missing details and next action instead.
