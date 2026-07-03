# Stageflow 사용법

설치는 [README.md](./README.md)를 참고하세요. 설치나 업데이트 후에는 새 Codex 스레드에서 사용하세요.

## 핵심 규칙

- 새 Stageflow 작업은 요청에 `Stageflow`, `stageflow`, `stage-flow`, `.stageflow` 중 하나를 반드시 포함해야 합니다.
- `이 작업 계획 세워줘`처럼 일반적으로 말하면 Stageflow가 자동 시작된다고 가정하면 안 됩니다.
- `atomic-docs`를 쓰려면 요청에 `atomic-docs`를 명시하세요.

## Stageflow 시작

```text
Stageflow로 이 변경 작업 계획 세워줘.
```

```text
Use Stageflow to plan this change before coding.
```

Stageflow는 다음 순서로 진행됩니다.

1. `definition`: 요구사항 정의
2. `implementation-plan`: 구현 계획
3. `implementation`: 구현 및 완료 검증

각 단계는 리뷰와 사용자 승인이 필요합니다.

## 단계별 확인

요청별 파일은 `.stageflow/requests/<request-id>/` 아래에 생성됩니다.

### 1. Definition

사용자가 할 일:

- Codex가 묻는 요구사항 질문에 답합니다.
- 요구사항이 충분하면 `질문은 여기까지 하고 구현 계획으로 넘어가자`처럼 말합니다.
- 리뷰가 통과하면 정의 내용을 보고 승인합니다.

주로 볼 파일:

```text
.stageflow/requests/<request-id>/01-definition/definition.md
```

### 2. Implementation Plan

사용자가 할 일:

- 구현 계획이 정의와 맞는지 봅니다.
- 빠진 작업, 잘못된 범위, 테스트 부족이 있으면 수정 요청합니다.
- 문제가 없으면 승인합니다.

주로 볼 파일:

```text
.stageflow/requests/<request-id>/02-implementation-plan/implementation-plan.md
```

### 3. Implementation

사용자가 할 일:

- 구현 결과와 검증 근거를 봅니다.
- 계획대로 완료됐는지 확인합니다.
- 문제가 없으면 완료 승인합니다.

주로 볼 파일:

```text
.stageflow/requests/<request-id>/03-implementation/implementation.md
```

## 질문 답변

정의 단계에서 선택지가 나오면 번호나 옵션으로 답하면 됩니다.

```text
1번은 Option 2, 2번은 Option 1로 해줘.
```

질문을 끝내고 다음 단계 준비를 시키려면 명시적으로 말합니다.

```text
질문은 여기까지 하고 구현 계획으로 넘어가자.
```

이 말은 최종 승인이 아니라 전환 리스크 점검 시작 신호입니다.

## 승인

승인할 때는 명확하게 말합니다.

```text
승인해. 다음 단계로 진행해줘.
```

```text
approve
```

## 기존 작업 이어가기

```text
현재 Stageflow 작업 이어서 진행해줘.
```

```text
Resume the current Stageflow request.
```

## Atomic Docs

새 문서화:

```text
atomic-docs로 이 프로젝트 문서화를 시작해줘.
```

코드 변경 반영:

```text
atomic-docs로 최근 코드 변경사항을 문서에 반영해줘.
```

의도/구현/갭 점검:

```text
atomic-docs로 현재 구현 의도와 갭을 점검해줘.
```

## 생성 위치

```text
.stageflow/requests/<request-id>/
.stageflow/atomic-docs.json
```
