# Validation Contract

## Responsibility

This reference defines the plugin-bundled structural validator. Structural validation catches deterministic format and relationship errors; semantic quality remains the responsibility of criteria, domain, and final reviewers.

## Validator Location And CLI

Run the validator from the installed or source plugin root:

```text
python <plugin-root>/scripts/validate_atomic_docs.py --root <target-project-root> --phase bootstrap
python <plugin-root>/scripts/validate_atomic_docs.py --root <target-project-root> --phase docs
python <plugin-root>/scripts/validate_atomic_docs.py --root <target-project-root> --phase baseline
```

Never search for or invoke `scripts/validate_atomic_docs.py` relative to the target project. The target project contains atomic-docs config and output, not the plugin validator.

The validator is read-only. It exits `0` with `PASS <phase>` and exits `1` with `FAIL <phase>` plus actionable findings.

## Phase Checks

`bootstrap` checks:

- `.stageflow/atomic-docs.json` exists and is valid JSON
- required config keys exist
- `storage_mode` is `repository` or `submodule`
- `docs_root`, `source_root`, and `baseline_metadata_path` are relative paths that do not escape their configured roots
- the managed docs root and `project/atomization-criteria.md` exist

`docs` includes bootstrap checks and checks every `*-atom.md` under the managed docs root:

- frontmatter exists and contains one lower-kebab-case `atom_key`
- `atom_key` values are globally unique
- required atom sections exist: `Intent`, `Rules`, `Current Implementation`, `Planned Changes`, and `Gaps`
- every discovered AID has valid `[AID:<key>.<section-code>.<NNN>]` shape and is globally unique
- an AID's section code matches the required section containing it
- a preserved AID may retain a historical key prefix after its meaning moves to another atom
- every graph edge has `type`, `target_key`, `target_path`, and `reason`
- `target_key` resolves to exactly one atom and `target_path` resolves to that same atom

`baseline` includes docs checks and requires valid baseline metadata at the configured path:

```json
{
  "version": "1",
  "source_commit": "<40-or-64-character-git-hash>",
  "coverage": "project-wide"
}
```

The baseline commit must resolve in the configured `source_root`. `coverage` values for domains, features, atoms, targeted work, or partial scope are invalid.

## Validation Boundary

The validator must not decide:

- whether a domain boundary is meaningful
- whether source discovery is complete
- whether natural-language behavior is sufficiently detailed
- whether development decisions are complete enough for the accepted implementation or review scope
- whether user intent or a judgment label is correct
- whether a global baseline is semantically authorized by reviewer PASS results

Those decisions remain reviewer-owned. A structural PASS never replaces required subagent review.
