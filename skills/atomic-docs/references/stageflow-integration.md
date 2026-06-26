# Stageflow Integration

## Responsibility

This reference defines how the `atomic-docs` skill behaves when invoked during Stageflow-controlled work.

## Gate Policy

- Respect Stageflow definition, implementation-plan, implementation, review, and approval gates.
- Do not perform non-Stageflow code edits before the active implementation-plan gate passes.
- Writing Stageflow request artifacts does not mean docs submodule files are approved for update.
- Writing docs submodule files requires the docs operation's own confirmed scope and change plan.
- Stageflow plan approval alone is not docs-submodule approval unless the approved docs operation names the affected docs paths and write actions.

## Evidence Boundaries

- Source files are the default evidence source for docs refresh.
- Stageflow artifacts own workflow state, decisions, approvals, and implementation evidence.
- Stageflow artifacts are not the default docs refresh evidence source.
- Docs submodule files own durable externalized project knowledge.

## Output Scope

By default, `atomic-docs` write operations modify only files inside the configured documentation submodule root. Plugin code, Stageflow request artifacts, and source files are outside docs output scope unless a separate approved request expands scope.

## Conflict Policy

If a full refresh overlaps with a targeted docs request, prioritize the current explicit user-requested scope. Put other impacted domains or atomic docs in follow-up proposals or `Gaps`.

If source behavior, confirmed intent, planned changes, and current implementation conflict, preserve the conflict instead of collapsing it into one claim. Use `Gaps`, bug candidates, implemented-plan candidates, or confirmation-needed notes.
