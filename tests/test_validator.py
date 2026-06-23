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


class ValidatorFourStageTests(unittest.TestCase):
    def run_validator(
        self,
        root: Path,
        phase: str,
        reference_root: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
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
        (stage_dir / "review.md").write_text(
            self.review_text(phase, fingerprint, STAGE_RULE_IDS[phase]),
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

    def test_print_template_outputs_four_stage_templates(self) -> None:
        for template, expected in {
            "stage-tree": "01-requirements/goal.md",
            "requirements": "## Request Profile",
            "service-plan": "## Policy Rules",
            "implementation-plan": "## Coverage Matrix",
            "implementation": "## Plan Compliance And Deviations",
            "goal": "Tool: create_goal",
            "review": "Writing And Review Rule Checklist",
            "approval": "Stage approved: yes",
        }.items():
            with self.subTest(template=template):
                result = subprocess.run(
                    [sys.executable, str(VALIDATOR), "--print-template", template],
                    text=True,
                    capture_output=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(expected, result.stdout)

    def test_skill_points_to_stage_instruction_files(self) -> None:
        skill_text = (ROOT / "skills" / "stageflow" / "SKILL.md").read_text(encoding="utf-8-sig")
        artifact_text = (ROOT / "skills" / "stageflow" / "references" / "artifact-format.md").read_text(
            encoding="utf-8-sig"
        )
        for relative in (
            "references/stages/01-requirements/requirements-writing-and-review-rules.md",
            "references/stages/02-service-plan/service-plan-writing-and-review-rules.md",
            "references/stages/03-implementation-plan/implementation-plan-writing-and-review-rules.md",
            "references/stages/04-implementation/implementation-writing-and-review-rules.md",
        ):
            with self.subTest(relative=relative):
                self.assertIn(relative, skill_text)
                self.assertIn(relative, artifact_text)
                stage_text = (ROOT / "skills" / "stageflow" / relative).read_text(encoding="utf-8-sig")
                self.assertIn("## Stage Artifact Format", stage_text)

        for relative in (
            "references/stages/01-requirements/requirements-review-agent-prompt.md",
            "references/stages/02-service-plan/service-plan-review-agent-prompt.md",
            "references/stages/03-implementation-plan/implementation-plan-review-agent-prompt.md",
            "references/stages/04-implementation/implementation-review-agent-prompt.md",
        ):
            with self.subTest(relative=relative):
                self.assertIn(relative, skill_text)
                self.assertIn(relative, artifact_text)
                prompt_text = (ROOT / "skills" / "stageflow" / relative).read_text(encoding="utf-8-sig")
                self.assertIn("## Required Output", prompt_text)

        for stage_heading in ("## requirements.md", "## service-plan.md", "## implementation-plan.md", "## implementation.md"):
            with self.subTest(stage_heading=stage_heading):
                self.assertNotIn(stage_heading, artifact_text)

    def test_stage_role_and_profile_guidance_is_documented(self) -> None:
        rule_expectations = {
            "references/stages/01-requirements/requirements-writing-and-review-rules.md": (
                "## Stage Responsibility",
                "## Request Type Profiles",
                "## Desired Outcomes",
                "## Current Problems",
                "## Problem-To-Requirement Mapping",
                "## Open Questions",
                "## Resolved Decisions",
                "## Clarification Loop",
                "## Blocking Question Criteria",
                "## Open Question Writing Rules",
                "## Open Question Resolution Rules",
                "User-Specified Constraints",
                "Discovered Constraints",
            ),
            "references/stages/02-service-plan/service-plan-writing-and-review-rules.md": (
                "## Stage Responsibility",
                "## Request Type Profiles",
                "normal behavior model",
                "## Normal Behavior Transformation",
                "Regression Prevention",
                "Integration Flow And Data Responsibilities",
                "requirements rows are repeated",
                "problem resolution model",
                "Do not include implementation file lists",
            ),
            "references/stages/03-implementation-plan/implementation-plan-writing-and-review-rules.md": (
                "## Stage Responsibility",
                "## Request Type Profiles",
                "Cause Or Design Notes",
                "Do not create new requirements",
                "endpoint semantics",
            ),
            "references/stages/04-implementation/implementation-writing-and-review-rules.md": (
                "## Stage Responsibility",
                "## Request Type Profiles",
                "Plan Compliance And Deviations",
                "problem-resolution or regression evidence",
            ),
        }
        for relative, expected_phrases in rule_expectations.items():
            text = (ROOT / "skills" / "stageflow" / relative).read_text(encoding="utf-8-sig")
            for phrase in expected_phrases:
                with self.subTest(relative=relative, phrase=phrase):
                    self.assertIn(phrase, text)

    def test_review_prompts_block_stage_role_regressions(self) -> None:
        prompt_expectations = {
            "references/stages/01-requirements/requirements-review-agent-prompt.md": (
                "mixed requests connect problems to resolving requirements",
                "user-specified files, endpoints, commands, screens, or reference systems",
                "Decision Needed",
                "vague concern",
                "User answer to Q-###",
                "blocking open question remains",
            ),
            "references/stages/02-service-plan/service-plan-review-agent-prompt.md": (
                "repeating the requirements list",
                "requirements rows are copied",
                "problem resolution model or regression model",
                "Regression Prevention",
                "does not introduce new requirements",
            ),
            "references/stages/03-implementation-plan/implementation-plan-review-agent-prompt.md": (
                "does not introduce new requirements",
                "UX policy",
                "endpoint semantics",
            ),
            "references/stages/04-implementation/implementation-review-agent-prompt.md": (
                "Plan Compliance And Deviations",
                "problem-resolution evidence",
            ),
        }
        for relative, expected_phrases in prompt_expectations.items():
            text = (ROOT / "skills" / "stageflow" / relative).read_text(encoding="utf-8-sig")
            for phrase in expected_phrases:
                with self.subTest(relative=relative, phrase=phrase):
                    self.assertIn(phrase, text)
    def test_validator_docs_use_plugin_script_and_target_root(self) -> None:
        skill_text = (ROOT / "skills" / "stageflow" / "SKILL.md").read_text(encoding="utf-8-sig")
        artifact_text = (ROOT / "skills" / "stageflow" / "references" / "artifact-format.md").read_text(
            encoding="utf-8-sig"
        )
        hooks_text = (ROOT / "skills" / "stageflow" / "references" / "hooks.md").read_text(encoding="utf-8-sig")

        for name, text in {
            "SKILL.md": skill_text,
            "artifact-format.md": artifact_text,
        }.items():
            with self.subTest(document=name):
                self.assertIn("<plugin-root>/scripts/validate_stageflow.py", text)
                self.assertIn("--root <target-project-root>", text)
                self.assertNotIn("python scripts/validate_stageflow.py --current", text)

        self.assertIn("<plugin-root>/scripts/stageflow_hook_check.py", hooks_text)
        self.assertIn("--root <target-project-root>", hooks_text)
        self.assertIn("__file__", hooks_text)
        self.assertNotIn("python scripts/stageflow_hook_check.py --event", hooks_text)
        self.assertNotIn("Run the validator from the target project root:", skill_text)

    def test_valid_four_stage_request_passes_all(self) -> None:
        with temp_project() as tmp:
            root = Path(tmp)
            self.create_project(root)
            result = self.run_validator(root, "all")
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertIn("PASS all", result.stdout)

    def test_stage_rule_document_is_required(self) -> None:
        with temp_project() as tmp:
            root = Path(tmp)
            self.create_project(root)
            copied_references = root / "references"
            shutil.copytree(REFERENCE_ROOT, copied_references)
            (
                copied_references
                / "stages"
                / "01-requirements"
                / "requirements-writing-and-review-rules.md"
            ).unlink()
            result = self.run_validator(root, "requirements", copied_references)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("requirements-writing-and-review-rules.md", result.stdout)

    def test_stage_rule_document_requires_stage_artifact_format(self) -> None:
        with temp_project() as tmp:
            root = Path(tmp)
            self.create_project(root)
            copied_references = root / "references"
            shutil.copytree(REFERENCE_ROOT, copied_references)
            rule_file = (
                copied_references
                / "stages"
                / "01-requirements"
                / "requirements-writing-and-review-rules.md"
            )
            rule_file.write_text(
                rule_file.read_text(encoding="utf-8").replace("## Stage Artifact Format", "## Removed Stage Artifact Format"),
                encoding="utf-8",
            )
            result = self.run_validator(root, "requirements", copied_references)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Stage Artifact Format", result.stdout)

    def test_stage_review_agent_prompt_is_required(self) -> None:
        with temp_project() as tmp:
            root = Path(tmp)
            self.create_project(root)
            copied_references = root / "references"
            shutil.copytree(REFERENCE_ROOT, copied_references)
            (
                copied_references
                / "stages"
                / "01-requirements"
                / "requirements-review-agent-prompt.md"
            ).unlink()
            result = self.run_validator(root, "requirements", copied_references)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("requirements-review-agent-prompt.md", result.stdout)

    def test_stage_review_agent_prompt_requires_output_contract(self) -> None:
        with temp_project() as tmp:
            root = Path(tmp)
            self.create_project(root)
            copied_references = root / "references"
            shutil.copytree(REFERENCE_ROOT, copied_references)
            prompt_file = (
                copied_references
                / "stages"
                / "01-requirements"
                / "requirements-review-agent-prompt.md"
            )
            prompt_file.write_text(
                prompt_file.read_text(encoding="utf-8").replace("## Required Output", "## Removed Required Output"),
                encoding="utf-8",
            )
            result = self.run_validator(root, "requirements", copied_references)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Required Output", result.stdout)

    def test_review_checklist_requires_all_rule_ids(self) -> None:
        with temp_project() as tmp:
            root = Path(tmp)
            self.create_project(root)
            review = root / ".stageflow" / "requests" / REQUEST_ID / "01-requirements" / "review.md"
            review.write_text(
                "\n".join(
                    line for line in review.read_text(encoding="utf-8").splitlines() if "REQ-RULE-004" not in line
                ),
                encoding="utf-8",
            )
            result = self.run_validator(root, "requirements")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("REQ-RULE-004", result.stdout)

    def test_requirements_requires_verifiable_columns(self) -> None:
        with temp_project() as tmp:
            root = Path(tmp)
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-requirements" / "requirements.md"
            artifact.write_text(
                "# Requirements\n\n"
                "## User Goal\n\nGoal.\n\n"
                "## Requirements\n\n"
                "| ID | Requirement | Acceptance Evidence |\n"
                "| --- | --- | --- |\n"
                "| REQ-001 | Requirement. | Evidence. |\n\n"
                "## Acceptance Criteria\n\n- Done.\n",
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "requirements")
            result = self.run_validator(root, "requirements")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Desired Outcomes", result.stdout)

    def test_mixed_requirements_need_problem_to_requirement_mapping(self) -> None:
        with temp_project() as tmp:
            root = Path(tmp)
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-requirements" / "requirements.md"
            artifact.write_text(
                "# Requirements\n\n"
                "## User Goal\n\nFix the current issue and adjust the behavior.\n\n"
                "## Request Profile\n\nPrimary: bugfix\nSecondary: feature-adjustment\n\n"
                "## Desired Outcomes\n\n"
                "| ID | Outcome | Source | Success Signal |\n"
                "| --- | --- | --- | --- |\n"
                "| OUT-001 | Corrected behavior exists. | User request. | User can verify it. |\n\n"
                "## Current Problems\n\n"
                "| ID | Problem | Expected Behavior | Actual Behavior | Evidence Or Reproduction | Impact |\n"
                "| --- | --- | --- | --- | --- | --- |\n"
                "| PROB-001 | Current behavior is wrong. | Corrected behavior. | Wrong behavior. | Repro steps. | User blocked. |\n\n"
                "## Problem-To-Requirement Mapping\n\n"
                "No mapping recorded.\n\n"
                "## User-Specified Constraints\n\n- None specified.\n\n"
                "## Discovered Constraints\n\n- None discovered.\n\n"
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
                "## Acceptance Criteria\n\n- `REQ-001` resolves `PROB-001`.\n",
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "requirements")
            result = self.run_validator(root, "requirements")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Problem-To-Requirement Mapping", result.stdout)

    def test_requirements_rejects_legacy_open_question_columns(self) -> None:
        with temp_project() as tmp:
            root = Path(tmp)
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-requirements" / "requirements.md"
            text = artifact.read_text(encoding="utf-8")
            text = text.replace(
                "## Open Questions\n\n"
                "| ID | Decision Needed | Context Or Conflict | Recommended Option | Alternatives | Impact | Blocking | Resolution Target |\n"
                "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
                "| Q-001 | No open question. | N/A | N/A | N/A | N/A | no | N/A |\n\n"
                "## Resolved Decisions",
                "## Open Questions\n\n"
                "| ID | Question | Recommended Option | Alternatives | Impact | Blocking |\n"
                "| --- | --- | --- | --- | --- | --- |\n"
                "| Q-001 | No open question. | N/A | N/A | N/A | no |\n\n"
                "## Resolved Decisions",
            )
            artifact.write_text(text, encoding="utf-8")
            self.refresh_stage_fingerprint(root, "requirements")
            result = self.run_validator(root, "requirements")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Decision Needed", result.stdout)
            self.assertIn("Resolution Target", result.stdout)

    def test_requirements_rejects_blocking_open_question(self) -> None:
        with temp_project() as tmp:
            root = Path(tmp)
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-requirements" / "requirements.md"
            artifact.write_text(
                artifact.read_text(encoding="utf-8").replace(
                    "| Q-001 | No open question. | N/A | N/A | N/A | N/A | no | N/A |",
                    "| Q-001 | Choose the approved flow. | Screen flow is undecided. | Use the existing flow. | Add a new flow. | Changes navigation. | yes | REQ-001 |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "requirements")
            result = self.run_validator(root, "requirements")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("still blocking", result.stdout)

    def test_requirements_requires_resolved_decisions_section(self) -> None:
        with temp_project() as tmp:
            root = Path(tmp)
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-requirements" / "requirements.md"
            text = artifact.read_text(encoding="utf-8")
            before, remainder = text.split("## Resolved Decisions\n\n", 1)
            _, after = remainder.split("## Requirements\n\n", 1)
            artifact.write_text(before + "## Requirements\n\n" + after, encoding="utf-8")
            self.refresh_stage_fingerprint(root, "requirements")
            result = self.run_validator(root, "requirements")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Resolved Decisions", result.stdout)

    def test_service_plan_requires_policy_rules(self) -> None:
        with temp_project() as tmp:
            root = Path(tmp)
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "02-service-plan" / "service-plan.md"
            artifact.write_text(
                "# Service Plan\n\n"
                "## User Visible Behavior\n\nUsers see behavior.\n\n"
                "## Service Behavior\n\nService behaves.\n\n"
                "## Service API Or Data Flow\n\nNo API change.\n\n"
                "## Boundaries\n\nScoped.\n\n"
                "## Failure And Exception Behavior\n\nRecoverable.\n",
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "service-plan")
            result = self.run_validator(root, "service-plan")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Policy Rules", result.stdout)

    def test_implementation_plan_requires_coverage_matrix(self) -> None:
        with temp_project() as tmp:
            root = Path(tmp)
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "03-implementation-plan" / "implementation-plan.md"
            artifact.write_text(
                "# Implementation Plan\n\n"
                "## Change Areas\n\nCode.\n\n"
                "## Work Items\n\n"
                "| ID | Work Item | Evidence |\n"
                "| --- | --- | --- |\n"
                "| WORK-001 | Work. | Evidence. |\n\n"
                "## Validation\n\n- Tests.\n\n"
                "## Risks\n\nNone.\n\n"
                "## Constraints\n\nScoped.\n",
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "implementation-plan")
            result = self.run_validator(root, "implementation-plan")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Coverage Matrix", result.stdout)

    def test_review_checklist_fail_blocks_pass(self) -> None:
        with temp_project() as tmp:
            root = Path(tmp)
            self.create_project(root)
            review = root / ".stageflow" / "requests" / REQUEST_ID / "01-requirements" / "review.md"
            review.write_text(
                review.read_text(encoding="utf-8").replace(
                    "| REQ-RULE-001 | Evidence for REQ-RULE-001. | PASS | None |",
                    "| REQ-RULE-001 | Evidence for REQ-RULE-001. | FAIL | Missing evidence. |",
                ),
                encoding="utf-8",
            )
            result = self.run_validator(root, "requirements")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("REQ-RULE-001", result.stdout)

    def test_each_stage_requires_goal(self) -> None:
        with temp_project() as tmp:
            root = Path(tmp)
            self.create_project(root)
            (root / ".stageflow" / "requests" / REQUEST_ID / "02-service-plan" / "goal.md").unlink()
            result = self.run_validator(root, "service-plan")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("goal.md", result.stdout)

    def test_each_stage_requires_subagent_review(self) -> None:
        with temp_project() as tmp:
            root = Path(tmp)
            self.create_project(root)
            review = root / ".stageflow" / "requests" / REQUEST_ID / "01-requirements" / "review.md"
            review.write_text(review.read_text(encoding="utf-8").replace("Subagent review.", "Self-review."), encoding="utf-8")
            result = self.run_validator(root, "requirements")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Subagent review", result.stdout)

    def test_next_stage_requires_previous_stage_approval(self) -> None:
        with temp_project() as tmp:
            root = Path(tmp)
            self.create_project(root)
            approval = root / ".stageflow" / "requests" / REQUEST_ID / "01-requirements" / "approval.md"
            approval.write_text(approval.read_text(encoding="utf-8").replace("Stage approved: yes", "Stage approved: no"), encoding="utf-8")
            result = self.run_validator(root, "service-plan")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Stage approved: yes", result.stdout)

    def test_implementation_plan_requires_service_plan_artifact(self) -> None:
        with temp_project() as tmp:
            root = Path(tmp)
            self.create_project(root)
            (root / ".stageflow" / "requests" / REQUEST_ID / "02-service-plan" / "service-plan.md").unlink()
            result = self.run_validator(root, "implementation-plan")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("service-plan.md", result.stdout)

    def test_implementation_requires_implementation_plan_approval(self) -> None:
        with temp_project() as tmp:
            root = Path(tmp)
            self.create_project(root, state_phase="implementation")
            approval = root / ".stageflow" / "requests" / REQUEST_ID / "03-implementation-plan" / "approval.md"
            approval.write_text(approval.read_text(encoding="utf-8").replace("Approved.", "Not approved."), encoding="utf-8")
            result = self.run_validator(root, "implementation")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Approval Text", result.stdout)

    def test_all_requires_completed_state(self) -> None:
        with temp_project() as tmp:
            root = Path(tmp)
            self.create_project(root, state_phase="implementation")
            result = self.run_validator(root, "all")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("phase must be `completed`", result.stdout)

    def test_requirements_requires_clarification_history(self) -> None:
        with temp_project() as tmp:
            root = Path(tmp)
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-requirements" / "requirements.md"
            text = artifact.read_text(encoding="utf-8")
            before, remainder = text.split("## Clarification History\n\n", 1)
            _, after = remainder.split("## Open Questions\n\n", 1)
            artifact.write_text(before + "## Open Questions\n\n" + after, encoding="utf-8")
            self.refresh_stage_fingerprint(root, "requirements")
            result = self.run_validator(root, "requirements")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Clarification History", result.stdout)

    def test_requirements_requires_service_plan_transition_choice(self) -> None:
        with temp_project() as tmp:
            root = Path(tmp)
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "01-requirements" / "requirements.md"
            artifact.write_text(
                artifact.read_text(encoding="utf-8").replace(
                    "| CLAR-001 | Which correction boundary should requirements capture? Options: fix only reported behavior, include adjacent regression guard, 서비스 계획으로 넘어가기. | User selected `서비스 계획으로 넘어가기`. | yes | 서비스 계획으로 넘어가기 | N/A |",
                    "| CLAR-001 | Which correction boundary should requirements capture? Options: fix only reported behavior, include adjacent regression guard. | User selected first proposal. | no | Continue asking. | REQ-001 |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "requirements")
            result = self.run_validator(root, "requirements")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("service-plan transition", result.stdout)

    def test_implementation_plan_requires_technical_sections(self) -> None:
        with temp_project() as tmp:
            root = Path(tmp)
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "03-implementation-plan" / "implementation-plan.md"
            artifact.write_text(
                "# Implementation Plan\n\n"
                "## Change Areas\n\nCode.\n\n"
                "## Cause Or Design Notes\n\nGrounded in SP-001.\n\n"
                "## Work Items\n\n"
                "| ID | Implementation Unit | Technical Design | Completion Evidence |\n"
                "| --- | --- | --- | --- |\n"
                "| WORK-001 | Validator. | Add checks. | Tests. |\n\n"
                "## Coverage Matrix\n\n"
                "| Service Rule ID | Work Item ID | Change Area | Validation Evidence | Risk/Constraint |\n"
                "| --- | --- | --- | --- | --- |\n"
                "| SP-001 | WORK-001 | Validator. | Tests. | Scoped. |\n\n"
                "## Risks\n\nNone.\n\n"
                "## Constraints\n\nScoped.\n",
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "implementation-plan")
            result = self.run_validator(root, "implementation-plan")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Technical Approach", result.stdout)

    def test_implementation_plan_rejects_shallow_work_item_text(self) -> None:
        with temp_project() as tmp:
            root = Path(tmp)
            self.create_project(root)
            artifact = root / ".stageflow" / "requests" / REQUEST_ID / "03-implementation-plan" / "implementation-plan.md"
            artifact.write_text(
                artifact.read_text(encoding="utf-8").replace(
                    "| WORK-001 | Implementation-plan validator contract. | Add required technical sections and work-item columns to the stage metadata, then reject generic implementation text. | Validator failure tests and full unittest output. |",
                    "| WORK-001 | Code and tests. | Implement behavior. | Run tests. |",
                ),
                encoding="utf-8",
            )
            self.refresh_stage_fingerprint(root, "implementation-plan")
            result = self.run_validator(root, "implementation-plan")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("too generic", result.stdout)

if __name__ == "__main__":
    unittest.main()
