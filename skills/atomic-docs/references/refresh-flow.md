# Refresh Flow

## Responsibility

This reference defines full refresh and targeted docs operations against source code and existing atom files.

## Source Baseline

Freshness is tracked with one source-code commit hash stored in metadata at the documentation submodule root. The baseline metadata is outside individual atom files.

The baseline records the last source-code commit hash used for a confirmed docs refresh. The `atomic-docs` skill should compare `git diff <stored-source-hash>..HEAD` or the equivalent source-root diff to prioritize changed source behavior files.

## Domain Context Discovery

Before assigning changed source behavior to a domain, inspect the context atoms that exist:

- `project/project-goal-atom.md` for project-wide purpose and success criteria
- `project/project-glossary-atom.md` for project-wide terms and domain-scoped terminology
- `common/common-context-atom.md` for shared concepts, policies, and code structures
- `<domain>/<domain>-context-atom.md` for existing domain goals and boundaries

If a new domain, new common atom, or domain move is plausible, include the candidate domain, evidence, affected atom files, and unresolved boundary questions in the change plan before writing docs.

If a domain candidate looks like a broad grouping instead of a durable ownership boundary, do not write it as confirmed structure. Present a split proposal using observed capabilities, workflows, responsibilities, contracts, or policies, and keep unresolved boundary questions in the change plan or `Gaps`.

## Full Refresh

A full refresh is a first-class operation when the user explicitly asks for it.

1. Read the configured docs root and source root.
2. Read the docs-root source commit baseline metadata.
3. Inspect changed source behavior files since the stored source commit hash.
4. Ignore tests, settings, schema, build, and auxiliary files by default unless the user requested auxiliary-file reflection.
5. Inspect project, common, and relevant domain context atoms when they exist.
6. Use source-to-atom seed discovery to find likely domain and atom candidates.
7. Expand affected scope through atomic graph traversal.
8. Stop graph expansion when related atom files no longer create modification candidates.
9. Present a domain-grouped change plan before writing docs.
10. Write confirmed updates only after the change plan is accepted.
11. Update the docs-root source commit baseline metadata after confirmed writes.

## Targeted Docs Operation

Targeted domain or atom work is also a first-class flow. When targeted work overlaps with full-refresh scope, prioritize the current user-requested target. Put adjacent affected scope in follow-up proposals or `Gaps`.

For domain-level work, update the domain context atom when the domain goal, responsibility, included behavior, excluded behavior, adjacent boundary, or common-promotion rule changes. Update `project/project-glossary-atom.md` when source or user intent changes project-wide terms, aliases, forbidden conflations, or domain-scoped terminology.

## Change Plan Requirements

A change plan should group by domain and list:

- source behavior files inspected
- affected atom files
- affected atom sections
- new domains, domain moves, atom splits, atom merges, and split proposals
- project goal, project glossary, common context, or domain context changes
- core business terms that require glossary or domain atom coverage before derived behavior is treated as covered
- parent business terms missing or underdefined in the glossary, including their source evidence and whether they belong in `Gaps`
- inferred `Intent` or `Rules` that require confirmation
- `Current Implementation` changes
- `Planned Changes` reconciliation candidates
- `Gaps`, bug candidates, uncertain mappings, rename/merge proposals, and implemented-plan candidates
- graph path corrections or target-key conflicts
- source-baseline metadata updates and docs-root config writes
- unresolved boundary questions that must be accepted before writing confirmed structure

The accepted change plan defines the only paths and write actions allowed for the current docs operation. Do not write atom files, graph corrections, source-baseline metadata, docs-root config, or docs-submodule structure before that acceptance.

## Inference And Gaps

The skill may draft `Current Implementation`, `Gaps`, and inferred `Intent` or `Rules` from code. Inferred `Intent` and `Rules` remain inferred until confirmed by the user. If observed code conflicts with confirmed intent or rules, do not resolve the conflict silently; preserve it as a gap or bug candidate.
