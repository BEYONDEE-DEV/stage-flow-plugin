# Docs Generation Flow

## Contents

- [Atomic Docs Goal Gate](#atomic-docs-goal-gate)
- [Atomic Docs Operation State](#atomic-docs-operation-state)
- [Required Subagent Authorization](#required-subagent-authorization)
- [Sequential Domain Bundles](#sequential-domain-bundles)
- [Bundle Preflight And Review](#bundle-preflight-and-review)
- [Conditional Integration And Baseline Gate](#conditional-integration-and-baseline-gate)
- [Progress Guard](#progress-guard)

## Atomic Docs Goal Gate

Bootstrap criteria drafting and criteria-review/revision do not require a Codex Goal. That limited scope may create or update only `.stageflow/atomic-docs.json` and `<doc-root>/project/atomization-criteria.md`.

After criteria approval and accepted docs write scope, call `create_goal` before creating project docs, inventory, atom files, graph edges, domain subagents, review output, or baseline metadata. The Goal objective must name the criteria path, docs root, accepted write scope, decision-complete documentation requirement, applicable domain/risk/project review gates, and completion condition.

If Goal creation is unavailable or fails, stop before docs generation. Complete the Goal only after the accepted operation satisfies every applicable review and validation gate. A reviewer that has not run, or an in-scope review FAIL that still needs correction, is not a Goal-blocked state.

## Atomic Docs Operation State

After criteria approval and scope acceptance, create or resume atomic-docs-owned operation state:

```text
.stageflow/atomic-docs/index.json
.stageflow/atomic-docs/sessions/<session-id>/current.json
.stageflow/atomic-docs/requests/<request-id>/state.json
.stageflow/atomic-docs/requests/<request-id>/work-state.json
```

Keep operation profile, accepted scope, ownership prepass, dependency-ordered bundle queue, active bundle, bundle attempt, review input revision, compact write plan, applicable risk triggers, changed artifacts, reviewer results, finding fingerprint, temporary evidence paths, integration/baseline-review state, baseline carry-forward basis when applicable, and `source_commit_observed` here. Record source basis and review input revision in every reviewer result. This state is not a Stageflow request, managed docs output, or direct implementation evidence.

Temporary `inventory.md`, `evidence.md`, domain review files, and `post-write-review.md` may live beside request state. Pin `evidence.md` to `source_commit_observed` and reuse it as a source-navigation index. Delete or ignore temporary inventory/evidence after completion unless the accepted scope explicitly retains a synced project coverage index.

Only Atomic Impl or an explicit docs/code compliance operation adds `## 구현 검증` to the linked request's `post-write-review.md`. Record docs and implementation basis once, followed by one row per changed in-scope required AID with `관련 AID | 구현 근거 | 검증 근거 | 판정 또는 gap`.

Normal docs generation or refresh does not require this table. Do not store it in an atom, project inventory, `work-state.json`, or a separate verification-trace file. If either basis changes, review only affected AID rows again.

For partial or targeted docs work, record the inspected source commit as `source_commit_observed`. Never use this operation-local value to advance the managed docs global source baseline.

## Required Subagent Authorization

Accepted bootstrap scope authorizes criteria-review and revision cycles. After criteria approval, accepted docs scope, and Goal handoff, the writer, required development-quality reviewer, applicable risk/contract reviewer, applicable integration/baseline reviewer, and their reruns are authorized operation steps and do not require separate approval merely to run.

Ask again only when a required step needs deletion, migration, push, an external service call, or a blocker cannot PASS without user judgment. Do not stop because a required subagent was not named again.

## Sequential Domain Bundles

Split multi-domain work into a sequential queue of durable domains or accepted domain shards. Do not run domain bundles in parallel by default.

For multi-domain or `initial-baseline` work, run the lightweight ownership/evidence prepass from `project-documents-and-inventory.md`. Confirm shared/high-fan-out owners first, then order their bundles before direct dependents. A targeted operation performs only local ownership and adjacent-contract checks. Do not require every local owner to be final before the first writer.

Before writing each bundle, classify and record the applicable risk triggers from `service-logic-coverage.md`. Ordinary CRUD or preference persistence is not a trigger by itself. Do not invent a risk trigger merely to add review, and do not omit one to save time.

Record a compact domain-grouped write plan before the first writer. When every path and action stays inside the accepted docs scope and approved boundaries, that prior scope approval authorizes the plan and no second user approval is required. Ask again for an expanded source/docs scope, a new or moved domain boundary, deletion, migration, or another protected action.

Each domain bundle uses exactly one writer. The writer uses the shared evidence index, reopens source when needed, and produces or revises lightweight inventory rows, atom files, selective AIDs, graph candidates, project-document impacts, and explicit dispositions at behavior-aggregate depth. At completion, record the changed artifacts/evidence and increment the bundle attempt.

## Bundle Preflight And Review

After each writer and before semantic review, run the plugin validator in docs phase with every atom key expected from that bundle:

```text
python <plugin-root>/scripts/validate_atomic_docs.py --root <target-project-root> --phase docs --expect-atom-key <key> [--expect-atom-key <key> ...]
```

Also check operation-local ownership closure, source basis, and planned atom keys against actual atom keys. Compare keys and dispositions, not raw document counts. Do not add an active/retired AID lifecycle merely for preflight; report total discovered AIDs and deterministic duplicate/shape failures.

If preflight FAILs, return to the writer without spending a semantic review. After preflight PASS, record one review input revision. Run exactly one independent development-quality reviewer and, when a risk trigger applies, exactly one independent risk/contract reviewer in parallel against that same revision and source basis. Parallel review reduces elapsed time but does not let one reviewer replace the other.

Repeated `--expect-atom-key` scopes this preflight to the active bundle while still checking its AIDs and graph targets against the whole docs set. Unrelated pre-existing structural findings do not block the bundle. Run unscoped docs validation after the accepted queue finishes and before any baseline validation.

After a shared-owner bundle or cross-domain ownership/graph change, run lightweight integration lint for duplicate owners, unresolved shared contracts, expected atom keys, graph targets, and source-basis consistency. This is not a project-wide semantic review.

The reviewer contracts and change-type rerun routing are defined in `reviewer-perspectives.md`. Do not start the next bundle until every reviewer applicable to the active bundle PASSes or a user decision is required.

If later work changes an earlier bundle's boundary, ownership, graph, shared contract, source evidence, risk classification, or decision basis, reopen that bundle and rerun its writer and affected reviewers. Rerun dependent later bundles only when their PASS basis changed.

After a shared-owner bundle PASSes, record its reviewed revision as the owner basis. A dependent writer references that basis and must not redefine the owner or shared contract silently. When source evidence contradicts it, pause the dependent bundle, reopen the owner bundle, and then reopen only dependents whose recorded basis changed.

`confirmation_needed` blocks a bundle only when the unresolved decision prevents the accepted scope from supporting implementation or verification. Other uncertainty may remain as a supported labeled gap in a provisional or partial result.

## Conditional Integration And Baseline Gate

Run one integration reviewer after applicable domain reviews PASS when a shared cross-domain contract, ownership, glossary source of truth, or graph relationship changed. For `targeted` or `change-impact-refresh`, inspect only the affected closure. Independent changes in several domains do not require this reviewer merely because more than one bundle changed.

For `initial-baseline` or `baseline-diff-refresh`, expand the same role to a project-wide integration/baseline review. Do not run it for an ordinary targeted single-domain operation with no shared relationship or baseline effect.

The reviewer checks cross-domain ownership and graph consistency, shared contracts, changed evidence, reporting accuracy, and baseline eligibility when applicable. It trusts unchanged local detail and does not repeat complete domain review.

If the project-wide reviewer finds a domain defect, reopen the affected bundle, rerun its writer and affected reviewers, then rerun the project-wide reviewer.

Reconcile durable criteria after writing: remove stale pending/future/current-run notes while preserving durable rules, approved or unresolved boundaries, decision-depth rules, risk triggers, and active blockers. Keep bundle queues and review logs in operation state.

For an initial global baseline, do not create metadata until every domain/risk review PASSes at `source_commit_observed`. For `baseline-diff-refresh`, impacted reviews must PASS at the new commit; unchanged reviews may be carried from the trusted prior baseline only when the operation records the old/new commits, unchanged bundles, complete diff-impact rationale, and project-wide reviewer approval. Structural validation and the reviewer must PASS before the baseline advances.

## Progress Guard

Do not use a fixed wall-clock timeout as a quality rule. A source-heavy writer may legitimately take longer. Instead, require every completed writer/reviewer run to report changed artifacts/evidence or a concrete finding.

If a completed writer produces none of the planned artifact/evidence changes, stop before semantic review and diagnose scope, ownership, tool, or prompt failure. If the same blocking finding fingerprint recurs twice without a changed decision, source basis, or artifact, do not launch the same cycle again. Report the cause, revise the bundle plan or reviewer routing, and move only dependency-independent bundles while the blocker is resolved.
