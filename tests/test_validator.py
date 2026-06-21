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
            "requirements": "Observable Behavior",
            "service-plan": "## Policy Rules",
            "implementation-plan": "## Coverage Matrix",
            "implementation": "## Completion Summary",
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
            self.assertIn("Observable Behavior", result.stdout)

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


if __name__ == "__main__":
    unittest.main()