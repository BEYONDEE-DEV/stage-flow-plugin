# Docs Generation Flow

## Contents

- [Atomic Docs Goal Gate](#atomic-docs-goal-gate)
- [Atomic Docs Operation State](#atomic-docs-operation-state)
- [Required Subagent Authorization](#required-subagent-authorization)
- [Sequential Domain Bundles](#sequential-domain-bundles)
- [Project-Wide Final Gate](#project-wide-final-gate)

## Atomic Docs Goal Gate

Bootstrap criteria drafting and criteria-review/revision do not require a Codex Goal. That limited scope may create or update only `.stageflow/atomic-docs.json` and `<doc-root>/project/atomization-criteria.md`.

After criteria approval and accepted docs write scope, call `create_goal` before creating project docs, inventory, atom files, graph edges, domain subagents, review output, or baseline metadata. The Goal objective must name the criteria path, docs root, accepted write scope, source-to-docs-to-code reconstruction requirement, domain writer/four-reviewer cycle, project-wide final gate, and completion condition.

If Goal creation is unavailable or fails, stop before docs generation. Complete the Goal only after the accepted operation actually satisfies its required review and validation gates. A reviewer that has not run, or an in-scope review FAIL that still needs correction, is not a Goal-blocked state.

## Atomic Docs Operation State

After criteria approval and scope acceptance, create or resume atomic-docs-owned operation state:

```text
.stageflow/atomic-docs/index.json
.stageflow/atomic-docs/sessions/<session-id>/current.json
.stageflow/atomic-docs/requests/<request-id>/state.json
.stageflow/atomic-docs/requests/<request-id>/work-state.json
```

Keep accepted scope, bundle queue, active bundle, writer/reviewer results, temporary evidence paths, final-review state, and `source_commit_observed` here. This state is not a Stageflow request, managed docs output, or code-suitability evidence.

Temporary `inventory.md`, `evidence.md`, domain review files, and `post-write-review.md` may live beside request state. Delete or ignore temporary inventory after completion unless the accepted scope explicitly retains a synced project coverage index.

For partial or targeted docs work, record the inspected source commit as `source_commit_observed`. Never use this operation-local value to advance the managed docs global source baseline.

## Required Subagent Authorization

Accepted bootstrap scope authorizes criteria-review and revision cycles. After criteria approval, accepted docs scope, and Goal handoff, the writer, four domain reviewers, reviewer reruns, and four project-wide final reviewers are authorized operation steps and do not require separate approval merely to run.

Ask again only when a required step needs deletion, migration, push, an external service call, or a blocker cannot PASS without user judgment. Do not stop because a required subagent was not named again.

## Sequential Domain Bundles

Split multi-domain work into a sequential queue of durable domains or accepted domain shards. Do not run domain bundles in parallel by default.

Each domain bundle uses exactly one writer and exactly four independent draft reviewers. The writer produces or revises the bundle's inventory rows, source evidence, atom files, AIDs, graph candidates, project-document impacts, and explicit dispositions. The four reviewer perspectives and their principle files are defined in `reviewer-perspectives.md`.

Run the four reviewers after the writer. If a perspective FAILs, revise the same bundle and rerun that perspective plus any perspective whose evidence changed. Do not rerun unaffected PASS results. Do not start the next bundle until all four perspectives PASS or a user decision is required.

Only a four-reviewer-PASS bundle can become input to the next bundle. If later work changes an earlier bundle's boundary, ownership, graph, shared contract, glossary/source convention, source evidence, or reconstruction basis, reopen that bundle and rerun its writer and affected reviewer perspectives. Rerun dependent later bundles when their PASS basis changed.

`confirmation_needed` blocks a bundle only when the unresolved decision prevents the accepted scope from reaching its declared readiness. Other uncertainty may remain as a supported labeled gap in a provisional or partial result.

## Project-Wide Final Gate

After every accepted bundle has four PASS results, run four separate project-wide final reviewer subagents from `reviewer-perspectives.md`. These reviewers check cross-domain boundaries and graph, project-wide source closure and changed shared evidence, end-to-end reconstruction across frontend/backend or other boundaries, and global baseline/reporting eligibility.

Final reviewers must not repeat unchanged row-level or branch-level domain review. They may recheck local evidence when a cross-domain contradiction, changed shared source, or missing end-to-end link makes the earlier PASS basis unreliable.

If a final reviewer finds a domain defect, reopen the affected bundle, rerun its writer and affected domain reviewers, then rerun every final perspective whose basis changed. Record perspective verdicts, principle files, blockers, and rerun status in operation-local post-write review.

Reconcile durable criteria after writing: remove stale pending/future/current-run notes while preserving durable rules, approved or unresolved boundaries, and active blockers. Keep bundle queues and review logs in operation state.

Do not report project-wide completion, create or update global baseline metadata, or complete the Goal until all four final perspectives PASS, structural validation passes, and no blocker prevents project-wide implementation reconstruction or judgment readiness. Partial results may be reported as partial but never advance the global baseline.
