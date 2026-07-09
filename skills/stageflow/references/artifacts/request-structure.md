# Stageflow Request Structure

This file owns registry files, request folders, and routing to stage rule and review-prompt files. `references/artifact-format.md` stays as the request-level router.

## Registry Files

`.stageflow/index.json`

```json
{
  "version": "1",
  "requests": [
    {
      "id": "20260621-1200-three-stage-workflow",
      "title": "Three stage workflow",
      "status": "definition",
      "created_at": "2026-06-21T03:00:00Z",
      "updated_at": "2026-06-21T03:00:00Z"
    }
  ]
}
```

`.stageflow/sessions/<session-id>/current.json`

```json
{
  "request_id": "20260621-1200-three-stage-workflow",
  "phase": "definition",
  "active": true,
  "activated_by": "explicit_skill_invocation"
}
```

`.stageflow/requests/<request-id>/state.json`

```json
{
  "request_id": "20260621-1200-three-stage-workflow",
  "phase": "definition",
  "last_validated_at": null
}
```

Allowed phases are `definition`, `implementation-plan`, `implementation`, and `completed`.

## Request Tree

```text
.stageflow/requests/<request-id>/
  state.json
  01-definition/
    definition.md
    definition-store/         (required hot-path store for active clarification)
      working-set.json
      decision-ledger.jsonl
      trace-index.json
      sync-state.json
      impact-candidates.json      (optional helper)
      targeted-sync-plan.json     (optional helper)
      full-consistency-report.json (required for full-consistency-required gate)
    question-backlog.md       (optional helper)
    question-scope-transition-review.md  (required before lower-scope pending questions)
    transition-risk-goal.md   (required after user stop signal before definition approval)
    transition-risk.md        (required after user stop signal before definition approval)
    review/
      final.md
      subagents/
        001-full-bounded-review.md
    approval.md
  02-implementation-plan/
    goal.md
    implementation-plan.md
    review/
      final.md
      subagents/
        001-full-bounded-review.md
        002-flow-completeness-review.md
    approval.md
  03-implementation/
    goal.md
    implementation.md
    review/
      final.md
      subagents/
        001-full-bounded-review.md
    approval.md
```

Each stage must pass in order. A later stage validation also validates every earlier stage.

## Stage Writing And Review Rule Files

Before writing or reviewing a stage artifact, read the matching rule file:

- Definition: `references/stages/01-definition/definition-writing-and-review-rules.md`
- Implementation plan: `references/stages/02-implementation-plan/implementation-plan-writing-and-review-rules.md`
- Implementation: `references/stages/03-implementation/implementation-writing-and-review-rules.md`

Each rule file owns that stage's artifact format, required sections, writing rules, and review checks.

Also read `references/language-policy.md` before writing or reviewing stage prose. Keep validator-required headings, table columns, schema keys, paths, commands, and status/control values unchanged, but write user-facing artifact content, clarification questions, option descriptions, review evidence, change plans, and summaries in the selected user/artifact language.

## Stage Review Agent Prompt Files

Before running a review subagent, use the matching prompt file:

- Definition: `references/stages/01-definition/definition-review-agent-prompt.md`
- Implementation plan: `references/stages/02-implementation-plan/implementation-plan-review-agent-prompt.md`
- Implementation: `references/stages/03-implementation/implementation-review-agent-prompt.md`

Each prompt file owns the review mission, allowed inputs, forbidden actions, review instructions, and required review output for that stage.

Use `references/intent-fidelity.md` when stage artifacts involve user wording that could be narrowed into unapproved UX, route, screen, state, data, API, or persistence behavior.

Use `references/language-policy.md` whenever starter templates, review evidence, or user-facing Stageflow workflow messages are written so template filler such as `Describe...`, `No pending...`, or `Record...` is replaced with request-specific prose in the selected language.
