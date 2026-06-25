# Atomic Document Contract

## Responsibility

This reference defines the managed documentation shape inside the configured documentation submodule.

## Path Contract

Every atomic target uses this exact organization:

```text
<doc-root>/<domain>/<atomic-target>/atomic.md
```

- `<doc-root>` is the confirmed documentation submodule root.
- `<domain>` is the first-level domain folder below the docs root.
- `<atomic-target>` is a folder slug for one user-visible behavior, policy, rule, state, plan, or gap boundary.
- `atomic.md` is the only required document file for that atomic target.
- The atomic target folder slug creates the default `target_key` and must be globally unique across the docs set.

## Required `atomic.md` Sections

Each `atomic.md` must preserve these sections:

- `Intent`
- `Rules`
- `Current Implementation`
- `Planned Changes`
- `Gaps`

`Intent` and `Rules` describe confirmed user intent only when the user or approved workflow has confirmed them. AI-written intent or rules must be marked as inferred until confirmed and must be linked to `Gaps`.

`Current Implementation` records source-observed implementation facts. `Planned Changes` records future intended work that is not yet confirmed as implemented. `Gaps` records mismatches, uncertain inference, bug candidates, missing intent, implemented-plan candidates, rename/merge candidates, and confirmation-needed boundaries.

## Forbidden Shapes

- Do not split state into type folders such as `current-state/`, `future-plan/`, or `gap/`.
- Do not put per-atomic freshness/status fields inside `atomic.md`.
- Do not store per-file commit status in the atomic document.
- Do not collapse `Intent`, `Rules`, `Current Implementation`, `Planned Changes`, and `Gaps` into one undifferentiated narrative.
- Do not present AI inference as confirmed user intent.

## Atomicity Policy

A document is too broad when it covers unrelated behaviors, policies, rules, states, planned changes, or gap boundaries. Split or propose a split before writing confirmed docs. If the split is ambiguous, keep candidates in the change plan or `Gaps` and ask the user.
