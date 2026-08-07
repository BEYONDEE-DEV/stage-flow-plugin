# Refresh Flow

## Inspect

`inspect` is read-only. Read config, selected docs, and relevant source. Report stale claims, unresolved questions, relationship issues, and suggested update scope. Do not write configuration, managed docs, or operation state.

## Writing Pass

Apply this pass only within the selected and directly inspected scope. If a natural owner lies
outside that scope, report the relationship and suggested update scope instead of expanding
automatically.

1. When the project goal is selected or materially affected, identify project-level observable outcomes for the intended human or system consumers.
2. For each selected Atom, assign each durable rule to its natural Atom owner without inventing a shared hub.
3. Separate contracts that must survive implementation changes from useful current mechanics.
4. Remove copied generic mechanics while preserving domain-specific consequences and additional conditions.

## Update All

Use `update all` for first creation or a complete replacement:

1. Confirm the accepted storage target and managed write set.
2. Capture stable primary `HEAD` and select its latest first-parent source-impact commit under `docs-root-and-config.md`.
3. Inspect project purpose, intended human or system consumers, project-level observable outcomes, domain vocabulary, durable domains, natural contract owners, and implementation anchors. Build the general glossary from terms a new developer needs to understand the project, including terms owned by only one proposed Atom, under `atomic-document-contract.md`.
4. Write `project-goal.md`, conditional glossary, and the complete Atom set.
5. Validate structure.
6. Run the single semantic review in `reviewer-perspectives.md`.
7. Validate again after any review correction.
8. Recheck source stability, then write the selected source-impact commit to `last_full_source_commit`.
9. Validate the final config and docs state. Restore the previous commit value if this check fails.

An incomplete or failed all-update must not advance the commit.

## Update Changed

Preserve `last_full_source_commit` and capture target primary `HEAD`. Require the previous commit on the target's first-parent history. Before any write, require `<docs-root>/atomic-docs.json` and managed docs to be clean; in `submodule` mode also require the documentation submodule worktree and containing gitlink to be clean. Pre-existing dirty state stops the update rather than joining the current-operation write set.

Walk each first-parent commit after the previous commit and compare it with its first parent. A merge that differs from its first parent on a non-output path is source-impact. Before source-impact selection:

- in repository mode, report and exclude `<docs-root>/atomic-docs.json` when only `last_full_source_commit` changed
- report and exclude paths below `docs_root` and the containing documentation-submodule gitlink from source seeds; inspect their committed path diff or old-to-new submodule commit diff and include those changed docs in bounded semantic reconciliation
- stop when another config field changed; use `update all` or an explicit config update with source inspection

Select the latest first-parent commit with any non-output path as the source-impact target. When only Atomic Docs config/docs/gitlink output remains, validate current config/docs, semantically reconcile committed managed-doc changes, report no primary source impact, and retain the previous commit value. For every changed primary-source file from the source-impact commits:

1. Find Atoms whose exact `Sources` locator names that file. These are seed Atoms.
2. Add each seed's direct `depends_on` targets.
3. Add Atoms that directly name a seed in their own `depends_on`.
4. Inspect the changed file for new responsibility or contracts that existing locators do not cover.

Every changed primary-source file must receive a reliable source-impact classification. A source change may be classified as requiring no managed-doc edit, but an unmapped material responsibility or uncertain impact stops the update rather than advancing the commit.

Update only this bounded set unless the user expands scope. Report:

- changed primary-source files
- seed Atom keys
- direct dependency and reverse-dependent Atom keys
- new or unmapped context found
- boundaries not inspected

This is one-hop impact selection, not proof of complete closure. Auxiliary sources are excluded from the primary diff and inspected only when selected or when a retained claim depends on their exact pinned revision.

Update glossary definitions when the changed source or selected Atoms introduce, change, or retire project vocabulary. Judge coverage only within the inspected changed scope.

After the bounded writing pass, or after recording a source-impact no-doc result:

1. Run structural validation.
2. Run the single semantic review over the selected source, complete managed-docs diff, any no-doc decision, and any committed managed-doc range. Apply the existing one-correction rule.
3. Run structural validation after any correction.
4. Recheck that `HEAD` equals the captured target and tracked primary source outside the exact current-operation config/docs changes is clean.
5. Set `last_full_source_commit` to the latest first-parent source-impact commit, including for a successful no-doc result. Never advance it to trailing config/docs/gitlink-only commits.
6. Validate the final config and docs state.

Stop when the baseline is null, unreachable, or outside the target's first-parent history; any required starting worktree is dirty; tracked primary source outside the current-operation write set is dirty; `HEAD` changes; a material changed file cannot be classified reliably; semantic reconciliation or review does not pass; or validation fails. Restore the previous commit value, validate the recovered state, and report the recovery instead of advancing the commit.

## Update Targeted

Accept explicit Atom keys, domains, source paths, or the project glossary. Inspect their source and only the direct dependencies needed to judge the selected change. Update glossary entries affected by that vocabulary and state the selected and uninspected scope. A targeted update does not advance `last_full_source_commit`.

## Delete Or Merge

Before changing an existing Atom set, show exact lists:

- delete: source `atom_key` values
- merge: source `atom_key` values and exact target `atom_key`

Proceed only after explicit user approval of those keys. Then update `depends_on`, active RID ownership/impact, and source locators. Run validation and semantic review. Git is the recovery mechanism.

## Completion Report

Report changed managed paths, selected source scope, validator result, semantic review result, remaining open questions, and uninspected boundaries. For changed or targeted work, explicitly say that no complete source-wide coverage claim is made.
