from __future__ import annotations

import unittest
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "simple-workflow" / "SKILL.md"
ARTIFACT_FORMAT = ROOT / "skills" / "simple-workflow" / "references" / "artifact-format.md"
HOOKS = ROOT / "skills" / "simple-workflow" / "references" / "hooks.md"
PLUGIN_JSON = ROOT / ".codex-plugin" / "plugin.json"


class SkillContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = SKILL.read_text(encoding="utf-8")
        cls.artifact_text = ARTIFACT_FORMAT.read_text(encoding="utf-8")
        cls.hooks_text = HOOKS.read_text(encoding="utf-8")

    def test_shared_planning_and_review_principles_are_the_common_contract(self) -> None:
        self.assertIn("## Shared Planning And Review Principles", self.text)
        self.assertIn("Use the same principles when writing `plan.md`, reviewing `plan.md` with a subagent", self.text)
        self.assertIn("confirmed intent", self.text)
        self.assertIn("approved scope", self.text)
        self.assertIn("every `REQ-###`", self.text)
        self.assertIn("relevant flow problems", self.text)
        self.assertIn("out-of-scope issues", self.text)
        self.assertIn("validation tied to the real affected", self.text)
        self.assertIn("body text in Korean", self.text)

    def test_reviews_refer_to_the_shared_principles(self) -> None:
        self.assertIn("The internal review must use `Shared Planning And Review Principles`", self.text)
        self.assertIn("Both reviews must use `Shared Planning And Review Principles`", self.text)

    def test_post_implementation_review_has_two_required_perspectives(self) -> None:
        self.assertIn("## Post-Implementation Review", self.text)
        self.assertIn("`Intent Compliance Review`", self.text)
        self.assertIn("confirmed user intent", self.text)
        self.assertIn("approved `plan.md`", self.text)
        self.assertIn("actual diff", self.text)
        self.assertIn("validation results", self.text)
        self.assertIn("`Flow / Unexpected Issue Review`", self.text)
        self.assertIn("affected user, state, data, failure or recovery, command, hook, and validator flows", self.text)

    def test_in_scope_issues_are_fixed_but_out_of_scope_issues_are_reported_first(self) -> None:
        self.assertIn("Codex must fix it automatically and repeat validation plus both post-implementation reviews", self.text)
        self.assertIn("outside the user's intent, pre-existing, or requires expanded scope", self.text)
        self.assertIn("Codex must tell the user before changing it", self.text)

    def test_post_implementation_review_does_not_create_extra_user_artifacts(self) -> None:
        self.assertIn("do not create a new artifact", self.text)
        self.assertNotIn("code-review.md", self.text)
        self.assertNotIn("implementation-log.md", self.text)

    def test_agent_owns_semantic_approval_and_hook_is_structural_only(self) -> None:
        self.assertIn("Natural-language approval intent belongs to the agent", self.text)
        self.assertIn("Hooks must not classify approval with keyword or regular-expression matching", self.text)
        self.assertIn("`PreToolUse(create_goal)` only enforces structural prerequisites", self.text)
        self.assertIn("The plugin `PreToolUse(create_goal)` hook is a structural gate only", self.text)

    def test_goal_reconciliation_prevents_duplicate_creation(self) -> None:
        self.assertIn("Before calling `create_goal`, call `get_goal`", self.text)
        self.assertIn("do not call `create_goal` again", self.text)
        self.assertIn("repair local `goal_status: active`", self.text)
        self.assertIn("another unfinished Goal exists", self.text)

    def test_v2_planning_is_outcome_and_evidence_first(self) -> None:
        self.assertIn("`workflow_version: 2`", self.text)
        self.assertIn("`## Outcome And Completion Criteria`", self.text)
        self.assertIn("`Requirement | Plan | Completion Evidence`", self.text)
        self.assertIn("planned and actual completion evidence", self.text)
        self.assertIn("Requests without `workflow_version` are legacy requests", self.text)

    def test_question_depth_is_adaptive_to_material_decisions(self) -> None:
        self.assertIn("Question depth is adaptive, not a quota", self.text)
        self.assertIn("materially change the goal, scope, expected outcome", self.text)
        self.assertIn("Infer reversible low-risk details", self.text)
        self.assertIn("behaviorally equivalent implementation details", self.text)

    def test_intent_challenge_precedes_confirmation_and_question_depth(self) -> None:
        core = self.text[self.text.index("## Core Rule"):self.text.index("## Request Storage")]
        self.assertLess(core.index("run the bounded `Intent Challenge Review`"), core.index("Ask the user to confirm"))
        self.assertLess(core.index("Ask the user to confirm"), core.index("Write `plan.md`"))
        self.assertIn("after project inspection and the main agent's first inference but before the first user intent confirmation", self.text)
        self.assertIn("Only then ask for the first intent confirmation and proceed to the Question Depth Gate", self.text)

    def test_intent_challenge_is_bounded_and_covers_requirement_quality(self) -> None:
        self.assertIn("using only the user's request, inspected project facts", self.text)
        self.assertIn("inferred intent, expected outcome, boundaries and assumptions", self.text)
        self.assertIn("plausible alternatives grounded in those facts", self.text)
        for perspective in (
            "whether the requested solution fits the underlying problem",
            "false assumptions, contradictions, omissions",
            "affected users, systems, owners",
            "simpler or safer alternatives",
            "failure paths, edge cases, irreversible effects",
            "mismatches between the request or inference and the actual project",
        ):
            self.assertIn(perspective, self.text)
        self.assertIn("it does not replace the user's intent or authorize a requirement change", self.text)

    def test_material_intent_findings_require_user_decision_and_repeat(self) -> None:
        self.assertIn("supporting fact, likely impact, and decision needed", self.text)
        self.assertIn("Never silently or automatically apply", self.text)
        self.assertIn("user's correction or explicit tradeoff acceptance", self.text)
        self.assertIn("repeat until the reviewer returns `PASS` with no unresolved material finding", self.text)
        self.assertIn("do not automatically revise the requirement or plan", self.text)
        self.assertIn("rerun any Question Depth checkpoints affected by it", self.text)

    def test_intent_challenge_uses_marker_and_existing_review_artifact(self) -> None:
        self.assertIn("exact integer `intent_challenge_version: 1`", self.text)
        self.assertIn("Marker-free existing v2 and legacy requests retain their previous review schema", self.text)
        self.assertIn("`Finding | User Decision Or Resolution | Verdict`", self.text)
        self.assertIn("unique `IC-###`", self.text)
        self.assertIn("one `NONE` row", self.text)
        self.assertIn("`### Intent Challenge Final Verdict` must be exact `PASS`", self.text)
        self.assertIn("Do not create a challenge artifact", self.text)
        self.assertIn("Do not repeat the initial Intent Challenge Gate during material replan", self.text)
        self.assertIn('"intent_challenge_version": 1', self.artifact_text)
        self.assertIn("Existing v2 and legacy requests that", self.artifact_text)
        self.assertIn("## Intent Challenge Check", self.artifact_text)

    def test_material_replan_reuses_goal_and_requires_reapproval(self) -> None:
        self.assertIn("## Adaptive Execution And Material Replan", self.text)
        self.assertIn("A method-only adaptation", self.text)
        self.assertIn("A material change", self.text)
        self.assertIn("`plan_approval_status: pending`", self.text)
        self.assertIn("ask for explicit execution approval again", self.text)
        self.assertIn("continue the same active Goal", self.text)
        self.assertIn("never change the immutable `goal_plan_fingerprint`", self.text)

    def test_v2_goal_start_and_recovery_track_both_fingerprints(self) -> None:
        self.assertIn("before `get_goal` or `create_goal`", self.text)
        self.assertIn("This `approved + pending` state", self.text)
        self.assertIn("If `create_goal` fails, preserve `approved + pending`", self.text)
        self.assertIn("record the objective fingerprint as `goal_plan_fingerprint`", self.text)
        self.assertIn("approval was already recorded and must not be rewritten", self.text)

    def test_post_reviews_require_requirement_evidence_and_block_gaps(self) -> None:
        self.assertIn("must list every `REQ-###` with the actual evidence", self.text)
        self.assertIn("response must cover every `REQ-###`", self.text)
        self.assertIn("A critical outcome that cannot be observed is a verification gap", self.text)
        self.assertIn("existing `review.md` Completion Review", self.text)

    def test_completion_pre_gate_and_rescope_policy_preserve_goal(self) -> None:
        self.assertIn("validation with `--phase completion`", self.text)
        self.assertIn("Do not continue on failure", self.text)
        self.assertIn("do not label partial work complete", self.text)
        self.assertIn("offer a fallback only when it preserves the approved outcome", self.text)
        self.assertIn("material rescope through the replan flow", self.text)

    def test_completion_order_and_partial_failure_recovery_are_explicit(self) -> None:
        self.assertIn("## Completion And Partial-Failure Recovery", self.text)
        self.assertIn("durably set `state.json` `goal_status: completing`", self.text)
        self.assertIn("If this write fails, do not call `update_goal`", self.text)
        self.assertIn("Call `update_goal(status=\"complete\")`", self.text)
        self.assertIn("Goal completion succeeds but local completion metadata fails", self.text)
        self.assertIn("repair only local completed metadata", self.text)
        self.assertIn("Never create a replacement Goal", self.text)

    def test_read_only_work_uses_the_same_post_execution_gate(self) -> None:
        self.assertIn("This gate applies to code-changing and read-only work", self.text)
        self.assertIn("actual outputs and commands when work was read-only", self.text)
        self.assertIn("For read-only work, the same completion order applies", self.text)

    def test_allowed_v2_states_and_durable_completion_review_are_explicit(self) -> None:
        for state in (
            "plan      | pending  | pending",
            "review    | approved | pending",
            "review    | pending  | active",
            "completed | approved | completed",
        ):
            self.assertIn(state, self.artifact_text)
        self.assertIn("## Completion Review", self.artifact_text)
        self.assertIn("Requirement | Actual Evidence | Verdict", self.artifact_text)
        self.assertIn("New completions require this section", self.artifact_text)

    def test_hook_activation_and_stop_boundaries_are_agent_owned(self) -> None:
        self.assertIn("Hooks do not infer activation from prompt strings", self.text)
        self.assertIn("search prompt text for `simple workflow`", self.hooks_text)
        self.assertIn("`Stop` never emits a deny or blocking", self.hooks_text)
        self.assertIn("without repeatedly running the full validator", self.hooks_text)

    def test_plugin_manifest_exposes_simple_workflow_prompt(self) -> None:
        manifest = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))
        interface = manifest["interface"]

        self.assertIn("Simple Workflow", interface["longDescription"])
        self.assertIn("Simple Workflow", interface["capabilities"])
        self.assertIn(
            "Use Simple Workflow to capture requirements, write plan.md, review it internally, and wait for approval.",
            interface["defaultPrompt"],
        )


if __name__ == "__main__":
    unittest.main()
