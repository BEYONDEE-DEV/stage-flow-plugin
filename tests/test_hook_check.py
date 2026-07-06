
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
            self.write_review_files(stage_dir, phase, fingerprint, STAGE_RULE_IDS[phase])
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

    def write_definition_store(
        self,
        root: Path,
        *,
        active_pending_ids: list[str],
        current_scope: str,
        fingerprint: str | None = None,
        current_gate: str = "pending-answer",
        active_pending_questions: list[dict[str, str]] | None = None,
    ) -> None:
        stage_dir = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition"
        store_dir = stage_dir / "definition-store"
        store_dir.mkdir(exist_ok=True)
        if fingerprint is None:
            fingerprint = hashlib.sha256((stage_dir / "definition.md").read_bytes()).hexdigest()
        if active_pending_questions is None:
            active_pending_questions = self.pending_questions_from_definition(stage_dir / "definition.md", active_pending_ids)
        (store_dir / "working-set.json").write_text(
            json.dumps(
                {
                    "active_pending_ids": active_pending_ids,
                    "active_pending_questions": active_pending_questions,
                    "current_scope": current_scope,
                    "latest_answer": None,
                    "next_question_candidate_ids": [],
                    "risk_level": "low",
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (store_dir / "decision-ledger.jsonl").write_text("", encoding="utf-8")
        (store_dir / "trace-index.json").write_text(
            json.dumps({"traces": []}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (store_dir / "sync-state.json").write_text(
            json.dumps(
                {"definition_fingerprint": f"sha256:{fingerprint}", "current_gate": current_gate, "decision_sync": {}},
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    def append_store_decision(
        self,
        root: Path,
        *,
        decision_id: str = "DEC-901",
        source_pending_id: str = "PENDING-001",
        affected_ids: list[str] | None = None,
        risk_level: str = "low",
        sync_status: str = "working-set-only",
        include_trace: bool = True,
        include_sync: bool = True,
    ) -> None:
        affected_ids = affected_ids or ["REQ-001"]
        store_dir = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition-store"
        ledger_path = store_dir / "decision-ledger.jsonl"
        with ledger_path.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {
                        "decision_id": decision_id,
                        "source_pending_id": source_pending_id,
                        "decision": "Recorded user answer for hook test.",
                        "affected_ids": affected_ids,
                        "risk_level": risk_level,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
        if include_trace:
            trace_path = store_dir / "trace-index.json"
            trace_index = json.loads(trace_path.read_text(encoding="utf-8"))
            trace_index.setdefault("traces", []).append(
                {
                    "pending_id": source_pending_id,
                    "decision_id": decision_id,
                    "affected_ids": affected_ids,
                }
            )
            trace_path.write_text(json.dumps(trace_index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if include_sync:
            sync_path = store_dir / "sync-state.json"
            sync_state = json.loads(sync_path.read_text(encoding="utf-8"))
            sync_state.setdefault("decision_sync", {})[decision_id] = {
                "risk_level": risk_level,
                "status": sync_status,
            }
            sync_path.write_text(json.dumps(sync_state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def replace_store_batch(self, root: Path, *, pending_id: str = "PENDING-002") -> None:
        store_dir = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition-store"
        working_set_path = store_dir / "working-set.json"
        working_set = json.loads(working_set_path.read_text(encoding="utf-8"))
        working_set["active_pending_ids"] = [pending_id]
        working_set["active_pending_questions"] = [
            {
                "id": pending_id,
                "scope": "큰방향",
                "question": "Which outcome should this clarify?",
                "options": "Option 1: status readability; Option 2: traceability for reviewers",
                "recommended_option": "Option 1",
                "transition_option": "N/A",
                "why_this_matters": "결과 우선순위는 아직 큰방향 질문입니다.",
                "status": "pending",
            }
        ]
        working_set_path.write_text(json.dumps(working_set, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    @staticmethod
    def next_batch_message() -> str:
        return (
            "Which outcome should this clarify?\n"
            "Option 1: status readability\n"
            "Option 2: traceability for reviewers"
        )

    def pending_questions_from_definition(self, path: Path, active_pending_ids: list[str]) -> list[dict[str, str]]:
        text = path.read_text(encoding="utf-8")
        marker = "## Pending Clarifications"
        if marker not in text:
            return []
        tail = text.split(marker, 1)[1]
        next_heading = tail.find("\n## ")
        section = tail[:next_heading] if next_heading != -1 else tail
        lines = [line.strip() for line in section.splitlines() if line.strip().startswith("|")]
        if len(lines) < 3:
            return []
        headers = [cell.strip() for cell in lines[0].strip("|").split("|")]
        wanted = {item.upper() for item in active_pending_ids}
        questions: list[dict[str, str]] = []
        for line in lines[2:]:
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            row = {header: cells[index] if index < len(cells) else "" for index, header in enumerate(headers)}
            if row.get("ID", "").upper() not in wanted:
                continue
            if row.get("Status", "").strip().lower() not in {"pending", "awaiting"}:
                continue
            questions.append(
                {
                    "id": row.get("ID", ""),
                    "scope": row.get("Question Scope", ""),
                    "question": row.get("Question", ""),
                    "options": row.get("Options", ""),
                    "recommended_option": row.get("Recommended Option", ""),
                    "transition_option": row.get("Transition Option", "N/A"),
                    "why_this_matters": row.get("Why This Matters", ""),
                    "status": row.get("Status", "pending"),
                }
            )
        return questions

    def write_pending_definition(self, root: Path, *, include_store: bool = True) -> None:
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
        if include_store:
            self.write_definition_store(root, active_pending_ids=["PENDING-001"], current_scope="큰방향")

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
            self.assertIn("definition-store", result["turn_start_instruction"])
            self.assertNotIn("event", wire_output)
            self.assertNotIn("status", wire_output)
            self.assertNotIn("turn_start_action", wire_output)

    def test_user_prompt_submit_resolves_parent_stageflow_root_from_nested_cwd(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            self.write_pending_definition(root)
            nested = root / "events-api" / "src" / "main"
            nested.mkdir(parents=True)

            payload = {"session_id": "session-1", "prompt": "workflow status"}
            proc = subprocess.run(
                [sys.executable, str(HOOK_CHECK), "--event", "user_prompt_submit", "--root", str(nested)],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
            )

            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            result = self.read_hook_state(root, payload)
            self.assertEqual(result["root"], str(root))
            self.assertEqual(result["status"], "AWAITING_USER")
            self.assertEqual(result["turn_start_action"], "handle_awaiting_user_clarification")
            self.assertIn("pending clarification", result["pending_clarification_output"])
            self.assertFalse((nested / ".stageflow" / "hook-state").exists())

    def test_stop_blocks_request_creation_without_definition_store(self) -> None:
        with temp_project() as root:
            self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "workflow status"})
            request_dir = root / ".stageflow" / "requests" / REQUEST_ID
            (root / ".stageflow" / "sessions" / "session-1").mkdir(parents=True)
            request_dir.mkdir(parents=True)
            (root / ".stageflow" / "index.json").write_text(
                json.dumps({"version": "1", "requests": [{"id": REQUEST_ID, "title": "Test", "status": "definition"}]}, indent=2),
                encoding="utf-8",
            )
            (root / ".stageflow" / "sessions" / "session-1" / "current.json").write_text(
                json.dumps({"request_id": REQUEST_ID, "phase": "definition"}, indent=2),
                encoding="utf-8",
            )
            (request_dir / "state.json").write_text(
                json.dumps({"request_id": REQUEST_ID, "phase": "definition"}, indent=2),
                encoding="utf-8",
            )
            (request_dir / "01-definition").mkdir()
            result = self.run_hook(
                root,
                "stop",
                {"session_id": "session-1", "last_assistant_message": "created request"},
                expected_returncode=0,
            )
            self.assertEqual(result["status"], "BLOCKED")
            self.assertEqual(result["_wire_output"]["reason"], "Stageflow cannot advance yet because the current workflow gate is not complete.")

    def test_stop_blocks_request_creation_with_invalid_definition_store(self) -> None:
        with temp_project() as root:
            self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "workflow status"})
            self.create_project(root, "definition")
            store_dir = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition-store"
            store_dir.mkdir()
            result = self.run_hook(
                root,
                "stop",
                {"session_id": "session-1", "last_assistant_message": "created request"},
                expected_returncode=0,
            )
            self.assertEqual(result["status"], "BLOCKED")
            self.assertEqual(result["_wire_output"]["reason"], "Stageflow cannot advance yet because the current workflow gate is not complete.")

    def test_request_creation_allows_stageflow_apply_patch_artifacts(self) -> None:
        with temp_project() as root:
            self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "workflow status"})
            result = self.run_hook(
                root,
                "pre_tool_use",
                {
                    "session_id": "session-1",
                    "tool_name": "apply_patch",
                    "tool_input": {
                        "command": "*** Begin Patch\n*** Add File: .stageflow/requests/20260621-1200-test-request/state.json\n+{}\n*** End Patch\n"
                    },
                },
            )
            self.assertEqual(result["_wire_output"], {})

    def test_plain_prompt_without_current_prepasses(self) -> None:
        with temp_project() as root:
            result = self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "hello"})
            self.assertEqual(result["status"], "PREPASS")
            self.assertEqual(result["turn_start_action"], "none")
            self.assertEqual(result["_stdout"], "")

    def test_stageflow_plugin_maintenance_prompt_without_current_prepasses(self) -> None:
        with temp_project() as root:
            result = self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "fix Stageflow plugin hook docs"})
            self.assertEqual(result["status"], "PREPASS")
            self.assertEqual(result["turn_start_action"], "none")
            self.assertEqual(result["_stdout"], "")

    def test_plain_prompt_clears_stale_request_required_state(self) -> None:
        with temp_project() as root:
            required = self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "workflow status"})
            self.assertEqual(required["status"], "REQUEST_REQUIRED")
            prepass = self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "commit and review linux compatibility"})
            self.assertEqual(prepass["status"], "PREPASS")
            result = self.run_hook(root, "stop", {"session_id": "session-1", "last_assistant_message": "Committed and reviewed."})
            self.assertEqual(result["status"], "PREPASS")
            self.assertEqual(result["_wire_output"], {})

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
            self.assertNotIn("preflight_marker", hook_output["additionalContext"])
            self.assertNotIn("Stageflow preflight", hook_output["additionalContext"])
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

    def test_completed_current_non_stageflow_prompt_prepasses(self) -> None:
        with temp_project() as root:
            self.create_project(root, "completed")
            result = self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "README 문구 수정해줘"})
            self.assertEqual(result["status"], "PREPASS")
            self.assertTrue(result["completed_current_prepass"])
            self.assertEqual(result["_stdout"], "")

    def test_completed_current_does_not_block_non_stageflow_write(self) -> None:
        with temp_project() as root:
            self.create_project(root, "completed")
            result = self.run_hook(
                root,
                "pre_tool_use",
                {"session_id": "session-1", "tool_name": "Write", "tool_input": {"file_path": "README.md"}},
            )
            self.assertEqual(result["_wire_output"], {})

    def test_implementation_prompt_checks_implementation_plan_gate(self) -> None:
        with temp_project() as root:
            self.create_project(root, "implementation")
            approval = root / ".stageflow" / "requests" / REQUEST_ID / "02-implementation-plan" / "approval.md"
            approval.write_text(approval.read_text(encoding="utf-8").replace("Approved.", "Not approved."), encoding="utf-8")
            result = self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "workflow implement"})
            self.assertEqual(result["status"], "IMPLEMENTATION_BLOCKED")
            self.assertEqual(result["turn_start_action"], "repair_implementation_plan_gate")
            self.assertEqual(result["implementation_entry_gate"]["status"], "FAIL")

    def test_stop_allows_response_without_preflight_marker(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "workflow status"})
            result = self.run_hook(root, "stop", {"session_id": "session-1", "last_assistant_message": "status answered"}, expected_returncode=0)
            self.assertEqual(result["status"], "PREPASS")
            self.assertEqual(result["_wire_output"], {})

    def test_stop_completion_like_response_blocks_with_safe_public_reason(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "workflow status"})
            result = self.run_hook(root, "stop", {"session_id": "session-1", "last_assistant_message": "completed"}, expected_returncode=0)
            self.assertEqual(result["status"], "BLOCKED")
            self.assertEqual(
                result["_wire_output"]["reason"],
                "Stageflow cannot advance yet because the current workflow gate is not complete.",
            )
            self.assertNotIn("completion-like response", result["_wire_output"]["reason"])
            self.assertNotIn("Stageflow preflight", result["_wire_output"]["reason"])
            self.assertNotIn(".stageflow/hook-state", result["_wire_output"]["reason"])
            self.assertNotIn("pending clarification", result["_wire_output"]["reason"].lower())

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
            self.write_definition_store(
                root,
                active_pending_ids=["PENDING-001", "PENDING-002", "PENDING-003", "PENDING-004", "PENDING-005"],
                current_scope="큰방향",
            )
            result = self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "workflow status"})
            self.assertEqual(result["status"], "AWAITING_USER")
            self.assertEqual(result["turn_start_action"], "handle_awaiting_user_clarification")
            self.assertNotIn("awaiting_user_prompt_kind", result)
            self.assertEqual(result["validation"]["status"], "AWAITING_USER")
            self.assertIn("How should docs sync status", result["pending_clarification_output"])
            self.assertIn("Which validation boundary", result["pending_clarification_output"])
            self.assertIn("Option 3: docs-wide status plus hook metadata", result["pending_clarification_output"])
            self.assertNotIn("구현 계획으로 넘어가기", result["pending_clarification_output"])


    def test_awaiting_user_prompts_keep_structural_action_without_intent_classification(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            self.write_pending_definition(root)
            prompts = (
                "Option 1",
                "1번은 2번, 2번은 3번, 3번은 넘김",
                "이게 무슨 뜻이야?",
                "질문 그만, 구현 계획으로 넘어가기",
            )
            for prompt in prompts:
                with self.subTest(prompt=prompt):
                    result = self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": prompt})
                    self.assertEqual(result["status"], "AWAITING_USER")
                    self.assertEqual(result["turn_start_action"], "handle_awaiting_user_clarification")
                    self.assertNotIn("awaiting_user_prompt_kind", result)
                    self.assertIn("pending clarification", result["pending_clarification_output"])

    def test_active_pending_without_store_returns_definition_store_required(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            self.write_pending_definition(root, include_store=False)
            result = self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "Option 1"})
            self.assertEqual(result["status"], "DEFINITION_STORE_REQUIRED")
            self.assertEqual(result["turn_start_action"], "create_definition_store")
            self.assertIn("definition-store", result["turn_start_instruction"])

    def test_definition_store_required_allows_only_required_store_files(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            self.write_pending_definition(root, include_store=False)
            self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "Option 1"})
            allowed = self.run_hook(
                root,
                "pre_tool_use",
                {
                    "session_id": "session-1",
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": ".stageflow/requests/20260621-1200-test-request/01-definition/definition-store/working-set.json"
                    },
                },
            )
            self.assertEqual(allowed["_wire_output"], {})

            blocked = self.run_hook(
                root,
                "pre_tool_use",
                {
                    "session_id": "session-1",
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": ".stageflow/requests/20260621-1200-test-request/01-definition/definition.md"
                    },
                },
                expected_returncode=0,
            )
            self.assertEqual(blocked["status"], "BLOCKED")
            self.assertIn("DEFINITION_STORE_REQUIRED turns may only create required", "\n".join(blocked["warnings"]))

    def test_stop_blocks_when_definition_store_required_remains_missing(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            self.write_pending_definition(root, include_store=False)
            self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "Option 1"})
            result = self.run_hook(
                root,
                "stop",
                {"session_id": "session-1", "last_assistant_message": "준비했습니다."},
                expected_returncode=0,
            )
            self.assertEqual(result["status"], "BLOCKED")
            self.assertEqual(result["_wire_output"]["reason"], "Stageflow cannot advance yet because the current workflow gate is not complete.")

    def test_awaiting_user_allows_only_definition_clarification_writes_before_resolution(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            self.write_pending_definition(root)
            self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "1번은 2번, 2번은 3번"})
            allowed_paths = (
                ".stageflow/requests/20260621-1200-test-request/01-definition/definition-store/working-set.json",
                ".stageflow/requests/20260621-1200-test-request/01-definition/definition-store/decision-ledger.jsonl",
                ".stageflow/requests/20260621-1200-test-request/01-definition/question-backlog.md",
                ".stageflow/requests/20260621-1200-test-request/01-definition/transition-risk-goal.md",
                ".stageflow/requests/20260621-1200-test-request/01-definition/transition-risk.md",
            )
            for path in allowed_paths:
                with self.subTest(path=path):
                    allowed = self.run_hook(
                        root,
                        "pre_tool_use",
                        {
                            "session_id": "session-1",
                            "tool_name": "Write",
                            "tool_input": {"file_path": path},
                        },
                    )
                    self.assertEqual(allowed["_wire_output"], {})

            blocked_paths = (
                ".stageflow/requests/20260621-1200-test-request/01-definition/definition.md",
                ".stageflow/requests/20260621-1200-test-request/01-definition/review/final.md",
                ".stageflow/requests/20260621-1200-test-request/01-definition/approval.md",
                ".stageflow/requests/20260621-1200-test-request/02-implementation-plan/implementation-plan.md",
                ".stageflow/requests/20260621-1200-test-request/03-implementation/implementation.md",
            )
            for path in blocked_paths:
                with self.subTest(path=path):
                    blocked = self.run_hook(
                        root,
                        "pre_tool_use",
                        {
                            "session_id": "session-1",
                            "tool_name": "Write",
                            "tool_input": {"file_path": path},
                        },
                        expected_returncode=0,
                    )
                    self.assertEqual(blocked["status"], "BLOCKED")
                    self.assertIn("definition", "\n".join(blocked["warnings"]))


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
            self.assertEqual(result["status"], "BLOCKED")
            self.assertEqual(
                result["_wire_output"]["reason"],
                "Stageflow cannot advance yet because the current workflow gate is not complete.",
            )
            self.assertNotIn("must not claim completion", result["_wire_output"]["reason"])


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

    def test_awaiting_user_allows_question_scope_transition_review_subagent(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            self.write_pending_definition(root)
            self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "Option 1 설명해줘"})
            result = self.run_hook(
                root,
                "subagent_start",
                {
                    "session_id": "session-1",
                    "agent_id": "agent-scope-review",
                    "role": "question scope transition review subagent",
                    "task": "Review whether 큰방향 questions are exhausted before moving to 주요결정",
                },
            )
            self.assertEqual(result["status"], "QUESTION_SCOPE_TRANSITION_REVIEW_SUBAGENT_ALLOWED")
            self.assertTrue(result["question_scope_transition_review_allowed"])

    def test_awaiting_user_allows_definition_store_helper_subagent(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            self.write_pending_definition(root)
            self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "Option 1 설명해줘"})
            result = self.run_hook(
                root,
                "subagent_start",
                {
                    "session_id": "session-1",
                    "agent_id": "agent-impact",
                    "role": "definition-store impact candidate helper subagent",
                    "task": "Prepare impact candidates for definition-store/impact-candidates.json",
                },
            )
            self.assertEqual(result["status"], "DEFINITION_STORE_HELPER_SUBAGENT_ALLOWED")
            self.assertTrue(result["definition_store_helper_allowed"])

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
            self.assertIn("definition clarification allows only", "\n".join(result["warnings"]))
            self.assertFalse(result["_wire_output"]["continue"])
            self.assertIn("definition clarification allows only", result["_wire_output"]["stopReason"])

    def test_awaiting_user_subagent_may_only_write_question_backlog(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            self.write_pending_definition(root)
            self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "Option 1 설명해줘"})
            self.run_hook(
                root,
                "subagent_start",
                {
                    "session_id": "session-1",
                    "agent_id": "agent-questions",
                    "role": "question-generation backlog candidate subagent",
                    "task": "Prepare clarification question backlog candidates for question-backlog.md",
                },
            )
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
                    "tool_input": {"file_path": ".stageflow/requests/20260621-1200-test-request/01-definition/review/final.md"},
                },
                expected_returncode=0,
            )
            self.assertEqual(blocked["status"], "BLOCKED")
            self.assertIn("registered role", "\n".join(blocked["warnings"]))

    def test_awaiting_user_subagent_may_write_question_scope_transition_review(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            self.write_pending_definition(root)
            self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "Option 1 설명해줘"})
            self.run_hook(
                root,
                "subagent_start",
                {
                    "session_id": "session-1",
                    "agent_id": "agent-scope-review",
                    "role": "question scope transition review subagent",
                    "task": "Review whether 큰방향 questions are exhausted before moving to 주요결정",
                },
            )
            allowed = self.run_hook(
                root,
                "pre_tool_use",
                {
                    "session_id": "session-1",
                    "agent_id": "agent-scope-review",
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": ".stageflow/requests/20260621-1200-test-request/01-definition/question-scope-transition-review.md"
                    },
                },
            )
            self.assertEqual(allowed["_wire_output"], {})

    def test_awaiting_user_subagent_may_write_definition_store_json_helper(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            self.write_pending_definition(root)
            self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "Option 1 설명해줘"})
            self.run_hook(
                root,
                "subagent_start",
                {
                    "session_id": "session-1",
                    "agent_id": "agent-impact",
                    "role": "definition-store impact candidate helper subagent",
                    "task": "Prepare impact candidates for definition-store/impact-candidates.json",
                },
            )
            allowed = self.run_hook(
                root,
                "pre_tool_use",
                {
                    "session_id": "session-1",
                    "agent_id": "agent-impact",
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": ".stageflow/requests/20260621-1200-test-request/01-definition/definition-store/impact-candidates.json"
                    },
                },
            )
            self.assertEqual(allowed["_wire_output"], {})
            blocked = self.run_hook(
                root,
                "pre_tool_use",
                {
                    "session_id": "session-1",
                    "agent_id": "agent-impact",
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": ".stageflow/requests/20260621-1200-test-request/01-definition/definition-store/decision-ledger.jsonl"
                    },
                },
                expected_returncode=0,
            )
            self.assertEqual(blocked["status"], "BLOCKED")
            self.assertIn("registered role", "\n".join(blocked["warnings"]))

    def test_awaiting_user_unregistered_subagent_write_is_blocked(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            self.write_pending_definition(root)
            self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "Option 1 설명해줘"})
            result = self.run_hook(
                root,
                "pre_tool_use",
                {
                    "session_id": "session-1",
                    "agent_id": "agent-spoof",
                    "role": "definition-store impact candidate helper subagent",
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": ".stageflow/requests/20260621-1200-test-request/01-definition/definition-store/impact-candidates.json"
                    },
                },
                expected_returncode=0,
            )
            self.assertEqual(result["status"], "BLOCKED")
            self.assertIn("registered by SubagentStart", "\n".join(result["warnings"]))

    def test_awaiting_user_pending_answer_blocks_main_definition_write(self) -> None:
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
                expected_returncode=0,
            )
            self.assertEqual(result["status"], "BLOCKED")
            self.assertIn("store-only", "\n".join(result["warnings"]))

    def test_awaiting_user_store_only_blocks_definition_read(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            self.write_pending_definition(root)
            self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "Option 1"})
            for tool_name, tool_input in (
                ("Read", {"file_path": ".stageflow/requests/20260621-1200-test-request/01-definition/definition.md"}),
                ("shell_command", {"command": "sed -n '1,120p' .stageflow/requests/20260621-1200-test-request/01-definition/definition.md"}),
            ):
                with self.subTest(tool_name=tool_name):
                    result = self.run_hook(
                        root,
                        "pre_tool_use",
                        {"session_id": "session-1", "tool_name": tool_name, "tool_input": tool_input},
                        expected_returncode=0,
                    )
                    self.assertEqual(result["status"], "BLOCKED")
                    self.assertIn("may not read", "\n".join(result["warnings"]))

    def test_invalid_store_gate_does_not_use_fast_path(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            self.write_pending_definition(root)
            sync_state = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition-store" / "sync-state.json"
            data = json.loads(sync_state.read_text(encoding="utf-8"))
            data["current_gate"] = "typo-gate"
            sync_state.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            result = self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "Option 1"})
            self.assertEqual(result["status"], "WARNING")
            self.assertEqual(result["validation"]["status"], "FAIL")
            self.assertIn("current_gate", result["validation"]["output"])

    def test_invalid_store_batches_do_not_use_fast_path(self) -> None:
        cases = [
            (
                "stop option",
                [
                    {
                        "id": "PENDING-101",
                        "scope": "큰방향",
                        "question": "Which option is valid?",
                        "options": "Option 1: proceed; Option 2: keep clarifying",
                        "recommended_option": "Option 2",
                        "transition_option": "N/A",
                        "why_this_matters": "Stop signals must not count as proposal options.",
                        "status": "pending",
                    }
                ],
                "must include at least two explicit labeled proposal options",
            ),
            (
                "mixed scope",
                [
                    {
                        "id": "PENDING-101",
                        "scope": "큰방향",
                        "question": "Which top scope?",
                        "options": "Option 1: A; Option 2: B",
                        "recommended_option": "Option 1",
                        "transition_option": "N/A",
                        "why_this_matters": "Top scope matters.",
                        "status": "pending",
                    },
                    {
                        "id": "PENDING-102",
                        "scope": "주요결정",
                        "question": "Which major decision?",
                        "options": "Option 1: A; Option 2: B",
                        "recommended_option": "Option 1",
                        "transition_option": "N/A",
                        "why_this_matters": "Major decision matters.",
                        "status": "pending",
                    },
                ],
                "must use one Question Scope at a time",
            ),
            (
                "too many",
                [
                    {
                        "id": f"PENDING-10{index}",
                        "scope": "큰방향",
                        "question": f"Question {index}?",
                        "options": "Option 1: A; Option 2: B",
                        "recommended_option": "Option 1",
                        "transition_option": "N/A",
                        "why_this_matters": "Batch size matters.",
                        "status": "pending",
                    }
                    for index in range(1, 7)
                ],
                "no more than five",
            ),
        ]
        for label, questions, expected in cases:
            with self.subTest(label=label), temp_project() as root:
                self.create_project(root, "definition")
                self.write_definition_store(
                    root,
                    active_pending_ids=[question["id"] for question in questions],
                    current_scope=questions[0]["scope"],
                    active_pending_questions=questions,
                )
                result = self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "workflow status"})
                self.assertEqual(result["status"], "WARNING")
                self.assertEqual(result["validation"]["status"], "FAIL")
                self.assertIn(expected, result["validation"]["output"])

    def test_targeted_sync_gate_registers_subagent_and_allows_plan_write(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            self.write_pending_definition(root)
            self.write_definition_store(
                root,
                active_pending_ids=["PENDING-001"],
                current_scope="큰방향",
                current_gate="targeted-sync-required",
            )
            self.append_store_decision(root, risk_level="medium", sync_status="pending")
            prompt_result = self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "Option 1"})
            self.assertEqual(prompt_result["status"], "TARGETED_SYNC_REQUIRED")
            result = self.run_hook(
                root,
                "subagent_start",
                {
                    "session_id": "session-1",
                    "agent_id": "agent-targeted",
                    "role": "targeted-sync subagent",
                    "task": "Prepare targeted-sync-plan.json for affected definition sections",
                },
            )
            self.assertEqual(result["status"], "TARGETED_SYNC_SUBAGENT_ALLOWED")
            allowed = self.run_hook(
                root,
                "pre_tool_use",
                {
                    "session_id": "session-1",
                    "agent_id": "agent-targeted",
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": ".stageflow/requests/20260621-1200-test-request/01-definition/definition-store/targeted-sync-plan.json"
                    },
                },
            )
            self.assertEqual(allowed["_wire_output"], {})

    def test_live_sync_gate_overrides_turn_start_pending_answer_permissions(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            self.write_pending_definition(root)
            self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "1번"})

            store_dir = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition-store"
            sync_state_path = store_dir / "sync-state.json"
            sync_state = json.loads(sync_state_path.read_text(encoding="utf-8"))
            sync_state["current_gate"] = "targeted-sync-required"
            sync_state_path.write_text(json.dumps(sync_state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            self.append_store_decision(root, risk_level="medium", sync_status="pending")

            subagent = self.run_hook(
                root,
                "subagent_start",
                {
                    "session_id": "session-1",
                    "agent_id": "agent-targeted",
                    "role": "targeted-sync subagent",
                    "task": "Prepare targeted-sync-plan.json for affected definition sections",
                },
            )
            self.assertEqual(subagent["status"], "TARGETED_SYNC_SUBAGENT_ALLOWED")

            stale_main_write = self.run_hook(
                root,
                "pre_tool_use",
                {
                    "session_id": "session-1",
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": ".stageflow/requests/20260621-1200-test-request/01-definition/definition-store/decision-ledger.jsonl"
                    },
                },
                expected_returncode=0,
            )
            self.assertEqual(stale_main_write["status"], "BLOCKED")
            self.assertIn("current `definition-store` gate", "\n".join(stale_main_write["warnings"]))

            targeted_write = self.run_hook(
                root,
                "pre_tool_use",
                {
                    "session_id": "session-1",
                    "agent_id": "agent-targeted",
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": ".stageflow/requests/20260621-1200-test-request/01-definition/definition-store/targeted-sync-plan.json"
                    },
                },
                expected_returncode=0,
            )
            self.assertEqual(targeted_write["_wire_output"], {})

    def test_full_consistency_gate_registers_subagent_and_allows_report_write(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            self.write_pending_definition(root)
            self.write_definition_store(
                root,
                active_pending_ids=["PENDING-001"],
                current_scope="큰방향",
                current_gate="full-consistency-required",
            )
            self.append_store_decision(root, risk_level="high", sync_status="pending")
            prompt_result = self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "Option 1"})
            self.assertEqual(prompt_result["status"], "FULL_CONSISTENCY_REQUIRED")
            result = self.run_hook(
                root,
                "subagent_start",
                {
                    "session_id": "session-1",
                    "agent_id": "agent-full",
                    "role": "full-consistency subagent",
                    "task": "Prepare full-consistency-report.json with PASS or blocking issues",
                },
            )
            self.assertEqual(result["status"], "FULL_CONSISTENCY_SUBAGENT_ALLOWED")
            allowed = self.run_hook(
                root,
                "pre_tool_use",
                {
                    "session_id": "session-1",
                    "agent_id": "agent-full",
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": ".stageflow/requests/20260621-1200-test-request/01-definition/definition-store/full-consistency-report.json"
                    },
                },
            )
            self.assertEqual(allowed["_wire_output"], {})

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
            self.write_definition_store(root, active_pending_ids=["PENDING-001"], current_scope="큰방향")
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

    def test_awaiting_user_answer_requires_store_progress_even_when_batch_restated(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            self.write_pending_definition(root)
            self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "1번"})
            last_message = (
                "Docs sync status의 큰방향 범위는 어디까지인가요?\n"
                "Option 1: docs-wide status only\n"
                "Option 2: docs-wide status plus review-session scope\n"
                "Option 3: docs-wide status plus hook metadata"
            )
            result = self.run_hook(root, "stop", {"session_id": "session-1", "last_assistant_message": last_message}, expected_returncode=0)
            self.assertEqual(result["status"], "BLOCKED")

    def test_awaiting_user_duplicate_challenge_requires_store_progress(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            self.write_pending_definition(root)
            self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "이거 이미 정해진 같은 질문 아니야?"})
            last_message = (
                "Docs sync status의 큰방향 범위는 어디까지인가요?\n"
                "Option 1: docs-wide status only\n"
                "Option 2: docs-wide status plus review-session scope\n"
                "Option 3: docs-wide status plus hook metadata"
            )
            result = self.run_hook(root, "stop", {"session_id": "session-1", "last_assistant_message": last_message}, expected_returncode=0)
            self.assertEqual(result["status"], "BLOCKED")

    def test_awaiting_user_malformed_ledger_does_not_count_as_progress(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            self.write_pending_definition(root)
            self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "1번"})
            store_dir = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition-store"
            with (store_dir / "decision-ledger.jsonl").open("a", encoding="utf-8") as handle:
                handle.write("{not-json}\n")
            self.replace_store_batch(root)
            result = self.run_hook(root, "stop", {"session_id": "session-1", "last_assistant_message": self.next_batch_message()}, expected_returncode=0)
            self.assertEqual(result["status"], "BLOCKED")

    def test_awaiting_user_decision_without_trace_or_sync_does_not_count_as_progress(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            self.write_pending_definition(root)
            self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "1번"})
            self.append_store_decision(root, include_trace=False, include_sync=False)
            self.replace_store_batch(root)
            result = self.run_hook(root, "stop", {"session_id": "session-1", "last_assistant_message": self.next_batch_message()}, expected_returncode=0)
            self.assertEqual(result["status"], "BLOCKED")

    def test_awaiting_user_decision_for_unrelated_pending_does_not_count_as_progress(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            self.write_pending_definition(root)
            self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "1번"})
            self.append_store_decision(root, source_pending_id="PENDING-999")
            self.replace_store_batch(root)
            result = self.run_hook(root, "stop", {"session_id": "session-1", "last_assistant_message": self.next_batch_message()}, expected_returncode=0)
            self.assertEqual(result["status"], "BLOCKED")

    def test_awaiting_user_valid_decision_must_advance_pending_batch(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            self.write_pending_definition(root)
            self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "1번"})
            self.append_store_decision(root)
            last_message = (
                "Docs sync status의 큰방향 범위는 어디까지인가요?\n"
                "Option 1: docs-wide status only\n"
                "Option 2: docs-wide status plus review-session scope\n"
                "Option 3: docs-wide status plus hook metadata"
            )
            result = self.run_hook(root, "stop", {"session_id": "session-1", "last_assistant_message": last_message}, expected_returncode=0)
            self.assertEqual(result["status"], "BLOCKED")

    def test_awaiting_user_valid_decision_and_next_batch_passes(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            self.write_pending_definition(root)
            self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "1번"})
            self.append_store_decision(root)
            self.replace_store_batch(root)
            result = self.run_hook(root, "stop", {"session_id": "session-1", "last_assistant_message": self.next_batch_message()}, expected_returncode=0)
            self.assertEqual(result["status"], "PREPASS")

    def test_awaiting_user_stop_signal_requires_sync_gate(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            self.write_pending_definition(root)
            self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "질문 그만"})
            store_dir = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition-store"
            working_set = json.loads((store_dir / "working-set.json").read_text(encoding="utf-8"))
            working_set["active_pending_ids"] = []
            working_set["active_pending_questions"] = []
            (store_dir / "working-set.json").write_text(json.dumps(working_set, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            result = self.run_hook(root, "stop", {"session_id": "session-1", "last_assistant_message": "질문 루프를 멈춥니다."}, expected_returncode=0)
            self.assertEqual(result["status"], "BLOCKED")

    def test_awaiting_user_yes_is_not_clarification_stop_signal(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            self.write_pending_definition(root)
            self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "yes"})
            store_dir = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition-store"
            working_set = json.loads((store_dir / "working-set.json").read_text(encoding="utf-8"))
            working_set["active_pending_ids"] = []
            working_set["active_pending_questions"] = []
            (store_dir / "working-set.json").write_text(json.dumps(working_set, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            result = self.run_hook(root, "stop", {"session_id": "session-1", "last_assistant_message": "yes로 확인했습니다."}, expected_returncode=0)
            self.assertEqual(result["status"], "BLOCKED")

    def test_awaiting_user_stop_allows_korean_option_labels(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(
                artifact.read_text(encoding="utf-8").replace(
                    "| PENDING-000 | N/A | No pending clarification. | N/A | N/A | N/A | N/A | none |",
                    "| PENDING-001 | 큰방향 | 어느 범위로 정리할까요? | 선택지 1: 현재 범위만 정리; 선택지 2: 인접 범위까지 정리 | 선택지 1 | N/A | 범위 결정은 후속 질문을 줄입니다. | pending |",
                ).replace(
                    "| CLAR-001 | Which correction boundary should definition capture? Options: fix only reported behavior, include adjacent regression guard. | User said `질문 그만, 구현 계획으로 넘어가기`. | no | 질문 그만, 구현 계획으로 넘어가기 | REQ-001, SP-001 |",
                    "| CLAR-000 | No completed clarification yet. | N/A | no | N/A | N/A |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "definition")
            self.write_definition_store(root, active_pending_ids=["PENDING-001"], current_scope="큰방향")
            prompt_result = self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "선택지 설명해줘"})
            self.assertEqual(prompt_result["status"], "AWAITING_USER")
            last_message = "어느 범위로 정리할까요?\n선택지 1: 현재 범위만 정리\n선택지 2: 인접 범위까지 정리"
            result = self.run_hook(root, "stop", {"session_id": "session-1", "last_assistant_message": last_message}, expected_returncode=0)
            self.assertEqual(result["status"], "PREPASS")

    def test_awaiting_user_stop_allows_letter_option_labels(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            self.write_definition_store(
                root,
                active_pending_ids=["PENDING-777"],
                current_scope="큰방향",
                active_pending_questions=[
                    {
                        "id": "PENDING-777",
                        "scope": "큰방향",
                        "question": "Which lettered option should remain available?",
                        "options": "A: Keep current scope; B: Expand adjacent scope",
                        "recommended_option": "A",
                        "transition_option": "N/A",
                        "why_this_matters": "Letter labels are accepted by the validator and hook.",
                        "status": "pending",
                    }
                ],
            )
            prompt_result = self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "옵션 설명"})
            self.assertEqual(prompt_result["status"], "AWAITING_USER")
            last_message = "Which lettered option should remain available?\nA: Keep current scope\nB: Expand adjacent scope"
            result = self.run_hook(root, "stop", {"session_id": "session-1", "last_assistant_message": last_message}, expected_returncode=0)
            self.assertEqual(result["status"], "PREPASS")

    def test_awaiting_user_letter_answer_requires_store_progress(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            self.write_definition_store(
                root,
                active_pending_ids=["PENDING-777"],
                current_scope="큰방향",
                active_pending_questions=[
                    {
                        "id": "PENDING-777",
                        "scope": "큰방향",
                        "question": "Which lettered option should remain available?",
                        "options": "A: Keep current scope; B: Expand adjacent scope",
                        "recommended_option": "A",
                        "transition_option": "N/A",
                        "why_this_matters": "Letter labels are accepted by the validator and hook.",
                        "status": "pending",
                    }
                ],
            )
            self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "A"})
            last_message = "Which lettered option should remain available?\nA: Keep current scope\nB: Expand adjacent scope"
            result = self.run_hook(root, "stop", {"session_id": "session-1", "last_assistant_message": last_message}, expected_returncode=0)
            self.assertEqual(result["status"], "BLOCKED")

    def test_awaiting_user_letter_follow_up_can_restate_batch_without_progress(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            self.write_definition_store(
                root,
                active_pending_ids=["PENDING-777"],
                current_scope="큰방향",
                active_pending_questions=[
                    {
                        "id": "PENDING-777",
                        "scope": "큰방향",
                        "question": "Which lettered option should remain available?",
                        "options": "A: Keep current scope; B: Expand adjacent scope",
                        "recommended_option": "A",
                        "transition_option": "N/A",
                        "why_this_matters": "Letter labels are accepted by the validator and hook.",
                        "status": "pending",
                    }
                ],
            )
            self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "A 옵션 설명해줘"})
            last_message = "Which lettered option should remain available?\nA: Keep current scope\nB: Expand adjacent scope"
            result = self.run_hook(root, "stop", {"session_id": "session-1", "last_assistant_message": last_message}, expected_returncode=0)
            self.assertEqual(result["status"], "PREPASS")

    def test_awaiting_user_decision_criteria_follow_up_is_not_duplicate_challenge(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            self.write_pending_definition(root)
            self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "결정 기준이 뭐야?"})
            last_message = (
                "Docs sync status의 큰방향 범위는 어디까지인가요?\n"
                "Option 1: docs-wide status only\n"
                "Option 2: docs-wide status plus review-session scope\n"
                "Option 3: docs-wide status plus hook metadata"
            )
            result = self.run_hook(root, "stop", {"session_id": "session-1", "last_assistant_message": last_message}, expected_returncode=0)
            self.assertEqual(result["status"], "PREPASS")

    def test_awaiting_user_stop_blocks_missing_pending_batch_restatement(self) -> None:
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
            self.write_definition_store(
                root,
                active_pending_ids=["PENDING-001", "PENDING-002", "PENDING-003", "PENDING-004", "PENDING-005"],
                current_scope="큰방향",
            )
            prompt_result = self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "workflow status"})
            marker = str(prompt_result["preflight_marker"])
            result = self.run_hook(root, "stop", {"session_id": "session-1", "last_assistant_message": marker + "\n대기 중입니다."}, expected_returncode=0)
            self.assertEqual(result["status"], "BLOCKED")

    def test_awaiting_user_stop_ignores_completion_words_in_question_options(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition.md"
            artifact.write_text(
                artifact.read_text(encoding="utf-8").replace(
                    "| PENDING-000 | N/A | No pending clarification. | N/A | N/A | N/A | N/A | none |",
                    "| PENDING-001 | 세부확인 | 모의거래 결과 확정 단위는 무엇인가요? | Option 1: 하루 장이 끝날 때마다 일별 결과를 확정한다; Option 2: 선택 완료 기준은 전략 실행 기간 전체를 하나의 run으로 본다; Option 3: 일별 스냅샷과 run 전체 누적 결과를 함께 둔다 | Option 3 | N/A | 확정 단위는 결과 표시와 회귀 방지 기준을 바꿉니다. | pending |",
                ).replace(
                    "| CLAR-001 | Which correction boundary should definition capture? Options: fix only reported behavior, include adjacent regression guard. | User said `질문 그만, 구현 계획으로 넘어가기`. | no | 질문 그만, 구현 계획으로 넘어가기 | REQ-001, SP-001 |",
                    "| CLAR-000 | No completed clarification yet. | N/A | no | N/A | N/A |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "definition")
            self.write_definition_store(root, active_pending_ids=["PENDING-001"], current_scope="세부확인")
            self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "workflow status"})
            last_message = (
                "모의거래 결과 확정 단위는 무엇인가요?\n"
                "Option 1: 하루 장이 끝날 때마다 일별 결과를 확정한다\n"
                "Option 2: 선택 완료 기준은 전략 실행 기간 전체를 하나의 run으로 본다\n"
                "Option 3: 일별 스냅샷과 run 전체 누적 결과를 함께 둔다"
            )
            result = self.run_hook(root, "stop", {"session_id": "session-1", "last_assistant_message": last_message}, expected_returncode=0)
            self.assertEqual(result["status"], "PREPASS")
            self.assertEqual(result["_wire_output"], {})
            self.assertNotIn("completion_validation", result)

    def test_awaiting_user_stop_blocks_partial_pending_batch_restatement(self) -> None:
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
            self.write_definition_store(
                root,
                active_pending_ids=["PENDING-001", "PENDING-002", "PENDING-003", "PENDING-004", "PENDING-005"],
                current_scope="큰방향",
            )
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


    def test_awaiting_user_stop_does_not_enforce_question_scope_label_from_hook_guess(self) -> None:
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
            self.write_definition_store(root, active_pending_ids=["PENDING-001"], current_scope="큰방향")
            prompt_result = self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "workflow status"})
            marker = str(prompt_result["preflight_marker"])
            last_message = (
                marker
                + "\n질문: Docs sync status의 큰방향 범위는 어디까지인가요?\n"
                + "선택지: Option 1: docs-wide status only / Option 2: docs-wide status plus review-session scope"
            )
            result = self.run_hook(root, "stop", {"session_id": "session-1", "last_assistant_message": last_message}, expected_returncode=0)
            self.assertEqual(result["status"], "PREPASS")

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
            self.write_definition_store(root, active_pending_ids=["PENDING-001"], current_scope="큰방향")
            prompt_result = self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "workflow status"})
            marker = str(prompt_result["preflight_marker"])
            last_message = (
                marker
                + "\n질문: Docs sync status의 큰방향 범위는 어디까지인가요?\n"
                + "선택지: Option 1: docs-wide status only / Option 2: docs-wide status plus review-session scope"
            )
            result = self.run_hook(root, "stop", {"session_id": "session-1", "last_assistant_message": last_message}, expected_returncode=0)
            self.assertEqual(result["status"], "BLOCKED")

    def test_awaiting_user_stop_blocks_next_pending_when_not_shown(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            self.write_pending_definition(root)
            self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "1번"})
            store_dir = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition-store"
            working_set = json.loads((store_dir / "working-set.json").read_text(encoding="utf-8"))
            working_set["active_pending_ids"] = ["PENDING-002"]
            working_set["active_pending_questions"] = [
                {
                    "id": "PENDING-002",
                    "scope": "큰방향",
                    "question": "Which outcome should this clarify?",
                    "options": "Option 1: status readability; Option 2: traceability for reviewers",
                    "recommended_option": "Option 1",
                    "transition_option": "N/A",
                    "why_this_matters": "결과 우선순위는 아직 큰방향 질문입니다.",
                    "status": "pending",
                }
            ]
            (store_dir / "working-set.json").write_text(json.dumps(working_set, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            result = self.run_hook(root, "stop", {"session_id": "session-1", "last_assistant_message": "답변 반영했습니다."}, expected_returncode=0)
            self.assertEqual(result["status"], "BLOCKED")

    def test_awaiting_user_stop_allows_next_pending_when_full_batch_shown(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            self.write_pending_definition(root)
            self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "1번"})
            store_dir = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition-store"
            working_set = json.loads((store_dir / "working-set.json").read_text(encoding="utf-8"))
            working_set["active_pending_ids"] = ["PENDING-002"]
            working_set["active_pending_questions"] = [
                {
                    "id": "PENDING-002",
                    "scope": "큰방향",
                    "question": "Which outcome should this clarify?",
                    "options": "Option 1: status readability; Option 2: traceability for reviewers",
                    "recommended_option": "Option 1",
                    "transition_option": "N/A",
                    "why_this_matters": "결과 우선순위는 아직 큰방향 질문입니다.",
                    "status": "pending",
                }
            ]
            (store_dir / "working-set.json").write_text(json.dumps(working_set, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            self.append_store_decision(root)
            last_message = (
                "Which outcome should this clarify?\n"
                "Option 1: status readability\n"
                "Option 2: traceability for reviewers"
            )
            result = self.run_hook(root, "stop", {"session_id": "session-1", "last_assistant_message": last_message}, expected_returncode=0)
            self.assertEqual(result["status"], "PREPASS")

    def test_awaiting_user_stop_blocks_sync_gate_transition_without_valid_decision(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            self.write_pending_definition(root)
            self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "1번"})
            store_dir = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition-store"
            working_set = json.loads((store_dir / "working-set.json").read_text(encoding="utf-8"))
            working_set["active_pending_ids"] = []
            working_set["active_pending_questions"] = []
            working_set["risk_level"] = "medium"
            (store_dir / "working-set.json").write_text(json.dumps(working_set, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            sync_state = json.loads((store_dir / "sync-state.json").read_text(encoding="utf-8"))
            sync_state["current_gate"] = "targeted-sync-required"
            (store_dir / "sync-state.json").write_text(json.dumps(sync_state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            stop_result = self.run_hook(root, "stop", {"session_id": "session-1", "last_assistant_message": "답변을 store에 기록했고 영향 범위 동기화가 필요합니다."}, expected_returncode=0)
            self.assertEqual(stop_result["status"], "BLOCKED")

    def test_awaiting_user_stop_allows_sync_gate_transition_and_next_turn_catches_gate(self) -> None:
        with temp_project() as root:
            self.create_project(root, "definition")
            self.write_pending_definition(root)
            self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "1번"})
            store_dir = root / ".stageflow" / "requests" / REQUEST_ID / "01-definition" / "definition-store"
            working_set = json.loads((store_dir / "working-set.json").read_text(encoding="utf-8"))
            working_set["active_pending_ids"] = []
            working_set["active_pending_questions"] = []
            working_set["risk_level"] = "medium"
            (store_dir / "working-set.json").write_text(json.dumps(working_set, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            sync_state = json.loads((store_dir / "sync-state.json").read_text(encoding="utf-8"))
            sync_state["current_gate"] = "targeted-sync-required"
            (store_dir / "sync-state.json").write_text(json.dumps(sync_state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            self.append_store_decision(root, risk_level="medium", sync_status="pending")

            stop_result = self.run_hook(root, "stop", {"session_id": "session-1", "last_assistant_message": "답변을 store에 기록했고 영향 범위 동기화가 필요합니다."}, expected_returncode=0)
            self.assertEqual(stop_result["status"], "PREPASS")

            prompt_result = self.run_hook(root, "user_prompt_submit", {"session_id": "session-1", "prompt": "workflow status"})
            self.assertEqual(prompt_result["status"], "TARGETED_SYNC_REQUIRED")
            self.assertEqual(prompt_result["turn_start_action"], "run_targeted_sync_subagent")

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
            self.write_definition_store(
                root,
                active_pending_ids=["PENDING-001", "PENDING-002", "PENDING-003", "PENDING-004", "PENDING-005"],
                current_scope="큰방향",
            )
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
            self.assertEqual(
                result["_wire_output"]["reason"],
                "Stageflow cannot advance yet because the current workflow gate is not complete.",
            )
            self.assertNotIn("must not claim completion", result["_wire_output"]["reason"])
            self.assertNotIn("Stageflow preflight", result["_wire_output"]["reason"])
            self.assertNotIn(".stageflow/hook-state", result["_wire_output"]["reason"])
            self.assertNotIn("pending clarification", result["_wire_output"]["reason"].lower())


if __name__ == "__main__":
    unittest.main()
