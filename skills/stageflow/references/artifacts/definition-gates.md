# Definition Gate Artifacts

This file owns definition-only gate artifacts that sit around clarification, review, and approval. Store hot-path files live in `definition-store.md`.

## Definition Question Scope Transition Review

`01-definition/question-scope-transition-review.md` is written by a question scope transition review subagent before lower-scope pending questions are shown. It is required when the active `Pending Clarifications` batch contains `주요결정` or `세부확인`. The file records whether higher-scope questions are truly exhausted, cites the current `definition.md` fingerprint, and uses `PASS` only when the subagent finds no remaining higher-scope questions.

Required table:

```md
# Question Scope Transition Review

## Transition Checks

| Transition | Definition Artifact Fingerprint | Evidence Reviewed | Remaining Higher-Scope Questions | Reviewer | Verdict |
| --- | --- | --- | --- | --- | --- |
| 큰방향 -> 주요결정 | sha256:<definition-fingerprint> | Reviewed definition-stage evidence. | 남은 큰방향 질문 없음: 근거를 기록한다. | question scope transition review subagent | PASS |
```

The subagent reviews only definition-stage evidence: current `01-definition/definition.md`, `## Clarification History`, `## Resolved Decisions`, `## Purpose And Intent`, `## Requirements`, `## Boundaries`, current `## Pending Clarifications`, and optional `01-definition/question-backlog.md`. It asks whether higher-scope questions are truly exhausted before the next lower scope is shown.

If the review finds any remaining higher-scope decision, write `FAIL` and keep the next active pending batch at that higher scope. Do not present lower-scope questions while the required transition row is missing, stale against the current definition fingerprint, or not `PASS`.

## Definition Transition Risk Gate

After the user gives a definition stop signal such as `구현 계획으로 넘어가기`, Stageflow must run a narrow transition-risk audit before definition review/approval. This is the only definition-stage `create_goal` exception, and it does not create `01-definition/goal.md`. It records `01-definition/transition-risk-goal.md` and produces `01-definition/transition-risk.md`. This audit is about goal-achievement decision readiness: before planning, ask whether the user goal can succeed without another definition-level decision. Generated risk cases are candidates only and must identify a missing required decision, a conflict between required decisions, or an ambiguity that can change how the goal is achieved. Before writing any row, compare the candidate against `Clarification History`, `Resolved Decisions`, `Intent Fidelity`, `Requirements`, `Acceptance Criteria`, `Policy Rules`, and `Boundaries`. Already-decided requirements, intent-fidelity rows, boundaries, policy rules, and already answered and reflected decisions are not risk cases; carry them into implementation-plan coverage or constraints instead of listing them as `accepted-risk`. Reflect true missing decisions into `definition.md` only after user confirmation, or record unresolved material decision risk as out-of-scope, accepted residual risk, duplicate generated risk, or not applicable.

`transition-risk-goal.md` records:

```md
# Transition Risk Goal

Stage: definition

Purpose: transition-risk

Artifact Path: `01-definition/transition-risk.md`

Definition Artifact Fingerprint: sha256:<definition-fingerprint>

## Goal Invocation

Tool: create_goal

Invocation recorded: yes

Invocation result: goal created

## Goal Tool Status

Goal created: yes

Goal status: completed
```

`transition-risk.md` contains `## Risk Generation Basis`, `## Generated Risk Cases`, `## Suggested Definition Updates`, `## User Confirmation`, and `## Final Disposition`. `Generated Risk Cases` must use columns `ID`, `Category`, `Risk Case`, `Affected Definition Area`, `Definition Coverage`, `Prior Answer Check`, `Suggested Handling`, `User Confirmation`, and `Disposition`. `Definition Coverage` must be `uncovered`, `conflicting`, `ambiguous`, or `not-applicable`: `uncovered` means a goal-critical decision is missing from definition, `conflicting` means goal-critical decisions conflict inside definition, `ambiguous` means a goal-critical decision can be interpreted multiple ways, and `not-applicable` means the audit found no material decision gap. `Prior Answer Check` must be `not-answered`, `answered-not-reflected`, `answered-conflicting`, or `not-applicable`: `not-answered` means no prior user answer or resolved decision covers the candidate, `answered-not-reflected` means the user answered but definition failed to carry it forward, `answered-conflicting` means a prior answer exists but the current definition conflicts with it, and `not-applicable` is only for the explicit no-material-risk row. Already answered and reflected decisions are not risk cases. Material risks cannot use `not-applicable` for either `Definition Coverage` or `Prior Answer Check`. If `Prior Answer Check` is `answered-not-reflected` or `answered-conflicting`, the disposition must be `apply-to-definition` or `ask-follow-up`. For every material risk, `Risk Case` explains the risk and `Suggested Handling` must contain at least two labeled resolution options such as `Option 1:` and `Option 2:` so the user can answer it like a clarification question. Allowed categories are `scope`, `acceptance`, `policy-data`, `failure-recovery`, `regression`, `integration`, `user-flow`, `security-privacy`, and `implementation-readiness`. Allowed dispositions are `apply-to-definition`, `ask-follow-up`, `out-of-scope`, `accepted-risk`, `duplicate`, and `not-applicable`; `accepted-risk` requires explicit user acceptance of a real residual risk, not a statement that the item was already decided.

Generated risk cases are not automatically requirements, and they are not a place to restate decisions that are already answered by the user and settled in `definition.md`. For each candidate, ask two questions: `이 목표를 달성하려면 이 결정이 definition 단계에서 이미 정해져 있어야 하는가?` and `그 결정이 현재 definition에 없거나, 충돌하거나, 애매한가?` A risk case must expose a required decision the definition does not currently settle, a required decision that conflicts with another definition decision, or a required decision that is ambiguous enough to let implementation planning choose the wrong path. Already-decided requirements, boundaries, policy rules, and already answered/reflected user answers must move to implementation-plan coverage or constraints instead. If an approved requirement or policy only lacks its derived `DFLOW-*` inventory row, repair `## Approved Flow Inventory` instead of asking the user to reconfirm the same decision.

When a material risk case is presented to the user, write it in the same user-answerable form as clarification questions: explain the risk in plain language, name the affected definition area, explain why it can block the goal, and put at least two labeled resolution options in `Suggested Handling` such as `Option 1:` and `Option 2:`. Do not use a single recommendation, an unlabeled sentence, or implementation-only TODOs as the handling. If the user confirms `apply-to-definition`, reflect the update in `## Requirements`, `## Acceptance Criteria`, `## Policy Rules`, `## Boundaries`, `## Failure And Recovery Behavior`, or `## Regression Prevention`. If a case needs more input, use `ask-follow-up` and restore active `Pending Clarifications`. If the user explicitly accepts a true residual risk, use `accepted-risk`; do not use `accepted-risk` to mean "already confirmed".
