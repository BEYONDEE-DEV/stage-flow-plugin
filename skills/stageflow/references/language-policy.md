# Stageflow Language Policy

## Responsibility

This reference defines which natural language Stageflow uses in request artifacts, user-facing questions, approvals, review evidence, and stage summaries while preserving validator-required structure.

## Default Language Selection

Use this priority order for prose inside Stageflow artifacts and user-facing workflow messages:

1. Use the language explicitly requested by the user for the current workflow request.
2. If the user did not specify a language, use the dominant language already used in the active request artifacts.
3. If no active artifact language can be inferred, use the current conversation language.

For the current Korean workflow, new artifact prose, pending clarification questions, proposal option descriptions, review evidence, change plans, and completion summaries should default to Korean unless the user asks for another language or the existing request artifact clearly uses another dominant language.

## Fixed Terms And Identifiers

Keep these values unchanged even when surrounding prose is written in another language:

- validator-required headings and table columns such as `## User Goal`, `## Pending Clarifications`, `Question Scope`, and `Why This Matters`
- schema keys, status values, rule IDs, artifact filenames, and stage folder names
- source-code identifiers, API names, file paths, enum values, commands, package names, and commit hashes
- option labels such as `Option 1:` and `Option 2:` when validator checks require those labels
- quoted user text when exact wording matters for intent preservation

## Template Prose

Starter templates are scaffolding, not approved content. Replace filler such as "Describe...", "No pending clarification.", "No completed clarification yet.", "One concrete requirement.", or "Record the actual work completed." with request-specific prose in the selected language before review or approval.

Reviewers should treat leftover English filler text as a blocking issue when the selected artifact language is not English.

## Mixed-Language Handling

- Do not translate code identifiers or schema terms to make prose feel more natural.
- If a request artifact mixes languages, prefer the language used in the latest user answers and newest artifact prose.
- If the language choice is ambiguous and affects user review, ask before writing confirmed Stageflow prose.
- Review notes and checklist evidence should use the selected artifact language, except for fixed rule IDs, file paths, command names, and quoted source text.
