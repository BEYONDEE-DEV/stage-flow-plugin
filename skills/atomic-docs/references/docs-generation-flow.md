# Docs Generation Flow

## Contents

- [Atomic Docs Goal Gate](#atomic-docs-goal-gate)
- [Atomic Docs Operation State](#atomic-docs-operation-state)
- [Required Subagent Authorization](#required-subagent-authorization)
- [Sequential Domain Bundles](#sequential-domain-bundles)
- [Conditional Project-Wide Gate](#conditional-project-wide-gate)

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

Keep accepted scope, bundle queue, active bundle, compact write plan, applicable risk triggers, writer/reviewer results, temporary evidence paths, project-review state, and `source_commit_observed` here. Record the source basis in every reviewer result. This state is not a Stageflow request, managed docs output, or direct implementation evidence.

Temporary `inventory.md`, `evidence.md`, domain review files, and `post-write-review.md` may live beside request state. Delete or ignore temporary inventory after completion unless the accepted scope explicitly retains a synced project coverage index.

Only Atomic Impl or an explicit docs/code compliance operation adds `## 구현 검증` to the linked request's `post-write-review.md`. Record docs and implementation basis once, followed by one row per changed in-scope required AID with `관련 AID | 구현 근거 | 검증 근거 | 판정 또는 gap`.

Normal docs generation or refresh does not require this table. Do not store it in an atom, project inventory, `work-state.json`, or a separate verification-trace file. If either basis changes, review only affected AID rows again.

For partial or targeted docs work, record the inspected source commit as `source_commit_observed`. Never use this operation-local value to advance the managed docs global source baseline.

## Required Subagent Authorization

Accepted bootstrap scope authorizes criteria-review and revision cycles. After criteria approval, accepted docs scope, and Goal handoff, the writer, required development-quality reviewer, applicable risk/contract reviewer, applicable project-wide reviewer, and their reruns are authorized operation steps and do not require separate approval merely to run.

Ask again only when a required step needs deletion, migration, push, an external service call, or a blocker cannot PASS without user judgment. Do not stop because a required subagent was not named again.

## Sequential Domain Bundles

Split multi-domain work into a sequential queue of durable domains or accepted domain shards. Do not run domain bundles in parallel by default.

Before writing each bundle, classify and record the applicable risk triggers from `service-logic-coverage.md`. Ordinary CRUD or preference persistence is not a trigger by itself. Do not invent a risk trigger merely to add review, and do not omit one to save time.

Record a compact domain-grouped write plan before the first writer. When every path and action stays inside the accepted docs scope and approved boundaries, that prior scope approval authorizes the plan and no second user approval is required. Ask again for an expanded source/docs scope, a new or moved domain boundary, deletion, migration, or another protected action.

Each domain bundle uses exactly one writer. The writer produces or revises lightweight inventory rows, source evidence, atom files, selective AIDs, graph candidates, project-document impacts, and explicit dispositions at behavior-aggregate depth.

After the writer, run exactly one independent development-quality reviewer. If any recorded risk trigger applies, also run exactly one independent risk/contract reviewer. The contracts and required principle files are defined in `reviewer-perspectives.md`.

If a reviewer FAILs, revise the same bundle and rerun that reviewer plus any reviewer whose evidence changed. Do not rerun unaffected PASS results. Do not start the next bundle until every reviewer applicable to the active bundle PASSes or a user decision is required.

If later work changes an earlier bundle's boundary, ownership, graph, shared contract, source evidence, risk classification, or decision basis, reopen that bundle and rerun its writer and affected reviewers. Rerun dependent later bundles only when their PASS basis changed.

`confirmation_needed` blocks a bundle only when the unresolved decision prevents the accepted scope from supporting implementation or verification. Other uncertainty may remain as a supported labeled gap in a provisional or partial result.

## Conditional Project-Wide Gate

Run one project-wide integration/baseline reviewer after applicable domain reviews PASS when the accepted operation is project-wide, changes multiple domains, changes a shared cross-domain contract or cross-domain ownership/graph relationship, or seeks global baseline creation/update.

Do not run a project-wide reviewer for an ordinary targeted single-domain operation with no shared-contract or baseline effect.

The project-wide reviewer checks cross-domain ownership and graph consistency, shared contracts, changed evidence, reporting accuracy, and baseline eligibility. It trusts unchanged local detail and does not repeat complete domain review.

If the project-wide reviewer finds a domain defect, reopen the affected bundle, rerun its writer and affected reviewers, then rerun the project-wide reviewer.

Reconcile durable criteria after writing: remove stale pending/future/current-run notes while preserving durable rules, approved or unresolved boundaries, decision-depth rules, risk triggers, and active blockers. Keep bundle queues and review logs in operation state.

For global baseline work, do not report project-wide completion, create or update baseline metadata, or complete the Goal until every applicable domain/risk review and the project-wide reviewer PASS, structural validation passes, and no blocker prevents project-wide development judgment. A partial result may be reported as partial but never advances the global baseline.
