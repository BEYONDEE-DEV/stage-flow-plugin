from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_simple_workflow.py"
REQUEST_ID = "20260609-1120-test-request"
SESSION_ID = "test-session"
TEST_TMP = ROOT / "tests" / ".tmp"


class TempProject:
    def __enter__(self) -> str:
        TEST_TMP.mkdir(parents=True, exist_ok=True)
        self.path = TEST_TMP / f"case-{uuid.uuid4().hex}"
        self.path.mkdir()
        return str(self.path)

    def __exit__(self, exc_type, exc, tb) -> None:
        shutil.rmtree(self.path, ignore_errors=True)


def temp_project() -> TempProject:
    return TempProject()


class ValidatorTests(unittest.TestCase):
    def run_validator(self, root: Path, *args: str, expect_success: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, str(VALIDATOR), "--root", str(root), *args],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if expect_success and result.returncode != 0:
            self.fail(result.stdout)
        if not expect_success and result.returncode == 0:
            self.fail("validator unexpectedly passed")
        return result

    def test_print_template_outputs_plan_centered_templates(self) -> None:
        expected = {
            "index": "\"version\": \"1\"",
            "current": "\"request_id\"",
            "state": "\"phase\": \"plan\"",
            "plan": "사용자 동선",
            "review": "사용자에게 알려야 할 관련 흐름 문제 없음",
        }
        for name, fragment in expected.items():
            result = subprocess.run(
                [sys.executable, str(VALIDATOR), "--print-template", name],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertIn(fragment, result.stdout)
        for removed in ("requirements", "goal", "approval"):
            result = subprocess.run(
                [sys.executable, str(VALIDATOR), "--print-template", removed],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            self.assertNotEqual(result.returncode, 0)

    def test_v2_plan_requires_observable_outcome(self) -> None:
        for outcome in (
            "잘 완료한다.",
            "결과는 추후 확인한다.",
            "결과를 확인한다.",
            "사용자가 상태를 확인한다.",
            "테스트가 통과한다.",
            "`TODO` 사용자가 명령 출력에서 승인 상태와 plan fingerprint 일치를 확인할 수 있다.",
            "`추후` 사용자가 명령 출력에서 승인 상태와 plan fingerprint 일치를 확인할 수 있다.",
        ):
            with self.subTest(outcome=outcome), temp_project() as td:
                root = make_v2_project(Path(td), phase="plan", plan_body=v2_plan_text(outcome=outcome))
                result = self.run_validator(
                    root,
                    "--current",
                    "--session-id",
                    SESSION_ID,
                    "--phase",
                    "plan",
                    expect_success=False,
                )
                self.assertIn("concrete observable outcome", result.stdout)

    def test_v2_plan_requires_completion_evidence_column_and_cells(self) -> None:
        cases = (
            (plan_text(), "Completion Evidence"),
            (
                v2_plan_text().replace(
                    "| Requirement | Plan | Completion Evidence |",
                    "| Requirement | Notes | Completion Evidence |",
                ),
                "header must be exactly",
            ),
            (v2_plan_text(evidence="-"), "concrete completion evidence"),
            (v2_plan_text(evidence="추후 확인한다."), "concrete completion evidence"),
            (v2_plan_text(evidence="테스트"), "concrete completion evidence"),
            (v2_plan_text(evidence="상태 확인"), "concrete completion evidence"),
            (v2_plan_text(evidence="관련 명령"), "concrete completion evidence"),
            (
                v2_plan_text(evidence="`xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` 테스트 상태 확인"),
                "concrete completion evidence",
            ),
            (
                v2_plan_text(evidence="`TODO` 관련 validator 테스트가 승인 상태 결과를 확인한다."),
                "concrete completion evidence",
            ),
            (
                v2_plan_text(evidence="`TBD` 관련 validator 테스트가 승인 상태 결과를 확인한다."),
                "concrete completion evidence",
            ),
            (
                v2_plan_text(evidence="`추후` 관련 validator 테스트가 승인 상태 결과를 확인한다."),
                "concrete completion evidence",
            ),
        )
        for body, expected in cases:
            with self.subTest(expected=expected), temp_project() as td:
                root = make_v2_project(Path(td), phase="plan", plan_body=body)
                result = self.run_validator(
                    root,
                    "--current",
                    "--session-id",
                    SESSION_ID,
                    "--phase",
                    "plan",
                    expect_success=False,
                )
                self.assertIn(expected, result.stdout)

    def test_v2_plan_with_concrete_evidence_passes(self) -> None:
        with temp_project() as td:
            root = make_v2_project(Path(td), phase="plan")
            self.run_validator(root, "--current", "--session-id", SESSION_ID, "--phase", "plan")
        with temp_project() as td:
            root = make_v2_project(
                Path(td),
                phase="plan",
                plan_body=v2_plan_text(outcome="확인 가능한 결과여야 하며 사용자는 최종 상태와 명령 출력을 관찰한다."),
            )
            self.run_validator(root, "--current", "--session-id", SESSION_ID, "--phase", "plan")

    def test_v2_state_requires_goal_and_plan_approval_status(self) -> None:
        with temp_project() as td:
            root = make_v2_project(Path(td), phase="plan")
            state = root / ".simple" / "requests" / REQUEST_ID / "state.json"
            write_json(state, {"request_id": REQUEST_ID, "workflow_version": 2, "phase": "plan"})
            result = self.run_validator(
                root,
                "--current",
                "--session-id",
                SESSION_ID,
                "--phase",
                "plan",
                expect_success=False,
            )
            self.assertIn("require `goal_status`", result.stdout)
            self.assertIn("plan_approval_status", result.stdout)

    def test_v2_pending_goal_cannot_claim_approved_plan(self) -> None:
        with temp_project() as td:
            root = make_v2_project(
                Path(td),
                phase="review",
                goal_status="pending",
                approval_status="approved",
            )
            result = self.run_validator(
                root,
                "--current",
                "--session-id",
                SESSION_ID,
                "--phase",
                "review",
                expect_success=False,
            )
            self.assertIn("pending goal_status requires", result.stdout)

    def test_unknown_workflow_version_is_rejected_but_missing_is_legacy(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td), phase="plan")
            self.run_validator(root, "--current", "--session-id", SESSION_ID, "--phase", "plan")
        for version in (1, 3, "2", True):
            with self.subTest(version=version), temp_project() as td:
                root = make_project(Path(td), phase="plan")
                state = root / ".simple" / "requests" / REQUEST_ID / "state.json"
                write_json(state, {"request_id": REQUEST_ID, "workflow_version": version, "phase": "plan"})
                result = self.run_validator(
                    root,
                    "--current",
                    "--session-id",
                    SESSION_ID,
                    "--phase",
                    "plan",
                    expect_success=False,
                )
                self.assertIn("workflow_version", result.stdout)

    def test_missing_plan_fails(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td), write_plan=False)
            result = self.run_validator(root, "--current", "--session-id", SESSION_ID, "--phase", "plan", expect_success=False)
            self.assertIn("plan.md", result.stdout)

    def test_plan_requires_existing_sections(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td), plan_body="# Plan\n\n## Summary\n\nToo small.\n")
            result = self.run_validator(root, "--current", "--session-id", SESSION_ID, "--phase", "plan", expect_success=False)
            self.assertIn("Requirements Coverage", result.stdout)

    def test_plan_requires_requirement_ids(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td), plan_body=plan_text(req="TASK-1"))
            result = self.run_validator(root, "--current", "--session-id", SESSION_ID, "--phase", "plan", expect_success=False)
            self.assertIn("REQ-###", result.stdout)

    def test_plan_requires_requirement_coverage_row(self) -> None:
        with temp_project() as td:
            body = plan_text(req="REQ-001") + "\nExtra mention: `REQ-002`.\n"
            root = make_project(Path(td), plan_body=body)
            result = self.run_validator(root, "--current", "--session-id", SESSION_ID, "--phase", "plan", expect_success=False)
            self.assertIn("REQ-002", result.stdout)

    def test_plan_requires_concrete_requirement_plan(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td), plan_body=plan_text(plan_cell="TODO"))
            result = self.run_validator(root, "--current", "--session-id", SESSION_ID, "--phase", "plan", expect_success=False)
            self.assertIn("concrete plan", result.stdout)

    def test_plan_rejects_placeholder_variants(self) -> None:
        for placeholder in (
            "TODO 나중에",
            "TBD 추후",
            "미정",
            "추후 결정",
            "구현 세부는 추후 결정한다",
            "구현 전에 TODO 나중에 정한다",
            "구현 세부는 TBD로 둔다",
            "`TODO`",
            "구현은 `TBD`",
            "구현은 `TBD`로 처리한다",
            "결정은 `미정`",
            "결정은 `미정`으로 작성한다",
            "`TODO 나중에`",
            "구현은 PLACEHOLDER로 둔다",
            "구현은 placeholder로 처리한다",
            "구현은 placeholder로 고정한다",
            "구현은 placeholder로 두고 검증한다",
            "구현은 placeholder를 넣고 검증한다",
            "구현은 placeholder 상태로 유지하고 회귀 테스트로 고정한다",
        ):
            with self.subTest(placeholder=placeholder), temp_project() as td:
                root = make_project(Path(td), phase="plan", plan_body=plan_text(plan_cell=placeholder))
                result = self.run_validator(
                    root,
                    "--current",
                    "--session-id",
                    SESSION_ID,
                    "--phase",
                    "plan",
                    expect_success=False,
                )
                self.assertIn("concrete plan", result.stdout)

    def test_backticked_placeholder_identifier_is_allowed_as_concrete_code_target(self) -> None:
        plans = (
            "`TODO` marker를 제거하고 실제 검증 명령을 연결한다.",
            "`TODO`, `TBD`, `미정` 등 placeholder 변형을 차단하고 회귀 테스트로 검증한다.",
            "`TODO`, `TBD`, `N/A`, `미정` 토큰을 차단하고 검증한다.",
            "placeholder 변형을 차단하고 검증한다.",
            "재현된 placeholder 계획을 자동 테스트로 고정한다.",
            "placeholder 계획과 빈 index 회귀를 자동 테스트로 고정한다.",
        )
        for plan in plans:
            with self.subTest(plan=plan), temp_project() as td:
                root = make_project(
                    Path(td),
                    phase="plan",
                    plan_body=plan_text(plan_cell=plan),
                )
                self.run_validator(
                    root,
                    "--current",
                    "--session-id",
                    SESSION_ID,
                    "--phase",
                    "plan",
                )

    def test_plan_requires_flow_check(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td), plan_body=plan_text(include_flow_check=False))
            result = self.run_validator(root, "--current", "--session-id", SESSION_ID, "--phase", "plan", expect_success=False)
            self.assertIn("Flow Check", result.stdout)

    def test_plan_requires_korean_body_text(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td), plan_body=english_plan_text())
            result = self.run_validator(root, "--current", "--session-id", SESSION_ID, "--phase", "plan", expect_success=False)
            self.assertIn("Korean body text", result.stdout)

    def test_review_missing_fails_for_review_phase(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td), write_review=False)
            result = self.run_validator(root, "--current", "--session-id", SESSION_ID, "--phase", "review", expect_success=False)
            self.assertIn("review.md", result.stdout)

    def test_review_rejects_stale_fingerprint(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td), review_stale=True)
            result = self.run_validator(root, "--current", "--session-id", SESSION_ID, "--phase", "review", expect_success=False)
            self.assertIn("fingerprint is stale", result.stdout)

    def test_review_verdict_must_be_exact_pass(self) -> None:
        for verdict in ("FAIL: do not PASS", "pass", "Pass", "PASSIVE"):
            with self.subTest(verdict=verdict), temp_project() as td:
                root = make_project(Path(td))
                request_dir = root / ".simple" / "requests" / REQUEST_ID
                review = request_dir / "review.md"
                review.write_text(
                    review.read_text(encoding="utf-8").replace("\nPASS\n", f"\n{verdict}\n"),
                    encoding="utf-8",
                )
                result = self.run_validator(
                    root,
                    "--current",
                    "--session-id",
                    SESSION_ID,
                    "--phase",
                    "review",
                    expect_success=False,
                )
                self.assertIn("verdict must be `PASS`", result.stdout)

    def test_review_status_vocabulary_is_field_specific(self) -> None:
        replacements = (
            ("차단 없음", "No flow issues", "Blocking Issues"),
            ("사용자에게 알려야 할 관련 흐름 문제 없음", "No blocking issues", "Flow Check"),
        )
        for old, new, expected in replacements:
            with self.subTest(field=expected), temp_project() as td:
                root = make_project(Path(td))
                request_dir = root / ".simple" / "requests" / REQUEST_ID
                review = request_dir / "review.md"
                review.write_text(review.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")
                result = self.run_validator(
                    root,
                    "--current",
                    "--session-id",
                    SESSION_ID,
                    "--phase",
                    "review",
                    expect_success=False,
                )
                self.assertIn(expected, result.stdout)

    def test_review_blocking_issues_block_goal_execution(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td), review_blocking=True)
            result = self.run_validator(root, "--current", "--session-id", SESSION_ID, "--phase", "review", expect_success=False)
            self.assertIn("Blocking Issues", result.stdout)

    def test_review_flow_issues_block_goal_execution(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td), review_flow_issue=True)
            result = self.run_validator(root, "--current", "--session-id", SESSION_ID, "--phase", "review", expect_success=False)
            self.assertIn("Flow Check", result.stdout)

    def test_review_requires_question_depth_check(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td), review_missing_question_depth=True)
            result = self.run_validator(root, "--current", "--session-id", SESSION_ID, "--phase", "review", expect_success=False)
            self.assertIn("Question Depth Check", result.stdout)

    def test_review_question_depth_issue_blocks_goal_execution(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td), review_question_depth_issue=True)
            result = self.run_validator(root, "--current", "--session-id", SESSION_ID, "--phase", "review", expect_success=False)
            self.assertIn("Question Depth Check", result.stdout)

    def test_review_requires_korean_notes(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td), review_body=review_text("0" * 64, notes="Reviewed."))
            request_dir = root / ".simple" / "requests" / REQUEST_ID
            fp = sha256(request_dir / "plan.md")
            (request_dir / "review.md").write_text(review_text(fp, notes="Reviewed."), encoding="utf-8")
            result = self.run_validator(root, "--current", "--session-id", SESSION_ID, "--phase", "review", expect_success=False)
            self.assertIn("Korean body text", result.stdout)

    def test_all_passes_with_plan_and_internal_review_only(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td), phase="completed")
            self.assertFalse((root / ".simple" / "requests" / REQUEST_ID / "requirements.md").exists())
            self.assertFalse((root / ".simple" / "requests" / REQUEST_ID / "goal.md").exists())
            self.run_validator(root, "--current", "--session-id", SESSION_ID, "--phase", "all")

    def test_empty_index_fails(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td))
            write_json(root / ".simple" / "index.json", {})
            result = self.run_validator(
                root,
                "--current",
                "--session-id",
                SESSION_ID,
                "--phase",
                "review",
                expect_success=False,
            )
            self.assertIn("requests` list", result.stdout)
            self.assertIn("registered exactly once", result.stdout)

    def test_metadata_phases_must_match(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td))
            write_json(
                root / ".simple" / "sessions" / SESSION_ID / "current.json",
                {"request_id": REQUEST_ID, "phase": "plan", "activated_by": "test"},
            )
            result = self.run_validator(
                root,
                "--current",
                "--session-id",
                SESSION_ID,
                "--phase",
                "review",
                expect_success=False,
            )
            self.assertIn("phases must match", result.stdout)

    def test_phase_and_legacy_status_aliases_must_not_conflict(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td))
            write_json(
                root / ".simple" / "index.json",
                {
                    "version": "1",
                    "requests": [
                        {"id": REQUEST_ID, "phase": "review", "status": "plan", "title": "Test"}
                    ],
                },
            )
            result = self.run_validator(
                root,
                "--current",
                "--session-id",
                SESSION_ID,
                "--phase",
                "review",
                expect_success=False,
            )
            self.assertIn("phase and legacy status values must match", result.stdout)

    def test_legacy_request_id_aliases_are_accepted_consistently(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td))
            write_json(
                root / ".simple" / "index.json",
                {"version": "1", "requests": [{"request_id": REQUEST_ID, "status": "review"}]},
            )
            write_json(
                root / ".simple" / "sessions" / SESSION_ID / "current.json",
                {"id": REQUEST_ID, "status": "review"},
            )
            write_json(
                root / ".simple" / "requests" / REQUEST_ID / "state.json",
                {"id": REQUEST_ID, "status": "review"},
            )
            self.run_validator(
                root,
                "--current",
                "--session-id",
                SESSION_ID,
                "--phase",
                "review",
            )

    def test_request_id_format_is_enforced_before_path_resolution(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td))
            bad_id = "../outside"
            write_json(
                root / ".simple" / "sessions" / SESSION_ID / "current.json",
                {"request_id": bad_id, "phase": "review"},
            )
            write_json(
                root / ".simple" / "index.json",
                {"version": "1", "requests": [{"id": bad_id, "status": "review"}]},
            )
            result = self.run_validator(
                root,
                "--current",
                "--session-id",
                SESSION_ID,
                "--phase",
                "review",
                expect_success=False,
            )
            self.assertIn("YYYYMMDD-HHMM-short-slug", result.stdout)

    def test_validation_phase_must_match_state_phase(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td), phase="plan")
            result = self.run_validator(
                root,
                "--current",
                "--session-id",
                SESSION_ID,
                "--phase",
                "review",
                expect_success=False,
            )
            self.assertIn("requires `state.json` phase `review`", result.stdout)

    def test_goal_status_must_be_compatible_with_phase(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td), phase="plan")
            write_json(
                root / ".simple" / "requests" / REQUEST_ID / "state.json",
                {
                    "request_id": REQUEST_ID,
                    "phase": "plan",
                    "goal_status": "active",
                    "goal_plan_fingerprint": "sha256:" + "0" * 64,
                },
            )
            result = self.run_validator(
                root,
                "--current",
                "--session-id",
                SESSION_ID,
                "--phase",
                "plan",
                expect_success=False,
            )
            self.assertIn("incompatible with goal_status", result.stdout)

    def test_active_goal_fingerprint_must_match_plan(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td))
            write_json(
                root / ".simple" / "requests" / REQUEST_ID / "state.json",
                {
                    "request_id": REQUEST_ID,
                    "phase": "review",
                    "goal_status": "active",
                    "goal_plan_fingerprint": "sha256:" + "0" * 64,
                },
            )
            result = self.run_validator(
                root,
                "--current",
                "--session-id",
                SESSION_ID,
                "--phase",
                "review",
                expect_success=False,
            )
            self.assertIn("goal_plan_fingerprint must match", result.stdout)

    def test_v2_initial_review_bootstraps_without_goal_fingerprints(self) -> None:
        with temp_project() as td:
            root = make_v2_project(
                Path(td),
                phase="review",
                goal_status="pending",
                approval_status="pending",
            )
            self.run_validator(root, "--current", "--session-id", SESSION_ID, "--phase", "review")

    def test_v2_pending_replan_allows_origin_and_approved_fingerprint_to_differ(self) -> None:
        with temp_project() as td:
            root = make_v2_project(
                Path(td),
                phase="review",
                goal_status="active",
                approval_status="pending",
                goal_fingerprint="sha256:" + "1" * 64,
                approved_fingerprint="sha256:" + "2" * 64,
            )
            self.run_validator(root, "--current", "--session-id", SESSION_ID, "--phase", "review")

    def test_v2_approved_replan_keeps_original_goal_fingerprint(self) -> None:
        with temp_project() as td:
            root = make_v2_project(
                Path(td),
                phase="review",
                goal_status="active",
                approval_status="approved",
                goal_fingerprint="sha256:" + "1" * 64,
            )
            self.run_validator(root, "--current", "--session-id", SESSION_ID, "--phase", "review")

    def test_v2_active_goal_requires_latest_approval_fingerprint(self) -> None:
        with temp_project() as td:
            root = make_v2_project(Path(td), phase="review", goal_status="active", approval_status="approved")
            request_dir = root / ".simple" / "requests" / REQUEST_ID
            write_json(
                request_dir / "state.json",
                {
                    "request_id": REQUEST_ID,
                    "workflow_version": 2,
                    "phase": "review",
                    "plan_approval_status": "approved",
                    "goal_status": "active",
                    "goal_plan_fingerprint": "sha256:" + sha256(request_dir / "plan.md"),
                },
            )
            result = self.run_validator(
                root,
                "--current",
                "--session-id",
                SESSION_ID,
                "--phase",
                "review",
                expect_success=False,
            )
            self.assertIn("approved_plan_fingerprint", result.stdout)

    def test_v2_approved_plan_fingerprint_must_match_current_plan(self) -> None:
        with temp_project() as td:
            root = make_v2_project(
                Path(td),
                phase="review",
                goal_status="active",
                approval_status="approved",
                goal_fingerprint="sha256:" + "1" * 64,
                approved_fingerprint="sha256:" + "2" * 64,
            )
            result = self.run_validator(
                root,
                "--current",
                "--session-id",
                SESSION_ID,
                "--phase",
                "review",
                expect_success=False,
            )
            self.assertIn("approved_plan_fingerprint must match", result.stdout)

    def test_v2_completion_pre_gate_runs_before_completed_phase(self) -> None:
        with temp_project() as td:
            root = make_v2_project(Path(td), phase="review", goal_status="active", approval_status="approved")
            self.run_validator(root, "--current", "--session-id", SESSION_ID, "--phase", "completion")
        with temp_project() as td:
            root = make_v2_project(Path(td), phase="review", goal_status="active", approval_status="pending")
            result = self.run_validator(
                root,
                "--current",
                "--session-id",
                SESSION_ID,
                "--phase",
                "completion",
                expect_success=False,
            )
            self.assertIn("plan_approval_status: approved", result.stdout)

    def test_v2_completed_request_passes_all(self) -> None:
        with temp_project() as td:
            root = make_v2_project(Path(td), phase="completed", goal_status="completed", approval_status="approved")
            self.run_validator(root, "--current", "--session-id", SESSION_ID, "--phase", "all")


def make_project(
    root: Path,
    *,
    write_plan: bool = True,
    write_review: bool = True,
    plan_body: str | None = None,
    review_stale: bool = False,
    review_blocking: bool = False,
    review_flow_issue: bool = False,
    review_missing_question_depth: bool = False,
    review_question_depth_issue: bool = False,
    review_body: str | None = None,
    phase: str = "review",
) -> Path:
    req_dir = root / ".simple" / "requests" / REQUEST_ID
    session_dir = root / ".simple" / "sessions" / SESSION_ID
    req_dir.mkdir(parents=True)
    session_dir.mkdir(parents=True)
    write_json(root / ".simple" / "index.json", {"version": "1", "requests": [{"id": REQUEST_ID, "title": "Test", "status": phase}]})
    write_json(session_dir / "current.json", {"request_id": REQUEST_ID, "phase": phase, "activated_by": "test"})
    write_json(req_dir / "state.json", {"request_id": REQUEST_ID, "phase": phase, "last_validated_at": None})
    if write_plan:
        (req_dir / "plan.md").write_text(plan_body if plan_body is not None else plan_text(), encoding="utf-8")
    if write_review:
        fp = sha256(req_dir / "plan.md")
        review_fp = "0" * 64 if review_stale else fp
        (req_dir / "review.md").write_text(
            review_body if review_body is not None else
            review_text(
                review_fp,
                review_blocking,
                review_flow_issue,
                missing_question_depth=review_missing_question_depth,
                question_depth_issue=review_question_depth_issue,
            ),
            encoding="utf-8",
        )
    return root


def make_v2_project(
    root: Path,
    *,
    phase: str = "review",
    plan_body: str | None = None,
    goal_status: str | None = None,
    approval_status: str | None = None,
    goal_fingerprint: str | None = None,
    approved_fingerprint: str | None = None,
) -> Path:
    root = make_project(root, phase=phase, plan_body=plan_body or v2_plan_text())
    request_dir = root / ".simple" / "requests" / REQUEST_ID
    current_fingerprint = "sha256:" + sha256(request_dir / "plan.md")
    resolved_goal_status = goal_status or {
        "plan": "pending",
        "review": "active",
        "completed": "completed",
    }[phase]
    resolved_approval_status = approval_status or (
        "pending" if resolved_goal_status == "pending" else "approved"
    )
    state: dict[str, object] = {
        "request_id": REQUEST_ID,
        "workflow_version": 2,
        "phase": phase,
        "plan_approval_status": resolved_approval_status,
        "goal_status": resolved_goal_status,
    }
    if resolved_goal_status in {"active", "completing", "completed"}:
        state["goal_plan_fingerprint"] = goal_fingerprint or current_fingerprint
        state["approved_plan_fingerprint"] = approved_fingerprint or current_fingerprint
    write_json(request_dir / "state.json", state)
    return root


def plan_text(req: str = "REQ-001", plan_cell: str | None = None, include_flow_check: bool = True) -> str:
    plan = plan_cell if plan_cell is not None else f"`{req}`에서 요구한 동작을 구현한다."
    flow_check = """## Flow Check

- 계획된 변경과 관련된 사용자 동선, 상태 전이, 데이터 흐름, 실패/재시도 경로, 검증 흐름을 확인한다.
- 이번 변경이 만든 문제가 아니더라도 관련 흐름 문제를 발견하면 사용자에게 알리고, 범위 밖이면 범위 밖이라고 명시한다.

""" if include_flow_check else ""
    return f"""# Plan

## Summary

워크플로 구현을 단순화하고 검증 가능한 계획 중심 흐름으로 정리한다.

## Requirements Coverage

| Requirement | Plan |
| --- | --- |
| {req} | {plan} |

## Change Targets

| Target | Planned Change |
| --- | --- |
| `scripts/` and `skills/simple-workflow/` | 여러 산출물 검사를 계획 중심 검사로 교체한다. |

{flow_check}## Validation

- `{req}`를 검증하기 위해 validator와 hook 테스트를 실행한다.

## Out Of Scope

- 사용자-facing requirements와 goal 산출물은 범위에서 제외한다.
"""


def v2_plan_text(
    req: str = "REQ-001",
    *,
    outcome: str = "사용자가 변경된 상태를 명령 출력으로 확인할 수 있고 관련 validator 테스트가 통과한다.",
    plan_cell: str | None = None,
    evidence: str = "관련 validator 테스트와 실제 상태 출력으로 완료 결과를 확인한다.",
) -> str:
    plan = plan_cell if plan_cell is not None else f"`{req}`에서 요구한 동작을 구현한다."
    return f"""# Plan

## Summary

워크플로 구현을 실제 목표와 검증 가능한 완료 증거 중심으로 정리한다.

## Outcome And Completion Criteria

- {outcome}

## Requirements Coverage

| Requirement | Plan | Completion Evidence |
| --- | --- | --- |
| {req} | {plan} | {evidence} |

## Change Targets

| Target | Planned Change |
| --- | --- |
| `scripts/` and `skills/simple-workflow/` | 목표 달성 중심의 검증 규칙을 적용한다. |

## Flow Check

- 사용자 목표, 상태 전이, 실패 복구, 승인, 검증 흐름을 함께 확인한다.

## Validation

- `{req}`의 실제 결과와 validator 테스트를 검증한다.

## Out Of Scope

- 다른 워크플로 정책 변경은 범위에서 제외한다.
"""


def english_plan_text() -> str:
    return """# Plan

## Summary

Simplify the workflow implementation.

## Requirements Coverage

| Requirement | Plan |
| --- | --- |
| REQ-001 | Implement the behavior described by `REQ-001`. |

## Change Targets

| Target | Planned Change |
| --- | --- |
| `scripts/` | Replace checks with plan-centered checks. |

## Flow Check

- The planned change does not break the affected user, state, data, failure, or validation flow.

## Validation

- Run validator and hook tests.

## Out Of Scope

- User-facing requirements and goal artifacts.
"""


def review_text(
    fp: str,
    blocking: bool = False,
    flow_issue: bool = False,
    *,
    missing_question_depth: bool = False,
    question_depth_issue: bool = False,
    notes: str = "검토 완료.",
) -> str:
    issues = "차단 이슈가 남아 있다" if blocking else "차단 없음"
    flow = "관련 사용자 동선의 실패 복구 흐름 문제가 사용자에게 보고되지 않았다" if flow_issue else "사용자에게 알려야 할 관련 흐름 문제 없음"
    question_depth = "해결되지 않은 대분류 질문이 남아 있다" if question_depth_issue else "상위 질문 없음"
    verdict = "FAIL" if blocking or flow_issue or question_depth_issue else "PASS"
    question_depth_section = "" if missing_question_depth else f"""
## Question Depth Check

{question_depth}
"""
    return f"""# Review

## Reviewed Plan Fingerprint

Reviewed Plan Fingerprint: sha256:{fp}

## Reviewer

subagent

## Verdict

{verdict}

## Blocking Issues

{issues}

## Flow Check

{flow}
{question_depth_section}

## Notes

{notes}
"""


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes() if path.is_file() else b"").hexdigest()
