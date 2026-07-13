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

Keep each state file's ownership narrow:

- `index.json`: request lookup only
- `sessions/<session-id>/current.json`: the active request pointer only
- `requests/<request-id>/state.json`: request lifecycle and session/Goal links only
- `requests/<request-id>/work-state.json`: the only owner of operation profile, accepted scope, `source_commit_observed`, ownership prepass, bundle queue, active attempt, persistent agent IDs, risk triggers, changed artifacts, reviewer verdicts, finding fingerprints, temporary evidence paths, integration/baseline state, and carry-forward basis

Do not duplicate queue position, source basis, agent identity, or reviewer state across these files. This state is not a Stageflow request, managed docs output, or direct implementation evidence.

Temporary `inventory.md`, `evidence.md`, compact domain review files, and `post-write-review.md` may live beside request state. Create `inventory.md` and `evidence.md` only after criteria approval and scope acceptance. Pin evidence to `source_commit_observed` and reuse it as a source-navigation index. Delete or ignore temporary inventory/evidence after completion unless the accepted scope explicitly retains a synced project coverage index.

Only Atomic Impl or an explicit docs/code compliance operation adds `## 구현 검증` to the linked request's `post-write-review.md`. Record docs and implementation basis once, followed by one row per changed in-scope required AID with `관련 AID | 구현 근거 | 검증 근거 | 판정 또는 gap`.

Normal docs generation or refresh does not require this table. Do not store it in an atom, project inventory, `work-state.json`, or a separate verification-trace file. If either basis changes, review only affected AID rows again.

For partial or targeted docs work, record the inspected source commit as `source_commit_observed`. Never use this operation-local value to advance the managed docs global source baseline.

## Required Subagent Authorization

Accepted bootstrap scope authorizes criteria-review and revision cycles. After criteria approval, accepted docs scope, and Goal handoff, the writer, required development-quality reviewer, applicable risk/contract reviewer, applicable integration/baseline reviewer, and their reruns are authorized operation steps and do not require separate approval merely to run.

Ask again only when a required step needs deletion, migration, push, an external service call, or a blocker cannot PASS without user judgment. Do not stop because a required subagent was not named again.

## Sequential Domain Bundles

Split multi-domain work into a sequential queue of durable domains or cohesive accepted domain shards. One bundle may own several atoms; do not create a writer/reviewer cycle per atom. Do not run domain bundles in parallel by default.

For multi-domain or `initial-baseline` work, run the lightweight ownership/evidence prepass from `project-documents-and-inventory.md`. Confirm shared/high-fan-out owners first, then order their bundles before direct dependents. A targeted operation performs only local ownership and adjacent-contract checks. Do not require every local owner to be final before the first writer.

Before writing each bundle, classify and record the applicable risk triggers from `service-logic-coverage.md`. Ordinary CRUD or preference persistence is not a trigger by itself. Do not invent a risk trigger merely to add review, and do not omit one to save time.

Record a compact domain-grouped write plan before the first writer. Report domain count, bundle count, risk-bundle count, shared-owner count, and expected final-review type in a short non-blocking user update. Do not invent an ETA. When every path and action stays inside accepted docs scope and boundaries, prior scope approval authorizes the plan. Ask again only for expanded source/docs scope, an ambiguous or moved boundary requiring user judgment, deletion, migration, or another protected action.

Create one writer and one independent development-quality reviewer for the operation and record their agent IDs in `work-state.json`. Reuse them for every sequential bundle. The writer uses the shared evidence index, reopens source when needed, and produces or revises inventory rows, atom files, selective AIDs, meaningful graph candidates, project-document impacts, and explicit dispositions. The reviewer receives managed docs, source/evidence, criteria, and operation state, but not the writer's private reasoning conversation.

When the first risk trigger appears, create one risk/contract reviewer and reuse it for later triggered bundles. If a persistent agent is unavailable or its context can no longer support the queue, create one same-role replacement using a compact handoff containing `work-state.json`, evidence index, active bundle, and last verdict. Do not spawn a fresh writer/reviewer pair merely because the queue advanced.

## Bundle Preflight And Review

After each writer and before semantic review, run the plugin validator in docs phase with every atom key expected from that bundle:

```text
python <plugin-root>/scripts/validate_atomic_docs.py --root <target-project-root> --phase docs --expect-atom-key <key> [--expect-atom-key <key> ...]
```

Also check operation-local ownership closure, source basis, and planned atom keys against actual atom keys. Compare keys and dispositions, not raw document counts. Do not add an active/retired AID lifecycle merely for preflight; report total discovered AIDs and deterministic duplicate/shape failures.

If preflight FAILs, return to the writer without spending a semantic review. After PASS, classify what changed:

- new atom, `atom_key`, `Intent`, `Rules`, behavior/contract meaning, `Planned Changes`, `Gaps`, judgment, owner, graph `type`, or graph `target_key`: run the development-quality reviewer
- Markdown formatting, file relocation, or graph `target_path` with unchanged meaning/key: scoped validator only
- source locator/evidence correction with unchanged claim: narrowed source-evidence check by the development reviewer, not a complete domain review

Record one review input revision. When development and risk reviews both apply, run the persistent reviewers in parallel against that same revision and source basis. An `initial-baseline` still requires development review for every domain bundle.

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

Do not reconcile discovered domains, atom candidates, source evidence, or review results back into durable criteria. Update criteria after writing only when the user approved a durable rule, project exception, or previously unresolved criteria decision.

For an initial global baseline, do not create metadata until every domain/risk review PASSes at `source_commit_observed`. For `baseline-diff-refresh`, impacted reviews must PASS at the new commit; unchanged reviews may be carried from the trusted prior baseline only when the operation records the old/new commits, unchanged bundles, complete diff-impact rationale, and project-wide reviewer approval. Structural validation and the reviewer must PASS before the baseline advances.

## Progress Guard

Do not use a fixed wall-clock timeout as a quality rule. A source-heavy writer may legitimately take longer. Instead, require every completed writer/reviewer run to report changed artifacts/evidence or a concrete finding.

After two bundles complete, report measured completed/remaining bundle counts and any change in risk or final-review scope. This is informational and does not pause the queue. Do not fabricate a time estimate when the operation lacks reliable elapsed measurements.

If a completed writer produces none of the planned artifact/evidence changes, stop before semantic review and diagnose scope, ownership, tool, or prompt failure. If the same blocking finding fingerprint recurs twice without a changed decision, source basis, or artifact, do not launch the same cycle again. Report the cause, revise the bundle plan or reviewer routing, and move only dependency-independent bundles while the blocker is resolved.
