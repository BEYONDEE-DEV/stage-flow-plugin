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
    "requirements": ["REQ-RULE-001", "REQ-RULE-002", "REQ-RULE-003", "REQ-RULE-004"],
    "service-plan": ["SP-RULE-001", "SP-RULE-002", "SP-RULE-003", "SP-RULE-004", "SP-RULE-005"],
    "implementation-plan": [
        "IP-RULE-001",
        "IP-RULE-002",
        "IP-RULE-003",
        "IP-RULE-004",
        "IP-RULE-005",
        "IP-RULE-006",
    ],
    "implementation": ["IMPL-RULE-001", "IMPL-RULE-002", "IMPL-RULE-003", "IMPL-RULE-004", "IMPL-RULE-005"],
}

STAGES = [
    (
        "requirements",
        "01-requirements",
        "requirements.md",
        "# Requirements\n\n"
        "## User Goal\n\nGoal based on inspected project context.\n\n"
        "## Requirements\n\n"
        "| ID | Actor | Trigger | Observable Behavior | Acceptance Evidence | Boundary Or Exclusion | Requirement |\n"
        "| --- | --- | --- | --- | --- | --- | --- |\n"
        "| REQ-001 | User | User requests behavior. | Reviewed behavior is recorded. | Acceptance criteria covers REQ-001. | No unrelated scope. | Requirement. |\n\n"
        "## Acceptance Criteria\n\n- `REQ-001` is satisfied.\n",
    ),
    (
        "service-plan",
        "02-service-plan",
        "service-plan.md",
        "# Service Plan\n\n"
        "## User Visible Behavior\n\nUsers see the changed behavior.\n\n"
        "## Service Behavior\n\nThe service behaves as approved.\n\n"
        "## Policy Rules\n\n"
        "| Rule ID | Trigger Or Condition | Policy | User/System Response | Data/State/API Effect | Failure/Exception Behavior | Source Requirement IDs |\n"
        "| --- | --- | --- | --- | --- | --- | --- |\n"
        "| SP-001 | User requests behavior. | Follow approved behavior. | User sees the planned response. | No API change. | Errors remain recoverable. | REQ-001 |\n\n"
        "## Service API Or Data Flow\n\nNo API change.\n\n"
        "## Boundaries\n\nOnly approved behavior is included.\n\n"
        "## Failure And Exception Behavior\n\nErrors remain recoverable.\n",
    ),
    (
        "implementation-plan",
        "03-implementation-plan",
        "implementation-plan.md",
        "# Implementation Plan\n\n"
        "## Change Areas\n\nCode and tests.\n\n"
        "## Work Items\n\n"
        "| ID | Work Item | Evidence |\n"
        "| --- | --- | --- |\n"
        "| WORK-001 | Implement behavior. | Tests. |\n\n"
        "## Coverage Matrix\n\n"
        "| Service Rule ID | Work Item ID | Change Area | Validation Evidence | Risk/Constraint |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| SP-001 | WORK-001 | Code and tests. | Test output. | Stay scoped. |\n\n"
        "## Validation\n\n- Run tests.\n\n"
        "## Risks\n\nNone.\n\n"
        "## Constraints\n\nStay scoped.\n",
    ),
    (
        "implementation",
        "04-implementation",
        "implementation.md",
        "# Implementation\n\n"
        "## Work Completed\n\nImplemented as planned; no deviations.\n\n"
        "## Validation\n\nTests passed.\n\n"
        "## Review Result\n\nSubagent review passed with no blocking issues.\n\n"
        "## Completion Summary\n\nCompleted as approved.\n",
    ),
]


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

Execute this stage.

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
            self.assertTrue(result["request_creation_required"])
            self.assertTrue(result["preflight_required"])
            self.assertIn("request-required", result["preflight_marker"])

    def test_plain_prompt_without_current_prepasses(self) -> None:
        with temp_project() as tmp:
            result = self.run_hook(Path(tmp), "user_prompt_submit", {"session_id": "session-1", "prompt": "hello"})
            self.assertEqual(result["status"], "PREPASS")
            self.assertFalse(result["preflight_required"])

    def test_active_request_emits_preflight_marker(self) -> None:
        with temp_project() as tmp:
            root = Path(tmp)
            self.create_project(root, "requirements")
            result = self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "workflow status"})
            self.assertEqual(result["status"], "OK")
            self.assertTrue(result["preflight_required"])
            self.assertIn("Stageflow preflight", result["preflight_marker"])
            self.assertEqual(result["validation"]["status"], "PASS")

    def test_implementation_prompt_checks_implementation_plan_gate(self) -> None:
        with temp_project() as tmp:
            root = Path(tmp)
            self.create_project(root, "implementation")
            approval = root / ".stageflow" / "requests" / REQUEST_ID / "03-implementation-plan" / "approval.md"
            approval.write_text(approval.read_text(encoding="utf-8").replace("Approved.", "Not approved."), encoding="utf-8")
            result = self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "workflow implement"})
            self.assertEqual(result["status"], "WARNING")
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


if __name__ == "__main__":
    unittest.main()