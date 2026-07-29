# Validation Contract

Run:

```text
python3 <plugin-root>/scripts/validate_atomic_docs.py --root <primary-project-root>
```

The validator checks only deterministic structure:

- exact config version, keys, values, paths, and reachable revisions
- required project goal and conditional glossary shape, including unique non-empty `Term` and `Definition` cells
- Atom frontmatter, unique keys, required heading order, and section content
- valid and resolvable `depends_on`
- exact source-locator syntax, configured source names, path containment, existing files, and no line ranges
- active RID placement, ownership, uniqueness, and syntax
- absence of retired AID/AID-REF syntax

It does not judge semantic usefulness, glossary coverage or definition accuracy, source-wide completeness, security, defects, operational timing, or whether the selected update scope was sufficient. The bounded semantic review owns those judgments. Those limits must not be converted into more persistent state.

Every failure identifies the path, failed field or heading, cause, and recovery action. Correct the docs/config and rerun. Do not bypass a failure with a legacy version, migration, alternate validator, or handwritten exception.
