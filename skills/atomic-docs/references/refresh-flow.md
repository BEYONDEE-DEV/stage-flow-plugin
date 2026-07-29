# Refresh Flow

## Inspect

`inspect` is read-only. Read config, selected docs, and relevant source. Report stale claims, unresolved questions, relationship issues, and suggested update scope. Do not write configuration, managed docs, or operation state.

## Update All

Use `update all` for first creation or a complete replacement:

1. Confirm the accepted storage target and managed write set.
2. Capture a stable primary-source commit under `docs-root-and-config.md`.
3. Inspect project purpose, user roles, domain vocabulary, durable domains, contracts, and implementation anchors. Build the general glossary from terms a new developer needs to understand the project, including terms owned by only one proposed Atom, under `atomic-document-contract.md`.
4. Write `project-goal.md`, conditional glossary, and the complete Atom set.
5. Validate structure.
6. Run the single semantic review in `reviewer-perspectives.md`.
7. Validate again after any review correction.
8. Recheck source stability, then update `last_full_source_commit`.
9. Validate the final config and docs state. Restore the previous commit value if this check fails.

An incomplete or failed all-update must not advance the commit.

## Update Changed

Use `git diff --name-only <last_full_source_commit>..HEAD` for the primary source. For each changed file:

1. Find Atoms whose exact `Sources` locator names that file. These are seed Atoms.
2. Add each seed's direct `depends_on` targets.
3. Add Atoms that directly name a seed in their own `depends_on`.
4. Inspect the changed file for new responsibility or contracts that existing locators do not cover.

Update only this bounded set unless the user expands scope. Report:

- changed primary-source files
- seed Atom keys
- direct dependency and reverse-dependent Atom keys
- new or unmapped context found
- boundaries not inspected

This is one-hop impact selection, not proof of complete closure. Auxiliary sources are excluded from the primary diff and inspected only when selected or when a retained claim depends on their exact pinned revision.

Update glossary definitions when the changed source or selected Atoms introduce, change, or retire project vocabulary. Judge coverage only within the inspected changed scope.

Stop and recommend `update all` or explicit `update targeted` when the baseline is null or unreachable, the primary tracked source is dirty, `HEAD` changes during the operation, or changed files cannot be mapped reliably.

## Update Targeted

Accept explicit Atom keys, domains, source paths, or the project glossary. Inspect their source and only the direct dependencies needed to judge the selected change. Update glossary entries affected by that vocabulary and state the selected and uninspected scope. A targeted update does not advance `last_full_source_commit`.

## Delete Or Merge

Before changing an existing Atom set, show exact lists:

- delete: source `atom_key` values
- merge: source `atom_key` values and exact target `atom_key`

Proceed only after explicit user approval of those keys. Then update `depends_on`, active RID ownership/impact, and source locators. Run validation and semantic review. Git is the recovery mechanism.

## Completion Report

Report changed managed paths, selected source scope, validator result, semantic review result, remaining open questions, and uninspected boundaries. For changed or targeted work, explicitly say that no complete source-wide coverage claim is made.
