# Service Logic Coverage

## Responsibility

This reference defines natural-language service logic coverage, implementation reconstruction readiness, source fact fidelity, and the Codex Goal boundary.

## Service Logic Natural-Language Coverage

Atomic docs are a natural-language service logic standard, not a source index. Generated docs should let a reviewer understand the meaningful runtime behavior without rereading every source file first.

Document all meaningful application, service, and domain logic that affects product behavior, operational behavior, or integration behavior. This includes conditions, branches, state transitions, validation, permission checks, policy rules, transaction or idempotency behavior, persistence side effects, external calls, emitted events, error handling, and recovery behavior.

Do not treat endpoint lists, controller lists, service class names, method names, file paths, or terse class-role summaries as service logic coverage. These identifiers are source evidence only until the atom explains in natural language what the source behavior does, when it does it, what it refuses, what it stores or changes, what it calls, and what result or failure it produces.

For each meaningful service logic item, the docs must record:

- source identifiers that were inspected
- owning atom or a coverage gap when ownership is unresolved
- natural-language behavior description
- input conditions, guards, branches, and failure conditions that affect the behavior
- state, persistence, integration, emitted-event, or external side effects
- confirmed or inferred basis for intent, rule, requirement, exclusion, or boundary
- judgment readiness: whether the item can be judged from the docs or must remain `confirmation_needed` or a coverage gap

Complex logic should be split into multiple atoms when separate behaviors, policies, states, or side effects need independent judgment. Splitting does not allow omission: each split atom must still describe the concrete conditions, outcomes, and side effects it owns.

Context atoms are not a shortcut for behavior coverage. A context atom may preserve domain purpose, glossary terms, included and excluded behavior, and adjacent boundaries, but it must not own concrete endpoint flow, payload rules, state transitions, persistence effects, external integration behavior, or failure/recovery details that belong in behavior atoms. Review must fail context atom pollution instead of treating it as acceptable broad coverage.

Trivial getters, mechanical DTO copying, framework boilerplate, and generated wiring do not require standalone atoms when they carry no service meaning. If such code changes validation, permission, persistence, transaction, state, integration, error, idempotency, or recovery behavior, document that behavior in natural language.

## Source Discovery Closure Gate

For the accepted scope, maintain source discovery closure from inspected source surface/aggregate to documentation outcome. Every meaningful route, controller, service method, policy rule, persistence mutation/read model, workflow step, UI entry, job, event, external integration, runtime schema/migration, runtime setting, route configuration, or behavior-relevant test must close as one of: owned by a real `atom_key`/AID, recorded as a coverage gap, marked `out_of_scope`, or marked not-applicable with a reason. Tests support source interpretation but do not replace inspection of reachable production behavior.

Unmapped or orphan source behavior is a blocking review finding when the docs claim judgment readiness, baseline readiness, or implementation reconstruction readiness. A rejected broad source root still needs sub-aggregate disposition; do not hide lower-level behavior behind the broad rejection.

High-risk atom coverage requires structured matrices when applicable. Account/auth/admin management, delete/approve actions, payment/refund behavior, external integration, persistence mutation, idempotency, and failure recovery must include payload/field matrix, branch matrix, state/persistence effect matrix, and failure/recovery matrix details, or a specific not-applicable reason. A label-only gap, endpoint summary, or generic "handled by service" sentence is not enough for these categories.

## Implementation Reconstruction Coverage

Atomic docs must satisfy a source-to-docs-to-code implementation reconstruction standard for the accepted scope. A competent implementer should be able to implement the same functional behavior from the docs without rereading source. This does not require pixel-perfect visual design, exact CSS values, component internal structure, or library choice unless source or user requirements make them behavior-relevant. It does require basic design/state presentation, screen structure, and visual feedback guidance when they affect product behavior or the style the user asked to preserve.

This is the default completion standard for every accepted behavior/contract scope, including targeted or partial work. Partial reconstruction PASS applies only to that accepted scope and must not be reported as project-wide readiness. Context atoms remain boundary/context documents and do not need behavior-atom detail unless they improperly own concrete behavior.

For frontend/UI source, document app shell behavior, routing, route/hash/query handling, selected entity and persistence, permission/access/no-data guards, preload/fallback behavior, form field matrix, collection editor behavior, validation/refusal/defaulting, payload transforms, save/delete scopes, confirmation modals, readiness blocker order, detail routes, empty/loading/error states, and basic design/state presentation enough to implement the required style.

For backend/API/service/job/integration source, document API contract, request/response payload, authorization/authentication, validation/guard behavior, domain policy, transaction or idempotency behavior, persistence mutation/read model, DB schema/DTO fields that affect behavior, async job/event behavior, external integration behavior, and error/retry/recovery semantics.

A docs set is not implementation-reconstruction-ready when these behaviors are only endpoint identifiers, screen identifiers, source identifiers, method-call sequences, source convention notes, one-line inventory, or unresolved `confirmation_needed` without next action.

The criteria document and writer/reviewer loop must make implementation reconstruction coverage an explicit shared standard before user approval. The shared standard must name applicable frontend/UI coverage, backend/API/service/job/integration coverage, explicit not-applicable reasons, and blockers that prevent docs-only implementation.

Review must fail when a criteria document or completed docs set omits implementation reconstruction coverage, applicable or not-applicable frontend/UI coverage, backend/API/service/job/integration coverage, or blockers that prevent docs-only implementation.

Do not use atom count, file count, or line count as a quality threshold. A short context atom can be complete when it only records a boundary, and a long behavior atom can still fail when implementation choices are missing. Review the density of reconstruction-critical decisions instead.

Shallow atom review must fail a behavior, contract, or matrix atom when it mentions forms, editors, routes, access guards, payloads, validations, readiness, save/delete behavior, API/service contracts, or state transitions but omits the concrete fields, branches, rules, payload shape, contract semantics, state effects, or failure outcomes an implementer would otherwise have to rediscover from source. If an atom uses terms such as `field matrix`, `payload`, `validation`, `contract`, `readiness`, or `state transition`, include a table or structured list for the applicable fields and branches, or record an explicit not-applicable reason. A sentence such as "handles local validation", "maps payload", or "calls the API" is not enough.

Implementation reconstruction review must not be combined with atom-boundary or source-closure review. Run each domain reconstruction/high-risk reviewer as a fresh docs-only reviewer. Its inputs are the managed docs in scope, approved criteria/project context, and required plugin principle files. Do not give it the source tree, operation inventory, or source evidence packet. Source identifiers already written in managed docs may remain visible, but the reviewer must not open source to fill a documentation gap.

The docs-only reviewer must FAIL when it needs source, unstated product decisions, or arbitrary implementation choices. Do not add a separate probe file, input manifest, path-access audit, or reviewer solely for this check; record the verdict and missing decisions in the existing reviewer report. The separate source-closure/fact-fidelity reviewer compares the completed natural-language docs with actual source.

Run the final reconstruction reviewer with docs-only input as well. It checks end-to-end behavior crossing domain or frontend/backend boundaries and does not redo unchanged local matrices. The reconstruction perspective must FAIL when applicable high-risk categories lack required matrices or specific not-applicable reasons.

## Source Fact Fidelity Gate

Within each domain bundle, local source fact fidelity is owned by the `Domain Draft Source Closure / Fact Fidelity Reviewer`, which compares judgment-bearing claims with the actual inspected source branch. In the project-wide final gate, the corresponding final reviewer checks cross-domain source ownership, project-wide closure, changed shared evidence, and contradictions that could invalidate an earlier domain PASS; it does not repeat every unchanged local claim.

Atom `Rules`, `Current Implementation`, `Gaps`, evidence packets, and review findings must preserve the source-observed behavior actually reachable through the inspected entry path. Do not simplify a branch into the behavior that a field annotation, method name, service class name, or DTO type seems to imply.

When documenting validation, refusal, defaulting, fallback, exception, read-only, or storage-effect behavior, compare the relevant source branches instead of relying on one identifier. Inspect the endpoint or caller binding, validator activation, service guard, null handling, blank handling, optional dependency fallback, default value fallback, explicit exception branches, runtime exception possibility, transaction mode, and persistence calls when those details affect product, operation, or integration behavior.

If source allows a null, blank, optional dependency, fallback value, or runtime path instead of refusing it, the docs must preserve that branch as observed behavior or record it as `confirmation_needed`. Do not rewrite an allowed fallback path as a guaranteed validation failure. Conversely, do not describe a behavior as safe or recovered when the source can throw an unhandled runtime exception.

If an observed behavior depends on both declarative metadata and runtime wiring, describe both sides. For example, a request field annotation is not enough to claim that the endpoint rejects the request unless the controller or caller path actually activates validation. Use a generic coverage gap or `confirmation_needed` when the inspected source does not prove the stronger claim.

Judgment-bearing `Gaps` and review findings are not sufficient when they only contain a label. Each such item must include source evidence, confirmed or inferred basis, affected behavior, next action, and related stable `atom_key` and AID values when the affected atom lines are known.

## Atomic Docs Goal Boundary

The Codex Goal used after criteria approval is an execution scope for performing the accepted docs operation. It does not replace criteria approval, accepted docs write scope, atom content, judgment labels, source evidence, user review, or source-baseline metadata.

Do not write Goal status or Goal completion as atom-level status, per-atom freshness, or judgment evidence. Code suitability judgments still come from approved criteria, generated atoms, source evidence, graph relationships, baseline metadata, and controlled judgment labels.

If the Goal is incomplete, waiting for user input, or blocked by a user-decision, tool, or runtime blocker, preserve that state in the operation summary or change plan rather than in atom judgment labels. Required reviewer/gate execution that has not run yet and review FAIL that can be corrected inside the accepted scope are not Goal-blocked states; run, revise, and rerun the required gate first. Atom files should continue to describe intent, rules, current implementation, planned changes, and gaps.
