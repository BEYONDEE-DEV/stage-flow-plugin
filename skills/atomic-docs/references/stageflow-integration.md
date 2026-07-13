# Stageflow Integration

## Responsibility

This reference defines how the `atomic-docs` skill behaves when invoked during Stageflow-controlled work.

## Gate Policy

- Respect Stageflow definition, implementation-plan, implementation, review, and approval gates.
- Do not perform non-Stageflow code edits before the active implementation-plan gate passes.
- Writing Stageflow request artifacts does not mean managed docs files are approved for update.
- Writing managed docs files requires the docs operation's own confirmed scope and change plan.
- Stageflow plan approval alone is not managed-docs-root approval unless the approved docs operation names the affected docs paths and write actions.

## Evidence Boundaries

- Source files are the default evidence source for docs refresh.
- Stageflow artifacts own workflow state, decisions, approvals, and implementation evidence.
- Stageflow artifacts are not the default docs refresh evidence source.
- Atomic-docs state under `.stageflow/atomic-docs/` and `.stageflow/atomic-docs.json` is owned by the atomic-docs skill. It follows a Stageflow-like session/request shape for resumability, but it is not a Stageflow workflow request artifact and must not be used to bypass or satisfy Stageflow gates.
- Managed docs files own durable externalized project knowledge.

## Requirement Evidence

Use a Stageflow artifact as required behavior evidence only when it is an approved definition, approved implementation plan, approved policy/rule, or approved user decision that explicitly names the requirement, boundary, or affected docs path. Draft artifacts, workflow notes, review comments, pending plans, and unapproved implementation notes are not confirmed requirements.

When an approved Stageflow plan is implemented, remove the completed delta from `Planned Changes`, keep the durable requirement in its owning `Outcomes`, `Boundaries`, or `Rules` section, and add only the concise source realization to `Current Implementation`. Any remaining difference must be recorded with the applicable judgment label from `change-judgment-policy.md`.

Do not promote a Stageflow implementation detail into confirmed `Intent`, `Outcomes`, `Boundaries`, or `Rules` unless the approved Stageflow artifact or user decision states that the meaning is required.

## Output Scope

By default, `atomic-docs` write operations modify only files inside the configured managed docs root. Plugin code, Stageflow request artifacts, and source files are outside docs output scope unless a separate approved request expands scope.

## Conflict Policy

If a full refresh overlaps with a targeted docs request, prioritize the current explicit user-requested scope. Put other impacted domains or atomic docs in follow-up proposals or `Gaps`.

If source behavior, confirmed intent, planned changes, and current implementation conflict, preserve the conflict instead of collapsing it into one claim. Use judgment-labeled `Gaps`, bug candidates, missing required behavior candidates, unapproved implementation candidates, implemented-plan candidates, or confirmation-needed notes.
