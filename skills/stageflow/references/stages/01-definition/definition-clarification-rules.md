# Definition Clarification And Store Rules

This file owns the clarification loop, implementation-plan deferral, question presentation, pending-question rules, and definition-store hot path. `definition-writing-and-review-rules.md` remains the router and Rule ID checklist source.

## Clarification Loop

After project inspection, assume only definition-level ambiguities remain until the user explicitly stops clarification. Before adding any pending question, classify whether the answer belongs to definition or implementation-plan. Ask breadth-first: start with 큰방향 questions, keep asking 큰방향 questions while 큰방향 ambiguities remain, and move to 주요결정 or 세부확인 questions only when `## Clarification History` or `## Resolved Decisions` records that the previous question scope has been sufficiently covered or that the user agreed to move deeper. Before moving from `큰방향` to `주요결정`, or from `주요결정` to `세부확인`, run a question scope transition review subagent and record PASS in `01-definition/question-scope-transition-review.md`. Purpose is mandatory 큰방향 coverage: if `## Purpose And Intent` is `unknown` or `inferred`, the active pending batch must include at least one purpose-focused 큰방향 question before asking only 주요결정/세부확인 questions.

## Implementation-Plan Deferral Gate

Definition questions must ask only for decisions that can change service meaning: user-visible behavior or outcome, acceptance outcome, product/service policy, domain boundary, user/system flow, data or integration responsibility at the service level, security/privacy/auth/payment responsibility, failure/recovery semantics, regression boundary, purpose, intent, or explicit user constraint.

Defer implementation-plan-only questions instead of asking them in definition. Do not ask the user in definition to choose files, modules, components, functions, classes, hooks, scripts, architecture, libraries, packages, schema/type/interface shape, storage/query implementation, control/data-flow implementation, test commands, validation strategy, work item split, or implementation order unless the answer would change the approved user-visible or service-level meaning. Carry safe technical defaults forward as implementation-plan assumptions, risks, work items, or validation needs.

If a technical uncertainty reveals a missing product/service decision, rewrite it as a concrete definition-level question. For example, ask whether a failure should be visible to the user or retried silently; do not ask which module should implement retry. Ask what success signal the user will accept; do not ask which test command should prove it.

Question scope is based on answer impact:

- `큰방향`: the answer can change request identity, purpose/intent, top-level scope, target user/system surface, desired outcomes, current problem framing, or explicit boundaries. It can revise at the 큰방향 level `User Goal`, `Purpose And Intent`, `Request Profile`, `Desired Outcomes`, `Current Problems`, `Requirements`, or `Boundaries`.
- `주요결정`: the answer stays inside the approved 큰방향 scope but can change major behavior areas, user/system flow, state model, policy groups, integration responsibility, or data responsibility. It can revise `Normal Behavior Model`, `User Flow`, `State And Policy Model`, `Policy Rules`, or `Integration Flow And Data Responsibilities`.
- `세부확인`: the answer stays inside an approved behavior or policy direction and refines acceptance outcome, copy/text, fallback behavior, error handling, recovery semantics, or regression boundary. It can revise `Acceptance Criteria`, specific `Policy Rules`, `Failure And Recovery Behavior`, or `Regression Prevention`; it must not ask for implementation-plan-only test commands or validation strategy.

## User-Facing Question Presentation

When returning a pending clarification batch to the user, render the table rows as understandable decisions rather than raw artifact maintenance. Use this order by default: current context, decision needed, labeled options, recommended option, why the answer matters, and where the answer will be reflected. If showing `큰방향`, `주요결정`, or `세부확인`, include a short plain-language explanation of the label in the user's language.

Each question should make the tradeoff visible. For example, say that a scope answer will update `## Boundaries` and prevent the implementation plan from including adjacent behavior, or that an acceptance outcome answer will update `## Acceptance Criteria` and prevent the plan from assuming the wrong success signal. Do not ask context-free questions such as "Which validation boundary should definition capture?" unless the preceding sentence explains the current request context and why that boundary changes user-visible acceptance rather than test strategy.

## Blocking Question Criteria

Mark an open question as blocking when its answer can change screen flow, authentication, authorization, payment, security, privacy, API responsibility, integration responsibility, service-level data responsibility, copied-project parity, scope, rollout boundary, acceptance outcome, service policy, failure recovery, or regression prevention. Do not mark implementation-plan-only questions as definition blockers; defer them to implementation-plan unless they reveal a missing service-level decision.

Questions outside those criteria may be non-blocking only when the recommended option is safe to carry forward and the impact of deferring the decision is documented.

## Open Question Writing Rules

Each open question must be written as a decision request, not a vague concern. It must include the decision needed, context or conflict, recommended option, alternatives, impact, blocking status, and resolution target. The resolution target names where the answer will be reflected, such as `REQ-002`, `SP-001`, `Boundary`, `Acceptance Criteria`, or `Failure And Recovery Behavior`.

## Open Question Resolution Rules

When the user answers an open question, add a `Resolved Decisions` row with the question ID, answer source, decision, and reflected artifact area. Also update the target requirement, policy rule, constraint, boundary, or acceptance criteria. If a row is updated from the answer, its source must include `User answer to Q-###` or `User answer to CLAR-###`.

## Pending Clarification Store Rules

After every user answer, record the answer into `01-definition/definition-store/`. If an existing active definition request lacks `definition-store/`, create the required store files before processing the answer. Low-risk answer turns stay store-only: update `working-set.json`, `decision-ledger.jsonl`, `trace-index.json`, and `sync-state.json` without reading or writing the full `definition.md`. If the answer can change broad scope, major policy/data responsibility, failure/recovery behavior, integration responsibility, or any already approved meaning, set the appropriate `sync-state.current_gate` and use the registered subagent gate before snapshotting. Then create or maintain the next concrete clarification batch with 1-5 active questions in `definition-store/working-set.json.active_pending_questions`. The active batch must use one `Question Scope` at a time; do not mix higher-scope and lower-scope rows in the same pending batch. If no sync gate is active, the user-facing response must show the full current or next active batch with every labeled option before stopping. The agent must not close definition by judging the request or behavior model `clear enough`, `충분함`, or complete on its own authority. The loop ends only when the user explicitly gives a stop signal such as `구현 계획으로 넘어가기`, `질문 그만`, `충분해`, `stop asking`, `enough`, `proceed`, or `go ahead`; `yes`, `approve`, `approved`, and `승인` are approval expressions, not clarification stop signals.

Before creating a new pending question, check whether the candidate is already answered or safely derivable from store evidence. In store-only turns, use `decision-ledger.jsonl`, `trace-index.json`, `working-set.json` summaries, and any snapshot-time decision index instead of reading `definition.md`. If `definition.md` sections are needed to decide whether a candidate is duplicate or derived, set `sync-state.current_gate` to `targeted-sync-required` or `full-consistency-required` and handle that gate on the next turn. A duplicate or derived pending question must be retired through a normal store decision: add a new `DEC-*`, `source_pending_id`, affected existing `DEC/REQ/SP/DFLOW/INTENT-*` IDs, trace entry, risk level, and `decision_sync` status, then show the next active batch or leave the required sync gate.

Record unanswered active questions canonically in `definition-store/working-set.json.active_pending_questions`. `## Pending Clarifications` in `definition.md` is the synced snapshot for review/approval or the legacy repair source when no store exists. Before a user stop signal exists, the live store batch or synced snapshot must contain 1-5 active question rows. Each active row must include `Question Scope` (`큰방향`, `주요결정`, or `세부확인`), at least two explicit labeled proposal options such as `Option 1:`, `선택지 1:`, or `A:`, a recommended option, user-facing context for why the question is being asked, why the answer matters, the definition area the answer will update, and Status `pending` or `awaiting`. `Transition Option` remains in the table for schema compatibility, but pending rows must write `N/A`; do not place a stop signal there. `Why This Matters` must not be generic; it should say whether the answer changes scope, purpose, behavior, user flow, service-level data responsibility, acceptance outcome, policy, failure recovery, or regression boundary, and what wrong implementation-plan assumption it prevents. `Option 3:` and higher are allowed. `구현 계획으로 넘어가기` is not a proposal option and must not be included inside the `Options` cell or `Transition Option`; it is only a user-authored stop signal recorded in `## Clarification History` under `User Transition Signal`. Do not write a pending question with only one recommendation, an unlabeled suggestion, unexplained internal terminology, prose-only guidance, or an implementation-plan-only decision. After presenting a pending clarification batch, stop and wait for the user. Do not create or complete a Codex goal for definition, run review, approval, next-stage work, or mark the goal blocked merely because the user has not answered yet.

If the user asks a follow-up about a pending option, the main response answers that follow-up first, then restates every still-pending question with its explicit labeled options and stops again. If the follow-up reveals that the pending question is repetitive, already decided, or derivable, record that retire decision in the store and continue to the next valid pending batch instead of ending with only an explanation. During this wait, a question-generation subagent may run in parallel to prepare optional `01-definition/question-backlog.md` candidates, limited to future candidate questions. When the user answers, judge answer impact against the backlog: reuse unaffected candidates as the next pending batch, revise partially affected candidates, or regenerate the backlog when the answer invalidates it.

## Definition Store Hot Path

`01-definition/definition-store/` is required for new Stageflow requests and for any active definition with `Pending Clarifications`. Use it as the default hot path so the agent does not rewrite the full `definition.md` after every answer. `definition-store/working-set.json.active_pending_questions` is the live pending-question source during active clarification. `definition.md` remains the approval-ready snapshot, and `## Pending Clarifications` there is synced from the store or used only as a legacy repair source when the store is missing.

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

Store progress is mandatory during `AWAITING_USER`. If the latest user prompt looks like an answer, an option selection, a duplicate challenge, or a clarification stop signal, the turn must record a valid new `DEC-*` in `decision-ledger.jsonl` with a turn-start `source_pending_id`, affected IDs, matching `trace-index.json`, and matching `sync-state.decision_sync`. If no sync gate is active, the active pending batch must also change before the response stops; simply restating the same batch is not progress. A turn may instead move to `targeted-sync-required`, `full-consistency-required`, or `snapshot-current`, but that gate transition still requires the valid decision evidence. If the latest user prompt is a follow-up, the store may remain unchanged only when the response restates every active pending question and every labeled option from the current store batch. A store with no active pending questions and no recognized sync gate is invalid, even if older clarification history contains a stop-like phrase.

Risk levels:

- `low`: copy, label, or minor acceptance detail. Record in the store, keep `current_gate` on `pending-answer`/`store-only`, and do not read or write full `definition.md`.
- `medium`: service policy, service-level data responsibility, exposed data, failure/recovery, or regression semantics. Set `current_gate: "targeted-sync-required"` and require a targeted-sync subagent before affected snapshot work.
- `high`: reverses a prior decision, changes ownership/scope, or changes auth, payment, privacy, security, or integration responsibility. Set `current_gate: "full-consistency-required"` and require full consistency before continuing to lower-scope questions, review, or approval.

Set `current_gate: "snapshot-current"` only when store decisions are ready to be reflected into `definition.md`. Snapshot sync is required before definition review or approval can rely on `definition.md`. Full consistency is required before `큰방향 -> 주요결정`, before `주요결정 -> 세부확인`, after user stop signals, before definition review/approval, and immediately after high-risk answers.

## Optional Question Backlog

`01-definition/question-backlog.md` is an optional helper artifact prepared by a question-generation subagent in parallel while the main agent waits for the user. It is not a review or approval gate and does not replace `Pending Clarifications`. It should record candidate question ID, question scope, question text, at least two labeled options, affected definition areas, and invalidation triggers. After the user answers, the main agent judges impact and only then promotes unaffected candidates, revises affected candidates, or regenerates the backlog.

## Question Scope Transition Review

`01-definition/question-scope-transition-review.md` is a helper artifact written by a question scope transition review subagent before the main agent shows lower-scope pending questions. It is required when the active `Pending Clarifications` batch contains `주요결정` or `세부확인` rows.

The subagent reviews only definition-stage evidence: current `01-definition/definition.md`, `## Clarification History`, `## Resolved Decisions`, `## Purpose And Intent`, `## Requirements`, `## Boundaries`, current `## Pending Clarifications`, and optional `01-definition/question-backlog.md`. It asks whether higher-scope questions are truly exhausted before the next lower scope is shown.

Required file format:

```md
# Question Scope Transition Review

## Transition Checks

| Transition | Definition Artifact Fingerprint | Evidence Reviewed | Remaining Higher-Scope Questions | Reviewer | Verdict |
| --- | --- | --- | --- | --- | --- |
| 큰방향 -> 주요결정 | sha256:<definition-fingerprint> | Clarification History, Resolved Decisions, Purpose And Intent, Requirements, Boundaries, Pending Clarifications, question-backlog.md if present. | 남은 큰방향 질문 없음: 근거를 한 문장으로 기록한다. | question scope transition review subagent | PASS |
| 주요결정 -> 세부확인 | sha256:<definition-fingerprint> | Clarification History, Resolved Decisions, Normal Behavior Model, User Flow, State And Policy Model, Policy Rules, Pending Clarifications, question-backlog.md if present. | 남은 주요결정 질문 없음: 근거를 한 문장으로 기록한다. | question scope transition review subagent | PASS |
```

If the review finds any remaining higher-scope decision, write `FAIL` and keep the next active pending batch at that higher scope. Do not present lower-scope questions while the required transition row is missing, stale against the current definition fingerprint, or not `PASS`.
