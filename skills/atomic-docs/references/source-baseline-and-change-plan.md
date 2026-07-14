# Source Baseline And Change Plan

## Contents

- [Responsibility](#responsibility)
- [Source Baseline](#source-baseline)
- [Change Scope Inputs](#change-scope-inputs)
- [Change Plan Requirements](#change-plan-requirements)

## Responsibility

This reference is the normative owner of global source-baseline schema and eligibility, carry-forward evidence, and the accepted docs change-plan shape. `refresh-flow.md` owns operation-profile selection and generic refresh routing; `reviewer-perspectives.md` owns reviewer verdicts; `change-judgment-policy.md` owns inference and judgment labels.

## Source Baseline

Project-wide freshness is tracked with one source-code commit hash stored in metadata at the managed docs root. The baseline metadata is outside individual atom files and exists only for complete project-wide coverage.

Use this exact baseline shape:

```json
{
  "version": "1",
  "source_commit": "<40-or-64-character-git-hash>",
  "coverage": "project-wide"
}
```

The baseline records the source commit used for a complete confirmed project-wide docs refresh. Compare `git diff <source_commit>..HEAD` or the equivalent source-root diff to prioritize later changes.

When judging code against docs, first determine whether the relevant source behavior is covered by the stored baseline. If the source behavior is newer than the docs baseline and has not been refreshed, classify the finding as `docs_stale` or include it in the refresh scope before making a stronger judgment.

Create the first baseline only when the accepted scope is the whole project, every discovered domain bundle has its required development-quality review and applicable risk review PASS at the same source commit, the project-wide integration/baseline reviewer PASSes, structural baseline validation PASSes, and no blocker prevents project-wide development judgment.

Advance an existing trusted baseline through `baseline-diff-refresh` without rerunning unaffected domain reviewers. Required reviews for impacted bundles must PASS at the new `source_commit_observed`. The project-wide reviewer may carry prior PASS results forward only after verifying a complete old-to-new source diff, ownership and graph expansion, shared-contract and criteria impact, and an operation-state record of prior/new commits, affected bundles, unchanged bundle classes, and carry-forward rationale. Carry-forward means the reviewed decision basis is unchanged; it is not a claim that an old review ran at the new commit.

Partial or targeted operations must not create, replace, or advance baseline metadata. Record their inspected commit as `source_commit_observed` in `.stageflow/atomic-docs/requests/<request-id>/work-state.json` and report the result as partial scope. That operation-local value is audit/resume state, not a global freshness claim.

Provisional atoms from `candidate` or `needs_confirmation` domains may be review targets, but they cannot support global baseline creation. In operation summaries, use project-wide baseline-ready wording only when the operation-local post-write review verifies project-wide decision coverage, source fidelity, applicable risk review, and integration consistency.

## Change Scope Inputs

Select `initial-baseline`, `baseline-diff-refresh`, `change-impact-refresh`, `targeted`, or `inspection` through `refresh-flow.md` before building a change plan. This reference consumes that profile only to decide whether baseline metadata is an allowed output and which commit/carry-forward evidence the plan must include; it does not repeat the generic refresh sequence.

For domain-level work, update the domain context atom when the domain goal, responsibility, included behavior, excluded behavior, adjacent boundary, or common-promotion rule changes. Update `project/project-glossary.md` when source or user intent changes project-wide terms, aliases, forbidden conflations, or domain-scoped terminology. If legacy `project/project-glossary-atom.md` exists, treat it as migration source material and include the migration/update action in the change plan.

## Change Plan Requirements

A compact change plan groups by domain and lists only applicable items from the following set. Do not add placeholder rows for unaffected artifacts, judgments, identities, or gates:

- criteria/config actions and approval state when criteria are new or changing
- accepted operation profile, Goal/state actions, source commit basis, temporary inventory/evidence paths, and post-write gate status
- project-document creation, retention, or accepted migration actions
- inspected source behavior and operation-local domain/atom candidates, owners, boundaries, dispositions, and coverage gaps
- affected atom files, sections, stable identities, splits/merges/moves, and selective AID actions under `atomic-document-contract.md` and `atom-format-and-judgment.md`
- decision-depth, source-fidelity, and risk-trigger impacts under `service-logic-coverage.md`
- applicable judgment, planned-change, gap, and confirmation actions under `change-judgment-policy.md`
- graph target/path/relationship actions under `atomic-graph.md`
- development, risk, integration, and baseline review gates selected by `reviewer-perspectives.md`
- global baseline or operation-local `source_commit_observed` actions under the Source Baseline contract above
- unresolved ownership, boundary, protected-action, or user decisions that prevent the planned write

The compact change plan defines the paths and write actions for the current docs operation. If every item is inside the user-accepted docs scope and follows approved criteria, that scope acceptance authorizes source-supported new domains and no second approval is required. Stop when the plan expands source/docs scope, moves/deletes/merges an existing boundary, leaves an ambiguous boundary requiring user judgment, performs migration, changes config/baseline outside the accepted action, or otherwise exceeds prior authorization.

Inference, confirmation, conflict, planned-change, and gap classification follow `change-judgment-policy.md`. The change plan names the affected decision and required action but does not redefine controlled labels or their precedence.
