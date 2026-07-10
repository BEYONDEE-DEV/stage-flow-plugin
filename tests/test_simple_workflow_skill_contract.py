from __future__ import annotations

import unittest
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "simple-workflow" / "SKILL.md"
PLUGIN_JSON = ROOT / ".codex-plugin" / "plugin.json"


class SkillContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = SKILL.read_text(encoding="utf-8")

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
        self.assertIn("Do not create new user-facing artifacts for post-implementation review", self.text)
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

    def test_material_replan_reuses_goal_and_requires_reapproval(self) -> None:
        self.assertIn("## Adaptive Execution And Material Replan", self.text)
        self.assertIn("A method-only adaptation", self.text)
        self.assertIn("A material change", self.text)
        self.assertIn("`plan_approval_status: pending`", self.text)
        self.assertIn("ask for explicit execution approval again", self.text)
        self.assertIn("continue the same active Goal", self.text)
        self.assertIn("never change the immutable `goal_plan_fingerprint`", self.text)

    def test_v2_goal_start_and_recovery_track_both_fingerprints(self) -> None:
        self.assertIn("`approved_plan_fingerprint: sha256:<hex>`", self.text)
        self.assertIn("the two fingerprints start equal", self.text)
        self.assertIn("original objective fingerprint", self.text)
        self.assertIn("repair all four local fields", self.text)

    def test_post_reviews_require_requirement_evidence_and_block_gaps(self) -> None:
        self.assertIn("must list every `REQ-###` with the actual evidence", self.text)
        self.assertIn("response must cover every `REQ-###`", self.text)
        self.assertIn("A critical outcome that cannot be observed is a verification gap", self.text)
        self.assertIn("do not create a new evidence artifact", self.text)

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
