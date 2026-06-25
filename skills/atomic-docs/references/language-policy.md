# Language Policy

## Responsibility

This reference defines which natural language the docs skill uses when writing or updating documentation content.

## Default Language Selection

Use this priority order for prose inside managed docs:

1. Use the language explicitly requested by the user for the current docs operation.
2. If the user did not specify a language, use the dominant language already used in the configured documentation submodule.
3. If there is no existing documentation language to infer from, use the current conversation language.

For the current Korean workflow, that means new prose should default to Korean unless the user requests another language or the existing docs submodule clearly uses another dominant language.

## Fixed Terms And Identifiers

Keep these values unchanged even when the surrounding prose is written in another language:

- schema headings such as `Intent`, `Rules`, `Current Implementation`, `Planned Changes`, and `Gaps`
- frontmatter keys such as `graph_edges`, `type`, `target_key`, `target_path`, and `reason`
- config keys such as `docs_root`, `source_root`, and `baseline_metadata_path`
- source-code identifiers, API names, file paths, enum values, commands, and commit hashes
- quoted user text when exact wording matters for intent preservation

## Mixed-Language Handling

- Do not translate code identifiers or schema keys to make prose feel more natural.
- If the existing docs submodule mixes languages, prefer the language used by the target domain or atomic document being edited.
- If a document's language is ambiguous and the choice may affect user review, ask before writing confirmed docs.
- AI-inferred `Intent` or `Rules` must still be marked as inferred in the selected docs language and connected to `Gaps` until confirmed.

## Change Plan Language

Write change plans in the user's current conversation language unless the user asks otherwise. When proposing edits to existing docs in another language, show enough original fixed terms and target headings for the user to recognize the affected atom sections.
