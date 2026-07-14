# Service Logic Coverage

## Responsibility

This reference is the normative owner of decision-complete service logic coverage, proportional documentation depth, risk triggers, and source fact fidelity. `atom-format-and-judgment.md` owns atom shape and AIDs; `change-judgment-policy.md` owns judgment labels and finding evidence; `docs-generation-flow.md` owns Goal sequencing.

## Development Decision Coverage

Atomic docs are a durable development-decision standard, not a source index, source replacement, or default security audit. They preserve source-established current contracts, approved product or operational requirements, and material unresolved decisions developers must not rediscover from scattered code or invent during implementation.

## Current Contract Evidence

A source-established current contract is an observable result, local boundary, rule, state/effect, or integration behavior supported by a reachable production path and, when available, behavior-relevant tests, schemas, settings, or local API contracts. It may be documented without separate user approval. AI authorship alone does not make the meaning inferred or create a Gap; a method name, field annotation, or test name alone still does not establish runtime behavior.

Reachability or repetition alone does not make behavior a normal contract. An inconsistent branch, violated local invariant, accidental fallback, unsafe bypass, or source quirk without consumer/operational meaning remains implementation context or a differential finding under `atom-format-and-judgment.md`; it must not be normalized merely because the current code executes it.

Trace current contracts through `Current Implementation` source locators and the applicable revision: the project-wide source baseline for complete coverage, or operation-local `source_commit_observed` for targeted/partial work. This establishes what the source currently does. It does not mean product policy approval or make the behavior a future required change.

`Intent` may state the smallest functional purpose supported by entry points, outcomes, ownership, and integration use, but must not present inferred product strategy or necessity as user-approved intent. Create a Gap only when competing purpose interpretations would materially change an outcome, boundary, rule, requirement, or implementation judgment. Section placement and defect routing are owned by `atom-format-and-judgment.md`.

For each meaningful behavior aggregate in the accepted scope, document the applicable items once in the section that owns them:

- why the behavior exists and what outcome it must preserve
- source-established or approved rules, invariants, explicit non-goals, and unresolved decisions
- user, caller, API, event, job, or operational entry points that establish the contract
- inputs and outputs whose values or shape affect observable behavior
- authorization, validation, refusal, defaulting, and consequential branches
- state transitions, persistence effects, external calls, emitted events, or destructive effects
- failure, retry, fallback, recovery, and runtime exception behavior when it changes the contract
- a concise observable verification target or invariant for changed requirements being used as an implementation basis
- related domains, shared contracts, graph relationships, and conflicts that can change the decision
- source identifiers sufficient to find and verify the relevant implementation

Not every item applies to every atom. Omit an item when it has no product, contract, safety, operational, verification, or change-impact meaning. Do not add placeholder matrices or repetitive not-applicable rows merely to satisfy a template. A verification target states what must be observed; it does not enumerate the complete test input matrix or execution procedure.

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

Stop adding detail when every remaining choice is an internal technical choice, such as function decomposition, library selection, framework convention, behavior-neutral DTO copying, or component structure. Also stop when the remaining work is a forensic defect inventory, attack-scenario catalog, or exhaustive failure reproduction outside an explicitly accepted audit scope. When a meaning is already complete in its owning section, another section needs a short reference, not a paraphrase.

Review must FAIL a behavior atom when the accepted change or judgment still forces a developer to invent a business rule, permission, externally visible contract, state transition, failure outcome, or verification target. Review must not fail merely because the reader needs source for internal mechanics or must derive concrete test cases from a clear invariant.

Do not use atom count, file count, line count, or source-surface count as a quality threshold. A short atom can preserve every relevant decision, while a long source narrative can still be shallow.

Use tables or structured lists only when compact prose would obscure independently varying durable decisions. For example, a matrix may be useful when several states have different product-authorized actions or several failure types have distinct contractual recovery behavior. The matrix must itself express a product or contract decision; do not use it merely to enumerate a Cartesian test plan. Do not require field, payload, branch, state, and failure matrices as a fixed set.

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

Ordinary CRUD, reversible preference persistence, or a routine state field is not a trigger by itself. For a triggered concern, document the specific risky contract, adverse branch, and concise verification target only when it affects the accepted implementation, review, or change-impact decision. Derive detailed actor/input/state/failure cases transiently during implementation or review rather than preserving their full cross-product in the atom or routine review report. Add a matrix only when the alternatives form a durable contract that cannot be reviewed reliably in prose. A trigger does not require unrelated detail elsewhere in the atom or a duplicate copy in `Gaps`.

For an external contract, use authoritative local or user-approved provider evidence such as a versioned schema/specification, SDK contract, fixture, or contract test when available. Record `confirmation_needed` only when the unavailable or conflicting external guarantee prevents the accepted implementation or review judgment; do not create a Gap merely because the remote implementation is outside the repository.

## Source Fact Fidelity

The development-quality reviewer compares judgment-bearing docs with the actual reachable source path. Do not infer runtime behavior from a field annotation, method name, type, endpoint name, or service class alone.

When validation, refusal, defaulting, fallback, exception, read-only behavior, or storage effects matter, inspect the relevant caller binding, runtime guard, null/blank path, default, transaction mode, persistence call, and exception path. Record only the distinctions that affect a documented decision or contract.

If source allows a fallback instead of refusing input, preserve it as a normal contract only when the reachable evidence supports that interpretation. Do not describe a path as recovered when source can throw an unhandled runtime exception. A non-blocking anomaly may remain concise `Current Implementation` context; if source conflicts with an approved requirement or a source-established current contract, route the differential finding under `change-judgment-policy.md`. Lack of product-intent proof alone does not create `confirmation_needed`.

Apply finding fields, label precedence, and AID-or-owning-section evidence from `change-judgment-policy.md`. This source-fidelity contract adds only that evidence must reach the relevant behavior path and that missing tests or possible runtime failures become gaps only when their absence prevents the accepted implementation or review judgment.

## Atomic Docs Goal Boundary

The Codex Goal after criteria approval is an execution scope for the accepted docs operation. It does not replace criteria approval, docs write scope, atom content, judgment labels, source evidence, user review, or baseline metadata.

Do not write Goal status into atom meaning. If execution is waiting or blocked, preserve that state in operation state or the change plan. A correctable review FAIL is not Goal-blocked; revise and rerun the applicable reviewer first.
