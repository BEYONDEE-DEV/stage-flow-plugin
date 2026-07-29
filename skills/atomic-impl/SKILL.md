---
name: atomic-impl
description: "Use when the user asks to implement code from requirements through atomic-docs first, invokes atomic-impl, wants requirements written into atomic docs before coding, asks for docs-first implementation, or wants implementation based on approved atomic-docs managed documentation."
---

# Atomic Impl

Turn approved requirements into a small Atomic Docs change basis, implement the code, and leave durable docs describing the realized system.

## Required Flow

1. Read `skills/atomic-docs/SKILL.md` and `references/implementation-flow.md`.
2. Inspect the requirement, relevant source, config, and affected Atoms.
3. Write each active requirement exactly once in the owning Atom's `Changes` section as `[RID:<atom_key>.<lower-kebab-slug>]`.
4. Correct current source-backed ownership in `Boundaries` only when needed. Keep any future boundary change in its RID item until implementation is approved and complete.
5. Run Atomic Docs structural validation and its single semantic review.
6. Present the changed docs paths, RIDs, implementation behavior, and unresolved decisions. Require explicit user approval before code implementation.
7. Implement the approved change using the project source and conventions.
8. Run relevant tests and one implementation review against the approved RIDs, actual diff, and validation results.
9. Present the implementation result and require explicit user approval before final Atomic Docs promotion.
10. Remove completed RIDs, promote durable meaning into `Contracts` or `Boundaries`, refresh `Implementation` and `Sources`, validate, and run the bounded Atomic Docs review.

Do not create operation state, a parallel compliance report, or another trace/control artifact.

## Requirement Rules

- A RID appears exactly once and only in the owning Atom's `Changes`.
- The RID item states the required outcome or invariant clearly enough to implement and review.
- Use `Open Questions` for a decision that still blocks a trustworthy implementation basis. Stop for the user rather than guessing.
- Do not describe unimplemented behavior as current `Implementation`, durable `Contracts`, or established `Boundaries`.
- Code scope is limited to the approved RIDs and necessary supporting changes.
- Do not record out-of-scope implementation as approved product behavior.

## Review Rules

The docs review follows Atomic Docs: one independent semantic reviewer, one correction, and one recheck of the original findings.

The implementation review checks:

- every approved RID has corresponding implementation evidence
- the resulting behavior matches its documented outcome or invariant
- relevant data flow, validation, state changes, side effects, and failure behavior are coherent
- tests or targeted validation cover the material change
- no material out-of-scope behavior was introduced

If implementation review fails, correct the implementation and rerun relevant validation before presenting the result. User approval of the result is still required before final docs promotion.

## Completion

Completed work has no RID left. Durable behavior belongs in `Contracts` or `Boundaries`; current realization and exact source anchors belong in `Implementation` and `Sources`. Report final docs paths, code paths, validation, review results, and remaining `Open Questions`.
