# Docs Generation Flow

## Contents

- [Responsibility](#responsibility)
- [Atomic Docs Goal Gate](#atomic-docs-goal-gate)
- [Atomic Docs Operation State](#atomic-docs-operation-state)
- [Required Subagent Authorization](#required-subagent-authorization)
- [Sequential Domain Bundles](#sequential-domain-bundles)
- [Bundle Preflight And Review](#bundle-preflight-and-review)
- [Conditional Integration And Baseline Gate](#conditional-integration-and-baseline-gate)
- [Progress Guard](#progress-guard)

## Responsibility

This reference owns Atomic Docs operation state from bootstrap through post-approval execution, including Goal handoff, persistent agents, sequential bundles, preflight order, and progress handling. Bootstrap discovery and approval sequencing belong to `criteria-flow.md`, operation-profile definitions to `refresh-flow.md`, semantic reviewer selection to `reviewer-perspectives.md`, and baseline eligibility to `source-baseline-and-change-plan.md`.

## Atomic Docs Goal Gate

Bootstrap criteria drafting, domain-proposal discovery, and bootstrap review/revision do not require a Codex Goal. Accepted bootstrap scope may create or update `.stageflow/atomic-docs.json`, `<doc-root>/project/atomization-criteria.md`, Atomic Docs request state, `work-state.json`, and a domain-only `inventory.md`.

After the combined approval of criteria, source-supported domain boundaries, and selected domain write scope, call `create_goal` before creating detailed `evidence.md`, Atom/context candidates, project docs, atom files, graph edges, domain writer/reviewer bundles, post-write review output, or baseline metadata. The Goal objective must name the criteria path, docs root, approved tentative domain paths, implementation-context selection requirement, applicable domain/risk/project review gates, and completion condition.

If Goal creation is unavailable or fails, preserve the approved criteria, domain paths, accepted scope, review PASS, and empty Goal link; stop before docs generation and retry the same Goal objective without asking for approval again. Complete the Goal only after the accepted operation satisfies every applicable review and validation gate. A reviewer that has not run, or an in-scope review FAIL that still needs correction, is not a Goal-blocked state.

## Atomic Docs Operation State

After the user accepts project-wide or targeted bootstrap discovery, create or resume atomic-docs-owned operation state:

```text
.stageflow/atomic-docs/index.json
.stageflow/atomic-docs/sessions/<session-id>/current.json
.stageflow/atomic-docs/requests/<request-id>/state.json
.stageflow/atomic-docs/requests/<request-id>/work-state.json
```

Keep each state file's ownership narrow:

- `index.json`: request lookup only
- `sessions/<session-id>/current.json`: the active request pointer only
- `requests/<request-id>/state.json`: request lifecycle and session/Goal links only; the Goal link stays empty before combined approval and Goal success
- `requests/<request-id>/work-state.json`: the only owner of operation profile, bootstrap discovery scope, domain candidate status, accepted scope, `source_commit_observed`, context selection and ownership prepass, bundle queue, active attempt, persistent agent IDs, risk triggers, changed artifacts, reviewer verdicts, finding fingerprints, temporary evidence paths, integration/baseline state, and carry-forward basis

Do not duplicate queue position, source basis, agent identity, or reviewer state across these files. This state is not a Stageflow request, managed docs output, or direct implementation evidence.

Before combined approval, keep accepted scope and execution profile empty and use `inventory.md` only for the domain proposal contract in `project-documents-and-inventory.md`; do not create queues, detailed evidence, or Atom candidates. `work-state.json` is the authoritative owner of domain candidate status; the inventory status column only mirrors it for user review. On approval, set only user-selected valid tentative domain paths to `approved` and accepted scope. Keep unselected and `needs_confirmation` domains outside that scope. Select `initial-baseline` only when baseline creation was included in the approved action and every required project domain is approved; partial approval selects `targeted` and cannot advance the global baseline.

After Goal success, expand the same `inventory.md` for approved-domain context candidates and create `evidence.md` pinned to `source_commit_observed`. Temporary evidence, compact domain review files, and `post-write-review.md` may then live beside request state. Delete or ignore temporary inventory/evidence after completion unless the accepted scope explicitly retains a synced project context index.

Atomic Docs request state remains owned by Atomic Docs even when a caller uses Stageflow, Simple Workflow, or another workflow. A caller session may link to the request but must not duplicate or replace its discovery scope, domain status, accepted scope, queue, or Goal link.

Only Atomic Impl or an explicit docs/code compliance operation adds `## 구현 검증` to the linked request's `post-write-review.md`. Record docs and implementation basis once, followed by one row per changed in-scope required AID with `관련 AID | 구현 근거 | 검증 근거 | 판정 또는 gap`.

Normal docs generation or refresh does not require this table. Do not store it in an atom, project inventory, `work-state.json`, or a separate verification-trace file. If either basis changes, review only affected AID rows again.

For partial or targeted docs work, record the inspected source commit as `source_commit_observed`. Never use this operation-local value to advance the managed docs global source baseline.

## Required Subagent Authorization

Accepted bootstrap scope authorizes domain-proposal discovery plus criteria and boundary review/revision cycles. After combined approval and Goal handoff, the writer, required development-quality reviewer, applicable risk/contract reviewer, applicable integration/baseline reviewer, and their reruns are authorized operation steps and do not require separate approval merely to run.

Ask again only when a required step needs deletion, migration, push, an external service call, or a blocker cannot PASS without user judgment. Do not stop because a required subagent was not named again.

## Sequential Domain Bundles

Split multi-domain work into a sequential queue of durable domains or cohesive accepted domain shards. One bundle may own several atoms; do not create a writer/reviewer cycle per atom. Do not run domain bundles in parallel by default.

For multi-domain or `initial-baseline` work, run the lightweight ownership/evidence prepass from `project-documents-and-inventory.md`. Confirm shared/high-fan-out owners first, then order their bundles before direct dependents. A targeted operation performs only local ownership and adjacent-contract checks. Do not require every local owner to be final before the first writer.

Before writing each selected bundle, classify and record the applicable risk triggers from `service-logic-coverage.md`. Ordinary CRUD, preference persistence, or a risk-shaped source surface is not a trigger by itself when no selected context or approved change relies on it. Do not invent a risk trigger merely to add review, and do not omit one from selected high-impact context to save time.

Record a compact domain-grouped write plan before the first writer. Report domain count, bundle count, risk-bundle count, shared-owner count, and expected final-review type in a short non-blocking user update. Do not invent an ETA. When every path and action stays inside accepted docs scope and approved boundaries, prior scope approval authorizes the plan.

Before Goal creation, an affected boundary review and user approval may replace accepted domain paths. After the Goal becomes active, its approved domain paths and accepted scope are immutable: do not add a newly discovered domain, moved/merged path, or scope-expanding boundary to its queue. A same-path boundary clarification may continue after affected review and user approval only when it preserves the Goal outcome and scope. Put independent new scope in a follow-up Atomic Docs request/Goal after the active Goal finishes. If a changed boundary invalidates an active in-scope path, stop that bundle and ask whether to complete unaffected scope or end the current operation before opening the replacement request. Never create a second Goal while the first is active.

Ask again for expanded source/docs scope, an ambiguous or moved boundary requiring user judgment, deletion, migration, or another protected action.

Create one writer and one independent development-quality reviewer for the operation and record their agent IDs in `work-state.json`. Reuse them for every sequential selected bundle. The writer uses the shared evidence index, reopens source when needed, and produces or revises selected inventory rows, atom files, selective AIDs, meaningful graph candidates, and project-document impacts. The reviewer receives managed docs, source/evidence, criteria, and operation state, but not the writer's private reasoning conversation.

When the first risk trigger appears, create one risk/contract reviewer and reuse it for later triggered bundles. If a persistent agent is unavailable or its context can no longer support the queue, create one same-role replacement using a compact handoff containing `work-state.json`, evidence index, active bundle, and last verdict. Do not spawn a fresh writer/reviewer pair merely because the queue advanced.

## Bundle Preflight And Review

After each writer and before semantic review, run the plugin validator in docs phase with every atom key expected from that bundle:

```text
python <plugin-root>/scripts/validate_atomic_docs.py --root <target-project-root> --phase docs --expect-atom-key <key> [--expect-atom-key <key> ...]
```

Also check the selected queue's owner references, source basis, and planned atom keys against actual atom keys. Compare planned selected keys, not raw source or document counts. Do not add an active/retired AID lifecycle merely for preflight; report total discovered AIDs and deterministic duplicate/shape failures.

If preflight FAILs, return to the writer without spending a semantic review. After PASS, route semantic, structural-only, and source-locator-only changes through the authoritative change-type table in `reviewer-perspectives.md`; do not maintain a second routing table here.

Record one review input revision. When development and risk reviews both apply, run the persistent reviewers in parallel against that same revision and source basis. An `initial-baseline` still requires development review for every selected domain bundle, not every behavior found in source.

Repeated `--expect-atom-key` scopes this preflight to the active bundle while still checking its AIDs and graph targets against the whole docs set. Unrelated pre-existing structural findings do not block the bundle. Run unscoped docs validation after the accepted queue finishes and before any baseline validation.

After a shared-owner bundle or cross-domain ownership/graph change, run lightweight integration lint for duplicate owners, unresolved shared contracts, expected atom keys, graph targets, and source-basis consistency. This is not a project-wide semantic review.

The reviewer contracts and change-type rerun routing are defined in `reviewer-perspectives.md`. Do not start the next bundle until every reviewer applicable to the active bundle PASSes or a user decision is required.

If later work changes an earlier bundle's boundary, ownership, graph, shared contract, source evidence, risk classification, or decision basis, reopen that bundle and rerun its writer and affected reviewers. Rerun dependent later bundles only when their PASS basis changed.

After a shared-owner bundle PASSes, record its reviewed revision as the owner basis. A dependent writer references that basis and must not redefine the owner or shared contract silently. When source evidence contradicts it, pause the dependent bundle, reopen the owner bundle, and then reopen only dependents whose recorded basis changed.

`confirmation_needed` blocks a bundle only when the unresolved decision prevents trustworthy use of its stated context or blocks an approved implementation/compliance judgment. Other uncertainty may remain as a supported labeled gap in a provisional or partial result.

## Conditional Integration And Baseline Gate

Run the integration or baseline reviewer selected by `reviewer-perspectives.md` after applicable domain reviews PASS. Execute its affected-closure or project-wide scope and any bundle reopen/rerun exactly as that reviewer contract defines; independent multi-domain work does not create another flow-local trigger.

Do not reconcile discovered domains, atom candidates, source evidence, or review results back into durable criteria. Update criteria after writing only when the user approved a durable rule, project exception, or previously unresolved criteria decision.

Create or advance baseline metadata only under the eligibility and carry-forward contract in `source-baseline-and-change-plan.md`. This flow records and executes the selected gate; it does not define a second baseline acceptance rule.

## Progress Guard

Do not use a fixed wall-clock timeout as a quality rule. A source-heavy writer may legitimately take longer. Instead, require every completed writer/reviewer run to report changed artifacts/evidence or a concrete finding.

After two bundles complete, report measured completed/remaining bundle counts and any change in risk or final-review scope. This is informational and does not pause the queue. Do not fabricate a time estimate when the operation lacks reliable elapsed measurements.

If a completed writer produces none of the planned artifact/evidence changes, stop before semantic review and diagnose scope, ownership, tool, or prompt failure. If the same blocking finding fingerprint recurs twice without a changed decision, source basis, or artifact, do not launch the same cycle again. Report the cause, revise the bundle plan or reviewer routing, and move only dependency-independent bundles while the blocker is resolved.
