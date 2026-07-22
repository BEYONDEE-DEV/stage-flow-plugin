# Operation Metrics And Event Journal

## Contents

- [Responsibility](#responsibility)
- [Authoritative Journal](#authoritative-journal)
- [Event Shape And Hash](#event-shape-and-hash)
- [Event Types](#event-types)
- [State Projection](#state-projection)
- [Completion Coverage](#completion-coverage)
- [Final Validation Sequence](#final-validation-sequence)
- [Rollback And Recovery](#rollback-and-recovery)
- [Boundary](#boundary)

## Responsibility

This reference is the normative owner of the v5 request-local event journal, canonical event hash, operation timing/work projection, terminal event order, and local rollback-detection boundary. `docs-generation-flow.md` decides when work runs, `reviewer-perspectives.md` decides which reviews are required, `shared-contract-readiness.md` owns dispatch cutoffs, `semantic-review-closure.md` owns semantic invalidation, and `validation-contract.md` owns deterministic CLI checks. Events observe that flow; they never authorize work or decide review meaning.

## Authoritative Journal

After Goal handoff, create `.stageflow/atomic-docs/requests/<request-id>/operation-events.jsonl` before v5 selection validation. Treat it as the authoritative operation timing/work record. Append exactly one canonical JSON object plus LF per event. Never edit, reorder, remove, or finish an earlier event in place.

Keep `work-state.json.operation_metrics` as the exact reducer projection of the complete valid journal. Do not treat that mutable projection as an independent metrics owner. After an interrupted append, validate the journal first and run the recorder's `sync` action to rebuild the projection; never make the validator repair state.

## Event Shape And Hash

Use only these outer keys in every event:

```text
version, sequence, request_id, event_type, payload, previous_hash, event_hash
```

Set exact `version: "1"`, a positive contiguous `sequence` starting at `1`, and the active lower-kebab-case `request_id`. Set the first `previous_hash` to exactly 64 lowercase `0` characters. Every later `previous_hash` equals the immediately preceding event's `event_hash`.

Calculate `event_hash` as SHA-256 over the ASCII domain separator `stageflow.atomic-docs.operation-event.v1\0` followed by the UTF-8 canonical JSON bytes of the event with `event_hash` omitted. Canonicalize with sorted object keys, compact separators `,` and `:`, and no ASCII escaping. Store lowercase 64-hex hashes.

## Event Types

Append only these event types and exact payloads:

- `operation-started`: `{started_at}`
- `span-started`: `{span_id,kind,scope,attempt_id,basis_revision,started_at}` with optional paired `rerun_of` and `rerun_reason`
- `span-finished`: `{span_id,finished_at,outcome}`
- `operation-finished`: `{finished_at}`

Use RFC 3339 timestamps with `T` and a timezone. Use unique lower-kebab-case span IDs, scope values, and attempt IDs. Record immutable positive `basis_revision`: a `development-review` scoped `selection-readiness` uses the current selection-readiness basis, and every other span uses the semantic-closure basis current when it starts. The recorder rejects a supplied basis that differs from that state owner. Use span kinds `bundle`, `writer`, `development-review`, `risk-review`, `integration-review`, `baseline-review`, or `validation`. Represent a dedicated terminal challenger as `integration-review` with scope `terminal-current-basis`; its span ID equals the challenge review ID. Review spans use only `PASS|FAIL`; bundle/writer work uses `completed|FAIL`, and validation uses `PASS|FAIL`. A rerun includes both optional fields and references an earlier finished span with the same kind and scope; initial work includes neither.

Append each start before its measured work and its finish immediately after the outcome is known. Do not synthesize a finished span as one event, append a finish without its unique start, finish twice, overlap another operation root, or append after `operation-finished`.

## State Projection

Reduce the journal deterministically to the existing exact `operation_metrics.version: "1"` shape: root `status`, `started_at`, optional `finished_at`, and ordered `spans`. Project a started span with its recorded `basis_revision`, its start event's positive `sequence` as immutable `started_sequence`, and `status: active`. Apply its matching finish as `status: finished` with the finish event's greater `finished_sequence`, `finished_at`, and `outcome`; an active span omits all three finish fields. Project operation finish the same way.

Require projected timestamps, span identity/order, rerun linkage, status, and outcomes to match `work-state.json.operation_metrics` exactly. Reject a journal whose chain is valid but whose projection is stale, partially updated, reordered, or rewritten. Keep readiness/dispatch cutoffs pointed at projected span IDs and times.

Every bundle/writer and bundle development/risk span uses an active or retired stable `bundle_id` as scope. Reserve `selection-readiness` so it can never be an active or retired bundle ID; only development readiness uses that scope. Risk review never uses `selection-readiness`. Integration review uses `affected-closure`, `project-wide`, or dedicated-challenge `terminal-current-basis`; baseline review uses `project-wide`. Validation uses its controlled lower-kebab scope, with final validation restricted to `docs|baseline`, and never records `metrics-preterminal|metrics-final`. Receipt-owned review/challenge spans equal their entry's basis; a successful bundle/writer pair shares one attempt ID and basis. A current-basis development/risk review follows the latest successful pair at that same basis; a retained unaffected lower-basis PASS still follows a successful pair at its own basis. Final validation uses the current semantic basis.

## Completion Coverage

Keep the operation root active through selection, bundle work, and final validation. Give every active queue item exactly one successful `bundle` span and one successful `writer` span with one shared attempt ID, one basis, and stable `bundle_id` scope at completion. In queue order, place each bundle's applicable development/risk reviews after its successful pair and finish them before dispatching the next sequential bundle. Derive a work span's readiness epoch from the latest finished receipt-bound readiness PASS before its `started_sequence`; never dispatch while that readiness span is active. Ready dispatch requires its current readiness review ID to be the latest finished readiness PASS. Apply the current queue adjacency and current risk route only to work anchored to that ID, so a late queue reorder is not retroactively imposed on an older epoch. Historical queue/risk order is not fully reconstructible without a preserved readiness-time queue manifest. Place the terminal challenge span after every basis-applicable required bundle review, after any selected final integration/baseline PASS when the challenge is dedicated, and, at the current basis, after the last bundle/writer correction. Challenge attempts follow both basis and non-overlapping journal order. Record every executed readiness, semantic review, challenge, correction, and validation. Each receipt entry points forward to an exact review span, and every finished review PASS span points back to exactly one receipt-bearing readiness, semantic, or dedicated challenge owner with the same kind, scope, and basis; reuse-final-review is the semantic owner's alias, not a second owner. Journal sequence is the sole causal ordering authority; RFC 3339 timestamps remain observations.

Use operation wall-clock as the primary observation and completed review/event/rerun counts as secondary workload observations. Report actual values. Treat `+10–25%` only as a design guardrail, never an ETA, guarantee, validator threshold, readiness signal, or semantic quality rule.

## Final Validation Sequence

For request-bound final docs or baseline validation:

1. Start final `docs|baseline` validation only after every other span is finished. Append `span-started` for that one final `validation` span scoped `docs` or `baseline`; keep the root active, and append no other `span-started` event until that final validation span finishes.
2. Retain inventory/evidence and receipt reports, run final selection with `--require-actions-final`, then run the request-bound unscoped docs/baseline validator. Keep only the root and this latest validation span active.
3. Append `span-finished` with the actual `PASS|FAIL` outcome.
4. After FAIL, keep the root active, append correction events, then start the same-basis retry with `rerun_of` naming the immediately prior failed same-kind/scope span and a non-empty `rerun_reason`. A first attempt at a greater semantic basis omits rerun provenance; a lower basis is a regression and fails.
5. After PASS, run `--phase metrics-preterminal --request-id <request-id>` without recording that self-check. Require every span finished, the latest event to be that final validation finish with PASS, and the root active.
6. Append `operation-finished`, rebuild the exact projection, and run `--phase metrics-final --request-id <request-id>` without recording that self-check. The recorder admits the finish, including pending-event recovery, only when the latest span is the current-basis successful final validation of the required `docs|baseline` scope. Require this to be the journal's terminal event and the projected root finished. Only then retire allowed temporary inputs.

Derive `baseline` versus `docs` only from the exact accepted `operation_profile`: `initial-baseline|baseline-diff-refresh` requires `baseline`, while `change-impact-refresh|targeted|inspection` requires `docs`. A final-gate reviewer or metric event cannot select or upgrade it and cannot downgrade the required phase. Never record `metrics-preterminal` or `metrics-final` spans because either self-record would create an unclosable cycle.

## Rollback And Recovery

Validate the current journal's canonical hash chain and exact projection equality during guarded operation-state rollback checks. Compare the rollback snapshot only with projected-span progression: retain prior span identity and order, preserve finished span facts, allow active spans/root to finish, and append later projected spans. Reject sequence gaps, bad previous/event hashes, a partial rewrite inside the current chain, a projection mismatch, invalid start/finish order, or snapshot projection regression.

The rollback snapshot stores the projection, not historical journal bytes or a trusted hash head. It therefore does not prove a byte-equivalent retained journal prefix, valid-prefix continuity, or whole-request rollback history. Do not require or claim those properties without an external trusted anchor.

Use the helper as `python3 <plugin-root>/scripts/record_atomic_docs_event.py --root <target-project-root> --request-id <request-id> <event-type|sync> ...`. Let it stage one pending canonical event, validate the prospective complete lifecycle and hash chain, atomically append it, then synchronize projection. Treat a present or symlinked pending-event path as fail-closed; recovery validates that pending event against the current journal before appending or recognizing a duplicate. Never append lifecycle-invalid pending data or use `sync` to bless an invalid chain.

## Boundary

The journal is locally tamper-evident only against the journal, projection, and rollback material that remain in the mutable request root. Without a trusted external anchor, it cannot detect adversarial replacement of the entire request with an older internally valid complete chain or valid prefix, and it is not immutable. Do not claim otherwise.

The helper flushes every written file before append/replace completion. POSIX hosts also flush the parent directory. Python has no portable directory `fsync` on Windows, so Windows keeps binary-mode file flushes and atomic replacement but treats parent-directory metadata survival across sudden power loss as best-effort; restart recovery must validate the pending record, journal, and projection before continuing.

The validator checks the current journal's canonical shape/hash chain, sequence, start/finish order, exact reducer projection equality, terminal order, controlled values, and snapshot projected-span progression. It does not authenticate a whole mutable request root or retained historical journal prefix, and it does not judge whether work was necessary, evidence was true, a reviewer was independent, or elapsed time was acceptable.
