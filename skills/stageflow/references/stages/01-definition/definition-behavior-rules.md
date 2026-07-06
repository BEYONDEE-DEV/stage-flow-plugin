# Definition Behavior And Intent Rules

This file owns definition-stage responsibility, behavior modeling, intent fidelity, scope narrowing, and approved flow extraction. `definition-writing-and-review-rules.md` remains the router and Rule ID checklist source.

## Stage Responsibility

The definition stage combines requirements and service behavior into one approved artifact. It captures the user's goal, purpose and intent, current problems, outcomes, constraints, decisions, requirements, acceptance criteria, normal behavior model, policy rules, boundaries, regression prevention, and failure recovery before implementation planning begins.

The definition also owns the approved flow inventory. It must turn the user's development intent into `DFLOW-*` rows so implementation planning does not have to rediscover or guess major user, system, policy, integration, empty-state, failure, and boundary flows from prose.

The definition may include technical constraints when supplied by the user or discovered through project inspection, but it must not assign code edits, TypeScript interfaces, file changes, or implementation work.

## Request Type Profiles

Record request shape as profile tags, not as a single exclusive type. Use `Primary` and optional `Secondary` values such as `feature`, `bugfix`, `feature-adjustment`, `refactor`, `docs`, or `tooling`.

- Feature-heavy requests emphasize desired outcomes, success criteria, normal behavior, user flow, and service policies.
- Bugfix-heavy requests emphasize current problems, expected-versus-actual behavior, corrected normal behavior, regression prevention, and validation needs.
- Mixed requests must include both desired outcomes and current problems, then connect them through requirements and service policy rules.

## Late Feedback And Redefinition

If implementation feedback shows that the approved definition is wrong, return to the definition stage and update only the affected definition content. Record the correction in `## Resolved Decisions`, update the affected `## Requirements`, `## Policy Rules`, `## Acceptance Criteria`, boundaries, or data responsibilities, and preserve later-stage artifacts as reference material until their impact is judged.

Do not automatically invalidate the implementation plan or implementation record. First decide whether each downstream work item still matches the revised definition, needs a partial update, needs a full rewrite, or belongs in a new request. Definition revisions must make that decision possible by clearly identifying which requirements or policy rules changed.

## Normal Behavior Transformation

The definition must transform requirements into behavior, not repeat requirement rows under a new heading. It should read like the service's approved operating model: what users do, what the system accepts or rejects, what state changes, what policies apply, what happens on failure, and what must not regress.

For bugfix or mixed requests, every material `Current Problems` row must appear as a corrected normal behavior, a regression prevention condition, or both. If the definition cannot explain how the problem is resolved, the stage is not ready.

## Intent Fidelity Guard

Read `references/intent-fidelity.md` when user wording could be narrowed into UX, route, screen, state, data, API, or persistence behavior. Definition must preserve user meaning in `## Intent Fidelity` before expanding it into requirements, acceptance criteria, user flow, policy rules, failure recovery, or boundaries.

## Scope Narrowing Evidence

Scope narrowing is any definition move that takes a broader user goal or service behavior and records a smaller included behavior set, an excluded adjacent behavior, a read-only/manual/future boundary, or an implementation-plan constraint that would prevent a plausible interpretation from being implemented. This is a semantic comparison, not a literal keyword rule: do not decompose a phrase only because a specific word appears.

When definition narrows scope, `## Boundaries` must cite an ID-bearing source from `## Requirements`, `## Policy Rules`, `## Resolved Decisions`, or `## Intent Fidelity`, or the narrowing must be recorded directly in one of those source tables. Acceptable evidence includes a user answer, a discovered system constraint reflected through a definition source, an approved requirement, or an approved policy rule. If the source is not settled, keep an active `## Pending Clarifications` row or generate a transition-risk case before approval.

Do not use a broad technical or operational assumption as the only reason to exclude behavior. For example, a statement that initial data is manually registered does not by itself prove that all future lifecycle management is out of scope; the definition must show whether that exclusion was user-approved, constrained by the current system, or still pending.

## Flow Extraction Checklist

Build `## Approved Flow Inventory` by scanning every approved definition section that can imply a user, system, policy, integration, boundary, failure, or empty-state flow. Extract `DFLOW-*` candidates from:

- `## Desired Outcomes`: each distinct success signal that needs a trigger and observable completion.
- `## Current Problems`: each corrected problem flow and regression prevention path.
- `## User Flow`: each actor-visible or consumer-visible path.
- `## Policy Rules`: each `SP-*` trigger, response, state/data responsibility, and failure/recovery behavior.
- `## Integration Flow And Data Responsibilities`: each producer/consumer handoff or external boundary.
- `## Boundaries`: each explicit out-of-scope or external-boundary behavior that implementation planning might otherwise implement or ignore.
- `## Failure And Recovery Behavior`: each validation failure, empty state, permission failure, recovery, or no-op path that changes completion semantics.

Every concrete `REQ-*` and `SP-*` row must be included in at least one `Approved Flow Inventory.Source IDs` cell. If an already approved `REQ-*` or `SP-*` clearly implies a missing `DFLOW-*`, repair the definition artifact by adding or revising the flow inventory row. Do not turn that omission into a transition-risk question unless the underlying requirement or policy itself is missing, conflicting, or ambiguous.

## Approved Flow Inventory

Record each major approved flow once as `DFLOW-*`. A flow candidate exists when a distinct trigger or entry has its own actor/consumer, target outcome, state/data responsibility, failure/empty behavior, integration responsibility, or boundary status. Include out-of-scope and external-boundary flows when they are important enough that implementation planning might otherwise accidentally implement, ignore, or reinterpret them.

Use `Boundary Status` values exactly: `in-scope`, `out-of-scope-by-definition`, or `external-boundary-by-definition`. Do not use implementation-plan terms such as files, modules, work items, commands, or architecture in this table.

The inventory is a definition artifact, not review commentary. Missing `DFLOW-*` rows that can be derived from approved `REQ-*` or `SP-*` content are artifact repair work: add the flow row, source it, and rerun review. Transition-risk is only for unresolved goal-critical decisions, not for flow inventory bookkeeping that the approved definition already supports.

## Language Policy

Read `references/language-policy.md` before writing or revising the definition artifact. Keep required headings, table columns, status values, IDs, paths, commands, and `Option 1:` style labels unchanged, but write artifact prose, pending clarification questions, option descriptions, recommendation reasons, review evidence, and user-facing summaries in the selected user/artifact language.

For a Korean workflow, new definition prose should default to Korean. English starter filler such as `Describe...`, `No pending clarification.`, `No completed clarification yet.`, `One concrete requirement.`, or option descriptions that remain in English is not review-ready content unless the selected artifact language is English.
