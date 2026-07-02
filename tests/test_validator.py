
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
VALIDATOR = ROOT / "scripts" / "validate_stageflow.py"
REFERENCE_ROOT = ROOT / "skills" / "stageflow" / "references"
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
    "definition": [f"DEF-RULE-{index:03d}" for index in range(1, 19)],
    "implementation-plan": [f"IP-RULE-{index:03d}" for index in range(1, 9)] + [f"IP-FLOW-{index:03d}" for index in range(1, 8)],
    "implementation": [f"IMPL-RULE-{index:03d}" for index in range(1, 10)],
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

## Approved Flow Inventory

| Definition Flow ID | Source IDs | Trigger Or Entry | Actor Or Consumer | Target Outcome | State/Data Responsibility | Failure Or Empty Behavior | Boundary Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DFLOW-001 | REQ-001, SP-001, INTENT-001 | User requests behavior. | User | User sees the planned corrected response. | Required state is updated according to policy. | Errors remain recoverable for the user. | in-scope |

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

## Implementation Flow Model

| Flow ID | Definition Flow ID | Definition Source | Trigger Or Entry | Target Outcome | Primary Work Items | Flow Status | Status Rationale |
| --- | --- | --- | --- | --- | --- | --- | --- |
| FLOW-001 | DFLOW-001 | REQ-001, SP-001, INTENT-001 | Stageflow validates an implementation-plan artifact before approval. | Shallow implementation-plan artifacts fail before approval while detailed artifacts pass. | WORK-001 | complete | DFLOW-001 is in scope and has no unresolved definition gap. |

## Flow Completeness Matrix

| Flow ID | Ordered Implementation Path | State/Data Transitions | Failure Or Empty States | Observable Completion | Validation Evidence |
| --- | --- | --- | --- | --- | --- |
| FLOW-001 | Validator loads stage metadata -> validates implementation-plan sections and flow tables -> checks review checklist and flow shard -> returns PASS or detailed failure output. | Request artifacts are not mutated; validator returns PASS for valid artifacts or validation errors for invalid artifacts. | Missing flow sections, missing complete-flow matrix rows, placeholder-only cells, and missing flow-completeness shard produce validation failures. | Users can observe validator PASS or a specific blocking error before implementation approval. | FLOW-001 is covered by subprocess validator tests and full unittest discovery. |

## Work Items

| ID | Implementation Unit | Technical Design | Completion Evidence |
| --- | --- | --- | --- |
| WORK-001 | Implementation-plan validator contract. | FLOW-001 adds required technical sections and work-item columns to the stage metadata, then rejects generic implementation text. | FLOW-001 validator failure tests and full unittest output. |

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

Completed WORK-001 with actual validator, rule, prompt, and fixture changes.

## Plan Compliance And Deviations

WORK-001 followed the approved Definition Fidelity Matrix with no deviations, skipped work, or incomplete work.

## Work Item Completion Evidence

| Work Item ID | Planned Unit | Actual Change | Validation Evidence | Linked Flow IDs | Status |
| --- | --- | --- | --- | --- | --- |
| WORK-001 | Implementation-plan validator contract. | Validator, rule, prompt, and fixture changes enforce the approved work item. | `python -m unittest discover -s tests` passed and validates WORK-001. | FLOW-001 | completed |

## Flow Completion Evidence

| Flow ID | Definition Flow ID | Planned Outcome | Actual Result | Validation Evidence | Observable Completion | Status |
| --- | --- | --- | --- | --- | --- | --- |
| FLOW-001 | DFLOW-001 | Shallow implementation-plan artifacts fail before approval while detailed artifacts pass. | Validator, rule, prompt, and fixture changes enforce the approved flow. | `python -m unittest discover -s tests` passed and validates FLOW-001. | Users can observe validator PASS or specific blocking errors. | completed |

## Validation

`python -m unittest discover -s tests` passed and validates WORK-001 coverage. PROB-001 no longer reproduces.

## Review Result

Implementation review subagent completed the work item completion audit for WORK-001 and passed with no blocking issues.

## Completion Summary

WORK-001 is completed as approved with no residual work item risk.
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
        if phase == "definition":
            self.write_transition_risk_files(root, fingerprint)
        else:
            (stage_dir / "goal.md").write_text(self.goal_text(phase, folder, artifact_name, fingerprint), encoding="utf-8")
        self.write_review_files(stage_dir, phase, fingerprint, STAGE_RULE_IDS[phase])

    def write_transition_risk_files(self, root: Path, fingerprint: str | None = None) -> None:
        stage_dir = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition"
        if fingerprint is None:
            fingerprint = hashlib.sha256((stage_dir / "definition.md").read_bytes()).hexdigest()
        (stage_dir / "transition-risk-goal.md").write_text(self.transition_risk_goal_text(fingerprint), encoding="utf-8")
        (stage_dir / "transition-risk.md").write_text(self.transition_risk_text(), encoding="utf-8")

    def write_question_scope_transition_review(
        self,
        root: Path,
        transitions: tuple[str, ...] = ("큰방향 -> 주요결정",),
        verdict: str = "PASS",
        fingerprint: str | None = None,
    ) -> None:
        stage_dir = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition"
        if fingerprint is None:
            fingerprint = hashlib.sha256((stage_dir / "definition.md").read_bytes()).hexdigest()
        rows = "\n".join(
            f"| {transition} | sha256:{fingerprint} | Clarification History, Resolved Decisions, Pending Clarifications, and question-backlog.md if present. | No remaining higher-scope questions for this transition. | question scope transition review subagent | {verdict} |"
            for transition in transitions
        )
        (stage_dir / "question-scope-transition-review.md").write_text(
            f"""# Question Scope Transition Review

## Transition Checks

| Transition | Definition Artifact Fingerprint | Evidence Reviewed | Remaining Higher-Scope Questions | Reviewer | Verdict |
| --- | --- | --- | --- | --- | --- |
{rows}
""",
            encoding="utf-8",
        )

    def write_definition_store(
        self,
        root: Path,
        *,
        active_pending_ids: list[str],
        current_scope: str,
        decision_id: str = "DEC-900",
        source_pending_id: str = "PENDING-001",
        affected_ids: list[str] | None = None,
        risk_level: str = "low",
        sync_status: str = "working-set-only",
        trace_affected_ids: list[str] | None = None,
        fingerprint: str | None = None,
    ) -> None:
        affected_ids = affected_ids or ["REQ-001"]
        trace_affected_ids = trace_affected_ids if trace_affected_ids is not None else affected_ids
        stage_dir = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition"
        store_dir = stage_dir / "definition-store"
        store_dir.mkdir(exist_ok=True)
        if fingerprint is None:
            fingerprint = hashlib.sha256((stage_dir / "definition.md").read_bytes()).hexdigest()
        (store_dir / "working-set.json").write_text(
            json.dumps(
                {
                    "active_pending_ids": active_pending_ids,
                    "current_scope": current_scope,
                    "risk_level": risk_level,
                    "latest_answer": {"source_pending_id": source_pending_id, "decision_id": decision_id},
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (store_dir / "decision-ledger.jsonl").write_text(
            json.dumps(
                {
                    "decision_id": decision_id,
                    "source_pending_id": source_pending_id,
                    "decision": "Recorded user decision for definition-store validation.",
                    "affected_ids": affected_ids,
                    "risk_level": risk_level,
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        (store_dir / "trace-index.json").write_text(
            json.dumps(
                {
                    "traces": [
                        {
                            "pending_id": source_pending_id,
                            "decision_id": decision_id,
                            "affected_ids": trace_affected_ids,
                        }
                    ]
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (store_dir / "sync-state.json").write_text(
            json.dumps(
                {
                    "definition_fingerprint": f"sha256:{fingerprint}",
                    "decision_sync": {
                        decision_id: {
                            "risk_level": risk_level,
                            "status": sync_status,
                        }
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

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

    def write_review_files(self, stage_dir: Path, phase: str, fingerprint: str, rule_ids: list[str]) -> None:
        review_dir = stage_dir / "review"
        subagent_dir = review_dir / "subagents"
        subagent_dir.mkdir(parents=True, exist_ok=True)
        (subagent_dir / "001-full-bounded-review.md").write_text(
            self.review_shard_text(phase, fingerprint),
            encoding="utf-8",
        )
        shard_rows = ["| review/subagents/001-full-bounded-review.md | full bounded review for a small stage | PASS | None |"]
        if phase == "implementation-plan":
            (subagent_dir / "002-flow-completeness-review.md").write_text(
                self.review_shard_text(phase, fingerprint, scope="flow-completeness"),
                encoding="utf-8",
            )
            shard_rows.append("| review/subagents/002-flow-completeness-review.md | flow-completeness | PASS | None |")
        (review_dir / "final.md").write_text(
            self.review_text(phase, fingerprint, rule_ids, "\n".join(shard_rows)),
            encoding="utf-8",
        )

    @staticmethod
    def review_shard_text(phase: str, fingerprint: str, scope: str = "full bounded review for a small stage") -> str:
        flow_sections = ""
        if phase == "implementation-plan" and scope == "flow-completeness":
            flow_sections = """
## Flow Rule Checklist

| Rule ID | Evidence | Verdict | Blocking Issue |
| --- | --- | --- | --- |
| IP-FLOW-001 | DFLOW-001 maps to FLOW-001. | PASS | None |
| IP-FLOW-002 | FLOW-001 has an ordered path. | PASS | None |
| IP-FLOW-003 | FLOW-001 records validator result transition. | PASS | None |
| IP-FLOW-004 | FLOW-001 records validation failure states. | PASS | None |
| IP-FLOW-005 | FLOW-001 completion is observable in validator output. | PASS | None |
| IP-FLOW-006 | FLOW-001 validation evidence is tied to tests. | PASS | None |
| IP-FLOW-007 | FLOW-001 has no unresolved gap. | PASS | None |

## Flow Coverage Audit

| Flow ID | Definition Sources Checked | IP-FLOW-001..007 Verdict | Gap | Decision |
| --- | --- | --- | --- | --- |
| DFLOW-001 -> FLOW-001 | REQ-001, SP-001, INTENT-001 | PASS | No flow gap. | PASS |
"""
        return f"""# Subagent Review Shard

Stage: {phase}

Reviewed Artifact Fingerprint: sha256:{fingerprint}

Shard Scope: {scope}

## Inputs Read

- Current stage artifact.
- Matching writing and review rule file.

## Verdict

PASS
{flow_sections}

## Blocking Issues

No blocking issues.
"""

    @staticmethod
    def review_text(phase: str, fingerprint: str, rule_ids: list[str], shard_rows: str | None = None) -> str:
        checklist_rows = "\n".join(f"| {rule_id} | Evidence for {rule_id}. | PASS | None |" for rule_id in rule_ids)
        shard_rows = shard_rows or "| review/subagents/001-full-bounded-review.md | full bounded review for a small stage | PASS | None |"
        return f"""# Review

Stage: {phase}

Reviewed Artifact Fingerprint: sha256:{fingerprint}

## Review Method

Subagent review.

## Reviewer

main agent synthesis

## Review Cycle

| Cycle | Reviewer | Result | Notes |
| --- | --- | --- | --- |
| 1 | main agent synthesis | PASS | Synthesized bounded subagent review shards. |

## Subagent Review Shards

| Shard File | Scope | Verdict | Blocking Issue |
| --- | --- | --- | --- |
{shard_rows}

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
            "stage-tree": "01-definition/definition.md",
            "definition": "PENDING-001",
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
                if template == "stage-tree":
                    self.assertNotIn("01-definition/goal.md", result.stdout)
                    self.assertIn("01-definition/transition-risk-goal.md", result.stdout)
                    self.assertIn("01-definition/transition-risk.md", result.stdout)
                if template == "definition":
                    self.assertIn("Purpose And Intent", result.stdout)
                    self.assertIn("Intent Fidelity", result.stdout)
                    self.assertIn("현재 목적은 아직 확인되지 않았습니다", result.stdout)
                    self.assertIn("Question Scope", result.stdout)
                    self.assertIn("큰방향", result.stdout)
                    self.assertIn("Option 3:", result.stdout)
                    self.assertNotIn("PENDING-006", result.stdout)
                    self.assertIn("완료된 clarification이 아직 없다", result.stdout)
                    self.assertNotIn("Describe the user's goal", result.stdout)
                    self.assertNotIn("Why is this request needed", result.stdout)
                    self.assertNotIn("No completed clarification yet", result.stdout)
                    self.assertNotIn("User selected `구현 계획으로 넘어가기`", result.stdout)
                if template == "implementation-plan":
                    self.assertIn("Definition Fidelity Matrix", result.stdout)
                    self.assertIn("승인된 definition의 `DFLOW-001`", result.stdout)
                    self.assertIn("external-boundary-by-definition", (REFERENCE_ROOT / "stages" / "02-implementation-plan" / "implementation-plan-writing-and-review-rules.md").read_text(encoding="utf-8-sig"))
                    self.assertNotIn("validator-driven", result.stdout)
                    self.assertNotIn("scripts/validate_stageflow.py", result.stdout)
                    self.assertNotIn("Stageflow implementation-plan artifact", result.stdout)
                    self.assertNotIn("Use the existing validator-driven", result.stdout)
                if template == "implementation":
                    self.assertIn("work item별로 실제로 완료한 작업", result.stdout)
                    self.assertIn("Work Item Completion Evidence", result.stdout)
                    self.assertNotIn("Record the actual work completed", result.stdout)

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
            "references/intent-fidelity.md",
            "references/language-policy.md",
            "references/stages/01-definition/definition-writing-and-review-rules.md",
            "references/stages/02-implementation-plan/implementation-plan-writing-and-review-rules.md",
            "references/stages/03-implementation/implementation-writing-and-review-rules.md",
        ):
            with self.subTest(relative=relative):
                self.assertIn(relative, skill_text)
                self.assertIn(relative, artifact_text)
                reference_text = (ROOT / "skills" / "stageflow" / relative).read_text(encoding="utf-8-sig")
                if relative == "references/language-policy.md":
                    self.assertIn("## Default Language Selection", reference_text)
                    self.assertIn("default to Korean", reference_text)
                    self.assertIn("validator-required headings", reference_text)
                if relative.endswith("writing-and-review-rules.md"):
                    self.assertIn("## Stage Artifact Format", reference_text)
                    self.assertIn("references/language-policy.md", reference_text)
        self.assertNotIn("references/stages/01-requirements", skill_text)
        self.assertNotIn("references/stages/02-service-plan", skill_text)

    def test_stage_role_and_review_guidance_is_documented(self) -> None:
        definition_rules = (REFERENCE_ROOT / "stages" / "01-definition" / "definition-writing-and-review-rules.md").read_text(encoding="utf-8-sig")
        definition_prompt = (REFERENCE_ROOT / "stages" / "01-definition" / "definition-review-agent-prompt.md").read_text(encoding="utf-8-sig")
        intent_fidelity = (REFERENCE_ROOT / "intent-fidelity.md").read_text(encoding="utf-8-sig")
        for phrase in (
            "## Stage Responsibility",
            "## Request Type Profiles",
            "## Normal Behavior Transformation",
            "## Intent Fidelity Guard",
            "## Late Feedback And Redefinition",
            "DEF-RULE-014",
            "구현 계획으로 넘어가기",
            "Do not automatically invalidate",
            "goal-achievement decision readiness",
            "이 목표를 달성하려면 이 결정이 definition 단계에서 이미 정해져 있어야 하는가?",
            "uncovered` means a goal-critical decision is missing from definition",
            "at least two labeled resolution options",
            "Option 1:",
            "Option 2:",
            "Prior Answer Check",
            "Clarification History",
            "already answered/reflected user answers must move to implementation-plan coverage or constraints instead",
            "Intent Fidelity",
            "Scope Narrowing Evidence",
            "Flow Extraction Checklist",
            "every `REQ-*` and `SP-*`",
            "artifact repair",
            "DEF-RULE-017",
            "not a literal keyword rule",
            "references/intent-fidelity.md",
            "## Implementation-Plan Deferral Gate",
            "implementation-plan-only questions",
            "modules, components, functions",
            "test commands, validation strategy",
            "architecture",
            "acceptance outcome",
        ):
            self.assertIn(phrase, definition_rules)
        for phrase in (
            "Definition Review Agent Prompt",
            "normal behavior model",
            "does not introduce file changes",
            "Self-review never satisfies",
            "goal-achievement decision readiness evidence",
            "Intent Fidelity is missing for core user wording",
            "scope narrowing semantically rather than by literal trigger words",
            "assignment-only behavior",
        ):
            self.assertIn(phrase, definition_prompt)

        skill_text = (ROOT / "skills" / "stageflow" / "SKILL.md").read_text(encoding="utf-8-sig")
        artifact_text = (ROOT / "skills" / "stageflow" / "references" / "artifact-format.md").read_text(encoding="utf-8-sig")
        implementation_plan_rules = (REFERENCE_ROOT / "stages" / "02-implementation-plan" / "implementation-plan-writing-and-review-rules.md").read_text(encoding="utf-8-sig")
        implementation_rules = (REFERENCE_ROOT / "stages" / "03-implementation" / "implementation-writing-and-review-rules.md").read_text(encoding="utf-8-sig")
        for text, phrase in (
            (skill_text, "the only allowed definition goal is the transition-risk audit"),
            (skill_text, "goal-achievement decision readiness audit"),
            (skill_text, "implementation-plan coverage or constraints"),
            (artifact_text, "uncovered` means a goal-critical decision is missing from definition"),
            (artifact_text, "the audit found no material decision gap"),
            (artifact_text, "at least two labeled resolution options"),
            (artifact_text, "Prior Answer Check"),
            (artifact_text, "Already answered and reflected decisions are not risk cases"),
            (skill_text, "already answered/reflected user decisions are not risk cases"),
            (skill_text, "Question Scope"),
            (skill_text, "exact localized `Question Scope` label"),
            (definition_rules, "큰방향"),
            (definition_rules, "주요결정"),
            (definition_rules, "세부확인"),
            (skill_text, "question-backlog.md"),
            (skill_text, "Implementation Feedback And Redefinition"),
            (skill_text, "Use selective rework instead of blanket invalidation"),
            (implementation_plan_rules, "## Definition Fidelity"),
            (implementation_plan_rules, "Definition Fidelity Matrix"),
            (implementation_plan_rules, "Implementation-plan owns the technical decisions that definition must defer"),
            (implementation_plan_rules, "test commands, validation strategy"),
            (implementation_plan_rules, "work item split"),
            (skill_text, "defer implementation-plan-only decisions"),
            (implementation_plan_rules, "return-to-definition"),
            (implementation_plan_rules, "read-only/manual/future/out-of-scope narrowing"),
            (implementation_plan_rules, "references/intent-fidelity.md"),
            (intent_fidelity, "Intent fidelity is semantic, not lexical"),
            (intent_fidelity, "not a keyword list"),
            (skill_text, "references/language-policy.md"),
            (artifact_text, "references/language-policy.md"),
            (definition_rules, "For a Korean workflow, new definition prose should default to Korean"),
            (definition_prompt, "Read `references/language-policy.md`"),
            (implementation_plan_rules, "new implementation-plan prose should default to Korean"),
            (implementation_rules, "new implementation prose should default to Korean"),
            (intent_fidelity, "수정 모드` must not silently become `수정 화면`, `edit route`"),
            (intent_fidelity, "edit route navigation"),
            (implementation_plan_rules, "## Selective Rework After Definition Changes"),
            (implementation_plan_rules, "Keep unaffected work items"),
            (implementation_rules, "## Selective Rework After Feedback"),
            (implementation_rules, "which completed work remains valid"),
            (skill_text, "completion audit subagent review"),
            (implementation_rules, "IMPL-RULE-007"),
            (implementation_rules, "IMPL-RULE-009"),
            (implementation_rules, "Work Item Completion Evidence"),
            (implementation_rules, "Keep work-item completion and flow completion evidence separate"),
            (implementation_rules, "fix/review cycle until the latest review verdict is PASS"),
        ):
            self.assertIn(phrase, text)

        user_facing_docs = "\n".join((skill_text, artifact_text, definition_rules, definition_prompt))
        self.assertNotIn("Question Depth", user_facing_docs)
        self.assertNotIn("`broad`", user_facing_docs)
        self.assertNotIn("`mid`", user_facing_docs)
        self.assertNotIn("`detail`", user_facing_docs)

    def test_review_folder_contract_is_documented(self) -> None:
        skill_text = (ROOT / "skills" / "stageflow" / "SKILL.md").read_text(encoding="utf-8-sig")
        artifact_text = (ROOT / "skills" / "stageflow" / "references" / "artifact-format.md").read_text(encoding="utf-8-sig")
        prompts = [
            (REFERENCE_ROOT / "stages" / "01-definition" / "definition-review-agent-prompt.md").read_text(encoding="utf-8-sig"),
            (REFERENCE_ROOT / "stages" / "02-implementation-plan" / "implementation-plan-review-agent-prompt.md").read_text(encoding="utf-8-sig"),
            (REFERENCE_ROOT / "stages" / "03-implementation" / "implementation-review-agent-prompt.md").read_text(encoding="utf-8-sig"),
        ]
        for text in (skill_text, artifact_text):
            self.assertIn("review/final.md", text)
            self.assertIn("review/subagents", text)
            self.assertIn("bounded", text)
            self.assertIn("main agent", text)
        self.assertIn("Subagent Review Shards", artifact_text)
        self.assertIn("legacy `review.md` does not satisfy", artifact_text)
        for prompt in prompts:
            self.assertIn("review/subagents/<cycle>-<slice>.md", prompt)
            self.assertIn("Do not write `review/final.md`", prompt)
            self.assertIn("# Subagent Review Shard", prompt)
            self.assertIn("Shard Scope", prompt)
            self.assertIn("bounded shard", prompt)

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
            review = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "review" / "final.md"
            review.write_text("\n".join(line for line in review.read_text(encoding="utf-8").splitlines() if "DEF-RULE-004" not in line), encoding="utf-8")
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("DEF-RULE-004", result.stdout)

    def test_implementation_plan_review_checklist_requires_flow_rule_ids(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            review = root / ".stageflow" / "requests" / REQUEST_ID / "02-implementation-plan" / "review" / "final.md"
            review.write_text("\n".join(line for line in review.read_text(encoding="utf-8").splitlines() if "IP-FLOW-001" not in line), encoding="utf-8")
            result = self.run_validator(root, "implementation-plan")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("IP-FLOW-001", result.stdout)

    def test_implementation_plan_review_requires_flow_completeness_shard(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            stage_dir = root / ".stageflow" / "requests" / REQUEST_ID / "02-implementation-plan"
            review = stage_dir / "review" / "final.md"
            review.write_text(
                "\n".join(line for line in review.read_text(encoding="utf-8").splitlines() if "flow-completeness" not in line),
                encoding="utf-8",
            )
            result = self.run_validator(root, "implementation-plan")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("flow-completeness", result.stdout)

    def test_implementation_plan_review_fails_when_flow_shard_fails(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            shard = root / ".stageflow" / "requests" / REQUEST_ID / "02-implementation-plan" / "review" / "subagents" / "002-flow-completeness-review.md"
            shard.write_text(shard.read_text(encoding="utf-8").replace("## Verdict\n\nPASS", "## Verdict\n\nFAIL"), encoding="utf-8")
            result = self.run_validator(root, "implementation-plan")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Verdict must be PASS", result.stdout)

    def test_implementation_plan_flow_shard_requires_flow_rule_checklist(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            shard = root / ".stageflow" / "requests" / REQUEST_ID / "02-implementation-plan" / "review" / "subagents" / "002-flow-completeness-review.md"
            shard.write_text(shard.read_text(encoding="utf-8").replace("## Flow Rule Checklist", "## Removed Flow Rule Checklist"), encoding="utf-8")
            result = self.run_validator(root, "implementation-plan")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Flow Rule Checklist", result.stdout)

    def test_implementation_plan_flow_shard_requires_each_flow_rule_id(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            shard = root / ".stageflow" / "requests" / REQUEST_ID / "02-implementation-plan" / "review" / "subagents" / "002-flow-completeness-review.md"
            shard.write_text("\n".join(line for line in shard.read_text(encoding="utf-8").splitlines() if "IP-FLOW-004" not in line), encoding="utf-8")
            result = self.run_validator(root, "implementation-plan")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("IP-FLOW-004", result.stdout)

    def test_implementation_plan_flow_shard_audit_must_cover_all_definition_and_plan_flows(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            definition = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            definition.write_text(
                DEFINITION_TEXT.replace(
                    "| DFLOW-001 | REQ-001, SP-001, INTENT-001 | User requests behavior. | User | User sees the planned corrected response. | Required state is updated according to policy. | Errors remain recoverable for the user. | in-scope |",
                    "| DFLOW-001 | REQ-001, SP-001, INTENT-001 | User requests behavior. | User | User sees the planned corrected response. | Required state is updated according to policy. | Errors remain recoverable for the user. | in-scope |\n| DFLOW-002 | REQ-001, SP-001 | External consumer receives the boundary response. | External consumer | Consumer observes the repo boundary response. | Current repo exposes the boundary; external consumer owns downstream state. | External consumer handles downstream failure. | external-boundary-by-definition |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "definition")
            plan = root / ".stageflow" / "requests" / REQUEST_ID / "02-implementation-plan" / "implementation-plan.md"
            plan.write_text(
                IMPLEMENTATION_PLAN_TEXT.replace(
                    "| FLOW-001 | DFLOW-001 | REQ-001, SP-001, INTENT-001 | Stageflow validates an implementation-plan artifact before approval. | Shallow implementation-plan artifacts fail before approval while detailed artifacts pass. | WORK-001 | complete | DFLOW-001 is in scope and has no unresolved definition gap. |",
                    "| FLOW-001 | DFLOW-001 | REQ-001, SP-001, INTENT-001 | Stageflow validates an implementation-plan artifact before approval. | Shallow implementation-plan artifacts fail before approval while detailed artifacts pass. | WORK-001 | complete | DFLOW-001 is in scope and has no unresolved definition gap. |\n| FLOW-002 | DFLOW-002 | REQ-001, SP-001 | External consumer receives the repo boundary response. | The repo boundary response is observable; downstream completion is consumer-owned. | Current repo boundary only; no WORK item. | external-boundary-by-definition | Current repo exposes an observable boundary and the external consumer owns downstream responsibility per REQ-001. |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "implementation-plan")
            result = self.run_validator(root, "implementation-plan")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Flow Coverage Audit must include approved Definition Flow `DFLOW-002`", result.stdout)
            self.assertIn("Flow Coverage Audit must include plan Flow `FLOW-002`", result.stdout)

    def test_implementation_plan_flow_shard_audit_rejects_unknown_flow_ids(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            shard = root / ".stageflow" / "requests" / REQUEST_ID / "02-implementation-plan" / "review" / "subagents" / "002-flow-completeness-review.md"
            shard.write_text(
                shard.read_text(encoding="utf-8").replace(
                    "| DFLOW-001 -> FLOW-001 | REQ-001, SP-001, INTENT-001 | PASS | No flow gap. | PASS |",
                    "| DFLOW-001 -> FLOW-001 | REQ-001, SP-001, INTENT-001 | PASS | No flow gap. | PASS |\n| DFLOW-999 -> FLOW-999 | REQ-001 | PASS | No gap. | PASS |",
                ),
                encoding="utf-8",
            )
            result = self.run_validator(root, "implementation-plan")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unknown Definition Flow ID `DFLOW-999`", result.stdout)
            self.assertIn("unknown Flow ID `FLOW-999`", result.stdout)

    def test_implementation_review_requires_completion_audit_rule(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            review = root / ".stageflow" / "requests" / REQUEST_ID / "03-implementation" / "review" / "final.md"
            review.write_text("\n".join(line for line in review.read_text(encoding="utf-8").splitlines() if "IMPL-RULE-007" not in line), encoding="utf-8")
            result = self.run_validator(root, "implementation")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("IMPL-RULE-007", result.stdout)

    def test_implementation_review_requires_flow_completion_rule(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            review = root / ".stageflow" / "requests" / REQUEST_ID / "03-implementation" / "review" / "final.md"
            review.write_text("\n".join(line for line in review.read_text(encoding="utf-8").splitlines() if "IMPL-RULE-008" not in line), encoding="utf-8")
            result = self.run_validator(root, "implementation")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("IMPL-RULE-008", result.stdout)

    def test_implementation_requires_flow_completion_evidence(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "03-implementation" / "implementation.md"
            artifact.write_text(IMPLEMENTATION_TEXT.replace("## Flow Completion Evidence", "## Removed Flow Completion Evidence"), encoding="utf-8")
            self.refresh_stage_fingerprint(root, "implementation")
            result = self.run_validator(root, "implementation")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Flow Completion Evidence", result.stdout)

    def test_implementation_complete_flow_requires_evidence_row(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "03-implementation" / "implementation.md"
            artifact.write_text(
                IMPLEMENTATION_TEXT.replace(
                    "| FLOW-001 | DFLOW-001 | Shallow implementation-plan artifacts fail before approval while detailed artifacts pass. | Validator, rule, prompt, and fixture changes enforce the approved flow. | `python -m unittest discover -s tests` passed and validates FLOW-001. | Users can observe validator PASS or specific blocking errors. | completed |\n",
                    "",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "implementation")
            result = self.run_validator(root, "implementation")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("complete flow `FLOW-001` must have Flow Completion Evidence", result.stdout)

    def test_implementation_requires_work_item_completion_evidence(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "03-implementation" / "implementation.md"
            artifact.write_text(IMPLEMENTATION_TEXT.replace("## Work Item Completion Evidence", "## Removed Work Item Completion Evidence"), encoding="utf-8")
            self.refresh_stage_fingerprint(root, "implementation")
            result = self.run_validator(root, "implementation")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Work Item Completion Evidence", result.stdout)

    def test_implementation_approved_work_item_requires_completion_evidence_row(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "03-implementation" / "implementation.md"
            artifact.write_text(
                IMPLEMENTATION_TEXT.replace(
                    "| WORK-001 | Implementation-plan validator contract. | Validator, rule, prompt, and fixture changes enforce the approved work item. | `python -m unittest discover -s tests` passed and validates WORK-001. | FLOW-001 | completed |\n",
                    "",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "implementation")
            result = self.run_validator(root, "implementation")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("approved work item `WORK-001` must have Work Item Completion Evidence", result.stdout)

    def test_implementation_work_item_completion_evidence_status_must_be_completed(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "03-implementation" / "implementation.md"
            artifact.write_text(IMPLEMENTATION_TEXT.replace("| FLOW-001 | completed |", "| FLOW-001 | incomplete |"), encoding="utf-8")
            self.refresh_stage_fingerprint(root, "implementation")
            result = self.run_validator(root, "implementation")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Work Item Completion Evidence row `WORK-001` Status must be completed", result.stdout)

    def test_implementation_review_requires_separate_work_and_flow_rule(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            review = root / ".stageflow" / "requests" / REQUEST_ID / "03-implementation" / "review" / "final.md"
            review.write_text("\n".join(line for line in review.read_text(encoding="utf-8").splitlines() if "IMPL-RULE-009" not in line), encoding="utf-8")
            result = self.run_validator(root, "implementation")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("IMPL-RULE-009", result.stdout)

    def test_review_final_file_is_required(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            review = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "review" / "final.md"
            review.unlink()
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("review/final.md", result.stdout)

    def test_review_requires_subagent_shard_section_and_file(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            review = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "review" / "final.md"
            review.write_text(review.read_text(encoding="utf-8").replace("## Subagent Review Shards", "## Removed Subagent Review Shards"), encoding="utf-8")
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Subagent Review Shards", result.stdout)

    def test_review_fails_when_shard_file_is_missing(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            shard = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "review" / "subagents" / "001-full-bounded-review.md"
            shard.unlink()
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("001-full-bounded-review.md", result.stdout)

    def test_review_fails_when_shard_verdict_fails(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            shard = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "review" / "subagents" / "001-full-bounded-review.md"
            shard.write_text(shard.read_text(encoding="utf-8").replace("## Verdict\n\nPASS", "## Verdict\n\nFAIL"), encoding="utf-8")
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Verdict must be PASS", result.stdout)

    def test_legacy_review_md_does_not_satisfy_review_gate(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            stage_dir = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition"
            shutil.rmtree(stage_dir / "review")
            (stage_dir / "review.md").write_text(self.review_text("definition", hashlib.sha256((stage_dir / "definition.md").read_bytes()).hexdigest(), STAGE_RULE_IDS["definition"]), encoding="utf-8")
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("review/final.md", result.stdout)

    def test_definition_requires_requirements_sections(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(DEFINITION_TEXT.replace("## Desired Outcomes", "## Removed Desired Outcomes"), encoding="utf-8")
            self.refresh_stage_fingerprint(root, "definition")
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Desired Outcomes", result.stdout)


    def test_definition_requires_purpose_section(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(DEFINITION_TEXT.replace("## Purpose And Intent", "## Removed Purpose And Intent"), encoding="utf-8")
            self.refresh_stage_fingerprint(root, "definition")
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Purpose And Intent", result.stdout)

    def test_definition_rejects_invalid_purpose_confidence(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(DEFINITION_TEXT.replace("| user request | confirmed |", "| user request | guessed |"), encoding="utf-8")
            self.refresh_stage_fingerprint(root, "definition")
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Confidence must be one of", result.stdout)

    def test_unknown_purpose_requires_purpose_focused_pending_question(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(
                DEFINITION_TEXT.replace("| user request | confirmed |", "| user request needs clarification | unknown |")
                .replace(
                    "| PENDING-000 | N/A | No pending clarification. | N/A | N/A | N/A | N/A | none |",
                    "| PENDING-001 | 큰방향 | Which model scope should be used? | Option 1: A; Option 2: B | Option 1 | N/A | This changes scope. | pending |",
                )
                .replace(
                    "| CLAR-001 | Which correction boundary should definition capture? Options: fix only reported behavior, include adjacent regression guard. | User said `질문 그만, 구현 계획으로 넘어가기`. | no | 질문 그만, 구현 계획으로 넘어가기 | REQ-001, SP-001 |",
                    "| CLAR-000 | No completed clarification yet. | N/A | no | N/A | N/A |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "definition")
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("purpose-focused 큰방향 question", result.stdout)

    def test_inferred_purpose_cannot_stop_definition(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(DEFINITION_TEXT.replace("| user request | confirmed |", "| inspected project context | inferred |"), encoding="utf-8")
            self.refresh_stage_fingerprint(root, "definition")
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("must be confirmed before definition clarification can stop", result.stdout)

    def test_definition_requires_service_behavior_sections(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(DEFINITION_TEXT.replace("## Normal Behavior Model", "## Removed Normal Behavior Model"), encoding="utf-8")
            self.refresh_stage_fingerprint(root, "definition")
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Normal Behavior Model", result.stdout)

    def test_definition_requires_intent_fidelity_section(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(DEFINITION_TEXT.replace("## Intent Fidelity", "## Removed Intent Fidelity"), encoding="utf-8")
            self.refresh_stage_fingerprint(root, "definition")
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Intent Fidelity", result.stdout)

    def test_definition_requires_intent_fidelity_columns(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(DEFINITION_TEXT.replace("Allowed Interpretations", "Allowed Meaning"), encoding="utf-8")
            self.refresh_stage_fingerprint(root, "definition")
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Allowed Interpretations", result.stdout)

    def test_definition_rejects_blocking_open_question(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(DEFINITION_TEXT.replace("| Q-001 | No open question. | N/A | N/A | N/A | N/A | no | N/A |", "| Q-001 | Choose policy. | Ambiguous behavior. | A | B | Changes behavior. | yes | SP-001 |"), encoding="utf-8")
            self.refresh_stage_fingerprint(root, "definition")
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("still blocking", result.stdout)

    def test_definition_rejects_agent_clear_enough_closure(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(
                DEFINITION_TEXT.replace("User said `질문 그만, 구현 계획으로 넘어가기`", "Agent judged the definition clear enough")
                .replace("| no | 질문 그만, 구현 계획으로 넘어가기 |", "| no | N/A |"),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "definition")
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("explicit user stop signal", result.stdout)
            self.assertIn("cannot decide the definition is clear enough", result.stdout)

    def test_definition_user_answer_without_stop_requires_next_question(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(
                DEFINITION_TEXT.replace("User said `질문 그만, 구현 계획으로 넘어가기`", "User selected the second proposal")
                .replace("| no | 질문 그만, 구현 계획으로 넘어가기 |", "| no | N/A |"),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "definition")
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("keep asking until the user explicitly stops", result.stdout)

    def test_pending_clarification_must_not_include_stop_signal_option(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(
                DEFINITION_TEXT.replace(
                    "| PENDING-000 | N/A | No pending clarification. | N/A | N/A | N/A | N/A | none |",
                    "| PENDING-001 | 큰방향 | Which model? | Option 1: A; Option 2: B; Option 3: 구현 계획으로 넘어가기 | Option 1 | N/A | This changes scope. | pending |",
                ).replace(
                    "| CLAR-001 | Which correction boundary should definition capture? Options: fix only reported behavior, include adjacent regression guard. | User said `질문 그만, 구현 계획으로 넘어가기`. | no | 질문 그만, 구현 계획으로 넘어가기 | REQ-001, SP-001 |",
                    "| CLAR-000 | No completed clarification yet. | N/A | no | N/A | N/A |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "definition")
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("must not include the user stop signal as a question option", result.stdout)

    def test_pending_clarification_must_not_include_stop_signal_transition_option(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(
                DEFINITION_TEXT.replace(
                    "| PENDING-000 | N/A | No pending clarification. | N/A | N/A | N/A | N/A | none |",
                    "| PENDING-001 | 큰방향 | Which model? | Option 1: A; Option 2: B | Option 1 | 구현 계획으로 넘어가기 | This changes scope. | pending |",
                ).replace(
                    "| CLAR-001 | Which correction boundary should definition capture? Options: fix only reported behavior, include adjacent regression guard. | User said `질문 그만, 구현 계획으로 넘어가기`. | no | 질문 그만, 구현 계획으로 넘어가기 | REQ-001, SP-001 |",
                    "| CLAR-000 | No completed clarification yet. | N/A | no | N/A | N/A |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "definition")
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("must not include the user stop signal in `Transition Option`", result.stdout)
            self.assertIn("Transition Option must be `N/A`", result.stdout)


    def test_pending_clarification_allows_implementation_plan_artifact_option_text(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(
                DEFINITION_TEXT.replace(
                    "| PENDING-000 | N/A | No pending clarification. | N/A | N/A | N/A | N/A | none |",
                    "| PENDING-001 | 큰방향 | Which artifact scope should be used? | Option 1: implementation plan artifact에 반영 범위 제한; Option 2: definition artifact에만 범위 기록 | Option 1 | N/A | This is a real proposal, not a stop signal. | pending |",
                ).replace(
                    "| CLAR-001 | Which correction boundary should definition capture? Options: fix only reported behavior, include adjacent regression guard. | User said `질문 그만, 구현 계획으로 넘어가기`. | no | 질문 그만, 구현 계획으로 넘어가기 | REQ-001, SP-001 |",
                    "| CLAR-000 | No completed clarification yet. | N/A | no | N/A | N/A |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "definition")
            result = self.run_validator(root, "definition")
            self.assertEqual(result.returncode, 3, result.stdout)
            self.assertIn("AWAITING_USER definition", result.stdout)

    def test_pending_clarification_rejects_module_selection_question(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(
                DEFINITION_TEXT.replace(
                    "| PENDING-000 | N/A | No pending clarification. | N/A | N/A | N/A | N/A | none |",
                    "| PENDING-001 | 세부확인 | Which module should implement the correction? | Option 1: validator module; Option 2: hook module | Option 1 | N/A | This chooses an implementation surface. | pending |",
                ).replace(
                    "| CLAR-001 | Which correction boundary should definition capture? Options: fix only reported behavior, include adjacent regression guard. | User said `질문 그만, 구현 계획으로 넘어가기`. | no | 질문 그만, 구현 계획으로 넘어가기 | REQ-001, SP-001 |",
                    "| CLAR-000 | No completed clarification yet. | N/A | no | N/A | N/A |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "definition")
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("implementation-plan-only question", result.stdout)

    def test_pending_clarification_rejects_test_command_question(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(
                DEFINITION_TEXT.replace(
                    "| PENDING-000 | N/A | No pending clarification. | N/A | N/A | N/A | N/A | none |",
                    "| PENDING-001 | 세부확인 | Which test command should validate the change? | Option 1: unittest validator; Option 2: full discovery | Option 1 | N/A | This chooses a validation strategy for implementation-plan. | pending |",
                ).replace(
                    "| CLAR-001 | Which correction boundary should definition capture? Options: fix only reported behavior, include adjacent regression guard. | User said `질문 그만, 구현 계획으로 넘어가기`. | no | 질문 그만, 구현 계획으로 넘어가기 | REQ-001, SP-001 |",
                    "| CLAR-000 | No completed clarification yet. | N/A | no | N/A | N/A |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "definition")
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("implementation-plan-only question", result.stdout)

    def test_pending_clarification_rejects_architecture_or_library_question(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(
                DEFINITION_TEXT.replace(
                    "| PENDING-000 | N/A | No pending clarification. | N/A | N/A | N/A | N/A | none |",
                    "| PENDING-001 | 주요결정 | Which architecture or library should the implementation use? | Option 1: parser helper; Option 2: regex helper | Option 1 | N/A | This chooses implementation architecture. | pending |",
                ).replace(
                    "| CLAR-001 | Which correction boundary should definition capture? Options: fix only reported behavior, include adjacent regression guard. | User said `질문 그만, 구현 계획으로 넘어가기`. | no | 질문 그만, 구현 계획으로 넘어가기 | REQ-001, SP-001 |",
                    "| CLAR-000 | No completed clarification yet. | N/A | no | N/A | N/A |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "definition")
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("implementation-plan-only question", result.stdout)

    def test_open_question_rejects_work_item_split_question(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(
                DEFINITION_TEXT.replace(
                    "| Q-001 | No open question. | N/A | N/A | N/A | N/A | no | N/A |",
                    "| Q-001 | How should work items be split? | Implementation can be split several ways. | One work item per file. | One work item per module. | Changes implementation order only. | no | Implementation Plan |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "definition")
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("implementation-plan-only question", result.stdout)

    def test_pending_clarification_allows_acceptance_outcome_question(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(
                DEFINITION_TEXT.replace(
                    "| PENDING-000 | N/A | No pending clarification. | N/A | N/A | N/A | N/A | none |",
                    "| PENDING-001 | 세부확인 | Which acceptance outcome should count as success for the user? | Option 1: reported workflow succeeds; Option 2: reported workflow plus adjacent regression guard succeeds | Option 1 | N/A | This changes the user-visible acceptance outcome, not the test command. | pending |",
                ).replace(
                    "| CLAR-001 | Which correction boundary should definition capture? Options: fix only reported behavior, include adjacent regression guard. | User said `질문 그만, 구현 계획으로 넘어가기`. | no | 질문 그만, 구현 계획으로 넘어가기 | REQ-001, SP-001 |",
                    "| CLAR-000 | No completed clarification yet. | N/A | no | N/A | N/A |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "definition")
            self.write_question_scope_transition_review(
                root,
                transitions=("큰방향 -> 주요결정", "주요결정 -> 세부확인"),
            )
            result = self.run_validator(root, "definition")
            self.assertEqual(result.returncode, 3, result.stdout)
            self.assertIn("AWAITING_USER definition", result.stdout)

    def test_pending_clarification_rejects_more_than_five_questions(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            pending_rows = (
                "| PENDING-001 | 큰방향 | Which model? | Option 1: A; Option 2: B | Option 1 | N/A | This changes scope. | pending |\n"
                "| PENDING-002 | 큰방향 | Which outcome? | Option 1: C; Option 2: D | Option 1 | N/A | This clarifies outcome. | pending |\n"
                "| PENDING-003 | 큰방향 | Which behavior? | Option 1: E; Option 2: F | Option 1 | N/A | This clarifies behavior. | pending |\n"
                "| PENDING-004 | 큰방향 | Which policy? | Option 1: G; Option 2: H | Option 1 | N/A | This clarifies policy. | pending |\n"
                "| PENDING-005 | 큰방향 | Which validation? | Option 1: I; Option 2: J | Option 1 | N/A | This clarifies validation. | pending |\n"
                "| PENDING-006 | 큰방향 | Which boundary? | Option 1: K; Option 2: L | Option 1 | N/A | This exceeds the batch limit. | pending |"
            )
            artifact.write_text(
                DEFINITION_TEXT.replace(
                    "| PENDING-000 | N/A | No pending clarification. | N/A | N/A | N/A | N/A | none |",
                    pending_rows,
                ).replace(
                    "| CLAR-001 | Which correction boundary should definition capture? Options: fix only reported behavior, include adjacent regression guard. | User said `질문 그만, 구현 계획으로 넘어가기`. | no | 질문 그만, 구현 계획으로 넘어가기 | REQ-001, SP-001 |",
                    "| CLAR-000 | No completed clarification yet. | N/A | no | N/A | N/A |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "definition")
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("no more than five active questions", result.stdout)

    def test_pending_clarification_requires_labeled_options(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(
                DEFINITION_TEXT.replace(
                    "| PENDING-000 | N/A | No pending clarification. | N/A | N/A | N/A | N/A | none |",
                    "| PENDING-001 | 큰방향 | Which model? | A; B | A | N/A | This changes scope. | pending |",
                ).replace(
                    "| CLAR-001 | Which correction boundary should definition capture? Options: fix only reported behavior, include adjacent regression guard. | User said `질문 그만, 구현 계획으로 넘어가기`. | no | 질문 그만, 구현 계획으로 넘어가기 | REQ-001, SP-001 |",
                    "| CLAR-000 | No completed clarification yet. | N/A | no | N/A | N/A |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "definition")
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("explicit labeled proposal options", result.stdout)

    def test_pending_clarification_requires_valid_question_scope(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(
                DEFINITION_TEXT.replace(
                    "| PENDING-000 | N/A | No pending clarification. | N/A | N/A | N/A | N/A | none |",
                    "| PENDING-001 | unclear | Which validation? | Option 1: A; Option 2: B | Option 1 | N/A | This uses an invalid question scope. | pending |",
                ).replace(
                    "| CLAR-001 | Which correction boundary should definition capture? Options: fix only reported behavior, include adjacent regression guard. | User said `질문 그만, 구현 계획으로 넘어가기`. | no | 질문 그만, 구현 계획으로 넘어가기 | REQ-001, SP-001 |",
                    "| CLAR-000 | No completed clarification yet. | N/A | no | N/A | N/A |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "definition")
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Question Scope must be one of", result.stdout)

    def test_pending_clarification_rejects_mixed_question_scopes(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(
                DEFINITION_TEXT.replace(
                    "| PENDING-000 | N/A | No pending clarification. | N/A | N/A | N/A | N/A | none |",
                    "| PENDING-001 | 큰방향 | Which purpose boundary should be clarified? | Option 1: A; Option 2: B | Option 1 | N/A | This is a 큰방향 question. | pending |\n"
                    "| PENDING-002 | 주요결정 | Which behavior decision should be clarified? | Option 1: C; Option 2: D | Option 1 | N/A | This is a 주요결정 question. | pending |\n"
                    "| PENDING-003 | 세부확인 | Which validation detail should be clarified? | Option 1: E; Option 2: F | Option 1 | N/A | This is a 세부확인 question. | pending |",
                ).replace(
                    "| CLAR-001 | Which correction boundary should definition capture? Options: fix only reported behavior, include adjacent regression guard. | User said `질문 그만, 구현 계획으로 넘어가기`. | no | 질문 그만, 구현 계획으로 넘어가기 | REQ-001, SP-001 |",
                    "| CLAR-000 | No completed clarification yet. | N/A | no | N/A | N/A |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "definition")
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("must use one Question Scope at a time", result.stdout)

    def test_major_decision_pending_requires_question_scope_transition_review(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(
                DEFINITION_TEXT.replace(
                    "| PENDING-000 | N/A | No pending clarification. | N/A | N/A | N/A | N/A | none |",
                    "| PENDING-001 | 주요결정 | Which behavior decision should be clarified? | Option 1: A; Option 2: B | Option 1 | N/A | This is a major service behavior decision. | pending |",
                ).replace(
                    "| CLAR-001 | Which correction boundary should definition capture? Options: fix only reported behavior, include adjacent regression guard. | User said `질문 그만, 구현 계획으로 넘어가기`. | no | 질문 그만, 구현 계획으로 넘어가기 | REQ-001, SP-001 |",
                    "| CLAR-001 | Which top direction should definition capture? Options: immediate fix, reusable workflow guard. | User selected immediate fix. | no | N/A | REQ-001, SP-001 |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "definition")
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("question-scope-transition-review.md", result.stdout)
            self.assertIn("큰방향 -> 주요결정", result.stdout)

    def test_major_decision_pending_rejects_failed_question_scope_transition_review(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(
                DEFINITION_TEXT.replace(
                    "| PENDING-000 | N/A | No pending clarification. | N/A | N/A | N/A | N/A | none |",
                    "| PENDING-001 | 주요결정 | Which behavior decision should be clarified? | Option 1: A; Option 2: B | Option 1 | N/A | This is a major service behavior decision. | pending |",
                ).replace(
                    "| CLAR-001 | Which correction boundary should definition capture? Options: fix only reported behavior, include adjacent regression guard. | User said `질문 그만, 구현 계획으로 넘어가기`. | no | 질문 그만, 구현 계획으로 넘어가기 | REQ-001, SP-001 |",
                    "| CLAR-001 | Which top direction should definition capture? Options: immediate fix, reusable workflow guard. | User selected immediate fix. | no | N/A | REQ-001, SP-001 |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "definition")
            self.write_question_scope_transition_review(root, verdict="FAIL")
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Verdict must be PASS", result.stdout)

    def test_major_decision_pending_rejects_stale_question_scope_transition_review(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(
                DEFINITION_TEXT.replace(
                    "| PENDING-000 | N/A | No pending clarification. | N/A | N/A | N/A | N/A | none |",
                    "| PENDING-001 | 주요결정 | Which behavior decision should be clarified? | Option 1: A; Option 2: B | Option 1 | N/A | This is a major service behavior decision. | pending |",
                ).replace(
                    "| CLAR-001 | Which correction boundary should definition capture? Options: fix only reported behavior, include adjacent regression guard. | User said `질문 그만, 구현 계획으로 넘어가기`. | no | 질문 그만, 구현 계획으로 넘어가기 | REQ-001, SP-001 |",
                    "| CLAR-001 | Which top direction should definition capture? Options: immediate fix, reusable workflow guard. | User selected immediate fix. | no | N/A | REQ-001, SP-001 |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "definition")
            self.write_question_scope_transition_review(root, fingerprint="0" * 64)
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("must reference current definition fingerprint", result.stdout)

    def test_major_decision_pending_accepts_passed_question_scope_transition_review(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(
                DEFINITION_TEXT.replace(
                    "| PENDING-000 | N/A | No pending clarification. | N/A | N/A | N/A | N/A | none |",
                    "| PENDING-001 | 주요결정 | Which behavior decision should be clarified? | Option 1: A; Option 2: B | Option 1 | N/A | This is a major service behavior decision. | pending |",
                ).replace(
                    "| CLAR-001 | Which correction boundary should definition capture? Options: fix only reported behavior, include adjacent regression guard. | User said `질문 그만, 구현 계획으로 넘어가기`. | no | 질문 그만, 구현 계획으로 넘어가기 | REQ-001, SP-001 |",
                    "| CLAR-001 | Which top direction should definition capture? Options: immediate fix, reusable workflow guard. | User selected immediate fix. | no | N/A | REQ-001, SP-001 |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "definition")
            self.write_question_scope_transition_review(root)
            result = self.run_validator(root, "definition")
            self.assertEqual(result.returncode, 3, result.stdout)
            self.assertIn("질문 범위: 주요결정", result.stdout)

    def test_detail_check_pending_requires_both_question_scope_transition_reviews(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(
                DEFINITION_TEXT.replace(
                    "| PENDING-000 | N/A | No pending clarification. | N/A | N/A | N/A | N/A | none |",
                    "| PENDING-001 | 세부확인 | Which acceptance detail should be clarified? | Option 1: A; Option 2: B | Option 1 | N/A | This refines the accepted behavior. | pending |",
                ).replace(
                    "| CLAR-001 | Which correction boundary should definition capture? Options: fix only reported behavior, include adjacent regression guard. | User said `질문 그만, 구현 계획으로 넘어가기`. | no | 질문 그만, 구현 계획으로 넘어가기 | REQ-001, SP-001 |",
                    "| CLAR-001 | Which top direction should definition capture? Options: immediate fix, reusable workflow guard. | User selected immediate fix. | no | N/A | REQ-001, SP-001 |\n"
                    "| CLAR-002 | Which behavior decision should definition capture? Options: preserve current flow, adjust policy flow. | User selected preserve current flow. | no | N/A | SP-001 |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "definition")
            self.write_question_scope_transition_review(root, transitions=("큰방향 -> 주요결정",))
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("주요결정 -> 세부확인", result.stdout)

    def test_pending_clarification_rejects_old_question_depth_column(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(
                DEFINITION_TEXT.replace("Question Scope", "Question Depth").replace(
                    "| PENDING-000 | N/A | No pending clarification. | N/A | N/A | N/A | N/A | none |",
                    "| PENDING-001 | broad | Which model scope? | Option 1: A; Option 2: B | Option 1 | N/A | Old schema should fail. | pending |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "definition")
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Question Scope", result.stdout)

    def test_pending_clarification_rejects_old_broad_value(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(
                DEFINITION_TEXT.replace(
                    "| PENDING-000 | N/A | No pending clarification. | N/A | N/A | N/A | N/A | none |",
                    "| PENDING-001 | broad | Which model scope? | Option 1: A; Option 2: B | Option 1 | N/A | Old scope value should fail. | pending |",
                ).replace(
                    "| CLAR-001 | Which correction boundary should definition capture? Options: fix only reported behavior, include adjacent regression guard. | User said `질문 그만, 구현 계획으로 넘어가기`. | no | 질문 그만, 구현 계획으로 넘어가기 | REQ-001, SP-001 |",
                    "| CLAR-000 | No completed clarification yet. | N/A | no | N/A | N/A |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "definition")
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Question Scope must be one of", result.stdout)

    def test_definition_pending_clarification_returns_awaiting_user(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            pending_rows = (
                "| PENDING-001 | 큰방향 | Which docs source boundary should definition capture? | Option 1: docs-wide reviewed commit only; Option 2: docs-wide commit plus review-session metadata; Option 3: docs plus hook metadata | Option 1 | N/A | 큰방향 문서 범위부터 정합니다. | pending |\n"
                "| PENDING-002 | 큰방향 | Which outcome should the docs workflow prioritize? | Option 1: reviewed status clarity; Option 2: review-session traceability | Option 1 | N/A | Outcomes shape later behavior questions. | pending |\n"
                "| PENDING-003 | 큰방향 | Which normal docs sync behavior should be clarified? | Option 1: docs-wide status only; Option 2: docs-wide status plus partial review notes | Option 2 | N/A | 세부확인 전에 큰방향 동작 범위를 정합니다. | pending |\n"
                "| PENDING-004 | 큰방향 | Which metadata responsibility should definition capture? | Option 1: commit metadata only; Option 2: commit plus reviewer metadata | Option 1 | N/A | Data responsibility narrows the policy layer. | pending |\n"
                "| PENDING-005 | 큰방향 | Which validation boundary should definition capture? | Option 1: validate docs-only behavior; Option 2: validate docs plus hook behavior | Option 1 | N/A | Validation boundary affects later checks. | pending |"
            )
            artifact.write_text(
                DEFINITION_TEXT.replace(
                    "| PENDING-000 | N/A | No pending clarification. | N/A | N/A | N/A | N/A | none |",
                    pending_rows,
                ).replace(
                    "| CLAR-001 | Which correction boundary should definition capture? Options: fix only reported behavior, include adjacent regression guard. | User said `질문 그만, 구현 계획으로 넘어가기`. | no | 질문 그만, 구현 계획으로 넘어가기 | REQ-001, SP-001 |",
                    "| CLAR-000 | No completed clarification yet. | N/A | no | N/A | N/A |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "definition")
            result = self.run_validator(root, "definition")
            self.assertEqual(result.returncode, 3, result.stdout)
            self.assertIn("AWAITING_USER definition", result.stdout)
            self.assertIn("Option 3: docs plus hook metadata", result.stdout)
            self.assertNotIn("구현 계획으로 넘어가기", result.stdout)

    def test_definition_store_cheap_check_keeps_awaiting_user(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(
                DEFINITION_TEXT.replace(
                    "| PENDING-000 | N/A | No pending clarification. | N/A | N/A | N/A | N/A | none |",
                    "| PENDING-001 | 큰방향 | Which goal should be clarified? | Option 1: A; Option 2: B | Option 1 | N/A | This keeps the hot path small. | pending |",
                ).replace(
                    "| CLAR-001 | Which correction boundary should definition capture? Options: fix only reported behavior, include adjacent regression guard. | User said `질문 그만, 구현 계획으로 넘어가기`. | no | 질문 그만, 구현 계획으로 넘어가기 | REQ-001, SP-001 |",
                    "| CLAR-000 | No completed clarification yet. | N/A | no | N/A | N/A |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "definition")
            self.write_definition_store(root, active_pending_ids=["PENDING-001"], current_scope="큰방향")
            result = self.run_validator(root, "definition")
            self.assertEqual(result.returncode, 3, result.stdout)
            self.assertIn("AWAITING_USER definition", result.stdout)

    def test_definition_store_rejects_active_pending_mismatch(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(
                DEFINITION_TEXT.replace(
                    "| PENDING-000 | N/A | No pending clarification. | N/A | N/A | N/A | N/A | none |",
                    "| PENDING-001 | 큰방향 | Which goal should be clarified? | Option 1: A; Option 2: B | Option 1 | N/A | This keeps the hot path small. | pending |",
                ).replace(
                    "| CLAR-001 | Which correction boundary should definition capture? Options: fix only reported behavior, include adjacent regression guard. | User said `질문 그만, 구현 계획으로 넘어가기`. | no | 질문 그만, 구현 계획으로 넘어가기 | REQ-001, SP-001 |",
                    "| CLAR-000 | No completed clarification yet. | N/A | no | N/A | N/A |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "definition")
            self.write_definition_store(root, active_pending_ids=["PENDING-999"], current_scope="큰방향")
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("active pending IDs must match", result.stdout)

    def test_definition_store_rejects_ledger_affected_id_missing_from_trace(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            self.write_definition_store(
                root,
                active_pending_ids=[],
                current_scope="큰방향",
                affected_ids=["REQ-001", "SP-001"],
                trace_affected_ids=["REQ-001"],
            )
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("affected ID `SP-001` must appear in trace-index", result.stdout)

    def test_definition_store_rejects_medium_risk_without_targeted_sync_before_approval(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            self.write_definition_store(
                root,
                active_pending_ids=[],
                current_scope="주요결정",
                risk_level="medium",
                sync_status="pending",
            )
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("medium-risk decision", result.stdout)

    def test_definition_store_rejects_high_risk_without_full_sync_while_pending(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(
                DEFINITION_TEXT.replace(
                    "| PENDING-000 | N/A | No pending clarification. | N/A | N/A | N/A | N/A | none |",
                    "| PENDING-001 | 큰방향 | Which ownership model should be clarified? | Option 1: A; Option 2: B | Option 1 | N/A | Ownership changes require full consistency. | pending |",
                ).replace(
                    "| CLAR-001 | Which correction boundary should definition capture? Options: fix only reported behavior, include adjacent regression guard. | User said `질문 그만, 구현 계획으로 넘어가기`. | no | 질문 그만, 구현 계획으로 넘어가기 | REQ-001, SP-001 |",
                    "| CLAR-000 | No completed clarification yet. | N/A | no | N/A | N/A |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "definition")
            self.write_definition_store(
                root,
                active_pending_ids=["PENDING-001"],
                current_scope="큰방향",
                risk_level="high",
                sync_status="targeted-synced",
            )
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("high-risk decision", result.stdout)

    def test_definition_store_rejects_stale_snapshot_before_approval(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            self.write_definition_store(
                root,
                active_pending_ids=[],
                current_scope="큰방향",
                fingerprint="0" * 64,
            )
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("snapshot fingerprint must match", result.stdout)

    def test_definition_store_targeted_sync_allows_pending_question(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(
                DEFINITION_TEXT.replace(
                    "| PENDING-000 | N/A | No pending clarification. | N/A | N/A | N/A | N/A | none |",
                    "| PENDING-001 | 주요결정 | Which policy should be clarified? | Option 1: A; Option 2: B | Option 1 | N/A | This policy answer needs targeted sync. | pending |",
                ).replace(
                    "| CLAR-001 | Which correction boundary should definition capture? Options: fix only reported behavior, include adjacent regression guard. | User said `질문 그만, 구현 계획으로 넘어가기`. | no | 질문 그만, 구현 계획으로 넘어가기 | REQ-001, SP-001 |",
                    "| CLAR-001 | Which top direction should definition capture? Options: immediate fix, reusable workflow guard. | User selected immediate fix. | no | N/A | REQ-001, SP-001 |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "definition")
            self.write_question_scope_transition_review(root)
            self.write_definition_store(
                root,
                active_pending_ids=["PENDING-001"],
                current_scope="주요결정",
                risk_level="medium",
                sync_status="targeted-synced",
            )
            result = self.run_validator(root, "definition")
            self.assertEqual(result.returncode, 3, result.stdout)
            self.assertIn("질문 범위: 주요결정", result.stdout)

    def test_definition_stop_signal_requires_transition_risk_files(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            stage_dir = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition"
            (stage_dir / "transition-risk-goal.md").unlink()
            (stage_dir / "transition-risk.md").unlink()
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("transition-risk-goal.md", result.stdout)
            self.assertIn("transition-risk.md", result.stdout)

    def test_definition_transition_risk_goal_fingerprint_must_match(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            goal = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "transition-risk-goal.md"
            current = goal.read_text(encoding="utf-8")
            goal.write_text(
                current.replace(
                    "Definition Artifact Fingerprint: sha256:",
                    "Definition Artifact Fingerprint: sha256:" + "1" * 64 + "\n\nOriginal Fingerprint: sha256:",
                    1,
                ),
                encoding="utf-8",
            )
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Definition Artifact Fingerprint", result.stdout)

    def test_definition_transition_risk_requires_user_confirmation(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            risk = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "transition-risk.md"
            risk.write_text(risk.read_text(encoding="utf-8").replace("User confirmed no material risks.", "pending"), encoding="utf-8")
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("must record User Confirmation", result.stdout)

    def test_definition_transition_risk_ask_follow_up_requires_pending_clarification(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            risk = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "transition-risk.md"
            risk.write_text(risk.read_text(encoding="utf-8").replace("not-applicable", "ask-follow-up"), encoding="utf-8")
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("must have active Pending Clarifications", result.stdout)

    def test_definition_transition_risk_apply_requires_reflected_evidence(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            risk = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "transition-risk.md"
            risk.write_text(
                risk.read_text(encoding="utf-8")
                .replace("No material transition risks found.", "A missing failure case should become part of the definition.")
                .replace("not-applicable | Proceed", "uncovered | Proceed", 1)
                .replace("not-applicable", "apply-to-definition"),
                encoding="utf-8",
            )
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("reflected definition evidence is missing", result.stdout)

    def test_definition_transition_risk_requires_two_labeled_resolution_options(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            risk = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "transition-risk.md"
            risk.write_text(
                """# Transition Risk

## Risk Generation Basis

Generated after stop signal.

## Generated Risk Cases

| ID | Category | Risk Case | Affected Definition Area | Definition Coverage | Prior Answer Check | Suggested Handling | User Confirmation | Disposition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RISK-001 | acceptance | Acceptance criteria does not decide which source proves success, so planning can validate the wrong artifact. | Acceptance Criteria | ambiguous | not-answered | Clarify the success source in definition. | User accepts residual risk explicitly. | accepted-risk |

## Suggested Definition Updates

No definition updates required.

## User Confirmation

User accepts residual risk explicitly.

## Final Disposition

Risk accepted.
""",
                encoding="utf-8",
            )
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Suggested Handling must explain at least two labeled resolution options", result.stdout)

    def test_definition_transition_risk_accepts_material_risk_with_two_resolution_options(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            risk = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "transition-risk.md"
            risk.write_text(
                """# Transition Risk

## Risk Generation Basis

Generated after stop signal.

## Generated Risk Cases

| ID | Category | Risk Case | Affected Definition Area | Definition Coverage | Prior Answer Check | Suggested Handling | User Confirmation | Disposition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RISK-001 | acceptance | Acceptance criteria does not decide which source proves success, so planning can validate the wrong artifact. | Acceptance Criteria | ambiguous | not-answered | Option 1: define source-file validation in Acceptance Criteria; Option 2: accept generated-artifact validation as a residual risk and record the tradeoff. | User explicitly accepts the residual risk for generated-artifact validation. | accepted-risk |

## Suggested Definition Updates

No definition updates required.

## User Confirmation

User explicitly accepts the residual risk for generated-artifact validation.

## Final Disposition

Risk accepted with two resolution options presented.
""",
                encoding="utf-8",
            )
            result = self.run_validator(root, "definition")
            self.assertEqual(result.returncode, 0, result.stdout)

    def test_definition_transition_risk_rejects_invalid_prior_answer_check(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            risk = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "transition-risk.md"
            risk.write_text(
                """# Transition Risk

## Risk Generation Basis

Generated after stop signal.

## Generated Risk Cases

| ID | Category | Risk Case | Affected Definition Area | Definition Coverage | Prior Answer Check | Suggested Handling | User Confirmation | Disposition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RISK-001 | acceptance | Acceptance criteria does not decide which source proves success, so planning can validate the wrong artifact. | Acceptance Criteria | ambiguous | answered-covered | Option 1: define source-file validation in Acceptance Criteria; Option 2: accept generated-artifact validation as a residual risk and record the tradeoff. | User explicitly accepts the residual risk for generated-artifact validation. | accepted-risk |

## Suggested Definition Updates

No definition updates required.

## User Confirmation

User explicitly accepts the residual risk for generated-artifact validation.

## Final Disposition

Risk accepted.
""",
                encoding="utf-8",
            )
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Prior Answer Check must be one of", result.stdout)

    def test_definition_transition_risk_rejects_prior_answer_parked_as_risk(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            risk = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "transition-risk.md"
            risk.write_text(
                """# Transition Risk

## Risk Generation Basis

Generated after stop signal.

## Generated Risk Cases

| ID | Category | Risk Case | Affected Definition Area | Definition Coverage | Prior Answer Check | Suggested Handling | User Confirmation | Disposition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RISK-001 | scope | The user answer selected the docs boundary, but the definition does not reflect that boundary yet. | Boundaries | uncovered | answered-not-reflected | Option 1: apply the answered boundary to definition; Option 2: ask a follow-up to resolve the missing reflection. | User explicitly accepts the residual risk. | accepted-risk |

## Suggested Definition Updates

No definition updates required.

## User Confirmation

User explicitly accepts the residual risk.

## Final Disposition

Incorrectly parked as residual risk.
""",
                encoding="utf-8",
            )
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("based on an existing user answer", result.stdout)

    def test_definition_transition_risk_rejects_already_decided_content(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            risk = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "transition-risk.md"
            risk.write_text(
                """# Transition Risk

## Risk Generation Basis

Generated after stop signal.

## Generated Risk Cases

| ID | Category | Risk Case | Affected Definition Area | Definition Coverage | Prior Answer Check | Suggested Handling | User Confirmation | Disposition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RISK-001 | scope | Already confirmed scope must be remembered during implementation planning. | Boundaries | uncovered | not-answered | Keep the existing decision as an implementation-plan checkpoint. | User confirmed this was already decided. | accepted-risk |

## Suggested Definition Updates

No definition updates required.

## User Confirmation

User confirmed this was already decided.

## Final Disposition

Already-decided content was incorrectly listed as risk.
""",
                encoding="utf-8",
            )
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("already-decided or already answered/reflected definition content as a risk", result.stdout)


    def test_definition_goal_file_is_not_required(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            goal = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "goal.md"
            self.assertFalse(goal.exists())
            result = self.run_validator(root, "definition")
            self.assertEqual(result.returncode, 0, result.stdout)

    def test_definition_pending_clarification_does_not_require_goal(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(
                DEFINITION_TEXT.replace(
                    "| PENDING-000 | N/A | No pending clarification. | N/A | N/A | N/A | N/A | none |",
                    "| PENDING-001 | 큰방향 | Which model scope? | Option 1: A; Option 2: B | Option 1 | N/A | This changes scope. | pending |",
                ).replace(
                    "| CLAR-001 | Which correction boundary should definition capture? Options: fix only reported behavior, include adjacent regression guard. | User said `질문 그만, 구현 계획으로 넘어가기`. | no | 질문 그만, 구현 계획으로 넘어가기 | REQ-001, SP-001 |",
                    "| CLAR-000 | No completed clarification yet. | N/A | no | N/A | N/A |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "definition")
            result = self.run_validator(root, "definition")
            self.assertEqual(result.returncode, 3, result.stdout)
            self.assertIn("AWAITING_USER definition", result.stdout)

    def test_definition_boundary_scope_narrowing_requires_traceable_source(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(
                DEFINITION_TEXT.replace(
                    "Only approved behavior is included.",
                    "Organizer account lifecycle is out of scope for this request.",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "definition")
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Boundaries records a scope narrowing or exclusion without a traceable source ID", result.stdout)

    def test_definition_boundary_scope_narrowing_accepts_traceable_source(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(
                DEFINITION_TEXT.replace(
                    "Only approved behavior is included.",
                    "Organizer account lifecycle is out of scope for this request per REQ-001.",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "definition")
            result = self.run_validator(root, "definition")
            self.assertEqual(result.returncode, 0, result.stdout)

    def test_definition_boundary_does_not_flag_non_narrowing_manual_language(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(
                DEFINITION_TEXT.replace(
                    "Only approved behavior is included.",
                    "Manual operation remains supported for existing workflows.",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "definition")
            result = self.run_validator(root, "definition")
            self.assertEqual(result.returncode, 0, result.stdout)

    def test_definition_boundary_does_not_flag_non_narrowing_korean_future_language(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(
                DEFINITION_TEXT.replace(
                    "Only approved behavior is included.",
                    "향후 운영에서도 기존 수동 절차는 계속 지원된다.",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "definition")
            result = self.run_validator(root, "definition")
            self.assertEqual(result.returncode, 0, result.stdout)

    def test_definition_boundary_flags_korean_scope_narrowing_without_source(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(
                DEFINITION_TEXT.replace(
                    "Only approved behavior is included.",
                    "계정 관리는 향후 범위로 미룬다.",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "definition")
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Boundaries records a scope narrowing or exclusion without a traceable source ID", result.stdout)

    def test_definition_pending_clarification_can_hold_unresolved_scope_narrowing(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(
                DEFINITION_TEXT.replace(
                    "Only approved behavior is included.",
                    "Organizer account lifecycle is out of scope unless the user chooses to include it.",
                ).replace(
                    "| PENDING-000 | N/A | No pending clarification. | N/A | N/A | N/A | N/A | none |",
                    "| PENDING-001 | 큰방향 | Should the lifecycle boundary be included or excluded? | Option 1: Include lifecycle behavior; Option 2: Exclude lifecycle behavior | Option 2 | N/A | This changes the approved scope boundary. | pending |",
                ).replace(
                    "| CLAR-001 | Which correction boundary should definition capture? Options: fix only reported behavior, include adjacent regression guard. | User said `질문 그만, 구현 계획으로 넘어가기`. | no | 질문 그만, 구현 계획으로 넘어가기 | REQ-001, SP-001 |",
                    "| CLAR-000 | No completed clarification yet. | N/A | no | N/A | N/A |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "definition")
            result = self.run_validator(root, "definition")
            self.assertEqual(result.returncode, 3, result.stdout)
            self.assertIn("AWAITING_USER definition", result.stdout)

    def test_definition_requires_approved_flow_inventory(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(DEFINITION_TEXT.replace("## Approved Flow Inventory", "## Removed Approved Flow Inventory"), encoding="utf-8")
            self.refresh_stage_fingerprint(root, "definition")
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Approved Flow Inventory", result.stdout)

    def test_definition_approved_flow_inventory_rejects_unknown_source(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(DEFINITION_TEXT.replace("DFLOW-001 | REQ-001, SP-001, INTENT-001", "DFLOW-001 | REQ-999"), encoding="utf-8")
            self.refresh_stage_fingerprint(root, "definition")
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("cites unknown Source ID `REQ-999`", result.stdout)

    def test_definition_approved_flow_inventory_requires_requirement_coverage(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(DEFINITION_TEXT.replace("DFLOW-001 | REQ-001, SP-001, INTENT-001", "DFLOW-001 | SP-001, INTENT-001"), encoding="utf-8")
            self.refresh_stage_fingerprint(root, "definition")
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("must include Source ID `REQ-001`", result.stdout)

    def test_definition_approved_flow_inventory_requires_policy_rule_coverage(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(DEFINITION_TEXT.replace("DFLOW-001 | REQ-001, SP-001, INTENT-001", "DFLOW-001 | REQ-001, INTENT-001"), encoding="utf-8")
            self.refresh_stage_fingerprint(root, "definition")
            result = self.run_validator(root, "definition")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("must include Source ID `SP-001`", result.stdout)

    def test_implementation_plan_requires_definition_fidelity_matrix(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "02-implementation-plan" / "implementation-plan.md"
            artifact.write_text(IMPLEMENTATION_PLAN_TEXT.replace("## Definition Fidelity Matrix", "## Removed Definition Fidelity Matrix"), encoding="utf-8")
            self.refresh_stage_fingerprint(root, "implementation-plan")
            result = self.run_validator(root, "implementation-plan")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Definition Fidelity Matrix", result.stdout)

    def test_implementation_plan_requires_definition_fidelity_columns(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "02-implementation-plan" / "implementation-plan.md"
            artifact.write_text(IMPLEMENTATION_PLAN_TEXT.replace("Must Not Interpret As", "Forbidden Meaning"), encoding="utf-8")
            self.refresh_stage_fingerprint(root, "implementation-plan")
            result = self.run_validator(root, "implementation-plan")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Must Not Interpret As", result.stdout)

    def test_implementation_plan_requires_flow_model(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "02-implementation-plan" / "implementation-plan.md"
            artifact.write_text(IMPLEMENTATION_PLAN_TEXT.replace("## Implementation Flow Model", "## Removed Implementation Flow Model"), encoding="utf-8")
            self.refresh_stage_fingerprint(root, "implementation-plan")
            result = self.run_validator(root, "implementation-plan")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Implementation Flow Model", result.stdout)

    def test_implementation_plan_requires_flow_completeness_matrix(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "02-implementation-plan" / "implementation-plan.md"
            artifact.write_text(IMPLEMENTATION_PLAN_TEXT.replace("## Flow Completeness Matrix", "## Removed Flow Completeness Matrix"), encoding="utf-8")
            self.refresh_stage_fingerprint(root, "implementation-plan")
            result = self.run_validator(root, "implementation-plan")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Flow Completeness Matrix", result.stdout)

    def test_implementation_plan_complete_flow_requires_matrix_row(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "02-implementation-plan" / "implementation-plan.md"
            artifact.write_text(
                IMPLEMENTATION_PLAN_TEXT.replace(
                    "| FLOW-001 | Validator loads stage metadata -> validates implementation-plan sections and flow tables -> checks review checklist and flow shard -> returns PASS or detailed failure output. | Request artifacts are not mutated; validator returns PASS for valid artifacts or validation errors for invalid artifacts. | Missing flow sections, missing complete-flow matrix rows, placeholder-only cells, and missing flow-completeness shard produce validation failures. | Users can observe validator PASS or a specific blocking error before implementation approval. | FLOW-001 is covered by subprocess validator tests and full unittest discovery. |\n",
                    "",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "implementation-plan")
            result = self.run_validator(root, "implementation-plan")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("complete flow `FLOW-001` must have a Flow Completeness Matrix row", result.stdout)

    def test_implementation_plan_complete_flow_requires_trigger_and_outcome(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "02-implementation-plan" / "implementation-plan.md"
            artifact.write_text(
                IMPLEMENTATION_PLAN_TEXT.replace(
                    "| FLOW-001 | DFLOW-001 | REQ-001, SP-001, INTENT-001 | Stageflow validates an implementation-plan artifact before approval. | Shallow implementation-plan artifacts fail before approval while detailed artifacts pass. | WORK-001 | complete | DFLOW-001 is in scope and has no unresolved definition gap. |",
                    "| FLOW-001 | DFLOW-001 | REQ-001, SP-001, INTENT-001 |  |  | WORK-001 | complete | DFLOW-001 is in scope and has no unresolved definition gap. |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "implementation-plan")
            result = self.run_validator(root, "implementation-plan")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("must include substantive `Trigger Or Entry`", result.stdout)
            self.assertIn("must include substantive `Target Outcome`", result.stdout)

    def test_implementation_plan_rejects_unknown_definition_flow(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "02-implementation-plan" / "implementation-plan.md"
            artifact.write_text(IMPLEMENTATION_PLAN_TEXT.replace("| FLOW-001 | DFLOW-001 |", "| FLOW-001 | DFLOW-999 |"), encoding="utf-8")
            self.refresh_stage_fingerprint(root, "implementation-plan")
            result = self.run_validator(root, "implementation-plan")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unknown Definition Flow ID `DFLOW-999`", result.stdout)

    def test_implementation_plan_requires_all_definition_flows(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            definition = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            definition.write_text(
                DEFINITION_TEXT.replace(
                    "| DFLOW-001 | REQ-001, SP-001, INTENT-001 | User requests behavior. | User | User sees the planned corrected response. | Required state is updated according to policy. | Errors remain recoverable for the user. | in-scope |",
                    "| DFLOW-001 | REQ-001, SP-001, INTENT-001 | User requests behavior. | User | User sees the planned corrected response. | Required state is updated according to policy. | Errors remain recoverable for the user. | in-scope |\n| DFLOW-002 | REQ-001, SP-001 | System reports an empty state. | System consumer | Empty state response is observable. | No state change: empty-state response only. | Empty state is returned without failure. | in-scope |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "definition")
            self.refresh_stage_fingerprint(root, "implementation-plan")
            result = self.run_validator(root, "implementation-plan")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("must include approved Definition Flow `DFLOW-002`", result.stdout)

    def test_implementation_plan_external_boundary_definition_flow_cannot_be_complete(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            definition = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            definition.write_text(
                DEFINITION_TEXT.replace(
                    "| DFLOW-001 | REQ-001, SP-001, INTENT-001 | User requests behavior. | User | User sees the planned corrected response. | Required state is updated according to policy. | Errors remain recoverable for the user. | in-scope |",
                    "| DFLOW-001 | REQ-001, SP-001, INTENT-001 | External consumer requests behavior. | External consumer | Consumer observes the repo boundary response. | Current repo exposes the boundary; external consumer owns downstream state. | External consumer handles downstream failure. | external-boundary-by-definition |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "definition")
            self.refresh_stage_fingerprint(root, "implementation-plan")
            result = self.run_validator(root, "implementation-plan")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("must use `external-boundary-by-definition`", result.stdout)

    def test_implementation_plan_rejects_unknown_primary_work_item(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "02-implementation-plan" / "implementation-plan.md"
            artifact.write_text(IMPLEMENTATION_PLAN_TEXT.replace("| WORK-001 | complete |", "| WORK-999 | complete |"), encoding="utf-8")
            self.refresh_stage_fingerprint(root, "implementation-plan")
            result = self.run_validator(root, "implementation-plan")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unknown Primary Work Item `WORK-999`", result.stdout)

    def test_implementation_plan_rejects_unknown_coverage_work_item(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "02-implementation-plan" / "implementation-plan.md"
            artifact.write_text(IMPLEMENTATION_PLAN_TEXT.replace("| SP-001 | WORK-001 |", "| SP-001 | WORK-999 |"), encoding="utf-8")
            self.refresh_stage_fingerprint(root, "implementation-plan")
            result = self.run_validator(root, "implementation-plan")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unknown Work Item ID `WORK-999`", result.stdout)

    def test_implementation_plan_return_to_definition_blocks_approval(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "02-implementation-plan" / "implementation-plan.md"
            artifact.write_text(IMPLEMENTATION_PLAN_TEXT.replace("| WORK-001 | complete |", "| WORK-001 | return-to-definition |"), encoding="utf-8")
            self.refresh_stage_fingerprint(root, "implementation-plan")
            result = self.run_validator(root, "implementation-plan")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("resolve the definition gap before approval", result.stdout)

    def test_implementation_plan_complete_flow_rejects_placeholder_matrix_cell(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "02-implementation-plan" / "implementation-plan.md"
            artifact.write_text(
                IMPLEMENTATION_PLAN_TEXT.replace(
                    "Request artifacts are not mutated; validator returns PASS for valid artifacts or validation errors for invalid artifacts.",
                    "N/A",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "implementation-plan")
            result = self.run_validator(root, "implementation-plan")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("must include substantive `State/Data Transitions`", result.stdout)

    def test_implementation_plan_complete_flow_rejects_generic_ordered_path(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "02-implementation-plan" / "implementation-plan.md"
            artifact.write_text(
                IMPLEMENTATION_PLAN_TEXT.replace(
                    "Validator loads stage metadata -> validates implementation-plan sections and flow tables -> checks review checklist and flow shard -> returns PASS or detailed failure output.",
                    "Implement service and UI",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "implementation-plan")
            result = self.run_validator(root, "implementation-plan")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Ordered Implementation Path is too generic", result.stdout)

    def test_implementation_plan_complete_flow_rejects_generic_validation_evidence(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "02-implementation-plan" / "implementation-plan.md"
            artifact.write_text(
                IMPLEMENTATION_PLAN_TEXT.replace(
                    "FLOW-001 is covered by subprocess validator tests and full unittest discovery.",
                    "Run tests",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "implementation-plan")
            result = self.run_validator(root, "implementation-plan")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Validation Evidence is too generic", result.stdout)

    def test_implementation_plan_rejects_shallow_work_items(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "02-implementation-plan" / "implementation-plan.md"
            artifact.write_text(IMPLEMENTATION_PLAN_TEXT.replace("FLOW-001 adds required technical sections and work-item columns to the stage metadata, then rejects generic implementation text.", "Implement behavior."), encoding="utf-8")
            self.refresh_stage_fingerprint(root, "implementation-plan")
            result = self.run_validator(root, "implementation-plan")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("too generic", result.stdout)

    def test_implementation_plan_scope_narrowing_requires_definition_source(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "02-implementation-plan" / "implementation-plan.md"
            artifact.write_text(
                IMPLEMENTATION_PLAN_TEXT.replace(
                    "| WORK-001 | REQ-001, SP-001, INTENT-001 | Enforce the approved artifact quality gate. | Add validator metadata, rule docs, prompts, and tests for that gate. | New product behavior, new approval semantics, or unrelated workflow changes. | Return to definition before planning a new meaning. |",
                    "| WORK-001 | N/A | Enforce the approved artifact quality gate. | Implement read-only lookup behavior for the narrowed plan. | New product behavior, new approval semantics, or unrelated workflow changes. | Return to definition before planning a new meaning. |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "implementation-plan")
            result = self.run_validator(root, "implementation-plan")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Definition Fidelity Matrix row `WORK-001` records a scope narrowing or exclusion without a valid definition source ID in `Definition Source`", result.stdout)

    def test_implementation_plan_scope_narrowing_rejects_unknown_definition_source(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "02-implementation-plan" / "implementation-plan.md"
            artifact.write_text(
                IMPLEMENTATION_PLAN_TEXT.replace(
                    "| WORK-001 | REQ-001, SP-001, INTENT-001 | Enforce the approved artifact quality gate. | Add validator metadata, rule docs, prompts, and tests for that gate. | New product behavior, new approval semantics, or unrelated workflow changes. | Return to definition before planning a new meaning. |",
                    "| WORK-001 | REQ-999 | Enforce the approved artifact quality gate. | Implement read-only lookup behavior for the narrowed plan. | New product behavior, new approval semantics, or unrelated workflow changes. | Return to definition before planning a new meaning. |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "implementation-plan")
            result = self.run_validator(root, "implementation-plan")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("without a valid definition source ID in `Definition Source`", result.stdout)

    def test_implementation_plan_scope_narrowing_rejects_source_outside_definition_source_column(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "02-implementation-plan" / "implementation-plan.md"
            artifact.write_text(
                IMPLEMENTATION_PLAN_TEXT.replace(
                    "| WORK-001 | REQ-001, SP-001, INTENT-001 | Enforce the approved artifact quality gate. | Add validator metadata, rule docs, prompts, and tests for that gate. | New product behavior, new approval semantics, or unrelated workflow changes. | Return to definition before planning a new meaning. |",
                    "| WORK-001 | N/A | Enforce the approved artifact quality gate. | Implement read-only lookup behavior for the narrowed plan per REQ-001. | New product behavior, new approval semantics, or unrelated workflow changes. | Return to definition before planning a new meaning. |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "implementation-plan")
            result = self.run_validator(root, "implementation-plan")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("without a valid definition source ID in `Definition Source`", result.stdout)

    def test_implementation_plan_scope_narrowing_rejects_existing_unrelated_definition_source(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            definition = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            definition.write_text(
                DEFINITION_TEXT.replace(
                    "| REQ-001 | bugfix | User request. | Implement corrected behavior. | No unrelated scope. | OUT-001, PROB-001 |",
                    "| REQ-001 | bugfix | User request. | Implement corrected behavior. | No unrelated scope. | OUT-001, PROB-001 |\n| REQ-002 | feature | User answer. | Organizer lookup is read-only for this request. | Account lifecycle is out of scope. | OUT-001 |",
                ).replace("DFLOW-001 | REQ-001, SP-001, INTENT-001", "DFLOW-001 | REQ-001, REQ-002, SP-001, INTENT-001"),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "definition")
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "02-implementation-plan" / "implementation-plan.md"
            artifact.write_text(
                IMPLEMENTATION_PLAN_TEXT.replace(
                    "| WORK-001 | REQ-001, SP-001, INTENT-001 | Enforce the approved artifact quality gate. | Add validator metadata, rule docs, prompts, and tests for that gate. | New product behavior, new approval semantics, or unrelated workflow changes. | Return to definition before planning a new meaning. |",
                    "| WORK-001 | REQ-001 | Enforce the approved artifact quality gate. | Implement read-only lookup behavior for the narrowed plan. | New product behavior, new approval semantics, or unrelated workflow changes. | Return to definition before planning a new meaning. |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "implementation-plan")
            result = self.run_validator(root, "implementation-plan")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("without a valid definition source ID in `Definition Source`", result.stdout)

    def test_implementation_plan_scope_narrowing_accepts_definition_source(self) -> None:
        with temp_project() as root:
            self.create_project(root)
            definition = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            definition.write_text(
                DEFINITION_TEXT.replace(
                    "| REQ-001 | bugfix | User request. | Implement corrected behavior. | No unrelated scope. | OUT-001, PROB-001 |",
                    "| REQ-001 | bugfix | User request. | Implement corrected behavior. | No unrelated scope. | OUT-001, PROB-001 |\n| REQ-002 | feature | User answer. | Organizer lookup is read-only for this request. | Account lifecycle is out of scope. | OUT-001 |",
                ).replace("DFLOW-001 | REQ-001, SP-001, INTENT-001", "DFLOW-001 | REQ-001, REQ-002, SP-001, INTENT-001"),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "definition")
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "02-implementation-plan" / "implementation-plan.md"
            artifact.write_text(
                IMPLEMENTATION_PLAN_TEXT.replace(
                    "| WORK-001 | REQ-001, SP-001, INTENT-001 | Enforce the approved artifact quality gate. | Add validator metadata, rule docs, prompts, and tests for that gate. | New product behavior, new approval semantics, or unrelated workflow changes. | Return to definition before planning a new meaning. |",
                    "| WORK-001 | REQ-002 | Enforce the approved artifact quality gate. | Implement read-only compatibility behavior for that gate. | New product behavior, new approval semantics, or unrelated workflow changes. | Return to definition before planning a new meaning. |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "implementation-plan")
            result = self.run_validator(root, "implementation-plan")
            self.assertEqual(result.returncode, 0, result.stdout)

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
