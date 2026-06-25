
from __future__ import annotations

import contextlib
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK_CHECK = ROOT / "scripts" / "stageflow_hook_check.py"
REQUEST_ID = "20260621-1200-test-request"
TMP_ROOT = Path(os.environ.get("STAGEFLOW_TEST_TMP", str(Path(tempfile.gettempdir()) / "stageflow-plugin-tests")))
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
    "definition": [f"DEF-RULE-{index:03d}" for index in range(1, 17)],
    "implementation-plan": [f"IP-RULE-{index:03d}" for index in range(1, 9)],
    "implementation": [f"IMPL-RULE-{index:03d}" for index in range(1, 7)],
}

DEFINITION_TEXT = """# Definition

## User Goal

Goal based on inspected project context.

## Purpose And Intent

| Purpose | User Value | Business/Product Value | Source | Confidence |
| --- | --- | --- | --- | --- |
| Correct the behavior so the user's workflow succeeds. | User can complete the affected workflow without the current failure. | Preserves product reliability for the affected workflow. | user request | confirmed |

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

| ID | Question Scope | Question | Options | Recommended Option | Transition Option | Why This Matters | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PENDING-000 | N/A | No pending clarification. | N/A | N/A | N/A | N/A | none |

## Clarification History

| Round ID | Questions Asked | User Response | Implementation Plan Option Offered | User Transition Signal | Reflected In |
| --- | --- | --- | --- | --- | --- |
| CLAR-001 | Which correction boundary should definition capture? Options: fix only reported behavior, include adjacent regression guard. | User said `질문 그만, 구현 계획으로 넘어가기`. | no | 질문 그만, 구현 계획으로 넘어가기 | REQ-001, SP-001 |

## Open Questions

| ID | Decision Needed | Context Or Conflict | Recommended Option | Alternatives | Impact | Blocking | Resolution Target |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Q-001 | No open question. | N/A | N/A | N/A | N/A | no | N/A |

## Resolved Decisions

| ID | Source Question ID | Answer Source | Decision | Reflected In |
| --- | --- | --- | --- | --- |
| DEC-001 | N/A | N/A | No resolved decision yet. | N/A |

## Intent Fidelity

| ID | User Wording | Normalized Requirement | Allowed Interpretations | Disallowed Interpretations | Linked Requirement/Policy |
| --- | --- | --- | --- | --- | --- |
| INTENT-001 | User requested corrected behavior. | Implement corrected behavior without unrelated scope. | The existing behavior is corrected according to REQ-001. | New UX meaning, unrelated routes, or extra product policy. | REQ-001, SP-001 |

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

## Definition Fidelity Matrix

| Work Item ID | Definition Source | Approved Meaning | Technical Interpretation | Must Not Interpret As | If Ambiguous |
| --- | --- | --- | --- | --- | --- |
| WORK-001 | REQ-001, SP-001, INTENT-001 | Enforce the approved artifact quality gate. | Add validator metadata, rule docs, prompts, and tests for that gate. | New product behavior, new approval semantics, or unrelated workflow changes. | Return to definition before planning a new meaning. |

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


class HookCheckThreeStageTests(unittest.TestCase):
    def read_hook_state(self, root: Path, payload: dict[str, object]) -> dict[str, object]:
        session_id = str(payload.get("session_id") or "no-session")
        agent_id = str(payload.get("agent_id") or "").strip()
        paths = []
        if agent_id:
            paths.append(root / ".stageflow" / "hook-state" / "sessions" / session_id / "agents" / agent_id / "current-turn.json")
        paths.extend(
            [
                root / ".stageflow" / "hook-state" / "sessions" / session_id / "main" / "current-turn.json",
                root / ".stageflow" / "hook-state" / "current-turn.json",
            ]
        )
        for path in paths:
            if path.is_file():
                return json.loads(path.read_text(encoding="utf-8"))
        return {}

    def run_hook(self, root: Path, event: str, payload: dict[str, object], expected_returncode: int = 0) -> dict[str, object]:
        proc = subprocess.run(
            [sys.executable, str(HOOK_CHECK), "--event", event, "--root", str(root)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
        )
        self.assertEqual(proc.returncode, expected_returncode, proc.stdout + proc.stderr)
        wire_output = json.loads(proc.stdout) if proc.stdout.strip() else {}
        result = self.read_hook_state(root, payload) if event in {"user_prompt_submit", "subagent_start", "subagent_stop"} else {}
        if not result:
            result = {"status": "PREPASS", "turn_start_action": "none", "warnings": []}
        if wire_output.get("decision") == "block":
            result.update({"status": "BLOCKED", "reason": wire_output.get("reason")})
            result.setdefault("warnings", []).append(str(wire_output.get("reason") or ""))
        hook_output = wire_output.get("hookSpecificOutput") if isinstance(wire_output.get("hookSpecificOutput"), dict) else {}
        if hook_output.get("permissionDecision") == "deny":
            reason = str(hook_output.get("permissionDecisionReason") or "")
            result.update({"status": "BLOCKED", "reason": reason})
            result.setdefault("warnings", []).append(reason)
        if wire_output.get("continue") is False:
            reason = str(wire_output.get("stopReason") or "")
            result.update({"status": "BLOCKED", "reason": reason})
            result.setdefault("warnings", []).append(reason)
        result["_wire_output"] = wire_output
        result["_stdout"] = proc.stdout
        result["_stderr"] = proc.stderr
        result["_returncode"] = proc.returncode
        return result

    def create_project(self, root: Path, state_phase: str = "definition") -> None:
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
            if phase == "definition":
                self.write_transition_risk_files(root, fingerprint)
            else:
                (stage_dir / "goal.md").write_text(self.goal_text(phase, folder, artifact_name, fingerprint), encoding="utf-8")
            (stage_dir / "review.md").write_text(self.review_text(phase, fingerprint, STAGE_RULE_IDS[phase]), encoding="utf-8")
            (stage_dir / "approval.md").write_text(self.approval_text(phase), encoding="utf-8")

    def refresh_stage_fingerprint(self, root: Path, phase: str) -> None:
        folder, artifact_name, _ = STAGE_BY_PHASE[phase]
        stage_dir = root / ".stageflow" / "requests" / REQUEST_ID / folder
        artifact_path = stage_dir / artifact_name
        fingerprint = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        if phase == "definition":
            self.write_transition_risk_files(root, fingerprint)
        else:
            (stage_dir / "goal.md").write_text(self.goal_text(phase, folder, artifact_name, fingerprint), encoding="utf-8")
        (stage_dir / "review.md").write_text(self.review_text(phase, fingerprint, STAGE_RULE_IDS[phase]), encoding="utf-8")


    def write_pending_definition(self, root: Path) -> None:
        artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
        artifact.write_text(
            artifact.read_text(encoding="utf-8").replace(
                "| PENDING-000 | N/A | No pending clarification. | N/A | N/A | N/A | N/A | none |",
                "| PENDING-001 | 큰방향 | Docs sync status의 큰방향 범위는 어디까지인가요? | Option 1: docs-wide status only; Option 2: docs-wide status plus review-session scope; Option 3: docs-wide status plus hook metadata | Option 1 | N/A | 큰방향 상태 범위부터 정합니다. | pending |",
            ).replace(
                "| CLAR-001 | Which correction boundary should definition capture? Options: fix only reported behavior, include adjacent regression guard. | User said `질문 그만, 구현 계획으로 넘어가기`. | no | 질문 그만, 구현 계획으로 넘어가기 | REQ-001, SP-001 |",
                "| CLAR-000 | No completed clarification yet. | N/A | no | N/A | N/A |",
            ),
            encoding="utf-8",
        )
        self.refresh_stage_fingerprint(root, "definition")

    def write_transition_risk_files(self, root: Path, fingerprint: str | None = None) -> None:
        stage_dir = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition"
        if fingerprint is None:
            fingerprint = hashlib.sha256((stage_dir / "definition.md").read_bytes()).hexdigest()
        (stage_dir / "transition-risk-goal.md").write_text(self.transition_risk_goal_text(fingerprint), encoding="utf-8")
        (stage_dir / "transition-risk.md").write_text(self.transition_risk_text(), encoding="utf-8")

    @staticmethod
    def transition_risk_goal_text(fingerprint: str) -> str:
        return f"""# Transition Risk Goal

Stage: definition

Purpose: transition-risk

Artifact Path: `01-definition/transition-risk.md`

Definition Artifact Fingerprint: sha256:{fingerprint}

## Goal Invocation

Tool: create_goal

Invocation recorded: yes

Invocation result: goal created

## Goal Objective

Generate transition risk cases before implementation planning and collect user confirmation before definition approval.

## Goal Tool Status

Goal created: yes

Goal status: completed
"""

    @staticmethod
    def transition_risk_text() -> str:
        return """# Transition Risk

## Risk Generation Basis

Generated after the user stop signal using the current definition artifact, with no automatic requirement changes before user confirmation.

## Generated Risk Cases

| ID | Category | Risk Case | Affected Definition Area | Definition Coverage | Prior Answer Check | Suggested Handling | User Confirmation | Disposition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RISK-001 | implementation-readiness | No material transition risks found. | Requirements, Acceptance Criteria, Policy Rules, Boundaries, Failure And Recovery Behavior, Regression Prevention | not-applicable | not-applicable | Proceed after user confirmation. | User confirmed no material risks. | not-applicable |

## Suggested Definition Updates

No definition updates required.

## User Confirmation

User confirmed generated transition risk disposition before definition approval.

## Final Disposition

All generated risk cases are confirmed and no follow-up clarification is required.
"""

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

    def test_explicit_workflow_without_current_requires_request(self) -> None:
        with temp_project() as root:
            result = self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "workflow status"})
            self.assertEqual(result["status"], "REQUEST_REQUIRED")
            self.assertEqual(result["turn_start_action"], "create_request")
            self.assertTrue(result["request_creation_required"])
            wire_output = result["_wire_output"]
            self.assertEqual(set(wire_output), {"hookSpecificOutput"})
            hook_output = wire_output["hookSpecificOutput"]
            self.assertEqual(hook_output["hookEventName"], "UserPromptSubmit")
            self.assertIn("REQUEST_REQUIRED", hook_output["additionalContext"])
            self.assertIn("create_request", hook_output["additionalContext"])
            self.assertNotIn("event", wire_output)
            self.assertNotIn("status", wire_output)
            self.assertNotIn("turn_start_action", wire_output)

    def test_plain_prompt_without_current_prepasses(self) -> None:
        with temp_project() as root:
            result = self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "hello"})
            self.assertEqual(result["status"], "PREPASS")
            self.assertEqual(result["turn_start_action"], "none")
            self.assertEqual(result["_stdout"], "")

    def test_invalid_current_requires_pointer_repair(self) -> None:
        with temp_project() as root:
            current_dir = root / ".stageflow" / "sessions" / "session-1"
            current_dir.mkdir(parents=True)
            (current_dir / "current.json").write_text(json.dumps({"request_id": "missing-request", "phase": "definition"}, indent=2), encoding="utf-8")
            result = self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "workflow status"})
            self.assertEqual(result["status"], "INVALID_CURRENT")
            self.assertEqual(result["turn_start_action"], "repair_current_pointer")

    def test_active_definition_request_emits_preflight_marker(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            result = self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "workflow status"})
            self.assertEqual(result["status"], "OK")
            self.assertEqual(result["phase"], "definition")
            self.assertEqual(result["turn_start_action"], "continue_current_stage")
            self.assertEqual(result["validation"]["status"], "PASS")
            self.assertIn("Stageflow preflight", result["preflight_marker"])
            wire_output = result["_wire_output"]
            self.assertEqual(set(wire_output), {"hookSpecificOutput"})
            hook_output = wire_output["hookSpecificOutput"]
            self.assertEqual(hook_output["hookEventName"], "UserPromptSubmit")
            self.assertIn("OK", hook_output["additionalContext"])
            self.assertIn("continue_current_stage", hook_output["additionalContext"])
            self.assertNotIn("status", wire_output)

    def test_old_phase_current_is_invalid(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            state = root / ".stageflow" / "requests" / REQUEST_ID / "state.json"
            current = root / ".stageflow" / "sessions" / "session-1" / "current.json"
            state.write_text(json.dumps({"request_id": REQUEST_ID, "phase": "service-plan"}, indent=2), encoding="utf-8")
            current.write_text(json.dumps({"request_id": REQUEST_ID, "phase": "service-plan"}, indent=2), encoding="utf-8")
            result = self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "workflow status"})
            self.assertEqual(result["status"], "INVALID_CURRENT")
            self.assertEqual(result["turn_start_action"], "repair_current_state")

    def test_completed_current_requires_new_request(self) -> None:
        with temp_project() as root:
            self.create_project(root, "completed")
            result = self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "workflow status"})
            self.assertEqual(result["status"], "COMPLETED_CURRENT")
            self.assertEqual(result["turn_start_action"], "start_new_request")

    def test_implementation_prompt_checks_implementation_plan_gate(self) -> None:
        with temp_project() as root:
            self.create_project(root, "implementation")
            approval = root / ".stageflow" / "requests" / REQUEST_ID / "02-implementation-plan" / "approval.md"
            approval.write_text(approval.read_text(encoding="utf-8").replace("Approved.", "Not approved."), encoding="utf-8")
            result = self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "workflow implement"})
            self.assertEqual(result["status"], "IMPLEMENTATION_BLOCKED")
            self.assertEqual(result["turn_start_action"], "repair_implementation_plan_gate")
            self.assertEqual(result["implementation_entry_gate"]["status"], "FAIL")

    def test_stop_warns_when_required_marker_missing(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "workflow status"})
            result = self.run_hook(root, "stop", {"session_id": "session-1", "last_assistant_message": "status answered"}, expected_returncode=0)
            self.assertEqual(result["status"], "BLOCKED")
            self.assertIn("preflight marker", "\n".join(result["warnings"]))
            self.assertEqual(result["_wire_output"]["decision"], "block")
            self.assertIn("preflight marker", result["_wire_output"]["reason"])

    def test_pre_tool_use_blocks_non_stageflow_write_before_implementation_plan_passes(self) -> None:
        with temp_project() as root:
            self.create_project(root, "implementation")
            approval = root / ".stageflow" / "requests" / REQUEST_ID / "02-implementation-plan" / "approval.md"
            approval.write_text(approval.read_text(encoding="utf-8").replace("Approved.", "Not approved."), encoding="utf-8")
            result = self.run_hook(root, "pre_tool_use", {"session_id": "session-1", "tool_name": "Write", "tool_input": {"file_path": "src/app.ts"}}, expected_returncode=0)
            self.assertEqual(result["status"], "BLOCKED")
            hook_output = result["_wire_output"]["hookSpecificOutput"]
            self.assertEqual(hook_output["hookEventName"], "PreToolUse")
            self.assertEqual(hook_output["permissionDecision"], "deny")
            self.assertIn("implementation-plan stage passes", hook_output["permissionDecisionReason"])
            self.assertNotIn("status", result["_wire_output"])
            self.assertNotIn("turn_start_action", result["_wire_output"])

    def test_pre_tool_use_allows_stageflow_artifact_write_before_implementation_plan_passes(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            approval = root / ".stageflow" / "requests" / REQUEST_ID / "02-implementation-plan" / "approval.md"
            approval.write_text(approval.read_text(encoding="utf-8").replace("Approved.", "Not approved."), encoding="utf-8")
            result = self.run_hook(root, "pre_tool_use", {"session_id": "session-1", "tool_name": "Write", "tool_input": {"file_path": ".stageflow/requests/20260621-1200-test-request/01-definition/definition.md"}})
            self.assertEqual(result["status"], "PREPASS")
            self.assertEqual(result["_wire_output"], {})

    def test_pre_tool_use_allows_read_only_shell_command(self) -> None:
        with temp_project() as root:
            result = self.run_hook(root, "pre_tool_use", {"session_id": "session-1", "tool_name": "shell_command", "tool_input": {"command": "rg Stageflow"}})
            self.assertEqual(result["status"], "PREPASS")
            self.assertEqual(result["_wire_output"], {})

    def test_completion_like_stop_runs_all_validation(self) -> None:
        with temp_project() as root:
            self.create_project(root, "completed")
            prompt_result = self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "workflow status"})
            marker = str(prompt_result["preflight_marker"])
            result = self.run_hook(root, "stop", {"session_id": "session-1", "last_assistant_message": marker + "\ncompleted"})
            self.assertEqual(result["_wire_output"], {})

    def test_definition_pending_clarification_returns_awaiting_user_action(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(
                artifact.read_text(encoding="utf-8").replace(
                    "| PENDING-000 | N/A | No pending clarification. | N/A | N/A | N/A | N/A | none |",
                    "| PENDING-001 | 큰방향 | Docs sync status의 큰방향 범위는 어디까지인가요? | Option 1: docs-wide status only; Option 2: docs-wide status plus review-session scope; Option 3: docs-wide status plus hook metadata | Option 1 | N/A | 큰방향 상태 범위부터 정합니다. | pending |\n| PENDING-002 | 큰방향 | Which outcome should this clarify? | Option 1: status readability; Option 2: traceability for reviewers | Option 1 | N/A | 결과 우선순위는 아직 큰방향 질문입니다. | pending |\n| PENDING-003 | 큰방향 | How should docs sync status be represented? | Option 1: docs-wide status only; Option 2: docs-wide status plus partial review notes | Option 2 | N/A | 현재 답변되지 않은 큰방향 동작 범위입니다. | pending |\n| PENDING-004 | 큰방향 | Which data should status own? | Option 1: status text only; Option 2: status plus hook response shape | Option 1 | N/A | Data responsibility can still shift the top-level boundary. | pending |\n| PENDING-005 | 큰방향 | Which validation boundary should be clarified with it? | Option 1: validate response text only; Option 2: validate status and hook response shape | Option 1 | N/A | Validation boundary affects later detail checks. | pending |",
                ).replace(
                    "| CLAR-001 | Which correction boundary should definition capture? Options: fix only reported behavior, include adjacent regression guard. | User said `질문 그만, 구현 계획으로 넘어가기`. | no | 질문 그만, 구현 계획으로 넘어가기 | REQ-001, SP-001 |",
                    "| CLAR-000 | No completed clarification yet. | N/A | no | N/A | N/A |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "definition")
            result = self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "workflow status"})
            self.assertEqual(result["status"], "AWAITING_USER")
            self.assertEqual(result["turn_start_action"], "answer_follow_up_and_restate_pending")
            self.assertEqual(result["awaiting_user_prompt_kind"], "follow_up")
            self.assertEqual(result["validation"]["status"], "AWAITING_USER")
            self.assertIn("How should docs sync status", result["pending_clarification_output"])
            self.assertIn("Which validation boundary", result["pending_clarification_output"])
            self.assertIn("Option 3: docs-wide status plus hook metadata", result["pending_clarification_output"])
            self.assertNotIn("구현 계획으로 넘어가기", result["pending_clarification_output"])


    def test_awaiting_user_prompt_option_answer_gets_answer_action(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            self.write_pending_definition(root)
            result = self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "1"})
            self.assertEqual(result["status"], "AWAITING_USER")
            self.assertEqual(result["awaiting_user_prompt_kind"], "pending_answer")
            self.assertEqual(result["turn_start_action"], "apply_user_clarification_answer")

    def test_awaiting_user_prompt_stop_signal_gets_stop_action(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            self.write_pending_definition(root)
            prompt_result = self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "질문 그만, 구현 계획으로 넘어가기"})
            self.assertEqual(prompt_result["status"], "AWAITING_USER")
            self.assertEqual(prompt_result["awaiting_user_prompt_kind"], "stop_signal")
            self.assertEqual(prompt_result["turn_start_action"], "run_definition_transition_risk_goal")
            marker = str(prompt_result["preflight_marker"])
            result = self.run_hook(root, "stop", {"session_id": "session-1", "last_assistant_message": marker + "\nClarification History에 종료 신호를 기록하겠습니다."})
            self.assertEqual(result["status"], "PREPASS")

    def test_stop_signal_allows_only_transition_risk_writes_before_review(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            self.write_pending_definition(root)
            self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "질문 그만, 구현 계획으로 넘어가기"})
            allowed = self.run_hook(
                root,
                "pre_tool_use",
                {
                    "session_id": "session-1",
                    "tool_name": "Write",
                    "tool_input": {"file_path": ".stageflow/requests/20260621-1200-test-request/01-definition/transition-risk.md"},
                },
            )
            self.assertEqual(allowed["_wire_output"], {})
            blocked = self.run_hook(
                root,
                "pre_tool_use",
                {
                    "session_id": "session-1",
                    "tool_name": "Write",
                    "tool_input": {"file_path": ".stageflow/requests/20260621-1200-test-request/02-implementation-plan/implementation-plan.md"},
                },
                expected_returncode=0,
            )
            self.assertIn("transition-risk", "\n".join(blocked["warnings"]))


    def test_stop_signal_blocks_definition_approval_claim_before_transition_risk(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            self.write_pending_definition(root)
            prompt_result = self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "질문 그만, 구현 계획으로 넘어가기"})
            marker = str(prompt_result["preflight_marker"])
            result = self.run_hook(
                root,
                "stop",
                {"session_id": "session-1", "last_assistant_message": marker + "\ndefinition approved"},
                expected_returncode=0,
            )
            self.assertIn("must not claim completion or next-stage progress", "\n".join(result["warnings"]))


    def test_awaiting_user_allows_question_generation_subagent(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            self.write_pending_definition(root)
            self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "Option 1 설명해줘"})
            result = self.run_hook(
                root,
                "subagent_start",
                {
                    "session_id": "session-1",
                    "agent_id": "agent-questions",
                    "role": "question-generation backlog candidate subagent",
                    "task": "Prepare clarification question backlog candidates for question-backlog.md",
                },
            )
            self.assertEqual(result["status"], "QUESTION_BACKLOG_SUBAGENT_ALLOWED")
            self.assertTrue(result["question_backlog_allowed"])

    def test_awaiting_user_blocks_non_question_generation_subagent(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            self.write_pending_definition(root)
            self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "Option 1 설명해줘"})
            result = self.run_hook(
                root,
                "subagent_start",
                {"session_id": "session-1", "agent_id": "agent-review", "role": "definition review subagent"},
                expected_returncode=0,
            )
            self.assertEqual(result["status"], "BLOCKED")
            self.assertIn("question-generation subagents", "\n".join(result["warnings"]))
            self.assertFalse(result["_wire_output"]["continue"])
            self.assertIn("question-generation subagents", result["_wire_output"]["stopReason"])

    def test_awaiting_user_subagent_may_only_write_question_backlog(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            self.write_pending_definition(root)
            self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "Option 1 설명해줘"})
            allowed = self.run_hook(
                root,
                "pre_tool_use",
                {
                    "session_id": "session-1",
                    "agent_id": "agent-questions",
                    "tool_name": "Write",
                    "tool_input": {"file_path": ".stageflow/requests/20260621-1200-test-request/01-definition/question-backlog.md"},
                },
            )
            self.assertEqual(allowed["_wire_output"], {})
            blocked = self.run_hook(
                root,
                "pre_tool_use",
                {
                    "session_id": "session-1",
                    "agent_id": "agent-questions",
                    "tool_name": "Write",
                    "tool_input": {"file_path": ".stageflow/requests/20260621-1200-test-request/01-definition/review.md"},
                },
                expected_returncode=0,
            )
            self.assertEqual(blocked["status"], "BLOCKED")
            self.assertIn("question-backlog.md", "\n".join(blocked["warnings"]))

    def test_awaiting_user_pending_answer_allows_main_definition_write(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            self.write_pending_definition(root)
            self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "Option 1"})
            result = self.run_hook(
                root,
                "pre_tool_use",
                {
                    "session_id": "session-1",
                    "tool_name": "Write",
                    "tool_input": {"file_path": ".stageflow/requests/20260621-1200-test-request/01-definition/definition.md"},
                },
            )
            self.assertEqual(result["_wire_output"], {})

    def test_awaiting_user_follow_up_allows_full_restatement_with_scope_label(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(
                artifact.read_text(encoding="utf-8").replace(
                    "| PENDING-000 | N/A | No pending clarification. | N/A | N/A | N/A | N/A | none |",
                    "| PENDING-001 | 큰방향 | Docs sync status의 큰방향 범위는 어디까지인가요? | Option 1: docs-wide status only; Option 2: docs-wide status plus review-session scope | Option 1 | N/A | 큰방향 상태 범위부터 정합니다. | pending |",
                ).replace(
                    "| CLAR-001 | Which correction boundary should definition capture? Options: fix only reported behavior, include adjacent regression guard. | User said `질문 그만, 구현 계획으로 넘어가기`. | no | 질문 그만, 구현 계획으로 넘어가기 | REQ-001, SP-001 |",
                    "| CLAR-000 | No completed clarification yet. | N/A | no | N/A | N/A |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "definition")
            prompt_result = self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "workflow status"})
            marker = str(prompt_result["preflight_marker"])
            last_message = (
                marker
                + "\n[큰방향] Docs sync status의 큰방향 범위는 어디까지인가요?\n"
                + "Option 1: docs-wide status only\n"
                + "Option 2: docs-wide status plus review-session scope"
            )
            result = self.run_hook(root, "stop", {"session_id": "session-1", "last_assistant_message": last_message})
            self.assertEqual(result["status"], "PREPASS")

    def test_awaiting_user_stop_blocks_response_without_pending_questions(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(
                artifact.read_text(encoding="utf-8").replace(
                    "| PENDING-000 | N/A | No pending clarification. | N/A | N/A | N/A | N/A | none |",
                    "| PENDING-001 | 큰방향 | Docs sync status의 큰방향 범위는 어디까지인가요? | Option 1: docs-wide status only; Option 2: docs-wide status plus review-session scope; Option 3: docs-wide status plus hook metadata | Option 1 | N/A | 큰방향 상태 범위부터 정합니다. | pending |\n| PENDING-002 | 큰방향 | Which outcome should this clarify? | Option 1: status readability; Option 2: traceability for reviewers | Option 1 | N/A | 결과 우선순위는 아직 큰방향 질문입니다. | pending |\n| PENDING-003 | 큰방향 | How should docs sync status be represented? | Option 1: docs-wide status only; Option 2: docs-wide status plus partial review notes | Option 2 | N/A | 현재 답변되지 않은 큰방향 동작 범위입니다. | pending |\n| PENDING-004 | 큰방향 | Which data should status own? | Option 1: status text only; Option 2: status plus hook response shape | Option 1 | N/A | Data responsibility can still shift the top-level boundary. | pending |\n| PENDING-005 | 큰방향 | Which validation boundary should be clarified with it? | Option 1: validate response text only; Option 2: validate status and hook response shape | Option 1 | N/A | Validation boundary affects later detail checks. | pending |",
                ).replace(
                    "| CLAR-001 | Which correction boundary should definition capture? Options: fix only reported behavior, include adjacent regression guard. | User said `질문 그만, 구현 계획으로 넘어가기`. | no | 질문 그만, 구현 계획으로 넘어가기 | REQ-001, SP-001 |",
                    "| CLAR-000 | No completed clarification yet. | N/A | no | N/A | N/A |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "definition")
            prompt_result = self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "workflow status"})
            marker = str(prompt_result["preflight_marker"])
            result = self.run_hook(root, "stop", {"session_id": "session-1", "last_assistant_message": marker + "\n대기 중입니다."}, expected_returncode=0)
            self.assertEqual(result["status"], "BLOCKED")
            self.assertIn("pending clarification questions and labeled options", "\n".join(result["warnings"]))

    def test_awaiting_user_stop_blocks_single_suggestion_without_labeled_options(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(
                artifact.read_text(encoding="utf-8").replace(
                    "| PENDING-000 | N/A | No pending clarification. | N/A | N/A | N/A | N/A | none |",
                    "| PENDING-001 | 큰방향 | Docs sync status의 큰방향 범위는 어디까지인가요? | Option 1: docs-wide status only; Option 2: docs-wide status plus review-session scope; Option 3: docs-wide status plus hook metadata | Option 1 | N/A | 큰방향 상태 범위부터 정합니다. | pending |\n| PENDING-002 | 큰방향 | Which outcome should this clarify? | Option 1: status readability; Option 2: traceability for reviewers | Option 1 | N/A | 결과 우선순위는 아직 큰방향 질문입니다. | pending |\n| PENDING-003 | 큰방향 | How should docs sync status be represented? | Option 1: docs-wide status only; Option 2: docs-wide status plus partial review notes | Option 2 | N/A | 현재 답변되지 않은 큰방향 동작 범위입니다. | pending |\n| PENDING-004 | 큰방향 | Which data should status own? | Option 1: status text only; Option 2: status plus hook response shape | Option 1 | N/A | Data responsibility can still shift the top-level boundary. | pending |\n| PENDING-005 | 큰방향 | Which validation boundary should be clarified with it? | Option 1: validate response text only; Option 2: validate status and hook response shape | Option 1 | N/A | Validation boundary affects later detail checks. | pending |",
                ).replace(
                    "| CLAR-001 | Which correction boundary should definition capture? Options: fix only reported behavior, include adjacent regression guard. | User said `질문 그만, 구현 계획으로 넘어가기`. | no | 질문 그만, 구현 계획으로 넘어가기 | REQ-001, SP-001 |",
                    "| CLAR-000 | No completed clarification yet. | N/A | no | N/A | N/A |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "definition")
            prompt_result = self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "workflow status"})
            marker = str(prompt_result["preflight_marker"])
            last_message = (
                marker
                + "\n질문: How should docs sync status be represented?\n"
                + "제안: docs-wide status plus partial review notes로 가겠습니다.\n"
                + "질문: 어떤 세부확인 검증 기준을 정해야 하나요?\n"
                + "제안: status text only로 가겠습니다."
            )
            result = self.run_hook(root, "stop", {"session_id": "session-1", "last_assistant_message": last_message}, expected_returncode=0)
            self.assertEqual(result["status"], "BLOCKED")
            self.assertIn("Option 1: docs-wide status only", "\n".join(result["warnings"]))
            self.assertIn("Option 3: docs-wide status plus hook metadata", "\n".join(result["warnings"]))


    def test_awaiting_user_stop_blocks_missing_question_scope_label(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(
                artifact.read_text(encoding="utf-8").replace(
                    "| PENDING-000 | N/A | No pending clarification. | N/A | N/A | N/A | N/A | none |",
                    "| PENDING-001 | 큰방향 | Docs sync status의 큰방향 범위는 어디까지인가요? | Option 1: docs-wide status only; Option 2: docs-wide status plus review-session scope | Option 1 | N/A | 큰방향 상태 범위부터 정합니다. | pending |",
                ).replace(
                    "| CLAR-001 | Which correction boundary should definition capture? Options: fix only reported behavior, include adjacent regression guard. | User said `질문 그만, 구현 계획으로 넘어가기`. | no | 질문 그만, 구현 계획으로 넘어가기 | REQ-001, SP-001 |",
                    "| CLAR-000 | No completed clarification yet. | N/A | no | N/A | N/A |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "definition")
            prompt_result = self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "workflow status"})
            marker = str(prompt_result["preflight_marker"])
            last_message = (
                marker
                + "\n질문: Docs sync status의 큰방향 범위는 어디까지인가요?\n"
                + "선택지: Option 1: docs-wide status only / Option 2: docs-wide status plus review-session scope"
            )
            result = self.run_hook(root, "stop", {"session_id": "session-1", "last_assistant_message": last_message}, expected_returncode=0)
            self.assertEqual(result["status"], "BLOCKED")
            self.assertIn("[큰방향]", "\n".join(result["warnings"]))

    def test_awaiting_user_stop_blocks_missing_third_option(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(
                artifact.read_text(encoding="utf-8").replace(
                    "| PENDING-000 | N/A | No pending clarification. | N/A | N/A | N/A | N/A | none |",
                    "| PENDING-001 | 큰방향 | Docs sync status의 큰방향 범위는 어디까지인가요? | Option 1: docs-wide status only; Option 2: docs-wide status plus review-session scope; Option 3: docs-wide status plus hook metadata | Option 1 | N/A | 큰방향 상태 범위부터 정합니다. | pending |",
                ).replace(
                    "| CLAR-001 | Which correction boundary should definition capture? Options: fix only reported behavior, include adjacent regression guard. | User said `질문 그만, 구현 계획으로 넘어가기`. | no | 질문 그만, 구현 계획으로 넘어가기 | REQ-001, SP-001 |",
                    "| CLAR-000 | No completed clarification yet. | N/A | no | N/A | N/A |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "definition")
            prompt_result = self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "workflow status"})
            marker = str(prompt_result["preflight_marker"])
            last_message = (
                marker
                + "\n질문: Docs sync status의 큰방향 범위는 어디까지인가요?\n"
                + "선택지: Option 1: docs-wide status only / Option 2: docs-wide status plus review-session scope"
            )
            result = self.run_hook(root, "stop", {"session_id": "session-1", "last_assistant_message": last_message}, expected_returncode=0)
            self.assertEqual(result["status"], "BLOCKED")
            self.assertIn("Option 3: docs-wide status plus hook metadata", "\n".join(result["warnings"]))

    def test_awaiting_user_stop_blocks_completion_claim_even_with_questions(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(
                artifact.read_text(encoding="utf-8").replace(
                    "| PENDING-000 | N/A | No pending clarification. | N/A | N/A | N/A | N/A | none |",
                    "| PENDING-001 | 큰방향 | Docs sync status의 큰방향 범위는 어디까지인가요? | Option 1: docs-wide status only; Option 2: docs-wide status plus review-session scope; Option 3: docs-wide status plus hook metadata | Option 1 | N/A | 큰방향 상태 범위부터 정합니다. | pending |\n| PENDING-002 | 큰방향 | Which outcome should this clarify? | Option 1: status readability; Option 2: traceability for reviewers | Option 1 | N/A | 결과 우선순위는 아직 큰방향 질문입니다. | pending |\n| PENDING-003 | 큰방향 | How should docs sync status be represented? | Option 1: docs-wide status only; Option 2: docs-wide status plus partial review notes | Option 2 | N/A | 현재 답변되지 않은 큰방향 동작 범위입니다. | pending |\n| PENDING-004 | 큰방향 | Which data should status own? | Option 1: status text only; Option 2: status plus hook response shape | Option 1 | N/A | Data responsibility can still shift the top-level boundary. | pending |\n| PENDING-005 | 큰방향 | Which validation boundary should be clarified with it? | Option 1: validate response text only; Option 2: validate status and hook response shape | Option 1 | N/A | Validation boundary affects later detail checks. | pending |",
                ).replace(
                    "| CLAR-001 | Which correction boundary should definition capture? Options: fix only reported behavior, include adjacent regression guard. | User said `질문 그만, 구현 계획으로 넘어가기`. | no | 질문 그만, 구현 계획으로 넘어가기 | REQ-001, SP-001 |",
                    "| CLAR-000 | No completed clarification yet. | N/A | no | N/A | N/A |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "definition")
            prompt_result = self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "workflow status"})
            marker = str(prompt_result["preflight_marker"])
            last_message = (
                marker
                + "\n질문: How should docs sync status be represented?\n"
                + "선택지: Option 1: docs-wide status only / Option 2: docs-wide status plus partial review notes\n"
                + "목표를 달성했습니다."
            )
            result = self.run_hook(root, "stop", {"session_id": "session-1", "last_assistant_message": last_message}, expected_returncode=0)
            self.assertEqual(result["status"], "BLOCKED")
            self.assertIn("must not claim completion", "\n".join(result["warnings"]))


if __name__ == "__main__":
    unittest.main()
