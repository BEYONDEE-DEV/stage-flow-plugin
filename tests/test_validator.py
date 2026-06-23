
from __future__ import annotations

import contextlib
import hashlib
import json
import os
import shutil
import subprocess
import sys
import uuid
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_stageflow.py"
REFERENCE_ROOT = ROOT / "skills" / "stageflow" / "references"
REQUEST_ID = "20260621-1200-test-request"
TMP_ROOT = Path(os.environ.get("STAGEFLOW_TEST_TMP", str(ROOT / "tests" / "tmp")))
TMP_ROOT.mkdir(parents=True, exist_ok=True)


@contextlib.contextmanager
def temp_project():
    path = TMP_ROOT / f"case-{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


STAGE_RULE_IDS = {
    "definition": [f"DEF-RULE-{index:03d}" for index in range(1, 15)],
    "implementation-plan": [f"IP-RULE-{index:03d}" for index in range(1, 9)],
    "implementation": [f"IMPL-RULE-{index:03d}" for index in range(1, 7)],
}

DEFINITION_TEXT = """# Definition

## User Goal

Goal based on inspected project context.

## Request Profile

Primary: bugfix
Secondary: feature-adjustment

## Desired Outcomes

| ID | Outcome | Source | Success Signal |
| --- | --- | --- | --- |
| OUT-001 | User can complete the corrected behavior. | User request. | Acceptance criteria covers REQ-001. |

## Current Problems

| ID | Problem | Expected Behavior | Actual Behavior | Evidence Or Reproduction | Impact |
| --- | --- | --- | --- | --- | --- |
| PROB-001 | Existing behavior is wrong. | Corrected behavior is available. | Incorrect behavior is present. | Reproduction notes. | User workflow is affected. |

## Problem-To-Requirement Mapping

| Problem ID | Requirement ID | Resolution |
| --- | --- | --- |
| PROB-001 | REQ-001 | REQ-001 defines the corrected behavior. |

## User-Specified Constraints

- User supplied constraint.

## Discovered Constraints

- Project inspection constraint.

## Pending Clarifications

| ID | Question | Options | Recommended Option | Transition Option | Why This Matters | Status |
| --- | --- | --- | --- | --- | --- | --- |
| PENDING-000 | No pending clarification. | N/A | N/A | N/A | N/A | none |

## Clarification History

| Round ID | Questions Asked | User Response | Implementation Plan Option Offered | User Transition Signal | Reflected In |
| --- | --- | --- | --- | --- | --- |
| CLAR-001 | Which correction boundary should definition capture? Options: fix only reported behavior, include adjacent regression guard, 구현 계획으로 넘어가기. | User selected `구현 계획으로 넘어가기`. | yes | 구현 계획으로 넘어가기 | REQ-001, SP-001 |

## Open Questions

| ID | Decision Needed | Context Or Conflict | Recommended Option | Alternatives | Impact | Blocking | Resolution Target |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Q-001 | No open question. | N/A | N/A | N/A | N/A | no | N/A |

## Resolved Decisions

| ID | Source Question ID | Answer Source | Decision | Reflected In |
| --- | --- | --- | --- | --- |
| DEC-001 | N/A | N/A | No resolved decision yet. | N/A |

## Requirements

| ID | Type | Source | Requirement Detail | Boundary Or Exclusion | Linked Outcomes Or Problems |
| --- | --- | --- | --- | --- | --- |
| REQ-001 | bugfix | User request. | Implement corrected behavior. | No unrelated scope. | OUT-001, PROB-001 |

## Acceptance Criteria

- `REQ-001` is satisfied when `OUT-001` is verifiable and `PROB-001` is resolved.

## Normal Behavior Model

The service exposes the corrected normal behavior and prevents the reported regression.

## User Flow

Users see the changed behavior in the approved flow.

## State And Policy Model

State changes follow the approved policy.

## Policy Rules

| Rule ID | Trigger Or Condition | Policy | User/System Response | State/Data Responsibility | Failure/Recovery Behavior | Source Requirement IDs |
| --- | --- | --- | --- | --- | --- | --- |
| SP-001 | User requests behavior. | Follow approved behavior. | User sees the planned response. | Required state is updated. | Errors remain recoverable. | REQ-001 |

## Integration Flow And Data Responsibilities

No integration change.

## Boundaries

Only approved behavior is included.

## Regression Prevention

PROB-001 must not recur.

## Failure And Recovery Behavior

Errors remain recoverable.
"""

IMPLEMENTATION_PLAN_TEXT = """# Implementation Plan

## Technical Approach

Extend the existing validator-driven Stageflow architecture so the same stage metadata and markdown table checks enforce the approved definition behavior.

## Implementation Architecture

`scripts/validate_stageflow.py` validates stage sections and tables, stage rule markdown defines authoring contracts, and subprocess tests verify fixture requests through the public CLI.

## Change Areas

Validator metadata, stage rule markdown, review prompts, and test fixtures.

## Cause Or Design Notes

Root cause and design notes are grounded in SP-001. The technical contract must reject shallow implementation plans before approval.

## Work Items

| ID | Implementation Unit | Technical Design | Completion Evidence |
| --- | --- | --- | --- |
| WORK-001 | Implementation-plan validator contract. | Add required technical sections and work-item columns to the stage metadata, then reject generic implementation text. | Validator failure tests and full unittest output. |

## Coverage Matrix

| Service Rule ID | Work Item ID | Change Area | Validation Evidence | Risk/Constraint |
| --- | --- | --- | --- | --- |
| SP-001 | WORK-001 | Validator, rule docs, and tests. | Subprocess validator tests cover accepted detailed plans and rejected shallow plans. | Stay scoped to artifact quality gates. |

## Edge Cases And Failure Modes

Legacy implementation-plan artifacts with missing technical sections or generic work items fail validation before implementation approval.

## Validation Strategy

Execute `python -m unittest discover -s tests`; targeted negative tests remove technical sections and use shallow work item text.

## Risks

Existing in-flight requests may need implementation-plan artifacts refreshed.

## Constraints

Stay scoped and preserve existing approval, review, and fingerprint gates.
"""

IMPLEMENTATION_TEXT = """# Implementation

## Work Completed

Implemented as planned.

## Plan Compliance And Deviations

No deviations.

## Validation

Tests passed and PROB-001 no longer reproduces.

## Review Result

Subagent review passed with no blocking issues.

## Completion Summary

Completed as approved with no residual risk.
"""

STAGES = [
    ("definition", "01-definition", "definition.md", DEFINITION_TEXT),
    ("implementation-plan", "02-implementation-plan", "implementation-plan.md", IMPLEMENTATION_PLAN_TEXT),
    ("implementation", "03-implementation", "implementation.md", IMPLEMENTATION_TEXT),
]
STAGE_BY_PHASE = {phase: (folder, artifact_name, artifact_text) for phase, folder, artifact_name, artifact_text in STAGES}


class ValidatorThreeStageTests(unittest.TestCase):
    def run_validator(self, root: Path, phase: str, reference_root: Path | None = None) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        if reference_root is not None:
            env["STAGEFLOW_REFERENCE_ROOT"] = str(reference_root)
        return subprocess.run(
            [
                sys.executable,
                str(VALIDATOR),
                "--root",
                str(root),
                "--current",
                "--session-id",
                "session-1",
                "--phase",
                phase,
            ],
            text=True,
            capture_output=True,
            env=env,
        )

    def create_project(self, root: Path, state_phase: str = "completed") -> None:
        stageflow = root / ".stageflow"
        request_dir = stageflow / "requests" / REQUEST_ID
        (stageflow / "sessions" / "session-1").mkdir(parents=True)
        request_dir.mkdir(parents=True)
        (stageflow / "index.json").write_text(
            json.dumps(
                {
                    "version": "1",
                    "requests": [
                        {
                            "id": REQUEST_ID,
                            "title": "Test request",
                            "status": state_phase,
                            "created_at": "2026-06-21T03:00:00Z",
                            "updated_at": "2026-06-21T03:00:00Z",
                        }
                    ],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        (stageflow / "sessions" / "session-1" / "current.json").write_text(
            json.dumps({"request_id": REQUEST_ID, "phase": state_phase}, indent=2),
            encoding="utf-8",
        )
        (request_dir / "state.json").write_text(
            json.dumps({"request_id": REQUEST_ID, "phase": state_phase, "last_validated_at": None}, indent=2),
            encoding="utf-8",
        )
        for phase, folder, artifact_name, artifact_text in STAGES:
            stage_dir = request_dir / folder
            stage_dir.mkdir()
            artifact_path = stage_dir / artifact_name
            artifact_path.write_text(artifact_text, encoding="utf-8")
            self.refresh_stage_fingerprint(root, phase)
            (stage_dir / "approval.md").write_text(self.approval_text(phase), encoding="utf-8")

    def refresh_stage_fingerprint(self, root: Path, phase: str) -> None:
        folder, artifact_name, _ = STAGE_BY_PHASE[phase]
        stage_dir = root / ".stageflow" / "requests" / REQUEST_ID / folder
        artifact_path = stage_dir / artifact_name
        fingerprint = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        (stage_dir / "goal.md").write_text(self.goal_text(phase, folder, artifact_name, fingerprint), encoding="utf-8")
        (stage_dir / "review.md").write_text(self.review_text(phase, fingerprint, STAGE_RULE_IDS[phase]), encoding="utf-8")

    def mark_goal_awaiting_user(self, root: Path, phase: str) -> None:
        folder, _, _ = STAGE_BY_PHASE[phase]
        goal_path = root / ".stageflow" / "requests" / REQUEST_ID / folder / "goal.md"
        goal_path.write_text(
            goal_path.read_text(encoding="utf-8").replace(
                "Goal status: active",
                "Goal status: completed\n\nGoal completion reason: awaiting user clarification",
            ),
            encoding="utf-8",
        )

    @staticmethod
    def goal_text(phase: str, folder: str, artifact_name: str, fingerprint: str) -> str:
        return f"""# Goal

Stage: {phase}

Artifact Path: `{folder}/{artifact_name}`

Artifact Fingerprint: sha256:{fingerprint}

## Goal Invocation

Tool: create_goal

Invocation recorded: yes

Invocation result: goal created

## Goal Objective

Advance this stage artifact to the next user input or approval gate.

## Goal Tool Status

Goal created: yes

Goal status: active
"""

    @staticmethod
    def review_text(phase: str, fingerprint: str, rule_ids: list[str]) -> str:
        checklist_rows = "\n".join(f"| {rule_id} | Evidence for {rule_id}. | PASS | None |" for rule_id in rule_ids)
        return f"""# Review

Stage: {phase}

Reviewed Artifact Fingerprint: sha256:{fingerprint}

## Review Method

Subagent review.

## Reviewer

reviewer subagent

## Review Cycle

| Cycle | Reviewer | Result | Notes |
| --- | --- | --- | --- |
| 1 | reviewer subagent | PASS | No blocking issues. |

## Writing And Review Rule Checklist

| Rule ID | Evidence Read | Verdict | Blocking Issue |
| --- | --- | --- | --- |
{checklist_rows}

## Latest Verdict

PASS

## Blocking Issues

No blocking issues

## Final Verdict

No blocking issues.
"""

    @staticmethod
    def approval_text(phase: str) -> str:
        return f"""# Approval

Stage: {phase}

Stage approved: yes

Approved By: user

Approved At: 2026-06-21T03:00:00Z

## Approval Text

Approved.
"""

    def test_print_template_outputs_three_stage_templates(self) -> None:
        expectations = {
            "stage-tree": "01-definition/goal.md",
            "definition": "## Normal Behavior Model",
            "implementation-plan": "## Coverage Matrix",
            "implementation": "## Plan Compliance And Deviations",
            "goal": "Tool: create_goal",
            "review": "DEF-RULE-001",
            "approval": "Stage approved: yes",
        }
        for template, expected in expectations.items():
            with self.subTest(template=template):
                result = subprocess.run(
                    [sys.executable, str(VALIDATOR), "--print-template", template],
                    text=True,
                    capture_output=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(expected, result.stdout)

    def test_old_stage_templates_are_removed(self) -> None:
        for template in ("requirements", "service-plan"):
            with self.subTest(template=template):
                result = subprocess.run(
                    [sys.executable, str(VALIDATOR), "--print-template", template],
                    text=True,
                    capture_output=True,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("invalid choice", result.stderr)

    def test_skill_points_to_three_stage_instruction_files(self) -> None:
        skill_text = (ROOT / "skills" / "stageflow" / "SKILL.md").read_text(encoding="utf-8-sig")
        artifact_text = (ROOT / "skills" / "stageflow" / "references" / "artifact-format.md").read_text(encoding="utf-8-sig")
        for relative in (
            "references/stages/01-definition/definition-writing-and-review-rules.md",
            "references/stages/02-implementation-plan/implementation-plan-writing-and-review-rules.md",
            "references/stages/03-implementation/implementation-writing-and-review-rules.md",
        ):
            with self.subTest(relative=relative):
                self.assertIn(relative, skill_text)
                self.assertIn(relative, artifact_text)
                self.assertIn("## Stage Artifact Format", (ROOT / "skills" / "stageflow" / relative).read_text(encoding="utf-8-sig"))
        self.assertNotIn("references/stages/01-requirements", skill_text)
        self.assertNotIn("references/stages/02-service-plan", skill_text)

    def test_stage_role_and_review_guidance_is_documented(self) -> None:
        definition_rules = (REFERENCE_ROOT / "stages" / "01-definition" / "definition-writing-and-review-rules.md").read_text(encoding="utf-8-sig")
        definition_prompt = (REFERENCE_ROOT / "stages" / "01-definition" / "definition-review-agent-prompt.md").read_text(encoding="utf-8-sig")
        for phrase in (
            "## Stage Responsibility",
            "## Request Type Profiles",
            "## Normal Behavior Transformation",
            "## Late Feedback And Redefinition",
            "DEF-RULE-014",
            "구현 계획으로 넘어가기",
            "Do not automatically invalidate",
        ):
            self.assertIn(phrase, definition_rules)
        for phrase in (
            "Definition Review Agent Prompt",
            "normal behavior model",
            "does not introduce file changes",
            "Self-review never satisfies",
        ):
            self.assertIn(phrase, definition_prompt)

        skill_text = (ROOT / "skills" / "stageflow" / "SKILL.md").read_text(encoding="utf-8-sig")
        implementation_plan_rules = (REFERENCE_ROOT / "stages" / "02-implementation-plan" / "implementation-plan-writing-and-review-rules.md").read_text(encoding="utf-8-sig")
        implementation_rules = (REFERENCE_ROOT / "stages" / "03-implementation" / "implementation-writing-and-review-rules.md").read_text(encoding="utf-8-sig")
        for text, phrase in (
            (skill_text, "Implementation Feedback And Redefinition"),
            (skill_text, "Use selective rework instead of blanket invalidation"),
            (implementation_plan_rules, "## Selective Rework After Definition Changes"),
            (implementation_plan_rules, "Keep unaffected work items"),
            (implementation_rules, "## Selective Rework After Feedback"),
            (implementation_rules, "which completed work remains valid"),
        ):
            self.assertIn(phrase, text)

    def test_validator_docs_use_plugin_script_and_target_root(self) -> None:
        skill_text = (ROOT / "skills" / "stageflow" / "SKILL.md").read_text(encoding="utf-8-sig")
        artifact_text = (ROOT / "skills" / "stageflow" / "references" / "artifact-format.md").read_text(encoding="utf-8-sig")
        hooks_text = (ROOT / "skills" / "stageflow" / "references" / "hooks.md").read_text(encoding="utf-8-sig")
        for text in (skill_text, artifact_text):
            self.assertIn("<plugin-root>/scripts/validate_stageflow.py", text)
            self.assertIn("--root <target-project-root>", text)
        self.assertIn("<plugin-root>/scripts/stageflow_hook_check.py", hooks_text)
        self.assertIn("three-stage workflow", hooks_text)

    def test_valid_three_stage_request_passes_all(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            result = self.run_validator(root, "all")
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertIn("PASS all", result.stdout)

    def test_old_phases_are_rejected(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            for phase in ("requirements", "service-plan"):
                with self.subTest(phase=phase):
                    result = self.run_validator(root, phase)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("invalid choice", result.stderr)

    def test_definition_rule_document_is_required(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            copied_references = root / "references"
            shutil.copytree(REFERENCE_ROOT, copied_references)
            (copied_references / "stages" / "01-definition" / "definition-writing-and-review-rules.md").unlink()
            result = self.run_validator(root, "definition", copied_references)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("definition-writing-and-review-rules.md", result.stdout)

    def test_definition_review_agent_prompt_is_required(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            copied_references = root / "references"
            shutil.copytree(REFERENCE_ROOT, copied_references)
            (copied_references / "stages" / "01-definition" / "definition-review-agent-prompt.md").unlink()
            result = self.run_validator(root, "definition", copied_references)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("definition-review-agent-prompt.md", result.stdout)

    def test_review_checklist_requires_all_rule_ids(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            review = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "review.md"
            review.write_text("\n".join(line for line in review.read_text(encoding="utf-8").splitlines() if "DEF-RULE-004" not in line), encoding="utf-8")
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("DEF-RULE-004", result.stdout)

    def test_definition_requires_requirements_sections(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(DEFINITION_TEXT.replace("## Desired Outcomes", "## Removed Desired Outcomes"), encoding="utf-8")
            self.refresh_stage_fingerprint(root, "definition")
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Desired Outcomes", result.stdout)

    def test_definition_requires_service_behavior_sections(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(DEFINITION_TEXT.replace("## Normal Behavior Model", "## Removed Normal Behavior Model"), encoding="utf-8")
            self.refresh_stage_fingerprint(root, "definition")
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Normal Behavior Model", result.stdout)

    def test_definition_rejects_blocking_open_question(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(DEFINITION_TEXT.replace("| Q-001 | No open question. | N/A | N/A | N/A | N/A | no | N/A |", "| Q-001 | Choose policy. | Ambiguous behavior. | A | B | Changes behavior. | yes | SP-001 |"), encoding="utf-8")
            self.refresh_stage_fingerprint(root, "definition")
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("still blocking", result.stdout)

    def test_definition_requires_implementation_plan_transition_choice(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(DEFINITION_TEXT.replace("User selected `구현 계획으로 넘어가기`", "User selected first proposal").replace("| yes | 구현 계획으로 넘어가기 |", "| no | Continue asking |"), encoding="utf-8")
            self.refresh_stage_fingerprint(root, "definition")
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("implementation-plan transition", result.stdout)

    def test_definition_pending_clarification_returns_awaiting_user(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(
                DEFINITION_TEXT.replace(
                    "| PENDING-000 | No pending clarification. | N/A | N/A | N/A | N/A | none |",
                    "| CLAR-001 | Which docs source-tracking model should definition capture? | Option 1: docs-wide reviewed commit only; Option 2: docs-wide commit plus review-session metadata; 구현 계획으로 넘어가기 | Option 1 | 구현 계획으로 넘어가기 | This changes the approved metadata boundary. | pending |",
                ).replace(
                    "| CLAR-001 | Which correction boundary should definition capture? Options: fix only reported behavior, include adjacent regression guard, 구현 계획으로 넘어가기. | User selected `구현 계획으로 넘어가기`. | yes | 구현 계획으로 넘어가기 | REQ-001, SP-001 |",
                    "| CLAR-000 | No completed clarification yet. | N/A | N/A | N/A | N/A |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "definition")
            self.mark_goal_awaiting_user(root, "definition")
            result = self.run_validator(root, "definition")
            self.assertEqual(result.returncode, 3, result.stdout)
            self.assertIn("AWAITING_USER definition", result.stdout)
            self.assertIn("구현 계획으로 넘어가기", result.stdout)

    def test_pending_clarification_requires_closed_goal(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(DEFINITION_TEXT.replace("| PENDING-000 | No pending clarification. | N/A | N/A | N/A | N/A | none |", "| CLAR-001 | Which model? | Option 1: A; Option 2: B; 구현 계획으로 넘어가기 | Option 1 | 구현 계획으로 넘어가기 | This changes scope. | pending |"), encoding="utf-8")
            self.refresh_stage_fingerprint(root, "definition")
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Goal status: completed", result.stdout)

    def test_implementation_plan_rejects_shallow_work_items(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "02-implementation-plan" / "implementation-plan.md"
            artifact.write_text(IMPLEMENTATION_PLAN_TEXT.replace("Add required technical sections and work-item columns to the stage metadata, then reject generic implementation text.", "Implement behavior."), encoding="utf-8")
            self.refresh_stage_fingerprint(root, "implementation-plan")
            result = self.run_validator(root, "implementation-plan")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("too generic", result.stdout)

    def test_later_stage_validation_requires_earlier_approval(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            approval = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "approval.md"
            approval.write_text(approval.read_text(encoding="utf-8").replace("Approved.", "Not approved."), encoding="utf-8")
            result = self.run_validator(root, "implementation-plan")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Approval Text", result.stdout)


if __name__ == "__main__":
    unittest.main()
