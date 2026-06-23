from __future__ import annotations

import contextlib
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK_CHECK = ROOT / "scripts" / "stageflow_hook_check.py"
REQUEST_ID = "20260621-1200-test-request"
TMP_ROOT = Path(os.environ.get("STAGEFLOW_TEST_TMP", str(ROOT / "tests" / "tmp")))
TMP_ROOT.mkdir(parents=True, exist_ok=True)


@contextlib.contextmanager
def temp_project():
    path = TMP_ROOT / f"case-{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    try:
        yield str(path)
    finally:
        shutil.rmtree(path, ignore_errors=True)

STAGE_RULE_IDS = {
    "requirements": [
        "REQ-RULE-001",
        "REQ-RULE-002",
        "REQ-RULE-003",
        "REQ-RULE-004",
        "REQ-RULE-005",
        "REQ-RULE-006",
        "REQ-RULE-007",
        "REQ-RULE-008",
        "REQ-RULE-009",
        "REQ-RULE-010",
    ],
    "service-plan": [
        "SP-RULE-001",
        "SP-RULE-002",
        "SP-RULE-003",
        "SP-RULE-004",
        "SP-RULE-005",
        "SP-RULE-006",
        "SP-RULE-007",
        "SP-RULE-008",
        "SP-RULE-009",
    ],
    "implementation-plan": [
        "IP-RULE-001",
        "IP-RULE-002",
        "IP-RULE-003",
        "IP-RULE-004",
        "IP-RULE-005",
        "IP-RULE-006",
        "IP-RULE-007",
        "IP-RULE-008",
    ],
    "implementation": [
        "IMPL-RULE-001",
        "IMPL-RULE-002",
        "IMPL-RULE-003",
        "IMPL-RULE-004",
        "IMPL-RULE-005",
        "IMPL-RULE-006",
    ],
}
STAGES = [
    (
        "requirements",
        "01-requirements",
        "requirements.md",
        "# Requirements\n\n"
        "## User Goal\n\nGoal based on inspected project context.\n\n"
        "## Request Profile\n\nPrimary: bugfix\nSecondary: feature-adjustment\n\n"
        "## Desired Outcomes\n\n"
        "| ID | Outcome | Source | Success Signal |\n"
        "| --- | --- | --- | --- |\n"
        "| OUT-001 | User can complete the corrected behavior. | User request. | Acceptance criteria covers REQ-001. |\n\n"
        "## Current Problems\n\n"
        "| ID | Problem | Expected Behavior | Actual Behavior | Evidence Or Reproduction | Impact |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| PROB-001 | Existing behavior is wrong. | Corrected behavior is available. | Incorrect behavior is present. | Reproduction notes. | User workflow is affected. |\n\n"
        "## Problem-To-Requirement Mapping\n\n"
        "| Problem ID | Requirement ID | Resolution |\n"
        "| --- | --- | --- |\n"
        "| PROB-001 | REQ-001 | REQ-001 defines the corrected behavior. |\n\n"
        "## User-Specified Constraints\n\n- User supplied constraint.\n\n"
        "## Discovered Constraints\n\n- Project inspection constraint.\n\n"
        "## Pending Clarifications\n\n"
        "| ID | Question | Options | Recommended Option | Transition Option | Why This Matters | Status |\n"
        "| --- | --- | --- | --- | --- | --- | --- |\n"
        "| PENDING-000 | No pending clarification. | N/A | N/A | N/A | N/A | none |\n\n"
        "## Clarification History\n\n"
        "| Round ID | Questions Asked | User Response | Service Plan Option Offered | User Transition Signal | Reflected In |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| CLAR-001 | Which correction boundary should requirements capture? Options: fix only reported behavior, include adjacent regression guard, 서비스 계획으로 넘어가기. | User selected `서비스 계획으로 넘어가기`. | yes | 서비스 계획으로 넘어가기 | N/A |\n\n"
        "## Open Questions\n\n"
        "| ID | Decision Needed | Context Or Conflict | Recommended Option | Alternatives | Impact | Blocking | Resolution Target |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
        "| Q-001 | No open question. | N/A | N/A | N/A | N/A | no | N/A |\n\n"
        "## Resolved Decisions\n\n"
        "| ID | Source Question ID | Answer Source | Decision | Reflected In |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| DEC-001 | N/A | N/A | No resolved decision yet. | N/A |\n\n"
        "## Requirements\n\n"
        "| ID | Type | Source | Requirement Detail | Boundary Or Exclusion | Linked Outcomes Or Problems |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| REQ-001 | bugfix | User request. | Implement corrected behavior. | No unrelated scope. | OUT-001, PROB-001 |\n\n"
        "## Acceptance Criteria\n\n- `REQ-001` is satisfied when `OUT-001` is verifiable and `PROB-001` is resolved.\n",
    ),
    (
        "service-plan",
        "02-service-plan",
        "service-plan.md",
        "# Service Plan\n\n"
        "## Normal Behavior Model\n\nThe service exposes the corrected normal behavior and prevents the reported regression.\n\n"
        "## User Flow\n\nUsers see the changed behavior in the approved flow.\n\n"
        "## State And Policy Model\n\nState changes follow the approved policy.\n\n"
        "## Pending Clarifications\n\n"
        "| ID | Question | Options | Recommended Option | Transition Option | Why This Matters | Status |\n"
        "| --- | --- | --- | --- | --- | --- | --- |\n"
        "| PENDING-000 | No pending clarification. | N/A | N/A | N/A | N/A | none |\n\n"
        "## Clarification History\n\n"
        "| Round ID | Questions Asked | User Response | Implementation Plan Option Offered | User Transition Signal | Reflected In |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| SVC-CLAR-001 | Which service behavior should the plan capture? Options: preserve current service flow, add explicit regression recovery, 구현 계획으로 넘어가기. | User selected `구현 계획으로 넘어가기`. | yes | 구현 계획으로 넘어가기 | N/A |\n\n"
        "## Policy Rules\n\n"
        "| Rule ID | Trigger Or Condition | Policy | User/System Response | State/Data Responsibility | Failure/Recovery Behavior | Source Requirement IDs |\n"
        "| --- | --- | --- | --- | --- | --- | --- |\n"
        "| SP-001 | User requests behavior. | Follow approved behavior. | User sees the planned response. | Required state is updated. | Errors remain recoverable. | REQ-001 |\n\n"
        "## Integration Flow And Data Responsibilities\n\nNo integration change.\n\n"
        "## Boundaries\n\nOnly approved behavior is included.\n\n"
        "## Regression Prevention\n\nPROB-001 must not recur.\n\n"
        "## Failure And Recovery Behavior\n\nErrors remain recoverable.\n",
    ),
    (
        "implementation-plan",
        "03-implementation-plan",
        "implementation-plan.md",
        "# Implementation Plan\n\n"
        "## Technical Approach\n\nExtend the existing validator-driven Stageflow architecture so the same stage metadata and markdown table checks enforce the approved behavior.\n\n"
        "## Implementation Architecture\n\n`scripts/validate_stageflow.py` validates stage sections and tables, stage rule markdown defines authoring contracts, and subprocess tests verify fixture requests through the public CLI.\n\n"
        "## Change Areas\n\nValidator metadata, stage rule markdown, review prompts, and test fixtures.\n\n"
        "## Cause Or Design Notes\n\nRoot cause and design notes are grounded in SP-001. The technical contract must reject shallow implementation plans before approval.\n\n"
        "## Work Items\n\n"
        "| ID | Implementation Unit | Technical Design | Completion Evidence |\n"
        "| --- | --- | --- | --- |\n"
        "| WORK-001 | Implementation-plan validator contract. | Add required technical sections and work-item columns to the stage metadata, then reject generic implementation text. | Validator failure tests and full unittest output. |\n\n"
        "## Coverage Matrix\n\n"
        "| Service Rule ID | Work Item ID | Change Area | Validation Evidence | Risk/Constraint |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| SP-001 | WORK-001 | Validator, rule docs, and tests. | Subprocess validator tests cover accepted detailed plans and rejected shallow plans. | Stay scoped to artifact quality gates. |\n\n"
        "## Edge Cases And Failure Modes\n\nLegacy plans with missing technical sections or generic work items fail validation before implementation approval.\n\n"
        "## Validation Strategy\n\nRun `python -m unittest discover -s tests`; targeted negative tests remove technical sections and use shallow work item text.\n\n"
        "## Risks\n\nExisting in-flight requests may need implementation-plan artifacts refreshed.\n\n"
        "## Constraints\n\nStay scoped and preserve existing approval, review, and fingerprint gates.\n",
    ),
    (
        "implementation",
        "04-implementation",
        "implementation.md",
        "# Implementation\n\n"
        "## Work Completed\n\nImplemented as planned.\n\n"
        "## Plan Compliance And Deviations\n\nNo deviations.\n\n"
        "## Validation\n\nTests passed and PROB-001 no longer reproduces.\n\n"
        "## Review Result\n\nSubagent review passed with no blocking issues.\n\n"
        "## Completion Summary\n\nCompleted as approved with no residual risk.\n",
    ),
]
STAGE_BY_PHASE = {phase: (folder, artifact_name, artifact_text) for phase, folder, artifact_name, artifact_text in STAGES}


class HookCheckFourStageTests(unittest.TestCase):
    def run_hook(
        self,
        root: Path,
        event: str,
        payload: dict[str, object],
        expected_returncode: int = 0,
    ) -> dict[str, object]:
        proc = subprocess.run(
            [sys.executable, str(HOOK_CHECK), "--event", event, "--root", str(root)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
        )
        self.assertEqual(proc.returncode, expected_returncode, proc.stdout + proc.stderr)
        return json.loads(proc.stdout)
    def create_project(self, root: Path, state_phase: str = "requirements") -> None:
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
            fingerprint = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
            (stage_dir / "goal.md").write_text(self.goal_text(phase, folder, artifact_name, fingerprint), encoding="utf-8")
            (stage_dir / "review.md").write_text(
                self.review_text(phase, fingerprint, STAGE_RULE_IDS[phase]),
                encoding="utf-8",
            )
            (stage_dir / "approval.md").write_text(self.approval_text(phase), encoding="utf-8")

    def refresh_stage_fingerprint(self, root: Path, phase: str) -> None:
        folder, artifact_name, _ = STAGE_BY_PHASE[phase]
        stage_dir = root / ".stageflow" / "requests" / REQUEST_ID / folder
        artifact_path = stage_dir / artifact_name
        fingerprint = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        (stage_dir / "goal.md").write_text(self.goal_text(phase, folder, artifact_name, fingerprint), encoding="utf-8")
        (stage_dir / "review.md").write_text(
            self.review_text(phase, fingerprint, STAGE_RULE_IDS[phase]),
            encoding="utf-8",
        )

    def mark_goal_awaiting_user(self, root: Path, phase: str) -> None:
        folder, _, _ = STAGE_BY_PHASE[phase]
        goal_path = root / ".stageflow" / "requests" / REQUEST_ID / folder / "goal.md"
        text = goal_path.read_text(encoding="utf-8")
        text = text.replace(
            "Goal status: active",
            "Goal status: completed\n\nGoal completion reason: awaiting user clarification",
        )
        goal_path.write_text(text, encoding="utf-8")

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
        checklist_rows = "\n".join(
            f"| {rule_id} | Evidence for {rule_id}. | PASS | None |" for rule_id in rule_ids
        )
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

    def test_explicit_workflow_without_current_requires_request(self) -> None:
        with temp_project() as tmp:
            result = self.run_hook(Path(tmp), "user_prompt_submit", {"session_id": "session-1", "prompt": "workflow status"})
            self.assertEqual(result["status"], "REQUEST_REQUIRED")
            self.assertEqual(result["turn_start_action"], "create_request")
            self.assertTrue(result["state_handling_required"])
            self.assertTrue(result["request_creation_required"])
            self.assertTrue(result["preflight_required"])
            self.assertIn("request-required", result["preflight_marker"])

    def test_plain_prompt_without_current_prepasses(self) -> None:
        with temp_project() as tmp:
            result = self.run_hook(Path(tmp), "user_prompt_submit", {"session_id": "session-1", "prompt": "hello"})
            self.assertEqual(result["status"], "PREPASS")
            self.assertEqual(result["turn_start_action"], "none")
            self.assertFalse(result["state_handling_required"])
            self.assertFalse(result["preflight_required"])

    def test_invalid_current_requires_pointer_repair(self) -> None:
        with temp_project() as tmp:
            root = Path(tmp)
            current_dir = root / ".stageflow" / "sessions" / "session-1"
            current_dir.mkdir(parents=True)
            (current_dir / "current.json").write_text(
                json.dumps({"request_id": "missing-request", "phase": "requirements"}, indent=2),
                encoding="utf-8",
            )
            result = self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "workflow status"})
            self.assertEqual(result["status"], "INVALID_CURRENT")
            self.assertEqual(result["turn_start_action"], "repair_current_pointer")
            self.assertTrue(result["state_handling_required"])

    def test_active_request_emits_preflight_marker(self) -> None:
        with temp_project() as tmp:
            root = Path(tmp)
            self.create_project(root, "requirements")
            result = self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "workflow status"})
            self.assertEqual(result["status"], "OK")
            self.assertEqual(result["turn_start_action"], "continue_current_stage")
            self.assertFalse(result["state_handling_required"])
            self.assertTrue(result["preflight_required"])
            self.assertIn("Stageflow preflight", result["preflight_marker"])
            self.assertEqual(result["validation"]["status"], "PASS")

    def test_completed_current_requires_new_request(self) -> None:
        with temp_project() as tmp:
            root = Path(tmp)
            self.create_project(root, "completed")
            result = self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "workflow status"})
            self.assertEqual(result["status"], "COMPLETED_CURRENT")
            self.assertEqual(result["turn_start_action"], "start_new_request")
            self.assertTrue(result["state_handling_required"])
            self.assertEqual(result["validation"]["status"], "PASS")

    def test_implementation_prompt_checks_implementation_plan_gate(self) -> None:
        with temp_project() as tmp:
            root = Path(tmp)
            self.create_project(root, "implementation")
            approval = root / ".stageflow" / "requests" / REQUEST_ID / "03-implementation-plan" / "approval.md"
            approval.write_text(approval.read_text(encoding="utf-8").replace("Approved.", "Not approved."), encoding="utf-8")
            result = self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "workflow implement"})
            self.assertEqual(result["status"], "IMPLEMENTATION_BLOCKED")
            self.assertEqual(result["turn_start_action"], "repair_implementation_plan_gate")
            self.assertTrue(result["state_handling_required"])
            self.assertEqual(result["implementation_entry_gate"]["status"], "FAIL")
            self.assertIn("implementation requested before implementation-plan stage passed", result["warnings"])

    def test_stop_warns_when_required_marker_missing(self) -> None:
        with temp_project() as tmp:
            root = Path(tmp)
            self.create_project(root, "requirements")
            self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "workflow status"})
            result = self.run_hook(
                root,
                "stop",
                {"session_id": "session-1", "last_assistant_message": "status answered"},
                expected_returncode=2,
            )
            self.assertEqual(result["status"], "BLOCKED")
            self.assertEqual(result["decision"], "block")
            self.assertIn("preflight marker", "\n".join(result["warnings"]))

    def test_explicit_workflow_without_current_blocks_stop_if_not_created(self) -> None:
        with temp_project() as tmp:
            root = Path(tmp)
            prompt_result = self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "workflow status"})
            marker = str(prompt_result["preflight_marker"])
            result = self.run_hook(
                root,
                "stop",
                {"session_id": "session-1", "last_assistant_message": marker + "\nstatus answered"},
                expected_returncode=2,
            )
            self.assertEqual(result["status"], "BLOCKED")
            self.assertIn("session current pointer", "\n".join(result["warnings"]))

    def test_pre_tool_use_blocks_non_stageflow_write_before_implementation_plan_passes(self) -> None:
        with temp_project() as tmp:
            root = Path(tmp)
            self.create_project(root, "implementation")
            approval = root / ".stageflow" / "requests" / REQUEST_ID / "03-implementation-plan" / "approval.md"
            approval.write_text(approval.read_text(encoding="utf-8").replace("Approved.", "Not approved."), encoding="utf-8")
            result = self.run_hook(
                root,
                "pre_tool_use",
                {"session_id": "session-1", "tool_name": "Write", "tool_input": {"file_path": "src/app.ts"}},
                expected_returncode=2,
            )
            self.assertEqual(result["status"], "BLOCKED")
            self.assertEqual(result["implementation_entry_gate"]["status"], "FAIL")

    def test_pre_tool_use_allows_stageflow_artifact_write_before_implementation_plan_passes(self) -> None:
        with temp_project() as tmp:
            root = Path(tmp)
            self.create_project(root, "requirements")
            approval = root / ".stageflow" / "requests" / REQUEST_ID / "03-implementation-plan" / "approval.md"
            approval.write_text(approval.read_text(encoding="utf-8").replace("Approved.", "Not approved."), encoding="utf-8")
            result = self.run_hook(
                root,
                "pre_tool_use",
                {
                    "session_id": "session-1",
                    "tool_name": "Write",
                    "tool_input": {"file_path": ".stageflow/requests/20260621-1200-test-request/01-requirements/requirements.md"},
                },
            )
            self.assertEqual(result["status"], "PREPASS")
            self.assertTrue(result["stageflow_artifact_write"])

    def test_pre_tool_use_allows_read_only_shell_command(self) -> None:
        with temp_project() as tmp:
            result = self.run_hook(
                Path(tmp),
                "pre_tool_use",
                {"session_id": "session-1", "tool_name": "shell_command", "tool_input": {"command": "rg Stageflow"}},
            )
            self.assertEqual(result["status"], "PREPASS")

    def test_completion_like_stop_runs_all_validation(self) -> None:
        with temp_project() as tmp:
            root = Path(tmp)
            self.create_project(root, "completed")
            prompt_result = self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "workflow status"})
            marker = str(prompt_result["preflight_marker"])
            result = self.run_hook(root, "stop", {"session_id": "session-1", "last_assistant_message": marker + "\ncompleted"})
            self.assertEqual(result["completion_validation"]["status"], "PASS")


    def test_pending_clarification_returns_awaiting_user_action(self) -> None:
        with temp_project() as tmp:
            root = Path(tmp)
            self.create_project(root, "service-plan")
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "02-service-plan" / "service-plan.md"
            artifact.write_text(
                artifact.read_text(encoding="utf-8").replace(
                    "| PENDING-000 | No pending clarification. | N/A | N/A | N/A | N/A | none |",
                    "| SVC-CLAR-001 | How should docs sync status be represented? | Option 1: docs-wide status only; Option 2: docs-wide status plus partial review notes; 구현 계획으로 넘어가기 | Option 2 | 구현 계획으로 넘어가기 | This is the current unanswered service decision. | pending |",
                ).replace(
                    "| SVC-CLAR-001 | Which service behavior should the plan capture? Options: preserve current service flow, add explicit regression recovery, 구현 계획으로 넘어가기. | User selected `구현 계획으로 넘어가기`. | yes | 구현 계획으로 넘어가기 | N/A |",
                    "| SVC-CLAR-000 | No completed clarification yet. | N/A | N/A | N/A | N/A |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "service-plan")
            self.mark_goal_awaiting_user(root, "service-plan")
            result = self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "workflow status"})
            self.assertEqual(result["status"], "AWAITING_USER")
            self.assertEqual(result["turn_start_action"], "await_user_clarification")
            self.assertEqual(result["validation"]["status"], "AWAITING_USER")
            self.assertIn("How should docs sync status", result["pending_clarification_output"])
            self.assertIn("구현 계획으로 넘어가기", result["pending_clarification_output"])
            self.assertNotIn("current Stageflow stage validation failed", result["warnings"])

    def test_awaiting_user_stop_blocks_response_without_pending_questions(self) -> None:
        with temp_project() as tmp:
            root = Path(tmp)
            self.create_project(root, "service-plan")
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "02-service-plan" / "service-plan.md"
            artifact.write_text(
                artifact.read_text(encoding="utf-8").replace(
                    "| PENDING-000 | No pending clarification. | N/A | N/A | N/A | N/A | none |",
                    "| SVC-CLAR-001 | How should docs sync status be represented? | Option 1: docs-wide status only; Option 2: docs-wide status plus partial review notes; 구현 계획으로 넘어가기 | Option 2 | 구현 계획으로 넘어가기 | This is the current unanswered service decision. | pending |",
                ).replace(
                    "| SVC-CLAR-001 | Which service behavior should the plan capture? Options: preserve current service flow, add explicit regression recovery, 구현 계획으로 넘어가기. | User selected `구현 계획으로 넘어가기`. | yes | 구현 계획으로 넘어가기 | N/A |",
                    "| SVC-CLAR-000 | No completed clarification yet. | N/A | N/A | N/A | N/A |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "service-plan")
            self.mark_goal_awaiting_user(root, "service-plan")
            prompt_result = self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "workflow status"})
            marker = str(prompt_result["preflight_marker"])
            result = self.run_hook(
                root,
                "stop",
                {"session_id": "session-1", "last_assistant_message": marker + "\n대기 중입니다."},
                expected_returncode=2,
            )
            self.assertEqual(result["status"], "BLOCKED")
            self.assertIn("pending clarification questions and options", "\n".join(result["warnings"]))

    def test_awaiting_user_stop_blocks_completion_claim_even_with_questions(self) -> None:
        with temp_project() as tmp:
            root = Path(tmp)
            self.create_project(root, "service-plan")
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "02-service-plan" / "service-plan.md"
            artifact.write_text(
                artifact.read_text(encoding="utf-8").replace(
                    "| PENDING-000 | No pending clarification. | N/A | N/A | N/A | N/A | none |",
                    "| SVC-CLAR-001 | How should docs sync status be represented? | Option 1: docs-wide status only; Option 2: docs-wide status plus partial review notes; 구현 계획으로 넘어가기 | Option 2 | 구현 계획으로 넘어가기 | This is the current unanswered service decision. | pending |",
                ).replace(
                    "| SVC-CLAR-001 | Which service behavior should the plan capture? Options: preserve current service flow, add explicit regression recovery, 구현 계획으로 넘어가기. | User selected `구현 계획으로 넘어가기`. | yes | 구현 계획으로 넘어가기 | N/A |",
                    "| SVC-CLAR-000 | No completed clarification yet. | N/A | N/A | N/A | N/A |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "service-plan")
            self.mark_goal_awaiting_user(root, "service-plan")
            prompt_result = self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "workflow status"})
            marker = str(prompt_result["preflight_marker"])
            last_message = (
                marker
                + "\n질문: How should docs sync status be represented?\n"
                + "선택지: Option 1: docs-wide status only / Option 2: docs-wide status plus partial review notes / 구현 계획으로 넘어가기\n"
                + "목표를 달성했습니다."
            )
            result = self.run_hook(
                root,
                "stop",
                {"session_id": "session-1", "last_assistant_message": last_message},
                expected_returncode=2,
            )
            self.assertEqual(result["status"], "BLOCKED")
            self.assertIn("must not claim completion", "\n".join(result["warnings"]))

if __name__ == "__main__":
    unittest.main()
