# Stageflow Integration

When Atomic Docs is used inside an active Stageflow request, Stageflow owns request definition, plan approval, Goal handoff, and implementation-stage progression. Atomic Docs owns only its config and managed docs.

An approved Stageflow requirement may supply an Atomic Impl RID change, but Atomic Docs does not create parallel workflow state or a second Goal. Respect the Stageflow-approved write scope and stop when Stageflow requires user approval.

Do not copy Stageflow request artifacts into managed docs. Promote only durable project meaning, active approved changes, and source-backed implementation context.
