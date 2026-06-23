# Stageflow Artifact Format

Stageflow uses one request folder with three fixed stage folders. This file defines request-level structure and common stage files. Stage-specific artifact formats live in each stage's writing and review rule file.

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
    goal.md
    definition.md
    review.md
    approval.md
  02-implementation-plan/
    goal.md
    implementation-plan.md
    review.md
    approval.md
  03-implementation/
    goal.md
    implementation.md
    review.md
    approval.md
```

Each stage must pass in order. A later stage validation also validates every earlier stage.

## Stage Writing And Review Rule Files

Before writing or reviewing a stage artifact, read the matching rule file:

- Definition: `references/stages/01-definition/definition-writing-and-review-rules.md`
- Implementation plan: `references/stages/02-implementation-plan/implementation-plan-writing-and-review-rules.md`
- Implementation: `references/stages/03-implementation/implementation-writing-and-review-rules.md`

Each rule file owns that stage's artifact format, required sections, writing rules, and review checks.

## Stage Review Agent Prompt Files

Before running a review subagent, use the matching prompt file:

- Definition: `references/stages/01-definition/definition-review-agent-prompt.md`
- Implementation plan: `references/stages/02-implementation-plan/implementation-plan-review-agent-prompt.md`
- Implementation: `references/stages/03-implementation/implementation-review-agent-prompt.md`

Each prompt file owns the review mission, allowed inputs, forbidden actions, review instructions, and required review output for that stage.

## goal.md

Every stage has its own `goal.md`. It records the goal handoff for that stage artifact, not the whole request.

```md
# Goal

Stage: definition

Artifact Path: `01-definition/definition.md`

Artifact Fingerprint: sha256:<artifact-fingerprint>

## Goal Invocation

Tool: create_goal

Invocation recorded: yes

Invocation result: goal created

## Goal Objective

Advance this stage artifact to the next required user input or approval gate. If pending clarifications are presented, stop at user-answer waiting instead of continuing review or next-stage work.

## Goal Tool Status

Goal created: yes

Goal status: active
```

Required values:

- `Stage` must match the folder phase.
- `Artifact Fingerprint` must be the SHA-256 of the current stage artifact bytes.
- `Tool: create_goal`, `Invocation recorded: yes`, and `Goal created: yes` are required.
- `Goal status` must be active, in progress, complete, completed, or another non-pending success state.
- When `Pending Clarifications` are active, `goal.md` must record `Goal status: completed` and `Goal completion reason: awaiting user clarification`; this means the current Codex goal reached a user-input wait point, not that the stage was approved.

## review.md

Every stage has one `review.md`. Use it as a compact review cycle ledger.

```md
# Review

Stage: definition

Reviewed Artifact Fingerprint: sha256:<artifact-fingerprint>

## Review Method

Subagent review.

## Reviewer

reviewer subagent

## Review Cycle

| Cycle | Reviewer | Result | Notes |
| --- | --- | --- | --- |
| 1 | reviewer subagent | PASS | No blocking issues. |

## Writing And Review Rule Checklist

| Rule ID | Evidence Read | Verdict | Blocking Issue |
| --- | --- | --- | --- |
| DEF-RULE-001 | Project context and definition were checked. | PASS | None |

## Latest Verdict

PASS

## Blocking Issues

No blocking issues

## Final Verdict

No blocking issues.
```

A passing review requires:

- `Subagent review.` in `## Review Method`.
- A reviewed artifact fingerprint matching the current stage artifact.
- `## Writing And Review Rule Checklist` containing every Rule ID from the matching stage rule file.
- `PASS` for each required Rule ID in the checklist.
- No blocking issue for each required Rule ID in the checklist.
- `PASS` as the latest verdict.
- No blocking issues.
- A final verdict confirming no blocking issues.

Self-review never satisfies the gate.

## approval.md

Every stage has one `approval.md`. It records the user's explicit approval for that stage only.

```md
# Approval

Stage: definition

Stage approved: yes

Approved By: user

Approved At: 2026-06-21T03:00:00Z

## Approval Text

Approved.
```

Approval text must contain a positive approval intent such as `approve`, `approved`, `go ahead`, `proceed`, `yes`, `승인`, or `진행`. Negative approval text fails validation.

## Validator Templates

The validator is bundled with the Stageflow plugin. Run it from the plugin root, and pass `--root <target-project-root>` when validating a target project rather than assuming that project has its own validator script.

The validator can print starter templates:

```powershell
python <plugin-root>/scripts/validate_stageflow.py --print-template stage-tree
python <plugin-root>/scripts/validate_stageflow.py --print-template goal
python <plugin-root>/scripts/validate_stageflow.py --print-template definition
python <plugin-root>/scripts/validate_stageflow.py --print-template implementation-plan
python <plugin-root>/scripts/validate_stageflow.py --print-template implementation
python <plugin-root>/scripts/validate_stageflow.py --print-template review
python <plugin-root>/scripts/validate_stageflow.py --print-template approval
```

Validate a target project with:

```powershell
python <plugin-root>/scripts/validate_stageflow.py --root <target-project-root> --current --session-id <session-id> --phase <phase>
```
