# Stageflow Artifact Format

Stageflow uses one request folder with three fixed stage folders. This file is the request-level artifact router; focused artifact details live in `references/artifacts/` so agents can load only the part needed for the current gate.

## Required Fanout

Read these files by need:

- `references/artifacts/request-structure.md`: `.stageflow/index.json`, session current pointer, request `state.json`, request tree, and stage rule/review prompt routing.
- `references/artifacts/definition-store.md`: `01-definition/definition-store/`, `working-set.json.active_pending_questions`, store progress invariant, duplicate/derived decision retirement, risk levels, and optional `question-backlog.md`.
- `references/artifacts/definition-gates.md`: `question-scope-transition-review.md`, `transition-risk-goal.md`, `transition-risk.md`, goal-achievement decision readiness audit, transition-risk categories, `Prior Answer Check`, and labeled resolution options.
- `references/artifacts/stage-review-approval.md`: later-stage `goal.md`, bounded `review/subagents`, main agent `review/final.md`, `approval.md`, and validator templates.

Stage-specific artifact formats and Rule ID tables stay in the stage writing and review rule files:

- Definition: `references/stages/01-definition/definition-writing-and-review-rules.md`
- Implementation plan: `references/stages/02-implementation-plan/implementation-plan-writing-and-review-rules.md`
- Implementation: `references/stages/03-implementation/implementation-writing-and-review-rules.md`

Also read `references/language-policy.md` before writing artifacts or user-facing workflow messages, and read `references/intent-fidelity.md` when user wording could be narrowed into unapproved UX, route, screen, state, data, API, or persistence behavior.

## Core Tree

The full tree and registry examples are in `references/artifacts/request-structure.md`. The required stage artifacts are:

```text
.stageflow/requests/<request-id>/
  state.json
  01-definition/
    definition.md
    definition-store/
    question-scope-transition-review.md
    transition-risk-goal.md
    transition-risk.md
    review/final.md
    review/subagents/001-full-bounded-review.md
    approval.md
  02-implementation-plan/
    goal.md
    implementation-plan.md
    review/final.md
    review/subagents/001-full-bounded-review.md
    review/subagents/002-flow-completeness-review.md
    approval.md
  03-implementation/
    goal.md
    implementation.md
    review/final.md
    review/subagents/001-full-bounded-review.md
    approval.md
```

Each stage must pass in order. A later stage validation also validates every earlier stage.

## Definition Hot Path Summary

`01-definition/definition-store/` is required for active clarification. `working-set.json.active_pending_questions` is the canonical live pending batch; `definition.md` is the approval-ready snapshot. Answer-like `AWAITING_USER` turns require valid store decision progress: a new `DEC-*` ledger row with a turn-start `source_pending_id`, non-empty affected IDs, matching `trace-index.json`, and matching `sync-state.decision_sync`. Follow-up turns may leave the store unchanged only when the response restates every active pending question and labeled option.

Duplicate or derived pending questions retire through the same store shape as user answers. A store with no active pending questions and no recognized sync gate is invalid.

## Definition Gate Summary

Question scope transitions require `01-definition/question-scope-transition-review.md` before lower-scope pending questions. A user stop signal requires `transition-risk-goal.md` plus `transition-risk.md` before definition review/approval. The transition-risk gate is a goal-achievement decision readiness audit: generated risks must be missing, conflicting, or ambiguous goal-critical definition decisions. Already answered and reflected decisions are not risk cases; carry them into implementation-plan coverage or constraints.

`transition-risk.md` risk rows use `Definition Coverage` values `uncovered`, `conflicting`, `ambiguous`, or `not-applicable`; `uncovered` means a goal-critical decision is missing from definition, while `not-applicable` means the audit found no material decision gap. `Prior Answer Check` must prove the candidate was compared against existing definition evidence. Material risks need at least two labeled resolution options such as `Option 1:` and `Option 2:`.

## Review And Approval Summary

Every stage review uses bounded subagent shards under `review/subagents/<cycle>-<slice>.md`; the main agent synthesizes `review/final.md`. Self-review never satisfies the gate, and legacy `review.md` does not satisfy the review gate. User approval is recorded in the same stage's `approval.md`.

## Validator Templates

The skill-local validator wrapper delegates to `<plugin-root>/scripts/validate_stageflow.py`. Run the wrapper from the plugin root and pass `--root <target-project-root>` when validating a target project.

```bash
python <plugin-root>/skills/stageflow/scripts/validate_stageflow.py --root <target-project-root> --current --session-id <session-id> --phase <phase>
python <plugin-root>/skills/stageflow/scripts/validate_stageflow.py --print-template stage-tree
python <plugin-root>/skills/stageflow/scripts/validate_stageflow.py --print-template definition
python <plugin-root>/skills/stageflow/scripts/validate_stageflow.py --print-template implementation-plan
python <plugin-root>/skills/stageflow/scripts/validate_stageflow.py --print-template implementation
python <plugin-root>/skills/stageflow/scripts/validate_stageflow.py --print-template review
python <plugin-root>/skills/stageflow/scripts/validate_stageflow.py --print-template approval
```
