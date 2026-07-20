# Operation Metrics

## Contents

- [Responsibility](#responsibility)
- [Versioned Shape](#versioned-shape)
- [Recording Contract](#recording-contract)
- [Completion Coverage](#completion-coverage)
- [Final Validation Sequence](#final-validation-sequence)
- [Snapshot Progression](#snapshot-progression)
- [Boundary](#boundary)

## Responsibility

This reference is the normative owner of Atomic Docs operation timing and rerun-work records. `docs-generation-flow.md` decides when work runs, `reviewer-perspectives.md` decides which reviews are required, `semantic-review-closure.md` owns semantic invalidation, and `validation-contract.md` owns deterministic CLI checks. Metrics observe that flow; they do not authorize work or change review meaning.

## Versioned Shape

New operations use `context_selection.version: "3"` with sibling `operation_metrics.version: "1"`. Version 3 keeps the version-2 candidate, queue, risk-trigger, and `semantic_review_closure.version: "1"` contracts unchanged. Existing version-2, version-1, and unversioned operations continue without migration.

```json
{
  "context_selection": {"version": "3", "candidates": []},
  "operation_metrics": {
    "version": "1",
    "status": "active",
    "started_at": "2026-07-16T09:00:00+09:00",
    "spans": [
      {
        "span_id": "domain-development-1",
        "kind": "development-review",
        "scope": "domain",
        "attempt_id": "domain-attempt-1",
        "status": "finished",
        "started_at": "2026-07-16T09:10:00+09:00",
        "finished_at": "2026-07-16T09:12:00+09:00",
        "outcome": "PASS"
      }
    ]
  }
}
```

Operation and span times use RFC 3339 date-time syntax with `T` and a timezone. Operation status is `active|finished`. A finished operation adds `finished_at`; an active operation omits it. Span status is `active|finished`. A finished span adds `finished_at` and `outcome: PASS|FAIL|completed`; an active span omits both. `started_at` must not follow `finished_at`, and every span stays inside the operation interval when it is closed.

Span IDs are unique lower-kebab-case values. Attempt IDs are lower-kebab-case values that may group the bundle, writer, and reviewers for one recorded attempt. Kinds are `bundle`, `writer`, `development-review`, `risk-review`, `integration-review`, `baseline-review`, or `validation`. `scope` names the domain, affected closure, project-wide review, or validation phase. A rerun adds both `rerun_of` and a concise `rerun_reason`; `rerun_of` references an earlier span with the same kind and scope. Initial work omits both.

## Recording Contract

Create the active operation record after Goal handoff and before version-3 selection validation. Start a span before its measured action and finish it immediately after the result is known. Record writer, applicable reviewer, validation, and correction attempts; do not create prose reports merely to explain metrics.

Use operation wall-clock as the primary observation and completed span/rerun counts as secondary workload observations. Do not turn either into a promised ETA or a validator performance threshold. A missing or slow timestamp never changes semantic reviewer judgment.

Rerun records name the prior span and actual reason selected under `reviewer-perspectives.md`. Metrics do not decide that a correction is risk-neutral and cannot replace an invalidation, reviewer PASS, or finding.

## Completion Coverage

Keep the root active through selection, bundle work, and final validation. Each queue item has one successful `bundle` span and one successful `writer` span with its domain as `scope` and the same `attempt_id`. Multiple queue items in one domain use distinct attempts.

For every current semantic review PASS at the latest closure basis, record a successful reviewer span whose `span_id` equals its `review_id`, with mapped reviewer kind and exact scope. A risk-triggered queued domain has at least one successful `risk-review` span. Older-basis carried or reused PASSes are not falsely reported as newly run, but any review actually executed in this operation is still recorded.

## Final Validation Sequence

For request-bound final docs or baseline validation:

Derive the required phase from the accepted operation profile and current final-gate reviewer. `initial-baseline`, `baseline-diff-refresh`, or a current `baseline`/`project-wide` final PASS requires `baseline`; a metric span cannot downgrade it to `docs`.

1. Start one `validation` span whose scope is `docs` or `baseline`; the operation root remains active.
2. Run the normal request-bound, unscoped docs/baseline validator. During this call, only the root and that final validation span may remain active, and the validation span is the last recorded span.
3. Record `PASS` or `FAIL` and finish the validation span.
4. On `FAIL`, keep the root active, append correction and rerun spans, then start a new validation attempt.
5. On `PASS`, run `--phase metrics-preterminal --request-id <request-id>` without recording that check. It reruns current unscoped docs/closure and applicable baseline structure, then requires every span finished, the latest final validation as the last span with outcome `PASS`, and the root still active.
6. Finish the root and run `--phase metrics-final --request-id <request-id>` without recording that check. It requires no active span, the same last validation `PASS`, and a valid finished operation.

The two terminal checks are read-only self-exclusions. Never record a `validation` span scoped `metrics-preterminal` or `metrics-final`; requiring either check to record itself would create an unclosable validation cycle.

## Snapshot Progression

Operation metrics are append-only through managed-artifact removal and merge rollback snapshots. A later state may append spans and may move an existing `active` span or root to `finished`. It must not remove or reorder earlier span IDs, rewrite identity, kind, scope, attempt, start, rerun reference/reason, reverse a finished state, or change a finished outcome/time.

A version-3 pre-mutation snapshot contains a structurally valid metrics record. Later reviewer, correction, and validation spans may be appended without making the snapshot incomplete. Existing version-2 snapshots have no metrics owner and remain valid under their recorded contract.

## Boundary

The validator checks version, keys, identifiers, controlled values, timestamp ordering, rerun references, allowed active spans for each phase, and append-only snapshot progression. It does not judge whether the measured work was necessary, whether risk meaning changed, whether an agent worked efficiently, or whether elapsed time is acceptable.
