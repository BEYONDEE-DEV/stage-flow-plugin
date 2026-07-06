# Stage Review And Approval Artifacts

This file owns `goal.md`, `review/`, `approval.md`, and validator-template documentation shared by stages.

## goal.md

`goal.md` is required only for `02-implementation-plan` and `03-implementation`. Normal `01-definition` clarification does not use `create_goal`; the stop-signal transition-risk audit is the only exception and is recorded as `transition-risk-goal.md`, not `goal.md`. For later stages, `goal.md` records the goal handoff for that stage artifact, not the whole request.

```md
# Goal

Stage: implementation-plan

Artifact Path: `02-implementation-plan/implementation-plan.md`

Artifact Fingerprint: sha256:<artifact-fingerprint>

## Goal Invocation

Tool: create_goal

Invocation recorded: yes

Invocation result: goal created

## Goal Objective

Advance this later-stage artifact to the next required approval gate.

## Goal Tool Status

Goal created: yes

Goal status: active
```

Required values:

- `Stage` must match the folder phase.
- `Artifact Fingerprint` must be the SHA-256 of the current stage artifact bytes.
- `Tool: create_goal`, `Invocation recorded: yes`, and `Goal created: yes` are required.
- `Goal status` must be active, in progress, complete, completed, or another non-pending success state.

## review folder

Every stage has one `review/` folder. Subagents write bounded shard files under `review/subagents/`; the main agent writes `review/final.md` after reading those shard files.

Required structure:

```text
<stage-folder>/review/
  final.md
  subagents/
    001-full-bounded-review.md
```

Use more shard files when review work can be split by rule cluster, domain/behavior area, changed area, or implementation work item. Use one bounded shard only for small/simple stages where parallelism would add no coverage.

`02-implementation-plan` must always include an additional `flow-completeness` shard, commonly `review/subagents/002-flow-completeness-review.md`, before approval. That shard must evaluate `IP-FLOW-001` through `IP-FLOW-007` and include `## Flow Rule Checklist` plus `## Flow Coverage Audit`.

A subagent shard file uses this shape:

```md
# Subagent Review Shard

Stage: definition

Reviewed Artifact Fingerprint: sha256:<artifact-fingerprint>

Shard Scope: intent and clarification coverage

## Inputs Read

- `01-definition/definition.md`
- `references/stages/01-definition/definition-writing-and-review-rules.md`

## Verdict

PASS

## Blocking Issues

No blocking issues.
```

The main-agent synthesis file `review/final.md` uses this shape:

```md
# Review

Stage: definition

Reviewed Artifact Fingerprint: sha256:<artifact-fingerprint>

## Review Method

Subagent review.

## Reviewer

main agent synthesis

## Review Cycle

| Cycle | Reviewer | Result | Notes |
| --- | --- | --- | --- |
| 1 | main agent synthesis | PASS | Synthesized bounded subagent review shards. |

## Subagent Review Shards

| Shard File | Scope | Verdict | Blocking Issue |
| --- | --- | --- | --- |
| review/subagents/001-full-bounded-review.md | full bounded review for a small stage | PASS | None |

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

- `review/final.md` exists; legacy `review.md` does not satisfy the review gate.
- `Subagent review.` in `## Review Method`.
- A reviewed artifact fingerprint matching the current stage artifact in `review/final.md` and every listed shard file.
- `## Subagent Review Shards` in `review/final.md`, with each listed shard file under `review/subagents/` and each shard verdict `PASS`.
- Each listed shard file exists, records `Stage`, `Reviewed Artifact Fingerprint`, `Shard Scope`, non-empty `## Inputs Read`, `PASS` verdict, and no blocking issues.
- For implementation-plan review, `## Subagent Review Shards` includes a `Scope` of `flow-completeness`; that shard records `## Flow Rule Checklist` with every `IP-FLOW-*` rule and `## Flow Coverage Audit`.
- `## Writing And Review Rule Checklist` in `review/final.md` containing every Rule ID from the matching stage rule file.
- `PASS` for each required Rule ID in the checklist.
- No blocking issue for each required Rule ID in the checklist.
- `PASS` as the latest verdict.
- No blocking issues.
- A final verdict confirming no blocking issues.

Self-review never satisfies the gate. Subagent shard files do not approve stages independently; only `review/final.md` can satisfy the stage review gate.

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

The skill-local validator wrapper delegates to `<plugin-root>/scripts/validate_stageflow.py`. Run the wrapper path from the plugin root, and pass `--root <target-project-root>` when validating a target project rather than assuming that project has its own validator script.

The validator can print starter templates:

```bash
python <plugin-root>/skills/stageflow/scripts/validate_stageflow.py --print-template stage-tree
python <plugin-root>/skills/stageflow/scripts/validate_stageflow.py --print-template goal  # implementation-plan/implementation only
python <plugin-root>/skills/stageflow/scripts/validate_stageflow.py --print-template definition
python <plugin-root>/skills/stageflow/scripts/validate_stageflow.py --print-template implementation-plan
python <plugin-root>/skills/stageflow/scripts/validate_stageflow.py --print-template implementation
python <plugin-root>/skills/stageflow/scripts/validate_stageflow.py --print-template review
python <plugin-root>/skills/stageflow/scripts/validate_stageflow.py --print-template approval
```

Validate a target project with:

```bash
python <plugin-root>/skills/stageflow/scripts/validate_stageflow.py --root <target-project-root> --current --session-id <session-id> --phase <phase>
```
