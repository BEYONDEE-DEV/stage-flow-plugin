# Language Policy

## Responsibility

This reference defines which natural language the `atomic-docs` skill uses when writing or updating managed documentation, change plans, review notes, and user-facing docs operation summaries while preserving fixed schema terms.

## Default Language Selection

Use this priority order for prose inside managed docs and docs change plans:

1. Use the language explicitly requested by the user for the current docs operation.
2. If the user did not specify a language, use the dominant language already used in the configured managed docs root.
3. If there is no existing documentation language to infer from, use the current conversation language.

For the current Korean workflow, managed docs prose, docs change plans, review notes, and user-facing operation summaries should default to Korean unless the user requests another language or the existing managed docs root clearly uses another dominant language.

## Fixed Terms And Identifiers

Keep these values unchanged even when the surrounding prose is written in another language:

- schema headings such as `Intent`, `Rules`, `Current Implementation`, `Planned Changes`, and `Gaps`
- frontmatter keys such as `atom_key`, `graph_edges`, `type`, `target_key`, `target_path`, and `reason`
- config keys such as `storage_mode`, `docs_root`, `source_root`, and `baseline_metadata_path`
- source-code identifiers, API names, file paths, enum values, commands, package names, and commit hashes
- atom line ID tokens such as `[AID:paid-order-processing.impl.003]`
- option labels, status/control values, or workflow terms required by a connected validator or Stageflow artifact
- quoted user text when exact wording matters for intent preservation

## User-Facing Terminology Policy

For user-facing docs operation summaries, approval requests, first-step bootstrap summaries, and change plans, use plain user language first. Keep schema keys, frontmatter keys, file paths, AID values, judgment labels, and option labels unchanged, but do not present them to the user as unexplained standalone lines.

Use the order "쉬운 설명 + 원문 식별자" when an internal identifier matters. For Korean interactions, apply these mappings:

- `storage_mode`: `문서 저장 방식`
- `repository`: `현재 프로젝트 안의 폴더에 저장`
- `submodule`: `별도 문서 저장소/submodule에 저장`
- `docs_root` and managed docs root: `문서 저장 위치`
- `.stageflow/atomic-docs.json`: `atomic docs 설정 파일`
- `project/atomization-criteria.md`: `문서 작성 기준 초안`
- `bootstrap`: `첫 설정 단계` or `처음 준비 단계`

Avoid first responses that consist only of raw config summaries such as `storage mode: repository`, `docs root: docs`, or `작성/갱신: .stageflow/atomic-docs.json`. Prefer a short natural-language explanation first, then put the exact key, option, or path in backticks when it helps the user identify the file or setting.

## Template And Filler Prose

Starter examples are scaffolding, not approved docs content. Replace generic English filler such as `Describe...`, `No pending...`, or placeholder row prose with request-specific prose in the selected language before asking for review or write approval.

Reviewers should treat leftover English filler text as a blocking issue when the selected managed-docs or change-plan language is not English.

## Korean-First Template Policy

When the selected managed-docs language is Korean, use Korean-first writing templates, Korean subheadings, Korean checklist wording, and Korean review criteria for all prose scaffolding. Do not draft an English skeleton first and then translate it into Korean.

Keep fixed schema headings, frontmatter keys, controlled judgment labels, and source identifiers unchanged, but write the structure under those headings in Korean. For example, keep `Current Implementation` as the atom section heading, then use Korean subheadings such as `### 동작 흐름`, `### 관찰된 판단 규칙`, `### 상태와 저장 효과`, `### 외부 연동과 이벤트`, `### 실패와 복구 동작`, and `### Source Evidence` when those subsections help explain the behavior.

Writer and reviewer checklists for Korean docs must be written directly in Korean. A draft that reads like translated English, preserves English placeholder prose, or uses an English-first scaffold for Korean managed docs is not ready for user review.

For Korean managed docs, criteria documents must also use Korean visible section headings and field labels. Do not use English visible labels such as `Purpose`, `Approval Status`, `Managed Docs Root And Scope`, `Atomization Perspectives`, `Atom candidate criteria`, `Source evidence only criteria`, or `Unresolved questions` unless the user explicitly asks for English. Preserve only fixed atom section headings, frontmatter keys, controlled judgment labels, AID tokens, and source identifiers.

## No Example Leakage

Reference prose that illustrates how the skill works is not managed docs content. Do not copy reference example wording into criteria documents, atom drafts, `Gaps`, review findings, or change plans.

When a docs item needs a concrete phrase, write it from the target project's user wording, source identifiers, inspected behavior, or approved workflow evidence. If that evidence is missing, record a confirmation-needed gap instead of borrowing wording from a skill reference.

Controlled judgment labels, fixed headings, schema keys, `atom_key` values, AID tokens, and source-code identifiers may be reused exactly. Explanatory prose from references must be rewritten from target-project evidence.

## Mixed-Language Handling

- Do not translate code identifiers or schema keys to make prose feel more natural.
- Do not translate or localize AID tokens. Korean docs must preserve `[AID:...]` exactly.
- If the existing managed docs root mixes languages, prefer the language used by the target domain or atomic document being edited.
- If a document's language is ambiguous and the choice may affect user review, ask before writing confirmed docs.
- AI-inferred `Intent` or `Rules` must still be marked as inferred in the selected docs language and connected to `Gaps` until confirmed.

## Change Plan Language

Write change plans in the selected language from this policy unless the user asks otherwise. When proposing edits to existing docs in another language, show enough original fixed terms and target headings for the user to recognize the affected atom sections. The change plan and managed docs prose should use the user/artifact language, while fixed headings and identifiers remain unchanged.
