# Validation Contract

## Contents

- [Responsibility](#responsibility)
- [Validator Location And CLI](#validator-location-and-cli)
- [Selection State Shape](#selection-state-shape)
- [Removal And Merge State](#removal-and-merge-state)
- [Phase Checks](#phase-checks)
- [Validation Boundary](#validation-boundary)

## Responsibility

This reference defines the plugin-bundled structural validator. Structural validation catches deterministic format and relationship errors; semantic quality remains the responsibility of criteria, domain, and final reviewers.

## Validator Location And CLI

Run the validator from the installed or source plugin root:

```text
python <plugin-root>/scripts/validate_atomic_docs.py --root <target-project-root> --phase bootstrap
python <plugin-root>/scripts/validate_atomic_docs.py --root <target-project-root> --phase selection --request-id <request-id>
python <plugin-root>/scripts/validate_atomic_docs.py --root <target-project-root> --phase selection --request-id <request-id> --require-actions-final
python <plugin-root>/scripts/validate_atomic_docs.py --root <target-project-root> --phase docs
python <plugin-root>/scripts/validate_atomic_docs.py --root <target-project-root> --phase docs --expect-atom-key <key> [--expect-atom-key <key> ...]
python <plugin-root>/scripts/validate_atomic_docs.py --root <target-project-root> --phase baseline
```

Never search for or invoke `scripts/validate_atomic_docs.py` relative to the target project. The target project contains atomic-docs config and output, not the plugin validator.

The validator is read-only. It exits `0` with `PASS <phase>` and exits `1` with `FAIL <phase>` plus actionable findings. Docs/baseline PASS output includes validated atom and AID totals; it does not create an active/retired AID lifecycle.

Run selection phase after candidate evidence anchors and `write|merge|drop` decisions are recorded but before creating the writer. `--request-id` is required only for selection. Intermediate removal/retry checks omit `--require-actions-final`; the request-bound final check includes it so `removal_pending`, `approved`, `applying`, or `rolling_back` cannot be mistaken for completion. Run docs phase after every bundle writer and before semantic reviewers. Pass every atom key expected from that bundle with repeated `--expect-atom-key`. This scopes strict file/section/AID/edge validation to the active bundle while checking its keys, AID collisions, and graph targets against the whole docs set, so unrelated pre-existing defects do not block the bundle. Run docs phase without expected keys after the accepted queue completes. `--expect-atom-key` is valid only for docs.

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

## Removal And Merge State

These fields are optional for compatibility. Their absence keeps an existing operation structurally valid but grants no automatic removal/merge authority.

`operation_created_artifacts` contains one record per output created by this operation: `candidate_id`, `atom_key`, managed-docs-relative `path`, `created_attempt_id`, lowercase 64-hex `last_operation_sha256`, and `status: present|removal_pending|removed`. The path must stay below its accepted candidate domain and be absent from the fixed managed-docs revision corresponding to `source_commit_observed` plus the current HEAD/index. For submodule storage, resolve the gitlink commit recorded at `source_commit_observed`; a path present there is pre-existing even if later HEAD removes it. `present` requires the path and hash to match. Before deletion, `removal_pending` adds artifact `rollback_path`, `state_rollback_path`, and `state_rollback_sha256`; it accepts either the unchanged managed path or its expected absence for crash-safe resume. `removed` requires managed-path absence. Both removal states retain rollback files through operation close, require candidate `drop` plus a backticked candidate ID in inventory, and forbid selected routes or incoming graph edges using the key.

`approved_existing_actions` is immutable. Each record has `action_id`, `action: delete|merge`, `source`, optional merge `target`, `reference_owners`, and `approved_action_fingerprint`. Every member has `atom_key`, managed-docs-relative `path`, and `preimage_sha256`; member paths are unique and stay below accepted domain paths. A delete omits `target`, while a merge requires it. Existing-action members and `operation_created_artifacts` must have disjoint paths and keys, so neither provenance contract can impersonate the other. Fingerprint the record without `approved_action_fingerprint`: sort `reference_owners` by path, serialize UTF-8 JSON with sorted keys and separators `,` and `:`, then SHA-256 the bytes.

`action_execution` has exactly one record per approved action: matching `action_id` and fingerprint, `status: approved|applying|rolling_back|applied`, and one runtime member for every immutable member. Each member repeats `role: source|target|reference_owner`, `atom_key`, and `path`, then records `expected_state: present|absent`; present requires `last_operation_sha256`, absent forbids it. Every non-`approved` state retains each member `rollback_path` plus `state_rollback_path` and `state_rollback_sha256`. The complete state snapshot must retain core scope/revision/selection/queue/risk fields, exactly match every unrelated top-level owner's key presence and value, keep unique candidate/artifact/action identities and unchanged artifact provenance/action manifests/execution members, provide a restorable version-1 routing contract, and obey the same status-specific allowed/forbidden keys for the pre-mutation `present` artifact or `approved` execution; a forbidden key is invalid even when its JSON value is `null`, and current-created snapshots also match `created_attempt_id`. Every member rollback matches its preimage. Runtime membership never expands the approved manifest.

At `approved`, every member is present at its preimage hash. Every later present/absent expectation must match disk. At `applied`, delete requires source absence and every reference owner at its postimage; merge additionally requires the approved target identity and postimage. Both require no selected route or graph edge to the removed source. A mismatch, recreated source, unapproved incoming owner, bad rollback copy/snapshot, changed fingerprint, or accepted-scope violation is structural FAIL; the validator never repairs it. Only `--require-actions-final` requires every current-operation removal to be `removed` and every existing action to be `applied`.

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
- optional operation-created and approved-existing-action state satisfies the removal/merge contract, including accepted scope, exclusive source provenance, current hashes, immutable membership, runtime progress, member/state rollback copies, source/target identity, retained drop inventory, selected-route closure, and incoming graph closure

Selection validation is the request-bound structural postcondition when a valid drop/delete leaves no managed Atom. If managed Atoms remain after an applied action, run unscoped docs validation too.

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
- whether a delete/merge action was actually approved by the user; the validator checks only the recorded immutable fingerprint and runtime state

Those decisions remain reviewer-owned. A structural PASS never replaces required subagent review.
