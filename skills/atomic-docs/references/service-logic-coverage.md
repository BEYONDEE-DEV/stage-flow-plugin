# Service Logic Coverage

## Responsibility

This reference defines decision-complete service logic coverage, proportional documentation depth, source fact fidelity, and the Codex Goal boundary.

## Development Decision Coverage

Atomic docs are a durable development-decision standard, not a source index or source replacement. They preserve the product, business, contract, and operational decisions that developers must not rediscover from scattered code or invent during implementation.

For each meaningful behavior aggregate in the accepted scope, document the applicable items once in the section that owns them:

- why the behavior exists and what outcome it must preserve
- confirmed rules, invariants, explicit non-goals, and unresolved decisions
- user, caller, API, event, job, or operational entry points that establish the contract
- inputs and outputs whose values or shape affect observable behavior
- authorization, validation, refusal, defaulting, and consequential branches
- state transitions, persistence effects, external calls, emitted events, or destructive effects
- failure, retry, fallback, recovery, and runtime exception behavior when it changes the contract
- an observable verification condition for changed requirements being used as an implementation basis
- related domains, shared contracts, graph relationships, and conflicts that can change the decision
- source identifiers sufficient to find and verify the relevant implementation

Not every item applies to every atom. Omit an item when it has no product, contract, safety, operational, verification, or change-impact meaning. Do not add placeholder matrices or repetitive not-applicable rows merely to satisfy a template.

`Intent` owns only why the atom exists. `Outcomes` owns its concise normal observable result, `Boundaries` owns behavior-local inclusion/exclusion and handoff, and `Rules` owns conditions, invariants, refusals, contracts, and required effects. `Current Implementation` orients a developer to how those decisions are currently realized. Record important entry points, storage or integration ownership, non-obvious constraints, and source locations, then refer to the owning section rather than specifying the same behavior again. Do not narrate every function call, framework callback, DTO copy, component split, query mapping, or branch whose only meaning is already clear from source.

Context atoms preserve domain-wide purpose, outcomes, vocabulary, ownership, included/excluded capabilities, and adjacent-domain boundaries. Behavior atoms reference that shared context and keep only behavior-local boundaries in their own `Boundaries`; context atoms do not absorb or enumerate concrete rules and workflow boundaries that need independent change or judgment.

## Accepted-Scope Coverage

Maintain closure from each meaningful behavior aggregate in the accepted scope to one of: an owning `atom_key`/AID, a coverage gap, `out_of_scope`, or not-applicable with a reason.

A behavior aggregate may span routes, controllers, services, repositories, UI components, settings, schemas, tests, jobs, or integrations. Close the aggregate once at the decision level; do not require a separate inventory row or AID for every mechanical source surface. Tests and configuration are evidence when they change runtime meaning, but behavior-neutral wiring is not documentation work.

For full refresh, inspect all project-native feature roots and continue beneath rejected broad roots until each meaningful product or operational aggregate has a disposition. For targeted work, close only the accepted behavior and the adjacent contracts needed to judge its impact. Partial closure must not be reported as project-wide coverage.

An endpoint list, class list, source path list, or one-line file summary is not decision coverage. Source identifiers become useful only when the docs explain the durable decision or behavior they support.

## Proportional Depth

Document until all of these questions can be answered:

1. What product or operational behavior must an implementation preserve or change?
2. What observable result proves success or failure?
3. Which rules, states, permissions, contracts, or failure paths may not be chosen arbitrarily?
4. Which other domain or shared contract could conflict with this decision?

Stop adding detail when every remaining choice is an internal technical choice, such as function decomposition, library selection, framework convention, behavior-neutral DTO copying, or component structure. Also stop when a meaning is already complete in its owning section: another section needs a short reference, not a paraphrase.

Review must FAIL a behavior atom when the accepted change or judgment still forces a developer to invent a business rule, permission, externally visible contract, state transition, failure outcome, or verification condition. Review must not fail merely because the reader needs source for internal mechanics.

Do not use atom count, file count, line count, or source-surface count as a quality threshold. A short atom can preserve every relevant decision, while a long source narrative can still be shallow.

Use tables or structured lists only when compact prose would obscure independently varying decisions. For example, a matrix may be useful when several fields have different validation outcomes, several states allow different actions, or several failure types have distinct recovery behavior. Do not require field, payload, branch, state, and failure matrices as a fixed set.

For frontend/UI behavior, include fields, routes, screen states, access guards, persistence, payload transforms, feedback, and design constraints only when they affect product behavior, verification, or an explicitly requested style. Display-only fields and exact CSS values are normally source-level details.

For backend/API/service/job/integration behavior, include payload fields, authorization, validation, domain policy, transaction/idempotency, persistence, schema, events, integrations, and recovery only to the depth needed to preserve a decision or observable contract.

## Conditional Risk Depth

Apply additional detail and the independent risk/contract reviewer when the accepted bundle includes any of these triggers:

- authentication, authorization, security, privacy, or sensitive-data handling
- money, billing, refund, settlement, quota, or entitlement
- delete, approve, publish, irreversible mutation, or destructive operation
- external integration, webhook, event delivery, or third-party dependency
- irreversible, high-impact, or concurrency-sensitive state transition; transaction boundary; idempotency; retry; or recovery
- shared payload, storage, permission, integration, or policy contract used by another domain

Ordinary CRUD, reversible preference persistence, or a routine state field is not a trigger by itself. For a triggered concern, document the specific risky decision, adverse branch, and verification evidence in the applicable owning section. Add a matrix only when the alternatives cannot be reviewed reliably in prose. A trigger does not require unrelated detail elsewhere in the atom or a duplicate copy in `Gaps`.

For an external contract, use authoritative local or user-approved provider evidence such as a versioned schema/specification, SDK contract, fixture, or contract test when available. If the accepted evidence cannot establish a behavior-affecting contract, record `confirmation_needed` instead of allowing reviewer PASS from local assumptions alone.

## Source Fact Fidelity

The development-quality reviewer compares judgment-bearing docs with the actual reachable source path. Do not infer runtime behavior from a field annotation, method name, type, endpoint name, or service class alone.

When validation, refusal, defaulting, fallback, exception, read-only behavior, or storage effects matter, inspect the relevant caller binding, runtime guard, null/blank path, default, transaction mode, persistence call, and exception path. Record only the distinctions that affect a documented decision or contract.

If source allows a fallback instead of refusing input, preserve that observable branch or record uncertainty. Do not describe a path as recovered when source can throw an unhandled runtime exception. When source cannot prove intent, use `confirmation_needed` rather than promoting observed behavior into a confirmed rule.

Judgment-bearing `Gaps` and review findings must include source evidence, confirmed or inferred basis, affected behavior, next action, and related stable `atom_key`/AID values when known. Use the related AID or section for the complete behavior and keep the gap's source evidence to the locator and differential fact needed to support the unresolved finding.

## Atomic Docs Goal Boundary

The Codex Goal after criteria approval is an execution scope for the accepted docs operation. It does not replace criteria approval, docs write scope, atom content, judgment labels, source evidence, user review, or baseline metadata.

Do not write Goal status into atom meaning. If execution is waiting or blocked, preserve that state in operation state or the change plan. A correctable review FAIL is not Goal-blocked; revise and rerun the applicable reviewer first.
