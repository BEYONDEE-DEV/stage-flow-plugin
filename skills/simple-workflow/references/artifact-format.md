# Simple Workflow Artifact Format

Simple Workflow uses one human artifact, one internal review record, and small metadata files.

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
  "activated_by": "explicit_skill_invocation"
}
```

`.simple/requests/<request-id>/state.json`

```json
{
  "request_id": "20260609-1120-simple-workflow-plugin",
  "workflow_version": 2,
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

`goal_status` is optional for legacy requests. New requests use `pending`, change it to `active`
only after `create_goal` succeeds, set `completing` immediately before requesting Goal completion,
and use `completed` only after `update_goal(status="complete")` succeeds. For v2, Goal creation sets
`goal_plan_fingerprint` and `approved_plan_fingerprint` to the same reviewed value.
`goal_plan_fingerprint` remains the immutable fingerprint from the Goal objective;
`approved_plan_fingerprint` changes only after an explicitly approved material replan.

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

## Notes

현재 `plan.md` fingerprint에 대한 내부 리뷰가 통과했다.
```

The complete trimmed `## Verdict` body must equal `PASS`; containing the word `PASS` inside a
different verdict is invalid. `## Blocking Issues` uses blocking-specific no-issue vocabulary,
while `## Flow Check` uses flow-specific no-issue vocabulary. Do not swap the two fields' status
values.
