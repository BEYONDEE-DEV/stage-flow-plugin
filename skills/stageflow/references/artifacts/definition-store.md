# Definition Store Artifact Rules

This file owns the definition clarification hot path and optional backlog helper. `definition.md` remains the approval-ready snapshot; `definition-store/working-set.json.active_pending_questions` is the live pending-question source during active clarification.

## Definition Store Hot Path

`01-definition/definition-store/` is required for new requests and for any existing definition that has active `Pending Clarifications`. It is the active clarification hot path while `definition.md` remains the approval-ready snapshot.

Required store files are `working-set.json`, `decision-ledger.jsonl`, `trace-index.json`, and `sync-state.json`. During active clarification, `working-set.json.active_pending_questions` is the canonical visible pending batch; `definition.md` is the approval-ready snapshot. Initial files for a pending batch use active pending IDs, `active_pending_questions`, and scope in `working-set.json`, an empty `decision-ledger.jsonl`, `{"traces":[]}` in `trace-index.json`, and the current `definition.md` fingerprint with `current_gate: "pending-answer"` and `decision_sync: {}` in `sync-state.json`.

`sync-state.current_gate` controls the allowed path:

- `pending-answer`, `store-only`, or `store-only-next-question`: answer/follow-up hot path; do not read or write `definition.md`.
- `targeted-sync-required`: medium-risk answer with a valid medium-risk store decision; registered targeted-sync subagent writes `targeted-sync-plan.json` before affected snapshot work.
- `full-consistency-required`: high-risk, stop, transition, review, or approval path with a valid high-risk store decision; registered full-consistency subagent writes PASS `full-consistency-report.json`.
- `snapshot-current`: main agent may sync `definition.md` from the store and update the current snapshot fingerprint.

Required files when the store exists:

- `working-set.json`: records `active_pending_ids`, canonical `active_pending_questions`, `current_scope`, latest answer summary, next question candidates, and `risk_level`.
- `decision-ledger.jsonl`: append-only JSON lines; each row records `decision_id`, `source_pending_id`, `decision`, `affected_ids`, and `risk_level`.
- `trace-index.json`: records trace entries from `PENDING-*` to `DEC-*` and affected `REQ-*`, `SP-*`, `DFLOW-*`, `DEC-*`, or `INTENT-*` IDs.
- `sync-state.json`: records current `definition.md` snapshot fingerprint, `current_gate`, and `decision_sync` status for each decision.

Initial store files for a new pending clarification batch:

- `working-set.json`: active pending IDs, `active_pending_questions`, current scope, `latest_answer: null`, `next_question_candidate_ids: []`, and `risk_level: "low"`.
- `decision-ledger.jsonl`: empty file until a user answer is recorded.
- `trace-index.json`: `{"traces":[]}`.
- `sync-state.json`: current `definition.md` fingerprint, `current_gate: "pending-answer"`, and `decision_sync: {}`.

Helper subagents may write only files allowed by their registered role and the current gate. `targeted-sync-required` allows a targeted-sync subagent to write `targeted-sync-plan.json`; `full-consistency-required` allows a full-consistency subagent to write PASS/FAIL evidence in `full-consistency-report.json`. The main agent owns risk classification, durable ledger entries, trace updates, snapshot sync, and the next visible pending batch.

Store progress invariant: an `AWAITING_USER` answer-like turn must record a valid store decision before it can stop. A valid decision means a new `DEC-*` ledger row whose `source_pending_id` was active at turn start, non-empty affected IDs, a matching `trace-index.json` entry, and a matching `sync-state.decision_sync` entry. If no sync gate is active, that valid decision must also change the active pending batch before the response stops. If the turn moves to `targeted-sync-required`, `full-consistency-required`, or `snapshot-current`, the same valid decision evidence is still required. Follow-up turns may leave the store unchanged only if the response shows the full current pending batch and all labeled options. A store with no active pending questions and no recognized sync gate is invalid; older stop-like text in `Clarification History` does not make that state valid.

If the latest user prompt looks like an answer, an option selection, a duplicate challenge, or a clarification stop signal, the turn must record a valid new `DEC-*` in `decision-ledger.jsonl` with a turn-start `source_pending_id`, affected IDs, matching `trace-index.json`, and matching `sync-state.decision_sync`. If no sync gate is active, the active pending batch must also change before the response stops; simply restating the same batch is not progress. A turn may instead move to `targeted-sync-required`, `full-consistency-required`, or `snapshot-current`, but that gate transition still requires the valid decision evidence. If the latest user prompt is a follow-up, the store may remain unchanged only when the response restates every active pending question and every labeled option from the current store batch.

Duplicate or derived pending questions retire through the same store shape as user answers: append a `DEC-*` row with `source_pending_id`, affected existing `DEC/REQ/SP/DFLOW/INTENT-*` IDs, and `risk_level`; add a matching `trace-index.json` trace; and update `sync-state.decision_sync` with the risk and sync status before replacing the visible batch or leaving a required sync gate.

Risk levels:

- `low`: copy, label, or minor acceptance detail. Record in the store, keep `current_gate` on `pending-answer`/`store-only`, and do not read or write full `definition.md`.
- `medium`: service policy, service-level data responsibility, exposed data, failure/recovery, or regression semantics. Set `current_gate: "targeted-sync-required"` and require a targeted-sync subagent before affected snapshot work.
- `high`: reverses a prior decision, changes ownership/scope, or changes auth, payment, privacy, security, or integration responsibility. Set `current_gate: "full-consistency-required"` and require full consistency before continuing to lower-scope questions, review, or approval.

Set `current_gate: "snapshot-current"` only when store decisions are ready to be reflected into `definition.md`. Snapshot sync is required before definition review or approval can rely on `definition.md`. Full consistency is required before `큰방향 -> 주요결정`, before `주요결정 -> 세부확인`, after user stop signals, before definition review/approval, and immediately after high-risk answers.

Before review or approval, `sync-state.json` must show the current `definition.md` fingerprint and no unsynced medium/high-risk decisions.

## Optional Definition Question Backlog

Definition artifacts include `## Purpose And Intent` as required first-class purpose coverage; confidence must be `confirmed`, `inferred`, or `unknown`, and inferred/unknown purpose requires a purpose-focused 큰방향 pending question.

`01-definition/question-backlog.md` may be created by a question-generation subagent in parallel while definition is waiting for user clarification. It is a helper artifact only: it does not replace `definition.md`, `review/final.md`, `approval.md`, or the current `Pending Clarifications`, and it is not required for validation. Use it to record candidate next questions, question scope (`큰방향`, `주요결정`, `세부확인`), labeled options, affected definition areas, and invalidation triggers before the main agent decides whether to promote, revise, or discard them after the user answer.
