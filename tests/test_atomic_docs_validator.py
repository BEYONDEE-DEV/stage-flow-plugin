from __future__ import annotations

import copy
import contextlib
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import scripts.validate_atomic_docs as validator_module

from scripts.record_atomic_docs_event import (
    OperationEventError,
    ZERO_HASH,
    canonical_event_hash,
    canonical_json_bytes,
    reduce_operation_events,
)
from scripts.validate_atomic_docs import (
    construct_unique_json_object,
    git_locator_content,
    markdown_body_text,
    markdown_lines_with_block,
    required_final_validation_scope,
    validate_operation_metrics,
    validate_semantic_challenge_recovery,
    validate_semantic_review_operation_order,
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

    def test_git_locator_is_revision_lexical_and_ignores_worktree_symlink_retarget(self) -> None:
        owner_a = self.root / "owner-a.txt"
        owner_b = self.root / "owner-b.txt"
        alias = self.root / "alias.txt"
        owner_a.write_text("a-one\na-two\na-three\n", encoding="utf-8")
        owner_b.write_text("b-one\nb-two\nb-three\n", encoding="utf-8")
        alias.symlink_to("owner-a.txt")
        self._git("add", "owner-a.txt", "owner-b.txt", "alias.txt")
        self._git("commit", "-m", "add locator symlink")
        revision = self._git("rev-parse", "HEAD").stdout.strip()

        self.assertEqual(
            b"a-two\na-three\n",
            git_locator_content(self.root, revision, "owner-a.txt:2-3"),
        )
        self.assertEqual(
            b"owner-a.txt",
            git_locator_content(self.root, revision, "alias.txt:1"),
        )

        alias.unlink()
        alias.symlink_to("owner-b.txt")
        self.assertEqual(
            b"owner-a.txt",
            git_locator_content(self.root, revision, "alias.txt:1"),
        )

    def test_material_challenge_fail_recovery_is_structurally_linked(self) -> None:
        attempts = [
            {"basis_revision": 1, "verdict": "FAIL"},
            {"basis_revision": 2, "verdict": "PASS"},
        ]
        handoffs = [
            {
                "reason": "challenger-material-fail",
                "basis_revision": 2,
                "affected_bundle_ids": ["accounts-owner"],
                "stale_review_ids": ["accounts-development-1"],
            }
        ]
        invalidations = [
            {
                "opened_revision": 2,
                "affected_bundles": ["accounts-owner"],
                "stale_review_ids": [
                    "accounts-development-1",
                    "accounts-risk-1",
                ],
                "status": "resolved",
            }
        ]
        errors: list[str] = []
        validate_semantic_challenge_recovery(
            attempts,
            handoffs,
            invalidations,
            errors,
        )
        self.assertEqual([], errors)

        mismatched = copy.deepcopy(invalidations)
        mismatched[0]["affected_bundles"] = ["programs-consumer"]
        errors = []
        validate_semantic_challenge_recovery(
            attempts,
            handoffs,
            mismatched,
            errors,
        )
        self.assertTrue(
            any("same affected bundles" in error for error in errors),
            errors,
        )

        errors = []
        validate_semantic_challenge_recovery(
            [{"basis_revision": 1, "verdict": "FAIL"}],
            [],
            [],
            errors,
            current_basis=1,
        )
        self.assertTrue(
            any("must immediately advance" in error for error in errors),
            errors,
        )

        errors = []
        validate_semantic_challenge_recovery(
            [{"basis_revision": 1, "verdict": "FAIL"}],
            [],
            [],
            errors,
            current_basis=2,
        )
        self.assertTrue(
            any("exactly one material-fail" in error for error in errors),
            errors,
        )

        open_recovery = copy.deepcopy(invalidations)
        open_recovery[0]["status"] = "open"
        errors = []
        validate_semantic_challenge_recovery(
            [{"basis_revision": 1, "verdict": "FAIL"}],
            handoffs,
            open_recovery,
            errors,
            current_basis=2,
            dispatch_status="paused",
        )
        self.assertEqual([], errors)

        errors = []
        validate_semantic_challenge_recovery(
            [{"basis_revision": 1, "verdict": "FAIL"}],
            handoffs,
            open_recovery,
            errors,
            current_basis=3,
            dispatch_status="paused",
        )
        self.assertTrue(
            any(
                "failed semantic challenge basis 1 recovery must remain at exact "
                "next basis 2" in error
                for error in errors
            ),
            errors,
        )

        errors = []
        validate_semantic_challenge_recovery(
            [{"basis_revision": 1, "verdict": "FAIL"}],
            handoffs,
            invalidations,
            errors,
            current_basis=2,
            dispatch_status="ready",
        )
        self.assertTrue(
            any("requires a next-basis terminal challenge" in error for error in errors),
            errors,
        )

        partial_invalidation = copy.deepcopy(invalidations)
        partial_invalidation[0]["required_reviews"] = []
        review_entries = {
            "accounts-development-1": {
                "reviewer_role": "development",
                "scope": "accounts-owner",
                "basis_revision": 1,
                "verdict": "PASS",
                "status": "superseded",
            },
            "programs-development-1": {
                "reviewer_role": "development",
                "scope": "programs-consumer",
                "basis_revision": 1,
                "verdict": "PASS",
                "status": "current",
            },
        }
        partial_handoff = copy.deepcopy(handoffs)
        partial_handoff[0]["affected_bundle_ids"].append("programs-consumer")
        partial_invalidation[0]["affected_bundles"].append("programs-consumer")
        errors = []
        validate_semantic_challenge_recovery(
            attempts,
            partial_handoff,
            partial_invalidation,
            errors,
            current_basis=2,
            review_entries=review_entries,
        )
        self.assertTrue(
            any(
                "must stale every latest development PASS for affected bundle "
                "`programs-consumer`" in error
                for error in errors
            ),
            errors,
        )
        self.assertTrue(
            any(
                "must require development review for affected bundle "
                "`programs-consumer`" in error
                for error in errors
            ),
            errors,
        )

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
        normalize_v5: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        if request_id is not None and normalize_v5:
            self.normalize_v5_request(
                request_id,
                require_terminal=(
                    phase in {"baseline", "metrics-preterminal", "metrics-final"}
                    or (phase == "docs" and not expected_atom_keys)
                    or (phase == "selection" and require_actions_final)
                ),
            )
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
        with_aids: bool = False,
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
        selection_version: str | None = "5",
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
        if selection_version == "5":
            bundle.update(
                {
                    "bundle_id": f"{bundle_domain}-bundle",
                    "depends_on_contract_ids": [],
                }
            )
            for trigger_index, trigger in enumerate(normalized_risk_triggers, start=1):
                if isinstance(trigger, dict):
                    trigger.setdefault("risk_id", f"risk-{trigger_index}")
                    trigger.setdefault("route", "local")
            state.update(
                {
                    "shared_contracts": [],
                    "contract_binding_traces": [],
                    "created_aids": [],
                    "persistent_agent_ids": {
                        "writer": "writer-1",
                        "reviewer": "reviewer-1",
                    },
                    "reviewer_handoffs": {"version": "1", "history": []},
                    "semantic_challenge": {"version": "1", "attempts": []},
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
        if selection_version == "5":
            self.normalize_v5_request(request_id, require_terminal=False)
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

    def normalize_v5_request(self, request_id: str, *, require_terminal: bool) -> None:
        state_path = self.selection_state_path(request_id)
        try:
            state = json.loads(
                state_path.read_text(encoding="utf-8"),
                object_pairs_hook=construct_unique_json_object,
            )
        except (OSError, json.JSONDecodeError, ValueError):
            return
        selection = state.get("context_selection")
        if not isinstance(selection, dict) or selection.get("version") != "5":
            return
        request_root = state_path.parent
        state.setdefault("created_aids", [])
        state.setdefault("contract_binding_traces", [])
        state.setdefault("reviewer_handoffs", {"version": "1", "history": []})
        state.setdefault("semantic_challenge", {"version": "1", "attempts": []})
        risks = state.get("risk_triggers")
        if isinstance(risks, list):
            for index, risk in enumerate(risks, start=1):
                if isinstance(risk, dict):
                    risk.setdefault("risk_id", f"risk-{index}")

        review_entries: list[dict[str, object]] = []
        readiness = state.get("selection_readiness")
        if isinstance(readiness, dict) and isinstance(readiness.get("reviews"), list):
            for review in readiness["reviews"]:
                if isinstance(review, dict):
                    review_entries.append(review)
                    if review.get("status") == "current" or "receipt" not in review:
                        review["receipt"] = self.make_test_review_receipt(
                            request_root,
                            state,
                            review_id=str(review.get("review_id", "readiness-review")),
                            agent_id=str(
                                review.get(
                                    "reviewer_agent_id",
                                    state.get("persistent_agent_ids", {}).get(
                                        "reviewer", "reviewer-1"
                                    ),
                                )
                            ),
                            role=str(review.get("reviewer_role", "development")),
                            scope="selection-readiness",
                            basis_revision=(
                                review.get("basis_revision")
                                if type(review.get("basis_revision")) is int
                                else 1
                            ),
                            verdict=str(review.get("verdict", "PASS")),
                        )
        closure = state.get("semantic_review_closure")
        semantic_reviews = (
            closure.get("review_passes") if isinstance(closure, dict) else None
        )
        if isinstance(semantic_reviews, list):
            for review in semantic_reviews:
                if not isinstance(review, dict):
                    continue
                review_entries.append(review)
                role = str(review.get("reviewer_role", "development"))
                agent_id = (
                    "risk-reviewer-1"
                    if role == "risk"
                    else f"reviewer-{review.get('review_id', 'semantic-review')}"
                    if role in {"integration", "baseline"}
                    else str(
                        state.get("persistent_agent_ids", {}).get(
                            "reviewer", "reviewer-1"
                        )
                    )
                )
                if review.get("status") == "current" or "receipt" not in review:
                    review["receipt"] = self.make_test_review_receipt(
                        request_root,
                        state,
                        review_id=str(review.get("review_id", "semantic-review")),
                        agent_id=agent_id,
                        role=role,
                        scope=str(review.get("scope", "project-wide")),
                        basis_revision=(
                            review.get("basis_revision")
                            if type(review.get("basis_revision")) is int
                            else 1
                        ),
                        verdict=str(review.get("verdict", "PASS")),
                    )

        self.normalize_test_binding_traces(state, review_entries)
        challenge = state.get("semantic_challenge")
        attempts = challenge.get("attempts") if isinstance(challenge, dict) else None
        if isinstance(attempts, list):
            attempts.clear()
        if require_terminal and isinstance(attempts, list) and not attempts:
            raw_basis = closure.get("basis_revision") if isinstance(closure, dict) else None
            basis = raw_basis if type(raw_basis) is int else 1
            final_gate = closure.get("final_gate") if isinstance(closure, dict) else None
            final_review_id = (
                final_gate.get("review_id") if isinstance(final_gate, dict) else None
            )
            reused = next(
                (
                    review
                    for review in review_entries
                    if review.get("review_id") == final_review_id
                    and review.get("reviewer_role") in {"integration", "baseline"}
                ),
                None,
            )
            if isinstance(reused, dict):
                reviewer_agent = str(reused["receipt"]["reviewer_agent_id"])
                attempts.append(
                    {
                        "challenge_id": f"challenge-{basis}",
                        "basis_revision": basis,
                        "mode": "reuse-final-review",
                        "review_id": str(reused["review_id"]),
                        "reviewer_agent_id": reviewer_agent,
                        "primary_agent_id": str(
                            state.get("persistent_agent_ids", {}).get(
                                "reviewer", "reviewer-1"
                            )
                        ),
                        "excluded_inputs": [
                            "primary-report",
                            "primary-verdict",
                            "primary-evidence-summary",
                        ],
                        "verdict": "PASS",
                        "receipt": copy.deepcopy(reused["receipt"]),
                    }
                )
            else:
                review_id = f"terminal-challenge-{basis}"
                receipt = self.make_test_review_receipt(
                    request_root,
                    state,
                    review_id=review_id,
                    agent_id="challenger-1",
                    role="challenger",
                    scope="terminal-current-basis",
                    basis_revision=basis,
                    verdict="PASS",
                )
                metrics = state.get("operation_metrics")
                metric_spans = metrics.get("spans") if isinstance(metrics, dict) else None
                if isinstance(metric_spans, list) and not any(
                    isinstance(span, dict) and span.get("span_id") == review_id
                    for span in metric_spans
                ):
                    challenge_span = {
                        "span_id": review_id,
                        "kind": "integration-review",
                        "scope": "terminal-current-basis",
                        "attempt_id": f"{review_id}-attempt",
                        "status": "finished",
                        "started_at": "2026-07-20T08:00:02.100000Z",
                        "finished_at": "2026-07-20T08:00:02.200000Z",
                        "outcome": "PASS",
                    }
                    validation_index = next(
                        (
                            index
                            for index, span in enumerate(metric_spans)
                            if isinstance(span, dict) and span.get("kind") == "validation"
                        ),
                        len(metric_spans),
                    )
                    metric_spans.insert(validation_index, challenge_span)
                attempts.append(
                    {
                        "challenge_id": f"challenge-{basis}",
                        "basis_revision": basis,
                        "mode": "dedicated",
                        "review_id": review_id,
                        "reviewer_agent_id": "challenger-1",
                        "primary_agent_id": str(
                            state.get("persistent_agent_ids", {}).get(
                                "reviewer", "reviewer-1"
                            )
                        ),
                        "excluded_inputs": [
                            "primary-report",
                            "primary-verdict",
                            "primary-evidence-summary",
                        ],
                        "verdict": "PASS",
                        "receipt": receipt,
                    }
                )
        state_path.write_text(json.dumps(state), encoding="utf-8")
        self.write_test_operation_journal(request_root, request_id, state)

    def make_test_review_receipt(
        self,
        request_root: Path,
        state: dict[str, object],
        *,
        review_id: str,
        agent_id: str,
        role: str,
        scope: str,
        basis_revision: int,
        verdict: str,
    ) -> dict[str, object]:
        evidence_path = request_root / "evidence.md"
        report_relative = Path("reviews") / f"{review_id}.md"
        report_path = request_root / report_relative
        report_path.parent.mkdir(parents=True, exist_ok=True)
        if not report_path.exists():
            report_path.write_text("# Findings\n\n- None.\n", encoding="utf-8")
        report_project_relative = report_path.relative_to(self.root).as_posix()
        source_revision = str(state.get("source_commit_observed", self.commit))
        source_result = subprocess.run(
            ["git", "show", f"{source_revision}:source.txt"],
            cwd=self.root,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        source_content = source_result.stdout or b"source\n"
        first_line = source_content.splitlines(keepends=True)[0]
        atom_paths = sorted(self.docs.rglob("*-atom.md"))
        atom_paths_by_key: dict[str, Path] = {}
        for path in atom_paths:
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.startswith("atom_key: "):
                    atom_paths_by_key[line.removeprefix("atom_key: ").strip("'\"")] = path
                    break
        raw_paths = [request_root / "evidence.md", request_root / "inventory.md"]
        criteria_path = self.docs / "project" / "atomization-criteria.md"
        if role == "development" and scope == "selection-readiness":
            reviewed_paths = [*raw_paths, criteria_path]
        elif role in {"integration", "baseline", "challenger"}:
            reviewed_paths = [*raw_paths, criteria_path, *atom_paths]
        else:
            reviewed_paths = [criteria_path]
            queue = state.get("bundle_queue")
            retirements = state.get("selection_retirements")
            retired = (
                retirements.get("retired_bundles")
                if isinstance(retirements, dict)
                else None
            )
            bundles = [
                *(queue if isinstance(queue, list) else []),
                *(retired if isinstance(retired, list) else []),
            ]
            for bundle in bundles:
                if not isinstance(bundle, dict) or bundle.get("bundle_id") != scope:
                    continue
                keys = bundle.get("expected_atom_keys")
                reviewed_paths.extend(
                    atom_paths_by_key[key]
                    for key in (keys if isinstance(keys, list) else [])
                    if isinstance(key, str) and key in atom_paths_by_key
                )
            if not reviewed_paths:
                reviewed_paths = [evidence_path]
            if role == "risk":
                reviewed_paths.extend(atom_paths)
        reviewed_docs = [
            {
                "path": path.relative_to(self.root).as_posix(),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            for path in sorted(
                set(reviewed_paths),
                key=lambda item: item.relative_to(self.root).as_posix(),
            )
        ]
        manifest = {
            "basis_revision": basis_revision,
            "docs": reviewed_docs,
            "source_revision": source_revision,
            "source_locators": [
                {
                    "locator": "source.txt:1",
                    "content_sha256": hashlib.sha256(first_line).hexdigest(),
                }
            ],
        }
        return {
            "reviewer_agent_id": agent_id,
            "review_run_id": f"run-{review_id}",
            "reviewer_role": role,
            "scope": scope,
            "basis_manifest": manifest,
            "basis_manifest_sha256": hashlib.sha256(
                json.dumps(
                    manifest,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                    allow_nan=False,
                ).encode("utf-8")
            ).hexdigest(),
            "validation_question": "Do the selected claims match the recorded basis?",
            "observed_result": "The sanitized fixture basis was inspected.",
            "verdict": verdict,
            "report_path": report_project_relative,
            "report_sha256": hashlib.sha256(report_path.read_bytes()).hexdigest(),
        }

    def normalize_test_binding_traces(
        self,
        state: dict[str, object],
        review_entries: list[dict[str, object]],
    ) -> None:
        risks = state.get("risk_triggers")
        traces = state.get("contract_binding_traces")
        if not isinstance(risks, list) or not isinstance(traces, list):
            return
        traces.clear()
        candidates = state.get("context_selection", {}).get("candidates", [])
        if not isinstance(candidates, list):
            candidates = []
        candidates_by_id = {
            item.get("candidate_id"): item
            for item in candidates
            if isinstance(item, dict)
        }
        contracts = state.get("shared_contracts", [])
        if not isinstance(contracts, list):
            contracts = []
        contracts_by_id = {
            item.get("contract_id"): item
            for item in contracts
            if isinstance(item, dict)
        }
        atom_bundles: dict[str, str] = {}
        raw_queue = state.get("bundle_queue", [])
        for bundle in raw_queue if isinstance(raw_queue, list) else []:
            if not isinstance(bundle, dict):
                continue
            expected_atom_keys = bundle.get("expected_atom_keys")
            if not isinstance(expected_atom_keys, list):
                continue
            for atom_key in expected_atom_keys:
                atom_bundles[str(atom_key)] = str(bundle.get("bundle_id", "domain-bundle"))
        current_semantic_reviews = [
            review
            for review in review_entries
            if review.get("status") == "current"
            and "scope" in review
            and isinstance(review.get("receipt"), dict)
        ]
        current_readiness_review = next(
            (
                review
                for review in review_entries
                if review.get("status") == "current"
                and "scope" not in review
                and isinstance(review.get("receipt"), dict)
            ),
            None,
        )
        source_revision = str(state.get("source_commit_observed", self.commit))
        source_result = subprocess.run(
            ["git", "show", f"{source_revision}:source.txt"],
            cwd=self.root,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        source_line = (source_result.stdout or b"source\n").splitlines(keepends=True)[0]
        digest = hashlib.sha256(source_line).hexdigest()
        for risk in risks:
            if not isinstance(risk, dict):
                continue
            risk_id = str(risk["risk_id"])
            risk_candidate = str(risk.get("candidate_id", "domain-context"))
            risk_atom = str(risk.get("atom_key", "domain-context"))
            contract = contracts_by_id.get(risk.get("shared_contract_id"))
            if isinstance(contract, dict):
                owner_candidate = str(contract.get("owner_candidate_id"))
                owner_atom = str(contract.get("owner_atom_key"))
                consumers = contract.get("direct_consumer_candidate_ids", [])
                consumer_candidate = str(consumers[0]) if consumers else risk_candidate
                owner_contract = str(contract.get("contract_id"))
                kind = (
                    "permission-privacy"
                    if contract.get("kind") == "permission"
                    else "contract"
                )
            else:
                owner_candidate = risk_candidate
                owner_atom = risk_atom
                consumer_candidate = risk_candidate
                owner_contract = f"local-{risk_id}"
                kind = "contract"
            consumer_data = candidates_by_id.get(consumer_candidate, {})
            consumer_keys = consumer_data.get("candidate_atom_keys", [])
            consumer_atom = str(consumer_keys[0]) if consumer_keys else risk_atom
            owner_bundle = atom_bundles.get(owner_atom)
            consumer_bundle = atom_bundles.get(consumer_atom, "domain-bundle")
            risk_bundle = atom_bundles.get(risk_atom)
            covering_reviews = [
                review
                for review in current_semantic_reviews
                if review.get("reviewer_role") in {"integration", "baseline"}
                or review.get("scope") in {owner_bundle, consumer_bundle}
            ]
            current_review = next(
                (
                    review
                    for review in covering_reviews
                    if review.get("reviewer_role") == "risk"
                    and review.get("scope") == risk_bundle
                ),
                next(
                    (
                        review
                        for review in covering_reviews
                        if review.get("reviewer_role") in {"integration", "baseline"}
                    ),
                    covering_reviews[0] if covering_reviews else current_readiness_review,
                ),
            )
            trace: dict[str, object] = {
                "trace_id": f"binding-{risk_id}",
                "risk_id": risk_id,
                "kind": kind,
                "owner_candidate_id": owner_candidate,
                "owner_atom_key": owner_atom,
                "owner_contract": owner_contract,
                "authority_status": "verified",
                "authority_revision": source_revision,
                "authority_locator": "source.txt:1",
                "authority_content_sha256": digest,
                "applicability_status": "verified",
                "applicability_basis": "The selected consumer uses this exact contract.",
                "consumer_candidate_id": consumer_candidate,
                "consumer_atom_key": consumer_atom,
                "consumer_bundle_id": consumer_bundle,
                "resource_or_identifier": "sanitized-resource",
                "implementation_locator": "source.txt:1",
                "implementation_content_sha256": digest,
                "review_id": str(
                    current_review.get("review_id", "selection-readiness-1")
                    if isinstance(current_review, dict)
                    else "selection-readiness-1"
                ),
                "verdict": "matches_confirmed_intent",
            }
            if kind == "permission-privacy":
                trace["permission_privacy"] = {
                    "principal": "authorized principal",
                    "authorized_object_or_data": "authorized resource",
                    "loaded_object": "loaded resource",
                    "projection_or_use": "sanitized projection",
                }
            traces.append(trace)

    def add_test_terminal_bundle_reviews(self, state: dict[str, object]) -> None:
        closure = state.get("semantic_review_closure")
        reviews = closure.get("review_passes") if isinstance(closure, dict) else None
        queue = state.get("bundle_queue")
        metrics = state.get("operation_metrics")
        spans = metrics.get("spans") if isinstance(metrics, dict) else None
        if (
            not isinstance(closure, dict)
            or not isinstance(reviews, list)
            or not isinstance(queue, list)
            or not isinstance(spans, list)
        ):
            return
        basis = closure.get("basis_revision")
        if type(basis) is not int:
            return
        active_bundles = {
            str(bundle["bundle_id"]): bundle
            for bundle in queue
            if isinstance(bundle, dict) and isinstance(bundle.get("bundle_id"), str)
        }
        work_insert_index = next(
            (
                index
                for index, span in enumerate(spans)
                if isinstance(span, dict)
                and span.get("kind")
                in {
                    "development-review",
                    "risk-review",
                    "integration-review",
                    "baseline-review",
                    "validation",
                }
                and span.get("scope") != "selection-readiness"
            ),
            len(spans),
        )
        for bundle_offset, bundle_id in enumerate(sorted(active_bundles)):
            bundle_attempts = {
                span.get("attempt_id")
                for span in spans
                if isinstance(span, dict)
                and span.get("kind") == "bundle"
                and span.get("scope") == bundle_id
                and span.get("status") == "finished"
                and span.get("outcome") in {"PASS", "completed"}
            }
            writer_attempts = {
                span.get("attempt_id")
                for span in spans
                if isinstance(span, dict)
                and span.get("kind") == "writer"
                and span.get("scope") == bundle_id
                and span.get("status") == "finished"
                and span.get("outcome") in {"PASS", "completed"}
            }
            if bundle_attempts & writer_attempts:
                continue
            attempt_id = f"fixture-{bundle_id}-attempt"
            started_second = 10 + bundle_offset * 4
            spans[work_insert_index:work_insert_index] = [
                {
                    "span_id": f"fixture-{bundle_id}-bundle",
                    "kind": "bundle",
                    "scope": bundle_id,
                    "attempt_id": attempt_id,
                    "status": "finished",
                    "started_at": f"2026-07-20T08:00:{started_second:02d}Z",
                    "finished_at": f"2026-07-20T08:00:{started_second + 1:02d}Z",
                    "outcome": "completed",
                },
                {
                    "span_id": f"fixture-{bundle_id}-writer",
                    "kind": "writer",
                    "scope": bundle_id,
                    "attempt_id": attempt_id,
                    "status": "finished",
                    "started_at": f"2026-07-20T08:00:{started_second + 2:02d}Z",
                    "finished_at": f"2026-07-20T08:00:{started_second + 3:02d}Z",
                    "outcome": "completed",
                },
            ]
            work_insert_index += 2
        atom_bundles = {
            str(atom_key): bundle_id
            for bundle_id, bundle in active_bundles.items()
            for atom_key in (
                bundle.get("expected_atom_keys")
                if isinstance(bundle.get("expected_atom_keys"), list)
                else []
            )
        }
        required_pairs = {
            ("development", bundle_id) for bundle_id in active_bundles
        }
        risks = state.get("risk_triggers")
        for trigger in risks if isinstance(risks, list) else []:
            if not isinstance(trigger, dict):
                continue
            bundle_id = atom_bundles.get(str(trigger.get("atom_key")))
            if bundle_id is not None:
                required_pairs.add(("risk", bundle_id))
        current_pairs = {
            (review.get("reviewer_role"), review.get("scope"))
            for review in reviews
            if isinstance(review, dict) and review.get("status") == "current"
        }
        final_gate = closure.get("final_gate")
        final_review_id = (
            final_gate.get("review_id") if isinstance(final_gate, dict) else None
        )
        validation_index = next(
            (
                index
                for index, span in enumerate(spans)
                if isinstance(span, dict)
                and (
                    span.get("span_id") == final_review_id
                    or span.get("kind") == "validation"
                )
            ),
            len(spans),
        )
        added = 0
        for role, scope in sorted(required_pairs):
            if (role, scope) in current_pairs:
                continue
            review_id = f"terminal-{role}-{scope}-{basis}"
            reviews.append(
                {
                    "review_id": review_id,
                    "reviewer_role": role,
                    "scope": scope,
                    "basis_revision": basis,
                    "verdict": "PASS",
                    "status": "current",
                }
            )
            started_second = 30 + added * 2
            spans.insert(
                validation_index + added,
                {
                    "span_id": review_id,
                    "kind": (
                        "development-review" if role == "development" else "risk-review"
                    ),
                    "scope": scope,
                    "attempt_id": f"{review_id}-attempt",
                    "status": "finished",
                    "started_at": f"2026-07-20T08:00:{started_second:02d}Z",
                    "finished_at": f"2026-07-20T08:00:{started_second + 1:02d}Z",
                    "outcome": "PASS",
                },
            )
            added += 1

    def add_test_semantic_review_operations(
        self,
        state: dict[str, object],
    ) -> None:
        closure = state.get("semantic_review_closure")
        reviews = closure.get("review_passes") if isinstance(closure, dict) else None
        metrics = state.get("operation_metrics")
        spans = metrics.get("spans") if isinstance(metrics, dict) else None
        if not isinstance(reviews, list) or not isinstance(spans, list):
            return
        queue = state.get("bundle_queue")
        queue_ids = [
            bundle.get("bundle_id")
            for bundle in (queue if isinstance(queue, list) else [])
            if isinstance(bundle, dict) and isinstance(bundle.get("bundle_id"), str)
        ]
        second = 10
        bundle_scopes = {
            review.get("scope")
            for review in reviews
            if isinstance(review, dict)
            and review.get("reviewer_role") in {"development", "risk"}
            and isinstance(review.get("scope"), str)
        }
        ordered_scopes = [scope for scope in queue_ids if scope in bundle_scopes]
        ordered_scopes.extend(sorted(bundle_scopes - set(ordered_scopes)))
        for scope in ordered_scopes:
            target_bases = sorted(
                {
                    review["basis_revision"]
                    for review in reviews
                    if isinstance(review, dict)
                    and review.get("scope") == scope
                    and review.get("reviewer_role") in {"development", "risk"}
                    and type(review.get("basis_revision")) is int
                }
            )
            bundle_attempts = {
                span.get("attempt_id"): span.get("basis_revision")
                for span in spans
                if isinstance(span, dict)
                and span.get("kind") == "bundle"
                and span.get("scope") == scope
                and span.get("status") == "finished"
                and span.get("outcome") in {"PASS", "completed"}
            }
            writer_attempts = {
                span.get("attempt_id"): span.get("basis_revision")
                for span in spans
                if isinstance(span, dict)
                and span.get("kind") == "writer"
                and span.get("scope") == scope
                and span.get("status") == "finished"
                and span.get("outcome") in {"PASS", "completed"}
            }
            completed_bases = {
                bundle_attempts[attempt]
                for attempt in bundle_attempts.keys() & writer_attempts.keys()
                if type(bundle_attempts[attempt]) is int
                and bundle_attempts[attempt] == writer_attempts[attempt]
            }
            missing_bases = [basis for basis in target_bases if basis not in completed_bases]
            if not missing_bases:
                continue
            scope_review_indexes = [
                index
                for index, span in enumerate(spans)
                if isinstance(span, dict)
                and span.get("scope") == scope
                and span.get("kind") in {"development-review", "risk-review"}
            ]
            review_bases_by_id = {
                review.get("review_id"): review.get("basis_revision")
                for review in reviews
                if isinstance(review, dict)
                and isinstance(review.get("review_id"), str)
                and type(review.get("basis_revision")) is int
            }
            future_scope_review_indexes = [
                index
                for index in scope_review_indexes
                if isinstance(spans[index], dict)
                and review_bases_by_id.get(spans[index].get("span_id"), 0)
                >= min(missing_bases)
            ]
            prior_scopes = set(queue_ids[: queue_ids.index(scope)]) if scope in queue_ids else set()
            prior_review_indexes = [
                index
                for index, span in enumerate(spans)
                if isinstance(span, dict)
                and span.get("scope") in prior_scopes
                and span.get("kind") in {"development-review", "risk-review"}
            ]
            prior_work_indexes = [
                index
                for index, span in enumerate(spans)
                if isinstance(span, dict)
                and span.get("scope") in prior_scopes
                and span.get("kind") in {"bundle", "writer"}
            ]
            terminal_index = next(
                (
                    index
                    for index, span in enumerate(spans)
                    if isinstance(span, dict)
                    and span.get("kind")
                    in {"integration-review", "baseline-review", "validation"}
                ),
                len(spans),
            )
            if future_scope_review_indexes:
                insert_at = min(future_scope_review_indexes)
            elif scope_review_indexes:
                insert_at = max(scope_review_indexes) + 1
            elif prior_review_indexes or prior_work_indexes:
                insert_at = max(prior_review_indexes + prior_work_indexes) + 1
            else:
                readiness_indexes = [
                    index
                    for index, span in enumerate(spans)
                    if isinstance(span, dict)
                    and span.get("scope") == "selection-readiness"
                ]
                insert_at = (
                    max(readiness_indexes) + 1 if readiness_indexes else terminal_index
                )
            dispatch = state.get("dispatch_control")
            episodes = dispatch.get("episodes") if isinstance(dispatch, dict) else None
            resume_review_ids = {
                episode.get("readiness_review_id")
                for episode in (episodes if isinstance(episodes, list) else [])
                if isinstance(episode, dict)
                and episode.get("status") == "resolved"
                and isinstance(episode.get("readiness_review_id"), str)
                and type(episode.get("resume_basis_revision")) is int
                and episode["resume_basis_revision"] <= min(missing_bases)
            }
            resume_indexes = [
                index
                for index, span in enumerate(spans)
                if isinstance(span, dict)
                and span.get("span_id") in resume_review_ids
            ]
            if resume_indexes:
                insert_at = max(insert_at, max(resume_indexes) + 1)
            insert_at = min(insert_at, terminal_index)
            work_spans: list[dict[str, object]] = []
            existing_span_ids = {
                span.get("span_id") for span in spans if isinstance(span, dict)
            }
            for basis in missing_bases:
                suffix = (
                    f"-basis-{basis}"
                    if f"fixture-{scope}-bundle" in existing_span_ids or len(missing_bases) > 1
                    else ""
                )
                attempt_id = f"fixture-{scope}-attempt-basis-{basis}"
                work_spans.extend(
                    [
                        {
                            "span_id": f"fixture-{scope}-bundle{suffix}",
                            "kind": "bundle",
                            "scope": scope,
                            "attempt_id": attempt_id,
                            "basis_revision": basis,
                            "status": "finished",
                            "started_at": f"2026-07-20T08:00:{second:02d}Z",
                            "finished_at": f"2026-07-20T08:00:{second + 1:02d}Z",
                            "outcome": "completed",
                        },
                        {
                            "span_id": f"fixture-{scope}-writer{suffix}",
                            "kind": "writer",
                            "scope": scope,
                            "attempt_id": attempt_id,
                            "basis_revision": basis,
                            "status": "finished",
                            "started_at": f"2026-07-20T08:00:{second + 2:02d}Z",
                            "finished_at": f"2026-07-20T08:00:{second + 3:02d}Z",
                            "outcome": "completed",
                        },
                    ]
                )
                second += 4
            spans[insert_at:insert_at] = work_spans
        final_gate = closure.get("final_gate") if isinstance(closure, dict) else None
        blocking_ids = {
            final_gate.get("review_id")
            if isinstance(final_gate, dict)
            else None
        }
        challenge = state.get("semantic_challenge")
        attempts = challenge.get("attempts") if isinstance(challenge, dict) else None
        blocking_ids.update(
            attempt.get("review_id")
            for attempt in (attempts if isinstance(attempts, list) else [])
            if isinstance(attempt, dict)
        )
        existing_ids = {
            span.get("span_id") for span in spans if isinstance(span, dict)
        }
        for review in reviews:
            if not isinstance(review, dict):
                continue
            review_id = review.get("review_id")
            role = review.get("reviewer_role")
            if not isinstance(review_id, str) or review_id in existing_ids:
                continue
            kind = {
                "development": "development-review",
                "risk": "risk-review",
                "integration": "integration-review",
                "baseline": "baseline-review",
            }.get(role)
            if kind is None:
                continue
            existing_scope_reviews = [
                index
                for index, span in enumerate(spans)
                if isinstance(span, dict)
                and span.get("scope") == review.get("scope")
                and span.get("kind") in {"development-review", "risk-review"}
            ]
            later_scopes = (
                set(queue_ids[queue_ids.index(review.get("scope")) + 1 :])
                if review.get("scope") in queue_ids
                else set()
            )
            later_work_indexes = [
                index
                for index, span in enumerate(spans)
                if isinstance(span, dict)
                and span.get("scope") in later_scopes
                and span.get("kind") in {"bundle", "writer"}
            ]
            blocking_index = next(
                (
                    index
                    for index, span in enumerate(spans)
                    if isinstance(span, dict)
                    and (
                        span.get("kind") == "validation"
                        or span.get("span_id") in blocking_ids
                    )
                ),
                len(spans),
            )
            matching_work_indexes = [
                index
                for index, span in enumerate(spans)
                if isinstance(span, dict)
                and span.get("scope") == review.get("scope")
                and span.get("kind") in {"bundle", "writer"}
                and span.get("basis_revision") == review.get("basis_revision")
            ]
            if matching_work_indexes:
                insert_at = min(max(matching_work_indexes) + 1, blocking_index)
            elif later_work_indexes:
                insert_at = min(min(later_work_indexes), blocking_index)
            elif existing_scope_reviews:
                # A later review of an already reviewed scope is a correction/rerun.
                # Keep it append-only instead of inserting it into prior history.
                insert_at = blocking_index
            else:
                scope_work_indexes = [
                    index
                    for index, span in enumerate(spans)
                    if isinstance(span, dict)
                    and span.get("scope") == review.get("scope")
                    and span.get("kind") in {"bundle", "writer"}
                ]
                insert_at = (
                    min(max(scope_work_indexes) + 1, blocking_index)
                    if scope_work_indexes
                    else blocking_index
                )
            spans.insert(
                insert_at,
                {
                    "span_id": review_id,
                    "kind": kind,
                    "scope": review.get("scope", "project-wide"),
                    "attempt_id": f"{review_id}-attempt",
                    "status": "finished",
                    "started_at": f"2026-07-20T08:00:{second:02d}Z",
                    "finished_at": f"2026-07-20T08:00:{second + 1:02d}Z",
                    "outcome": "PASS",
                },
            )
            existing_ids.add(review_id)
            second += 2

        readiness = state.get("selection_readiness")
        readiness_reviews = (
            readiness.get("reviews") if isinstance(readiness, dict) else None
        )
        basis_by_review_id = {
            entry.get("review_id"): entry.get("basis_revision")
            for entry in [
                *(readiness_reviews if isinstance(readiness_reviews, list) else []),
                *reviews,
            ]
            if isinstance(entry, dict)
            and isinstance(entry.get("review_id"), str)
            and type(entry.get("basis_revision")) is int
        }
        for index, span in enumerate(spans):
            if not isinstance(span, dict) or type(span.get("basis_revision")) is int:
                continue
            inferred_basis = basis_by_review_id.get(span.get("span_id"))
            if inferred_basis is None and span.get("kind") in {"bundle", "writer"}:
                inferred_basis = next(
                    (
                        basis_by_review_id.get(later.get("span_id"))
                        for later in spans[index + 1 :]
                        if isinstance(later, dict)
                        and later.get("kind") in {"development-review", "risk-review"}
                        and later.get("scope") == span.get("scope")
                        and basis_by_review_id.get(later.get("span_id")) is not None
                    ),
                    None,
                )
            span["basis_revision"] = (
                inferred_basis
                if type(inferred_basis) is int
                else closure.get("basis_revision", 1)
            )
        spans.sort(
            key=lambda span: (
                span.get("basis_revision", 1) if isinstance(span, dict) else 1,
                0
                if isinstance(span, dict)
                and span.get("kind") == "development-review"
                and span.get("scope") == "selection-readiness"
                else 1,
            )
        )

    def write_test_operation_journal(
        self,
        request_root: Path,
        request_id: str,
        state: dict[str, object],
    ) -> None:
        metrics = state.get("operation_metrics")
        if not isinstance(metrics, dict) or not isinstance(metrics.get("spans"), list):
            return
        if not isinstance(metrics.get("started_at"), str):
            return
        closure = state.get("semantic_review_closure")
        readiness = state.get("selection_readiness")
        fallback_basis = (
            closure.get("basis_revision") if isinstance(closure, dict) else None
        )
        if type(fallback_basis) is not int:
            fallback_basis = (
                readiness.get("basis_revision")
                if isinstance(readiness, dict)
                else 1
            )
        challenge = state.get("semantic_challenge")
        owned_basis: dict[str, int] = {}
        for owner in (
            readiness.get("reviews") if isinstance(readiness, dict) else [],
            closure.get("review_passes") if isinstance(closure, dict) else [],
            state.get("semantic_fail_diagnostics", []),
            challenge.get("attempts") if isinstance(challenge, dict) else [],
        ):
            for entry in owner if isinstance(owner, list) else []:
                if not isinstance(entry, dict) or type(entry.get("basis_revision")) is not int:
                    continue
                span_id = entry.get("review_id", entry.get("review_span_id"))
                if isinstance(span_id, str):
                    owned_basis[span_id] = entry["basis_revision"]
        metric_spans = metrics["spans"]
        inferred_work_basis: dict[tuple[str, str], int] = {}
        work_indexes: dict[tuple[str, str], list[int]] = {}
        for index, span in enumerate(metric_spans):
            if (
                isinstance(span, dict)
                and span.get("kind") in {"bundle", "writer"}
                and isinstance(span.get("scope"), str)
                and isinstance(span.get("attempt_id"), str)
            ):
                work_indexes.setdefault(
                    (span["scope"], span["attempt_id"]), []
                ).append(index)
        for identity, indexes in work_indexes.items():
            for later in metric_spans[max(indexes) + 1 :]:
                if (
                    isinstance(later, dict)
                    and later.get("kind") in {"development-review", "risk-review"}
                    and later.get("scope") == identity[0]
                    and isinstance(later.get("span_id"), str)
                    and later["span_id"] in owned_basis
                ):
                    inferred_work_basis[identity] = owned_basis[later["span_id"]]
                    break
        events: list[dict[str, object]] = []

        def append_event(event_type: str, payload: dict[str, object]) -> None:
            event: dict[str, object] = {
                "version": "1",
                "sequence": len(events) + 1,
                "request_id": request_id,
                "event_type": event_type,
                "payload": payload,
                "previous_hash": events[-1]["event_hash"] if events else ZERO_HASH,
            }
            event["event_hash"] = canonical_event_hash(event)
            events.append(event)

        append_event("operation-started", {"started_at": metrics["started_at"]})
        try:
            for span in metrics["spans"]:
                if not isinstance(span, dict):
                    return
                span.setdefault(
                    "basis_revision",
                    owned_basis.get(
                        str(span.get("span_id")),
                        inferred_work_basis.get(
                            (str(span.get("scope")), str(span.get("attempt_id"))),
                            fallback_basis,
                        ),
                    ),
                )
                started = {
                    "span_id": span["span_id"],
                    "kind": span["kind"],
                    "scope": span["scope"],
                    "attempt_id": span["attempt_id"],
                    "basis_revision": span["basis_revision"],
                    "started_at": span["started_at"],
                }
                if "rerun_of" in span or "rerun_reason" in span:
                    started["rerun_of"] = span["rerun_of"]
                    started["rerun_reason"] = span["rerun_reason"]
                append_event("span-started", started)
                if span.get("status") == "finished":
                    append_event(
                        "span-finished",
                        {
                            "span_id": span["span_id"],
                            "finished_at": span["finished_at"],
                            "outcome": span["outcome"],
                        },
                    )
            if metrics.get("status") == "finished":
                append_event(
                    "operation-finished",
                    {"finished_at": metrics["finished_at"]},
                )
        except (KeyError, TypeError):
            return
        projection = reduce_operation_events(
            events,
            expected_request_id=request_id,
        )
        (request_root / "operation-events.jsonl").write_bytes(
            b"".join(canonical_json_bytes(event) + b"\n" for event in events)
        )
        state["operation_metrics"] = projection
        projected_spans = {
            span.get("span_id"): span
            for span in state["operation_metrics"]["spans"]
            if isinstance(span, dict) and isinstance(span.get("span_id"), str)
        }
        dispatch = state.get("dispatch_control")
        episodes = dispatch.get("episodes") if isinstance(dispatch, dict) else None
        for episode in episodes if isinstance(episodes, list) else []:
            if not isinstance(episode, dict) or episode.get("cause") != "late-shared-contract":
                continue
            cutoff = projected_spans.get(episode.get("pause_after_span_id"))
            if isinstance(cutoff, dict) and type(cutoff.get("finished_sequence")) is int:
                episode.setdefault("pause_after_sequence", cutoff["finished_sequence"])
        (request_root / "work-state.json").write_text(
            json.dumps(state),
            encoding="utf-8",
        )

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
            selection_version="5",
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
        self.normalize_v5_request(request_id, require_terminal=False)
        return request_id, self.read_selection_state(request_id)

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
        bundle_review_passes = [
            {
                "review_id": "accounts-development-1",
                "reviewer_role": "development",
                "scope": "accounts-owner",
                "basis_revision": 1,
                "verdict": "PASS",
                "status": "current",
            },
            {
                "review_id": "accounts-risk-1",
                "reviewer_role": "risk",
                "scope": "accounts-owner",
                "basis_revision": 1,
                "verdict": "PASS",
                "status": "current",
            },
            {
                "review_id": "programs-development-1",
                "reviewer_role": "development",
                "scope": "programs-consumer",
                "basis_revision": 1,
                "verdict": "PASS",
                "status": "current",
            },
            {
                "review_id": "programs-risk-1",
                "reviewer_role": "risk",
                "scope": "programs-consumer",
                "basis_revision": 1,
                "verdict": "PASS",
                "status": "current",
            },
        ]
        spans = state["operation_metrics"]["spans"]
        spans.extend(
            [
                {
                    "span_id": "accounts-bundle-1",
                    "kind": "bundle",
                    "scope": "accounts-owner",
                    "attempt_id": "accounts-attempt-1",
                    "status": "finished",
                    "started_at": "2026-07-20T08:00:03Z",
                    "finished_at": "2026-07-20T08:00:04Z",
                    "outcome": "completed",
                },
                {
                    "span_id": "accounts-writer-1",
                    "kind": "writer",
                    "scope": "accounts-owner",
                    "attempt_id": "accounts-attempt-1",
                    "status": "finished",
                    "started_at": "2026-07-20T08:00:05Z",
                    "finished_at": "2026-07-20T08:00:06Z",
                    "outcome": "completed",
                },
                {
                    "span_id": "accounts-development-1",
                    "kind": "development-review",
                    "scope": "accounts-owner",
                    "attempt_id": "accounts-development-attempt-1",
                    "status": "finished",
                    "started_at": "2026-07-20T08:00:06.100000Z",
                    "finished_at": "2026-07-20T08:00:06.200000Z",
                    "outcome": "PASS",
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
                    "scope": "programs-consumer",
                    "attempt_id": "programs-attempt-1",
                    "status": "finished",
                    "started_at": "2026-07-20T08:00:09Z",
                    "finished_at": "2026-07-20T08:00:10Z",
                    "outcome": "completed",
                },
                {
                    "span_id": "programs-writer-1",
                    "kind": "writer",
                    "scope": "programs-consumer",
                    "attempt_id": "programs-attempt-1",
                    "status": "finished",
                    "started_at": "2026-07-20T08:00:11Z",
                    "finished_at": "2026-07-20T08:00:12Z",
                    "outcome": "completed",
                },
                {
                    "span_id": "programs-development-1",
                    "kind": "development-review",
                    "scope": "programs-consumer",
                    "attempt_id": "programs-development-attempt-1",
                    "status": "finished",
                    "started_at": "2026-07-20T08:00:12.100000Z",
                    "finished_at": "2026-07-20T08:00:12.200000Z",
                    "outcome": "PASS",
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
                    *bundle_review_passes,
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
        else:
            state["semantic_review_closure"] = {
                "version": "1",
                "basis_revision": 1,
                "review_passes": [
                    *bundle_review_passes,
                    {
                        "review_id": "integration-review-1",
                        "reviewer_role": "integration",
                        "scope": "affected-closure",
                        "basis_revision": 1,
                        "verdict": "PASS",
                        "status": "current",
                    }
                ],
                "invalidations": [],
                "final_gate": {
                    "required": True,
                    "review_id": "integration-review-1",
                    "review_history": ["integration-review-1"],
                },
            }
            spans.append(
                {
                    "span_id": "integration-review-1",
                    "kind": "integration-review",
                    "scope": "affected-closure",
                    "attempt_id": "integration-attempt-1",
                    "status": "finished",
                    "started_at": "2026-07-20T08:00:15Z",
                    "finished_at": "2026-07-20T08:00:16Z",
                    "outcome": "PASS",
                }
            )
        validation_start = "2026-07-20T08:00:17Z"
        validation_finish = "2026-07-20T08:00:18Z"
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
                    "finished_at": "2026-07-20T08:00:19Z",
                }
            )
        self.write_selection_data(request_id, state)
        self.normalize_v5_request(request_id, require_terminal=True)
        return request_id, self.read_selection_state(request_id)

    def write_state_rollback(
        self,
        request_id: str,
        relative_path: str,
        state: dict[str, object],
    ) -> tuple[Path, str]:
        self.normalize_v5_snapshot_state(request_id, state)
        path = self.selection_request_root(request_id) / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state), encoding="utf-8")
        return path, self.file_sha256(path)

    def normalize_v5_snapshot_state(
        self, request_id: str, state: dict[str, object]
    ) -> None:
        request_root = self.selection_request_root(request_id)
        state.setdefault("created_aids", [])
        state.setdefault("contract_binding_traces", [])
        state.setdefault("reviewer_handoffs", {"version": "1", "history": []})
        state.setdefault("semantic_challenge", {"version": "1", "attempts": []})
        risks = state.get("risk_triggers")
        if isinstance(risks, list):
            for index, risk in enumerate(risks, start=1):
                if isinstance(risk, dict):
                    risk.setdefault("risk_id", f"risk-{index}")
        reviews: list[dict[str, object]] = []
        readiness = state.get("selection_readiness")
        readiness_reviews = readiness.get("reviews") if isinstance(readiness, dict) else None
        if isinstance(readiness_reviews, list):
            for review in readiness_reviews:
                if not isinstance(review, dict):
                    continue
                reviews.append(review)
                review.setdefault(
                    "receipt",
                    self.make_test_review_receipt(
                        request_root,
                        state,
                        review_id=str(review.get("review_id", "readiness-review")),
                        agent_id=str(review.get("reviewer_agent_id", "reviewer-1")),
                        role=str(review.get("reviewer_role", "development")),
                        scope="selection-readiness",
                        basis_revision=(
                            review.get("basis_revision")
                            if type(review.get("basis_revision")) is int
                            else 1
                        ),
                        verdict=str(review.get("verdict", "PASS")),
                    ),
                )
        closure = state.get("semantic_review_closure")
        semantic_reviews = closure.get("review_passes") if isinstance(closure, dict) else None
        if isinstance(semantic_reviews, list):
            for review in semantic_reviews:
                if not isinstance(review, dict):
                    continue
                reviews.append(review)
                role = str(review.get("reviewer_role", "development"))
                review.setdefault(
                    "receipt",
                    self.make_test_review_receipt(
                        request_root,
                        state,
                        review_id=str(review.get("review_id", "semantic-review")),
                        agent_id=(
                            "risk-reviewer-1"
                            if role == "risk"
                            else f"reviewer-{review.get('review_id', 'semantic-review')}"
                            if role in {"integration", "baseline"}
                            else str(
                                state.get("persistent_agent_ids", {}).get(
                                    "reviewer", "reviewer-1"
                                )
                            )
                        ),
                        role=role,
                        scope=str(review.get("scope", "project-wide")),
                        basis_revision=(
                            review.get("basis_revision")
                            if type(review.get("basis_revision")) is int
                            else 1
                        ),
                        verdict=str(review.get("verdict", "PASS")),
                    ),
                )
        self.add_test_semantic_review_operations(state)
        self.normalize_test_binding_traces(state, reviews)
        self.write_test_operation_journal(request_root, request_id, state)

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

    def test_v5_receipt_recomputes_every_embedded_hash(self) -> None:
        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "domain-context",
                    "domain": "domain",
                    "candidate": "도메인 맥락",
                    "disposition": "write",
                    "selection_basis": "검토 입력을 고정한다.",
                    "candidate_atom_keys": ["domain-context"],
                }
            ],
            bundle_keys=["domain-context"],
            request_id="20260721-220001-v5-receipt",
        )
        base = self.read_selection_state(request_id)
        result = self.run_validator(
            "selection", request_id=request_id, normalize_v5=False
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        unicode_doc = self.docs / "project" / "검토-참고.md"
        unicode_doc.write_text("비 ASCII receipt 입력\n", encoding="utf-8")
        unicode_manifest_state = copy.deepcopy(base)
        unicode_receipt = unicode_manifest_state["selection_readiness"]["reviews"][0][
            "receipt"
        ]
        unicode_receipt["basis_manifest"]["docs"].append(
            {
                "path": unicode_doc.relative_to(self.root).as_posix(),
                "sha256": self.file_sha256(unicode_doc),
            }
        )
        unicode_receipt["basis_manifest"]["docs"].sort(
            key=lambda item: item["path"]
        )
        unicode_receipt["basis_manifest_sha256"] = hashlib.sha256(
            json.dumps(
                unicode_receipt["basis_manifest"],
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        self.write_selection_data(request_id, unicode_manifest_state)
        result = self.run_validator(
            "selection", request_id=request_id, normalize_v5=False
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        cases = []
        escaped_unicode = copy.deepcopy(unicode_manifest_state)
        escaped_receipt = escaped_unicode["selection_readiness"]["reviews"][0][
            "receipt"
        ]
        escaped_receipt["basis_manifest_sha256"] = hashlib.sha256(
            json.dumps(
                escaped_receipt["basis_manifest"],
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        cases.append(
            (escaped_unicode, "basis manifest hash does not match canonical JSON")
        )

        invalid = copy.deepcopy(base)
        receipt = invalid["selection_readiness"]["reviews"][0]["receipt"]
        receipt["basis_manifest"]["docs"][0]["sha256"] = "0" * 64
        receipt["basis_manifest_sha256"] = hashlib.sha256(
            json.dumps(
                receipt["basis_manifest"],
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        cases.append((invalid, "receipt document 1 hash does not match approved preimage"))

        invalid = copy.deepcopy(base)
        receipt = invalid["selection_readiness"]["reviews"][0]["receipt"]
        receipt["basis_manifest"]["source_locators"][0]["content_sha256"] = "0" * 64
        receipt["basis_manifest_sha256"] = hashlib.sha256(
            json.dumps(
                receipt["basis_manifest"],
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        cases.append((invalid, "content hash does not match source revision"))

        invalid = copy.deepcopy(base)
        invalid["selection_readiness"]["reviews"][0]["receipt"][
            "basis_manifest_sha256"
        ] = "0" * 64
        cases.append((invalid, "basis manifest hash does not match canonical JSON"))

        invalid = copy.deepcopy(base)
        invalid["selection_readiness"]["reviews"][0]["receipt"][
            "report_sha256"
        ] = "0" * 64
        cases.append((invalid, "findings-only report hash does not match approved preimage"))

        invalid = copy.deepcopy(base)
        receipt = invalid["selection_readiness"]["reviews"][0]["receipt"]
        receipt["basis_manifest"]["docs"] = [
            item
            for item in receipt["basis_manifest"]["docs"]
            if not item["path"].endswith("/project/atomization-criteria.md")
        ]
        receipt["basis_manifest_sha256"] = hashlib.sha256(
            json.dumps(
                receipt["basis_manifest"],
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        cases.append((invalid, "atomization-criteria.md"))

        invalid = copy.deepcopy(base)
        receipt = invalid["selection_readiness"]["reviews"][0]["receipt"]
        receipt["basis_manifest"]["source_locators"][0]["locator"] = (
            "source.txt:" + "9" * 5000
        )
        receipt["basis_manifest_sha256"] = hashlib.sha256(
            json.dumps(
                receipt["basis_manifest"],
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        cases.append((invalid, "does not resolve at source revision"))

        for index, (state, expected) in enumerate(cases, start=1):
            with self.subTest(case=index):
                self.write_selection_data(request_id, state)
                result = self.run_validator(
                    "selection", request_id=request_id, normalize_v5=False
                )
                self.assertEqual(1, result.returncode)
                self.assertIn(expected, result.stdout)
                self.assertNotIn("Traceback", result.stdout + result.stderr)

    def test_v5_binding_trace_enforces_permission_chain_and_authority_precedence(
        self,
    ) -> None:
        request_id, base = self.write_v4_owner_readiness_state(
            "20260721-220002-v5-binding"
        )
        result = self.run_validator(
            "selection", request_id=request_id, normalize_v5=False
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        cases = []
        invalid = copy.deepcopy(base)
        del invalid["contract_binding_traces"][0]["permission_privacy"]
        cases.append((invalid, "must contain `permission_privacy` binding"))

        invalid = copy.deepcopy(base)
        trace = invalid["contract_binding_traces"][0]
        trace["authority_status"] = "unresolved"
        trace["verdict"] = "bug_or_regression"
        cases.append((invalid, "must be `confirmation_needed`"))

        allowed_uncertainty = copy.deepcopy(base)
        allowed_uncertainty["contract_binding_traces"][0]["verdict"] = (
            "confirmation_needed"
        )
        self.write_selection_data(request_id, allowed_uncertainty)
        result = self.run_validator(
            "selection", request_id=request_id, normalize_v5=False
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        invalid = copy.deepcopy(allowed_uncertainty)
        invalid["contract_binding_traces"][0]["observed_conflict"] = True
        cases.append(
            (
                invalid,
                "verified authoritative/applicable observed conflict must use "
                "`bug_or_regression`",
            )
        )

        invalid = copy.deepcopy(base)
        invalid["contract_binding_traces"][0].update(
            {"observed_conflict": True, "verdict": "matches_confirmed_intent"}
        )
        cases.append(
            (
                invalid,
                "verified authoritative/applicable observed conflict must use "
                "`bug_or_regression`",
            )
        )

        invalid = copy.deepcopy(base)
        invalid["contract_binding_traces"][0]["observed_conflict"] = "yes"
        cases.append((invalid, "`observed_conflict` must be boolean"))

        invalid = copy.deepcopy(base)
        invalid["contract_binding_traces"].pop()
        cases.append((invalid, "is missing its exact binding trace"))

        for index, (state, expected) in enumerate(cases, start=1):
            with self.subTest(case=index):
                self.write_selection_data(request_id, state)
                result = self.run_validator(
                    "selection", request_id=request_id, normalize_v5=False
                )
                self.assertEqual(1, result.returncode)
                self.assertIn(expected, result.stdout)

    def test_v5_affected_closure_receipt_requires_current_atom_coverage(self) -> None:
        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "domain-context",
                    "domain": "domain",
                    "candidate": "도메인 맥락",
                    "disposition": "write",
                    "selection_basis": "최초 affected closure를 검토한다.",
                    "candidate_atom_keys": ["domain-context"],
                }
            ],
            bundle_keys=["domain-context"],
            request_id="20260721-220008-v5-affected-receipt",
        )
        self.write_atom("domain/domain-context-atom.md", "domain-context")
        state = self.read_selection_state(request_id)
        review_id = "affected-integration-1"
        state["semantic_review_closure"]["review_passes"] = [
            {
                "review_id": review_id,
                "reviewer_role": "integration",
                "scope": "affected-closure",
                "basis_revision": 1,
                "verdict": "PASS",
                "status": "current",
                "receipt": self.make_test_review_receipt(
                    self.selection_request_root(request_id),
                    state,
                    review_id=review_id,
                    agent_id="integration-reviewer-1",
                    role="integration",
                    scope="affected-closure",
                    basis_revision=1,
                    verdict="PASS",
                ),
            }
        ]
        state["operation_metrics"]["spans"].append(
            {
                "span_id": review_id,
                "kind": "integration-review",
                "scope": "affected-closure",
                "attempt_id": "affected-integration-attempt-1",
                "status": "finished",
                "started_at": "2026-07-20T08:00:03Z",
                "finished_at": "2026-07-20T08:00:04Z",
                "outcome": "PASS",
            }
        )
        self.write_selection_data(request_id, state)
        self.write_test_operation_journal(
            self.selection_request_root(request_id), request_id, state
        )
        result = self.run_validator(
            "selection", request_id=request_id, normalize_v5=False
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        invalid = copy.deepcopy(state)
        receipt = invalid["semantic_review_closure"]["review_passes"][0]["receipt"]
        receipt["basis_manifest"]["docs"] = [
            item
            for item in receipt["basis_manifest"]["docs"]
            if not item["path"].endswith("domain-context-atom.md")
        ]
        receipt["basis_manifest_sha256"] = hashlib.sha256(
            json.dumps(
                receipt["basis_manifest"],
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        self.write_selection_data(request_id, invalid)
        result = self.run_validator(
            "selection", request_id=request_id, normalize_v5=False
        )
        self.assertEqual(1, result.returncode)
        self.assertIn(
            "omits required reviewed document `docs/domain/domain-context-atom.md`",
            result.stdout,
        )

    def test_v5_conditional_reviewer_handoff_preserves_primary_chain(self) -> None:
        request_id, state = self.write_v4_owner_readiness_state(
            "20260721-220003-v5-handoff"
        )
        state["persistent_agent_ids"]["reviewer"] = "reviewer-2"
        readiness = state["selection_readiness"]
        readiness["basis_revision"] = 2
        readiness["reviews"][0]["status"] = "superseded"
        readiness["reviews"].append(
            {
                "review_id": "selection-readiness-2",
                "reviewer_role": "development",
                "reviewer_agent_id": "reviewer-2",
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
        state["reviewer_handoffs"]["history"].append(
            {
                "handoff_id": "reviewer-handoff-2",
                "from_agent_id": "reviewer-1",
                "to_agent_id": "reviewer-2",
                "reason": "agent-unavailable",
                "basis_revision": 2,
                "affected_bundle_ids": ["accounts-owner"],
                "stale_review_ids": ["selection-readiness-1"],
            }
        )
        self.write_selection_data(request_id, state)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        state = self.read_selection_state(request_id)
        self.write_atom("accounts/access-policy-atom.md", "access-policy")
        self.write_atom("programs/program-access-atom.md", "program-access")
        closure = state["semantic_review_closure"]
        closure["basis_revision"] = 2
        closure["review_passes"] = [
            {
                "review_id": "accounts-development-2",
                "reviewer_role": "development",
                "scope": "accounts-owner",
                "basis_revision": 2,
                "verdict": "PASS",
                "status": "current",
                "receipt": self.make_test_review_receipt(
                    self.selection_request_root(request_id),
                    state,
                    review_id="accounts-development-2",
                    agent_id="reviewer-2",
                    role="development",
                    scope="accounts-owner",
                    basis_revision=2,
                    verdict="PASS",
                ),
            },
            {
                "review_id": "programs-risk-1",
                "reviewer_role": "risk",
                "scope": "programs-consumer",
                "basis_revision": 1,
                "verdict": "PASS",
                "status": "current",
                "receipt": self.make_test_review_receipt(
                    self.selection_request_root(request_id),
                    state,
                    review_id="programs-risk-1",
                    agent_id="risk-reviewer-1",
                    role="risk",
                    scope="programs-consumer",
                    basis_revision=1,
                    verdict="PASS",
                ),
            },
        ]
        closure["review_passes"].insert(
            1,
            {
                "review_id": "accounts-risk-1",
                "reviewer_role": "risk",
                "scope": "accounts-owner",
                "basis_revision": 1,
                "verdict": "PASS",
                "status": "current",
                "receipt": self.make_test_review_receipt(
                    self.selection_request_root(request_id),
                    state,
                    review_id="accounts-risk-1",
                    agent_id="risk-reviewer-1",
                    role="risk",
                    scope="accounts-owner",
                    basis_revision=1,
                    verdict="PASS",
                ),
            },
        )
        state["operation_metrics"]["spans"].extend(
            [
                {
                    "span_id": "accounts-development-2",
                    "kind": "development-review",
                    "scope": "accounts-owner",
                    "attempt_id": "accounts-development-attempt-2",
                    "status": "finished",
                    "started_at": "2026-07-20T08:00:05Z",
                    "finished_at": "2026-07-20T08:00:06Z",
                    "outcome": "PASS",
                },
                {
                    "span_id": "accounts-risk-1",
                    "kind": "risk-review",
                    "scope": "accounts-owner",
                    "attempt_id": "accounts-risk-attempt-1",
                    "status": "finished",
                    "started_at": "2026-07-20T08:00:06.100000Z",
                    "finished_at": "2026-07-20T08:00:06.200000Z",
                    "outcome": "PASS",
                },
                {
                    "span_id": "programs-risk-1",
                    "kind": "risk-review",
                    "scope": "programs-consumer",
                    "attempt_id": "programs-risk-attempt-1",
                    "status": "finished",
                    "started_at": "2026-07-20T08:00:07Z",
                    "finished_at": "2026-07-20T08:00:08Z",
                    "outcome": "PASS",
                },
            ]
        )
        self.add_test_semantic_review_operations(state)
        review_entries = [
            *state["selection_readiness"]["reviews"],
            *closure["review_passes"],
        ]
        self.normalize_test_binding_traces(state, review_entries)
        self.write_selection_data(request_id, state)
        self.write_test_operation_journal(
            self.selection_request_root(request_id), request_id, state
        )
        result = self.run_validator(
            "selection", request_id=request_id, normalize_v5=False
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        handoff_cases = [
            (
                {"basis_revision": 3},
                "basis revision exceeds the current review basis",
            ),
            (
                {"affected_bundle_ids": []},
                "must name at least one affected bundle id",
            ),
            (
                {"reason": "context-saturation"},
                "context-saturation requires four distinct completed queue items",
            ),
            (
                {"reason": "basis-reset"},
                "basis-reset requires a same-basis invalidation",
            ),
            (
                {"reason": "challenger-material-fail"},
                "challenger-material-fail requires exactly one failed semantic challenge",
            ),
        ]
        for updates, expected in handoff_cases:
            with self.subTest(updates=updates):
                invalid = copy.deepcopy(state)
                invalid["reviewer_handoffs"]["history"][0].update(updates)
                self.write_selection_data(request_id, invalid)
                result = self.run_validator(
                    "selection", request_id=request_id, normalize_v5=False
                )
                self.assertEqual(1, result.returncode)
                self.assertIn(expected, result.stdout)

    def test_v5_terminal_challenger_is_exactly_one_fresh_blind_pass(self) -> None:
        request_id, base = self.write_v4_final_state(
            "20260721-220004-v5-challenger"
        )
        result = self.run_validator(
            "docs", request_id=request_id, normalize_v5=False
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        result = self.run_validator(
            "selection", request_id=request_id, normalize_v5=False
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        paused_with_current_challenge = copy.deepcopy(base)
        paused_with_current_challenge["dispatch_control"]["status"] = "paused"
        self.write_selection_data(request_id, paused_with_current_challenge)
        result = self.run_validator(
            "selection", request_id=request_id, normalize_v5=False
        )
        self.assertEqual(1, result.returncode)
        self.assertIn(
            "current-basis challenge requires dispatch control to be `ready`",
            result.stdout,
        )

        future_work_after_challenge = copy.deepcopy(base)
        future_work_after_challenge["operation_metrics"]["spans"] = [
            span
            for span in future_work_after_challenge["operation_metrics"]["spans"]
            if span["kind"] != "validation"
        ]
        future_work_after_challenge["operation_metrics"]["spans"].append(
            {
                "span_id": "accounts-writer-future-basis",
                "kind": "writer",
                "scope": "accounts-owner",
                "attempt_id": "accounts-future-attempt",
                "basis_revision": 2,
                "status": "active",
                "started_at": "2026-07-20T08:00:17Z",
            }
        )
        self.write_selection_data(request_id, future_work_after_challenge)
        self.write_test_operation_journal(
            self.selection_request_root(request_id),
            request_id,
            future_work_after_challenge,
        )
        result = self.run_validator(
            "selection", request_id=request_id, normalize_v5=False
        )
        self.assertEqual(1, result.returncode)
        self.assertIn(
            "current-basis challenge must start after every bundle/writer span "
            "finishes",
            result.stdout,
        )
        self.assertIn(
            "basis_revision must not exceed the current semantic closure basis",
            result.stdout,
        )

        early = copy.deepcopy(base)
        early_review_id = early["semantic_challenge"]["attempts"][0]["review_id"]
        early_spans = early["operation_metrics"]["spans"]
        early_span = next(
            span for span in early_spans if span["span_id"] == early_review_id
        )
        early_spans.remove(early_span)
        early_spans.insert(1, early_span)
        self.write_selection_data(request_id, early)
        self.write_test_operation_journal(
            self.selection_request_root(request_id), request_id, early
        )
        result = self.run_validator(
            "selection", request_id=request_id, normalize_v5=False
        )
        self.assertEqual(1, result.returncode)
        self.assertIn(
            "semantic challenge attempt 1 must follow every basis-applicable "
            "bundle development/risk review",
            result.stdout,
        )

        buried = copy.deepcopy(early)
        buried["semantic_review_closure"]["basis_revision"] = 2
        current_review_id = "terminal-current-challenge-2"
        current_receipt = self.make_test_review_receipt(
            self.selection_request_root(request_id),
            buried,
            review_id=current_review_id,
            agent_id="current-challenger-2",
            role="challenger",
            scope="terminal-current-basis",
            basis_revision=2,
            verdict="PASS",
        )
        buried["semantic_challenge"]["attempts"].append(
            {
                "challenge_id": "terminal-current-challenge-2",
                "basis_revision": 2,
                "mode": "dedicated",
                "review_id": current_review_id,
                "reviewer_agent_id": "current-challenger-2",
                "primary_agent_id": "reviewer-1",
                "excluded_inputs": [
                    "primary-report",
                    "primary-verdict",
                    "primary-evidence-summary",
                ],
                "verdict": "PASS",
                "receipt": current_receipt,
            }
        )
        validation_index = next(
            index
            for index, span in enumerate(buried["operation_metrics"]["spans"])
            if span["kind"] == "validation"
        )
        buried["operation_metrics"]["spans"].insert(
            validation_index,
            {
                "span_id": current_review_id,
                "kind": "integration-review",
                "scope": "terminal-current-basis",
                "attempt_id": "terminal-current-challenge-attempt-2",
                "status": "finished",
                "started_at": "2026-07-20T08:00:16.300000Z",
                "finished_at": "2026-07-20T08:00:16.400000Z",
                "outcome": "PASS",
            },
        )
        self.write_selection_data(request_id, buried)
        self.write_test_operation_journal(
            self.selection_request_root(request_id), request_id, buried
        )
        result = self.run_validator(
            "selection", request_id=request_id, normalize_v5=False
        )
        self.assertEqual(1, result.returncode)
        self.assertIn(
            "semantic challenge attempt 1 must follow every basis-applicable "
            "bundle development/risk review",
            result.stdout,
        )

        aliased = copy.deepcopy(base)
        alias_path = self.docs / "reviews" / "copied-primary-summary.md"
        alias_path.parent.mkdir(parents=True, exist_ok=True)
        alias_path.write_text("copied primary summary\n", encoding="utf-8")
        final_review_id = aliased["semantic_review_closure"]["final_gate"][
            "review_id"
        ]
        final_review = next(
            review
            for review in aliased["semantic_review_closure"]["review_passes"]
            if review["review_id"] == final_review_id
        )
        final_manifest = final_review["receipt"]["basis_manifest"]
        final_manifest["docs"].append(
            {
                "path": alias_path.relative_to(self.root).as_posix(),
                "sha256": self.file_sha256(alias_path),
            }
        )
        final_manifest["docs"].sort(key=lambda item: item["path"])
        final_review["receipt"]["basis_manifest_sha256"] = hashlib.sha256(
            json.dumps(
                final_manifest,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        aliased["semantic_challenge"]["attempts"][0]["receipt"] = copy.deepcopy(
            final_review["receipt"]
        )
        self.write_selection_data(request_id, aliased)
        result = self.run_validator(
            "docs", request_id=request_id, normalize_v5=False
        )
        self.assertEqual(1, result.returncode)
        self.assertIn("outside the exact raw challenge allowlist", result.stdout)

        invalid = copy.deepcopy(base)
        attempt = invalid["semantic_challenge"]["attempts"][0]
        attempt["primary_agent_id"] = attempt["reviewer_agent_id"]
        self.write_selection_data(request_id, invalid)
        result = self.run_validator("docs", request_id=request_id, normalize_v5=False)
        self.assertEqual(1, result.returncode)
        self.assertIn("challenger must differ from the primary reviewer", result.stdout)
        self.assertIn("persistent primary active at its basis", result.stdout)

        invalid = copy.deepcopy(base)
        duplicate = copy.deepcopy(invalid["semantic_challenge"]["attempts"][0])
        duplicate["challenge_id"] = "challenge-duplicate"
        invalid["semantic_challenge"]["attempts"].append(duplicate)
        self.write_selection_data(request_id, invalid)
        result = self.run_validator("docs", request_id=request_id, normalize_v5=False)
        self.assertEqual(1, result.returncode)
        self.assertIn("has more than one attempt", result.stdout)

        invalid = copy.deepcopy(base)
        invalid["semantic_challenge"]["attempts"][0]["excluded_inputs"].pop()
        self.write_selection_data(request_id, invalid)
        result = self.run_validator("docs", request_id=request_id, normalize_v5=False)
        self.assertEqual(1, result.returncode)
        self.assertIn("must blindly exclude", result.stdout)

        invalid = copy.deepcopy(base)
        primary_receipt = invalid["selection_readiness"]["reviews"][0]["receipt"]
        final_review = invalid["semantic_review_closure"]["review_passes"][0]
        reviewed_docs = final_review["receipt"]["basis_manifest"]["docs"]
        reviewed_docs.append(
            {
                "path": primary_receipt["report_path"],
                "sha256": primary_receipt["report_sha256"],
            }
        )
        reviewed_docs.sort(key=lambda item: item["path"])
        manifest = final_review["receipt"]["basis_manifest"]
        final_review["receipt"]["basis_manifest_sha256"] = hashlib.sha256(
            json.dumps(
                manifest,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()
        invalid["semantic_challenge"]["attempts"][0]["receipt"] = copy.deepcopy(
            final_review["receipt"]
        )
        self.write_selection_data(request_id, invalid)
        result = self.run_validator("docs", request_id=request_id, normalize_v5=False)
        self.assertEqual(1, result.returncode)
        self.assertIn("must exclude primary findings reports", result.stdout)

        dedicated = copy.deepcopy(base)
        dedicated_review_id = "terminal-challenge-1"
        dedicated_receipt = self.make_test_review_receipt(
            self.selection_request_root(request_id),
            dedicated,
            review_id=dedicated_review_id,
            agent_id="dedicated-challenger-1",
            role="challenger",
            scope="terminal-current-basis",
            basis_revision=1,
            verdict="PASS",
        )
        dedicated["semantic_challenge"]["attempts"] = [
            {
                "challenge_id": "dedicated-challenge-1",
                "basis_revision": 1,
                "mode": "dedicated",
                "review_id": dedicated_review_id,
                "reviewer_agent_id": "dedicated-challenger-1",
                "primary_agent_id": "reviewer-1",
                "excluded_inputs": [
                    "primary-report",
                    "primary-verdict",
                    "primary-evidence-summary",
                ],
                "verdict": "PASS",
                "receipt": dedicated_receipt,
            }
        ]
        validation_span = dedicated["operation_metrics"]["spans"].pop()
        dedicated["operation_metrics"]["spans"].append(
            {
                "span_id": dedicated_review_id,
                "kind": "integration-review",
                "scope": "terminal-current-basis",
                "attempt_id": "dedicated-challenge-attempt-1",
                "status": "finished",
                "started_at": "2026-07-20T08:00:16.100000Z",
                "finished_at": "2026-07-20T08:00:16.200000Z",
                "outcome": "PASS",
            }
        )
        dedicated["operation_metrics"]["spans"].append(validation_span)
        self.write_selection_data(request_id, dedicated)
        self.write_test_operation_journal(
            self.selection_request_root(request_id), request_id, dedicated
        )
        result = self.run_validator("docs", request_id=request_id, normalize_v5=False)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        duplicate_run = copy.deepcopy(dedicated)
        duplicate_run["semantic_challenge"]["attempts"][0]["receipt"][
            "review_run_id"
        ] = base["semantic_review_closure"]["review_passes"][-1]["receipt"][
            "review_run_id"
        ]
        self.write_selection_data(request_id, duplicate_run)
        result = self.run_validator("docs", request_id=request_id, normalize_v5=False)
        self.assertEqual(1, result.returncode)
        self.assertIn("must use a fresh `review_run_id`", result.stdout)

        duplicate_report = copy.deepcopy(dedicated)
        existing_receipt = base["semantic_review_closure"]["review_passes"][-1][
            "receipt"
        ]
        challenge_receipt = duplicate_report["semantic_challenge"]["attempts"][0][
            "receipt"
        ]
        challenge_receipt["report_path"] = existing_receipt["report_path"]
        challenge_receipt["report_sha256"] = existing_receipt["report_sha256"]
        self.write_selection_data(request_id, duplicate_report)
        result = self.run_validator("docs", request_id=request_id, normalize_v5=False)
        self.assertEqual(1, result.returncode)
        self.assertIn("must use a fresh findings report", result.stdout)

        missing_raw_input = copy.deepcopy(dedicated)
        challenge_receipt = missing_raw_input["semantic_challenge"]["attempts"][0][
            "receipt"
        ]
        manifest = challenge_receipt["basis_manifest"]
        manifest["docs"] = [
            item
            for item in manifest["docs"]
            if not item["path"].endswith("/inventory.md")
        ]
        challenge_receipt["basis_manifest_sha256"] = hashlib.sha256(
            json.dumps(
                manifest,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        self.write_selection_data(request_id, missing_raw_input)
        result = self.run_validator("docs", request_id=request_id, normalize_v5=False)
        self.assertEqual(1, result.returncode)
        self.assertIn("blind basis manifest omits raw request input", result.stdout)

        leaked_state = copy.deepcopy(dedicated)
        challenge_receipt = leaked_state["semantic_challenge"]["attempts"][0][
            "receipt"
        ]
        work_state_path = self.selection_state_path(request_id)
        challenge_receipt["basis_manifest"]["docs"].append(
            {
                "path": work_state_path.relative_to(self.root).as_posix(),
                "sha256": self.file_sha256(work_state_path),
            }
        )
        challenge_receipt["basis_manifest"]["docs"].sort(
            key=lambda item: item["path"]
        )
        challenge_receipt["basis_manifest_sha256"] = hashlib.sha256(
            json.dumps(
                challenge_receipt["basis_manifest"],
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        self.write_selection_data(request_id, leaked_state)
        result = self.run_validator("docs", request_id=request_id, normalize_v5=False)
        self.assertEqual(1, result.returncode)
        self.assertIn("must exclude `work-state.json`", result.stdout)

        repeated_agent = copy.deepcopy(base)
        second = copy.deepcopy(repeated_agent["semantic_challenge"]["attempts"][0])
        second["challenge_id"] = "challenge-next-basis"
        second["basis_revision"] = 2
        repeated_agent["semantic_challenge"]["attempts"].append(second)
        self.write_selection_data(request_id, repeated_agent)
        result = self.run_validator("docs", request_id=request_id, normalize_v5=False)
        self.assertEqual(1, result.returncode)
        self.assertIn("fresh from every prior challenge basis", result.stdout)

        missing_metric = copy.deepcopy(dedicated)
        missing_metric["operation_metrics"]["spans"] = [
            span
            for span in missing_metric["operation_metrics"]["spans"]
            if span["span_id"] != dedicated_review_id
        ]
        self.write_selection_data(request_id, missing_metric)
        self.write_test_operation_journal(
            self.selection_request_root(request_id), request_id, missing_metric
        )
        result = self.run_validator("docs", request_id=request_id, normalize_v5=False)
        self.assertEqual(1, result.returncode)
        self.assertIn(
            "needs a matching finished `integration-review` operation metric span",
            result.stdout,
        )

    def test_v5_final_requires_bundle_development_and_risk_semantic_passes(
        self,
    ) -> None:
        request_id, base = self.write_v4_final_state(
            "20260721-220009-v5-final-semantic-passes"
        )
        result = self.run_validator(
            "docs", request_id=request_id, normalize_v5=False
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        readiness_trace = copy.deepcopy(base)
        for trace in readiness_trace["contract_binding_traces"]:
            trace["review_id"] = "selection-readiness-1"
        self.write_selection_data(request_id, readiness_trace)
        result = self.run_validator(
            "docs", request_id=request_id, normalize_v5=False
        )
        self.assertEqual(1, result.returncode)
        self.assertIn(
            "final review must resolve to semantic review closure PASS",
            result.stdout,
        )

        missing_development = copy.deepcopy(base)
        missing_development["semantic_review_closure"]["review_passes"] = [
            review
            for review in missing_development["semantic_review_closure"]["review_passes"]
            if review["review_id"] != "accounts-development-1"
        ]
        self.write_selection_data(request_id, missing_development)
        result = self.run_validator(
            "docs", request_id=request_id, normalize_v5=False
        )
        self.assertEqual(1, result.returncode)
        self.assertIn(
            "missing current development PASS for active bundle `accounts-owner`",
            result.stdout,
        )

        missing_risk = copy.deepcopy(base)
        missing_risk["semantic_review_closure"]["review_passes"] = [
            review
            for review in missing_risk["semantic_review_closure"]["review_passes"]
            if review["review_id"] != "programs-risk-1"
        ]
        self.write_selection_data(request_id, missing_risk)
        result = self.run_validator(
            "docs", request_id=request_id, normalize_v5=False
        )
        self.assertEqual(1, result.returncode)
        self.assertIn(
            "missing current risk PASS for risk-triggered bundle `programs-consumer`",
            result.stdout,
        )

    def test_v5_reviewer_identity_matrix_is_independent_and_persistent(self) -> None:
        request_id, base = self.write_v4_final_state(
            "20260721-220011-v5-reviewer-identities"
        )

        same_writer_primary = copy.deepcopy(base)
        same_writer_primary["persistent_agent_ids"]["writer"] = (
            same_writer_primary["persistent_agent_ids"]["reviewer"]
        )
        self.write_selection_data(request_id, same_writer_primary)
        result = self.run_validator("docs", request_id=request_id, normalize_v5=False)
        self.assertEqual(1, result.returncode)
        self.assertIn("writer and primary reviewer must be different", result.stdout)

        risk_is_primary = copy.deepcopy(base)
        risk_review = next(
            review
            for review in risk_is_primary["semantic_review_closure"]["review_passes"]
            if review["reviewer_role"] == "risk"
        )
        risk_review["receipt"]["reviewer_agent_id"] = "reviewer-1"
        self.write_selection_data(request_id, risk_is_primary)
        result = self.run_validator("docs", request_id=request_id, normalize_v5=False)
        self.assertEqual(1, result.returncode)
        self.assertIn("independent risk reviewer", result.stdout)

        risk_drift = copy.deepcopy(base)
        risk_reviews = [
            review
            for review in risk_drift["semantic_review_closure"]["review_passes"]
            if review["reviewer_role"] == "risk"
        ]
        risk_reviews[-1]["receipt"]["reviewer_agent_id"] = "risk-reviewer-2"
        self.write_selection_data(request_id, risk_drift)
        result = self.run_validator("docs", request_id=request_id, normalize_v5=False)
        self.assertEqual(1, result.returncode)
        self.assertIn("must reuse one independent risk reviewer", result.stdout)

        writer_as_final = copy.deepcopy(base)
        final_review_id = writer_as_final["semantic_review_closure"]["final_gate"][
            "review_id"
        ]
        final_review = next(
            review
            for review in writer_as_final["semantic_review_closure"]["review_passes"]
            if review["review_id"] == final_review_id
        )
        writer_id = writer_as_final["persistent_agent_ids"]["writer"]
        final_review["receipt"]["reviewer_agent_id"] = writer_id
        attempt = writer_as_final["semantic_challenge"]["attempts"][0]
        attempt["reviewer_agent_id"] = writer_id
        attempt["receipt"] = copy.deepcopy(final_review["receipt"])
        self.write_selection_data(request_id, writer_as_final)
        result = self.run_validator("docs", request_id=request_id, normalize_v5=False)
        self.assertEqual(1, result.returncode)
        self.assertIn("independent from writer and primary", result.stdout)
        self.assertIn("challenger is not fresh from prior review work", result.stdout)

    def test_v5_terminal_review_order_follows_writers_and_bundle_reviews(self) -> None:
        request_id, base = self.write_v4_final_state(
            "20260721-220012-v5-review-order"
        )

        early_challenge = copy.deepcopy(base)
        spans = early_challenge["operation_metrics"]["spans"]
        final_review_id = early_challenge["semantic_review_closure"]["final_gate"][
            "review_id"
        ]
        final_span = next(span for span in spans if span["span_id"] == final_review_id)
        spans.remove(final_span)
        spans.insert(1, final_span)
        self.write_selection_data(request_id, early_challenge)
        self.write_test_operation_journal(
            self.selection_request_root(request_id), request_id, early_challenge
        )
        result = self.run_validator("docs", request_id=request_id, normalize_v5=False)
        self.assertEqual(1, result.returncode)
        self.assertIn(
            "must follow every basis-applicable bundle development/risk review",
            result.stdout,
        )
        self.assertIn("must follow the last bundle/writer correction", result.stdout)

        early_bundle_reviews = copy.deepcopy(base)
        spans = early_bundle_reviews["operation_metrics"]["spans"]
        moved = [
            span
            for span in spans
            if span["kind"] in {"development-review", "risk-review"}
            and span["scope"] != "selection-readiness"
        ]
        spans[:] = [span for span in spans if span not in moved]
        spans[1:1] = moved
        self.write_selection_data(request_id, early_bundle_reviews)
        self.write_test_operation_journal(
            self.selection_request_root(request_id), request_id, early_bundle_reviews
        )
        result = self.run_validator("docs", request_id=request_id, normalize_v5=False)
        self.assertEqual(1, result.returncode)
        self.assertIn("must follow its successful bundle/writer attempt", result.stdout)

    def test_v5_causal_order_uses_interleaved_journal_sequences(self) -> None:
        request_id, base = self.write_v4_final_state(
            "20260721-220014-v5-interleaved-order"
        )
        request_root = self.selection_request_root(request_id)
        journal_path = request_root / "operation-events.jsonl"
        base_events = [
            json.loads(line)
            for line in journal_path.read_text(encoding="utf-8").splitlines()
        ]

        def write_interleaved(start_span_id: str, finish_span_id: str) -> None:
            events = copy.deepcopy(base_events)
            start_event = next(
                event
                for event in events
                if event["event_type"] == "span-started"
                and event["payload"]["span_id"] == start_span_id
            )
            events.remove(start_event)
            finish_index = next(
                index
                for index, event in enumerate(events)
                if event["event_type"] == "span-finished"
                and event["payload"]["span_id"] == finish_span_id
            )
            events.insert(finish_index, start_event)
            previous_hash = ZERO_HASH
            for sequence, event in enumerate(events, start=1):
                event["sequence"] = sequence
                event["previous_hash"] = previous_hash
                event["event_hash"] = canonical_event_hash(event)
                previous_hash = event["event_hash"]
            journal_path.write_bytes(
                b"".join(canonical_json_bytes(event) + b"\n" for event in events)
            )
            state = copy.deepcopy(base)
            state["operation_metrics"] = reduce_operation_events(
                events, expected_request_id=request_id
            )
            self.write_selection_data(request_id, state)

        write_interleaved("programs-bundle-1", "accounts-risk-1")
        result = self.run_validator(
            "selection", request_id=request_id, normalize_v5=False
        )
        self.assertEqual(1, result.returncode)
        self.assertIn("must start after an applicable risk review", result.stdout)

        challenge_review_id = base["semantic_challenge"]["attempts"][0]["review_id"]
        write_interleaved(challenge_review_id, "programs-risk-1")
        result = self.run_validator(
            "selection", request_id=request_id, normalize_v5=False
        )
        self.assertEqual(1, result.returncode)
        self.assertIn(
            "must follow every basis-applicable bundle development/risk review",
            result.stdout,
        )

        validation_span_id = next(
            span["span_id"]
            for span in base["operation_metrics"]["spans"]
            if span["kind"] == "validation"
        )
        with self.assertRaisesRegex(
            OperationEventError, "after every other span finishes"
        ):
            write_interleaved(validation_span_id, challenge_review_id)
        result = self.run_validator("docs", request_id=request_id, normalize_v5=False)
        self.assertEqual(1, result.returncode)
        self.assertIn(
            "invalid authoritative operation event journal",
            result.stdout,
        )

        forged_projection = copy.deepcopy(base)
        validation_span = next(
            span
            for span in forged_projection["operation_metrics"]["spans"]
            if span["span_id"] == validation_span_id
        )
        validation_span["started_sequence"] = max(
            span["finished_sequence"]
            for span in forged_projection["operation_metrics"]["spans"]
            if "finished_sequence" in span
        )
        metric_errors: list[str] = []
        validate_operation_metrics(
            forged_projection,
            metric_errors,
            mode="final-validation",
            validation_scope="docs",
        )
        self.assertTrue(
            any(
                "final validation span must start after every other span finishes"
                in error
                for error in metric_errors
            ),
            metric_errors,
        )

    def test_v5_binding_trace_is_cross_bound_to_receipt_inputs(self) -> None:
        request_id, base = self.write_v4_final_state(
            "20260721-220013-v5-trace-receipt-binding"
        )

        locator_drift = copy.deepcopy(base)
        for trace in locator_drift["contract_binding_traces"]:
            trace["authority_locator"] = "source.txt:1-1"
            trace["implementation_locator"] = "source.txt:1-1"
        self.write_selection_data(request_id, locator_drift)
        result = self.run_validator("docs", request_id=request_id, normalize_v5=False)
        self.assertEqual(1, result.returncode)
        self.assertIn("must be present exactly in its review receipt", result.stdout)

        missing_consumer = copy.deepcopy(base)
        trace = missing_consumer["contract_binding_traces"][0]
        review = next(
            review
            for review in missing_consumer["semantic_review_closure"]["review_passes"]
            if review["review_id"] == trace["review_id"]
        )
        consumer_atom = trace["consumer_atom_key"]
        receipt = review["receipt"]
        receipt["basis_manifest"]["docs"] = [
            item
            for item in receipt["basis_manifest"]["docs"]
            if not item["path"].endswith(f"/{consumer_atom}-atom.md")
        ]
        receipt["basis_manifest_sha256"] = hashlib.sha256(
            json.dumps(
                receipt["basis_manifest"],
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        self.write_selection_data(request_id, missing_consumer)
        result = self.run_validator("docs", request_id=request_id, normalize_v5=False)
        self.assertEqual(1, result.returncode)
        self.assertIn("omits bound owner/consumer Atom", result.stdout)

        wrong_final_role = copy.deepcopy(base)
        trace = wrong_final_role["contract_binding_traces"][0]
        risk_review = next(
            review
            for review in wrong_final_role["semantic_review_closure"]["review_passes"]
            if review["review_id"] == trace["review_id"]
        )
        development_review = next(
            review
            for review in wrong_final_role["semantic_review_closure"]["review_passes"]
            if review["reviewer_role"] == "development"
            and review["scope"] == risk_review["scope"]
        )
        trace["review_id"] = development_review["review_id"]
        self.write_selection_data(request_id, wrong_final_role)
        result = self.run_validator("docs", request_id=request_id, normalize_v5=False)
        self.assertEqual(1, result.returncode)
        self.assertIn(
            "final review must be the current risk PASS for the risk atom bundle",
            result.stdout,
        )

    def test_v5_request_created_aid_orphan_is_final_only_and_refs_are_exact(self) -> None:
        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "domain-context",
                    "domain": "domain",
                    "candidate": "도메인 맥락",
                    "disposition": "write",
                    "selection_basis": "새 원자 문서를 작성한다.",
                    "candidate_atom_keys": ["domain-context"],
                }
            ],
            bundle_keys=["domain-context"],
            request_id="20260721-220005-v5-aid",
        )
        atom = self.write_atom(
            "domain/domain-context-atom.md",
            "domain-context",
        )
        atom.write_text(
            atom.read_text(encoding="utf-8").replace(
                "- 의도", "- [AID:domain-context.intent.001] 의도", 1
            ),
            encoding="utf-8",
        )
        state = self.read_selection_state(request_id)
        self.add_test_terminal_bundle_reviews(state)
        self.write_selection_data(request_id, state)
        self.normalize_v5_request(request_id, require_terminal=True)
        state = self.read_selection_state(request_id)
        self.write_selection_data(request_id, state)
        unlisted = self.run_validator(
            "selection",
            request_id=request_id,
            require_actions_final=True,
            normalize_v5=False,
        )
        self.assertEqual(1, unlisted.returncode)
        self.assertIn(
            "is missing from `created_aids`",
            unlisted.stdout,
        )
        state["created_aids"] = ["domain-context.intent.001"]
        self.write_selection_data(request_id, state)

        intermediate = self.run_validator(
            "selection", request_id=request_id, normalize_v5=False
        )
        self.assertEqual(0, intermediate.returncode, intermediate.stdout + intermediate.stderr)
        final = self.run_validator(
            "selection",
            request_id=request_id,
            require_actions_final=True,
            normalize_v5=False,
        )
        self.assertEqual(1, final.returncode)
        self.assertIn("has no external `[AID-REF:...]` consumer", final.stdout)

        atom.write_text(
            atom.read_text(encoding="utf-8").replace(
                "[AID:domain-context.intent.001] 의도",
                "[AID:domain-context.intent.001] "
                "[AID-REF:domain-context.intent.001] 의도",
                1,
            ),
            encoding="utf-8",
        )
        self.normalize_v5_request(request_id, require_terminal=True)
        same_block = self.run_validator(
            "selection",
            request_id=request_id,
            require_actions_final=True,
            normalize_v5=False,
        )
        self.assertEqual(1, same_block.returncode)
        self.assertIn("has no external `[AID-REF:...]` consumer", same_block.stdout)

        atom.write_text(
            atom.read_text(encoding="utf-8").replace(
                "- [AID:domain-context.intent.001] "
                "[AID-REF:domain-context.intent.001] 의도",
                "- 의도",
                1,
            ),
            encoding="utf-8",
        )
        state = self.read_selection_state(request_id)
        state["created_aids"] = []
        self.write_selection_data(request_id, state)
        self.normalize_v5_request(request_id, require_terminal=True)
        corrected = self.run_validator(
            "selection",
            request_id=request_id,
            require_actions_final=True,
            normalize_v5=False,
        )
        self.assertEqual(0, corrected.returncode, corrected.stdout + corrected.stderr)

        atom.write_text(
            atom.read_text(encoding="utf-8").replace(
                "- 의도", "- [AID:domain-context.intent.001] 의도", 1
            ),
            encoding="utf-8",
        )
        state = self.read_selection_state(request_id)
        state["created_aids"] = ["domain-context.intent.001"]
        self.write_selection_data(request_id, state)

        recognized = self.selection_request_root(request_id) / "post-write-review.md"
        recognized.write_text(
            "---\n"
            "example: '[AID:ignored-request.rules.001] "
            "[AID-REF:domain-context.intent.001]'\n"
            "---\n\n"
            "`[AID-REF:domain-context.intent.001]`\n\n"
            "```text\n[AID-REF:domain-context.intent.001]\n```\n\n"
            "    [AID-REF:domain-context.intent.001]\n\n"
            "<!-- [AID-REF:domain-context.intent.001] -->\n",
            encoding="utf-8",
        )
        self.normalize_v5_request(request_id, require_terminal=True)
        nonsemantic_consumer = self.run_validator(
            "selection",
            request_id=request_id,
            require_actions_final=True,
            normalize_v5=False,
        )
        self.assertEqual(1, nonsemantic_consumer.returncode)
        self.assertIn(
            "has no external `[AID-REF:...]` consumer",
            nonsemantic_consumer.stdout,
        )
        self.assertNotIn(
            "must reference AIDs with `[AID-REF:...]`",
            nonsemantic_consumer.stdout,
        )
        recognized.unlink()

        scratch = self.selection_request_root(request_id) / "scratch.md"
        scratch.write_text(
            "[AID-REF:domain-context.intent.001]\n",
            encoding="utf-8",
        )
        self.normalize_v5_request(request_id, require_terminal=True)
        unrecognized = self.run_validator(
            "selection",
            request_id=request_id,
            require_actions_final=True,
            normalize_v5=False,
        )
        self.assertEqual(1, unrecognized.returncode)
        self.assertIn("has no external `[AID-REF:...]` consumer", unrecognized.stdout)
        scratch.unlink()

        with atom.open("a", encoding="utf-8") as stream:
            stream.write("\n[AID-REF:domain-context.intent.001]\n")
        self.normalize_v5_request(request_id, require_terminal=True)
        final = self.run_validator(
            "selection",
            request_id=request_id,
            require_actions_final=True,
            normalize_v5=False,
        )
        self.assertEqual(0, final.returncode, final.stdout + final.stderr)

        dangling = self.write_atom("other/dangling-atom.md", "dangling")
        with dangling.open("a", encoding="utf-8") as stream:
            stream.write("\n[AID-REF:missing.intent.001]\n")
        result = self.run_validator("docs")
        self.assertEqual(1, result.returncode)
        self.assertIn("dangling AID reference `[AID:missing.intent.001]`", result.stdout)

    def test_v5_created_aid_consumer_requires_a_distinct_commonmark_block(self) -> None:
        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "domain-context",
                    "domain": "domain",
                    "candidate": "도메인 맥락",
                    "disposition": "write",
                    "selection_basis": "새 AID의 소비 블록을 검증한다.",
                    "candidate_atom_keys": ["domain-context"],
                }
            ],
            bundle_keys=["domain-context"],
            request_id="20260721-220006-v5-aid-blocks",
        )
        atom = self.write_atom("domain/domain-context-atom.md", "domain-context")
        base_text = atom.read_text(encoding="utf-8")
        state = self.read_selection_state(request_id)
        self.add_test_terminal_bundle_reviews(state)
        state["created_aids"] = ["domain-context.intent.001"]
        self.write_selection_data(request_id, state)

        variants = (
            (
                "same-paragraph-hash-tag",
                "- [AID:domain-context.intent.001] meaning\n"
                "  #tag [AID-REF:domain-context.intent.001]",
            ),
            (
                "same-list-item-after-blank",
                "- [AID:domain-context.intent.001] meaning\n\n"
                "  continuation [AID-REF:domain-context.intent.001]",
            ),
            (
                "same-list-item-nested-quote",
                "- [AID:domain-context.intent.001] meaning\n\n"
                "  > [AID-REF:domain-context.intent.001] nested quote",
            ),
            (
                "same-paragraph-multiline-code",
                "[AID:domain-context.intent.001] meaning `code\n"
                "more`\n"
                "[AID-REF:domain-context.intent.001] same paragraph",
            ),
            (
                "same-paragraph-multiline-comment",
                "[AID:domain-context.intent.001] meaning <!-- comment\n"
                "more -->\n"
                "[AID-REF:domain-context.intent.001] same paragraph",
            ),
            (
                "same-list-item-tab-continuation",
                "- [AID:domain-context.intent.001] meaning\n\n"
                "\t[AID-REF:domain-context.intent.001] same item",
            ),
            (
                "list-item-tab-indented-code",
                "- [AID:domain-context.intent.001] meaning\n\n"
                "\t\t[AID-REF:domain-context.intent.001] code",
            ),
            (
                "resumed-parent-list-item",
                "- [AID:domain-context.intent.001] parent\n"
                "  - child\n\n"
                "  [AID-REF:domain-context.intent.001] parent continuation",
            ),
        )
        for name, replacement in variants:
            with self.subTest(name=name):
                atom.write_text(
                    base_text.replace("- 의도", replacement, 1),
                    encoding="utf-8",
                )
                self.normalize_v5_request(request_id, require_terminal=True)
                result = self.run_validator(
                    "selection",
                    request_id=request_id,
                    require_actions_final=True,
                    normalize_v5=False,
                )
                self.assertEqual(1, result.returncode)
                self.assertIn(
                    "has no external `[AID-REF:...]` consumer", result.stdout
                )

        atom.write_text(
            base_text.replace(
                "- 의도", "- [AID:domain-context.intent.001] meaning", 1
            ),
            encoding="utf-8",
        )
        recognized = self.selection_request_root(request_id) / "post-write-review.md"
        recognized.write_text(
            "---\n"
            "notes: |\n"
            "  example\n"
            "  ---\n"
            "  [AID-REF:domain-context.intent.001]\n"
            "---\n\n"
            "No semantic consumer.\n",
            encoding="utf-8",
        )
        self.assertEqual(
            "No semantic consumer.",
            markdown_body_text(recognized.read_text(encoding="utf-8")).strip(),
        )
        self.normalize_v5_request(request_id, require_terminal=True)
        result = self.run_validator(
            "selection",
            request_id=request_id,
            require_actions_final=True,
            normalize_v5=False,
        )
        self.assertEqual(1, result.returncode)
        self.assertIn("has no external `[AID-REF:...]` consumer", result.stdout)
        recognized.unlink()

        hidden_consumers = (
            "[label]([AID-REF:domain-context.intent.001])",
            "![alt]([AID-REF:domain-context.intent.001])",
            "[label](url \"[AID-REF:domain-context.intent.001]\")",
            "[label](foo(bar) \"[AID-REF:domain-context.intent.001]\")",
            "[label](foo'bar/[AID-REF:domain-context.intent.001])",
            '[label](foo"bar/[AID-REF:domain-context.intent.001])',
            "[label](url\n  \"[AID-REF:domain-context.intent.001]\")",
            "[label](\n  [AID-REF:domain-context.intent.001]\n)",
            "[outer [inner]]([AID-REF:domain-context.intent.001])",
            "[outer\ninner]([AID-REF:domain-context.intent.001])",
            "[label][ref]\n\n"
            "[ref]: https://example.test/[AID-REF:domain-context.intent.001]",
            "[label][ref]\n\n"
            "[ref]: https://example.test\n"
            "    \"[AID-REF:domain-context.intent.001]\"",
            "[ref]: [AID-REF:domain-context.intent.001]",
            '<div data-ref="[AID-REF:domain-context.intent.001]">visible</div>',
            '<div\n data-ref="[AID-REF:domain-context.intent.001]">visible</div>',
            '<div title=">" '
            'data-ref="[AID-REF:domain-context.intent.001]">visible</div>',
            "<script>[AID-REF:domain-context.intent.001]</script>",
            "<style>[AID-REF:domain-context.intent.001]</style>",
            "<pre>[AID-REF:domain-context.intent.001]</pre>",
            "<textarea>[AID-REF:domain-context.intent.001]</textarea>",
        )
        for hidden_consumer in hidden_consumers:
            with self.subTest(hidden_consumer=hidden_consumer):
                recognized.write_text(hidden_consumer + "\n", encoding="utf-8")
                self.normalize_v5_request(request_id, require_terminal=True)
                result = self.run_validator(
                    "selection",
                    request_id=request_id,
                    require_actions_final=True,
                    normalize_v5=False,
                )
                self.assertEqual(1, result.returncode)
                self.assertIn(
                    "has no external `[AID-REF:...]` consumer", result.stdout
                )
        recognized.unlink()

        visible_consumers = (
            "[x](foo bar [AID-REF:domain-context.intent.001])",
            "[x](foo <[AID-REF:domain-context.intent.001]>)",
            "[ref]: url\n"
            "  prose [AID-REF:domain-context.intent.001]",
            r"\[AID-REF:domain-context.intent.001]",
            "<div>[AID-REF:domain-context.intent.001]</div>",
        )
        for visible_consumer in visible_consumers:
            with self.subTest(visible_consumer=visible_consumer):
                recognized.write_text(visible_consumer + "\n", encoding="utf-8")
                self.normalize_v5_request(request_id, require_terminal=True)
                result = self.run_validator(
                    "selection",
                    request_id=request_id,
                    require_actions_final=True,
                    normalize_v5=False,
                )
                self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        recognized.unlink()

        atom.write_text(
            base_text.replace(
                "- 의도",
                "[AID:domain-context.intent.001] meaning\n"
                "---\n"
                "[AID-REF:domain-context.intent.001] consumer",
                1,
            ),
            encoding="utf-8",
        )
        self.normalize_v5_request(request_id, require_terminal=True)
        result = self.run_validator(
            "selection",
            request_id=request_id,
            require_actions_final=True,
            normalize_v5=False,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_v5_nonstandard_json_constant_fails_without_traceback(self) -> None:
        request_id, _ = self.write_v4_owner_readiness_state(
            "20260721-220007-v5-nonstandard-json"
        )
        state_path = self.selection_state_path(request_id)
        raw = state_path.read_text(encoding="utf-8")
        state_path.write_text(
            raw.replace('"basis_revision": 1', '"basis_revision": NaN', 1),
            encoding="utf-8",
        )
        result = self.run_validator(
            "selection", request_id=request_id, normalize_v5=False
        )
        self.assertEqual(1, result.returncode)
        self.assertIn("non-standard JSON constant `NaN` is not allowed", result.stdout)
        self.assertNotIn("Traceback", result.stdout + result.stderr)

    def test_v5_aid_index_is_global_and_request_files_are_consumers_only(
        self,
    ) -> None:
        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "domain-context",
                    "domain": "domain",
                    "candidate": "도메인 맥락",
                    "disposition": "write",
                    "selection_basis": "AID 인덱스 경계를 검증한다.",
                    "candidate_atom_keys": ["domain-context"],
                }
            ],
            bundle_keys=["domain-context"],
            request_id="20260721-220010-v5-aid-index",
        )
        atom = self.write_atom("domain/domain-context-atom.md", "domain-context")
        atom.write_text(
            atom.read_text(encoding="utf-8").replace(
                "- 의도", "- [AID:shared.intent.001] 의도", 1
            ),
            encoding="utf-8",
        )
        inventory = self.selection_request_root(request_id) / "inventory.md"
        original_inventory = inventory.read_text(encoding="utf-8")

        inventory.write_text(
            original_inventory + "\n[AID:request.intent.001]\n",
            encoding="utf-8",
        )
        result = self.run_validator(
            "selection", request_id=request_id, normalize_v5=False
        )
        self.assertEqual(1, result.returncode)
        self.assertIn("must reference AIDs with `[AID-REF:...]`", result.stdout)

        inventory.write_text(
            original_inventory + "\n[AID-REF:missing.intent.001]\n",
            encoding="utf-8",
        )
        result = self.run_validator(
            "selection", request_id=request_id, normalize_v5=False
        )
        self.assertEqual(1, result.returncode)
        self.assertIn(
            "request-bound dangling AID reference `[AID:missing.intent.001]`",
            result.stdout,
        )

        inventory.write_text(original_inventory, encoding="utf-8")
        duplicate = self.write_atom("other/duplicate-atom.md", "duplicate")
        duplicate.write_text(
            duplicate.read_text(encoding="utf-8").replace(
                "- 의도", "- [AID:shared.intent.001] 의도", 1
            ),
            encoding="utf-8",
        )
        result = self.run_validator(
            "selection", request_id=request_id, normalize_v5=False
        )
        self.assertEqual(1, result.returncode)
        self.assertIn("duplicate AID `[AID:shared.intent.001]`", result.stdout)

    def test_v5_validator_uses_journal_as_authoritative_projection(self) -> None:
        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "domain-context",
                    "domain": "domain",
                    "candidate": "도메인 맥락",
                    "disposition": "write",
                    "selection_basis": "저널 투영을 검증한다.",
                    "candidate_atom_keys": ["domain-context"],
                }
            ],
            bundle_keys=["domain-context"],
            request_id="20260721-220006-v5-journal",
        )
        base = self.read_selection_state(request_id)
        invalid = copy.deepcopy(base)
        invalid["operation_metrics"]["started_at"] = "2026-07-20T07:59:59Z"
        self.write_selection_data(request_id, invalid)
        result = self.run_validator(
            "selection", request_id=request_id, normalize_v5=False
        )
        self.assertEqual(1, result.returncode)
        self.assertIn("must exactly equal the authoritative", result.stdout)

        self.write_selection_data(request_id, base)
        journal = self.selection_request_root(request_id) / "operation-events.jsonl"
        events = [json.loads(line) for line in journal.read_text(encoding="utf-8").splitlines()]
        events[0]["payload"]["started_at"] = "2026-07-20T07:59:59Z"
        journal.write_bytes(
            b"".join(canonical_json_bytes(event) + b"\n" for event in events)
        )
        result = self.run_validator(
            "selection", request_id=request_id, normalize_v5=False
        )
        self.assertEqual(1, result.returncode)
        self.assertIn("invalid authoritative operation event journal", result.stdout)

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
        self.add_test_semantic_review_operations(state)
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
            "changes primary reviewer without an append-only handoff",
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
        self.add_test_semantic_review_operations(state)
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
        self.add_test_semantic_review_operations(state)
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
        self.add_test_terminal_bundle_reviews(state)
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
        self.add_test_terminal_bundle_reviews(state)
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
            "`context_selection.version` must be exact `5`", result.stdout
        )
        self.assertIn(
            "create a new v5 request and do not resume, migrate, backfill, or dual-read",
            result.stdout,
        )

        missing_selection_state = self.read_selection_state(non_v4_request_id)
        missing_selection_state.pop("context_selection", None)
        self.write_selection_data(non_v4_request_id, missing_selection_state)
        result = self.run_validator(
            "selection", request_id=non_v4_request_id, normalize_v5=False
        )
        self.assertEqual(1, result.returncode)
        self.assertIn("must contain a `context_selection` object", result.stdout)
        self.assertIn("create a new v5 request", result.stdout)

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

    def test_selection_rejects_every_non_v5_context_selection_version(self) -> None:
        for version in (None, "1", "2", "3", "4", " 5 ", "6", 5):
            label = (
                "unversioned"
                if version is None
                else "padded-v5"
                if version == " 5 "
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
                    "`context_selection.version` must be exact `5`", result.stdout
                )
                self.assertIn("create a new v5 request", result.stdout)

    def test_selection_version_five_requires_closure_and_metrics(self) -> None:
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
            (
                "operation_metrics",
                "must exactly equal the authoritative operation event journal projection",
            ),
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
        cases.append((invalid, "must reuse the persistent reviewer active at its basis"))

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
                "scope": "programs-consumer",
                "attempt_id": "programs-attempt-1",
                "status": "finished",
                "started_at": "2026-07-20T08:00:00Z",
                "finished_at": "2026-07-20T08:00:01Z",
                "outcome": "completed",
            },
        )
        cases.append((invalid, "must finish before the first writer starts"))

        invalid = copy.deepcopy(state)
        invalid["operation_metrics"]["spans"].insert(
            0,
            {
                "span_id": "programs-writer-before-readiness",
                "kind": "writer",
                "scope": "programs-consumer",
                "attempt_id": "programs-attempt-before-readiness",
                "status": "finished",
                "started_at": "2026-07-20T08:00:01Z",
                "finished_at": "2026-07-20T08:00:01.500Z",
                "outcome": "completed",
            },
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
            "v5 risk-review scope must be an active/retired stable bundle_id",
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
            "v5 risk-review scope must be an active/retired stable bundle_id",
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
            "v5 development-review scope must be `selection-readiness` or an "
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
        self.add_test_semantic_review_operations(state)
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
                "scope": "accounts-owner",
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
        cross_basis["semantic_review_closure"]["basis_revision"] = 2
        cross_basis["semantic_fail_diagnostics"][1]["basis_revision"] = 2
        next(
            span
            for span in cross_basis["operation_metrics"]["spans"]
            if span.get("span_id") == "programs-risk-fail-1"
        )["basis_revision"] = 2
        cross_basis["dispatch_control"]["episodes"][0]["basis_revision"] = 2
        self.write_selection_data(request_id, cross_basis)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        overlapping = copy.deepcopy(state)
        overlapping["selection_readiness"]["basis_revision"] = 2
        overlapping["semantic_review_closure"]["basis_revision"] = 2
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
                "scope": "programs-consumer",
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
                },
                {
                    "review_id": "accounts-risk-1",
                    "reviewer_role": "risk",
                    "scope": "accounts-owner",
                    "basis_revision": 1,
                    "verdict": "PASS",
                    "status": "current",
                },
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
                    "pause_after_span_id": "accounts-risk-1",
                    "paused_at": "2026-07-20T08:00:40Z",
                    "basis_revision": 2,
                    "status": "open",
                }
            ],
        }
        self.add_test_semantic_review_operations(state)
        self.write_selection_data(request_id, state)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        current_risk_reuse = copy.deepcopy(state)
        current_risk_reuse["semantic_review_closure"]["review_passes"].extend(
            [
                {
                    "review_id": "programs-risk-1",
                    "reviewer_role": "risk",
                    "scope": "programs-consumer",
                    "basis_revision": 1,
                    "verdict": "PASS",
                    "status": "current",
                },
            ]
        )
        self.add_test_semantic_review_operations(current_risk_reuse)
        current_risk_reuse["dispatch_control"]["episodes"][0][
            "pause_after_span_id"
        ] = "programs-risk-1"
        current_risk_reuse["dispatch_control"]["episodes"][0][
            "paused_at"
        ] = "2026-07-20T08:00:40Z"
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
            "stale v5 PASS `programs-risk-1` must include exact required review "
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
        self.add_test_semantic_review_operations(state)
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
        self.add_test_semantic_review_operations(state)
        self.write_selection_data(request_id, state)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        open_dispatch = copy.deepcopy(state)
        open_dispatch["operation_metrics"]["spans"].append(
            {
                "span_id": "programs-bundle-after-late-cutoff",
                "kind": "bundle",
                "scope": "programs-consumer",
                "attempt_id": "programs-after-late-cutoff",
                "status": "finished",
                "started_at": "2026-07-20T08:00:03Z",
                "started_sequence": 4,
                "finished_at": "2026-07-20T08:00:04Z",
                "finished_sequence": 5,
                "outcome": "completed",
            }
        )
        self.write_selection_data(request_id, open_dispatch)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("after its pause cutoff", result.stdout)

        moved_cutoff = self.read_selection_state(request_id)
        moved_cutoff["dispatch_control"]["episodes"][0][
            "pause_after_span_id"
        ] = "programs-bundle-after-late-cutoff"
        self.write_selection_data(request_id, moved_cutoff)
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn("must equal its cutoff span finish sequence", result.stdout)

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
                "scope": "programs-consumer",
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
                    "pause_after_span_id": "accounts-owner-development-1",
                    "paused_at": "2026-07-20T08:00:02Z",
                    "basis_revision": 2,
                    "status": "open",
                }
            ],
        }
        self.add_test_semantic_review_operations(state)
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

    def test_request_bound_phases_reject_non_v5_operation_state(self) -> None:
        self.write_atom("domain/domain-context-atom.md", "domain-context")
        self.write_baseline()
        for version in (None, "1", "2", "3", "4", " 5 ", "6", 5):
            label = (
                "unversioned"
                if version is None
                else "padded-v5"
                if version == " 5 "
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
                        "`context_selection.version` must be exact `5`",
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
                    "scope": "domain-bundle",
                    "attempt_id": "domain-attempt-1",
                    "status": "finished",
                    "started_at": "2026-07-16T09:01:00+09:00",
                    "finished_at": "2026-07-16T09:05:00+09:00",
                    "outcome": "completed",
                },
                {
                    "span_id": "domain-writer-1",
                    "kind": "writer",
                    "scope": "domain-bundle",
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
                "scope": "domain-bundle",
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
            "semantic review PASS `domain-development-1`", result.stdout
        )
        self.assertIn(
            "semantic review PASS `project-baseline-1`", result.stdout
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
                    "scope": "domain-bundle",
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
                    "scope": "domain-bundle",
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
        self.assertIn("must exactly equal the authoritative", result.stdout)
        metric_errors: list[str] = []
        validate_operation_metrics(
            state,
            metric_errors,
            mode="active",
            validation_scope=None,
        )
        metric_output = "\n".join(metric_errors)
        self.assertIn("must be RFC 3339 with a timezone", metric_output)
        self.assertIn(
            "must omit `finished_at`, `finished_sequence`, and `outcome`",
            metric_output,
        )
        self.assertIn("`finished_at` must not precede `started_at`", metric_output)
        self.assertIn("must set `rerun_of` and `rerun_reason` together", metric_output)
        self.assertIn("must reference an earlier span", metric_output)
        self.assertIn("must not instrument a terminal metrics check", metric_output)

    def test_operation_metrics_rerun_provenance_respects_challenge_basis(self) -> None:
        state = {
            "context_selection": {"version": "5", "candidates": []},
            "bundle_queue": [],
            "selection_readiness": {"version": "1", "basis_revision": 1, "reviews": []},
            "semantic_review_closure": {
                "version": "1",
                "basis_revision": 2,
                "review_passes": [],
                "invalidations": [],
                "final_gate": {"required": False, "review_history": []},
            },
            "semantic_fail_diagnostics": [],
            "semantic_challenge": {
                "version": "1",
                "attempts": [
                    {"review_id": "challenge-fail-1", "basis_revision": 1},
                    {"review_id": "challenge-pass-2", "basis_revision": 2},
                ],
            },
            "operation_metrics": {
                "version": "1",
                "status": "active",
                "started_at": "2026-07-21T21:00:00+09:00",
                "spans": [
                    {
                        "span_id": "challenge-fail-1",
                        "kind": "integration-review",
                        "scope": "terminal-current-basis",
                        "attempt_id": "challenge-attempt-1",
                        "basis_revision": 1,
                        "status": "finished",
                        "started_at": "2026-07-21T21:01:00+09:00",
                        "started_sequence": 2,
                        "finished_at": "2026-07-21T21:02:00+09:00",
                        "finished_sequence": 3,
                        "outcome": "FAIL",
                    },
                    {
                        "span_id": "challenge-pass-2",
                        "kind": "integration-review",
                        "scope": "terminal-current-basis",
                        "attempt_id": "challenge-attempt-2",
                        "basis_revision": 2,
                        "status": "finished",
                        "started_at": "2026-07-21T21:03:00+09:00",
                        "started_sequence": 4,
                        "finished_at": "2026-07-21T21:04:00+09:00",
                        "finished_sequence": 5,
                        "outcome": "PASS",
                    },
                ],
            },
        }
        errors: list[str] = []
        validate_operation_metrics(
            state,
            errors,
            mode="active",
            validation_scope=None,
        )
        self.assertFalse(
            any("immediately prior failed" in error for error in errors),
            errors,
        )

        same_basis = copy.deepcopy(state)
        same_basis["semantic_challenge"]["attempts"][1]["basis_revision"] = 1
        same_basis["operation_metrics"]["spans"][1]["basis_revision"] = 1
        errors = []
        validate_operation_metrics(
            same_basis,
            errors,
            mode="active",
            validation_scope=None,
        )
        self.assertTrue(
            any("immediately prior failed" in error for error in errors),
            errors,
        )

        cross_basis_rerun = copy.deepcopy(state)
        cross_basis_rerun["operation_metrics"]["spans"][1].update(
            {
                "rerun_of": "challenge-fail-1",
                "rerun_reason": "new basis must remain a first attempt",
            }
        )
        errors = []
        validate_operation_metrics(
            cross_basis_rerun,
            errors,
            mode="active",
            validation_scope=None,
        )
        self.assertTrue(
            any("later-basis first attempt" in error for error in errors),
            errors,
        )

    def test_queue_adjacency_uses_current_readiness_review_epoch(self) -> None:
        def span(
            span_id: str,
            kind: str,
            scope: str,
            attempt_id: str,
            start: int,
            finish: int,
            *,
            outcome: str = "PASS",
        ) -> dict[str, object]:
            return {
                "span_id": span_id,
                "kind": kind,
                "scope": scope,
                "attempt_id": attempt_id,
                "basis_revision": 1,
                "status": "finished",
                "started_sequence": start,
                "finished_sequence": finish,
                "outcome": outcome,
            }

        readiness_reviews = [
            {
                "review_id": "readiness-old",
                "basis_revision": 1,
                "verdict": "PASS",
                "status": "superseded",
            },
            {
                "review_id": "readiness-current",
                "basis_revision": 1,
                "verdict": "PASS",
                "status": "current",
            },
        ]
        reviews = {
            "a-development-old": {
                "review_id": "a-development-old",
                "reviewer_role": "development",
                "scope": "a-bundle",
                "basis_revision": 1,
                "verdict": "PASS",
                "status": "superseded",
            },
            "a-risk-old": {
                "review_id": "a-risk-old",
                "reviewer_role": "risk",
                "scope": "a-bundle",
                "basis_revision": 1,
                "verdict": "PASS",
                "status": "superseded",
            },
            "a-development-current": {
                "review_id": "a-development-current",
                "reviewer_role": "development",
                "scope": "a-bundle",
                "basis_revision": 1,
                "verdict": "PASS",
                "status": "current",
            },
            "a-risk-current": {
                "review_id": "a-risk-current",
                "reviewer_role": "risk",
                "scope": "a-bundle",
                "basis_revision": 1,
                "verdict": "PASS",
                "status": "current",
            },
            "c-development-current": {
                "review_id": "c-development-current",
                "reviewer_role": "development",
                "scope": "c-bundle",
                "basis_revision": 1,
                "verdict": "PASS",
                "status": "current",
            },
        }
        state = {
            "bundle_queue": [
                {"bundle_id": "a-bundle", "expected_atom_keys": ["a"]},
                {"bundle_id": "c-bundle", "expected_atom_keys": ["c"]},
                {"bundle_id": "b-bundle", "expected_atom_keys": ["b"]},
            ],
            "risk_triggers": [{"atom_key": "a"}],
            "selection_readiness": {
                "version": "1",
                "basis_revision": 1,
                "reviews": readiness_reviews,
            },
            "semantic_review_closure": {"basis_revision": 1},
            "dispatch_control": {"status": "ready"},
            "operation_metrics": {
                "spans": [
                    span(
                        "readiness-old",
                        "development-review",
                        "selection-readiness",
                        "readiness-old-attempt",
                        2,
                        3,
                    ),
                    span("a-bundle-old", "bundle", "a-bundle", "a-old", 4, 5),
                    span("a-writer-old", "writer", "a-bundle", "a-old", 6, 7),
                    span(
                        "a-development-old",
                        "development-review",
                        "a-bundle",
                        "a-development-old-attempt",
                        8,
                        9,
                    ),
                    span(
                        "a-risk-old",
                        "risk-review",
                        "a-bundle",
                        "a-risk-old-attempt",
                        10,
                        11,
                    ),
                    # B was dispatched under the old queue [A, B]. The current
                    # queue [A, C, B] must not apply C -> B retroactively.
                    span("b-bundle-old", "bundle", "b-bundle", "b-old", 12, 13),
                    span("b-writer-old", "writer", "b-bundle", "b-old", 14, 15),
                    span(
                        "readiness-current",
                        "development-review",
                        "selection-readiness",
                        "readiness-current-attempt",
                        20,
                        21,
                    ),
                    span("a-bundle-current", "bundle", "a-bundle", "a-current", 22, 23),
                    span("a-writer-current", "writer", "a-bundle", "a-current", 24, 25),
                    span(
                        "a-development-current",
                        "development-review",
                        "a-bundle",
                        "a-development-current-attempt",
                        26,
                        27,
                    ),
                    span(
                        "a-risk-current",
                        "risk-review",
                        "a-bundle",
                        "a-risk-current-attempt",
                        28,
                        29,
                    ),
                    span("c-bundle-current", "bundle", "c-bundle", "c-current", 30, 31),
                    span("c-writer-current", "writer", "c-bundle", "c-current", 32, 33),
                    span(
                        "c-development-current",
                        "development-review",
                        "c-bundle",
                        "c-development-current-attempt",
                        34,
                        35,
                    ),
                    span("b-bundle-current", "bundle", "b-bundle", "b-current", 36, 37),
                    span("b-writer-current", "writer", "b-bundle", "b-current", 38, 39),
                ]
            },
        }

        errors: list[str] = []
        validate_semantic_review_operation_order(state, reviews, errors)
        self.assertEqual([], errors)

        before_current_risk = copy.deepcopy(state)
        next(
            item
            for item in before_current_risk["operation_metrics"]["spans"]
            if item["span_id"] == "c-bundle-current"
        )["started_sequence"] = 28
        errors = []
        validate_semantic_review_operation_order(before_current_risk, reviews, errors)
        self.assertTrue(
            any("applicable risk review" in error for error in errors), errors
        )

        stale_only = copy.deepcopy(reviews)
        stale_only["a-development-current"]["status"] = "superseded"
        stale_only["a-risk-current"]["status"] = "superseded"
        errors = []
        validate_semantic_review_operation_order(state, stale_only, errors)
        self.assertTrue(
            any("applicable development review" in error for error in errors), errors
        )

        during_readiness = copy.deepcopy(state)
        next(
            item
            for item in during_readiness["operation_metrics"]["spans"]
            if item["span_id"] == "a-bundle-current"
        )["started_sequence"] = 21
        errors = []
        validate_semantic_review_operation_order(during_readiness, reviews, errors)
        self.assertTrue(
            any("selection readiness review is in progress" in error for error in errors),
            errors,
        )

        reversed_current = copy.deepcopy(state)
        reversed_current["selection_readiness"]["reviews"][0]["status"] = "current"
        reversed_current["selection_readiness"]["reviews"][1]["status"] = "superseded"
        errors = []
        validate_semantic_review_operation_order(reversed_current, reviews, errors)
        self.assertTrue(
            any("must be the latest finished readiness review" in error for error in errors),
            errors,
        )

    def test_bundle_writer_validation_retry_provenance_is_basis_scoped(self) -> None:
        def metric(
            kind: str,
            suffix: str,
            basis: int,
            start: int,
            outcome: str,
        ) -> dict[str, object]:
            scope = "docs" if kind == "validation" else "domain-bundle"
            return {
                "span_id": f"{kind}-{suffix}",
                "kind": kind,
                "scope": scope,
                "attempt_id": f"{kind}-{suffix}-attempt",
                "basis_revision": basis,
                "status": "finished",
                "started_at": f"2026-07-21T21:00:{start:02d}+09:00",
                "started_sequence": start,
                "finished_at": f"2026-07-21T21:00:{start + 1:02d}+09:00",
                "finished_sequence": start + 1,
                "outcome": outcome,
            }

        def state_for(spans: list[dict[str, object]]) -> dict[str, object]:
            return {
                "context_selection": {"version": "5", "candidates": []},
                "bundle_queue": [{"bundle_id": "domain-bundle"}],
                "selection_readiness": {
                    "version": "1",
                    "basis_revision": 2,
                    "reviews": [],
                },
                "semantic_review_closure": {
                    "version": "1",
                    "basis_revision": 2,
                    "review_passes": [],
                    "invalidations": [],
                    "final_gate": {"required": False, "review_history": []},
                },
                "semantic_fail_diagnostics": [],
                "semantic_challenge": {"version": "1", "attempts": []},
                "operation_metrics": {
                    "version": "1",
                    "status": "active",
                    "started_at": "2026-07-21T21:00:00+09:00",
                    "spans": spans,
                },
            }

        for kind in ("bundle", "writer", "validation"):
            success_outcome = "completed" if kind in {"bundle", "writer"} else "PASS"
            wrong_outcome = "PASS" if kind in {"bundle", "writer"} else "completed"
            with self.subTest(kind=kind, case="kind-specific-outcome"):
                invalid_outcome = state_for(
                    [metric(kind, "invalid-outcome", 1, 2, wrong_outcome)]
                )
                errors: list[str] = []
                validate_operation_metrics(
                    invalid_outcome, errors, mode="active", validation_scope=None
                )
                self.assertTrue(
                    any("outcome must be" in error for error in errors), errors
                )

            with self.subTest(kind=kind, case="same-basis-missing-rerun"):
                same_basis = state_for(
                    [
                        metric(kind, "failed", 1, 2, "FAIL"),
                        metric(kind, "retry", 1, 4, success_outcome),
                    ]
                )
                errors = []
                validate_operation_metrics(
                    same_basis, errors, mode="active", validation_scope=None
                )
                self.assertTrue(
                    any("immediately prior failed" in error for error in errors),
                    errors,
                )

            with self.subTest(kind=kind, case="cross-basis-first-attempt"):
                cross_basis = state_for(
                    [
                        metric(kind, "failed", 1, 2, "FAIL"),
                        metric(kind, "new-basis", 2, 4, success_outcome),
                    ]
                )
                errors = []
                validate_operation_metrics(
                    cross_basis, errors, mode="active", validation_scope=None
                )
                self.assertEqual([], errors)

            with self.subTest(kind=kind, case="cross-basis-rerun"):
                cross_basis_rerun = state_for(
                    [
                        metric(kind, "failed", 1, 2, "FAIL"),
                        metric(kind, "new-basis", 2, 4, success_outcome),
                    ]
                )
                cross_basis_rerun["operation_metrics"]["spans"][1].update(
                    {
                        "rerun_of": f"{kind}-failed",
                        "rerun_reason": "basis changed",
                    }
                )
                errors = []
                validate_operation_metrics(
                    cross_basis_rerun, errors, mode="active", validation_scope=None
                )
                self.assertTrue(
                    any("later-basis first attempt" in error for error in errors),
                    errors,
                )

            with self.subTest(kind=kind, case="basis-regression"):
                regressed = state_for(
                    [
                        metric(kind, "basis-two", 2, 2, success_outcome),
                        metric(kind, "basis-one", 1, 4, success_outcome),
                    ]
                )
                errors = []
                validate_operation_metrics(
                    regressed, errors, mode="active", validation_scope=None
                )
                self.assertTrue(
                    any("must not regress" in error for error in errors), errors
                )

    def test_bundle_writer_pair_basis_is_bound_to_consuming_review(self) -> None:
        metrics_state = {
            "context_selection": {"version": "5", "candidates": []},
            "bundle_queue": [{"bundle_id": "domain-bundle"}],
            "selection_readiness": {"basis_revision": 2, "reviews": []},
            "semantic_review_closure": {
                "basis_revision": 2,
                "review_passes": [],
            },
            "semantic_fail_diagnostics": [],
            "semantic_challenge": {"attempts": []},
            "operation_metrics": {
                "version": "1",
                "status": "active",
                "started_at": "2026-07-21T21:00:00+09:00",
                "spans": [
                    {
                        "span_id": "domain-bundle-one",
                        "kind": "bundle",
                        "scope": "domain-bundle",
                        "attempt_id": "domain-attempt",
                        "basis_revision": 1,
                        "status": "finished",
                        "started_at": "2026-07-21T21:00:02+09:00",
                        "started_sequence": 2,
                        "finished_at": "2026-07-21T21:00:03+09:00",
                        "finished_sequence": 3,
                        "outcome": "completed",
                    },
                    {
                        "span_id": "domain-writer-two",
                        "kind": "writer",
                        "scope": "domain-bundle",
                        "attempt_id": "domain-attempt",
                        "basis_revision": 2,
                        "status": "finished",
                        "started_at": "2026-07-21T21:00:04+09:00",
                        "started_sequence": 4,
                        "finished_at": "2026-07-21T21:00:05+09:00",
                        "finished_sequence": 5,
                        "outcome": "completed",
                    },
                ],
            },
        }
        errors: list[str] = []
        validate_operation_metrics(
            metrics_state, errors, mode="active", validation_scope=None
        )
        self.assertTrue(
            any("must use one semantic basis_revision" in error for error in errors),
            errors,
        )

        for role, kind in (
            ("development", "development-review"),
            ("risk", "risk-review"),
        ):
            with self.subTest(role=role):
                review_id = f"domain-{role}-two"
                order_state = {
                    "bundle_queue": [{"bundle_id": "domain-bundle"}],
                    "risk_triggers": [],
                    "selection_readiness": {"basis_revision": 2, "reviews": []},
                    "semantic_review_closure": {"basis_revision": 2},
                    "operation_metrics": {
                        "spans": [
                            {
                                "span_id": "domain-bundle-one",
                                "kind": "bundle",
                                "scope": "domain-bundle",
                                "attempt_id": "domain-attempt",
                                "basis_revision": 1,
                                "status": "finished",
                                "started_sequence": 2,
                                "finished_sequence": 3,
                                "outcome": "completed",
                            },
                            {
                                "span_id": "domain-writer-one",
                                "kind": "writer",
                                "scope": "domain-bundle",
                                "attempt_id": "domain-attempt",
                                "basis_revision": 1,
                                "status": "finished",
                                "started_sequence": 4,
                                "finished_sequence": 5,
                                "outcome": "completed",
                            },
                            {
                                "span_id": review_id,
                                "kind": kind,
                                "scope": "domain-bundle",
                                "attempt_id": f"{review_id}-attempt",
                                "basis_revision": 2,
                                "status": "finished",
                                "started_sequence": 6,
                                "finished_sequence": 7,
                                "outcome": "PASS",
                            },
                        ]
                    },
                }
                review = {
                    review_id: {
                        "review_id": review_id,
                        "reviewer_role": role,
                        "scope": "domain-bundle",
                        "basis_revision": 2,
                        "verdict": "PASS",
                        "status": "current",
                    }
                }
                errors = []
                validate_semantic_review_operation_order(order_state, review, errors)
                self.assertTrue(
                    any(
                        "successful bundle/writer attempt" in error
                        and "same basis" in error
                        for error in errors
                    ),
                    errors,
                )

    def test_challenge_basis_array_must_match_journal_nonoverlap(self) -> None:
        request_id, state = self.write_v4_final_state(
            "20260722-000001-v5-challenge-journal-order"
        )
        first_attempt = state["semantic_challenge"]["attempts"][0]
        first_review_id = first_attempt["review_id"]
        state["semantic_review_closure"]["basis_revision"] = 2
        second_attempt = {
            "challenge_id": "challenge-basis-two",
            "basis_revision": 2,
            "mode": "dedicated",
            "review_id": "challenge-review-basis-two",
            "reviewer_agent_id": "challenger-basis-two",
            "primary_agent_id": first_attempt["primary_agent_id"],
            "excluded_inputs": copy.deepcopy(first_attempt["excluded_inputs"]),
            "verdict": "PASS",
            "receipt": self.make_test_review_receipt(
                self.selection_request_root(request_id),
                state,
                review_id="challenge-review-basis-two",
                agent_id="challenger-basis-two",
                role="challenger",
                scope="terminal-current-basis",
                basis_revision=2,
                verdict="PASS",
            ),
        }
        state["semantic_challenge"]["attempts"].append(second_attempt)
        spans = state["operation_metrics"]["spans"]
        first_index = next(
            index
            for index, item in enumerate(spans)
            if item["span_id"] == first_review_id
        )
        spans.insert(
            first_index,
            {
                "span_id": "challenge-review-basis-two",
                "kind": "integration-review",
                "scope": "terminal-current-basis",
                "attempt_id": "challenge-basis-two-attempt",
                "basis_revision": 2,
                "status": "finished",
                "started_at": "2026-07-20T08:00:14.100000Z",
                "finished_at": "2026-07-20T08:00:14.200000Z",
                "outcome": "PASS",
            },
        )
        self.write_test_operation_journal(
            self.selection_request_root(request_id), request_id, state
        )
        result = self.run_validator(
            "selection", request_id=request_id, normalize_v5=False
        )
        self.assertEqual(1, result.returncode)
        self.assertIn(
            "must start after prior attempt", result.stdout + result.stderr
        )

    def test_dedicated_challenge_waits_for_final_review_but_reuse_shares_span(
        self,
    ) -> None:
        for phase, validation_scope in (("docs", "docs"), ("baseline", "baseline")):
            with self.subTest(phase=phase):
                request_id, state = self.write_v4_final_state(
                    f"20260722-000002-v5-dedicated-{phase}",
                    validation_scope=validation_scope,
                )
                final_review_id = state["semantic_review_closure"]["final_gate"][
                    "review_id"
                ]
                reused = state["semantic_challenge"]["attempts"][0]
                self.assertEqual("reuse-final-review", reused["mode"])
                self.assertEqual(final_review_id, reused["review_id"])
                result = self.run_validator(
                    phase, request_id=request_id, normalize_v5=False
                )
                self.assertEqual(0, result.returncode, result.stdout + result.stderr)

                dedicated = copy.deepcopy(state)
                dedicated_review_id = f"dedicated-{phase}-challenge"
                dedicated_receipt = self.make_test_review_receipt(
                    self.selection_request_root(request_id),
                    dedicated,
                    review_id=dedicated_review_id,
                    agent_id=f"dedicated-{phase}-challenger",
                    role="challenger",
                    scope="terminal-current-basis",
                    basis_revision=1,
                    verdict="PASS",
                )
                dedicated["semantic_challenge"]["attempts"] = [
                    {
                        "challenge_id": dedicated_review_id,
                        "basis_revision": 1,
                        "mode": "dedicated",
                        "review_id": dedicated_review_id,
                        "reviewer_agent_id": f"dedicated-{phase}-challenger",
                        "primary_agent_id": "reviewer-1",
                        "excluded_inputs": [
                            "primary-report",
                            "primary-verdict",
                            "primary-evidence-summary",
                        ],
                        "verdict": "PASS",
                        "receipt": dedicated_receipt,
                    }
                ]
                spans = dedicated["operation_metrics"]["spans"]
                final_index = next(
                    index
                    for index, item in enumerate(spans)
                    if item["span_id"] == final_review_id
                )
                spans.insert(
                    final_index,
                    {
                        "span_id": dedicated_review_id,
                        "kind": "integration-review",
                        "scope": "terminal-current-basis",
                        "attempt_id": f"{dedicated_review_id}-attempt",
                        "status": "finished",
                        "started_at": "2026-07-20T08:00:14.100000Z",
                        "finished_at": "2026-07-20T08:00:14.200000Z",
                        "outcome": "PASS",
                    },
                )
                self.write_test_operation_journal(
                    self.selection_request_root(request_id), request_id, dedicated
                )
                result = self.run_validator(
                    phase, request_id=request_id, normalize_v5=False
                )
                self.assertEqual(1, result.returncode)
                self.assertIn(
                    "dedicated challenge must start after its basis-applicable final "
                    "integration/baseline PASS finishes",
                    result.stdout + result.stderr,
                )

    def test_operation_metrics_snapshot_progression_is_append_only(self) -> None:
        _, snapshot = self.write_v4_owner_readiness_state(
            "20260720-180101-v4-metrics-progression"
        )
        snapshot["operation_metrics"]["spans"].append(
            {
                "span_id": "accounts-writer-1",
                "kind": "writer",
                "scope": "accounts-owner",
                "attempt_id": "accounts-attempt-1",
                "basis_revision": 1,
                "status": "finished",
                "started_at": "2026-07-20T08:00:03Z",
                "started_sequence": 4,
                "finished_at": "2026-07-20T08:00:04Z",
                "finished_sequence": 5,
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
                "basis_revision": 1,
                "status": "finished",
                "started_at": "2026-07-20T08:00:05Z",
                "started_sequence": 6,
                "finished_at": "2026-07-20T08:00:06Z",
                "finished_sequence": 7,
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

        changed_start_sequence = copy.deepcopy(current)
        changed_start_sequence["operation_metrics"]["spans"][0][
            "started_sequence"
        ] = 8
        errors = []
        validate_state_snapshot_completeness(
            snapshot, changed_start_sequence, "snapshot", errors
        )
        self.assertTrue(
            any("field `started_sequence`" in error for error in errors),
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

    def test_v5_validator_fails_closed_on_pending_and_valid_suffix_truncation(self) -> None:
        request_id, state = self.write_v4_owner_readiness_state(
            "20260721-230001-v5-pending-truncation"
        )
        request_root = self.selection_request_root(request_id)
        pending = request_root / "operation-events.pending"
        pending.write_bytes(b"unrecovered\n")
        result = self.run_validator(
            "selection", request_id=request_id, normalize_v5=False
        )
        self.assertEqual(1, result.returncode)
        self.assertIn("unrecovered operation event pending record", result.stdout)
        pending.unlink()

        journal = request_root / "operation-events.jsonl"
        journal_lines = journal.read_bytes().splitlines(keepends=True)
        self.assertGreaterEqual(len(journal_lines), 3)
        journal.write_bytes(b"".join(journal_lines[:-1]))
        self.write_selection_data(request_id, state)
        result = self.run_validator(
            "selection", request_id=request_id, normalize_v5=False
        )
        self.assertEqual(1, result.returncode)
        self.assertIn("must exactly equal the authoritative", result.stdout)

    def test_v5_projection_mismatch_uses_authoritative_sequences_without_crash(self) -> None:
        request_id, state = self.write_v4_owner_readiness_state(
            "20260721-230002-v5-projection-mismatch"
        )
        state["operation_metrics"]["spans"][0]["finished_sequence"] = "bad"
        self.write_selection_data(request_id, state)
        result = self.run_validator(
            "selection", request_id=request_id, normalize_v5=False
        )
        self.assertEqual(1, result.returncode)
        self.assertIn("must exactly equal the authoritative", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_v5_queue_work_waits_for_prior_bundle_reviews(self) -> None:
        request_id, state = self.write_v4_final_state(
            "20260721-230003-v5-queue-order"
        )
        spans = state["operation_metrics"]["spans"]
        programs_work = [
            span
            for span in spans
            if span.get("kind") in {"bundle", "writer"}
            and span.get("scope") == "programs-consumer"
        ]
        spans[:] = [span for span in spans if span not in programs_work]
        insertion = next(
            index
            for index, span in enumerate(spans)
            if span.get("kind") in {"development-review", "risk-review"}
            and span.get("scope") == "accounts-owner"
        )
        spans[insertion:insertion] = programs_work
        self.write_test_operation_journal(
            self.selection_request_root(request_id), request_id, state
        )
        result = self.run_validator("docs", request_id=request_id, normalize_v5=False)
        self.assertEqual(1, result.returncode)
        self.assertIn("must start after an applicable", result.stdout)

    def test_v5_receipt_report_rejects_in_root_symlink_alias(self) -> None:
        request_id, state = self.write_v4_final_state(
            "20260721-230002-v5-report-symlink"
        )
        reviews = state["semantic_review_closure"]["review_passes"]
        source_receipt = reviews[0]["receipt"]
        aliased_receipt = reviews[1]["receipt"]
        source_report = self.root / source_receipt["report_path"]
        alias = self.selection_request_root(request_id) / "reviews" / "report-alias.md"
        alias.symlink_to(source_report.name)
        aliased_receipt["report_path"] = alias.relative_to(self.root).as_posix()
        aliased_receipt["report_sha256"] = source_receipt["report_sha256"]
        self.write_selection_data(request_id, state)

        result = self.run_validator(
            "docs", request_id=request_id, normalize_v5=False
        )
        self.assertEqual(1, result.returncode)
        self.assertIn("receipt report path must not use a symlink", result.stdout)

    def test_v5_revisions_must_be_reachable_from_source_head(self) -> None:
        tree = self._git("rev-parse", "HEAD^{tree}").stdout.strip()
        dangling = self._git("commit-tree", tree, "-m", "dangling revision").stdout.strip()
        self.assertNotEqual(self.commit, dangling)

        request_id = self.write_selection_state(
            [
                {
                    "candidate_id": "domain-context",
                    "domain": "domain",
                    "candidate": "도메인 맥락",
                    "disposition": "write",
                    "selection_basis": "고정 revision 도달성을 검증한다.",
                    "candidate_atom_keys": ["domain-context"],
                }
            ],
            bundle_keys=["domain-context"],
            source_commit=dangling,
            request_id="20260721-230003-v5-dangling-source",
        )
        result = self.run_validator("selection", request_id=request_id)
        self.assertEqual(1, result.returncode)
        self.assertIn(f"source commit `{dangling}` is not reachable", result.stdout)

        request_id, state = self.write_v4_final_state(
            "20260721-230004-v5-dangling-authority"
        )
        trace = state["contract_binding_traces"][0]
        trace["authority_revision"] = dangling
        self.write_selection_data(request_id, state)
        result = self.run_validator(
            "docs", request_id=request_id, normalize_v5=False
        )
        self.assertEqual(1, result.returncode)
        self.assertIn(
            "revision must be a reachable 40- or 64-character Git hash",
            result.stdout,
        )

    def test_v5_review_pass_spans_require_one_exact_receipt_owner(self) -> None:
        request_id, base = self.write_v4_final_state(
            "20260721-230004-v5-review-span-owner"
        )
        cases = (
            ("development-review", "accounts-owner"),
            ("risk-review", "accounts-owner"),
            ("integration-review", "affected-closure"),
            ("baseline-review", "project-wide"),
        )
        for index, (kind, scope) in enumerate(cases, start=1):
            with self.subTest(kind=kind):
                invalid = copy.deepcopy(base)
                spans = invalid["operation_metrics"]["spans"]
                validation_index = next(
                    position
                    for position, span in enumerate(spans)
                    if span.get("kind") == "validation"
                )
                spans.insert(
                    validation_index,
                    {
                        "span_id": f"unowned-{kind}",
                        "kind": kind,
                        "scope": scope,
                        "attempt_id": f"unowned-{kind}-attempt",
                        "basis_revision": 1,
                        "status": "finished",
                        "started_at": f"2026-07-20T08:00:16.{index}00000Z",
                        "finished_at": f"2026-07-20T08:00:16.{index}50000Z",
                        "outcome": "PASS",
                    },
                )
                self.write_selection_data(request_id, invalid)
                self.write_test_operation_journal(
                    self.selection_request_root(request_id), request_id, invalid
                )
                result = self.run_validator(
                    "docs", request_id=request_id, normalize_v5=False
                )
                self.assertEqual(1, result.returncode)
                self.assertIn(
                    "must have exactly one receipt-bearing readiness, semantic, "
                    "or dedicated challenge owner",
                    result.stdout,
                )

        for kind in ("integration-review", "baseline-review"):
            with self.subTest(uncontrolled_kind=kind):
                invalid = copy.deepcopy(base)
                spans = invalid["operation_metrics"]["spans"]
                validation_index = next(
                    position
                    for position, span in enumerate(spans)
                    if span.get("kind") == "validation"
                )
                spans.insert(
                    validation_index,
                    {
                        "span_id": f"uncontrolled-{kind}",
                        "kind": kind,
                        "scope": "arbitrary-scope",
                        "attempt_id": f"uncontrolled-{kind}-attempt",
                        "basis_revision": 1,
                        "status": "finished",
                        "started_at": "2026-07-20T08:00:16.600000Z",
                        "finished_at": "2026-07-20T08:00:16.700000Z",
                        "outcome": "FAIL",
                    },
                )
                self.write_selection_data(request_id, invalid)
                self.write_test_operation_journal(
                    self.selection_request_root(request_id), request_id, invalid
                )
                result = self.run_validator(
                    "docs", request_id=request_id, normalize_v5=False
                )
                self.assertEqual(1, result.returncode)
                self.assertIn(f"{kind} scope must be", result.stdout)

    def test_v5_selection_readiness_is_a_reserved_non_bundle_scope(self) -> None:
        request_id, base = self.write_v4_final_state(
            "20260721-230005-v5-reserved-readiness"
        )
        invalid = copy.deepcopy(base)
        invalid["bundle_queue"][0]["bundle_id"] = "selection-readiness"
        self.write_selection_data(request_id, invalid)
        result = self.run_validator(
            "selection", request_id=request_id, normalize_v5=False
        )
        self.assertEqual(1, result.returncode)
        self.assertIn("reserved for the readiness review", result.stdout)

        risk_scope = copy.deepcopy(base)
        risk_review = next(
            review
            for review in risk_scope["semantic_review_closure"]["review_passes"]
            if review.get("reviewer_role") == "risk"
        )
        risk_review["scope"] = "selection-readiness"
        risk_span = next(
            span
            for span in risk_scope["operation_metrics"]["spans"]
            if span.get("span_id") == risk_review["review_id"]
        )
        risk_span["scope"] = "selection-readiness"
        self.write_selection_data(request_id, risk_scope)
        self.write_test_operation_journal(
            self.selection_request_root(request_id), request_id, risk_scope
        )
        result = self.run_validator(
            "selection", request_id=request_id, normalize_v5=False
        )
        self.assertEqual(1, result.returncode)
        self.assertIn("risk scope must not be `selection-readiness`", result.stdout)

    def test_v5_final_validation_retry_requires_explicit_rerun_provenance(self) -> None:
        request_id, state = self.write_v4_final_state(
            "20260721-230004-v5-validation-rerun"
        )
        spans = state["operation_metrics"]["spans"]
        validation_index = next(
            index
            for index, span in enumerate(spans)
            if span.get("kind") == "validation"
        )
        spans.insert(
            validation_index,
            {
                "span_id": "docs-validation-failed-1",
                "kind": "validation",
                "scope": "docs",
                "attempt_id": "docs-validation-failed-attempt-1",
                "status": "finished",
                "started_at": "2026-07-20T08:00:16.300000Z",
                "finished_at": "2026-07-20T08:00:16.400000Z",
                "outcome": "FAIL",
            },
        )
        journal = self.selection_request_root(request_id) / "operation-events.jsonl"
        before = journal.read_bytes()
        with self.assertRaisesRegex(OperationEventError, "same-basis retry"):
            self.write_test_operation_journal(
                self.selection_request_root(request_id), request_id, state
            )
        self.assertEqual(before, journal.read_bytes())

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
        self.assertIn("must follow journal finish order", result.stdout)

        non_v4_snapshot = copy.deepcopy(state)
        non_v4_snapshot["context_selection"]["version"] = "3"
        errors = []
        validate_state_snapshot_completeness(
            non_v4_snapshot, state, "snapshot", errors
        )
        self.assertEqual(
            [
                "snapshot operation-state rollback requires "
                "context selection version `5`"
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
        self.normalize_v5_snapshot_state(
            "20260720-170007-v4-snapshot-bundle-guard", state
        )
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
            any("cannot map guarded v5 path" in error for error in errors), errors
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
        self.add_test_semantic_review_operations(state)
        self.write_selection_data(request_id, state)
        self.normalize_v5_request(request_id, require_terminal=False)
        state = self.read_selection_state(request_id)
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
        self.add_test_terminal_bundle_reviews(current)
        self.add_test_semantic_review_operations(current)
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
        self.normalize_v5_snapshot_state(request_id, reviewed_snapshot)
        readiness_two_span = next(
            copy.deepcopy(span)
            for span in reviewed_current["operation_metrics"]["spans"]
            if span.get("span_id") == "selection-readiness-2"
        )
        reviewed_current["operation_metrics"] = copy.deepcopy(
            reviewed_snapshot["operation_metrics"]
        )
        reviewed_current["operation_metrics"]["spans"].append(readiness_two_span)
        self.normalize_v5_snapshot_state(request_id, reviewed_current)
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
        self.add_test_semantic_review_operations(state)
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
                    "scope": "domain-bundle",
                    "attempt_id": "domain-attempt-1",
                    "status": "finished",
                    "started_at": "2026-07-20T08:00:03Z",
                    "finished_at": "2026-07-20T08:00:04Z",
                    "outcome": "completed",
                },
                {
                    "span_id": "domain-writer-1",
                    "kind": "writer",
                    "scope": "domain-bundle",
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

        self.assertEqual(
            1,
            state["selection_readiness"]["basis_revision"],
            "a semantic-only basis advance must keep its still-applicable readiness PASS",
        )
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
        self.add_test_semantic_review_operations(state)
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
            "stale v5 PASS `domain-risk-1` must include exact required review "
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
        self.add_test_semantic_review_operations(risk_neutral)
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
        self.add_test_semantic_review_operations(risk_changed)
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
            "affected bundle `outside-bundle` does not resolve to a v5 "
            "`bundle_queue.bundle_id`",
            result.stdout,
        )
        self.assertIn(
            "scope `outside-bundle` does not resolve to a v5 "
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
        self.write_atom("domain/example-atom.md", "example", with_aids=True)
        docs_result = self.run_validator("docs")
        self.assertEqual(0, docs_result.returncode, docs_result.stdout + docs_result.stderr)
        self.assertIn("1 atoms", docs_result.stdout)
        self.assertIn("[STRUCTURAL]", docs_result.stdout)
        self.assertNotIn("AIDs", docs_result.stdout)

        self.write_baseline()
        baseline_result = self.run_validator("baseline")
        self.assertEqual(0, baseline_result.returncode, baseline_result.stdout + baseline_result.stderr)
        self.assertIn("PASS baseline", baseline_result.stdout)

    def test_atom_without_aids_is_valid(self) -> None:
        self.write_atom("domain/context-atom.md", "context", with_aids=False)

        result = self.run_validator("docs")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("1 atoms", result.stdout)
        self.assertIn("[STRUCTURAL]", result.stdout)
        self.assertNotIn("AIDs", result.stdout)

    def test_aid_scanner_ignores_nonsemantic_markdown_tokens(self) -> None:
        atom = self.write_atom("domain/semantic-markdown-atom.md", "semantic-markdown")
        text = atom.read_text(encoding="utf-8")
        text = text.replace(
            "---\natom_key:",
            "---\n# [AID:ignored-frontmatter.rules.001] "
            "[AID-REF:missing-frontmatter.rules.001]\natom_key:",
            1,
        )
        text = text.replace(
            "- 관찰 결과",
            "- [AID-REF:semantic-markdown.rules.001] 관찰 결과",
            1,
        )
        text = text.replace(
            "- 규칙",
            "- [AID:semantic-markdown.rules.001] 규칙",
            1,
        )
        text += """

`[AID:ignored-inline.rules.001] [AID-REF:missing-inline.rules.001]`

```text
[AID:ignored-fence.rules.001]
[AID-REF:missing-fence.rules.001]
```

    [AID:ignored-indent.rules.001]
    [AID-REF:missing-indent.rules.001]

>     [AID-REF:missing-quoted-indent.rules.001]

> ```text
> [AID:ignored-quoted-fence.rules.001]
> [AID-REF:missing-quoted-fence.rules.001]
> ```

- ```text
  [AID:ignored-list-fence.rules.001]
  [AID-REF:missing-list-fence.rules.001]
  ```

<!-- [AID:ignored-comment.rules.001]
[AID-REF:missing-comment.rules.001] -->

<!-- [AID-REF:missing-unclosed-comment.rules.001]
"""
        atom.write_text(text, encoding="utf-8")

        result = self.run_validator("docs")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_aid_validation_fails_closed_without_markdown_it(self) -> None:
        request_id, _ = self.write_v4_final_state(
            "20260722-000005-v5-markdown-parser-required"
        )
        original = validator_module.MarkdownIt
        validator_module.MarkdownIt = None
        try:
            for arguments in (
                ["--root", str(self.root), "--phase", "docs"],
                [
                    "--root",
                    str(self.root),
                    "--phase",
                    "selection",
                    "--request-id",
                    request_id,
                    "--require-actions-final",
                ],
            ):
                with self.subTest(arguments=arguments):
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        returncode = validator_module.main(arguments)
                    self.assertEqual(1, returncode)
                    self.assertIn(
                        "semantic AID validation requires the plugin-bundled "
                        "`markdown-it-py`/`mdurl` runtime",
                        output.getvalue(),
                    )
        finally:
            validator_module.MarkdownIt = original

    def test_validator_loads_plugin_vendored_runtimes_without_site_packages(
        self,
    ) -> None:
        probe = (
            "import scripts.validate_atomic_docs as validator; "
            "print(validator.yaml.__file__); "
            "print(validator._markdown_it.__file__); "
            "print(validator._mdurl.__file__)"
        )
        result = subprocess.run(
            [sys.executable, "-B", "-S", "-c", probe],
            cwd=ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        vendor_root = (ROOT / "scripts" / "_vendor").resolve()
        origins = result.stdout.splitlines()
        self.assertEqual(3, len(origins), result.stdout)
        for origin in origins:
            self.assertTrue(Path(origin).resolve().is_relative_to(vendor_root), origin)
        self.assertTrue((vendor_root / "THIRD_PARTY_NOTICES.md").is_file())
        source_inventory = subprocess.run(
            [
                "git",
                "ls-files",
                "--cached",
                "--others",
                "--exclude-standard",
                "--",
                "scripts/_vendor",
            ],
            cwd=ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(
            0,
            source_inventory.returncode,
            source_inventory.stdout + source_inventory.stderr,
        )
        packaged_paths = source_inventory.stdout.splitlines()
        self.assertTrue(packaged_paths)
        self.assertFalse(
            [
                path
                for path in packaged_paths
                if Path(path).suffix.lower() in {".pyc", ".so", ".pyd", ".dll", ".dylib"}
            ]
        )

    def test_aid_scanner_does_not_let_indented_code_interrupt_paragraphs(self) -> None:
        atom = self.write_atom("domain/indent-continuation-atom.md", "indent-continuation")
        with atom.open("a", encoding="utf-8") as stream:
            stream.write(
                "\nProse\n"
                "    [AID-REF:missing-indent-cont.rules.001]\n\n"
                "> Prose\n"
                ">     [AID-REF:missing-quote-indent-cont.rules.001]\n\n"
                "- Prose\n"
                "      [AID-REF:missing-list-indent-cont.rules.001]\n"
            )
        result = self.run_validator("docs")
        self.assertEqual(1, result.returncode)
        for aid_id in (
            "missing-indent-cont.rules.001",
            "missing-quote-indent-cont.rules.001",
            "missing-list-indent-cont.rules.001",
        ):
            self.assertIn(f"dangling AID reference `[AID:{aid_id}]`", result.stdout)

        ignored = """
Prose

    [AID-REF:ignored-indent-code.rules.001]

	[AID-REF:ignored-tab-indent-code.rules.001]

> Prose
>
>     [AID-REF:ignored-quote-indent-code.rules.001]

>		[AID-REF:ignored-quote-tab-code.rules.001]

- Prose

      [AID-REF:ignored-list-indent-code.rules.001]

- Prose

		[AID-REF:ignored-list-tab-code.rules.001]

- Prose

    ~~~text
    [AID-REF:ignored-list-tilde-fence.rules.001]
    ~~~

- Prose

	~~~text
	[AID-REF:ignored-list-tab-fence.rules.001]
	~~~

# Heading
    [AID-REF:ignored-heading-code.rules.001]

> # Quoted heading
>     [AID-REF:ignored-quoted-heading-code.rules.001]

***
    [AID-REF:ignored-break-code.rules.001]

| header |
| --- |
| value |
    [AID-REF:ignored-after-table-code.rules.001]
"""
        semantic = "\n".join(
            line for line, _ in markdown_lines_with_block(ignored)
        )
        self.assertNotIn("ignored-indent-code", semantic)
        self.assertNotIn("ignored-tab-indent-code", semantic)
        self.assertNotIn("ignored-quote-indent-code", semantic)
        self.assertNotIn("ignored-quote-tab-code", semantic)
        self.assertNotIn("ignored-list-indent-code", semantic)
        self.assertNotIn("ignored-list-tab-code", semantic)
        self.assertNotIn("ignored-list-tilde-fence", semantic)
        self.assertNotIn("ignored-list-tab-fence", semantic)
        self.assertNotIn("ignored-heading-code", semantic)
        self.assertNotIn("ignored-quoted-heading-code", semantic)
        self.assertNotIn("ignored-break-code", semantic)
        self.assertNotIn("ignored-after-table-code", semantic)

    def test_aid_scanner_only_strips_mapping_yaml_frontmatter(self) -> None:
        mapping = "---\natom_key: example\n---\nsemantic body"
        self.assertEqual("semantic body", markdown_body_text(mapping))

        thematic_break = (
            "---\n"
            "[AID-REF:missing-thematic.rules.001]\n"
            "---\n"
            "outer prose"
        )
        self.assertEqual(thematic_break, markdown_body_text(thematic_break))
        semantic_lines = "\n".join(
            line for line, _ in markdown_lines_with_block(
                markdown_body_text(thematic_break)
            )
        )
        self.assertIn("[AID-REF:missing-thematic.rules.001]", semantic_lines)

    def test_aid_scanner_reprocesses_outer_prose_after_nested_fence_ends(self) -> None:
        markdown = """
> ```text
> [AID-REF:ignored-quoted-fence.rules.001]
[AID-REF:visible-after-quote.rules.001]

- ```text
  [AID-REF:ignored-list-fence.rules.001]
[AID-REF:visible-after-list.rules.001]
"""
        semantic_lines = "\n".join(
            line for line, _ in markdown_lines_with_block(markdown)
        )
        self.assertNotIn("ignored-quoted-fence", semantic_lines)
        self.assertNotIn("ignored-list-fence", semantic_lines)
        self.assertIn("[AID-REF:visible-after-quote.rules.001]", semantic_lines)
        self.assertIn("[AID-REF:visible-after-list.rules.001]", semantic_lines)

    def test_aid_scanner_tracks_commonmark_paragraph_and_list_item_blocks(self) -> None:
        paragraph = markdown_lines_with_block(
            "[AID:example.intent.001] meaning\n"
            "#tag [AID-REF:example.intent.001]"
        )
        self.assertEqual(paragraph[0][1], paragraph[1][1])

        list_item = markdown_lines_with_block(
            "- [AID:example.intent.001] meaning\n\n"
            "  continuation [AID-REF:example.intent.001]"
        )
        self.assertEqual(list_item[0][1], list_item[1][1])

        nested_quote = markdown_lines_with_block(
            "- [AID:example.intent.001] meaning\n\n"
            "  > [AID-REF:example.intent.001] nested quote"
        )
        self.assertEqual(nested_quote[0][1], nested_quote[1][1])

        tab_continuation = markdown_lines_with_block(
            "- [AID:example.intent.001] meaning\n\n"
            "\t[AID-REF:example.intent.001] same item"
        )
        self.assertEqual(tab_continuation[0][1], tab_continuation[1][1])

        for resumed_parent in (
            "- [AID:example.intent.001] parent\n"
            "  - child\n\n"
            "  [AID-REF:example.intent.001] parent continuation",
            "- [AID:example.intent.001] parent\n"
            "  - child\n\n"
            "  # [AID-REF:example.intent.001] parent heading",
            "- [AID:example.intent.001] parent\n"
            "  - child\n\n"
            "  > [AID-REF:example.intent.001] parent quote",
        ):
            with self.subTest(resumed_parent=resumed_parent):
                blocks = markdown_lines_with_block(resumed_parent)
                self.assertEqual(blocks[0][1], blocks[-1][1])

        for markdown in (
            "[AID:example.intent.001] meaning `code\n"
            "more`\n"
            "[AID-REF:example.intent.001] same paragraph",
            "[AID:example.intent.001] meaning <!-- comment\n"
            "more -->\n"
            "[AID-REF:example.intent.001] same paragraph",
        ):
            with self.subTest(multiline_inline=markdown):
                blocks = markdown_lines_with_block(markdown)
                self.assertEqual(blocks[0][1], blocks[-1][1])

        separated = markdown_lines_with_block(
            "[AID:example.intent.001] meaning\n"
            "---\n"
            "[AID-REF:example.intent.001] consumer"
        )
        self.assertNotEqual(separated[0][1], separated[-1][1])

        for markdown in (
            "[AID:example.intent.001] meaning\n"
            "> [AID-REF:example.intent.001] consumer",
            "> [AID:example.intent.001] meaning\n\n"
            "[AID-REF:example.intent.001] consumer",
            "- [AID:example.intent.001] meaning\n"
            "  - [AID-REF:example.intent.001] nested consumer",
            "| identity | meaning |\n"
            "| --- | --- |\n"
            "| [AID:example.intent.001] | definition |\n"
            "| [AID-REF:example.intent.001] | consumer |",
            "> | identity | meaning |\n"
            "> | --- | --- |\n"
            "> | [AID:example.intent.001] | definition |\n"
            "> | [AID-REF:example.intent.001] | consumer |",
            "- [AID:example.intent.001] parent\n"
            "    - [AID-REF:example.intent.001] nested child",
            "1. [AID:example.intent.001] parent\n"
            "    1. [AID-REF:example.intent.001] nested child",
            "- [AID:example.intent.001] parent\n"
            "\t- [AID-REF:example.intent.001] nested child",
            "1. [AID:example.intent.001] parent\n"
            "\t1. [AID-REF:example.intent.001] nested child",
            "a \\| b | c\n"
            "--- | ---\n"
            "[AID:example.intent.001] | definition\n"
            "[AID-REF:example.intent.001] | consumer",
        ):
            with self.subTest(markdown=markdown):
                blocks = markdown_lines_with_block(markdown)
                definition_block = next(
                    block for line, block in blocks if "[AID:" in line
                )
                reference_block = next(
                    block for line, block in blocks if "[AID-REF:" in line
                )
                self.assertNotEqual(definition_block, reference_block)

        for markdown in (
            "> [AID:example.intent.001] meaning\n"
            "[AID-REF:example.intent.001] lazy continuation",
            "[AID:example.intent.001] meaning\n"
            "|literal [AID-REF:example.intent.001] continuation",
        ):
            with self.subTest(lazy_markdown=markdown):
                blocks = markdown_lines_with_block(markdown)
                self.assertEqual(blocks[0][1], blocks[-1][1])

    def test_aid_scanner_rejects_empty_tokens_and_invalid_backtick_fence(self) -> None:
        atom = self.write_atom("domain/malformed-aid-atom.md", "malformed-aid")
        with atom.open("a", encoding="utf-8") as stream:
            stream.write(
                "\n[AID:]\n[AID-REF:]\n"
                "```bad`info\n"
                "[AID-REF:missing-invalid-fence.rules.001]\n"
                "```\n"
            )

        result = self.run_validator("docs")
        self.assertEqual(1, result.returncode)
        self.assertIn("malformed AID `[AID:]`", result.stdout)
        self.assertIn("malformed AID reference `[AID-REF:]`", result.stdout)
        self.assertIn(
            "dangling AID reference `[AID:missing-invalid-fence.rules.001]`",
            result.stdout,
        )
        edge_cases = (
            (
                "missing-joined-comment.rules.001",
                "<!`code`-- [AID-REF:missing-joined-comment.rules.001]",
            ),
            (
                "missing-escaped-comment.rules.001",
                "\\<!-- [AID-REF:missing-escaped-comment.rules.001] -->",
            ),
            (
                "missing-after-comment.rules.001",
                "<!-- `code -->` [AID-REF:missing-after-comment.rules.001]",
            ),
            (
                "missing-after-code.rules.001",
                "`code \\` [AID-REF:missing-after-code.rules.001]`",
            ),
            (
                "missing-inline-comment-blank.rules.001",
                "Prose <!-- [AID-REF:missing-inline-comment-blank.rules.001]\n\n"
                "closing -->",
            ),
            (
                "missing-code-blank.rules.001",
                "`code\n\n[AID-REF:missing-code-blank.rules.001]\n`",
            ),
            (
                "missing-heading-boundary.rules.001",
                "`code\n# [AID-REF:missing-heading-boundary.rules.001] `",
            ),
            (
                "missing-list-boundary.rules.001",
                "`code\n- [AID-REF:missing-list-boundary.rules.001] `",
            ),
            (
                "missing-table-boundary.rules.001",
                "`code\nh | x\n--- | ---\n"
                "[AID-REF:missing-table-boundary.rules.001] | x `",
            ),
            (
                "missing-pseudo-table-indent.rules.001",
                "Prose\n---|---\n"
                "    [AID-REF:missing-pseudo-table-indent.rules.001]",
            ),
            (
                "missing-quote-blank.rules.001",
                "> `code\n>\n"
                "> [AID-REF:missing-quote-blank.rules.001]\n> `",
            ),
            (
                "missing-list-four-space.rules.001",
                "- Prose\n\n"
                "    [AID-REF:missing-list-four-space.rules.001]",
            ),
            (
                "missing-list-five-space.rules.001",
                "- Prose\n\n"
                "     [AID-REF:missing-list-five-space.rules.001]",
            ),
        )
        for index, (aid_id, markdown) in enumerate(edge_cases, start=1):
            with self.subTest(aid_id=aid_id):
                edge_atom = self.write_atom(
                    f"domain/scanner-edge-{index}-atom.md", f"scanner-edge-{index}"
                )
                with edge_atom.open("a", encoding="utf-8") as stream:
                    stream.write(f"\n{markdown}\n")
                edge_result = self.run_validator("docs")
                self.assertEqual(1, edge_result.returncode)
                self.assertIn(
                    f"dangling AID reference `[AID:{aid_id}]`",
                    edge_result.stdout,
                )
                edge_atom.unlink()

    def test_aid_scanner_strips_inline_code_before_html_comments(self) -> None:
        markdown = (
            "`<!--` [AID-REF:visible-after-inline-marker.rules.001]\n"
            "[AID-REF:visible-on-next-line.rules.001]"
        )
        semantic_lines = "\n".join(
            line for line, _ in markdown_lines_with_block(markdown)
        )
        self.assertIn(
            "[AID-REF:visible-after-inline-marker.rules.001]", semantic_lines
        )
        self.assertIn("[AID-REF:visible-on-next-line.rules.001]", semantic_lines)

        edge_cases = (
            "<!`code`-- [AID-REF:visible-no-joined-comment.rules.001]",
            "\\<!-- [AID-REF:visible-escaped-comment.rules.001] -->",
            "<!-- `code -->` [AID-REF:visible-after-comment.rules.001]",
            "`code \\` [AID-REF:visible-after-code.rules.001]`",
        )
        for edge_case in edge_cases:
            with self.subTest(edge_case=edge_case):
                visible = "\n".join(
                    line for line, _ in markdown_lines_with_block(edge_case)
                )
                self.assertIn("[AID-REF:visible-", visible)

    def test_aid_scanner_masks_nonprose_destinations_and_raw_elements(self) -> None:
        hidden_cases = (
            "[label]([AID-REF:hidden-link.rules.001])",
            "![alt]([AID-REF:hidden-image.rules.001])",
            '[label](foo(bar) "[AID-REF:hidden-title.rules.001]")',
            "[label](foo'bar/[AID-REF:hidden-quote-url.rules.001])",
            '[label](foo"bar/[AID-REF:hidden-double-quote-url.rules.001])',
            '[label](url\n  "[AID-REF:hidden-multiline-title.rules.001]")',
            "[label](\n  [AID-REF:hidden-multiline-destination.rules.001]\n)",
            "[outer [inner]]([AID-REF:hidden-nested-label.rules.001])",
            "[outer\ninner]([AID-REF:hidden-soft-label.rules.001])",
            "[![alt]([AID-REF:hidden-nested-image.rules.001])](outer)",
            "[label][ref]\n\n"
            "[ref]: url\n    \"[AID-REF:hidden-reference-title.rules.001]\"",
            "[ref]: [AID-REF:hidden-reference-destination.rules.001]",
            r"[foo\]]: [AID-REF:hidden-escaped-reference.rules.001]",
            "[foo\nbar]: [AID-REF:hidden-soft-reference.rules.001]",
            '<div\n data-ref="[AID-REF:hidden-attribute.rules.001]">visible</div>',
            '<div title=">" data-ref="[AID-REF:hidden-late-attribute.rules.001]">'
            "visible</div>",
            "<script>[AID-REF:hidden-script.rules.001]</script>",
            "<style>[AID-REF:hidden-style.rules.001]</style>",
            "<pre>[AID-REF:hidden-pre.rules.001]</pre>",
            "<textarea>[AID-REF:hidden-textarea.rules.001]</textarea>",
        )
        for hidden_case in hidden_cases:
            with self.subTest(hidden_case=hidden_case):
                semantic = "\n".join(
                    line for line, _ in markdown_lines_with_block(hidden_case)
                )
                self.assertNotIn("[AID-REF:hidden-", semantic)

        visible_cases = (
            r"\[AID-REF:visible-escaped.rules.001]",
            r"[\[AID-REF:visible-link-label.rules.001\]](url)",
            r"![\[AID-REF:visible-image-alt.rules.001\]](image.png)",
            "<div>[AID-REF:visible-html-body.rules.001]</div>",
            "[x](foo bar [AID-REF:visible-invalid-link.rules.001])",
            "[x](foo <[AID-REF:visible-invalid-angle.rules.001]>)",
            "[ref]: url\n"
            "  prose [AID-REF:visible-reference-follow.rules.001]",
            "[[inner](https://inner.test)]"
            "([AID-REF:visible-invalid-nested-link.rules.001])",
        )
        for visible_case in visible_cases:
            with self.subTest(visible_case=visible_case):
                semantic = "\n".join(
                    line for line, _ in markdown_lines_with_block(visible_case)
                )
                self.assertIn("[AID-REF:visible-", semantic)

    def test_aid_scanner_ignores_multiline_inline_code(self) -> None:
        markdown = """
`example
[AID-REF:ignored-multiline-inline.rules.001]
`
[AID-REF:visible-after-multiline-inline.rules.001]
"""
        semantic_lines = "\n".join(
            line for line, _ in markdown_lines_with_block(markdown)
        )
        self.assertNotIn("ignored-multiline-inline", semantic_lines)
        self.assertIn(
            "[AID-REF:visible-after-multiline-inline.rules.001]", semantic_lines
        )

    def test_unclosed_inline_code_does_not_hide_dangling_aid_reference(self) -> None:
        atom = self.write_atom("domain/unclosed-inline-atom.md", "unclosed-inline")
        with atom.open("a", encoding="utf-8") as stream:
            stream.write("\n`example [AID-REF:missing-inline.rules.001]\n")

        result = self.run_validator("docs")
        self.assertEqual(1, result.returncode)
        self.assertIn(
            "dangling AID reference `[AID:missing-inline.rules.001]`",
            result.stdout,
        )

    def test_duplicate_atom_key_and_aid_fail(self) -> None:
        self.write_atom("domain/first-atom.md", "duplicate", with_aids=True)
        self.write_atom("domain/second-atom.md", "duplicate", with_aids=True)
        result = self.run_validator("docs")
        self.assertEqual(1, result.returncode)
        self.assertIn("duplicate atom_key `duplicate`", result.stdout)
        self.assertIn("duplicate AID `[AID:duplicate.intent.001]`", result.stdout)

    def test_duplicate_aid_across_different_atoms_fails(self) -> None:
        self.write_atom(
            "domain/first-atom.md", "first", aid_key="shared-origin", with_aids=True
        )
        self.write_atom(
            "domain/second-atom.md", "second", aid_key="shared-origin", with_aids=True
        )
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
        self.write_atom(
            "domain/new-owner-atom.md",
            "new-owner",
            aid_key="original-owner",
            with_aids=True,
        )
        result = self.run_validator("docs")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_aid_section_code_must_match_containing_section(self) -> None:
        path = self.write_atom("domain/example-atom.md", "example", with_aids=True)
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
        self.write_atom(
            "domain/active-atom.md", "active", aid_key="shared-origin", with_aids=True
        )
        self.write_atom(
            "other/other-atom.md", "other", aid_key="shared-origin", with_aids=True
        )

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
