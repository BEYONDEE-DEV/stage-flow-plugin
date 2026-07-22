# Shared Contract Readiness

## Contents

- [Responsibility](#responsibility)
- [Version 5 Boundary](#version-5-boundary)
- [Local And Shared Risk Routes](#local-and-shared-risk-routes)
- [Bounded Shared Contract Closure](#bounded-shared-contract-closure)
- [Selected Contract Binding Traces](#selected-contract-binding-traces)
- [Retirement And Rollback Identity](#retirement-and-rollback-identity)
- [Pre-Writer Readiness Review](#pre-writer-readiness-review)
- [Late Discovery](#late-discovery)
- [First-Attempt Failure Diagnosis](#first-attempt-failure-diagnosis)
- [Final Revalidation](#final-revalidation)
- [Validation Boundary](#validation-boundary)

## Responsibility

This reference is the normative owner of version-5 local/shared risk routing, selected contract-binding traces, bounded shared-contract and retirement state, stable bundle identity during rollback, pre-writer readiness review, late shared-contract discovery, and adaptive semantic-FAIL dispatch control. `service-logic-coverage.md` owns candidate admission and semantic risk signals, `semantic-review-proof.md` owns receipts and reviewer identity, `reviewer-perspectives.md` owns verdict quality, `semantic-review-closure.md` owns post-PASS invalidation, `operation-metrics.md` owns the event journal, and `validation-contract.md` owns deterministic checks.

## Version 5 Boundary

After Goal handoff, every executable Atomic Docs operation uses exact `context_selection.version: "5"`. Version 5 includes candidate selection, receipt-bound semantic closure, event-journal projection, removal/merge, rollback, final validation, and these top-level owners in `work-state.json`:

- `shared_contracts`
- `selection_readiness`
- `late_shared_contract_discoveries`
- `semantic_fail_diagnostics`
- `dispatch_control`
- `selection_retirements`
- `contract_binding_traces`
- `created_aids`
- `semantic_challenge`
- `reviewer_handoffs`

Give every `risk_triggers` entry a unique lower-kebab-case `risk_id` and `route: local|shared-contract`; give every `bundle_queue` entry `bundle_id` plus `depends_on_contract_ids`. A `shared-contract` route names `shared_contract_id`; a `local` route omits it. Initialize exact `selection_retirements: {"version":"1","retired_bundles":[],"retired_contracts":[]}`, `created_aids: []`, challenge, and handoff owners before writing. A pre-Goal bootstrap request may resume without selection. After Goal handoff, reject a missing, non-string, v1-v4, future, or unknown marker and direct the agent to a new v5 request under the existing approval and Goal gates. Never mutate, resume, migrate, backfill, or dual-read rejected state.

Bundle-scoped development/risk review PASSes and required reviews use stable `bundle_id` as `scope`, and semantic invalidation `affected_bundles` contains those bundle IDs. This preserves affected-only review when one domain has several shards. Readiness itself keeps the fixed `selection-readiness` scope.

## Local And Shared Risk Routes

Classify each selected risk trigger before readiness review:

- `local`: the concern can be judged inside one candidate/bundle without reopening a different owner bundle
- `shared-contract`: changing the contract owner or meaning could invalidate one or more direct consumer bundles

Risk severity, sensitive source, destructive naming, transaction detail, or a large reference count does not by itself make a shared contract. Keep ordinary authorization branches, payload fields, transaction order, retry mechanics, projection fields, incidental defects, and other source-local detail on the `local` route unless they depend on one of the bounded shared kinds below.

Every shared route resolves to one declared contract. Every declared direct consumer has a candidate-linked shared route to that contract. A contract with no routed owner/consumer, an unknown contract reference, or a local route carrying `shared_contract_id` is invalid.

## Bounded Shared Contract Closure

Create `shared_contracts` only for an actual high-fan-out contract of kind `permission`, `shared-identifier`, `money-entitlement`, `final-projection`, or `integration`. High-fan-out means the contract has an owner and at least one direct consumer in a different bundle whose review basis would change when that owner or contract meaning changes. Do not promote every risk candidate or every aggregate owner.

Each contract records a unique lower-kebab-case `contract_id`, one allowed `kind`, `owner_candidate_id`, `owner_atom_key`, non-empty `direct_consumer_candidate_ids`, `evidence_routes`, `owner_bundle_id`, and `consumer_bundle_ids`. Each evidence route is a non-empty single-line string resolving to the operation evidence needed to judge owner/enforcement or direct consumption. Cover the owner and every declared direct consumer. The owner and consumers must be selected `write|merge` candidates with resolvable output keys, and the bundle IDs must resolve to their actual queue items.

Each queue item has a unique lower-kebab-case `bundle_id`. The owner bundle precedes every direct consumer bundle. Each consumer bundle lists the contract in `depends_on_contract_ids`; unrelated bundles do not acquire the dependency. Reference count may prompt semantic review but never proves ownership or completeness.

## Selected Contract Binding Traces

Create top-level `contract_binding_traces` with exactly one trace for every selected `risk_triggers.risk_id`. Do not create traces for unselected source behavior or use them as a general API/security inventory. Use this exact common shape:

```text
trace_id, risk_id, kind, owner_candidate_id, owner_atom_key, owner_contract,
authority_status, authority_revision, authority_locator, authority_content_sha256,
applicability_status, applicability_basis, consumer_candidate_id,
consumer_atom_key, consumer_bundle_id, resource_or_identifier,
implementation_locator, implementation_content_sha256, review_id, verdict
[, observed_conflict]
```

Use `kind: contract|permission-privacy`, `authority_status: verified|unresolved`, `applicability_status: verified|unresolved`, and `verdict: matches_confirmed_intent|bug_or_regression|confirmation_needed`. Omit `observed_conflict` when no conflict has been established; when present it is an exact boolean recording whether the reviewer actually observed the implementation contradicting the bound authoritative/applicable contract. Require lower-kebab-case unique trace/risk IDs, resolvable selected owner and consumer candidates/atoms/bundles, an authoritative revision and locator content digest, an observed implementation locator content digest, and a concrete resource or canonical identifier. During pre-writer or intermediate selection, `review_id` may resolve to the current receipt-bound `selection_readiness` PASS at the trace basis; this avoids requiring a semantic bundle PASS before any writer can run. Once the applicable semantic review exists, promote the trace to that current receipt-bound `semantic_review_closure.review_passes` PASS. Final selection with `--require-actions-final`, request-bound docs/baseline, and terminal checks require that semantic-closure promotion and reject a readiness-only trace. A shared route also resolves the same `shared_contract_id`; a local trace may name its bounded owner contract without promoting it to shared-contract state.

For `kind: permission-privacy`, add exact `permission_privacy` fields `principal`, `authorized_object_or_data`, `loaded_object`, and `projection_or_use`. Require all four as non-empty observed relationships. Omit `permission_privacy` for `kind: contract`. Make the reviewer compare the authorized resource/data with the object actually loaded and the projection/use; never normalize cross-resource sensitive-data exposure into a healthy Rule.

Use `bug_or_regression` for an observed conflict only when `observed_conflict: true` and both authority and target applicability are `verified`. If either is unresolved, use `confirmation_needed`; never let a missing consumer-local restatement override verified authoritative/applicable owner evidence. Verified status alone does not prove a conflict and may coexist with `confirmation_needed` for a different unresolved judgment basis. `change-judgment-policy.md` owns the label precedence, while this trace owns the authority/applicability/consumer evidence binding.

## Retirement And Rollback Identity

`bundle_queue` and `shared_contracts` contain only active selection. When a version-5 `write` becomes `drop`, a bundle disappears, or a shared contract is retired, preserve its prior identity in `selection_retirements`. A `retired_bundles` row copies the active queue entry's `bundle_id`, `domain`, `expected_atom_keys`, and `depends_on_contract_ids`, then adds positive `retired_basis_revision` and a non-empty single-line `reason`. A `retired_contracts` row copies all eight active contract fields—`contract_id`, `kind`, `owner_candidate_id`, `owner_atom_key`, `direct_consumer_candidate_ids`, `evidence_routes`, `owner_bundle_id`, and `consumer_bundle_ids`—and adds the same retirement metadata.

Retirement rows are immutable append-only history, ordered by nondecreasing `retired_basis_revision` no later than the current readiness basis. Active and retired IDs are disjoint, and an ID is never reused. From a rollback snapshot to current state, each newly retired row has `snapshot readiness basis < retired_basis_revision <= current readiness basis`, equals one exact snapshot-active bundle or contract after excluding retirement metadata, and is absent from current active state; retired contract owner/consumer bundle IDs resolve through active plus retired bundles. Snapshot normalization may remove only a dependency or `shared-contract` risk route that directly names the newly retired contract; every participant's local route or route to another contract remains exact. Current risk routing, binding traces, dependencies, owner/consumer closure, queue order, and a new/open discovery resolve active IDs only. Historical version-5 development/risk scopes, invalidation `affected_bundles`, and diagnostic/resolved-discovery references resolve IDs across active plus retired history, so a correction never erases their meaning.

Couple retirement to the pre-mutation snapshot without broadening impact. For each newly retired bundle, consider every prior `current|stale` development/risk PASS scoped to its stable bundle ID. Before mutation, the snapshot must show each retirement-affected PASS as `stale` and contain an open invalidation whose `affected_bundles` includes that exact bundle, whose `stale_review_ids` includes every such PASS ID, whose `required_reviews` contains the exact `(reviewer_role, bundle_id)` pair for every stale PASS, and whose `opened_revision == retired_basis_revision`. This forces a same-role/scope rerun before resolution. Retirement necessarily changes the retired bundle's identity basis, so every pre-retirement development and risk PASS in that stable scope is retirement-affected and must become stale; no current pre-retirement risk PASS in that scope is reusable. Risk-neutral reuse applies only outside the retirement-affected stable scope, or to a non-retirement correction whose risk basis is independently unchanged. If the bundle has no prior semantic PASS, retirement needs no invalidation. For a newly retired contract, every owner/consumer stable bundle scope still live at retirement necessarily changes its contract route, dependency, or identity basis; apply the same rule to every prior development/risk PASS in each such scope. A live scope without a prior PASS needs no invalidation, and a scope retired strictly before the contract is excluded by the temporal rule below. A bundle and related contract retired by one correction share one `retired_basis_revision`.

Every current version-5 selection also revalidates the entire retirement history, not only newly appended snapshot transitions. For a retirement at revision `T`, inspect each development/risk PASS in its stable bundle scope with `basis_revision < T`. Exclude a corrected PASS with `basis_revision >= T`, and exclude a pre-`T` PASS only when an earlier invalidation with `resolved_revision < T` already superseded it. Every other pre-`T` PASS, regardless of current status, has one matching `status: open|resolved` invalidation with `opened_revision == T`, the exact bundle in `affected_bundles`, its ID in `stale_review_ids`, and its exact `(reviewer_role, bundle_id)` in `required_reviews`. For a contract retirement, apply this temporal rule to its owner/consumer stable bundle scopes that were still live at `T`; omit a bundle scope retired strictly before the contract's `T`.

For a guarded mutation, map each guarded managed path through its pre-mutation snapshot action/artifact `atom_key` to the snapshot queue entry whose `expected_atom_keys` contains that key. Current development and risk PASSes scoped to that exact stable `bundle_id` are pre-mutation invalidation targets, and the existing final-gate guard still applies; a same-domain shard with another bundle ID remains current. If an approved-existing source path's `atom_key` is absent from the snapshot queue, do not infer a bundle from its domain or candidate—apply only the existing final-gate protection.

## Pre-Writer Readiness Review

Before creating or dispatching the first writer, create the operation's persistent development reviewer and run one selection-readiness review, then run request-bound structural selection validation. This is the same reviewer later used for domain development-quality review, not a fourth reviewer role.

`selection_readiness` has `version: "1"`, a positive `basis_revision`, and append-only `reviews`. Each review records unique `review_id`, `reviewer_role: development`, `reviewer_agent_id`, matching `basis_revision`, exact `verdict: PASS`, `status: current|stale|superseded`, and the embedded `receipt` from `semantic-review-proof.md`. The latest current review's `reviewer_agent_id` equals the current `persistent_agent_ids.reviewer`; each historical stale/superseded review equals the persistent reviewer active at its basis under `reviewer_handoffs`. When `dispatch_control.status` is `ready`, exactly one current receipt-bound PASS matches the readiness basis; a paused operation may have none. Append matching `span-started` and `span-finished` journal events whose projected span has outcome `PASS`, `kind: development-review`, `scope: selection-readiness`, and `span_id` equal to `review_id`. Finish that span before the first writer span starts.

The reviewer independently checks candidate economy, every selected risk trigger's local/shared disposition, bounded-kind admission, owner/Atom/evidence/direct-consumer closure, and owner-before-consumer ordering. PASS means this declared selection is ready to write; it does not claim every source behavior, API, aggregate, or possible consumer was inventoried.

Stop source discovery when the declared selected claims and their bounded contract routes can be judged reliably. While verifying them, escalate a directly evidenced omitted high-impact shared contract as a prepass defect. Do not demand new managed-doc detail for ordinary fields, branches, transaction steps, projection fields, failures, or attack paths; apply `drop`, `remove`, or `generalize` under the existing candidate/reviewer contracts.

## Late Discovery

When a directly evidenced shared contract appears after the initial prepass, stop new bundle dispatch and append a `late_shared_contract_discoveries` record before changing selection state. Each record has `discovery_id`, `contract_id`, `stage: pre-readiness|post-readiness`, positive `basis_revision`, non-empty `affected_bundle_ids`, and `status: open|resolved`. Every post-readiness discovery has exactly one matching `late-shared-contract` dispatch episode with the same status and its discovery ID in `trigger_ids`. Update the bounded prepass, evidence routes, risk routes, dependencies, and queue order, then rerun structural selection validation and the same persistent development review.

A `pre-readiness` discovery is recorded already `resolved` and needs no stale-readiness or semantic-invalidation fields. A `post-readiness` discovery always records `stale_readiness_review_id` and `semantic_invalidation_ids`. When readiness PASSed but no affected bundle has a semantic PASS yet, record exact `semantic_invalidation_ids: []`; there is no prior bundle PASS to invalidate. Once any affected bundle semantic PASS exists, the list is non-empty and those invalidations must open before editing. When resolved, add `resolved_revision` and `resolution_readiness_review_id`. Stale and rerun only the owner and direct consumer bundles whose recorded basis changed, using their stable bundle IDs; carry unrelated PASSes forward. Resume only after the discovery is resolved, structural validation PASSes, readiness returns PASS on the current basis, and every required affected review/invalidation is closed.

## First-Attempt Failure Diagnosis

Append one `semantic_fail_diagnostics` entry for each first-attempt development, risk, integration, or baseline semantic review that FAILs. Record unique `diagnostic_id`, the failed `review_span_id`, `first_attempt: true`, positive `basis_revision`, one `root_category`, and non-empty `candidate_ids` and/or `contract_ids`. Categories are `candidate-admission`, `contract-routing`, `owner-evidence`, `consumer-closure`, `evidence-depth`, and `selected-claim-fidelity`. Keep the concise finding in the normal reviewer report; this entry exists only to detect a shared execution root.

Unrelated first-attempt FAILs continue through normal affected correction. Pause new dispatch only when consecutive first-attempt FAIL entries share the same category and at least one candidate or contract root. `dispatch_control` has `version: "1"`, `status: ready|paused`, and append-only `episodes`. Each episode records unique `episode_id`, `cause: late-shared-contract|shared-root-semantic-fail`, non-empty `trigger_ids`, positive `basis_revision`, and `status: open|resolved`; every resolved episode also records non-empty `diagnosis`, `action`, `resume_basis_revision`, and `readiness_review_id`. A resolved shared-root basis is strictly greater than every trigger diagnostic basis. Preserve every episode and its opening identity.

A post-readiness `late-shared-contract` episode additionally records immutable `pause_after_span_id`, positive `pause_after_sequence`, and RFC3339 `paused_at`. The ID resolves to an existing finished projected span and the sequence equals that span's `finished_sequence`; this journal sequence is the causal cutoff, while `finished_at <= paused_at` is only an observation check. While open, reject every active or finished `bundle`/`writer` whose `started_sequence` is after the cutoff, even when timestamps or list placement suggest otherwise. When resolved, its matching readiness metric has `span_id` equal to `readiness_review_id`, starts strictly after the cutoff, and no bundle/writer starts between cutoff and that readiness PASS finish; dispatch resumes only after the PASS and episode resolution. A shared-root episode does not add these late-contract fields: it keeps the no-intervening-dispatch rule from its latest triggering FAIL and resumes only at its strictly higher-basis readiness PASS; until then, do not start a new `bundle` or `writer` dispatch.

Never pause, fail, or resume because of raw FAIL count, bundle count, elapsed time, wall-clock duration, or a promised performance target. Metrics may report actual work but do not choose the diagnostic root or dispatch status.

## Final Revalidation

Promote every binding trace from any pre-writer readiness review to its current receipt-bound semantic-closure PASS before final validation. Before request-bound final docs/baseline validation, rerun full selection with `--require-actions-final`. The request-bound final docs/baseline call and both `metrics-preterminal` and `metrics-final` checks then revalidate current version-5 local/shared routing, promoted binding traces, contract/queue dependencies, immutable retirement history and historical references, receipt-bound readiness, blind challenge, dispatch cutoffs, and `dispatch_control.status: ready` with no open episode. Keep request-local inventory, evidence, receipts, and findings-only reports through these checks; retire only allowed temporary inputs after terminal PASS.

## Validation Boundary

The validator checks versions, controlled values, active/retired IDs and append-only progression, rollback bundle mapping, required receipt-bound readiness, trace completeness/references, reviewer identity reuse, owner-before-consumer ordering, journal-projected pause/resume ordering, and affected-state links. It does not decide whether a source concern is truly local, authority/applicability is semantically valid, every real consumer was found, a permission/resource chain is correct, two findings share a root cause, or a reviewer should PASS. Those remain reviewer judgments.
