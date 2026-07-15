from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_atomic_docs.py"


class AtomicDocsValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.docs = self.root / "docs"
        (self.root / ".stageflow").mkdir()
        (self.docs / "project").mkdir(parents=True)
        (self.docs / "project" / "atomization-criteria.md").write_text(
            "# 문서 작성 기준\n", encoding="utf-8"
        )
        (self.root / ".stageflow" / "atomic-docs.json").write_text(
            json.dumps(
                {
                    "storage_mode": "repository",
                    "docs_root": "docs",
                    "source_root": ".",
                    "baseline_metadata_path": "source-baseline.json",
                }
            ),
            encoding="utf-8",
        )
        self._git("init")
        self._git("config", "user.email", "atomic-docs@example.com")
        self._git("config", "user.name", "Atomic Docs Test")
        (self.root / "source.txt").write_text("source\n", encoding="utf-8")
        self._git("add", "source.txt")
        self._git("commit", "-m", "source baseline")
        self.commit = self._git("rev-parse", "HEAD").stdout.strip()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=self.root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def run_validator(
        self,
        phase: str,
        *expected_atom_keys: str,
        request_id: str | None = None,
        require_actions_final: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        command = [
            sys.executable,
            str(VALIDATOR),
            "--root",
            str(self.root),
            "--phase",
            phase,
        ]
        for atom_key in expected_atom_keys:
            command.extend(["--expect-atom-key", atom_key])
        if request_id is not None:
            command.extend(["--request-id", request_id])
        if require_actions_final:
            command.append("--require-actions-final")
        return subprocess.run(
            command,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def write_atom(
        self,
        rel_path: str,
        atom_key: str,
        *,
        aid_key: str | None = None,
        edges: list[dict[str, str]] | None = None,
        omit_section: str | None = None,
        with_aids: bool = True,
    ) -> Path:
        path = self.docs / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        prefix = aid_key or atom_key
        frontmatter = ["---", f"atom_key: {atom_key}"]
        if edges:
            frontmatter.append("graph_edges:")
            for edge in edges:
                frontmatter.append(f"  - type: {edge['type']}")
                frontmatter.append(f"    target_key: {edge['target_key']}")
                frontmatter.append(f"    target_path: {edge['target_path']}")
                frontmatter.append(f"    reason: {edge['reason']}")
        else:
            frontmatter.append("graph_edges: []")
        frontmatter.append("---")
        sections = [
            ("Intent", "intent", "의도"),
            ("Outcomes", "outcome", "관찰 결과"),
            ("Boundaries", "boundary", "책임 경계"),
            ("Rules", "rules", "규칙"),
            ("Current Implementation", "impl", "현재 동작"),
            ("Planned Changes", "plan", "계획"),
            ("Gaps", "gap", "차이"),
        ]
        body: list[str] = []
        for heading, code, prose in sections:
            if heading == omit_section:
                continue
            content = f"- [AID:{prefix}.{code}.001] {prose}" if with_aids else f"- {prose}"
            body.extend(["", f"## {heading}", "", content])
        path.write_text("\n".join(frontmatter + body) + "\n", encoding="utf-8")
        return path

    def write_baseline(self, coverage: str = "project-wide") -> None:
        (self.docs / "source-baseline.json").write_text(
            json.dumps(
                {
                    "version": "1",
                    "source_commit": self.commit,
                    "coverage": coverage,
                }
            ),
            encoding="utf-8",
        )

    def write_selection_state(
        self,
        candidates: list[dict[str, object]],
        *,
        bundle_keys: list[str],
        risk_triggers: list[dict[str, object]] | None = None,
        request_id: str = "20260714-120000-selection-test",
        accepted_scope: list[str] | None = None,
        bundle_domain: str = "domain",
        selection_version: str | None = "1",
        source_commit: str | None = None,
    ) -> str:
        request_root = self.root / ".stageflow" / "atomic-docs" / "requests" / request_id
        request_root.mkdir(parents=True)
        (request_root / "inventory.md").write_text("# 후보\n", encoding="utf-8")
        observed = source_commit or self.commit
        evidence = ["# 근거 색인", "", f"source_commit_observed: `{observed}`"]
        for candidate in candidates:
            candidate_id = candidate.get("candidate_id")
            if isinstance(candidate_id, str):
                evidence.extend(
                    ["", f"## {candidate_id}", "", "- `source.txt:1` 후보 판단 근거"]
                )
        (request_root / "evidence.md").write_text(
            "\n".join(evidence) + "\n", encoding="utf-8"
        )
        context_selection: dict[str, object] = {"candidates": candidates}
        if selection_version is not None:
            context_selection["version"] = selection_version
        (request_root / "work-state.json").write_text(
            json.dumps(
                {
                    "accepted_scope": ["domain"] if accepted_scope is None else accepted_scope,
                    "source_commit_observed": observed,
                    "context_selection": context_selection,
                    "bundle_queue": [
                        {"domain": bundle_domain, "expected_atom_keys": bundle_keys}
                    ],
                    "risk_triggers": risk_triggers or [],
                }
            ),
            encoding="utf-8",
        )
        return request_id

    def selection_state_path(self, request_id: str) -> Path:
        return (
            self.root
            / ".stageflow"
            / "atomic-docs"
            / "requests"
            / request_id
            / "work-state.json"
        )

    def selection_request_root(self, request_id: str) -> Path:
        return self.selection_state_path(request_id).parent

    def read_selection_state(self, request_id: str) -> dict[str, object]:
        return json.loads(self.selection_state_path(request_id).read_text(encoding="utf-8"))

    def write_selection_data(self, request_id: str, state: dict[str, object]) -> None:
        self.selection_state_path(request_id).write_text(json.dumps(state), encoding="utf-8")

    def write_state_rollback(
        self,
        request_id: str,
        relative_path: str,
        state: dict[str, object],
    ) -> tuple[Path, str]:
        path = self.selection_request_root(request_id) / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state), encoding="utf-8")
        return path, self.file_sha256(path)

    @staticmethod
    def file_sha256(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    @staticmethod
    def approved_action_fingerprint(action: dict[str, object]) -> str:
        payload = {key: value for key, value in action.items() if key != "approved_action_fingerprint"}
        owners = payload.get("reference_owners")
        if isinstance(owners, list):
            payload["reference_owners"] = sorted(owners, key=lambda owner: owner["path"])
        serialized = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(serialized).hexdigest()

    def test_bootstrap_passes_without_atoms_or_baseline(self) -> None:
        result = self.run_validator("bootstrap")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("PASS bootstrap", result.stdout)

    def test_selection_accepts_write_merge_drop_and_candidate_linked_risk(self) -> None:
        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "domain-context",
                    "domain": "domain",
                    "candidate": "도메인 맥락",
                    "disposition": "write",
                    "selection_basis": "공유 소유권을 소스 한 곳에서 찾기 어렵다.",
                    "candidate_atom_keys": ["domain-context"],
                },
                {
                    "candidate_id": "durable-contract",
                    "domain": "domain",
                    "candidate": "지속적인 계약",
                    "disposition": "write",
                    "selection_basis": "다른 도메인이 사용하는 계약이다.",
                    "candidate_atom_keys": ["durable-contract"],
                },
                {
                    "candidate_id": "supporting-context",
                    "domain": "domain",
                    "candidate": "중복된 보조 흐름",
                    "disposition": "merge",
                    "selection_basis": "독립 소유권 없이 기존 계약의 읽기 맥락만 보완한다.",
                    "merge_target_atom_key": "durable-contract",
                },
                {
                    "candidate_id": "dormant-mutation",
                    "domain": "domain",
                    "candidate": "호출되지 않는 mutation",
                    "disposition": "drop",
                    "selection_basis": "현재 consumer와 승인된 활성화 계획이 없다.",
                },
            ],
            bundle_keys=["domain-context", "durable-contract"],
            risk_triggers=[
                {
                    "candidate_id": "durable-contract",
                    "atom_key": "durable-contract",
                    "triggers": ["shared policy contract"],
                    "basis": "선택된 계약을 다른 도메인이 소비한다.",
                },
                {
                    "candidate_id": "supporting-context",
                    "atom_key": "durable-contract",
                    "triggers": ["money contract"],
                    "basis": "합쳐지는 결제 맥락이 같은 계약에 위험 검토를 요구한다.",
                }
            ],
        )

        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("PASS selection", result.stdout)

    def test_selection_tracks_current_operation_artifact_through_drop_and_zero_output(self) -> None:
        atom = self.write_atom("domain/temporary-detail-atom.md", "temporary-detail")
        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "temporary-detail",
                    "domain": "domain",
                    "candidate": "임시 상세",
                    "disposition": "write",
                    "selection_basis": "검토 전에는 독립 맥락 후보였다.",
                    "candidate_atom_keys": ["temporary-detail"],
                }
            ],
            bundle_keys=["temporary-detail"],
            request_id="20260715-100001-created-artifact",
            accepted_scope=["domain", "other"],
            selection_version="2",
        )
        state = self.read_selection_state(request_id)
        state["semantic_review_closure"] = {
            "version": "1",
            "basis_revision": 1,
            "review_passes": [
                {
                    "review_id": "domain-development-1",
                    "reviewer_role": "development",
                    "scope": "domain",
                    "basis_revision": 1,
                    "verdict": "PASS",
                    "status": "current",
                },
                {
                    "review_id": "domain-risk-1",
                    "reviewer_role": "risk",
                    "scope": "domain",
                    "basis_revision": 1,
                    "verdict": "PASS",
                    "status": "current",
                }
            ],
            "invalidations": [],
            "final_gate": {"required": False, "review_history": []},
        }
        state["operation_created_artifacts"] = [
            {
                "candidate_id": "temporary-detail",
                "atom_key": "temporary-detail",
                "path": "domain/temporary-detail-atom.md",
                "created_attempt_id": "domain-attempt-1",
                "last_operation_sha256": self.file_sha256(atom),
                "status": "present",
            }
        ]
        state["persistent_agent_ids"] = {
            "writer": "writer-1",
            "reviewer": "reviewer-1",
        }
        self.write_selection_data(request_id, state)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        closure = state["semantic_review_closure"]
        closure["basis_revision"] = 2
        closure["review_passes"][0]["status"] = "stale"
        closure["invalidations"] = [
            {
                "invalidation_id": "temporary-detail-drop-1",
                "trigger": "candidate-disposition",
                "cause": "독립 문서 후보가 소스에서 바로 확인 가능한 내용으로 재분류됐다.",
                "opened_revision": 2,
                "affected_artifacts": [
                    {
                        "location": "managed-docs",
                        "path": "domain/temporary-detail-atom.md",
                    },
                    {"location": "request", "path": "inventory.md"},
                ],
                "affected_bundles": ["domain"],
                "stale_review_ids": ["domain-development-1"],
                "required_reviews": [
                    {"reviewer_role": "development", "scope": "domain"}
                ],
                "status": "open",
            }
        ]
        self.write_selection_data(request_id, state)
        rollback = self.selection_request_root(request_id) / "rollback" / "temporary-detail.md"
        rollback.parent.mkdir(parents=True)
        rollback.write_bytes(atom.read_bytes())
        _, state_backup_hash = self.write_state_rollback(
            request_id,
            "rollback/temporary-detail-work-state.json",
            state,
        )
        state["context_selection"]["candidates"][0] = {
            "candidate_id": "temporary-detail",
            "domain": "domain",
            "candidate": "임시 상세",
            "disposition": "drop",
            "selection_basis": "소스에서 바로 확인할 수 있어 영구 문서가 불필요하다.",
        }
        state["bundle_queue"] = []
        state["operation_created_artifacts"][0].update(
            {
                "status": "removal_pending",
                "rollback_path": "rollback/temporary-detail.md",
                "state_rollback_path": "rollback/temporary-detail-work-state.json",
                "state_rollback_sha256": state_backup_hash,
            }
        )
        self.write_selection_data(request_id, state)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("is missing from operation inventory", result.stdout)

        (self.selection_request_root(request_id) / "inventory.md").write_text(
            "# 후보\n\n- `temporary-detail`: 검토 결과 영구 Atom에서 제외\n",
            encoding="utf-8",
        )
        state_backup = (
            self.selection_request_root(request_id)
            / "rollback"
            / "temporary-detail-work-state.json"
        )
        state_backup_bytes = state_backup.read_bytes()
        full_snapshot = json.loads(state_backup_bytes)
        partial_snapshot = {
            "context_selection": full_snapshot["context_selection"],
            "operation_created_artifacts": full_snapshot["operation_created_artifacts"],
        }
        state_backup.write_text(json.dumps(partial_snapshot), encoding="utf-8")
        state["operation_created_artifacts"][0]["state_rollback_sha256"] = (
            self.file_sha256(state_backup)
        )
        self.write_selection_data(request_id, state)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("is missing core field(s)", result.stdout)

        changed_owner_snapshot = json.loads(state_backup_bytes)
        changed_owner_snapshot["persistent_agent_ids"]["reviewer"] = "reviewer-2"
        state_backup.write_text(
            json.dumps(changed_owner_snapshot), encoding="utf-8"
        )
        state["operation_created_artifacts"][0]["state_rollback_sha256"] = (
            self.file_sha256(state_backup)
        )
        self.write_selection_data(request_id, state)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn(
            "changes unrelated top-level owner `persistent_agent_ids`",
            result.stdout,
        )

        extra_null_owner_snapshot = json.loads(state_backup_bytes)
        extra_null_owner_snapshot["unexpected_owner"] = None
        state_backup.write_text(
            json.dumps(extra_null_owner_snapshot), encoding="utf-8"
        )
        state["operation_created_artifacts"][0]["state_rollback_sha256"] = (
            self.file_sha256(state_backup)
        )
        self.write_selection_data(request_id, state)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn(
            "changes unrelated top-level owner `unexpected_owner`",
            result.stdout,
        )

        broken_queue_snapshot = json.loads(state_backup_bytes)
        broken_queue_snapshot["bundle_queue"] = []
        state_backup.write_text(json.dumps(broken_queue_snapshot), encoding="utf-8")
        state["operation_created_artifacts"][0]["state_rollback_sha256"] = (
            self.file_sha256(state_backup)
        )
        self.write_selection_data(request_id, state)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("is not restorable", result.stdout)
        self.assertIn("is missing from bundle queue", result.stdout)

        wrong_domain_snapshot = json.loads(state_backup_bytes)
        wrong_domain_snapshot["context_selection"]["candidates"][0]["domain"] = (
            "other"
        )
        wrong_domain_snapshot["bundle_queue"][0]["domain"] = "other"
        state_backup.write_text(json.dumps(wrong_domain_snapshot), encoding="utf-8")
        state["operation_created_artifacts"][0]["state_rollback_sha256"] = (
            self.file_sha256(state_backup)
        )
        self.write_selection_data(request_id, state)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("changes context candidate domain ownership", result.stdout)
        self.assertIn("path is outside candidate domain `other`", result.stdout)

        duplicate_artifact_snapshot = json.loads(state_backup_bytes)
        duplicate_artifact_snapshot["operation_created_artifacts"].append(
            dict(duplicate_artifact_snapshot["operation_created_artifacts"][0])
        )
        state_backup.write_text(
            json.dumps(duplicate_artifact_snapshot), encoding="utf-8"
        )
        state["operation_created_artifacts"][0]["state_rollback_sha256"] = (
            self.file_sha256(state_backup)
        )
        self.write_selection_data(request_id, state)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("repeats `operation_created_artifacts` identity", result.stdout)
        self.assertIn("repeats operation-created atom_key", result.stdout)

        invalid_present_snapshot = json.loads(state_backup_bytes)
        invalid_present_snapshot["operation_created_artifacts"][0][
            "rollback_path"
        ] = None
        state_backup.write_text(
            json.dumps(invalid_present_snapshot), encoding="utf-8"
        )
        state["operation_created_artifacts"][0]["state_rollback_sha256"] = (
            self.file_sha256(state_backup)
        )
        self.write_selection_data(request_id, state)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("present must not set `rollback_path`", result.stdout)

        wrong_attempt_snapshot = json.loads(state_backup_bytes)
        wrong_attempt_snapshot["operation_created_artifacts"][0][
            "created_attempt_id"
        ] = "older-attempt"
        state_backup.write_text(json.dumps(wrong_attempt_snapshot), encoding="utf-8")
        state["operation_created_artifacts"][0]["state_rollback_sha256"] = (
            self.file_sha256(state_backup)
        )
        self.write_selection_data(request_id, state)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("does not contain the pre-removal artifact state", result.stdout)

        state_backup.write_bytes(state_backup_bytes)
        state["operation_created_artifacts"][0][
            "state_rollback_sha256"
        ] = state_backup_hash
        self.write_selection_data(request_id, state)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        result = self.run_validator(
            "selection", request_id=request_id, require_actions_final=True
        )
        self.assertEqual(1, result.returncode)
        self.assertIn("must be `removed`", result.stdout)

        invalidation = closure["invalidations"][0]
        original_cause = invalidation["cause"]
        invalidation["cause"] = original_cause + " 추가 근거도 같은 수정에 포함한다."
        invalidation["affected_artifacts"].append(
            {"location": "request", "path": "evidence.md"}
        )
        self.write_selection_data(request_id, state)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("without advancing basis revision", result.stdout)
        invalidation["cause"] = original_cause
        invalidation["affected_artifacts"].pop()
        self.write_selection_data(request_id, state)

        atom.unlink()
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        state["operation_created_artifacts"][0]["status"] = "removed"
        closure["review_passes"][0]["status"] = "superseded"
        closure["review_passes"].append(
            {
                "review_id": "domain-development-2",
                "reviewer_role": "development",
                "scope": "domain",
                "basis_revision": 2,
                "verdict": "PASS",
                "status": "current",
            }
        )
        closure["invalidations"][0].update(
            {"status": "resolved", "resolved_revision": 2}
        )
        self.write_selection_data(request_id, state)
        result = self.run_validator(
            "selection", request_id=request_id, require_actions_final=True
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("PASS selection final", result.stdout)

        closure["review_passes"] = []
        closure["invalidations"] = []
        self.write_selection_data(request_id, state)
        result = self.run_validator(
            "selection", request_id=request_id, require_actions_final=True
        )
        self.assertEqual(1, result.returncode)
        self.assertIn("semantic history drops review PASS", result.stdout)
        self.assertIn("semantic history drops invalidation", result.stdout)

    def test_selection_rejects_retroactive_invalidation_after_created_artifact_drop(self) -> None:
        atom = self.write_atom("domain/late-drop-atom.md", "late-drop")
        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "late-drop",
                    "domain": "domain",
                    "candidate": "뒤늦게 제외된 후보",
                    "disposition": "write",
                    "selection_basis": "첫 검토에서는 독립 맥락으로 선택됐다.",
                    "candidate_atom_keys": ["late-drop"],
                }
            ],
            bundle_keys=["late-drop"],
            request_id="20260715-100002-retroactive-invalidation",
            selection_version="2",
        )
        state = self.read_selection_state(request_id)
        state["semantic_review_closure"] = {
            "version": "1",
            "basis_revision": 1,
            "review_passes": [
                {
                    "review_id": "domain-development-1",
                    "reviewer_role": "development",
                    "scope": "domain",
                    "basis_revision": 1,
                    "verdict": "PASS",
                    "status": "current",
                }
            ],
            "invalidations": [],
            "final_gate": {"required": False, "review_history": []},
        }
        state["operation_created_artifacts"] = [
            {
                "candidate_id": "late-drop",
                "atom_key": "late-drop",
                "path": "domain/late-drop-atom.md",
                "created_attempt_id": "domain-attempt-1",
                "last_operation_sha256": self.file_sha256(atom),
                "status": "present",
            }
        ]
        self.write_selection_data(request_id, state)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        rollback = self.selection_request_root(request_id) / "rollback" / "late-drop.md"
        rollback.parent.mkdir(parents=True)
        rollback.write_bytes(atom.read_bytes())
        _, state_backup_hash = self.write_state_rollback(
            request_id,
            "rollback/late-drop-work-state.json",
            state,
        )
        state["context_selection"]["candidates"][0] = {
            "candidate_id": "late-drop",
            "domain": "domain",
            "candidate": "뒤늦게 제외된 후보",
            "disposition": "drop",
            "selection_basis": "독립 소유권이 없어 영구 문서에서 제외한다.",
        }
        state["bundle_queue"] = []
        state["operation_created_artifacts"][0].update(
            {
                "status": "removed",
                "rollback_path": "rollback/late-drop.md",
                "state_rollback_path": "rollback/late-drop-work-state.json",
                "state_rollback_sha256": state_backup_hash,
            }
        )
        state["semantic_review_closure"] = {
            "version": "1",
            "basis_revision": 2,
            "review_passes": [
                {
                    "review_id": "domain-development-1",
                    "reviewer_role": "development",
                    "scope": "domain",
                    "basis_revision": 1,
                    "verdict": "PASS",
                    "status": "superseded",
                },
                {
                    "review_id": "domain-development-2",
                    "reviewer_role": "development",
                    "scope": "domain",
                    "basis_revision": 2,
                    "verdict": "PASS",
                    "status": "current",
                },
            ],
            "invalidations": [
                {
                    "invalidation_id": "late-drop-1",
                    "trigger": "candidate-disposition",
                    "cause": "제거 뒤에 무효화를 기록한 잘못된 순서를 재현한다.",
                    "opened_revision": 2,
                    "affected_artifacts": [
                        {
                            "location": "managed-docs",
                            "path": "domain/late-drop-atom.md",
                        },
                        {"location": "request", "path": "inventory.md"},
                    ],
                    "affected_bundles": ["domain"],
                    "stale_review_ids": ["domain-development-1"],
                    "required_reviews": [
                        {"reviewer_role": "development", "scope": "domain"}
                    ],
                    "status": "resolved",
                    "resolved_revision": 2,
                }
            ],
            "final_gate": {"required": False, "review_history": []},
        }
        (self.selection_request_root(request_id) / "inventory.md").write_text(
            "# 후보\n\n- `late-drop`: 영구 문서에서 제외\n",
            encoding="utf-8",
        )
        atom.unlink()
        self.write_selection_data(request_id, state)

        result = self.run_validator(
            "selection", request_id=request_id, require_actions_final=True
        )
        self.assertEqual(1, result.returncode)
        self.assertIn(
            "must open semantic invalidation and stale reviewed PASS(es) before guarded mutation",
            result.stdout,
        )
        self.assertIn(
            "must contain open invalidation `late-drop-1` before guarded mutation",
            result.stdout,
        )

    def test_selection_rejects_created_artifact_presence_and_hash_mismatches(self) -> None:
        cases = (
            ("present-missing", "present", False, "1" * 64, "expected managed path"),
            ("removed-present", "removed", True, "1" * 64, "requires managed path"),
            ("present-hash", "present", True, "0" * 64, "current hash does not match"),
        )
        for suffix, status, keep_file, digest, expected in cases:
            with self.subTest(suffix=suffix):
                atom = self.write_atom(f"domain/{suffix}-atom.md", suffix)
                request_id = self.write_selection_state(
                    [
                        {
                            "candidate_id": suffix,
                            "domain": "domain",
                            "candidate": "검증 후보",
                            "disposition": "write" if status == "present" else "drop",
                            "selection_basis": "상태 불일치를 검증한다.",
                            **({"candidate_atom_keys": [suffix]} if status == "present" else {}),
                        }
                    ],
                    bundle_keys=[suffix] if status == "present" else [],
                    request_id=f"20260715-10001-{suffix}",
                )
                if not keep_file:
                    atom.unlink()
                state = self.read_selection_state(request_id)
                state["operation_created_artifacts"] = [
                    {
                        "candidate_id": suffix,
                        "atom_key": suffix,
                        "path": f"domain/{suffix}-atom.md",
                        "created_attempt_id": "attempt-1",
                        "last_operation_sha256": digest,
                        "status": status,
                    }
                ]
                self.write_selection_data(request_id, state)
                result = self.run_validator("selection", request_id=request_id)
                self.assertEqual(1, result.returncode)
                self.assertIn(expected, result.stdout)

    def test_selection_rejects_created_artifact_outside_candidate_domain(self) -> None:
        atom = self.write_atom("outside/new-output-atom.md", "new-output")
        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "new-output",
                    "domain": "domain",
                    "candidate": "승인 범위 안 후보",
                    "disposition": "write",
                    "selection_basis": "생성 경로 범위를 검증한다.",
                    "candidate_atom_keys": ["new-output"],
                }
            ],
            bundle_keys=["new-output"],
            request_id="20260715-100019-created-outside",
        )
        state = self.read_selection_state(request_id)
        state["operation_created_artifacts"] = [
            {
                "candidate_id": "new-output",
                "atom_key": "new-output",
                "path": "outside/new-output-atom.md",
                "created_attempt_id": "attempt-1",
                "last_operation_sha256": self.file_sha256(atom),
                "status": "present",
            }
        ]
        self.write_selection_data(request_id, state)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("is outside candidate domain `domain`", result.stdout)

    def test_selection_rejects_tracked_atom_as_operation_created(self) -> None:
        atom = self.write_atom("domain/existing-atom.md", "existing")
        self._git("add", "docs/domain/existing-atom.md")
        self._git("commit", "-m", "existing managed atom")
        tracked_commit = self._git("rev-parse", "HEAD").stdout.strip()
        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "existing",
                    "domain": "domain",
                    "candidate": "기존 문서 오분류",
                    "disposition": "write",
                    "selection_basis": "생성 provenance를 검증한다.",
                    "candidate_atom_keys": ["existing"],
                }
            ],
            bundle_keys=["existing"],
            request_id="20260715-100019-tracked-created",
            source_commit=tracked_commit,
        )
        state = self.read_selection_state(request_id)
        state["operation_created_artifacts"] = [
            {
                "candidate_id": "existing",
                "atom_key": "existing",
                "path": "domain/existing-atom.md",
                "created_attempt_id": "attempt-1",
                "last_operation_sha256": self.file_sha256(atom),
                "status": "present",
            }
        ]
        self.write_selection_data(request_id, state)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("is already tracked and is not operation-created", result.stdout)
        self.assertIn("already exists in managed docs Git HEAD", result.stdout)

        self._git("rm", "docs/domain/existing-atom.md")
        self._git("commit", "-m", "remove existing managed atom")
        atom = self.write_atom("domain/existing-atom.md", "existing")
        state["operation_created_artifacts"][0]["last_operation_sha256"] = (
            self.file_sha256(atom)
        )
        self.write_selection_data(request_id, state)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("exists at the operation's fixed docs revision", result.stdout)

    def test_selection_validates_approved_existing_delete_once_and_applied_state(self) -> None:
        source = self.write_atom("domain/old-contract-atom.md", "old-contract")
        owner = self.write_atom(
            "domain/owner-context-atom.md",
            "owner-context",
            edges=[
                {
                    "type": "depends_on",
                    "target_key": "old-contract",
                    "target_path": "domain/old-contract-atom.md",
                    "reason": "기존 계약을 참조한다.",
                }
            ],
        )
        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "owner-context",
                    "domain": "domain",
                    "candidate": "소유자 맥락",
                    "disposition": "write",
                    "selection_basis": "남는 소유자 문서다.",
                    "candidate_atom_keys": ["owner-context"],
                }
            ],
            bundle_keys=["owner-context"],
            request_id="20260715-100020-approved-delete",
        )
        source_member = {
            "atom_key": "old-contract",
            "path": "domain/old-contract-atom.md",
            "preimage_sha256": self.file_sha256(source),
        }
        owner_member = {
            "atom_key": "owner-context",
            "path": "domain/owner-context-atom.md",
            "preimage_sha256": self.file_sha256(owner),
        }
        action: dict[str, object] = {
            "action_id": "remove-old-contract",
            "action": "delete",
            "source": source_member,
            "reference_owners": [owner_member],
        }
        fingerprint = self.approved_action_fingerprint(action)
        action["approved_action_fingerprint"] = fingerprint
        state = self.read_selection_state(request_id)
        state["approved_existing_actions"] = [action]
        state["action_execution"] = [
            {
                "action_id": "remove-old-contract",
                "approved_action_fingerprint": fingerprint,
                "status": "approved",
                "members": [
                    {
                        "role": "source",
                        "atom_key": "old-contract",
                        "path": "domain/old-contract-atom.md",
                        "expected_state": "present",
                        "last_operation_sha256": source_member["preimage_sha256"],
                    },
                    {
                        "role": "reference_owner",
                        "atom_key": "owner-context",
                        "path": "domain/owner-context-atom.md",
                        "expected_state": "present",
                        "last_operation_sha256": owner_member["preimage_sha256"],
                    },
                ],
            }
        ]
        self.write_selection_data(request_id, state)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        action["approved_action_fingerprint"] = "0" * 64
        self.write_selection_data(request_id, state)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("does not match its immutable manifest", result.stdout)
        action["approved_action_fingerprint"] = fingerprint

        rollback_root = (
            self.selection_request_root(request_id)
            / "rollback"
            / "remove-old-contract"
        )
        rollback_root.mkdir(parents=True)
        source_backup = rollback_root / "source.md"
        owner_backup = rollback_root / "owner.md"
        source_backup.write_bytes(source.read_bytes())
        owner_backup.write_bytes(owner.read_bytes())
        _, state_backup_hash = self.write_state_rollback(
            request_id,
            "rollback/remove-old-contract/work-state.json",
            state,
        )
        state["action_execution"][0] = {
            "action_id": "remove-old-contract",
            "approved_action_fingerprint": fingerprint,
            "status": "applying",
            "state_rollback_path": "rollback/remove-old-contract/work-state.json",
            "state_rollback_sha256": state_backup_hash,
            "members": [
                {
                    "role": "source",
                    "atom_key": "old-contract",
                    "path": "domain/old-contract-atom.md",
                    "expected_state": "present",
                    "last_operation_sha256": source_member["preimage_sha256"],
                    "rollback_path": "rollback/remove-old-contract/source.md",
                },
                {
                    "role": "reference_owner",
                    "atom_key": "owner-context",
                    "path": "domain/owner-context-atom.md",
                    "expected_state": "present",
                    "last_operation_sha256": owner_member["preimage_sha256"],
                    "rollback_path": "rollback/remove-old-contract/owner.md",
                },
            ],
        }
        self.write_selection_data(request_id, state)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        state_backup = rollback_root / "work-state.json"
        state_backup_bytes = state_backup.read_bytes()
        state_backup.write_bytes(state_backup_bytes + b"\n")
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("operation-state rollback hash does not match", result.stdout)
        state_backup.write_bytes(state_backup_bytes)
        invalid_snapshot = json.loads(state_backup_bytes)
        invalid_snapshot["action_execution"] = []
        state_backup.write_text(json.dumps(invalid_snapshot), encoding="utf-8")
        state["action_execution"][0]["state_rollback_sha256"] = self.file_sha256(
            state_backup
        )
        self.write_selection_data(request_id, state)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("does not contain the pre-mutation execution state", result.stdout)

        invalid_approved_snapshot = json.loads(state_backup_bytes)
        invalid_approved_snapshot["action_execution"][0][
            "state_rollback_path"
        ] = "rollback/remove-old-contract/work-state.json"
        state_backup.write_text(
            json.dumps(invalid_approved_snapshot), encoding="utf-8"
        )
        state["action_execution"][0]["state_rollback_sha256"] = self.file_sha256(
            state_backup
        )
        self.write_selection_data(request_id, state)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn(
            "snapshot approved execution has unsupported field `state_rollback_path`",
            result.stdout,
        )

        state_backup.write_bytes(state_backup_bytes)
        state["action_execution"][0]["state_rollback_sha256"] = state_backup_hash
        self.write_selection_data(request_id, state)
        result = self.run_validator(
            "selection", request_id=request_id, require_actions_final=True
        )
        self.assertEqual(1, result.returncode)
        self.assertIn("must be `applied`", result.stdout)

        source.unlink()
        owner = self.write_atom("domain/owner-context-atom.md", "owner-context")
        state["action_execution"][0] = {
            "action_id": "remove-old-contract",
            "approved_action_fingerprint": fingerprint,
            "status": "applying",
            "state_rollback_path": "rollback/remove-old-contract/work-state.json",
            "state_rollback_sha256": state_backup_hash,
            "members": [
                {
                    "role": "source",
                    "atom_key": "old-contract",
                    "path": "domain/old-contract-atom.md",
                    "expected_state": "absent",
                    "rollback_path": "rollback/remove-old-contract/source.md",
                },
                {
                    "role": "reference_owner",
                    "atom_key": "owner-context",
                    "path": "domain/owner-context-atom.md",
                    "expected_state": "present",
                    "last_operation_sha256": self.file_sha256(owner),
                    "rollback_path": "rollback/remove-old-contract/owner.md",
                },
            ],
        }
        self.write_selection_data(request_id, state)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        state["action_execution"][0]["status"] = "applied"
        self.write_selection_data(request_id, state)
        result = self.run_validator(
            "selection", request_id=request_id, require_actions_final=True
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_selection_validates_existing_merge_target_and_closure(self) -> None:
        source = self.write_atom("domain/legacy-rule-atom.md", "legacy-rule")
        target = self.write_atom("domain/current-rule-atom.md", "current-rule")
        owner = self.write_atom(
            "domain/rule-owner-atom.md",
            "rule-owner",
            edges=[
                {
                    "type": "depends_on",
                    "target_key": "legacy-rule",
                    "target_path": "domain/legacy-rule-atom.md",
                    "reason": "이전 규칙을 참조한다.",
                }
            ],
        )
        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "current-rule",
                    "domain": "domain",
                    "candidate": "현재 규칙",
                    "disposition": "write",
                    "selection_basis": "병합 후 계약 소유자다.",
                    "candidate_atom_keys": ["current-rule"],
                },
                {
                    "candidate_id": "rule-owner",
                    "domain": "domain",
                    "candidate": "규칙 소비자",
                    "disposition": "write",
                    "selection_basis": "병합 대상 참조를 소유한다.",
                    "candidate_atom_keys": ["rule-owner"],
                },
            ],
            bundle_keys=["current-rule", "rule-owner"],
            request_id="20260715-100030-approved-merge",
        )
        members = {
            "source": {
                "atom_key": "legacy-rule",
                "path": "domain/legacy-rule-atom.md",
                "preimage_sha256": self.file_sha256(source),
            },
            "target": {
                "atom_key": "current-rule",
                "path": "domain/current-rule-atom.md",
                "preimage_sha256": self.file_sha256(target),
            },
            "owner": {
                "atom_key": "rule-owner",
                "path": "domain/rule-owner-atom.md",
                "preimage_sha256": self.file_sha256(owner),
            },
        }
        action: dict[str, object] = {
            "action_id": "merge-legacy-rule",
            "action": "merge",
            "source": members["source"],
            "target": members["target"],
            "reference_owners": [members["owner"]],
        }
        fingerprint = self.approved_action_fingerprint(action)
        action["approved_action_fingerprint"] = fingerprint
        state = self.read_selection_state(request_id)
        state["approved_existing_actions"] = [action]
        state["action_execution"] = [
            {
                "action_id": "merge-legacy-rule",
                "approved_action_fingerprint": fingerprint,
                "status": "approved",
                "members": [
                    {
                        "role": role,
                        "atom_key": member["atom_key"],
                        "path": member["path"],
                        "expected_state": "present",
                        "last_operation_sha256": member["preimage_sha256"],
                    }
                    for role, member in (
                        ("source", members["source"]),
                        ("target", members["target"]),
                        ("reference_owner", members["owner"]),
                    )
                ],
            }
        ]
        self.write_selection_data(request_id, state)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        rollback_root = (
            self.selection_request_root(request_id)
            / "rollback"
            / "merge-legacy-rule"
        )
        rollback_root.mkdir(parents=True)
        for name, path in (("source", source), ("target", target), ("owner", owner)):
            (rollback_root / f"{name}.md").write_bytes(path.read_bytes())
        _, state_backup_hash = self.write_state_rollback(
            request_id,
            "rollback/merge-legacy-rule/work-state.json",
            state,
        )
        source.unlink()
        target.write_text(target.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        owner = self.write_atom(
            "domain/rule-owner-atom.md",
            "rule-owner",
            edges=[
                {
                    "type": "depends_on",
                    "target_key": "current-rule",
                    "target_path": "domain/current-rule-atom.md",
                    "reason": "통합된 현재 규칙을 참조한다.",
                }
            ],
        )
        state["action_execution"][0] = {
            "action_id": "merge-legacy-rule",
            "approved_action_fingerprint": fingerprint,
            "status": "applying",
            "state_rollback_path": "rollback/merge-legacy-rule/work-state.json",
            "state_rollback_sha256": state_backup_hash,
            "members": [
                {
                    "role": "source",
                    "atom_key": "legacy-rule",
                    "path": "domain/legacy-rule-atom.md",
                    "expected_state": "absent",
                    "rollback_path": "rollback/merge-legacy-rule/source.md",
                },
                {
                    "role": "target",
                    "atom_key": "current-rule",
                    "path": "domain/current-rule-atom.md",
                    "expected_state": "present",
                    "last_operation_sha256": self.file_sha256(target),
                    "rollback_path": "rollback/merge-legacy-rule/target.md",
                },
                {
                    "role": "reference_owner",
                    "atom_key": "rule-owner",
                    "path": "domain/rule-owner-atom.md",
                    "expected_state": "present",
                    "last_operation_sha256": self.file_sha256(owner),
                    "rollback_path": "rollback/merge-legacy-rule/owner.md",
                },
            ],
        }
        self.write_selection_data(request_id, state)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        state["action_execution"][0]["status"] = "applied"
        self.write_selection_data(request_id, state)
        result = self.run_validator(
            "selection", request_id=request_id, require_actions_final=True
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        target.write_text(target.read_text(encoding="utf-8") + "changed\n", encoding="utf-8")
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("current hash does not match runtime postimage", result.stdout)

    def test_selection_rejects_existing_action_outside_accepted_scope(self) -> None:
        source = self.write_atom("outside/old-atom.md", "outside-old")
        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "domain-context",
                    "domain": "domain",
                    "candidate": "승인된 도메인",
                    "disposition": "write",
                    "selection_basis": "승인 범위 경계를 검증한다.",
                    "candidate_atom_keys": ["domain-context"],
                }
            ],
            bundle_keys=["domain-context"],
            request_id="20260715-100035-outside-action",
        )
        member = {
            "atom_key": "outside-old",
            "path": "outside/old-atom.md",
            "preimage_sha256": self.file_sha256(source),
        }
        action: dict[str, object] = {
            "action_id": "remove-outside-old",
            "action": "delete",
            "source": member,
            "reference_owners": [],
        }
        fingerprint = self.approved_action_fingerprint(action)
        action["approved_action_fingerprint"] = fingerprint
        state = self.read_selection_state(request_id)
        state["approved_existing_actions"] = [action]
        state["action_execution"] = [
            {
                "action_id": "remove-outside-old",
                "approved_action_fingerprint": fingerprint,
                "status": "approved",
                "members": [
                    {
                        "role": "source",
                        "atom_key": "outside-old",
                        "path": "outside/old-atom.md",
                        "expected_state": "present",
                        "last_operation_sha256": member["preimage_sha256"],
                    }
                ],
            }
        ]
        self.write_selection_data(request_id, state)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("is outside `accepted_scope`", result.stdout)

    def test_selection_rejects_existing_source_with_created_provenance(self) -> None:
        source = self.write_atom("domain/new-output-atom.md", "new-output")
        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "new-output",
                    "domain": "domain",
                    "candidate": "현재 작업 산출물",
                    "disposition": "write",
                    "selection_basis": "소유권 계약 충돌을 검증한다.",
                    "candidate_atom_keys": ["new-output"],
                }
            ],
            bundle_keys=["new-output"],
            request_id="20260715-100036-provenance-overlap",
        )
        digest = self.file_sha256(source)
        member = {
            "atom_key": "new-output",
            "path": "domain/new-output-atom.md",
            "preimage_sha256": digest,
        }
        action: dict[str, object] = {
            "action_id": "remove-new-output-as-existing",
            "action": "delete",
            "source": member,
            "reference_owners": [],
        }
        fingerprint = self.approved_action_fingerprint(action)
        action["approved_action_fingerprint"] = fingerprint
        state = self.read_selection_state(request_id)
        state["operation_created_artifacts"] = [
            {
                "candidate_id": "new-output",
                "atom_key": "new-output",
                "path": "domain/new-output-atom.md",
                "created_attempt_id": "attempt-1",
                "last_operation_sha256": digest,
                "status": "present",
            }
        ]
        state["approved_existing_actions"] = [action]
        state["action_execution"] = [
            {
                "action_id": "remove-new-output-as-existing",
                "approved_action_fingerprint": fingerprint,
                "status": "approved",
                "members": [
                    {
                        "role": "source",
                        "atom_key": "new-output",
                        "path": "domain/new-output-atom.md",
                        "expected_state": "present",
                        "last_operation_sha256": digest,
                    }
                ],
            }
        ]
        self.write_selection_data(request_id, state)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("source path `domain/new-output-atom.md` is also operation-created", result.stdout)

    def test_selection_rejects_unapproved_graph_owner_and_unsafe_rollback_resume(self) -> None:
        source = self.write_atom("domain/remove-me-atom.md", "remove-me")
        owner = self.write_atom("domain/known-owner-atom.md", "known-owner")
        unknown = self.write_atom(
            "domain/unknown-owner-atom.md",
            "unknown-owner",
            edges=[
                {
                    "type": "depends_on",
                    "target_key": "remove-me",
                    "target_path": "domain/remove-me-atom.md",
                    "reason": "승인되지 않은 참조다.",
                }
            ],
        )
        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "known-owner",
                    "domain": "domain",
                    "candidate": "알려진 소유자",
                    "disposition": "write",
                    "selection_basis": "삭제 후에도 유지된다.",
                    "candidate_atom_keys": ["known-owner"],
                },
                {
                    "candidate_id": "unknown-owner",
                    "domain": "domain",
                    "candidate": "새 참조 소유자",
                    "disposition": "write",
                    "selection_basis": "closure 검증을 위한 문서다.",
                    "candidate_atom_keys": ["unknown-owner"],
                },
            ],
            bundle_keys=["known-owner", "unknown-owner"],
            request_id="20260715-100040-unsafe-resume",
        )
        source_member = {
            "atom_key": "remove-me",
            "path": "domain/remove-me-atom.md",
            "preimage_sha256": self.file_sha256(source),
        }
        owner_member = {
            "atom_key": "known-owner",
            "path": "domain/known-owner-atom.md",
            "preimage_sha256": self.file_sha256(owner),
        }
        action: dict[str, object] = {
            "action_id": "remove-managed-atom",
            "action": "delete",
            "source": source_member,
            "reference_owners": [owner_member],
        }
        fingerprint = self.approved_action_fingerprint(action)
        action["approved_action_fingerprint"] = fingerprint
        state = self.read_selection_state(request_id)
        state["approved_existing_actions"] = [action]
        state["action_execution"] = [
            {
                "action_id": "remove-managed-atom",
                "approved_action_fingerprint": fingerprint,
                "status": "approved",
                "members": [
                    {
                        "role": "source",
                        "atom_key": "remove-me",
                        "path": "domain/remove-me-atom.md",
                        "expected_state": "present",
                        "last_operation_sha256": source_member["preimage_sha256"],
                    },
                    {
                        "role": "reference_owner",
                        "atom_key": "known-owner",
                        "path": "domain/known-owner-atom.md",
                        "expected_state": "present",
                        "last_operation_sha256": owner_member["preimage_sha256"],
                    },
                ],
            }
        ]
        self.write_selection_data(request_id, state)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("unapproved incoming graph owner", result.stdout)

        unknown.unlink()
        request_root = self.selection_request_root(request_id)
        rollback_root = request_root / "rollback" / "remove-managed-atom"
        rollback_root.mkdir(parents=True)
        source_backup = rollback_root / "source.md"
        owner_backup = rollback_root / "owner.md"
        source_backup.write_bytes(source.read_bytes())
        owner_backup.write_bytes(owner.read_bytes())
        _, state_backup_hash = self.write_state_rollback(
            request_id,
            "rollback/remove-managed-atom/work-state.json",
            state,
        )
        source.unlink()
        state["action_execution"][0] = {
            "action_id": "remove-managed-atom",
            "approved_action_fingerprint": fingerprint,
            "status": "rolling_back",
            "state_rollback_path": "rollback/remove-managed-atom/work-state.json",
            "state_rollback_sha256": state_backup_hash,
            "members": [
                {
                    "role": "source",
                    "atom_key": "remove-me",
                    "path": "domain/remove-me-atom.md",
                    "expected_state": "absent",
                    "rollback_path": "rollback/remove-managed-atom/source.md",
                },
                {
                    "role": "reference_owner",
                    "atom_key": "known-owner",
                    "path": "domain/known-owner-atom.md",
                    "expected_state": "present",
                    "last_operation_sha256": self.file_sha256(owner),
                    "rollback_path": "rollback/remove-managed-atom/owner.md",
                },
            ],
        }
        self.write_selection_data(request_id, state)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        source_backup_bytes = source_backup.read_bytes()
        source_backup.write_bytes(source_backup_bytes + b"changed")
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("rollback hash does not match approved preimage", result.stdout)
        source_backup.write_bytes(source_backup_bytes)

        owner.write_text(owner.read_text(encoding="utf-8") + "사용자 변경\n", encoding="utf-8")
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("current hash does not match runtime postimage", result.stdout)

        owner.write_bytes(owner_backup.read_bytes())
        source.write_bytes(source_backup.read_bytes())
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("expected path to be absent", result.stdout)

        source_runtime = state["action_execution"][0]["members"][0]
        source_runtime["expected_state"] = "present"
        source_runtime["last_operation_sha256"] = source_member["preimage_sha256"]
        self.write_selection_data(request_id, state)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        execution = state["action_execution"][0]
        execution["status"] = "approved"
        del execution["state_rollback_path"]
        del execution["state_rollback_sha256"]
        for member in execution["members"]:
            del member["rollback_path"]
        self.write_selection_data(request_id, state)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_selection_rejects_blank_basis_and_unknown_merge_target(self) -> None:
        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "domain-context",
                    "domain": "domain",
                    "candidate": "도메인 맥락",
                    "disposition": "write",
                    "selection_basis": " ",
                    "candidate_atom_keys": ["domain-context"],
                },
                {
                    "candidate_id": "merge-context",
                    "domain": "domain",
                    "candidate": "합칠 후보",
                    "disposition": "merge",
                    "selection_basis": "기존 문맥에 포함한다.",
                    "merge_target_atom_key": "missing-owner",
                },
            ],
            bundle_keys=["domain-context"],
        )

        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("must include non-empty `selection_basis`", result.stdout)
        self.assertIn("merge target `missing-owner` is not a write candidate atom", result.stdout)

    def test_selection_rejects_drop_output_and_domain_level_risk_reference(self) -> None:
        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "domain-context",
                    "domain": "domain",
                    "candidate": "도메인 맥락",
                    "disposition": "write",
                    "selection_basis": "도메인 소유권을 설명한다.",
                    "candidate_atom_keys": ["domain-context"],
                },
                {
                    "candidate_id": "dropped-detail",
                    "domain": "domain",
                    "candidate": "제외할 상세",
                    "disposition": "drop",
                    "selection_basis": "소스에서 바로 확인되는 내부 동작이다.",
                    "candidate_atom_keys": ["dropped-detail"],
                },
            ],
            bundle_keys=["domain-context", "dropped-detail"],
            risk_triggers=[
                {
                    "candidate_id": "dropped-detail",
                    "atom_key": "dropped-detail",
                    "triggers": ["destructive method"],
                    "basis": "코드에 위험한 이름이 있다.",
                }
            ],
        )

        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("with disposition `drop` must not create atom keys", result.stdout)
        self.assertIn("must not reference dropped candidate `dropped-detail`", result.stdout)
        self.assertIn("bundle queue atom key `dropped-detail` has no write candidate", result.stdout)

    def test_selection_rejects_empty_scope_and_wrong_bundle_domain(self) -> None:
        empty_scope = self.write_selection_state(
            [
                {
                    "candidate_id": "domain-context",
                    "domain": "domain",
                    "candidate": "도메인 맥락",
                    "disposition": "write",
                    "selection_basis": "승인된 경계를 설명한다.",
                    "candidate_atom_keys": ["domain-context"],
                }
            ],
            bundle_keys=["domain-context"],
            accepted_scope=[],
            request_id="20260714-120001-empty-scope",
        )
        result = self.run_validator("selection", request_id=empty_scope)
        self.assertEqual(1, result.returncode)
        self.assertIn("must contain at least one approved domain path", result.stdout)
        self.assertIn("domain `domain` is outside `accepted_scope`", result.stdout)

        wrong_domain = self.write_selection_state(
            [
                {
                    "candidate_id": "domain-context",
                    "domain": "domain",
                    "candidate": "도메인 맥락",
                    "disposition": "write",
                    "selection_basis": "승인된 경계를 설명한다.",
                    "candidate_atom_keys": ["domain-context"],
                }
            ],
            bundle_keys=["domain-context"],
            bundle_domain="other-domain",
            request_id="20260714-120002-wrong-domain",
        )
        result = self.run_validator("selection", request_id=wrong_domain)
        self.assertEqual(1, result.returncode)
        self.assertIn("domain `other-domain` is outside `accepted_scope`", result.stdout)
        self.assertIn("belongs to domain `domain`, not `other-domain`", result.stdout)

    def test_selection_requires_version_revision_candidate_id_and_evidence_locator(self) -> None:
        request_id = self.write_selection_state(
            [
                {
                    "domain": "domain",
                    "candidate": "도메인 맥락",
                    "disposition": "write",
                    "selection_basis": "승인된 경계를 설명한다.",
                    "candidate_atom_keys": ["domain-context"],
                }
            ],
            bundle_keys=["domain-context"],
            selection_version=None,
            source_commit="0" * 40,
            request_id="20260714-120003-bad-evidence",
        )
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("`context_selection.version` must be `1` or `2`", result.stdout)
        self.assertIn("source commit `0000000000000000000000000000000000000000` is not reachable", result.stdout)
        self.assertIn("must include lower-kebab-case `candidate_id`", result.stdout)

        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "domain-context",
                    "domain": "domain",
                    "candidate": "도메인 맥락",
                    "disposition": "write",
                    "selection_basis": "승인된 경계를 설명한다.",
                    "candidate_atom_keys": ["domain-context"],
                }
            ],
            bundle_keys=["domain-context"],
            request_id="20260714-120004-empty-evidence",
        )
        evidence_path = (
            self.root
            / ".stageflow"
            / "atomic-docs"
            / "requests"
            / request_id
            / "evidence.md"
        )
        evidence_path.write_text(
            f"# 근거 색인\n\nsource_commit_observed: `{self.commit}`\n\n## domain-context\n",
            encoding="utf-8",
        )
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("needs a source locator and concise relevance", result.stdout)

    def test_selection_rejects_evidence_header_that_declares_another_revision(self) -> None:
        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "domain-context",
                    "domain": "domain",
                    "candidate": "도메인 맥락",
                    "disposition": "write",
                    "selection_basis": "승인된 경계를 설명한다.",
                    "candidate_atom_keys": ["domain-context"],
                }
            ],
            bundle_keys=["domain-context"],
            request_id="20260714-120005-contradictory-revision",
        )
        evidence_path = (
            self.root
            / ".stageflow"
            / "atomic-docs"
            / "requests"
            / request_id
            / "evidence.md"
        )
        evidence_path.write_text(
            "\n".join(
                [
                    "# 근거 색인",
                    "",
                    f"source_commit_observed: `{'0' * 40}`",
                    "",
                    "## domain-context",
                    "",
                    f"- `source.txt:1` 실제 상태 hash는 {self.commit}",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn(
            f"evidence source commit `{'0' * 40}` does not match work-state `{self.commit}`",
            result.stdout,
        )

    def test_selection_rejects_multiline_evidence_revision_declaration(self) -> None:
        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "domain-context",
                    "domain": "domain",
                    "candidate": "도메인 맥락",
                    "disposition": "write",
                    "selection_basis": "승인된 경계를 설명한다.",
                    "candidate_atom_keys": ["domain-context"],
                }
            ],
            bundle_keys=["domain-context"],
            request_id="20260714-120015-multiline-revision",
        )
        evidence_path = (
            self.root
            / ".stageflow"
            / "atomic-docs"
            / "requests"
            / request_id
            / "evidence.md"
        )
        evidence_path.write_text(
            "\n".join(
                [
                    "# 근거 색인",
                    "source_commit_observed:",
                    "",
                    f"`{self.commit}`",
                    "## domain-context",
                    "- `source.txt:1` 실제 표시되는 근거",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn(
            "must declare exactly one `source_commit_observed` line",
            result.stdout,
        )

    def test_selection_rejects_duplicate_json_keys_in_operation_state(self) -> None:
        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "domain-context",
                    "domain": "domain",
                    "candidate": "도메인 맥락",
                    "disposition": "write",
                    "selection_basis": "승인된 경계를 설명한다.",
                    "candidate_atom_keys": ["domain-context"],
                }
            ],
            bundle_keys=["domain-context"],
            request_id="20260714-120006-duplicate-json-key",
        )
        state_path = (
            self.root
            / ".stageflow"
            / "atomic-docs"
            / "requests"
            / request_id
            / "work-state.json"
        )
        state_text = state_path.read_text(encoding="utf-8")
        state_path.write_text(
            state_text.replace(
                '{"accepted_scope": ["domain"]',
                '{"accepted_scope": [], "accepted_scope": ["domain"]',
                1,
            ),
            encoding="utf-8",
        )

        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("duplicate JSON key 'accepted_scope'", result.stdout)

    def test_selection_rejects_fenced_evidence_shape(self) -> None:
        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "domain-context",
                    "domain": "domain",
                    "candidate": "도메인 맥락",
                    "disposition": "write",
                    "selection_basis": "승인된 경계를 설명한다.",
                    "candidate_atom_keys": ["domain-context"],
                }
            ],
            bundle_keys=["domain-context"],
            request_id="20260714-120007-fenced-evidence",
        )
        evidence_path = (
            self.root
            / ".stageflow"
            / "atomic-docs"
            / "requests"
            / request_id
            / "evidence.md"
        )
        evidence_path.write_text(
            "\n".join(
                [
                    "# 근거 색인",
                    "",
                    "```bad`info",
                    f"source_commit_observed: `{self.commit}`",
                    "",
                    "## domain-context",
                    "- `source.txt:1` 코드 예시 안의 가짜 근거",
                    "```",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("evidence index must not contain fenced code", result.stdout)

    def test_selection_ignores_evidence_shape_inside_hidden_html(self) -> None:
        wrappers = {
            "comment": (["<!--"], ["-->"]),
            "pre": (["<pre>"], ["</pre>"]),
            "multiline-pre": (["<pre", 'class="hidden">'], ["</pre>"]),
            "multiline-pre-quoted-close": (
                ["<pre", 'data="</pre>">'],
                ["</pre>"],
            ),
            "active-pre-nested-attribute": (
                ["<pre>", '<span data="</pre>">'],
                ["</span>", "</pre>"],
            ),
            "active-pre-comment": (
                ["<pre>", "<!-- </pre> -->"],
                ["</pre>"],
            ),
            "closed-root-trailing-hidden-root": (
                ["<pre></pre><div hidden>"],
                ["</div>"],
            ),
            "void-root-trailing-hidden-root": (
                ["<hr><div hidden>"],
                ["</div>"],
            ),
            "comment-trailing-hidden-root": (
                ["<!-- closed --><div hidden>"],
                ["</div>"],
            ),
            "processing-instruction-trailing-hidden-root": (
                ["<?closed?><div hidden>"],
                ["</div>"],
            ),
            "multiline-void-quoted-delimiter": (
                ["<img", 'alt=">"'],
                [">"],
            ),
            "processing-instruction": (["<?hidden"], ["?>"]),
            "processing-instruction-with-fake-close": (
                ["<div>", '<?pi data="> </div>"?>'],
                ["</div>"],
            ),
            "cdata": (["<![CDATA["], ["]]>"]),
            "self-closing-nonvoid": (["<div/>"], []),
            "slash-newline-tag": (["<div/", ">"], []),
            "slash-tab-tag": (["<img/", "\talt=x>"], []),
            "namespaced-tag": (["<svg:path>"], ["</svg:path>"]),
            "underscore-tag": (["<x_widget>"], ["</x_widget>"]),
            "generic-blank-boundary": (["<section>", ""], ["</section>"]),
            "escaped-backticks": ([r"\`<div hidden>\`"], []),
        }
        for suffix, (opening_lines, closing_lines) in wrappers.items():
            with self.subTest(suffix=suffix):
                request_id = self.write_selection_state(
                    [
                        {
                            "candidate_id": "domain-context",
                            "domain": "domain",
                            "candidate": "도메인 맥락",
                            "disposition": "write",
                            "selection_basis": "승인된 경계를 설명한다.",
                            "candidate_atom_keys": ["domain-context"],
                        }
                    ],
                    bundle_keys=["domain-context"],
                    request_id=f"20260714-120008-hidden-{suffix}",
                )
                evidence_path = (
                    self.root
                    / ".stageflow"
                    / "atomic-docs"
                    / "requests"
                    / request_id
                    / "evidence.md"
                )
                evidence_path.write_text(
                    "\n".join(
                        [
                            "# 근거 색인",
                            "",
                            *opening_lines,
                            f"source_commit_observed: `{self.commit}`",
                            "",
                            "## domain-context",
                            "- `source.txt:1` 숨겨진 HTML 안의 가짜 근거",
                            *closing_lines,
                            "",
                        ]
                    ),
                    encoding="utf-8",
                )

                result = self.run_validator("selection", request_id=request_id)
                self.assertEqual(1, result.returncode)
                self.assertIn(
                    "must not contain raw HTML-like syntax",
                    result.stdout,
                )

    def test_selection_rejects_raw_html_before_visible_evidence(self) -> None:
        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "domain-context",
                    "domain": "domain",
                    "candidate": "도메인 맥락",
                    "disposition": "write",
                    "selection_basis": "승인된 경계를 설명한다.",
                    "candidate_atom_keys": ["domain-context"],
                }
            ],
            bundle_keys=["domain-context"],
            request_id="20260714-120009-void-html",
        )
        evidence_path = (
            self.root
            / ".stageflow"
            / "atomic-docs"
            / "requests"
            / request_id
            / "evidence.md"
        )
        evidence_path.write_text(
            "\n".join(
                [
                    "# 근거 색인",
                    "",
                    "<img",
                    'alt="표시용 구분선">',
                    f"source_commit_observed: `{self.commit}`",
                    "",
                    "## domain-context",
                    "- `source.txt:1` 실제 표시되는 근거",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn(
            "must not contain raw HTML-like syntax",
            result.stdout,
        )

    def test_selection_rejects_nested_and_mixed_indented_evidence(self) -> None:
        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "domain-context",
                    "domain": "domain",
                    "candidate": "도메인 맥락",
                    "disposition": "write",
                    "selection_basis": "승인된 경계를 설명한다.",
                    "candidate_atom_keys": ["domain-context"],
                }
            ],
            bundle_keys=["domain-context"],
            request_id="20260714-120010-indented-html",
        )
        evidence_path = (
            self.root
            / ".stageflow"
            / "atomic-docs"
            / "requests"
            / request_id
            / "evidence.md"
        )
        evidence_path.write_text(
            "\n".join(
                [
                    "# 근거 색인",
                    "",
                    ">     exact payload/parser dump",
                    "-     exact nested-list dump",
                    "   \texact serializer detail",
                    f"source_commit_observed: `{self.commit}`",
                    "",
                    "## domain-context",
                    "- `source.txt:1` 실제 표시되는 근거",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("evidence index must not contain indented code", result.stdout)

    def test_selection_rejects_tab_padded_locator(self) -> None:
        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "domain-context",
                    "domain": "domain",
                    "candidate": "도메인 맥락",
                    "disposition": "write",
                    "selection_basis": "승인된 경계를 설명한다.",
                    "candidate_atom_keys": ["domain-context"],
                }
            ],
            bundle_keys=["domain-context"],
            request_id="20260714-120014-tab-locator",
        )
        evidence_path = (
            self.root
            / ".stageflow"
            / "atomic-docs"
            / "requests"
            / request_id
            / "evidence.md"
        )
        evidence_path.write_text(
            "\n".join(
                [
                    "# 근거 색인",
                    f"source_commit_observed: `{self.commit}`",
                    "## domain-context",
                    "-\t`source.txt:1` tab으로 구분한 locator",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("evidence index must not contain tab characters", result.stdout)
        self.assertIn(
            "evidence section `## domain-context` needs a source locator",
            result.stdout,
        )

    def test_selection_rejects_html_text_inside_inline_code(self) -> None:
        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "domain-context",
                    "domain": "domain",
                    "candidate": "도메인 맥락",
                    "disposition": "write",
                    "selection_basis": "승인된 경계를 설명한다.",
                    "candidate_atom_keys": ["domain-context"],
                }
            ],
            bundle_keys=["domain-context"],
            request_id="20260714-120011-inline-html",
        )
        evidence_path = (
            self.root
            / ".stageflow"
            / "atomic-docs"
            / "requests"
            / request_id
            / "evidence.md"
        )
        evidence_path.write_text(
            "\n".join(
                [
                    "# 근거 색인",
                    "",
                    "`<div hidden>`은 코드 예시일 뿐이다.",
                    f"source_commit_observed: `{self.commit}`",
                    "",
                    "## domain-context",
                    "- `source.txt:1` 실제 표시되는 근거",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("must not contain raw HTML-like syntax", result.stdout)

    def test_selection_rejects_multiline_inline_code_evidence_shape(self) -> None:
        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "domain-context",
                    "domain": "domain",
                    "candidate": "도메인 맥락",
                    "disposition": "write",
                    "selection_basis": "승인된 경계를 설명한다.",
                    "candidate_atom_keys": ["domain-context"],
                }
            ],
            bundle_keys=["domain-context"],
            request_id="20260714-120012-multiline-inline",
        )
        evidence_path = (
            self.root
            / ".stageflow"
            / "atomic-docs"
            / "requests"
            / request_id
            / "evidence.md"
        )
        evidence_path.write_text(
            "\n".join(
                [
                    "# 근거 색인",
                    "prefix ``code",
                    f"source_commit_observed: `{self.commit}`",
                    "## domain-context",
                    "- `source.txt:1` 코드 span 안의 가짜 근거",
                    "end`` suffix",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn(
            "evidence inline code must open and close on the same line",
            result.stdout,
        )

    def test_selection_handles_backslash_inside_line_local_code_span(self) -> None:
        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "domain-context",
                    "domain": "domain",
                    "candidate": "도메인 맥락",
                    "disposition": "write",
                    "selection_basis": "승인된 경계를 설명한다.",
                    "candidate_atom_keys": ["domain-context"],
                }
            ],
            bundle_keys=["domain-context"],
            request_id="20260714-120013-backslash-code",
        )
        evidence_path = (
            self.root
            / ".stageflow"
            / "atomic-docs"
            / "requests"
            / request_id
            / "evidence.md"
        )
        evidence_path.write_text(
            "\n".join(
                [
                    "# 근거 색인",
                    "코드 표기: `path\\`",
                    f"source_commit_observed: `{self.commit}`",
                    "## domain-context",
                    "- `source.txt:1` 실제 표시되는 근거",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        evidence_path.write_text(
            "\n".join(
                [
                    "# 근거 색인",
                    "prefix `first\\` tail`",
                    f"source_commit_observed: `{self.commit}`",
                    "## domain-context",
                    "- `source.txt:1` 다음 줄까지 이어지는 가짜 code span",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn(
            "evidence inline code must open and close on the same line",
            result.stdout,
        )

    def test_selection_version_two_requires_closure_and_version_one_forbids_it(self) -> None:
        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "domain-context",
                    "domain": "domain",
                    "candidate": "도메인 맥락",
                    "disposition": "write",
                    "selection_basis": "도메인 소유권을 설명한다.",
                    "candidate_atom_keys": ["domain-context"],
                }
            ],
            bundle_keys=["domain-context"],
            request_id="20260715-130000-version-two-closure",
            selection_version="2",
        )
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn(
            "`context_selection.version` `2` must contain `semantic_review_closure`",
            result.stdout,
        )

        state = self.read_selection_state(request_id)
        state["semantic_review_closure"] = {
            "version": "1",
            "basis_revision": 1,
            "review_passes": [],
            "invalidations": [],
            "final_gate": {"required": False, "review_history": []},
        }
        self.write_selection_data(request_id, state)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        state["context_selection"]["version"] = "1"
        self.write_selection_data(request_id, state)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn(
            "`semantic_review_closure` requires `context_selection.version` `2`",
            result.stdout,
        )

    def test_semantic_review_closure_blocks_final_until_affected_reviews_pass(self) -> None:
        self.write_atom("domain/domain-context-atom.md", "domain-context")
        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "domain-context",
                    "domain": "domain",
                    "candidate": "도메인 맥락",
                    "disposition": "write",
                    "selection_basis": "공유 소유권 변경 영향을 설명한다.",
                    "candidate_atom_keys": ["domain-context"],
                }
            ],
            bundle_keys=["domain-context"],
            request_id="20260715-130001-semantic-closure",
            selection_version="2",
        )
        state = self.read_selection_state(request_id)
        state["semantic_review_closure"] = {
            "version": "1",
            "basis_revision": 2,
            "review_passes": [
                {
                    "review_id": "domain-development-1",
                    "reviewer_role": "development",
                    "scope": "domain",
                    "basis_revision": 1,
                    "verdict": "PASS",
                    "status": "stale",
                }
            ],
            "invalidations": [
                {
                    "invalidation_id": "domain-owner-change-1",
                    "trigger": "ownership",
                    "cause": "공유 소유자가 변경되어 이전 도메인 검토 근거가 오래됐다.",
                    "opened_revision": 2,
                    "affected_artifacts": [
                        {
                            "location": "managed-docs",
                            "path": "domain/domain-context-atom.md",
                        },
                        {"location": "request", "path": "inventory.md"},
                    ],
                    "affected_bundles": ["domain"],
                    "stale_review_ids": ["domain-development-1"],
                    "required_reviews": [
                        {"reviewer_role": "development", "scope": "domain"},
                        {
                            "reviewer_role": "integration",
                            "scope": "affected-closure",
                        },
                    ],
                    "status": "open",
                }
            ],
            "final_gate": {"required": True, "review_history": []},
        }
        self.write_selection_data(request_id, state)

        selection = self.run_validator("selection", request_id=request_id)
        self.assertEqual(0, selection.returncode, selection.stdout + selection.stderr)
        final_selection = self.run_validator(
            "selection", request_id=request_id, require_actions_final=True
        )
        self.assertEqual(1, final_selection.returncode)
        self.assertIn("is still open at final validation", final_selection.stdout)

        final_docs = self.run_validator("docs", request_id=request_id)
        self.assertEqual(1, final_docs.returncode)
        self.assertIn("is still open at final validation", final_docs.stdout)
        self.assertIn("is still stale at final validation", final_docs.stdout)
        self.assertIn("requires a recorded final PASS", final_docs.stdout)

        closure = state["semantic_review_closure"]
        closure["review_passes"][0]["status"] = "superseded"
        closure["review_passes"].extend(
            [
                {
                    "review_id": "domain-development-2",
                    "reviewer_role": "development",
                    "scope": "domain",
                    "basis_revision": 2,
                    "verdict": "PASS",
                    "status": "current",
                },
                {
                    "review_id": "affected-integration-2",
                    "reviewer_role": "integration",
                    "scope": "affected-closure",
                    "basis_revision": 2,
                    "verdict": "PASS",
                    "status": "current",
                },
            ]
        )
        closure["invalidations"][0].update(
            {"status": "resolved", "resolved_revision": 2}
        )
        closure["final_gate"]["review_history"].append("affected-integration-2")
        closure["final_gate"]["review_id"] = "affected-integration-2"
        self.write_selection_data(request_id, state)

        final_docs = self.run_validator("docs", request_id=request_id)
        self.assertEqual(0, final_docs.returncode, final_docs.stdout + final_docs.stderr)
        del closure["final_gate"]["review_id"]
        self.write_selection_data(request_id, state)
        cleared_pointer = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, cleared_pointer.returncode)
        self.assertIn(
            "must point to its latest current history PASS",
            cleared_pointer.stdout,
        )
        closure["final_gate"]["review_id"] = "affected-integration-2"
        self.write_selection_data(request_id, state)
        self.write_baseline()
        baseline = self.run_validator("baseline", request_id=request_id)
        self.assertEqual(1, baseline.returncode)
        self.assertIn(
            "must reference a current `baseline`/`project-wide` PASS",
            baseline.stdout,
        )

        closure["review_passes"].append(
            {
                "review_id": "project-baseline-2",
                "reviewer_role": "baseline",
                "scope": "project-wide",
                "basis_revision": 2,
                "verdict": "PASS",
                "status": "current",
            }
        )
        closure["final_gate"]["review_history"].append("project-baseline-2")
        closure["final_gate"]["review_id"] = "project-baseline-2"
        self.write_selection_data(request_id, state)
        baseline = self.run_validator("baseline", request_id=request_id)
        self.assertEqual(0, baseline.returncode, baseline.stdout + baseline.stderr)

    def test_semantic_review_closure_rejects_false_resolution_and_bad_paths(self) -> None:
        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "domain-context",
                    "domain": "domain",
                    "candidate": "도메인 맥락",
                    "disposition": "write",
                    "selection_basis": "소유권 맥락을 설명한다.",
                    "candidate_atom_keys": ["domain-context"],
                }
            ],
            bundle_keys=["domain-context"],
            request_id="20260715-130002-invalid-semantic-closure",
            selection_version="2",
        )
        state = self.read_selection_state(request_id)
        state["semantic_review_closure"] = {
            "version": "1",
            "basis_revision": 2,
            "review_passes": [
                {
                    "review_id": "domain-development-1",
                    "reviewer_role": "development",
                    "scope": "domain",
                    "basis_revision": 1,
                    "verdict": "PASS",
                    "status": "superseded",
                }
            ],
            "invalidations": [
                {
                    "invalidation_id": "domain-meaning-change-1",
                    "trigger": "documented-meaning",
                    "cause": "문서 의미가 변경됐다.",
                    "opened_revision": 2,
                    "affected_artifacts": [
                        {"location": "request", "path": "work-state.json"}
                    ],
                    "affected_bundles": ["domain"],
                    "stale_review_ids": ["domain-development-1"],
                    "required_reviews": [
                        {"reviewer_role": "development", "scope": "domain"}
                    ],
                    "status": "resolved",
                    "resolved_revision": 2,
                }
            ],
            "final_gate": {"required": False, "review_history": []},
        }
        self.write_selection_data(request_id, state)

        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("must not reference work-state.json itself", result.stdout)
        self.assertIn("is missing current PASS", result.stdout)

        state["semantic_review_closure"] = None
        self.write_selection_data(request_id, state)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("`semantic_review_closure` must be an object", result.stdout)

    def test_semantic_review_closure_rejects_overlapping_stale_pass_and_scope_escape(self) -> None:
        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "domain-context",
                    "domain": "domain",
                    "candidate": "도메인 맥락",
                    "disposition": "write",
                    "selection_basis": "공유 결정을 설명한다.",
                    "candidate_atom_keys": ["domain-context"],
                }
            ],
            bundle_keys=["domain-context"],
            request_id="20260715-130004-overlapping-invalidation",
            selection_version="2",
        )
        state = self.read_selection_state(request_id)
        prior_pass = {
            "review_id": "domain-development-1",
            "reviewer_role": "development",
            "scope": "domain",
            "basis_revision": 1,
            "verdict": "PASS",
            "status": "stale",
        }
        first = {
            "invalidation_id": "domain-owner-change-1",
            "trigger": "ownership",
            "cause": "공유 소유자가 변경됐다.",
            "opened_revision": 2,
            "affected_artifacts": [
                {"location": "request", "path": "inventory.md"}
            ],
            "affected_bundles": ["domain"],
            "stale_review_ids": ["domain-development-1"],
            "required_reviews": [
                {"reviewer_role": "development", "scope": "domain"}
            ],
            "status": "open",
        }
        second = {
            **first,
            "invalidation_id": "domain-glossary-change-1",
            "trigger": "glossary-source",
            "cause": "용어 원본도 함께 변경됐다.",
            "affected_bundles": ["outside"],
            "required_reviews": [
                {"reviewer_role": "development", "scope": "outside"}
            ],
        }
        state["semantic_review_closure"] = {
            "version": "1",
            "basis_revision": 2,
            "review_passes": [prior_pass],
            "invalidations": [first, second],
            "final_gate": {"required": False, "review_history": []},
        }
        self.write_selection_data(request_id, state)

        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("is stale in more than one invalidation", result.stdout)
        self.assertIn("affected bundle `outside` is outside `accepted_scope`", result.stdout)
        self.assertIn("scope `outside` is outside `accepted_scope`", result.stdout)

    def test_request_bound_final_validation_keeps_legacy_operation_compatible(self) -> None:
        self.write_atom("domain/domain-context-atom.md", "domain-context")
        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "domain-context",
                    "domain": "domain",
                    "candidate": "도메인 맥락",
                    "disposition": "write",
                    "selection_basis": "레거시 작업의 기존 선택 상태다.",
                    "candidate_atom_keys": ["domain-context"],
                }
            ],
            bundle_keys=["domain-context"],
            request_id="20260715-130003-legacy-closure",
        )

        docs = self.run_validator("docs", request_id=request_id)
        self.assertEqual(0, docs.returncode, docs.stdout + docs.stderr)
        self.write_baseline()
        baseline = self.run_validator("baseline", request_id=request_id)
        self.assertEqual(0, baseline.returncode, baseline.stdout + baseline.stderr)

    def test_selection_requires_request_id_and_keeps_existing_phases_compatible(self) -> None:
        selection = self.run_validator("selection")
        self.assertEqual(1, selection.returncode)
        self.assertIn("requires `--request-id`", selection.stdout)

        bootstrap = self.run_validator("bootstrap")
        self.assertEqual(0, bootstrap.returncode, bootstrap.stdout + bootstrap.stderr)

        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "domain-context",
                    "domain": "domain",
                    "candidate": "도메인 맥락",
                    "disposition": "write",
                    "selection_basis": "소유권을 설명한다.",
                    "candidate_atom_keys": ["domain-context"],
                }
            ],
            bundle_keys=["domain-context"],
        )
        wrong_phase = self.run_validator("bootstrap", request_id=request_id)
        self.assertEqual(1, wrong_phase.returncode)
        self.assertIn(
            "`--request-id` requires `--phase selection`, `docs`, or `baseline`",
            wrong_phase.stdout,
        )

    def test_docs_and_project_wide_baseline_pass(self) -> None:
        self.write_atom("domain/example-atom.md", "example")
        docs_result = self.run_validator("docs")
        self.assertEqual(0, docs_result.returncode, docs_result.stdout + docs_result.stderr)
        self.assertIn("1 atoms", docs_result.stdout)
        self.assertIn("7 AIDs", docs_result.stdout)

        self.write_baseline()
        baseline_result = self.run_validator("baseline")
        self.assertEqual(0, baseline_result.returncode, baseline_result.stdout + baseline_result.stderr)
        self.assertIn("PASS baseline", baseline_result.stdout)

    def test_atom_without_aids_is_valid(self) -> None:
        self.write_atom("domain/context-atom.md", "context", with_aids=False)

        result = self.run_validator("docs")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("1 atoms", result.stdout)
        self.assertIn("0 AIDs", result.stdout)

    def test_duplicate_atom_key_and_aid_fail(self) -> None:
        self.write_atom("domain/first-atom.md", "duplicate")
        self.write_atom("domain/second-atom.md", "duplicate")
        result = self.run_validator("docs")
        self.assertEqual(1, result.returncode)
        self.assertIn("duplicate atom_key `duplicate`", result.stdout)
        self.assertIn("duplicate AID `[AID:duplicate.intent.001]`", result.stdout)

    def test_duplicate_aid_across_different_atoms_fails(self) -> None:
        self.write_atom("domain/first-atom.md", "first", aid_key="shared-origin")
        self.write_atom("domain/second-atom.md", "second", aid_key="shared-origin")
        result = self.run_validator("docs")
        self.assertEqual(1, result.returncode)
        self.assertIn("duplicate AID `[AID:shared-origin.intent.001]`", result.stdout)

    def test_missing_required_section_fails(self) -> None:
        self.write_atom("domain/example-atom.md", "example", omit_section="Outcomes")
        result = self.run_validator("docs")
        self.assertEqual(1, result.returncode)
        self.assertIn("must contain exactly one `## Outcomes` section", result.stdout)

    def test_graph_target_must_exist_and_match_key(self) -> None:
        self.write_atom("domain/target-atom.md", "target")
        self.write_atom("domain/other-atom.md", "other")
        source = self.write_atom(
            "domain/source-atom.md",
            "source",
            edges=[
                {
                    "type": "depends_on",
                    "target_key": "target",
                    "target_path": "domain/other-atom.md",
                    "reason": "계약을 사용한다.",
                }
            ],
        )
        result = self.run_validator("docs")
        self.assertEqual(1, result.returncode)
        self.assertIn("resolve to different atoms", result.stdout)

        text = source.read_text(encoding="utf-8").replace(
            "target_path: domain/other-atom.md", "target_path: domain/missing-atom.md"
        )
        source.write_text(text, encoding="utf-8")
        result = self.run_validator("docs")
        self.assertEqual(1, result.returncode)
        self.assertIn("does not exist", result.stdout)

    def test_partial_baseline_is_rejected(self) -> None:
        self.write_atom("domain/example-atom.md", "example")
        self.write_baseline("partial")
        result = self.run_validator("baseline")
        self.assertEqual(1, result.returncode)
        self.assertIn("partial baselines are invalid", result.stdout)

    def test_moved_meaning_may_keep_historical_aid_prefix(self) -> None:
        self.write_atom("domain/new-owner-atom.md", "new-owner", aid_key="original-owner")
        result = self.run_validator("docs")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_aid_section_code_must_match_containing_section(self) -> None:
        path = self.write_atom("domain/example-atom.md", "example")
        text = path.read_text(encoding="utf-8").replace(
            "[AID:example.outcome.001]", "[AID:example.boundary.001]"
        )
        path.write_text(text, encoding="utf-8")
        result = self.run_validator("docs")
        self.assertEqual(1, result.returncode)
        self.assertIn("belongs under `## Boundaries`, not `Outcomes`", result.stdout)

    def test_config_paths_cannot_escape_project(self) -> None:
        config_path = self.root / ".stageflow" / "atomic-docs.json"
        data = json.loads(config_path.read_text(encoding="utf-8"))
        data["docs_root"] = "../outside"
        config_path.write_text(json.dumps(data), encoding="utf-8")
        result = self.run_validator("bootstrap")
        self.assertEqual(1, result.returncode)
        self.assertIn("`docs_root` must be a safe relative path", result.stdout)

    def test_standard_yaml_frontmatter_is_parsed(self) -> None:
        target = self.write_atom("domain/target-atom.md", "target")
        source = self.write_atom("domain/source-atom.md", "source")
        text = source.read_text(encoding="utf-8").replace(
            "atom_key: source\ngraph_edges: []",
            "atom_key: 'source'\n"
            "title: \"Source: contract\"\n"
            "graph_edges:\n"
            "  - type: depends_on\n"
            "    target_key: target\n"
            "    target_path: domain/target-atom.md\n"
            "    reason: \"Uses target: contract\"",
        )
        source.write_text(text, encoding="utf-8")

        result = self.run_validator("docs", "source", "target")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertTrue(target.is_file())

    def test_invalid_or_duplicate_yaml_frontmatter_fails(self) -> None:
        path = self.write_atom("domain/example-atom.md", "example")
        text = path.read_text(encoding="utf-8").replace(
            "atom_key: example", "atom_key: example\natom_key: duplicate"
        )
        path.write_text(text, encoding="utf-8")
        result = self.run_validator("docs")
        self.assertEqual(1, result.returncode)
        self.assertIn("invalid YAML frontmatter", result.stdout)
        self.assertIn("duplicate key", result.stdout)

    def test_bundle_expected_atom_keys_must_exist(self) -> None:
        self.write_atom("domain/example-atom.md", "example")

        result = self.run_validator("docs", "example", "missing-owner")
        self.assertEqual(1, result.returncode)
        self.assertIn("expected atom key `missing-owner` does not exist", result.stdout)

    def test_bundle_scope_ignores_unrelated_structure_but_full_docs_does_not(self) -> None:
        self.write_atom("domain/active-atom.md", "active")
        self.write_atom("other/broken-atom.md", "broken", omit_section="Gaps")

        scoped = self.run_validator("docs", "active")
        self.assertEqual(0, scoped.returncode, scoped.stdout + scoped.stderr)
        self.assertIn("1 scoped atoms", scoped.stdout)

        full = self.run_validator("docs")
        self.assertEqual(1, full.returncode)
        self.assertIn("`docs/other/broken-atom.md` must contain exactly one `## Gaps`", full.stdout)

    def test_bundle_scope_still_checks_global_aid_collisions(self) -> None:
        self.write_atom("domain/active-atom.md", "active", aid_key="shared-origin")
        self.write_atom("other/other-atom.md", "other", aid_key="shared-origin")

        result = self.run_validator("docs", "active")
        self.assertEqual(1, result.returncode)
        self.assertIn("duplicate AID `[AID:shared-origin.intent.001]`", result.stdout)

    def test_expected_atom_key_requires_docs_phase(self) -> None:
        result = self.run_validator("bootstrap", "example")
        self.assertEqual(1, result.returncode)
        self.assertIn("requires `--phase docs`", result.stdout)

        self.write_atom("domain/example-atom.md", "example")
        self.write_baseline()
        result = self.run_validator("baseline", "example")
        self.assertEqual(1, result.returncode)
        self.assertIn("requires `--phase docs`", result.stdout)


if __name__ == "__main__":
    unittest.main()
