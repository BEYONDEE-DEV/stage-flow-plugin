from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.validate_atomic_docs import (
    required_final_validation_scope,
    validate_state_snapshot_completeness,
)

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

    def test_required_final_validation_scope_uses_operation_profile(self) -> None:
        self.assertEqual(
            "baseline",
            required_final_validation_scope({"operation_profile": "initial-baseline"}),
        )
        self.assertEqual(
            "baseline",
            required_final_validation_scope(
                {"operation_profile": "baseline-diff-refresh"}
            ),
        )
        self.assertEqual("docs", required_final_validation_scope({}))

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
        selection_version: str | None = "4",
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
        normalized_risk_triggers = copy.deepcopy(risk_triggers or [])
        bundle: dict[str, object] = {
            "domain": bundle_domain,
            "expected_atom_keys": bundle_keys,
        }
        state: dict[str, object] = {
            "accepted_scope": ["domain"] if accepted_scope is None else accepted_scope,
            "source_commit_observed": observed,
            "context_selection": context_selection,
            "bundle_queue": [bundle],
            "risk_triggers": normalized_risk_triggers,
        }
        if selection_version == "4":
            bundle.update(
                {
                    "bundle_id": f"{bundle_domain}-bundle",
                    "depends_on_contract_ids": [],
                }
            )
            for trigger in normalized_risk_triggers:
                if isinstance(trigger, dict):
                    trigger.setdefault("route", "local")
            state.update(
                {
                    "shared_contracts": [],
                    "persistent_agent_ids": {
                        "writer": "writer-1",
                        "reviewer": "reviewer-1",
                    },
                    "selection_readiness": {
                        "version": "1",
                        "basis_revision": 1,
                        "reviews": [
                            {
                                "review_id": "selection-readiness-1",
                                "reviewer_role": "development",
                                "reviewer_agent_id": "reviewer-1",
                                "basis_revision": 1,
                                "verdict": "PASS",
                                "status": "current",
                            }
                        ],
                    },
                    "late_shared_contract_discoveries": [],
                    "semantic_fail_diagnostics": [],
                    "selection_retirements": {
                        "version": "1",
                        "retired_bundles": [],
                        "retired_contracts": [],
                    },
                    "dispatch_control": {
                        "version": "1",
                        "status": "ready",
                        "episodes": [],
                    },
                    "semantic_review_closure": {
                        "version": "1",
                        "basis_revision": 1,
                        "review_passes": [],
                        "invalidations": [],
                        "final_gate": {"required": False, "review_history": []},
                    },
                    "operation_metrics": {
                        "version": "1",
                        "status": "active",
                        "started_at": "2026-07-20T08:00:00Z",
                        "spans": [
                            {
                                "span_id": "selection-readiness-1",
                                "kind": "development-review",
                                "scope": "selection-readiness",
                                "attempt_id": "readiness-attempt-1",
                                "status": "finished",
                                "started_at": "2026-07-20T08:00:01Z",
                                "finished_at": "2026-07-20T08:00:02Z",
                                "outcome": "PASS",
                            }
                        ],
                    },
                }
            )
        (request_root / "work-state.json").write_text(
            json.dumps(state),
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

    def write_v4_owner_readiness_state(
        self,
        request_id: str = "20260720-170000-owner-readiness-v4",
    ) -> tuple[str, dict[str, object]]:
        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "access-policy",
                    "domain": "accounts",
                    "candidate": "공유 접근 정책",
                    "disposition": "write",
                    "selection_basis": "여러 도메인이 소비하는 권한 계약이다.",
                    "candidate_atom_keys": ["access-policy"],
                },
                {
                    "candidate_id": "program-access",
                    "domain": "programs",
                    "candidate": "프로그램 접근 소비자",
                    "disposition": "write",
                    "selection_basis": "공유 접근 정책을 직접 소비한다.",
                    "candidate_atom_keys": ["program-access"],
                },
            ],
            bundle_keys=["access-policy"],
            risk_triggers=[],
            request_id=request_id,
            accepted_scope=["accounts", "programs"],
            bundle_domain="accounts",
            selection_version="4",
        )
        state = self.read_selection_state(request_id)
        state.update(
            {
                "bundle_queue": [
                    {
                        "bundle_id": "accounts-owner",
                        "domain": "accounts",
                        "expected_atom_keys": ["access-policy"],
                        "depends_on_contract_ids": [],
                    },
                    {
                        "bundle_id": "programs-consumer",
                        "domain": "programs",
                        "expected_atom_keys": ["program-access"],
                        "depends_on_contract_ids": ["access-policy-contract"],
                    },
                ],
                "risk_triggers": [
                    {
                        "candidate_id": "access-policy",
                        "atom_key": "access-policy",
                        "triggers": ["shared permission contract"],
                        "basis": "프로그램 도메인이 직접 소비한다.",
                        "route": "shared-contract",
                        "shared_contract_id": "access-policy-contract",
                    },
                    {
                        "candidate_id": "program-access",
                        "atom_key": "program-access",
                        "triggers": ["shared permission consumer"],
                        "basis": "공유 접근 정책을 직접 소비한다.",
                        "route": "shared-contract",
                        "shared_contract_id": "access-policy-contract",
                    },
                    {
                        "candidate_id": "program-access",
                        "atom_key": "program-access",
                        "triggers": ["local authorization branch"],
                        "basis": "소비자 내부의 추가 분기는 로컬 검토로 충분하다.",
                        "route": "local",
                    },
                ],
                "shared_contracts": [
                    {
                        "contract_id": "access-policy-contract",
                        "kind": "permission",
                        "owner_candidate_id": "access-policy",
                        "owner_atom_key": "access-policy",
                        "direct_consumer_candidate_ids": ["program-access"],
                        "evidence_routes": ["source.txt:1"],
                        "owner_bundle_id": "accounts-owner",
                        "consumer_bundle_ids": ["programs-consumer"],
                    }
                ],
                "persistent_agent_ids": {
                    "writer": "writer-1",
                    "reviewer": "reviewer-1",
                },
                "selection_readiness": {
                    "version": "1",
                    "basis_revision": 1,
                    "reviews": [
                        {
                            "review_id": "selection-readiness-1",
                            "reviewer_role": "development",
                            "reviewer_agent_id": "reviewer-1",
                            "basis_revision": 1,
                            "verdict": "PASS",
                            "status": "current",
                        }
                    ],
                },
                "late_shared_contract_discoveries": [],
                "semantic_fail_diagnostics": [],
                "selection_retirements": {
                    "version": "1",
                    "retired_bundles": [],
                    "retired_contracts": [],
                },
                "dispatch_control": {
                    "version": "1",
                    "status": "ready",
                    "episodes": [],
                },
                "semantic_review_closure": {
                    "version": "1",
                    "basis_revision": 1,
                    "review_passes": [],
                    "invalidations": [],
                    "final_gate": {"required": False, "review_history": []},
                },
                "operation_metrics": {
                    "version": "1",
                    "status": "active",
                    "started_at": "2026-07-20T08:00:00Z",
                    "spans": [
                        {
                            "span_id": "selection-readiness-1",
                            "kind": "development-review",
                            "scope": "selection-readiness",
                            "attempt_id": "readiness-attempt-1",
                            "status": "finished",
                            "started_at": "2026-07-20T08:00:01Z",
                            "finished_at": "2026-07-20T08:00:02Z",
                            "outcome": "PASS",
                        }
                    ],
                },
            }
        )
        self.write_selection_data(request_id, state)
        return request_id, state

    def write_v4_final_state(
        self,
        request_id: str,
        *,
        validation_scope: str = "docs",
        terminal_stage: str = "active-validation",
    ) -> tuple[str, dict[str, object]]:
        request_id, state = self.write_v4_owner_readiness_state(request_id)
        self.write_atom("accounts/access-policy-atom.md", "access-policy")
        self.write_atom("programs/program-access-atom.md", "program-access")
        spans = state["operation_metrics"]["spans"]
        spans.extend(
            [
                {
                    "span_id": "accounts-bundle-1",
                    "kind": "bundle",
                    "scope": "accounts",
                    "attempt_id": "accounts-attempt-1",
                    "status": "finished",
                    "started_at": "2026-07-20T08:00:03Z",
                    "finished_at": "2026-07-20T08:00:04Z",
                    "outcome": "completed",
                },
                {
                    "span_id": "accounts-writer-1",
                    "kind": "writer",
                    "scope": "accounts",
                    "attempt_id": "accounts-attempt-1",
                    "status": "finished",
                    "started_at": "2026-07-20T08:00:05Z",
                    "finished_at": "2026-07-20T08:00:06Z",
                    "outcome": "completed",
                },
                {
                    "span_id": "accounts-risk-1",
                    "kind": "risk-review",
                    "scope": "accounts-owner",
                    "attempt_id": "accounts-attempt-1",
                    "status": "finished",
                    "started_at": "2026-07-20T08:00:07Z",
                    "finished_at": "2026-07-20T08:00:08Z",
                    "outcome": "PASS",
                },
                {
                    "span_id": "programs-bundle-1",
                    "kind": "bundle",
                    "scope": "programs",
                    "attempt_id": "programs-attempt-1",
                    "status": "finished",
                    "started_at": "2026-07-20T08:00:09Z",
                    "finished_at": "2026-07-20T08:00:10Z",
                    "outcome": "completed",
                },
                {
                    "span_id": "programs-writer-1",
                    "kind": "writer",
                    "scope": "programs",
                    "attempt_id": "programs-attempt-1",
                    "status": "finished",
                    "started_at": "2026-07-20T08:00:11Z",
                    "finished_at": "2026-07-20T08:00:12Z",
                    "outcome": "completed",
                },
                {
                    "span_id": "programs-risk-1",
                    "kind": "risk-review",
                    "scope": "programs-consumer",
                    "attempt_id": "programs-attempt-1",
                    "status": "finished",
                    "started_at": "2026-07-20T08:00:13Z",
                    "finished_at": "2026-07-20T08:00:14Z",
                    "outcome": "PASS",
                },
            ]
        )
        if validation_scope == "baseline":
            state["operation_profile"] = "initial-baseline"
            state["semantic_review_closure"] = {
                "version": "1",
                "basis_revision": 1,
                "review_passes": [
                    {
                        "review_id": "baseline-review-1",
                        "reviewer_role": "baseline",
                        "scope": "project-wide",
                        "basis_revision": 1,
                        "verdict": "PASS",
                        "status": "current",
                    }
                ],
                "invalidations": [],
                "final_gate": {
                    "required": True,
                    "review_id": "baseline-review-1",
                    "review_history": ["baseline-review-1"],
                },
            }
            spans.append(
                {
                    "span_id": "baseline-review-1",
                    "kind": "baseline-review",
                    "scope": "project-wide",
                    "attempt_id": "baseline-attempt-1",
                    "status": "finished",
                    "started_at": "2026-07-20T08:00:15Z",
                    "finished_at": "2026-07-20T08:00:16Z",
                    "outcome": "PASS",
                }
            )
            self.write_baseline()
        validation_start = (
            "2026-07-20T08:00:17Z"
            if validation_scope == "baseline"
            else "2026-07-20T08:00:15Z"
        )
        validation_finish = (
            "2026-07-20T08:00:18Z"
            if validation_scope == "baseline"
            else "2026-07-20T08:00:16Z"
        )
        validation_span = {
            "span_id": f"{validation_scope}-final-1",
            "kind": "validation",
            "scope": validation_scope,
            "attempt_id": f"{validation_scope}-final-attempt-1",
            "status": "active",
            "started_at": validation_start,
        }
        if terminal_stage != "active-validation":
            validation_span.update(
                {
                    "status": "finished",
                    "finished_at": validation_finish,
                    "outcome": "PASS",
                }
            )
        spans.append(validation_span)
        if terminal_stage == "finished":
            state["operation_metrics"].update(
                {
                    "status": "finished",
                    "finished_at": (
                        "2026-07-20T08:00:19Z"
                        if validation_scope == "baseline"
                        else "2026-07-20T08:00:17Z"
                    ),
                }
            )
        self.write_selection_data(request_id, state)
        return request_id, state

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
        )
        state = self.read_selection_state(request_id)
        active_bundle = copy.deepcopy(state["bundle_queue"][0])
        state["semantic_review_closure"] = {
            "version": "1",
            "basis_revision": 1,
            "review_passes": [
                {
                    "review_id": "domain-development-1",
                    "reviewer_role": "development",
                    "scope": "domain-bundle",
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
                "affected_bundles": ["domain-bundle"],
                "stale_review_ids": ["domain-development-1"],
                "required_reviews": [
                    {
                        "reviewer_role": "development",
                        "scope": "domain-bundle",
                    }
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
        state["selection_retirements"]["retired_bundles"] = [
            {
                **active_bundle,
                "retired_basis_revision": 2,
                "reason": "candidate drop removed the bundle's last write key",
            }
        ]
        state["selection_readiness"]["basis_revision"] = 2
        state["selection_readiness"]["reviews"][0]["status"] = "superseded"
        state["selection_readiness"]["reviews"].append(
            {
                "review_id": "selection-readiness-2",
                "reviewer_role": "development",
                "reviewer_agent_id": "reviewer-1",
                "basis_revision": 2,
                "verdict": "PASS",
                "status": "current",
            }
        )
        state["operation_metrics"]["spans"].append(
            {
                "span_id": "selection-readiness-2",
                "kind": "development-review",
                "scope": "selection-readiness",
                "attempt_id": "readiness-attempt-2",
                "status": "finished",
                "started_at": "2026-07-20T08:00:03Z",
                "finished_at": "2026-07-20T08:00:04Z",
                "outcome": "PASS",
            }
        )
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
                "scope": "domain-bundle",
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
        )
        state = self.read_selection_state(request_id)
        active_bundle = copy.deepcopy(state["bundle_queue"][0])
        state["semantic_review_closure"] = {
            "version": "1",
            "basis_revision": 1,
            "review_passes": [
                {
                    "review_id": "domain-development-1",
                    "reviewer_role": "development",
                    "scope": "domain-bundle",
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
        state["selection_retirements"]["retired_bundles"] = [
            {
                **active_bundle,
                "retired_basis_revision": 2,
                "reason": "candidate drop removed the bundle's last write key",
            }
        ]
        state["selection_readiness"]["basis_revision"] = 2
        state["selection_readiness"]["reviews"][0]["status"] = "superseded"
        state["selection_readiness"]["reviews"].append(
            {
                "review_id": "selection-readiness-2",
                "reviewer_role": "development",
                "reviewer_agent_id": "reviewer-1",
                "basis_revision": 2,
                "verdict": "PASS",
                "status": "current",
            }
        )
        state["operation_metrics"]["spans"].append(
            {
                "span_id": "selection-readiness-2",
                "kind": "development-review",
                "scope": "selection-readiness",
                "attempt_id": "readiness-attempt-2",
                "status": "finished",
                "started_at": "2026-07-20T08:00:03Z",
                "finished_at": "2026-07-20T08:00:04Z",
                "outcome": "PASS",
            }
        )
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
                    "scope": "domain-bundle",
                    "basis_revision": 1,
                    "verdict": "PASS",
                    "status": "superseded",
                },
                {
                    "review_id": "domain-development-2",
                    "reviewer_role": "development",
                    "scope": "domain-bundle",
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
                    "affected_bundles": ["domain-bundle"],
                    "stale_review_ids": ["domain-development-1"],
                    "required_reviews": [
                        {
                            "reviewer_role": "development",
                            "scope": "domain-bundle",
                        }
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
        non_v4_request_id = self.write_selection_state(
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
            selection_version=None,
            request_id="20260714-120003-unversioned-selection",
        )
        result = self.run_validator("selection", request_id=non_v4_request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn(
            "`context_selection.version` must be exact `4`", result.stdout
        )

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
            source_commit="0" * 40,
            request_id="20260714-120004-bad-evidence",
        )
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
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
            request_id="20260714-120005-empty-evidence",
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

    def test_selection_rejects_every_non_v4_context_selection_version(self) -> None:
        for version in (None, "1", "2", "3", " 4 "):
            label = (
                "unversioned"
                if version is None
                else "padded-v4"
                if version == " 4 "
                else f"v{version}"
            )
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
                request_id=f"20260720-180000-reject-{label}",
                selection_version=version,
            )
            with self.subTest(version=version):
                result = self.run_validator("selection", request_id=request_id)
                self.assertEqual(1, result.returncode)
                self.assertIn(
                    "`context_selection.version` must be exact `4`", result.stdout
                )

    def test_selection_version_four_requires_closure_and_metrics(self) -> None:
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
            request_id="20260720-180001-v4-required-sections",
        )
        state = self.read_selection_state(request_id)
        for field, message in (
            ("semantic_review_closure", "must contain `semantic_review_closure`"),
            ("operation_metrics", "must contain `operation_metrics`"),
        ):
            invalid = copy.deepcopy(state)
            del invalid[field]
            self.write_selection_data(request_id, invalid)
            with self.subTest(field=field):
                result = self.run_validator("selection", request_id=request_id)
                self.assertEqual(1, result.returncode)
                self.assertIn(message, result.stdout)

    def test_selection_version_four_validates_bounded_contract_routing_and_readiness(self) -> None:
        request_id, state = self.write_v4_owner_readiness_state()
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        cases = []
        invalid = copy.deepcopy(state)
        invalid["risk_triggers"][2]["shared_contract_id"] = "access-policy-contract"
        cases.append((invalid, "local route must omit"))

        invalid = copy.deepcopy(state)
        invalid["risk_triggers"].pop(1)
        cases.append((invalid, "is missing its shared risk route"))

        invalid = copy.deepcopy(state)
        invalid["shared_contracts"][0]["owner_candidate_id"] = "unknown-owner"
        cases.append((invalid, "owner candidate does not resolve"))

        invalid = copy.deepcopy(state)
        invalid["shared_contracts"][0]["evidence_routes"] = []
        cases.append((invalid, "at least one evidence route"))

        invalid = copy.deepcopy(state)
        invalid["bundle_queue"].reverse()
        cases.append((invalid, "owner bundle must precede consumer bundle"))

        invalid = copy.deepcopy(state)
        invalid["selection_readiness"]["reviews"][0]["reviewer_agent_id"] = (
            "new-reviewer"
        )
        cases.append((invalid, "must reuse `persistent_agent_ids.reviewer`"))

        invalid = copy.deepcopy(state)
        del invalid["selection_retirements"]
        cases.append((invalid, "`selection_retirements` must be an object"))

        invalid = copy.deepcopy(state)
        invalid["selection_readiness"]["basis_revision"] = 2
        invalid["selection_readiness"]["reviews"][0]["status"] = "stale"
        invalid["selection_readiness"]["reviews"].append(
            {
                "review_id": "selection-readiness-2",
                "reviewer_role": "development",
                "reviewer_agent_id": "reviewer-1",
                "basis_revision": 2,
                "verdict": "PASS",
                "status": "current",
            }
        )
        invalid["operation_metrics"]["spans"].append(
            {
                "span_id": "selection-readiness-2",
                "kind": "development-review",
                "scope": "selection-readiness",
                "attempt_id": "readiness-attempt-2",
                "status": "finished",
                "started_at": "2026-07-20T08:00:05Z",
                "finished_at": "2026-07-20T08:00:06Z",
                "outcome": "PASS",
            }
        )
        cases.append((invalid, "must not retain stale readiness PASSes"))

        invalid = copy.deepcopy(state)
        invalid["operation_metrics"]["spans"].insert(
            0,
            {
                "span_id": "programs-writer-1",
                "kind": "writer",
                "scope": "programs",
                "attempt_id": "programs-attempt-1",
                "status": "finished",
                "started_at": "2026-07-20T08:00:00Z",
                "finished_at": "2026-07-20T08:00:01Z",
                "outcome": "completed",
            },
        )
        cases.append((invalid, "must precede the first writer span"))

        invalid = copy.deepcopy(state)
        invalid["operation_metrics"]["spans"].append(
            {
                "span_id": "programs-writer-before-readiness",
                "kind": "writer",
                "scope": "programs",
                "attempt_id": "programs-attempt-before-readiness",
                "status": "finished",
                "started_at": "2026-07-20T08:00:01Z",
                "finished_at": "2026-07-20T08:00:01.500Z",
                "outcome": "completed",
            }
        )
        cases.append((invalid, "must finish before the first writer starts"))

        for index, (invalid_state, expected) in enumerate(cases, start=1):
            with self.subTest(case=index):
                self.write_selection_data(request_id, invalid_state)
                result = self.run_validator("selection", request_id=request_id)
                self.assertEqual(1, result.returncode)
                self.assertIn(expected, result.stdout)

    def test_version_four_final_phases_revalidate_current_owner_readiness(self) -> None:
        phase_cases = [
            ("docs", "docs", "active-validation"),
            ("baseline", "baseline", "active-validation"),
            ("metrics-preterminal", "docs", "preterminal"),
            ("metrics-final", "docs", "finished"),
        ]
        for phase, validation_scope, terminal_stage in phase_cases:
            with self.subTest(phase=phase, state="valid"):
                request_id, valid = self.write_v4_final_state(
                    f"20260720-v4-final-{phase}",
                    validation_scope=validation_scope,
                    terminal_stage=terminal_stage,
                )
                result = self.run_validator(phase, request_id=request_id)
                self.assertEqual(0, result.returncode, result.stdout + result.stderr)

            invalid_cases: list[tuple[str, dict[str, object], str]] = []
            missing_readiness = copy.deepcopy(valid)
            del missing_readiness["selection_readiness"]
            invalid_cases.append(
                (
                    "missing-readiness",
                    missing_readiness,
                    "`selection_readiness` must be an object",
                )
            )

            stale_readiness = copy.deepcopy(valid)
            stale_readiness["selection_readiness"]["basis_revision"] = 2
            stale_readiness["selection_readiness"]["reviews"][0]["status"] = "stale"
            invalid_cases.append(
                (
                    "stale-readiness",
                    stale_readiness,
                    "ready dispatch requires exactly one current readiness PASS",
                )
            )

            open_pause = copy.deepcopy(valid)
            open_pause["selection_readiness"]["basis_revision"] = 2
            open_pause["selection_readiness"]["reviews"][0]["status"] = "stale"
            open_pause["late_shared_contract_discoveries"] = [
                {
                    "discovery_id": "late-before-semantic-pass",
                    "contract_id": "access-policy-contract",
                    "stage": "post-readiness",
                    "basis_revision": 2,
                    "affected_bundle_ids": ["accounts-owner"],
                    "status": "open",
                    "stale_readiness_review_id": "selection-readiness-1",
                    "semantic_invalidation_ids": [],
                }
            ]
            open_pause["dispatch_control"] = {
                "version": "1",
                "status": "paused",
                "episodes": [
                    {
                        "episode_id": "late-before-semantic-pause",
                        "cause": "late-shared-contract",
                        "trigger_ids": ["late-before-semantic-pass"],
                        "pause_after_span_id": next(
                            span["span_id"]
                            for span in reversed(
                                open_pause["operation_metrics"]["spans"]
                            )
                            if span["status"] == "finished"
                        ),
                        "paused_at": next(
                            span["finished_at"]
                            for span in reversed(
                                open_pause["operation_metrics"]["spans"]
                            )
                            if span["status"] == "finished"
                        ),
                        "basis_revision": 2,
                        "status": "open",
                    }
                ],
            }
            invalid_cases.append(
                (
                    "open-pause",
                    open_pause,
                    "requires ready dispatch with no open pause",
                )
            )

            broken_route = copy.deepcopy(valid)
            broken_route["risk_triggers"][0]["shared_contract_id"] = (
                "missing-contract"
            )
            invalid_cases.append(
                (
                    "broken-route",
                    broken_route,
                    "shared_contract_id `missing-contract` does not resolve",
                )
            )

            for name, invalid, expected in invalid_cases:
                with self.subTest(phase=phase, state=name):
                    self.write_selection_data(request_id, invalid)
                    result = self.run_validator(phase, request_id=request_id)
                    self.assertEqual(1, result.returncode)
                    self.assertIn(expected, result.stdout)

    def test_selection_version_four_reports_malformed_nested_state_without_traceback(self) -> None:
        request_id, state = self.write_v4_owner_readiness_state(
            "20260720-170004-v4-malformed"
        )
        mutations = [
            lambda value: value["bundle_queue"][0].update(
                {"expected_atom_keys": None}
            ),
            lambda value: value["bundle_queue"][0].update(
                {"depends_on_contract_ids": None}
            ),
            lambda value: value["shared_contracts"][0].update(
                {"direct_consumer_candidate_ids": None}
            ),
            lambda value: value["shared_contracts"][0].update(
                {"consumer_bundle_ids": None}
            ),
            lambda value: value["shared_contracts"][0].update(
                {"consumer_bundle_ids": [{}]}
            ),
            lambda value: (
                value["shared_contracts"][0].update({"owner_bundle_id": {}}),
                value["late_shared_contract_discoveries"].append(
                    {
                        "discovery_id": "malformed-owner-discovery",
                        "contract_id": "access-policy-contract",
                        "stage": "pre-readiness",
                        "basis_revision": 1,
                        "affected_bundle_ids": ["accounts-owner"],
                        "status": "resolved",
                    }
                ),
            ),
            lambda value: (
                value["bundle_queue"][0].update({"domain": {}}),
                value["late_shared_contract_discoveries"].append(
                    {
                        "discovery_id": "malformed-domain-discovery",
                        "contract_id": "access-policy-contract",
                        "stage": "post-readiness",
                        "basis_revision": 1,
                        "affected_bundle_ids": ["accounts-owner"],
                        "status": "open",
                        "stale_readiness_review_id": "selection-readiness-1",
                        "semantic_invalidation_ids": ["missing-invalidation"],
                    }
                ),
            ),
            lambda value: value["operation_metrics"].update({"spans": None}),
            lambda value: value.update({"selection_retirements": None}),
            lambda value: value["selection_retirements"].update(
                {"retired_bundles": [{"bundle_id": {}}]}
            ),
            lambda value: value["dispatch_control"].update(
                {
                    "status": "paused",
                    "episodes": [
                        {
                            "episode_id": "malformed-pause",
                            "cause": "shared-root-semantic-fail",
                            "trigger_ids": None,
                            "basis_revision": 1,
                            "status": "open",
                        }
                    ],
                }
            ),
        ]
        for index, mutate in enumerate(mutations, start=1):
            with self.subTest(case=index):
                malformed = copy.deepcopy(state)
                mutate(malformed)
                self.write_selection_data(request_id, malformed)
                result = self.run_validator("selection", request_id=request_id)
                self.assertEqual(1, result.returncode)
                self.assertNotIn("Traceback", result.stderr)

    def test_selection_version_four_common_root_pause_and_unrelated_fail_continue(self) -> None:
        request_id, state = self.write_v4_owner_readiness_state(
            "20260720-170001-v4-diagnostics"
        )
        state["operation_metrics"]["spans"].extend(
            [
                {
                    "span_id": "accounts-risk-fail-1",
                    "kind": "risk-review",
                    "scope": "accounts-owner",
                    "attempt_id": "accounts-risk-attempt-1",
                    "status": "finished",
                    "started_at": "2026-07-20T08:00:03Z",
                    "finished_at": "2026-07-20T08:00:04Z",
                    "outcome": "FAIL",
                },
                {
                    "span_id": "programs-risk-fail-1",
                    "kind": "risk-review",
                    "scope": "programs-consumer",
                    "attempt_id": "programs-risk-attempt-1",
                    "status": "finished",
                    "started_at": "2026-07-20T08:00:05Z",
                    "finished_at": "2026-07-20T08:00:06Z",
                    "outcome": "FAIL",
                },
            ]
        )
        state["semantic_fail_diagnostics"] = [
            {
                "diagnostic_id": "accounts-owner-evidence-fail",
                "review_span_id": "accounts-risk-fail-1",
                "first_attempt": True,
                "root_category": "owner-evidence",
                "candidate_ids": ["access-policy"],
                "contract_ids": ["access-policy-contract"],
                "basis_revision": 1,
            },
            {
                "diagnostic_id": "programs-owner-evidence-fail",
                "review_span_id": "programs-risk-fail-1",
                "first_attempt": True,
                "root_category": "owner-evidence",
                "candidate_ids": ["program-access"],
                "contract_ids": ["access-policy-contract"],
                "basis_revision": 1,
            },
        ]
        self.write_selection_data(request_id, state)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("require a dispatch pause/diagnosis episode", result.stdout)

        legacy_domain_review_scope = copy.deepcopy(state)
        legacy_domain_review_scope["operation_metrics"]["spans"][1]["scope"] = (
            "accounts"
        )
        self.write_selection_data(request_id, legacy_domain_review_scope)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn(
            "v4 risk-review scope must be an active/retired stable bundle_id",
            result.stdout,
        )

        unknown_review_scope = copy.deepcopy(state)
        unknown_review_scope["operation_metrics"]["spans"][2]["scope"] = (
            "unknown-bundle"
        )
        self.write_selection_data(request_id, unknown_review_scope)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn(
            "v4 risk-review scope must be an active/retired stable bundle_id",
            result.stdout,
        )

        missing_diagnostic = copy.deepcopy(state)
        missing_diagnostic["semantic_fail_diagnostics"].pop()
        self.write_selection_data(request_id, missing_diagnostic)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("needs a bounded diagnostic", result.stdout)

        duplicate_diagnostic = copy.deepcopy(state)
        duplicate = copy.deepcopy(duplicate_diagnostic["semantic_fail_diagnostics"][1])
        duplicate["diagnostic_id"] = "programs-owner-evidence-duplicate"
        duplicate_diagnostic["semantic_fail_diagnostics"].append(duplicate)
        self.write_selection_data(request_id, duplicate_diagnostic)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("is diagnosed more than once", result.stdout)

        trailing_unrelated = copy.deepcopy(state)
        trailing_unrelated["operation_metrics"]["spans"].append(
            {
                "span_id": "programs-development-fail-1",
                "kind": "development-review",
                "scope": "programs-consumer",
                "attempt_id": "programs-development-attempt-1",
                "status": "finished",
                "started_at": "2026-07-20T08:00:07Z",
                "finished_at": "2026-07-20T08:00:08Z",
                "outcome": "FAIL",
            }
        )
        trailing_unrelated["semantic_fail_diagnostics"].append(
            {
                "diagnostic_id": "programs-fidelity-fail",
                "review_span_id": "programs-development-fail-1",
                "first_attempt": True,
                "root_category": "selected-claim-fidelity",
                "candidate_ids": ["program-access"],
                "contract_ids": [],
                "basis_revision": 1,
            }
        )
        self.write_selection_data(request_id, trailing_unrelated)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("require a dispatch pause/diagnosis episode", result.stdout)

        legacy_development_scope = copy.deepcopy(trailing_unrelated)
        legacy_development_scope["operation_metrics"]["spans"][-1]["scope"] = (
            "programs"
        )
        self.write_selection_data(request_id, legacy_development_scope)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn(
            "v4 development-review scope must be `selection-readiness` or an "
            "active/retired stable bundle_id",
            result.stdout,
        )

        state["dispatch_control"] = {
            "version": "1",
            "status": "paused",
            "episodes": [
                {
                    "episode_id": "owner-evidence-pause-1",
                    "cause": "shared-root-semantic-fail",
                    "trigger_ids": [
                        "accounts-owner-evidence-fail",
                        "programs-owner-evidence-fail",
                    ],
                    "basis_revision": 1,
                    "status": "open",
                }
            ],
        }
        self.write_selection_data(request_id, state)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        result = self.run_validator(
            "selection", request_id=request_id, require_actions_final=True
        )
        self.assertEqual(1, result.returncode)
        self.assertIn("requires ready dispatch with no open pause", result.stdout)

        dispatch_after_open_pause = copy.deepcopy(state)
        dispatch_after_open_pause["operation_metrics"]["spans"].append(
            {
                "span_id": "accounts-bundle-after-pause",
                "kind": "bundle",
                "scope": "accounts",
                "attempt_id": "accounts-after-pause",
                "status": "finished",
                "started_at": "2026-07-20T08:00:07Z",
                "finished_at": "2026-07-20T08:00:08Z",
                "outcome": "completed",
            }
        )
        self.write_selection_data(request_id, dispatch_after_open_pause)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("must not dispatch bundle/writer work", result.stdout)

        cross_basis = copy.deepcopy(state)
        cross_basis["selection_readiness"]["basis_revision"] = 2
        cross_basis["selection_readiness"]["reviews"][0]["status"] = "stale"
        cross_basis["semantic_fail_diagnostics"][1]["basis_revision"] = 2
        cross_basis["dispatch_control"]["episodes"][0]["basis_revision"] = 2
        self.write_selection_data(request_id, cross_basis)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        overlapping = copy.deepcopy(state)
        overlapping["selection_readiness"]["basis_revision"] = 2
        overlapping["selection_readiness"]["reviews"][0]["status"] = "superseded"
        overlapping["selection_readiness"]["reviews"].append(
            {
                "review_id": "selection-readiness-2",
                "reviewer_role": "development",
                "reviewer_agent_id": "reviewer-1",
                "basis_revision": 2,
                "verdict": "PASS",
                "status": "current",
            }
        )
        overlapping["operation_metrics"]["spans"].append(
            {
                "span_id": "selection-readiness-2",
                "kind": "development-review",
                "scope": "selection-readiness",
                "attempt_id": "readiness-attempt-2",
                "status": "finished",
                "started_at": "2026-07-20T08:00:07Z",
                "finished_at": "2026-07-20T08:00:08Z",
                "outcome": "PASS",
            }
        )
        overlapping["operation_metrics"]["spans"].append(
            {
                "span_id": "accounts-risk-fail-2",
                "kind": "risk-review",
                "scope": "accounts-owner",
                "attempt_id": "accounts-risk-attempt-2",
                "status": "finished",
                "started_at": "2026-07-20T08:00:09Z",
                "finished_at": "2026-07-20T08:00:10Z",
                "outcome": "FAIL",
            }
        )
        overlapping["semantic_fail_diagnostics"].append(
            {
                "diagnostic_id": "accounts-owner-evidence-fail-2",
                "review_span_id": "accounts-risk-fail-2",
                "first_attempt": True,
                "root_category": "owner-evidence",
                "candidate_ids": ["access-policy"],
                "contract_ids": ["access-policy-contract"],
                "basis_revision": 2,
            }
        )
        first_episode = overlapping["dispatch_control"]["episodes"][0]
        first_episode.update(
            {
                "status": "resolved",
                "diagnosis": "첫 공통 원인을 진단했다.",
                "action": "owner evidence를 갱신했다.",
                "resume_basis_revision": 2,
                "readiness_review_id": "selection-readiness-2",
            }
        )
        overlapping["dispatch_control"]["episodes"].append(
            {
                "episode_id": "owner-evidence-pause-2",
                "cause": "shared-root-semantic-fail",
                "trigger_ids": [
                    "programs-owner-evidence-fail",
                    "accounts-owner-evidence-fail-2",
                ],
                "basis_revision": 2,
                "status": "open",
            }
        )
        self.write_selection_data(request_id, overlapping)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        unrelated = copy.deepcopy(state)
        unrelated["semantic_fail_diagnostics"][1]["root_category"] = (
            "selected-claim-fidelity"
        )
        unrelated["dispatch_control"] = {
            "version": "1",
            "status": "ready",
            "episodes": [],
        }
        self.write_selection_data(request_id, unrelated)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        different_root = copy.deepcopy(state)
        different_root["semantic_fail_diagnostics"][1]["contract_ids"] = []
        different_root["dispatch_control"] = {
            "version": "1",
            "status": "ready",
            "episodes": [],
        }
        self.write_selection_data(request_id, different_root)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        namespace_collision = copy.deepcopy(state)
        namespace_collision["shared_contracts"][0]["contract_id"] = "program-access"
        namespace_collision["bundle_queue"][1]["depends_on_contract_ids"] = [
            "program-access"
        ]
        for trigger in namespace_collision["risk_triggers"][:2]:
            trigger["shared_contract_id"] = "program-access"
        namespace_collision["semantic_fail_diagnostics"][0].update(
            {"candidate_ids": ["program-access"], "contract_ids": []}
        )
        namespace_collision["semantic_fail_diagnostics"][1].update(
            {"candidate_ids": [], "contract_ids": ["program-access"]}
        )
        namespace_collision["dispatch_control"] = {
            "version": "1",
            "status": "ready",
            "episodes": [],
        }
        self.write_selection_data(request_id, namespace_collision)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        unchanged_basis = copy.deepcopy(state)
        unchanged_episode = unchanged_basis["dispatch_control"]["episodes"][0]
        unchanged_episode.update(
            {
                "status": "resolved",
                "diagnosis": "공통 원인을 진단했다.",
                "action": "근거를 다시 확인했다.",
                "resume_basis_revision": 1,
                "readiness_review_id": "selection-readiness-1",
            }
        )
        unchanged_basis["dispatch_control"]["status"] = "ready"
        self.write_selection_data(request_id, unchanged_basis)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("must advance beyond its pause/trigger basis", result.stdout)

        resolved = copy.deepcopy(state)
        resolved["selection_readiness"]["basis_revision"] = 2
        resolved["selection_readiness"]["reviews"][0]["status"] = "superseded"
        resolved["selection_readiness"]["reviews"].append(
            {
                "review_id": "selection-readiness-2",
                "reviewer_role": "development",
                "reviewer_agent_id": "reviewer-1",
                "basis_revision": 2,
                "verdict": "PASS",
                "status": "current",
            }
        )
        resolved["operation_metrics"]["spans"].append(
            {
                "span_id": "selection-readiness-2",
                "kind": "development-review",
                "scope": "selection-readiness",
                "attempt_id": "readiness-attempt-2",
                "status": "finished",
                "started_at": "2026-07-20T08:00:07Z",
                "finished_at": "2026-07-20T08:00:08Z",
                "outcome": "PASS",
            }
        )
        episode = resolved["dispatch_control"]["episodes"][0]
        episode.update(
            {
                "status": "resolved",
                "diagnosis": "공통 owner evidence route가 readiness에서 누락됐다.",
                "action": "공유 계약 evidence route를 갱신하고 다시 검토했다.",
                "resume_basis_revision": 2,
                "readiness_review_id": "selection-readiness-2",
            }
        )
        resolved["dispatch_control"]["status"] = "ready"
        self.write_selection_data(request_id, resolved)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        dispatch_before_resume = copy.deepcopy(resolved)
        dispatch_before_resume["operation_metrics"]["spans"].insert(
            -1,
            {
                "span_id": "programs-writer-before-resume",
                "kind": "writer",
                "scope": "programs",
                "attempt_id": "programs-before-resume",
                "status": "finished",
                "started_at": "2026-07-20T08:00:06.100Z",
                "finished_at": "2026-07-20T08:00:06.900Z",
                "outcome": "completed",
            },
        )
        self.write_selection_data(request_id, dispatch_before_resume)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("must not dispatch bundle/writer work", result.stdout)

        del episode["diagnosis"]
        self.write_selection_data(request_id, resolved)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("missing required field `diagnosis`", result.stdout)

    def test_selection_version_four_late_discovery_pauses_and_limits_invalidation(self) -> None:
        request_id, state = self.write_v4_owner_readiness_state(
            "20260720-170002-v4-late-discovery"
        )
        state["selection_readiness"]["basis_revision"] = 2
        state["selection_readiness"]["reviews"][0]["status"] = "stale"
        state["semantic_review_closure"] = {
            "version": "1",
            "basis_revision": 2,
            "review_passes": [
                {
                    "review_id": "accounts-development-1",
                    "reviewer_role": "development",
                    "scope": "accounts-owner",
                    "basis_revision": 1,
                    "verdict": "PASS",
                    "status": "stale",
                }
            ],
            "invalidations": [
                {
                    "invalidation_id": "late-access-contract-1",
                    "trigger": "ownership",
                    "cause": "직접 consumer가 readiness 뒤에 발견됐다.",
                    "opened_revision": 2,
                    "affected_artifacts": [
                        {"location": "request", "path": "inventory.md"}
                    ],
                    "affected_bundles": ["accounts-owner", "programs-consumer"],
                    "stale_review_ids": ["accounts-development-1"],
                    "required_reviews": [
                        {
                            "reviewer_role": "development",
                            "scope": "accounts-owner",
                        },
                        {
                            "reviewer_role": "development",
                            "scope": "programs-consumer",
                        },
                    ],
                    "status": "open",
                }
            ],
            "final_gate": {"required": False, "review_history": []},
        }
        state["late_shared_contract_discoveries"] = [
            {
                "discovery_id": "late-access-consumer",
                "contract_id": "access-policy-contract",
                "stage": "post-readiness",
                "basis_revision": 2,
                "affected_bundle_ids": ["accounts-owner", "programs-consumer"],
                "status": "open",
                "stale_readiness_review_id": "selection-readiness-1",
                "semantic_invalidation_ids": ["late-access-contract-1"],
            }
        ]
        state["dispatch_control"] = {
            "version": "1",
            "status": "paused",
            "episodes": [
                {
                    "episode_id": "late-access-pause-1",
                    "cause": "late-shared-contract",
                    "trigger_ids": ["late-access-consumer"],
                    "pause_after_span_id": "selection-readiness-1",
                    "paused_at": "2026-07-20T08:00:02Z",
                    "basis_revision": 2,
                    "status": "open",
                }
            ],
        }
        self.write_selection_data(request_id, state)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        current_risk_reuse = copy.deepcopy(state)
        current_risk_reuse["semantic_review_closure"]["review_passes"].append(
            {
                "review_id": "programs-risk-1",
                "reviewer_role": "risk",
                "scope": "programs-consumer",
                "basis_revision": 1,
                "verdict": "PASS",
                "status": "current",
            }
        )
        self.write_selection_data(request_id, current_risk_reuse)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        missing_open_risk_pair = copy.deepcopy(current_risk_reuse)
        missing_open_risk_pair["semantic_review_closure"]["review_passes"][-1][
            "status"
        ] = "stale"
        missing_open_risk_pair["semantic_review_closure"]["invalidations"][0][
            "stale_review_ids"
        ].append("programs-risk-1")
        self.write_selection_data(request_id, missing_open_risk_pair)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn(
            "stale v4 PASS `programs-risk-1` must include exact required review "
            "`risk`/`programs-consumer`",
            result.stdout,
        )

        unrelated = copy.deepcopy(state)
        unrelated["late_shared_contract_discoveries"][0]["affected_bundle_ids"] = [
            "accounts-owner"
        ]
        self.write_selection_data(request_id, unrelated)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("must cover only its affected bundles", result.stdout)

        readiness_review = {
            "review_id": "selection-readiness-2",
            "reviewer_role": "development",
            "reviewer_agent_id": "reviewer-1",
            "basis_revision": 2,
            "verdict": "PASS",
            "status": "current",
        }
        state["selection_readiness"]["reviews"][0]["status"] = "superseded"
        state["selection_readiness"]["reviews"].append(readiness_review)
        state["operation_metrics"]["spans"].append(
            {
                "span_id": "selection-readiness-2",
                "kind": "development-review",
                "scope": "selection-readiness",
                "attempt_id": "readiness-attempt-2",
                "status": "finished",
                "started_at": "2026-07-20T08:00:03Z",
                "finished_at": "2026-07-20T08:00:04Z",
                "outcome": "PASS",
            }
        )
        closure = state["semantic_review_closure"]
        closure["review_passes"][0]["status"] = "superseded"
        closure["review_passes"].extend(
            [
                {
                    "review_id": "accounts-development-2",
                    "reviewer_role": "development",
                    "scope": "accounts-owner",
                    "basis_revision": 2,
                    "verdict": "PASS",
                    "status": "current",
                },
                {
                    "review_id": "programs-development-2",
                    "reviewer_role": "development",
                    "scope": "programs-consumer",
                    "basis_revision": 2,
                    "verdict": "PASS",
                    "status": "current",
                },
            ]
        )
        closure["invalidations"][0].update(
            {"status": "resolved", "resolved_revision": 2}
        )
        discovery = state["late_shared_contract_discoveries"][0]
        discovery.update(
            {
                "status": "resolved",
                "resolved_revision": 2,
                "resolution_readiness_review_id": "selection-readiness-2",
            }
        )
        episode = state["dispatch_control"]["episodes"][0]
        episode.update(
            {
                "status": "resolved",
                "diagnosis": "공유 권한 consumer 누락으로 queue closure가 불완전했다.",
                "action": "owner와 직접 consumer bundle만 무효화하고 재검토했다.",
                "resume_basis_revision": 2,
                "readiness_review_id": "selection-readiness-2",
            }
        )
        state["dispatch_control"]["status"] = "ready"
        self.write_selection_data(request_id, state)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        resolved_without_risk_rerun = copy.deepcopy(state)
        resolved_closure = resolved_without_risk_rerun["semantic_review_closure"]
        resolved_closure["review_passes"].append(
            {
                "review_id": "programs-risk-1",
                "reviewer_role": "risk",
                "scope": "programs-consumer",
                "basis_revision": 1,
                "verdict": "PASS",
                "status": "superseded",
            }
        )
        resolved_closure["invalidations"][0]["stale_review_ids"].append(
            "programs-risk-1"
        )
        resolved_closure["invalidations"][0]["required_reviews"].append(
            {"reviewer_role": "risk", "scope": "programs-consumer"}
        )
        self.write_selection_data(request_id, resolved_without_risk_rerun)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn(
            "is missing current PASS for `risk`/`programs-consumer`",
            result.stdout,
        )

        reversed_resolution = copy.deepcopy(state)
        reversed_resolution["semantic_review_closure"]["basis_revision"] = 3
        reversed_resolution["semantic_review_closure"]["invalidations"][0][
            "resolved_revision"
        ] = 3
        self.write_selection_data(request_id, reversed_resolution)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("resolves before linked semantic invalidation", result.stdout)

        state["selection_readiness"]["basis_revision"] = 3
        state["selection_readiness"]["reviews"][1]["status"] = "superseded"
        state["selection_readiness"]["reviews"].append(
            {
                "review_id": "selection-readiness-3",
                "reviewer_role": "development",
                "reviewer_agent_id": "reviewer-1",
                "basis_revision": 3,
                "verdict": "PASS",
                "status": "current",
            }
        )
        state["operation_metrics"]["spans"].append(
            {
                "span_id": "selection-readiness-3",
                "kind": "development-review",
                "scope": "selection-readiness",
                "attempt_id": "readiness-attempt-3",
                "status": "finished",
                "started_at": "2026-07-20T08:00:05Z",
                "finished_at": "2026-07-20T08:00:06Z",
                "outcome": "PASS",
            }
        )
        self.write_selection_data(request_id, state)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        reversed_discoveries = copy.deepcopy(state)
        reversed_discoveries["late_shared_contract_discoveries"].append(
            {
                "discovery_id": "earlier-pre-readiness-discovery",
                "contract_id": "access-policy-contract",
                "stage": "pre-readiness",
                "basis_revision": 1,
                "affected_bundle_ids": ["accounts-owner"],
                "status": "resolved",
            }
        )
        self.write_selection_data(request_id, reversed_discoveries)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("discoveries must follow basis revision order", result.stdout)

        duplicate_episode = copy.deepcopy(state)
        repeated = copy.deepcopy(duplicate_episode["dispatch_control"]["episodes"][0])
        repeated["episode_id"] = "late-access-pause-duplicate"
        duplicate_episode["dispatch_control"]["episodes"].append(repeated)
        self.write_selection_data(request_id, duplicate_episode)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("reuses `late-access-consumer`", result.stdout)

    def test_version_four_late_discovery_before_semantic_pass_needs_no_invalidation(self) -> None:
        request_id, state = self.write_v4_owner_readiness_state(
            "20260720-170005-v4-late-before-semantic-pass"
        )
        state["selection_readiness"]["basis_revision"] = 2
        state["selection_readiness"]["reviews"][0]["status"] = "stale"
        state["semantic_review_closure"]["basis_revision"] = 2
        state["late_shared_contract_discoveries"] = [
            {
                "discovery_id": "late-access-before-semantic-pass",
                "contract_id": "access-policy-contract",
                "stage": "post-readiness",
                "basis_revision": 2,
                "affected_bundle_ids": ["accounts-owner", "programs-consumer"],
                "status": "open",
                "stale_readiness_review_id": "selection-readiness-1",
                "semantic_invalidation_ids": [],
            }
        ]
        state["dispatch_control"] = {
            "version": "1",
            "status": "paused",
            "episodes": [
                {
                    "episode_id": "late-access-before-semantic-pause",
                    "cause": "late-shared-contract",
                    "trigger_ids": ["late-access-before-semantic-pass"],
                    "pause_after_span_id": "selection-readiness-1",
                    "paused_at": "2026-07-20T08:00:02Z",
                    "basis_revision": 2,
                    "status": "open",
                }
            ],
        }
        self.write_selection_data(request_id, state)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        open_dispatch = copy.deepcopy(state)
        open_dispatch["operation_metrics"]["spans"].append(
            {
                "span_id": "programs-bundle-after-late-cutoff",
                "kind": "bundle",
                "scope": "programs",
                "attempt_id": "programs-after-late-cutoff",
                "status": "finished",
                "started_at": "2026-07-20T08:00:03Z",
                "finished_at": "2026-07-20T08:00:04Z",
                "outcome": "completed",
            }
        )
        self.write_selection_data(request_id, open_dispatch)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("after its pause cutoff", result.stdout)

        moved_cutoff = copy.deepcopy(open_dispatch)
        moved_cutoff["dispatch_control"]["episodes"][0][
            "pause_after_span_id"
        ] = "programs-bundle-after-late-cutoff"
        self.write_selection_data(request_id, moved_cutoff)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("after immutable `paused_at`", result.stdout)

        unknown_cutoff = copy.deepcopy(state)
        unknown_cutoff["dispatch_control"]["episodes"][0][
            "pause_after_span_id"
        ] = "missing-cutoff-span"
        self.write_selection_data(request_id, unknown_cutoff)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("dispatch cutoff metric span does not resolve", result.stdout)

        resolved = copy.deepcopy(state)
        resolved["selection_readiness"]["reviews"][0]["status"] = "superseded"
        resolved["selection_readiness"]["reviews"].append(
            {
                "review_id": "selection-readiness-2",
                "reviewer_role": "development",
                "reviewer_agent_id": "reviewer-1",
                "basis_revision": 2,
                "verdict": "PASS",
                "status": "current",
            }
        )
        resolved["operation_metrics"]["spans"].append(
            {
                "span_id": "selection-readiness-2",
                "kind": "development-review",
                "scope": "selection-readiness",
                "attempt_id": "readiness-attempt-2",
                "status": "finished",
                "started_at": "2026-07-20T08:00:03Z",
                "finished_at": "2026-07-20T08:00:04Z",
                "outcome": "PASS",
            }
        )
        resolved["late_shared_contract_discoveries"][0].update(
            {
                "status": "resolved",
                "resolved_revision": 2,
                "resolution_readiness_review_id": "selection-readiness-2",
            }
        )
        resolved["dispatch_control"]["episodes"][0].update(
            {
                "status": "resolved",
                "diagnosis": "writer 전에 직접 consumer를 발견했다.",
                "action": "prepass와 queue를 갱신했다.",
                "resume_basis_revision": 2,
                "readiness_review_id": "selection-readiness-2",
            }
        )
        resolved["dispatch_control"]["status"] = "ready"
        self.write_selection_data(request_id, resolved)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        resolved_dispatch = copy.deepcopy(resolved)
        resolved_dispatch["operation_metrics"]["spans"].insert(
            -1,
            {
                "span_id": "programs-writer-before-late-resume",
                "kind": "writer",
                "scope": "programs",
                "attempt_id": "programs-before-late-resume",
                "status": "finished",
                "started_at": "2026-07-20T08:00:02.100Z",
                "finished_at": "2026-07-20T08:00:02.900Z",
                "outcome": "completed",
            },
        )
        self.write_selection_data(request_id, resolved_dispatch)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("after its pause cutoff", result.stdout)

        prior_pass = copy.deepcopy(state)
        prior_pass["semantic_review_closure"]["review_passes"] = [
            {
                "review_id": "accounts-development-1",
                "reviewer_role": "development",
                "scope": "accounts-owner",
                "basis_revision": 1,
                "verdict": "PASS",
                "status": "stale",
            }
        ]
        self.write_selection_data(request_id, prior_pass)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("because an affected prior PASS exists", result.stdout)

    def test_version_four_late_invalidation_preserves_same_domain_bundle_identity(self) -> None:
        request_id, state = self.write_v4_owner_readiness_state(
            "20260720-170006-v4-same-domain-shards"
        )
        state["accepted_scope"] = ["accounts"]
        state["context_selection"]["candidates"][1]["domain"] = "accounts"
        state["bundle_queue"][1]["domain"] = "accounts"
        state["selection_readiness"]["basis_revision"] = 2
        state["selection_readiness"]["reviews"][0]["status"] = "stale"
        state["semantic_review_closure"] = {
            "version": "1",
            "basis_revision": 2,
            "review_passes": [
                {
                    "review_id": "accounts-owner-development-1",
                    "reviewer_role": "development",
                    "scope": "accounts-owner",
                    "basis_revision": 1,
                    "verdict": "PASS",
                    "status": "stale",
                }
            ],
            "invalidations": [
                {
                    "invalidation_id": "late-owner-only-1",
                    "trigger": "ownership",
                    "cause": "같은 domain의 owner shard 근거만 바뀌었다.",
                    "opened_revision": 2,
                    "affected_artifacts": [
                        {"location": "request", "path": "inventory.md"}
                    ],
                    "affected_bundles": ["accounts-owner"],
                    "stale_review_ids": ["accounts-owner-development-1"],
                    "required_reviews": [
                        {
                            "reviewer_role": "development",
                            "scope": "accounts-owner",
                        }
                    ],
                    "status": "open",
                }
            ],
            "final_gate": {"required": False, "review_history": []},
        }
        state["late_shared_contract_discoveries"] = [
            {
                "discovery_id": "late-owner-only",
                "contract_id": "access-policy-contract",
                "stage": "post-readiness",
                "basis_revision": 2,
                "affected_bundle_ids": ["accounts-owner"],
                "status": "open",
                "stale_readiness_review_id": "selection-readiness-1",
                "semantic_invalidation_ids": ["late-owner-only-1"],
            }
        ]
        state["dispatch_control"] = {
            "version": "1",
            "status": "paused",
            "episodes": [
                {
                    "episode_id": "late-owner-only-pause",
                    "cause": "late-shared-contract",
                    "trigger_ids": ["late-owner-only"],
                    "pause_after_span_id": "selection-readiness-1",
                    "paused_at": "2026-07-20T08:00:02Z",
                    "basis_revision": 2,
                    "status": "open",
                }
            ],
        }
        self.write_selection_data(request_id, state)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        sibling_included = copy.deepcopy(state)
        sibling_included["semantic_review_closure"]["invalidations"][0][
            "affected_bundles"
        ].append("programs-consumer")
        self.write_selection_data(request_id, sibling_included)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("must cover only its affected bundles", result.stdout)

    def test_request_bound_phases_reject_non_v4_operation_state(self) -> None:
        self.write_atom("domain/domain-context-atom.md", "domain-context")
        self.write_baseline()
        for version in (None, "1", "2", "3", " 4 "):
            label = (
                "unversioned"
                if version is None
                else "padded-v4"
                if version == " 4 "
                else f"v{version}"
            )
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
                request_id=f"20260720-180100-request-bound-{label}",
                selection_version=version,
            )
            for phase in (
                "selection",
                "docs",
                "baseline",
                "metrics-preterminal",
                "metrics-final",
            ):
                with self.subTest(version=version, phase=phase):
                    result = self.run_validator(phase, request_id=request_id)
                    self.assertEqual(1, result.returncode)
                    self.assertIn(
                        "`context_selection.version` must be exact `4`",
                        result.stdout,
                    )

    def test_operation_metrics_final_fail_retry_and_terminal_sequence(self) -> None:
        self.write_atom("domain/domain-context-atom.md", "domain-context")
        self.write_baseline("partial")
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
            request_id="20260716-090001-final-metrics",
        )
        state = self.read_selection_state(request_id)
        readiness_span = copy.deepcopy(state["operation_metrics"]["spans"][0])
        readiness_span.update(
            {
                "started_at": "2026-07-16T09:00:01+09:00",
                "finished_at": "2026-07-16T09:00:02+09:00",
            }
        )
        state["semantic_review_closure"] = {
            "version": "1",
            "basis_revision": 1,
            "review_passes": [
                {
                    "review_id": "domain-development-1",
                    "reviewer_role": "development",
                    "scope": "domain-bundle",
                    "basis_revision": 1,
                    "verdict": "PASS",
                    "status": "current",
                },
                {
                    "review_id": "project-baseline-1",
                    "reviewer_role": "baseline",
                    "scope": "project-wide",
                    "basis_revision": 1,
                    "verdict": "PASS",
                    "status": "current",
                },
            ],
            "invalidations": [],
            "final_gate": {
                "required": True,
                "review_history": ["project-baseline-1"],
                "review_id": "project-baseline-1",
            },
        }
        state["operation_metrics"] = {
            "version": "1",
            "status": "active",
            "started_at": "2026-07-16T09:00:00+09:00",
            "spans": [
                readiness_span,
                {
                    "span_id": "domain-bundle-1",
                    "kind": "bundle",
                    "scope": "domain",
                    "attempt_id": "domain-attempt-1",
                    "status": "finished",
                    "started_at": "2026-07-16T09:01:00+09:00",
                    "finished_at": "2026-07-16T09:05:00+09:00",
                    "outcome": "completed",
                },
                {
                    "span_id": "domain-writer-1",
                    "kind": "writer",
                    "scope": "domain",
                    "attempt_id": "domain-attempt-1",
                    "status": "finished",
                    "started_at": "2026-07-16T09:02:00+09:00",
                    "finished_at": "2026-07-16T09:05:00+09:00",
                    "outcome": "completed",
                },
                {
                    "span_id": "domain-development-1",
                    "kind": "development-review",
                    "scope": "domain-bundle",
                    "attempt_id": "domain-attempt-1",
                    "status": "finished",
                    "started_at": "2026-07-16T09:06:00+09:00",
                    "finished_at": "2026-07-16T09:09:00+09:00",
                    "outcome": "PASS",
                },
                {
                    "span_id": "project-baseline-1",
                    "kind": "baseline-review",
                    "scope": "project-wide",
                    "attempt_id": "baseline-attempt-1",
                    "status": "finished",
                    "started_at": "2026-07-16T09:10:00+09:00",
                    "finished_at": "2026-07-16T09:20:00+09:00",
                    "outcome": "PASS",
                },
                {
                    "span_id": "baseline-validation-1",
                    "kind": "validation",
                    "scope": "baseline",
                    "attempt_id": "baseline-validation-attempt-1",
                    "status": "active",
                    "started_at": "2026-07-16T09:21:00+09:00",
                },
            ],
        }
        self.write_selection_data(request_id, state)

        docs_only = copy.deepcopy(state)
        docs_validation = docs_only["operation_metrics"]["spans"][-1]
        docs_validation["scope"] = "docs"
        docs_validation["attempt_id"] = "docs-validation-attempt-1"
        self.write_selection_data(request_id, docs_only)
        result = self.run_validator("docs", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("operation requires final `baseline` validation", result.stdout)

        docs_validation.update(
            {
                "status": "finished",
                "finished_at": "2026-07-16T09:22:00+09:00",
                "outcome": "PASS",
            }
        )
        self.write_selection_data(request_id, docs_only)
        result = self.run_validator("metrics-preterminal", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("requires final `baseline` validation", result.stdout)
        self.assertIn("partial baselines are invalid", result.stdout)

        self.write_selection_data(request_id, state)
        result = self.run_validator("baseline", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("partial baselines are invalid", result.stdout)

        first_validation = state["operation_metrics"]["spans"][-1]
        first_validation.update(
            {
                "status": "finished",
                "finished_at": "2026-07-16T09:22:00+09:00",
                "outcome": "FAIL",
            }
        )
        self.write_selection_data(request_id, state)
        result = self.run_validator("metrics-preterminal", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("latest final validation span to have outcome `PASS`", result.stdout)

        self.write_baseline()
        state["operation_metrics"]["spans"].extend(
            [
                {
                    "span_id": "domain-correction-1",
                    "kind": "writer",
                    "scope": "domain",
                    "attempt_id": "domain-attempt-2",
                    "status": "finished",
                    "started_at": "2026-07-16T09:23:00+09:00",
                    "finished_at": "2026-07-16T09:25:00+09:00",
                    "outcome": "completed",
                },
                {
                    "span_id": "baseline-validation-2",
                    "kind": "validation",
                    "scope": "baseline",
                    "attempt_id": "baseline-validation-attempt-2",
                    "status": "active",
                    "started_at": "2026-07-16T09:26:00+09:00",
                    "rerun_of": "baseline-validation-1",
                    "rerun_reason": "이전 검증 실패를 수정한 뒤 다시 확인한다.",
                },
            ]
        )
        self.write_selection_data(request_id, state)
        result = self.run_validator("baseline", request_id=request_id)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        second_validation = state["operation_metrics"]["spans"][-1]
        second_validation.update(
            {
                "status": "finished",
                "finished_at": "2026-07-16T09:27:00+09:00",
                "outcome": "PASS",
            }
        )
        stale_closure_state = copy.deepcopy(state)
        stale_closure = stale_closure_state["semantic_review_closure"]
        stale_closure["basis_revision"] = 2
        stale_closure["review_passes"][0]["status"] = "stale"
        stale_closure["invalidations"] = [
            {
                "invalidation_id": "late-meaning-change-1",
                "trigger": "documented-meaning",
                "cause": "최종 검증 뒤 문서 의미가 바뀌었다.",
                "opened_revision": 2,
                "affected_artifacts": [
                    {"location": "managed-docs", "path": "domain/domain-context-atom.md"}
                ],
                "affected_bundles": ["domain-bundle"],
                "stale_review_ids": ["domain-development-1"],
                "required_reviews": [
                    {
                        "reviewer_role": "development",
                        "scope": "domain-bundle",
                    }
                ],
                "status": "open",
            }
        ]
        self.write_selection_data(request_id, stale_closure_state)
        result = self.run_validator("metrics-preterminal", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("is still open at final validation", result.stdout)

        self.write_selection_data(request_id, state)
        result = self.run_validator("metrics-preterminal", request_id=request_id)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        stale_state = copy.deepcopy(state)
        stale_state["operation_metrics"]["spans"].append(
            {
                "span_id": "late-writer-1",
                "kind": "writer",
                "scope": "domain",
                "attempt_id": "domain-attempt-3",
                "status": "finished",
                "started_at": "2026-07-16T09:27:10+09:00",
                "finished_at": "2026-07-16T09:27:20+09:00",
                "outcome": "completed",
            }
        )
        self.write_selection_data(request_id, stale_state)
        result = self.run_validator("metrics-preterminal", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("to be the last recorded span", result.stdout)
        self.write_selection_data(request_id, state)

        state["operation_metrics"].update(
            {
                "status": "finished",
                "finished_at": "2026-07-16T09:28:00+09:00",
            }
        )
        self.write_selection_data(request_id, state)
        result = self.run_validator("metrics-final", request_id=request_id)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_operation_metrics_final_requires_queue_and_review_coverage(self) -> None:
        self.write_atom("domain/domain-context-atom.md", "domain-context")
        self.write_baseline()
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
            risk_triggers=[
                {
                    "candidate_id": "domain-context",
                    "atom_key": "domain-context",
                    "triggers": ["shared policy contract"],
                    "basis": "선택된 공유 계약이 변경 영향에 중요하다.",
                }
            ],
            request_id="20260716-090003-missing-metric-coverage",
        )
        state = self.read_selection_state(request_id)
        readiness_span = copy.deepcopy(state["operation_metrics"]["spans"][0])
        readiness_span.update(
            {
                "started_at": "2026-07-16T09:00:01+09:00",
                "finished_at": "2026-07-16T09:00:02+09:00",
            }
        )
        state["semantic_review_closure"] = {
            "version": "1",
            "basis_revision": 1,
            "review_passes": [
                {
                    "review_id": "domain-development-1",
                    "reviewer_role": "development",
                    "scope": "domain-bundle",
                    "basis_revision": 1,
                    "verdict": "PASS",
                    "status": "current",
                },
                {
                    "review_id": "project-baseline-1",
                    "reviewer_role": "baseline",
                    "scope": "project-wide",
                    "basis_revision": 1,
                    "verdict": "PASS",
                    "status": "current",
                },
            ],
            "invalidations": [],
            "final_gate": {
                "required": True,
                "review_history": ["project-baseline-1"],
                "review_id": "project-baseline-1",
            },
        }
        state["operation_metrics"] = {
            "version": "1",
            "status": "active",
            "started_at": "2026-07-16T09:00:00+09:00",
            "spans": [
                readiness_span,
                {
                    "span_id": "baseline-validation-1",
                    "kind": "validation",
                    "scope": "baseline",
                    "attempt_id": "baseline-validation-attempt-1",
                    "status": "active",
                    "started_at": "2026-07-16T09:10:00+09:00",
                }
            ],
        }
        self.write_selection_data(request_id, state)
        result = self.run_validator("baseline", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("completed bundle/writer attempt", result.stdout)
        self.assertIn(
            "current semantic review PASS `domain-development-1`", result.stdout
        )
        self.assertIn(
            "current semantic review PASS `project-baseline-1`", result.stdout
        )
        self.assertIn("needs a finished risk-review metric span", result.stdout)

    def test_operation_metrics_rejects_invalid_shape_and_time_order(self) -> None:
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
            request_id="20260716-090002-invalid-metrics",
        )
        state = self.read_selection_state(request_id)
        state["semantic_review_closure"] = {
            "version": "1",
            "basis_revision": 1,
            "review_passes": [],
            "invalidations": [],
            "final_gate": {"required": False, "review_history": []},
        }
        state["operation_metrics"] = {
            "version": "1",
            "status": "active",
            "started_at": "2026-07-16 09:00:00+09:00",
            "spans": [
                {
                    "span_id": "invalid-active-span",
                    "kind": "writer",
                    "scope": "domain",
                    "attempt_id": "domain-attempt-1",
                    "status": "active",
                    "started_at": "2026-07-16T09:10:00+09:00",
                    "finished_at": "2026-07-16T09:09:00+09:00",
                    "outcome": "PASS",
                    "rerun_of": "missing-span",
                },
                {
                    "span_id": "reversed-finished-span",
                    "kind": "writer",
                    "scope": "domain",
                    "attempt_id": "domain-attempt-2",
                    "status": "finished",
                    "started_at": "2026-07-16T09:12:00+09:00",
                    "finished_at": "2026-07-16T09:11:00+09:00",
                    "outcome": "completed",
                },
                {
                    "span_id": "instrumented-terminal-check",
                    "kind": "validation",
                    "scope": "metrics-preterminal",
                    "attempt_id": "terminal-attempt-1",
                    "status": "finished",
                    "started_at": "2026-07-16T09:13:00+09:00",
                    "finished_at": "2026-07-16T09:14:00+09:00",
                    "outcome": "PASS",
                }
            ],
        }
        self.write_selection_data(request_id, state)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("must be RFC 3339 with a timezone", result.stdout)
        self.assertIn("must omit `finished_at` and `outcome`", result.stdout)
        self.assertIn("`finished_at` must not precede `started_at`", result.stdout)
        self.assertIn("must set `rerun_of` and `rerun_reason` together", result.stdout)
        self.assertIn("must reference an earlier span", result.stdout)
        self.assertIn("must not instrument a terminal metrics check", result.stdout)

    def test_operation_metrics_snapshot_progression_is_append_only(self) -> None:
        _, snapshot = self.write_v4_owner_readiness_state(
            "20260720-180101-v4-metrics-progression"
        )
        snapshot["operation_metrics"]["spans"].append(
            {
                "span_id": "accounts-writer-1",
                "kind": "writer",
                "scope": "accounts",
                "attempt_id": "accounts-attempt-1",
                "status": "finished",
                "started_at": "2026-07-20T08:00:03Z",
                "finished_at": "2026-07-20T08:00:04Z",
                "outcome": "completed",
            }
        )
        current = copy.deepcopy(snapshot)
        current["operation_metrics"]["spans"].append(
            {
                "span_id": "accounts-development-1",
                "kind": "development-review",
                "scope": "accounts-owner",
                "attempt_id": "accounts-attempt-1",
                "status": "finished",
                "started_at": "2026-07-20T08:00:05Z",
                "finished_at": "2026-07-20T08:00:06Z",
                "outcome": "PASS",
            }
        )
        errors: list[str] = []
        validate_state_snapshot_completeness(snapshot, current, "snapshot", errors)
        self.assertEqual([], errors)

        changed = copy.deepcopy(current)
        changed["operation_metrics"]["spans"][0]["outcome"] = "FAIL"
        errors = []
        validate_state_snapshot_completeness(snapshot, changed, "snapshot", errors)
        self.assertTrue(
            any("rewrites finished operation metric span" in error for error in errors),
            errors,
        )

        shortened = copy.deepcopy(snapshot)
        shortened["operation_metrics"]["spans"] = []
        errors = []
        validate_state_snapshot_completeness(snapshot, shortened, "snapshot", errors)
        self.assertTrue(
            any("removes or reorders operation metric spans" in error for error in errors),
            errors,
        )

    def test_version_four_snapshot_keeps_owner_readiness_history_complete(self) -> None:
        request_id, state = self.write_v4_owner_readiness_state(
            "20260720-170003-v4-snapshot"
        )
        errors: list[str] = []
        validate_state_snapshot_completeness(
            copy.deepcopy(state), state, "snapshot", errors
        )
        self.assertEqual([], errors)

        incomplete = copy.deepcopy(state)
        del incomplete["shared_contracts"]
        errors = []
        validate_state_snapshot_completeness(incomplete, state, "snapshot", errors)
        self.assertTrue(
            any("missing current field(s): shared_contracts" in error for error in errors)
        )

        reversed_history = copy.deepcopy(state)
        reversed_history["selection_readiness"]["reviews"][0]["status"] = (
            "superseded"
        )
        errors = []
        validate_state_snapshot_completeness(
            reversed_history, state, "snapshot", errors
        )
        self.assertTrue(
            any("reverses readiness review" in error for error in errors), errors
        )

        reordered = copy.deepcopy(state)
        reordered["selection_readiness"]["basis_revision"] = 2
        reordered["selection_readiness"]["reviews"][0]["status"] = "superseded"
        reordered["selection_readiness"]["reviews"].insert(
            0,
            {
                "review_id": "selection-readiness-2",
                "reviewer_role": "development",
                "reviewer_agent_id": "reviewer-1",
                "basis_revision": 2,
                "verdict": "PASS",
                "status": "current",
            },
        )
        reordered["operation_metrics"]["spans"].append(
            {
                "span_id": "selection-readiness-2",
                "kind": "development-review",
                "scope": "selection-readiness",
                "attempt_id": "readiness-attempt-2",
                "status": "finished",
                "started_at": "2026-07-20T08:00:03Z",
                "finished_at": "2026-07-20T08:00:04Z",
                "outcome": "PASS",
            }
        )
        errors = []
        validate_state_snapshot_completeness(state, reordered, "snapshot", errors)
        self.assertTrue(any("readiness reviews must be append-only" in error for error in errors))
        self.write_selection_data(request_id, reordered)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("must follow basis revision order", result.stdout)
        self.assertIn("must follow metric span order", result.stdout)

        non_v4_snapshot = copy.deepcopy(state)
        non_v4_snapshot["context_selection"]["version"] = "3"
        errors = []
        validate_state_snapshot_completeness(
            non_v4_snapshot, state, "snapshot", errors
        )
        self.assertEqual(
            [
                "snapshot operation-state rollback requires "
                "context selection version `4`"
            ],
            errors,
        )

    def test_version_four_snapshot_guard_maps_path_to_exact_same_domain_bundle(self) -> None:
        _, state = self.write_v4_owner_readiness_state(
            "20260720-170007-v4-snapshot-bundle-guard"
        )
        state["accepted_scope"] = ["accounts"]
        state["context_selection"]["candidates"][1]["domain"] = "accounts"
        state["bundle_queue"][1]["domain"] = "accounts"
        guarded_path = "accounts/access-policy-atom.md"
        state["operation_created_artifacts"] = [
            {
                "candidate_id": "access-policy",
                "atom_key": "access-policy",
                "path": guarded_path,
                "created_attempt_id": "accounts-attempt-1",
                "last_operation_sha256": "a" * 64,
                "status": "present",
            }
        ]
        state["semantic_review_closure"] = {
            "version": "1",
            "basis_revision": 1,
            "review_passes": [
                {
                    "review_id": "accounts-owner-development-1",
                    "reviewer_role": "development",
                    "scope": "accounts-owner",
                    "basis_revision": 1,
                    "verdict": "PASS",
                    "status": "current",
                },
                {
                    "review_id": "accounts-sibling-development-1",
                    "reviewer_role": "development",
                    "scope": "programs-consumer",
                    "basis_revision": 1,
                    "verdict": "PASS",
                    "status": "current",
                },
            ],
            "invalidations": [],
            "final_gate": {"required": False, "review_history": []},
        }
        errors: list[str] = []
        validate_state_snapshot_completeness(
            state,
            state,
            "snapshot",
            errors,
            active_semantic_paths={guarded_path},
        )
        joined = "\n".join(errors)
        self.assertIn("accounts-owner-development-1", joined)
        self.assertNotIn("accounts-sibling-development-1", joined)

        risk_only = copy.deepcopy(state)
        risk_only["semantic_review_closure"]["review_passes"][0].update(
            {
                "review_id": "accounts-owner-risk-1",
                "reviewer_role": "risk",
            }
        )
        errors = []
        validate_state_snapshot_completeness(
            risk_only,
            risk_only,
            "snapshot",
            errors,
            active_semantic_paths={guarded_path},
        )
        joined = "\n".join(errors)
        self.assertIn("accounts-owner-risk-1", joined)
        self.assertNotIn("accounts-sibling-development-1", joined)

        approved_source = copy.deepcopy(state)
        approved_source["operation_created_artifacts"] = []
        legacy_path = "accounts/legacy-access-policy-atom.md"
        approved_source["approved_existing_actions"] = [
            {
                "source": {
                    "atom_key": "legacy-access-policy",
                    "path": legacy_path,
                }
            }
        ]
        errors = []
        validate_state_snapshot_completeness(
            approved_source,
            approved_source,
            "snapshot",
            errors,
            active_semantic_paths={legacy_path},
        )
        self.assertFalse(
            any("cannot map guarded v4 path" in error for error in errors), errors
        )

        guarded = copy.deepcopy(state)
        guarded["semantic_review_closure"]["basis_revision"] = 2
        guarded["semantic_review_closure"]["review_passes"][0]["status"] = "stale"
        guarded["semantic_review_closure"]["invalidations"] = [
            {
                "invalidation_id": "accounts-owner-drop-1",
                "trigger": "ownership",
                "cause": "owner bundle drop 전에 PASS를 무효화했다.",
                "opened_revision": 2,
                "affected_artifacts": [
                    {"location": "managed-docs", "path": guarded_path}
                ],
                "affected_bundles": ["accounts-owner"],
                "stale_review_ids": ["accounts-owner-development-1"],
                "required_reviews": [
                    {"reviewer_role": "development", "scope": "accounts-owner"}
                ],
                "status": "open",
            }
        ]
        errors = []
        validate_state_snapshot_completeness(
            guarded,
            guarded,
            "snapshot",
            errors,
            active_semantic_paths={guarded_path},
        )
        self.assertEqual([], errors)

        wrong_shard = copy.deepcopy(guarded)
        invalidation = wrong_shard["semantic_review_closure"]["invalidations"][0]
        invalidation["affected_bundles"] = ["programs-consumer"]
        invalidation["required_reviews"][0]["scope"] = "programs-consumer"
        errors = []
        validate_state_snapshot_completeness(
            wrong_shard,
            wrong_shard,
            "snapshot",
            errors,
            active_semantic_paths={guarded_path},
        )
        self.assertTrue(
            any("lacks an open pre-mutation invalidation" in error for error in errors),
            errors,
        )

    def test_version_four_local_bundle_drop_retires_identity_through_final(self) -> None:
        request_id, state = self.write_v4_owner_readiness_state(
            "20260720-170008-v4-local-retirement"
        )
        atom = self.write_atom("accounts/access-policy-atom.md", "access-policy")
        state["accepted_scope"] = ["accounts"]
        state["context_selection"]["candidates"][1]["domain"] = "accounts"
        active_bundle = copy.deepcopy(state["bundle_queue"][0])
        state["bundle_queue"][1]["domain"] = "accounts"
        state["bundle_queue"][1]["depends_on_contract_ids"] = []
        sibling_bundle = copy.deepcopy(state["bundle_queue"][1])
        state["risk_triggers"] = [
            {
                "candidate_id": "access-policy",
                "atom_key": "access-policy",
                "triggers": ["local permission decision"],
                "basis": "단일 bundle 안에서 판단한다.",
                "route": "local",
            },
            {
                "candidate_id": "program-access",
                "atom_key": "program-access",
                "triggers": ["local sibling decision"],
                "basis": "같은 domain의 별도 shard 안에서 판단한다.",
                "route": "local",
            },
        ]
        state["shared_contracts"] = []
        guarded_path = "accounts/access-policy-atom.md"
        state["operation_created_artifacts"] = [
            {
                "candidate_id": "access-policy",
                "atom_key": "access-policy",
                "path": guarded_path,
                "created_attempt_id": "accounts-attempt-1",
                "last_operation_sha256": self.file_sha256(atom),
                "status": "present",
            }
        ]
        state["semantic_review_closure"] = {
            "version": "1",
            "basis_revision": 2,
            "review_passes": [
                {
                    "review_id": "accounts-owner-development-1",
                    "reviewer_role": "development",
                    "scope": "accounts-owner",
                    "basis_revision": 1,
                    "verdict": "PASS",
                    "status": "stale",
                },
                {
                    "review_id": "accounts-sibling-development-1",
                    "reviewer_role": "development",
                    "scope": "programs-consumer",
                    "basis_revision": 1,
                    "verdict": "PASS",
                    "status": "current",
                },
            ],
            "invalidations": [
                {
                    "invalidation_id": "accounts-owner-drop-1",
                    "trigger": "candidate-disposition",
                    "cause": "local 후보를 drop하기 전에 기존 PASS를 무효화했다.",
                    "opened_revision": 2,
                    "affected_artifacts": [
                        {"location": "managed-docs", "path": guarded_path},
                        {"location": "request", "path": "inventory.md"},
                    ],
                    "affected_bundles": ["accounts-owner"],
                    "stale_review_ids": ["accounts-owner-development-1"],
                    "required_reviews": [
                        {
                            "reviewer_role": "development",
                            "scope": "accounts-owner",
                        }
                    ],
                    "status": "open",
                }
            ],
            "final_gate": {"required": False, "review_history": []},
        }
        self.write_selection_data(request_id, state)
        rollback = self.selection_request_root(request_id) / "rollback" / "access-policy.md"
        rollback.parent.mkdir(parents=True)
        rollback.write_bytes(atom.read_bytes())
        _, state_backup_hash = self.write_state_rollback(
            request_id,
            "rollback/access-policy-work-state.json",
            state,
        )

        current = copy.deepcopy(state)
        current["context_selection"]["candidates"][0] = {
            "candidate_id": "access-policy",
            "domain": "accounts",
            "candidate": "공유 접근 정책",
            "disposition": "drop",
            "selection_basis": "검토 결과 source-local detail로 재분류했다.",
        }
        current["bundle_queue"] = [sibling_bundle]
        current["risk_triggers"] = [copy.deepcopy(state["risk_triggers"][1])]
        current["selection_retirements"]["retired_bundles"] = [
            {
                **active_bundle,
                "retired_basis_revision": 2,
                "reason": "candidate drop removed the bundle's last write key",
            }
        ]
        current["selection_readiness"]["basis_revision"] = 2
        current["selection_readiness"]["reviews"][0]["status"] = "superseded"
        current["selection_readiness"]["reviews"].append(
            {
                "review_id": "selection-readiness-2",
                "reviewer_role": "development",
                "reviewer_agent_id": "reviewer-1",
                "basis_revision": 2,
                "verdict": "PASS",
                "status": "current",
            }
        )
        current["operation_metrics"]["spans"].append(
            {
                "span_id": "selection-readiness-2",
                "kind": "development-review",
                "scope": "selection-readiness",
                "attempt_id": "readiness-attempt-2",
                "status": "finished",
                "started_at": "2026-07-20T08:00:03Z",
                "finished_at": "2026-07-20T08:00:04Z",
                "outcome": "PASS",
            }
        )
        current["operation_created_artifacts"][0].update(
            {
                "status": "removal_pending",
                "rollback_path": "rollback/access-policy.md",
                "state_rollback_path": "rollback/access-policy-work-state.json",
                "state_rollback_sha256": state_backup_hash,
            }
        )
        (self.selection_request_root(request_id) / "inventory.md").write_text(
            "# 후보\n\n- `access-policy`: 검토 결과 drop\n", encoding="utf-8"
        )
        self.write_selection_data(request_id, current)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        same_basis_retirement = copy.deepcopy(current)
        same_basis_retirement["selection_retirements"]["retired_bundles"][0][
            "retired_basis_revision"
        ] = 1
        self.write_selection_data(request_id, same_basis_retirement)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("must advance beyond the snapshot readiness basis", result.stdout)

        mismatched_invalidation_basis = copy.deepcopy(current)
        retirement = mismatched_invalidation_basis["selection_retirements"][
            "retired_bundles"
        ][0]
        retirement["retired_basis_revision"] = 3
        readiness = mismatched_invalidation_basis["selection_readiness"]
        readiness["basis_revision"] = 3
        readiness["reviews"][1]["review_id"] = "selection-readiness-3"
        readiness["reviews"][1]["basis_revision"] = 3
        readiness_metric = mismatched_invalidation_basis["operation_metrics"]["spans"][-1]
        readiness_metric["span_id"] = "selection-readiness-3"
        self.write_selection_data(request_id, mismatched_invalidation_basis)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn(
            "needs snapshot open invalidation for prior PASS "
            "`accounts-owner-development-1`",
            result.stdout,
        )

        missing_retirement = copy.deepcopy(current)
        missing_retirement["selection_retirements"]["retired_bundles"] = []
        self.write_selection_data(request_id, missing_retirement)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("without an append-only retirement record", result.stdout)

        forged_retirement = copy.deepcopy(current)
        forged_retirement["selection_retirements"]["retired_bundles"][0][
            "domain"
        ] = "forged-domain"
        self.write_selection_data(request_id, forged_retirement)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("forged retired bundle", result.stdout)

        atom.unlink()
        current["operation_created_artifacts"][0]["status"] = "removed"
        current["semantic_review_closure"]["review_passes"][0]["status"] = (
            "superseded"
        )
        current["semantic_review_closure"]["review_passes"].append(
            {
                "review_id": "accounts-owner-development-2",
                "reviewer_role": "development",
                "scope": "accounts-owner",
                "basis_revision": 2,
                "verdict": "PASS",
                "status": "current",
            }
        )
        current["semantic_review_closure"]["invalidations"][0].update(
            {"status": "resolved", "resolved_revision": 2}
        )
        self.write_selection_data(request_id, current)
        result = self.run_validator(
            "selection", request_id=request_id, require_actions_final=True
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        rewritten_snapshot = copy.deepcopy(current)
        rewritten_snapshot["selection_retirements"]["retired_bundles"][0][
            "reason"
        ] = "rewritten"
        errors: list[str] = []
        validate_state_snapshot_completeness(
            current,
            rewritten_snapshot,
            "snapshot",
            errors,
        )
        self.assertTrue(
            any("rewrites retired bundle" in error for error in errors), errors
        )

    def test_version_four_shared_contract_retirement_preserves_history_only(self) -> None:
        request_id, state = self.write_v4_owner_readiness_state(
            "20260720-170009-v4-contract-retirement"
        )
        atom = self.write_atom("accounts/access-policy-atom.md", "access-policy")
        active_owner_bundle = copy.deepcopy(state["bundle_queue"][0])
        active_contract = copy.deepcopy(state["shared_contracts"][0])
        guarded_path = "accounts/access-policy-atom.md"
        state["operation_created_artifacts"] = [
            {
                "candidate_id": "access-policy",
                "atom_key": "access-policy",
                "path": guarded_path,
                "created_attempt_id": "accounts-attempt-1",
                "last_operation_sha256": self.file_sha256(atom),
                "status": "present",
            }
        ]
        state["operation_metrics"]["spans"].append(
            {
                "span_id": "accounts-risk-history-fail-1",
                "kind": "risk-review",
                "scope": "accounts-owner",
                "attempt_id": "accounts-risk-history-attempt-1",
                "status": "finished",
                "started_at": "2026-07-20T08:00:03Z",
                "finished_at": "2026-07-20T08:00:04Z",
                "outcome": "FAIL",
            }
        )
        state["semantic_fail_diagnostics"] = [
            {
                "diagnostic_id": "accounts-contract-history-fail",
                "review_span_id": "accounts-risk-history-fail-1",
                "first_attempt": True,
                "root_category": "owner-evidence",
                "candidate_ids": ["access-policy"],
                "contract_ids": ["access-policy-contract"],
                "basis_revision": 1,
            }
        ]
        state["late_shared_contract_discoveries"] = [
            {
                "discovery_id": "historical-access-prepass",
                "contract_id": "access-policy-contract",
                "stage": "pre-readiness",
                "basis_revision": 1,
                "affected_bundle_ids": ["accounts-owner"],
                "status": "resolved",
            }
        ]
        self.write_selection_data(request_id, state)
        rollback = self.selection_request_root(request_id) / "rollback" / "shared-access.md"
        rollback.parent.mkdir(parents=True)
        rollback.write_bytes(atom.read_bytes())
        _, state_backup_hash = self.write_state_rollback(
            request_id,
            "rollback/shared-access-work-state.json",
            state,
        )

        current = copy.deepcopy(state)
        current["context_selection"]["candidates"][0] = {
            "candidate_id": "access-policy",
            "domain": "accounts",
            "candidate": "공유 접근 정책",
            "disposition": "drop",
            "selection_basis": "공유 owner 후보를 제거하기로 검토했다.",
        }
        current["bundle_queue"] = [copy.deepcopy(current["bundle_queue"][1])]
        current["bundle_queue"][0]["depends_on_contract_ids"] = []
        current["risk_triggers"] = [copy.deepcopy(state["risk_triggers"][2])]
        current["shared_contracts"] = []
        current["selection_retirements"]["retired_bundles"] = [
            {
                **active_owner_bundle,
                "retired_basis_revision": 2,
                "reason": "owner candidate drop retired its last-key bundle",
            }
        ]
        current["selection_retirements"]["retired_contracts"] = [
            {
                **active_contract,
                "retired_basis_revision": 2,
                "reason": "owner candidate drop retired the shared contract",
            }
        ]
        current["selection_readiness"]["basis_revision"] = 2
        current["selection_readiness"]["reviews"][0]["status"] = "superseded"
        current["selection_readiness"]["reviews"].append(
            {
                "review_id": "selection-readiness-2",
                "reviewer_role": "development",
                "reviewer_agent_id": "reviewer-1",
                "basis_revision": 2,
                "verdict": "PASS",
                "status": "current",
            }
        )
        current["operation_metrics"]["spans"].append(
            {
                "span_id": "selection-readiness-2",
                "kind": "development-review",
                "scope": "selection-readiness",
                "attempt_id": "readiness-attempt-2",
                "status": "finished",
                "started_at": "2026-07-20T08:00:05Z",
                "finished_at": "2026-07-20T08:00:06Z",
                "outcome": "PASS",
            }
        )
        current["semantic_review_closure"]["basis_revision"] = 2
        current["operation_created_artifacts"][0].update(
            {
                "status": "removal_pending",
                "rollback_path": "rollback/shared-access.md",
                "state_rollback_path": "rollback/shared-access-work-state.json",
                "state_rollback_sha256": state_backup_hash,
            }
        )
        (self.selection_request_root(request_id) / "inventory.md").write_text(
            "# 후보\n\n- `access-policy`: 검토 결과 drop\n", encoding="utf-8"
        )
        self.write_selection_data(request_id, current)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        uninvalidated_history = copy.deepcopy(current)
        uninvalidated_history["semantic_review_closure"] = {
            "version": "1",
            "basis_revision": 2,
            "review_passes": [
                {
                    "review_id": "accounts-owner-development-1",
                    "reviewer_role": "development",
                    "scope": "accounts-owner",
                    "basis_revision": 1,
                    "verdict": "PASS",
                    "status": "current",
                },
                {
                    "review_id": "programs-consumer-risk-1",
                    "reviewer_role": "risk",
                    "scope": "programs-consumer",
                    "basis_revision": 1,
                    "verdict": "PASS",
                    "status": "current",
                },
            ],
            "invalidations": [],
            "final_gate": {"required": False, "review_history": []},
        }
        self.write_selection_data(request_id, uninvalidated_history)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("needs invalidation opened at retirement basis 2", result.stdout)
        self.assertIn("`accounts-owner-development-1`", result.stdout)
        self.assertIn("`programs-consumer-risk-1`", result.stdout)

        later_superseded_history = copy.deepcopy(current)
        later_superseded_history["semantic_review_closure"] = {
            "version": "1",
            "basis_revision": 3,
            "review_passes": [
                {
                    "review_id": "accounts-owner-development-1",
                    "reviewer_role": "development",
                    "scope": "accounts-owner",
                    "basis_revision": 1,
                    "verdict": "PASS",
                    "status": "superseded",
                },
                {
                    "review_id": "accounts-owner-development-3",
                    "reviewer_role": "development",
                    "scope": "accounts-owner",
                    "basis_revision": 3,
                    "verdict": "PASS",
                    "status": "current",
                },
            ],
            "invalidations": [
                {
                    "invalidation_id": "unrelated-later-correction-3",
                    "trigger": "documented-meaning",
                    "cause": "retirement 뒤의 별도 변경으로 이전 PASS를 교체했다.",
                    "opened_revision": 3,
                    "affected_artifacts": [
                        {"location": "request", "path": "inventory.md"}
                    ],
                    "affected_bundles": ["accounts-owner"],
                    "stale_review_ids": ["accounts-owner-development-1"],
                    "required_reviews": [
                        {"reviewer_role": "development", "scope": "accounts-owner"}
                    ],
                    "status": "resolved",
                    "resolved_revision": 3,
                }
            ],
            "final_gate": {"required": False, "review_history": []},
        }
        later_readiness = later_superseded_history["selection_readiness"]
        later_readiness["basis_revision"] = 3
        later_readiness["reviews"][1]["review_id"] = "selection-readiness-3"
        later_readiness["reviews"][1]["basis_revision"] = 3
        later_metric = later_superseded_history["operation_metrics"]["spans"][-1]
        later_metric["span_id"] = "selection-readiness-3"
        self.write_selection_data(request_id, later_superseded_history)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("needs invalidation opened at retirement basis 2", result.stdout)
        self.assertIn("`accounts-owner-development-1`", result.stdout)

        reviewed_snapshot = copy.deepcopy(state)
        reviewed_snapshot["semantic_review_closure"] = {
            "version": "1",
            "basis_revision": 2,
            "review_passes": [
                {
                    "review_id": "accounts-owner-development-1",
                    "reviewer_role": "development",
                    "scope": "accounts-owner",
                    "basis_revision": 1,
                    "verdict": "PASS",
                    "status": "stale",
                },
                {
                    "review_id": "programs-consumer-risk-1",
                    "reviewer_role": "risk",
                    "scope": "programs-consumer",
                    "basis_revision": 1,
                    "verdict": "PASS",
                    "status": "stale",
                },
            ],
            "invalidations": [
                {
                    "invalidation_id": "contract-retirement-2",
                    "trigger": "candidate-disposition",
                    "cause": "공유 계약 retirement 전에 영향 PASS를 무효화했다.",
                    "opened_revision": 2,
                    "affected_artifacts": [
                        {"location": "request", "path": "inventory.md"}
                    ],
                    "affected_bundles": ["accounts-owner", "programs-consumer"],
                    "stale_review_ids": [
                        "accounts-owner-development-1",
                        "programs-consumer-risk-1",
                    ],
                    "required_reviews": [
                        {"reviewer_role": "development", "scope": "accounts-owner"},
                        {"reviewer_role": "risk", "scope": "programs-consumer"},
                    ],
                    "status": "open",
                }
            ],
            "final_gate": {"required": False, "review_history": []},
        }
        reviewed_current = copy.deepcopy(current)
        reviewed_current["semantic_review_closure"] = copy.deepcopy(
            reviewed_snapshot["semantic_review_closure"]
        )
        errors: list[str] = []
        validate_state_snapshot_completeness(
            reviewed_snapshot,
            reviewed_current,
            "snapshot",
            errors,
            active_created_path=guarded_path,
            active_candidate_id="access-policy",
            active_atom_key="access-policy",
        )
        self.assertEqual([], errors)

        missing_risk_requirement_snapshot = copy.deepcopy(reviewed_snapshot)
        missing_risk_requirement_current = copy.deepcopy(reviewed_current)
        for value in (
            missing_risk_requirement_snapshot,
            missing_risk_requirement_current,
        ):
            value["semantic_review_closure"]["invalidations"][0][
                "required_reviews"
            ] = [
                {"reviewer_role": "development", "scope": "accounts-owner"}
            ]
        errors = []
        validate_state_snapshot_completeness(
            missing_risk_requirement_snapshot,
            missing_risk_requirement_current,
            "snapshot",
            errors,
            active_created_path=guarded_path,
            active_candidate_id="access-policy",
            active_atom_key="access-policy",
        )
        self.assertTrue(
            any(
                "must include required review `risk`/`programs-consumer`" in error
                for error in errors
            ),
            errors,
        )

        reviewed_current["selection_readiness"]["basis_revision"] = 3
        reviewed_current["selection_retirements"]["retired_bundles"][0][
            "retired_basis_revision"
        ] = 3
        reviewed_current["selection_retirements"]["retired_contracts"][0][
            "retired_basis_revision"
        ] = 3
        errors = []
        validate_state_snapshot_completeness(
            reviewed_snapshot,
            reviewed_current,
            "snapshot",
            errors,
            active_created_path=guarded_path,
            active_candidate_id="access-policy",
            active_atom_key="access-policy",
        )
        joined = "\n".join(errors)
        self.assertIn("`accounts-owner-development-1`", joined)
        self.assertIn("`programs-consumer-risk-1`", joined)
        self.assertIn("at retirement basis 3", joined)

        missing_unrelated_local_route = copy.deepcopy(current)
        missing_unrelated_local_route["risk_triggers"] = []
        self.write_selection_data(request_id, missing_unrelated_local_route)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("changes unrelated risk routing", result.stdout)

        active_retired_collision = copy.deepcopy(current)
        active_retired_collision["shared_contracts"] = [active_contract]
        self.write_selection_data(request_id, active_retired_collision)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("cannot be active and retired", result.stdout)

        retired_route = copy.deepcopy(current)
        retired_route["risk_triggers"][0].update(
            {
                "route": "shared-contract",
                "shared_contract_id": "access-policy-contract",
            }
        )
        self.write_selection_data(request_id, retired_route)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("does not resolve", result.stdout)

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
        )
        state = self.read_selection_state(request_id)
        state["semantic_review_closure"] = {
            "version": "1",
            "basis_revision": 2,
            "review_passes": [
                {
                    "review_id": "domain-development-1",
                    "reviewer_role": "development",
                    "scope": "domain-bundle",
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
                    "affected_bundles": ["domain-bundle"],
                    "stale_review_ids": ["domain-development-1"],
                    "required_reviews": [
                        {
                            "reviewer_role": "development",
                            "scope": "domain-bundle",
                        },
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
                    "scope": "domain-bundle",
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
        state["operation_metrics"]["spans"].extend(
            [
                {
                    "span_id": "domain-bundle-1",
                    "kind": "bundle",
                    "scope": "domain",
                    "attempt_id": "domain-attempt-1",
                    "status": "finished",
                    "started_at": "2026-07-20T08:00:03Z",
                    "finished_at": "2026-07-20T08:00:04Z",
                    "outcome": "completed",
                },
                {
                    "span_id": "domain-writer-1",
                    "kind": "writer",
                    "scope": "domain",
                    "attempt_id": "domain-attempt-1",
                    "status": "finished",
                    "started_at": "2026-07-20T08:00:05Z",
                    "finished_at": "2026-07-20T08:00:06Z",
                    "outcome": "completed",
                },
                {
                    "span_id": "domain-development-2",
                    "kind": "development-review",
                    "scope": "domain-bundle",
                    "attempt_id": "domain-attempt-1",
                    "status": "finished",
                    "started_at": "2026-07-20T08:00:07Z",
                    "finished_at": "2026-07-20T08:00:08Z",
                    "outcome": "PASS",
                },
                {
                    "span_id": "affected-integration-2",
                    "kind": "integration-review",
                    "scope": "affected-closure",
                    "attempt_id": "integration-attempt-1",
                    "status": "finished",
                    "started_at": "2026-07-20T08:00:09Z",
                    "finished_at": "2026-07-20T08:00:10Z",
                    "outcome": "PASS",
                },
                {
                    "span_id": "docs-validation-2",
                    "kind": "validation",
                    "scope": "docs",
                    "attempt_id": "docs-validation-attempt-2",
                    "status": "active",
                    "started_at": "2026-07-20T08:00:11Z",
                },
            ]
        )
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
        state["operation_profile"] = "initial-baseline"
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
        validation_span = state["operation_metrics"]["spans"].pop()
        state["operation_metrics"]["spans"].append(
            {
                "span_id": "project-baseline-2",
                "kind": "baseline-review",
                "scope": "project-wide",
                "attempt_id": "baseline-attempt-2",
                "status": "finished",
                "started_at": "2026-07-20T08:00:11Z",
                "finished_at": "2026-07-20T08:00:12Z",
                "outcome": "PASS",
            }
        )
        validation_span.update(
            {
                "span_id": "baseline-validation-2",
                "scope": "baseline",
                "attempt_id": "baseline-validation-attempt-2",
                "started_at": "2026-07-20T08:00:13Z",
            }
        )
        state["operation_metrics"]["spans"].append(validation_span)
        self.write_selection_data(request_id, state)
        baseline = self.run_validator("baseline", request_id=request_id)
        self.assertEqual(0, baseline.returncode, baseline.stdout + baseline.stderr)

    def test_semantic_closure_supports_provisional_risk_impact_routing(self) -> None:
        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "domain-context",
                    "domain": "domain",
                    "candidate": "도메인 맥락",
                    "disposition": "write",
                    "selection_basis": "공유 계약의 변경 영향을 설명한다.",
                    "candidate_atom_keys": ["domain-context"],
                }
            ],
            bundle_keys=["domain-context"],
            risk_triggers=[
                {
                    "candidate_id": "domain-context",
                    "atom_key": "domain-context",
                    "triggers": ["shared policy contract"],
                    "basis": "선택된 공유 계약이 변경 영향에 중요하다.",
                }
            ],
            request_id="20260716-090004-provisional-risk-routing",
        )
        state = self.read_selection_state(request_id)
        state["semantic_review_closure"] = {
            "version": "1",
            "basis_revision": 2,
            "review_passes": [
                {
                    "review_id": "domain-development-1",
                    "reviewer_role": "development",
                    "scope": "domain-bundle",
                    "basis_revision": 1,
                    "verdict": "PASS",
                    "status": "stale",
                },
                {
                    "review_id": "domain-risk-1",
                    "reviewer_role": "risk",
                    "scope": "domain-bundle",
                    "basis_revision": 1,
                    "verdict": "PASS",
                    "status": "current",
                },
            ],
            "invalidations": [
                {
                    "invalidation_id": "domain-generalization-1",
                    "trigger": "documented-meaning",
                    "cause": "참조 문구를 일반화해 위험 영향 확인이 필요하다.",
                    "opened_revision": 2,
                    "affected_artifacts": [
                        {
                            "location": "managed-docs",
                            "path": "domain/domain-context-atom.md",
                        }
                    ],
                    "affected_bundles": ["domain-bundle"],
                    "stale_review_ids": ["domain-development-1"],
                    "required_reviews": [
                        {
                            "reviewer_role": "development",
                            "scope": "domain-bundle",
                        }
                    ],
                    "status": "open",
                }
            ],
            "final_gate": {"required": False, "review_history": []},
        }
        self.write_selection_data(request_id, state)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        stale_risk_without_required_pair = copy.deepcopy(state)
        incomplete_closure = stale_risk_without_required_pair[
            "semantic_review_closure"
        ]
        incomplete_closure["review_passes"][1]["status"] = "stale"
        incomplete_closure["invalidations"][0]["stale_review_ids"].append(
            "domain-risk-1"
        )
        self.write_selection_data(request_id, stale_risk_without_required_pair)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn(
            "stale v4 PASS `domain-risk-1` must include exact required review "
            "`risk`/`domain-bundle`",
            result.stdout,
        )

        risk_neutral = copy.deepcopy(state)
        neutral_closure = risk_neutral["semantic_review_closure"]
        neutral_closure["review_passes"][0]["status"] = "superseded"
        neutral_closure["review_passes"].append(
            {
                "review_id": "domain-development-2",
                "reviewer_role": "development",
                "scope": "domain-bundle",
                "basis_revision": 2,
                "verdict": "PASS",
                "status": "current",
            }
        )
        neutral_closure["invalidations"][0].update(
            {"status": "resolved", "resolved_revision": 2}
        )
        self.write_selection_data(request_id, risk_neutral)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        risk_changed = copy.deepcopy(state)
        changed_closure = risk_changed["semantic_review_closure"]
        changed_closure["basis_revision"] = 3
        changed_closure["review_passes"][0]["status"] = "superseded"
        changed_closure["review_passes"][1]["status"] = "superseded"
        changed_closure["review_passes"].extend(
            [
                {
                    "review_id": "domain-development-3",
                    "reviewer_role": "development",
                    "scope": "domain-bundle",
                    "basis_revision": 3,
                    "verdict": "PASS",
                    "status": "current",
                },
                {
                    "review_id": "domain-risk-3",
                    "reviewer_role": "risk",
                    "scope": "domain-bundle",
                    "basis_revision": 3,
                    "verdict": "PASS",
                    "status": "current",
                },
            ]
        )
        changed_invalidation = changed_closure["invalidations"][0]
        changed_invalidation["stale_review_ids"].append("domain-risk-1")
        changed_invalidation["required_reviews"].append(
            {"reviewer_role": "risk", "scope": "domain-bundle"}
        )
        changed_invalidation.update({"status": "resolved", "resolved_revision": 3})
        self.write_selection_data(request_id, risk_changed)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

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
        )
        state = self.read_selection_state(request_id)
        state["semantic_review_closure"] = {
            "version": "1",
            "basis_revision": 2,
            "review_passes": [
                {
                    "review_id": "domain-development-1",
                    "reviewer_role": "development",
                    "scope": "domain-bundle",
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
                    "affected_bundles": ["domain-bundle"],
                    "stale_review_ids": ["domain-development-1"],
                    "required_reviews": [
                        {
                            "reviewer_role": "development",
                            "scope": "domain-bundle",
                        }
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
        )
        state = self.read_selection_state(request_id)
        prior_pass = {
            "review_id": "domain-development-1",
            "reviewer_role": "development",
            "scope": "domain-bundle",
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
            "affected_bundles": ["domain-bundle"],
            "stale_review_ids": ["domain-development-1"],
            "required_reviews": [
                {
                    "reviewer_role": "development",
                    "scope": "domain-bundle",
                }
            ],
            "status": "open",
        }
        second = {
            **first,
            "invalidation_id": "domain-glossary-change-1",
            "trigger": "glossary-source",
            "cause": "용어 원본도 함께 변경됐다.",
            "affected_bundles": ["outside-bundle"],
            "required_reviews": [
                {"reviewer_role": "development", "scope": "outside-bundle"}
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
        self.assertIn(
            "affected bundle `outside-bundle` does not resolve to a v4 "
            "`bundle_queue.bundle_id`",
            result.stdout,
        )
        self.assertIn(
            "scope `outside-bundle` does not resolve to a v4 "
            "`bundle_queue.bundle_id`",
            result.stdout,
        )

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
            "`--request-id` requires `--phase selection`, `docs`, `baseline`, "
            "`metrics-preterminal`, or `metrics-final`",
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
