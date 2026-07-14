# Validation Contract

## Contents

- [Responsibility](#responsibility)
- [Validator Location And CLI](#validator-location-and-cli)
- [Selection State Shape](#selection-state-shape)
- [Phase Checks](#phase-checks)
- [Validation Boundary](#validation-boundary)

## Responsibility

This reference defines the plugin-bundled structural validator. Structural validation catches deterministic format and relationship errors; semantic quality remains the responsibility of criteria, domain, and final reviewers.

## Validator Location And CLI

Run the validator from the installed or source plugin root:

```text
python <plugin-root>/scripts/validate_atomic_docs.py --root <target-project-root> --phase bootstrap
python <plugin-root>/scripts/validate_atomic_docs.py --root <target-project-root> --phase selection --request-id <request-id>
python <plugin-root>/scripts/validate_atomic_docs.py --root <target-project-root> --phase docs
python <plugin-root>/scripts/validate_atomic_docs.py --root <target-project-root> --phase docs --expect-atom-key <key> [--expect-atom-key <key> ...]
python <plugin-root>/scripts/validate_atomic_docs.py --root <target-project-root> --phase baseline
```

Never search for or invoke `scripts/validate_atomic_docs.py` relative to the target project. The target project contains atomic-docs config and output, not the plugin validator.

The validator is read-only. It exits `0` with `PASS <phase>` and exits `1` with `FAIL <phase>` plus actionable findings. Docs/baseline PASS output includes validated atom and AID totals; it does not create an active/retired AID lifecycle.

Run selection phase after candidate evidence anchors and `write|merge|drop` decisions are recorded but before creating the writer. `--request-id` is required only for selection. Run docs phase after every bundle writer and before semantic reviewers. Pass every atom key expected from that bundle with repeated `--expect-atom-key`. This scopes strict file/section/AID/edge validation to the active bundle while checking its keys, AID collisions, and graph targets against the whole docs set, so unrelated pre-existing defects do not block the bundle. Run docs phase without expected keys after the accepted queue completes. `--expect-atom-key` is valid only for docs.

## Selection State Shape

New operations use this version-1 machine shape. `domain` is the exact approved tentative domain path, while `candidate` is its user-language display description.

```json
{
  "accepted_scope": ["domain/path"],
  "source_commit_observed": "<40-or-64-character-git-hash>",
  "context_selection": {
    "version": "1",
    "candidates": [
      {
        "candidate_id": "domain-context",
        "domain": "domain/path",
        "candidate": "도메인 맥락",
        "disposition": "write",
        "selection_basis": "변경 전에 소유 경계를 알아야 한다.",
        "candidate_atom_keys": ["domain-context"]
      }
    ]
  },
  "bundle_queue": [
    {"domain": "domain/path", "expected_atom_keys": ["domain-context"]}
  ],
  "risk_triggers": [
    {
      "candidate_id": "domain-context",
      "atom_key": "domain-context",
      "triggers": ["shared policy contract"],
      "basis": "선택된 공유 계약이 변경 영향에 중요하다."
    }
  ]
}
```

A `merge` candidate replaces `candidate_atom_keys` with `merge_target_atom_key`; a `drop` candidate has neither. Candidate IDs are unique within the operation. More than one candidate contract may route risk to the same Atom key.

Use this compact evidence projection beside state:

```text
source_commit_observed: `<hash>`

## <candidate_id>
- `<source locator>` why this location matters to selection
```

The source revision and every candidate section must be present. The validator checks only this shape, locator presence, and references; reviewers judge locator authority, relevance, and selection quality.

## Phase Checks

`bootstrap` checks:

- `.stageflow/atomic-docs.json` exists, is valid JSON, and has no duplicate object keys
- required config keys exist
- `storage_mode` is `repository` or `submodule`
- `docs_root`, `source_root`, and `baseline_metadata_path` are relative paths that do not escape their configured roots
- the managed docs root and `project/atomization-criteria.md` exist

`selection` includes bootstrap checks and reads the explicit operation request under `.stageflow/atomic-docs/requests/<request-id>/`:

- `inventory.md`, `evidence.md`, and `work-state.json` exist
- version 1, a reachable `source_commit_observed`, non-empty accepted scope, and candidate/evidence structures are well formed without duplicate JSON keys
- every candidate has a unique ID, exact accepted domain path, `write|merge|drop`, non-empty selection basis, and a locator/relevance evidence section
- evidence revision, candidate headings, and locator rows use constrained plain Markdown: no tab characters, fenced or indented code (including inside blockquote or list containers), multiline inline code, or raw HTML-like syntax
- `write` owns valid planned Atom keys, `merge` resolves to a `write` key, and `drop` creates no key
- bundle expected keys equal the `write` keys and stay under each key owner's approved domain
- every risk trigger resolves its candidate and output/merge target, names at least one trigger, and has a non-empty selected-contract basis

Selection validation applies to newly created version-1 operations. A legacy active request without this version continues its existing unversioned state, queue, and in-scope correction/review rules without invoking selection validation or adding version-1 fields. It does not claim version-1 guarantees; scope expansion still follows its normal approval and Goal boundary. Bootstrap/docs/baseline remain compatible without selection fields.

`docs` includes bootstrap checks. Without `--expect-atom-key`, it checks every `*-atom.md` under the managed docs root. With expected keys, it strictly checks those atoms and their references into the global identity/AID/graph index:

- frontmatter is valid standard YAML with no duplicate mapping keys and contains one lower-kebab-case `atom_key`
- `atom_key` values are globally unique
- required atom sections exist exactly once: `Intent`, `Outcomes`, `Boundaries`, `Rules`, `Current Implementation`, `Planned Changes`, and `Gaps`
- every discovered AID has valid `[AID:<key>.<section-code>.<NNN>]` shape and is globally unique
- an AID's section code matches the required section containing it
- a preserved AID may retain a historical key prefix after its meaning moves to another atom
- every graph edge has `type`, `target_key`, `target_path`, and `reason`
- `target_key` resolves to exactly one atom and `target_path` resolves to that same atom
- every `--expect-atom-key` resolves to a real atom

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
- whether source exploration found the useful context candidates
- whether a candidate's `write|merge|drop` selection or stated basis is semantically correct
- whether an evidence index is concise enough or a source detail has durable value
- whether a selected candidate semantically requires a risk trigger; the development-quality reviewer checks completeness even when the trigger list is empty
- whether natural-language implementation context is accurate or useful
- whether an important owner, shared/external contract, or non-obvious constraint is missing
- whether an Atomic Impl/compliance requirement is complete enough for its approved implementation scope
- whether user intent or a judgment label is correct
- whether a global baseline is semantically authorized by reviewer PASS results

Those decisions remain reviewer-owned. A structural PASS never replaces required subagent review.
