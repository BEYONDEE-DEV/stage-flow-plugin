# Plan

## Summary

현재 프로젝트 `stage-flow-plugin`의 Stageflow definition 질문 흐름을 개선한다. 사용자가 원하는 핵심은 `큰방향 -> 주요결정`, `주요결정 -> 세부확인`으로 질문 깊이를 낮추기 전에, 별도 subagent가 상위 질문이 정말 남아 있지 않은지 검토하도록 만드는 것이다.

구현은 `simple-workflow-plugin`이 아니라 이 저장소의 Stageflow plugin 코드와 문서에만 적용한다. 코드 수정은 이 계획이 리뷰를 통과하고 사용자가 명시적으로 승인한 뒤에만 진행한다.

## Requirements Coverage

| ID | Requirement | Execution Plan |
| --- | --- | --- |
| REQ-001 | Stageflow definition 질문 흐름에서 `큰방향 -> 주요결정` 전환 전에 상위 질문 잔여 여부를 subagent가 검토한다. | definition 작성 규칙과 Stageflow SKILL 지침에 `큰방향` 전환 검토 조건을 추가한다. 전환 검토 subagent의 목적, 입력, 허용 출력, 실패 시 동작을 문서화하고, validator 또는 hook에서 필요한 구조적 증거를 확인하도록 구현한다. |
| REQ-002 | Stageflow definition 질문 흐름에서 `주요결정 -> 세부확인` 전환 전에 상위 질문 잔여 여부를 subagent가 검토한다. | `주요결정`에서 `세부확인`으로 내려가는 경우도 같은 전환 검토 gate를 적용한다. `Clarification History`, `Resolved Decisions`, 현재 `Pending Clarifications`, 선택적 `question-backlog.md`를 검토 근거로 사용하게 한다. |
| REQ-003 | 상위 질문이 남아 있으면 더 낮은 질문 scope로 내려가지 않는다. | validator 또는 review 규칙에 실패 조건을 추가한다. 전환 검토가 FAIL이거나 누락되면 낮은 scope pending row를 review-ready로 인정하지 않게 하고, 다음 pending batch는 상위 scope 질문으로 유지하도록 지침을 보강한다. |
| REQ-004 | 전환 검토 subagent는 기존 Stageflow `AWAITING_USER` 안전 규칙과 충돌하지 않아야 한다. | `scripts/stageflow_hook_check.py`의 `AWAITING_USER` subagent 허용 조건을 검토해, `question-generation` 후보 생성과 구분되는 `question-scope-transition-review` 역할을 안전하게 허용할지 계획한다. 허용한다면 쓰기 범위는 definition 관련 helper artifact로 제한한다. |
| REQ-005 | 변경은 Stageflow plugin 프로젝트 안에서 검증 가능해야 한다. | 관련 tests를 추가 또는 갱신한다. 예상 검증은 `python3 -m unittest discover -s tests`이며, 최소한 전환 검토 누락, FAIL 검토, 잘못된 낮은 scope 진행, hook subagent 허용/차단 경계를 다룬다. |

## Change Targets

- `skills/stageflow/SKILL.md`: 질문 scope 전환 전 subagent checkpoint를 Stageflow 운영 규칙에 추가한다.
- `skills/stageflow/references/stages/01-definition/definition-writing-and-review-rules.md`: definition 작성자가 전환 검토를 언제 요구하고 어떻게 기록해야 하는지 추가한다.
- `skills/stageflow/references/stages/01-definition/definition-review-agent-prompt.md`: definition review subagent가 전환 검토 누락 또는 실패를 blocking issue로 판단하도록 보강한다.
- `skills/stageflow/references/artifact-format.md` 또는 기존 definition reference: 새 helper artifact가 필요할 경우 그 위치와 의미를 기존 artifact 설명에 맞춰 기록한다.
- `scripts/stageflow_hook_check.py`: `AWAITING_USER` 상태에서 허용되는 subagent role과 쓰기 경계를 기존 안전 모델과 충돌하지 않게 조정한다.
- `scripts/validate_stageflow.py`: 전환 검토 기록이 필요한 경우를 구조적으로 검증한다. 의미 판단은 subagent review가 맡고, validator는 누락, FAIL, 잘못된 scope 진행 같은 명백한 gate 위반을 막는다.
- `tests/test_hook_check.py`, `tests/test_validator.py`: 변경된 gate와 훅 경계를 검증하는 negative/positive tests를 추가한다.

## Flow Check

요청 자체에는 workflow-level 위험이 있다. 현재 Stageflow 규칙에는 breadth-first 질문 원칙이 이미 있지만, `AWAITING_USER` 중 허용되는 subagent가 `question-generation`으로 제한되어 있어 새 전환 검토 subagent를 단순히 문서에만 추가하면 실제 사용 중 차단될 수 있다.

따라서 구현 순서는 다음과 같아야 한다.

1. 전환 검토가 필요한 정확한 조건을 정의한다.
2. 전환 검토 subagent의 역할명, 입력, 출력, 쓰기 위치를 정한다.
3. 훅이 그 subagent만 안전하게 허용하도록 조정한다.
4. validator가 누락/FAIL/잘못된 낮은 scope 전환을 막도록 한다.
5. 테스트로 문서 규칙, validator, hook 동작을 함께 닫는다.

이 계획이 승인되기 전에는 Stageflow plugin 코드 수정으로 넘어가지 않는다.

## Validation

- `python3 -m unittest discover -s tests`
- 필요한 경우 특정 실패를 빠르게 확인하기 위해 `python3 -m unittest tests.test_validator tests.test_hook_check`를 먼저 실행한다.
- Simple Workflow validator는 현재 프로젝트에 `scripts/validate_simple_workflow.py`가 없으므로 이 workflow artifact에 대해서는 실행하지 않는다.

## Out Of Scope

- `simple-workflow-plugin` 수정.
- 새 Stageflow stage 추가.
- definition 질문 scope 이름 변경.
- implementation-plan 또는 implementation stage의 별도 flow gate 재설계.
- 사용자 승인 전 코드 구현.
