# Validation Contract

Run:

```text
python3 <plugin-root>/scripts/validate_atomic_docs.py --root <primary-project-root>
python3 <plugin-root>/scripts/validate_atomic_docs.py --root <primary-project-root> --config <docs-root>/atomic-docs.json
```

`--config` is optional and is relative to the primary root unless absolute. Before parsing JSON, the validator searches the contained primary project for the exact file name `atomic-docs.json`, excluding Git internals. Exactly one regular-file candidate must exist even when `--config` is supplied, and the explicit path must select that candidate. The candidate must not be a symbolic link, must be inside the primary project, must use the exact file name, must avoid the retired `.stageflow` location, and must have a parent equal to resolved `docs_root`. A submodule-root invocation must direct the user back to the primary project root.

The validator checks only deterministic structure:

- unique config discovery, exact config version, keys, values, docs-root placement, paths, and reachable revisions
- required project goal and conditional glossary shape, including unique non-empty `Term` and `Definition` cells
- Atom frontmatter, unique keys, required heading order, and section content
- valid and resolvable `depends_on`
- exact source-locator syntax, configured source names, path containment, existing files, and no line ranges
- active RID placement, ownership, uniqueness, and syntax
- absence of retired AID/AID-REF syntax

It does not judge semantic usefulness, glossary coverage or definition accuracy, source-wide completeness, security, defects, operational timing, or whether the selected update scope was sufficient. The bounded semantic review owns those judgments. Those limits must not be converted into more persistent state.

Every failure identifies the path, failed field or heading, cause, and recovery action. Correct the docs/config and rerun. Do not bypass a failure with a legacy version, migration, alternate validator, or handwritten exception.
