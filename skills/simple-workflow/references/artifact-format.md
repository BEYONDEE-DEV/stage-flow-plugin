# Simple Workflow Artifact Format

Simple Workflow uses one human artifact, one internal review record, and small metadata files.

## Workflow Root

Every path below is relative to one resolved workflow root. An explicit root is authoritative. A
confirmed multi-repository request uses the bundle root named by an exact `slot.path` in an ancestor
`.stageflow-worktrees/slots.json`, while a single-repository request keeps its repository root. A
manifest's presence alone does not promote a pointerless single-repo request, and path names such as
`worktrees/<name>` are never bundle evidence. Hook continuation may recover the bundle from a child
cwd only when the bundle session pointer selects the same request.

The bundle owns one canonical `.simple` tree. A child copy with byte-identical `plan.md`, `review.md`, and `state.json`
produces a warning and the bundle remains authoritative. A missing or
different file is a divergent duplicate: UserPrompt and Stop report it without blocking, but the
in-scope Simple Workflow `create_goal` is denied until the user manually removes or aligns the child
copy; unrelated Goal calls prepass. The plugin never moves, merges, aligns, or deletes these artifacts.

## Metadata Files

`.simple/index.json`

```json
{
  "version": "1",
  "requests": [
    {
      "id": "20260609-1120-simple-workflow-plugin",
      "title": "Simple workflow request",
      "status": "plan",
      "created_at": "2026-06-09T02:20:00Z",
      "updated_at": "2026-06-09T02:30:00Z"
    }
  ]
}
```

`.simple/sessions/<session-id>/current.json`

```json
{
  "request_id": "20260609-1120-simple-workflow-plugin",
  "phase": "plan",
  "activated_by": "explicit_skill_invocation",
  "workflow_root": "/absolute/path/to/project"
}
```

`workflow_root` is optional for existing pointers and required by the agent when it creates or
selects a new pointer. It is the canonical host-native absolute root that owns this request's
`.simple` tree. The field is a consistency assertion after a root has been located, not a global
session locator. `--current` validation accepts a missing legacy field, but when present requires
canonical absolute path text equal to the validator root; relative values, another root, symlink
aliases, and non-canonical spellings are invalid. `--request` validation does not read or require a
session pointer. Hooks never migrate or rewrite this field.

`.simple/requests/<request-id>/state.json`

```json
{
  "request_id": "20260609-1120-simple-workflow-plugin",
  "workflow_version": 2,
  "intent_challenge_version": 1,
  "phase": "plan",
  "plan_approval_status": "pending",
  "goal_status": "pending",
  "goal_plan_fingerprint": null,
  "approved_plan_fingerprint": null,
  "last_validated_at": null
}
```

Allowed phases are `plan`, `review`, and `completed`.

The selected request id must match `YYYYMMDD-HHMM-short-slug` and be registered exactly once in
`index.json`. The selected index entry, session `current.json`, and request `state.json` must have
the same phase. Readers accept legacy `id` in place of `request_id` and legacy `status` in place of
`phase`, but missing or contradictory values are invalid.

Missing `workflow_version` identifies a legacy request. New requests use integer
`workflow_version: 2`; other values are invalid. V2 requests use `plan_approval_status: pending`
before initial approval or during material replan, and `approved` only while the current plan is
authorized for execution.

New requests also use exact integer `intent_challenge_version: 1`. This marker requires the
structured `## Intent Challenge Check` review contract below. Existing v2 and legacy requests that
do not have the marker keep their previous review schema. A marker with any other value is invalid,
and the marker is invalid without `workflow_version: 2`.

`goal_status` is optional for legacy requests. New requests use `pending`, change it to `active`
only after `create_goal` succeeds, set `completing` immediately before requesting Goal completion,
and use `completed` only after `update_goal(status="complete")` succeeds. Before Goal creation,
explicit approval sets `approved_plan_fingerprint` to the current reviewed plan while Goal remains
`pending`. Goal creation sets only `goal_plan_fingerprint` and Goal status.
`goal_plan_fingerprint` remains the immutable fingerprint from the Goal objective;
`approved_plan_fingerprint` changes only after an explicitly approved material replan.

V2 permits only these `phase | plan_approval_status | goal_status` combinations:

```text
plan      | pending  | pending
review    | pending  | pending
review    | approved | pending
review    | approved | active
review    | pending  | active
review    | approved | completing
completed | approved | completed
```

`review | approved | pending` preserves approval when Goal creation fails and is retried.
`review | pending | active` preserves the original Goal and previous approval fingerprints while a
material replan waits for approval.

## plan.md

`plan.md` is the only human-facing workflow artifact.

```md
# Plan

## Summary

요청된 변경의 목적과 접근 방식을 간단히 설명한다.

## Outcome And Completion Criteria

- 사용자가 변경된 요청 상태를 validator 명령 출력에서 확인할 수 있고 관련 테스트가 통과한다.

## Requirements Coverage

| Requirement | Plan | Completion Evidence |
| --- | --- | --- |
| REQ-001 | `REQ-001`에서 요구한 동작을 구현한다. | 관련 테스트와 실제 사용자 흐름의 상태 출력으로 완료를 확인한다. |

## Change Targets

| Target | Planned Change |
| --- | --- |
| `path/or/module` | `REQ-001`을 만족하는 가장 작은 변경을 적용한다. |

## Flow Check

- 계획된 변경과 관련된 사용자 동선, 상태 전이, 데이터 흐름, 실패/재시도 경로, 검증 흐름을 확인한다.
- 이번 변경이 만든 문제가 아니더라도 관련 흐름 문제를 발견하면 사용자에게 알리고, 범위 밖이면 범위 밖이라고 명시한다.

## Validation

- `REQ-001`이 만족되는지 증명하는 대상 검사를 실행한다.

## Out Of Scope

- `## Requirements Coverage`에 포함되지 않은 작업은 범위에서 제외한다.
```

The outcome must be observable rather than a generic completion claim. Each v2 requirement row
must name evidence that can prove the affected result, such as a test, command output, state,
response, file, or user-flow observation. Empty, deferred, or placeholder evidence is invalid.

During material replan, set `plan_approval_status: pending` before editing `plan.md`. Keep
`goal_plan_fingerprint` unchanged, replace `review.md` with a passing review of the revised plan,
and update `approved_plan_fingerprint` plus approval status only after explicit reapproval. No new
Goal or plan artifact is created.

## review.md

`review.md` is an internal subagent review record. It is not a user-facing workflow artifact.

```md
# Review

## Reviewed Plan Fingerprint

Reviewed Plan Fingerprint: sha256:<hex>

## Reviewer

subagent

## Verdict

PASS

## Blocking Issues

차단 없음

## Flow Check

사용자에게 알려야 할 관련 흐름 문제 없음

## Question Depth Check

상위 질문 없음

## Intent Challenge Check

### Findings

| Finding | User Decision Or Resolution | Verdict |
| --- | --- | --- |
| NONE | 요구사항 타당성과 대안을 검토했으며 사용자 결정이 필요한 material finding이 없다. | PASS |

### Intent Challenge Final Verdict

PASS

## Notes

현재 `plan.md` fingerprint에 대한 내부 리뷰가 통과했다.
```

The complete trimmed `## Verdict` body must equal `PASS`; containing the word `PASS` inside a
different verdict is invalid. `## Blocking Issues` uses blocking-specific no-issue vocabulary.
`## Flow Check` and `## Question Depth Check` require non-empty review results and may record a
non-blocking observation without invalidating the passing verdict.

For a request with `intent_challenge_version: 1`, `## Intent Challenge Check` records the durable
result of the bounded review that ran before the first user intent confirmation. The Findings table
header is exactly `Finding | User Decision Or Resolution | Verdict` and contains at least one row.
Each material finding uses a unique `IC-###`, substantive Korean decision or resolution text, and
exact `PASS`. If there were no material findings, exactly one `NONE` row records the Korean review
basis. `NONE` cannot be combined with another row. Every row and
`### Intent Challenge Final Verdict` must be exact uppercase `PASS`, proving that no material
finding remains unresolved. The plan reviewer also checks that these resolutions, the confirmed
intent, and the current plan agree.

After both post-execution reviews pass, the main agent appends this internal section to the same
`review.md`:

```md
## Completion Review
### Completion Plan Fingerprint
Completion Plan Fingerprint: sha256:<hex>
### Requirements Evidence
| Requirement | Actual Evidence | Verdict |
| --- | --- | --- |
| REQ-001 | 실제 테스트, 출력, 상태 또는 파일 근거 | PASS |

### Observable Outcome Evidence

사용자 또는 시스템이 최종 결과를 관찰한 실제 근거

### Completion Verdict

PASS
```

Exactly one Completion Review exists and every planned REQ appears exactly once. Evidence must be non-empty and not an obvious placeholder;
each row and the final verdict use exact uppercase `PASS`. The completion fingerprint must equal the
current plan and approved fingerprint. New completions require this section. `--phase all` still
accepts an older completed v2 request without it, but validates it whenever present.
