# Definition Artifact Template

This file owns the starter `01-definition/definition.md` shape. Keep validator-required headings and table columns exact; fill natural-language content using `references/language-policy.md`.

## Stage Artifact Format

```md
# Definition

## User Goal

사용자가 달성하려는 목표를 한두 문장으로 기록한다.

## Purpose And Intent

| Field | Value |
| --- | --- |
| Purpose | 사용자가 이 변경을 요청한 근본 목적. 모르면 `unknown`으로 기록하고 purpose-focused 큰방향 pending question을 유지한다. |
| User Value | 사용자가 얻는 가치. |
| Business/Product Value | 제품 또는 운영 관점의 가치. |
| Source | user-request, user-answer, project-context, inferred 중 하나와 근거. |
| Confidence | confirmed, inferred, unknown 중 하나. |

## Request Profile

| Field | Value |
| --- | --- |
| Primary | feature |
| Secondary | N/A |

## Desired Outcomes

| ID | Outcome | Source |
| --- | --- | --- |
| OUT-001 | 사용자가 기대하는 완료 결과. | 사용자 요청 |

## Current Problems

| ID | Problem | Expected Behavior | Source |
| --- | --- | --- | --- |
| PROB-001 | 현재 문제가 없으면 `N/A`로 기록한다. | N/A | N/A |

## Problem-To-Requirement Mapping

| Problem ID | Requirement IDs | Behavior Resolution |
| --- | --- | --- |
| PROB-001 | REQ-001 | 문제를 어떤 요구사항/동작으로 해결하는지 기록한다. |

## User-Specified Constraints

- 사용자가 명시한 제약을 기록하거나 `명시된 제약 없음`을 쓴다.

## Discovered Constraints

- 프로젝트 확인 중 발견한 제약을 기록하거나 `발견된 제약 없음`을 쓴다.

## Pending Clarifications

| ID | Question Scope | Question | Options | Recommended Option | Transition Option | Why This Matters | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PENDING-001 | 큰방향 | 현재 목적은 아직 확인되지 않았습니다. 이 변경이 우선 달성해야 할 목적은 무엇인가요? | Option 1: 사용자가 제기한 즉시 workflow 문제를 해결한다; Option 2: 후속 변경에 대비한 재사용 가능한 제품 유연성을 만든다 | Option 1 | N/A | 이 답변은 `Purpose And Intent`와 `Desired Outcomes`에 반영되어 이후 범위와 검증 기준의 기준점이 됩니다. | pending |
| PENDING-002 | 큰방향 | 현재 요청 범위가 핵심 변경에만 머물지, 인접 동작까지 포함할지 열려 있습니다. 상위 범위는 어디까지로 잡을까요? | Option 1: 직접 요청된 동작으로 범위를 좁힌다; Option 2: 나중에 영향을 받을 인접 동작까지 포함한다 | Option 1 | N/A | 이 답변은 `Requirements`와 `Boundaries`에 반영되어 구현 계획이 불필요한 인접 동작까지 포함하지 않도록 합니다. | pending |
| PENDING-003 | 큰방향 | 현재 영향 대상이 사용자 화면/경험인지 내부 workflow인지 아직 확정되지 않았습니다. 주된 적용 표면은 무엇인가요? | Option 1: 사용자-facing 동작; Option 2: 내부 workflow 동작; Option 3: 둘 다 | Option 1 | N/A | 이 답변은 `User Flow`, `Normal Behavior Model`, `Policy Rules`에 반영되어 이후 동작 질문의 기준을 정합니다. | pending |

## Clarification History

| Round ID | Questions Asked | User Response | Implementation Plan Option Offered | User Transition Signal | Reflected In |
| --- | --- | --- | --- | --- | --- |
| CLAR-000 | 완료된 clarification이 아직 없다. | N/A | no | N/A | N/A |

## Open Questions

| ID | Decision Needed | Context Or Conflict | Recommended Option | Alternatives | Impact | Blocking | Resolution Target |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Q-001 | 열린 질문 없음. | N/A | N/A | N/A | N/A | no | N/A |

## Resolved Decisions

| ID | Source Question ID | Answer Source | Decision | Reflected In |
| --- | --- | --- | --- | --- |
| DEC-001 | N/A | N/A | 확정된 결정 없음. | N/A |

## Intent Fidelity

| ID | User Wording | Normalized Requirement | Allowed Interpretations | Disallowed Interpretations | Linked Requirement/Policy |
| --- | --- | --- | --- | --- | --- |
| INTENT-001 | 사용자의 원문 또는 의미를 보존한 요약. | 사용자 표현에서 요구사항 의미를 보존한다. | 사용자 답변이나 resolved decision이 명시적으로 뒷받침한 해석. | 승인되지 않은 더 좁거나 넓거나 기술적인 해석. | REQ-001, SP-001 |

## Requirements

| ID | Type | Source | Requirement Detail | Boundary Or Exclusion | Linked Outcomes Or Problems |
| --- | --- | --- | --- | --- | --- |
| REQ-001 | feature | 사용자 요청. | 검증 가능한 요구사항 한 가지를 기록한다. | 제외되는 동작을 명시한다. | OUT-001 |

## Acceptance Criteria

- `REQ-001`은 연결된 outcome 또는 problem resolution을 검증할 수 있을 때 충족된다.

## Normal Behavior Model

수정되거나 원하는 서비스 동작을 구조화된 모델로 설명한다.

## User Flow

사용자 또는 시스템이 무엇을 하고, 보고, 받는지 순서대로 설명한다.

## State And Policy Model

상태, 전이, 권한, 검증 규칙, 제품 정책을 설명한다.

## Approved Flow Inventory

| Definition Flow ID | Source IDs | Trigger Or Entry | Actor Or Consumer | Target Outcome | State/Data Responsibility | Failure Or Empty Behavior | Boundary Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DFLOW-001 | REQ-001, SP-001, INTENT-001 | 승인된 flow를 시작하는 사용자 또는 시스템 진입점. | 사용자, 관리자, 시스템 consumer 중 해당 주체. | 사용자가 보거나 시스템 consumer가 확인하는 완료 결과. | 생성, 수정, 조회, 캐시 갱신, no-op, 외부 책임 등 service-level 책임. | 검증 실패, 빈 상태, 권한 실패, 외부 consumer 책임 등 flow별 실패/빈 상태. | in-scope |

## Policy Rules

| Rule ID | Trigger Or Condition | Policy | User/System Response | State/Data Responsibility | Failure/Recovery Behavior | Source Requirement IDs |
| --- | --- | --- | --- | --- | --- | --- |
| SP-001 | 관련 조건이 발생한다. | 서비스는 승인된 동작을 따른다. | 사용자 또는 시스템은 계획된 응답을 받는다. | 상태 또는 데이터 책임을 설명한다. | 복구 동작을 설명한다. | REQ-001 |

## Integration Flow And Data Responsibilities

동작 이해에 필요한 경우에만 서비스 수준 통합 순서와 데이터 책임을 설명한다.

## Boundaries

포함 범위와 제외 범위의 동작을 설명한다.

## Regression Prevention

bugfix 또는 mixed 요청에서 회귀하면 안 되는 동작을 설명한다.

## Failure And Recovery Behavior

오류, 빈 상태, 권한, 검증 실패, 복구 동작을 설명한다.
```
