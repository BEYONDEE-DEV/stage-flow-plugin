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

New operations use `context_selection.version: "4"` with sibling `operation_metrics.version: "1"`. Version 4 keeps the version-3 metrics and `semantic_review_closure.version: "1"` contracts unchanged and adds readiness state through `shared-contract-readiness.md`. Existing version-3, version-2, version-1, and unversioned operations continue without migration.

```json
{
  "context_selection": {"version": "4", "candidates": []},
  "operation_metrics": {
    "version": "1",
    "status": "active",
    "started_at": "2026-07-16T09:00:00+09:00",
    "spans": [
      {
        "span_id": "fulfillment-development-1",
        "kind": "development-review",
        "scope": "fulfillment-bundle",
        "attempt_id": "fulfillment-attempt-1",
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

Span IDs are unique lower-kebab-case values. Attempt IDs are lower-kebab-case values that may group the bundle, writer, and reviewers for one recorded attempt. Kinds are `bundle`, `writer`, `development-review`, `risk-review`, `integration-review`, `baseline-review`, or `validation`. In version 4, every `development-review` and `risk-review` span, whether active or finished and whether outcome is `PASS` or `FAIL`, uses an active or retired stable `bundle_id` as `scope`. The only non-bundle scope is `selection-readiness` on a `development-review` span; a `risk-review` span never uses `selection-readiness`. A first-attempt FAIL span referenced by `semantic_fail_diagnostics` obeys the same rule. Version 3 retains domain-scoped reviewer spans, while affected closure, project-wide, and validation use their controlled scopes. A rerun adds both `rerun_of` and a concise `rerun_reason`; `rerun_of` references an earlier span with the same kind and scope. Initial work omits both.

## Recording Contract

Create the active operation record after Goal handoff and before version-4 selection validation. Start a span before its measured action and finish it immediately after the result is known. Record writer, applicable reviewer, validation, and correction attempts; do not create prose reports merely to explain metrics. Record the version-4 readiness PASS as the existing `development-review` kind with scope `selection-readiness`; do not create a new role or metric kind. A post-readiness late-contract episode records immutable `pause_after_span_id` pointing to an existing finished span in this append-only sequence plus immutable RFC3339 `paused_at`; the cutoff span has `finished_at <= paused_at`.

Use operation wall-clock as the primary observation and completed span/rerun counts as secondary workload observations. Do not turn either into a promised ETA or a validator performance threshold. A missing or slow timestamp never changes semantic reviewer judgment.

Rerun records name the prior span and actual reason selected under `reviewer-perspectives.md`. Metrics do not decide that a correction is risk-neutral and cannot replace an invalidation, reviewer PASS, or finding.

## Completion Coverage

Keep the root active through selection, bundle work, and final validation. Each queue item has one successful `bundle` span and one successful `writer` span with its domain as `scope` and the same `attempt_id`. Multiple queue items in one domain use distinct attempts.

For every current semantic review PASS at the latest closure basis, record a successful reviewer span whose `span_id` equals its `review_id`, with mapped reviewer kind and exact scope. A version-4 risk-triggered bundle ID has a successful `risk-review` span; version 3 retains domain coverage. Older-basis carried or reused PASSes are not falsely reported as newly run, but any review actually executed in this operation is still recorded.

## Final Validation Sequence

For request-bound final docs or baseline validation:

Derive the required phase from the accepted operation profile and current final-gate reviewer. `initial-baseline`, `baseline-diff-refresh`, or a current `baseline`/`project-wide` final PASS requires `baseline`; a metric span cannot downgrade it to `docs`.

1. Start one `validation` span whose scope is `docs` or `baseline`; the operation root remains active.
2. For version 4, retain inventory/evidence, run final selection with `--require-actions-final`, then run the request-bound unscoped docs/baseline validator; that call revalidates current routing, readiness, and ready dispatch. During this call, only the root and that final validation span may remain active, with the latest final validation as the last span.
3. Record `PASS` or `FAIL` and finish the validation span.
4. On `FAIL`, keep the root active, append correction and rerun spans, then start a new validation attempt.
5. On `PASS`, run `--phase metrics-preterminal --request-id <request-id>` without recording that check. It reruns current unscoped docs/closure, applicable baseline structure, and full version-4 selection/readiness/dispatch/retirement history, then requires every span finished, the latest final validation as the last span with outcome `PASS`, and the root active.
6. Finish the root and run `--phase metrics-final --request-id <request-id>` without recording that check. It reruns the same version-4 selection/history gate, requires no active span, the same last validation `PASS`, and a valid finished operation. Only then retire version-4 inventory/evidence.

The two terminal checks are read-only self-exclusions. Never record a `validation` span scoped `metrics-preterminal` or `metrics-final`; requiring either check to record itself would create an unclosable validation cycle. After a shared-root trigger FAIL, no later `bundle` or `writer` span may start until a readiness PASS finishes at a strictly higher changed basis and resolves the episode. For a post-readiness late-contract episode, no active or finished bundle/writer span may appear after `pause_after_span_id` while open or between that cutoff and the later matching readiness span while resolved. Independently reject any such span that began after `paused_at` before resume readiness, even if record order was changed to move the cutoff behind it; shared-root behavior is unchanged.

## Snapshot Progression

Operation metrics are append-only through managed-artifact removal and merge rollback snapshots. A later state may append spans and may move an existing `active` span or root to `finished`. It must not remove or reorder earlier span IDs, rewrite identity, kind, scope, attempt, start, rerun reference/reason, reverse a finished state, or change a finished outcome/time.

A version-4 or version-3 pre-mutation snapshot contains a structurally valid metrics record. Later reviewer, correction, and validation spans may be appended without making the snapshot incomplete. Existing version-2 snapshots have no metrics owner and remain valid under their recorded contract.

## Boundary

The validator checks version, keys, identifiers, controlled values, timestamp ordering, rerun references, allowed active spans for each phase, and append-only snapshot progression. It does not judge whether the measured work was necessary, whether risk meaning changed, whether an agent worked efficiently, or whether elapsed time is acceptable.
