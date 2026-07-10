from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills" / "atomic-docs"
SKILL = SKILL_DIR / "SKILL.md"
REFS = SKILL_DIR / "references"
OPENAI_YAML = SKILL_DIR / "agents" / "openai.yaml"
PLUGIN_JSON = ROOT / ".codex-plugin" / "plugin.json"
VALIDATOR = ROOT / "scripts" / "validate_atomic_docs.py"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def refs(*names: str) -> str:
    return "\n".join(read(REFS / name) for name in names)


def assert_all(test: unittest.TestCase, text: str, values: list[str] | tuple[str, ...]) -> None:
    for value in values:
        test.assertIn(value, text)


class DocsSkillTests(unittest.TestCase):
    def test_skill_entry_routes_every_direct_reference(self) -> None:
        text = read(SKILL)
        self.assertIn("name: atomic-docs", text)
        self.assertIn("same-functional-behavior reconstruction", text)
        expected = {
            "docs-root-and-config.md",
            "atomic-document-contract.md",
            "atomization-criteria-contract.md",
            "source-convention-and-domain-policy.md",
            "service-logic-coverage.md",
            "atom-format-and-judgment.md",
            "language-policy.md",
            "refresh-flow.md",
            "criteria-flow.md",
            "docs-generation-flow.md",
            "reviewer-perspectives.md",
            "project-documents-and-inventory.md",
            "source-baseline-and-change-plan.md",
            "validation-contract.md",
            "change-judgment-policy.md",
            "atomic-graph.md",
            "stageflow-integration.md",
        }
        self.assertEqual(expected, {path.name for path in REFS.glob("*.md")})
        for name in expected:
            self.assertIn(f"references/{name}", text)

    def test_skill_and_references_remain_progressively_disclosed(self) -> None:
        skill_text = read(SKILL)
        self.assertLessEqual(len(skill_text.splitlines()), 200)
        self.assertLessEqual(len(skill_text.split()), 2500)
        for path in sorted(REFS.glob("*.md")):
            self.assertLessEqual(
                len(read(path).splitlines()),
                200,
                f"{path.name} exceeds the direct-reference line budget",
            )

    def test_ui_metadata_matches_source_reconstruction_goal(self) -> None:
        text = read(OPENAI_YAML)
        assert_all(
            self,
            text,
            (
                'display_name: "Atomic Docs"',
                'short_description: "Docs for same-behavior reconstruction and review."',
                'default_prompt: "Use $atomic-docs',
                "same-functional-behavior reconstruction",
                "fresh docs-only reviewer",
            ),
        )

    def test_plugin_manifest_exposes_atomic_docs(self) -> None:
        text = read(PLUGIN_JSON)
        assert_all(
            self,
            text,
            (
                '"skills": "./skills/"',
                "Use atomic-docs to create storage-mode-aware project documentation.",
                "Use atomic-docs to refresh atom files from source-code changes.",
                "Use atomic-docs to inspect intent, implementation, planned changes, and gaps.",
            ),
        )

    def test_storage_config_supports_repository_and_submodule(self) -> None:
        text = read(REFS / "docs-root-and-config.md")
        assert_all(
            self,
            text,
            (
                "Do not assume a hardcoded `docs/` root",
                "Supported storage modes are `submodule` and `repository`",
                '"storage_mode": "submodule"',
                '"storage_mode": "repository"',
                '"baseline_metadata_path": "source-baseline.json"',
                "Partial or targeted operations must not create or update this file",
                "<plugin-root>/scripts/validate_atomic_docs.py",
                "do not look for a validator under the target project's `scripts/` directory",
            ),
        )

    def test_user_facing_language_precedes_internal_terms(self) -> None:
        text = refs("language-policy.md", "docs-root-and-config.md", "criteria-flow.md")
        assert_all(
            self,
            text,
            (
                "쉬운 설명 + 원문 식별자",
                "문서 저장 방식",
                "현재 프로젝트 안의 폴더에 저장",
                "별도 문서 저장소/submodule에 저장",
                "문서 저장 위치",
                "atomic docs 설정 파일",
                "문서 작성 기준 초안",
                "Do not reduce this message to raw",
            ),
        )

    def test_operation_state_is_separate_from_durable_docs(self) -> None:
        text = refs(
            "docs-generation-flow.md",
            "atomization-criteria-contract.md",
            "project-documents-and-inventory.md",
            "stageflow-integration.md",
        )
        assert_all(
            self,
            text,
            (
                ".stageflow/atomic-docs/index.json",
                ".stageflow/atomic-docs/sessions/<session-id>/current.json",
                ".stageflow/atomic-docs/requests/<request-id>/state.json",
                ".stageflow/atomic-docs/requests/<request-id>/work-state.json",
                "must not become the live progress ledger",
                "operation-local by default",
                "not a Stageflow request",
            ),
        )

    def test_project_documents_are_not_atoms(self) -> None:
        text = refs("atomic-document-contract.md", "project-documents-and-inventory.md")
        for path in (
            "project/atomization-criteria.md",
            "project/project-goal.md",
            "project/project-glossary.md",
            "project/source-convention.md",
            "project/service-logic-inventory.md",
        ):
            self.assertIn(path, text)
        assert_all(
            self,
            text,
            (
                "Project documents are non-atom documents",
                "must not require frontmatter `atom_key`",
                "must not require AID values",
                "must not use `graph_edges`",
                "one-line term definitions",
            ),
        )

    def test_atom_path_identity_and_required_sections(self) -> None:
        text = refs("atomic-document-contract.md", "atom-format-and-judgment.md")
        assert_all(
            self,
            text,
            (
                "<doc-root>/<domain-path>/<file-slug>-atom.md",
                "globally unique across the docs set",
                "lower-kebab-case",
                "Intent",
                "Rules",
                "Current Implementation",
                "Planned Changes",
                "Gaps",
            ),
        )

    def test_aid_creation_prefix_and_cross_atom_stability_are_compatible(self) -> None:
        text = read(REFS / "atom-format-and-judgment.md")
        assert_all(
            self,
            text,
            (
                "[AID:<atom_key>.<section-code>.<NNN>]",
                "current owning atom's stable `atom_key` as their creation prefix",
                "preserved AID prefix may identify the atom where the AID was created",
                "valid and must not be treated as an ownership mismatch",
                "Resolve current ownership from the containing file's frontmatter `atom_key`",
                "Do not renumber existing AID values",
            ),
        )

    def test_compact_criteria_uses_shared_rules_and_result_table(self) -> None:
        text = refs("atomization-criteria-contract.md", "criteria-flow.md")
        for heading in (
            "공통 Atom 후보 기준",
            "공통 소스 근거 기준",
            "공통 분리/병합 기준",
            "공통 해당 없음/미해결 처리",
        ):
            self.assertIn(heading, text)
        self.assertIn(
            "관점 | 적용 상태 | 프로젝트 근거/후보 | 공통 기준 예외 | 미해결 질문",
            text,
        )
        for state in ("Atom 후보", "소스 근거만", "해당 없음", "미해결"):
            self.assertIn(state, text)
        self.assertIn("do not repeat these rules for every perspective", text)
        self.assertIn("Do not repeat the shared atom/evidence/split/not-applicable rules", text)
        self.assertNotIn("every entry under `Atom화 관점` with these exact visible subfields", text)

    def test_criteria_keeps_domain_discovery_and_atom_candidates_separate(self) -> None:
        text = refs(
            "atomization-criteria-contract.md",
            "criteria-flow.md",
            "source-convention-and-domain-policy.md",
        )
        assert_all(
            self,
            text,
            (
                "durable domain/category boundary map",
                "full discovery candidate map",
                "behavior-level `Atom 후보 맵`",
                "accepted-scope rules",
                "project-native",
                "broad roots",
                "concrete business aggregates",
                "leaf workflows",
            ),
        )

    def test_criteria_review_and_user_handoff_are_gated(self) -> None:
        text = read(REFS / "criteria-flow.md")
        assert_all(
            self,
            text,
            (
                "independent criteria-review subagent",
                "Continue until PASS",
                "PASS means ready for user review; it does not approve the criteria",
                "문서 작성 기준에서 정한 핵심 원칙",
                "도메인/범위 후보",
                "실제 atom 후보 또는 분리 후보",
                "아직 불확실한 점과 승인 차단 항목",
                "지금 승인하면 허용되는 것과 아직 허용되지 않는 것",
                "문서 작성 기준 승인은 완료됐고, 아직 실제 서비스 로직 문서는 작성하지 않았다",
            ),
        )

    def test_source_coverage_is_behavior_oriented_and_reconstructable(self) -> None:
        text = refs("service-logic-coverage.md", "atom-format-and-judgment.md")
        assert_all(
            self,
            text,
            (
                "natural-language service logic standard",
                "conditions, branches, state transitions, validation",
                "transaction or idempotency behavior",
                "persistence side effects",
                "external calls",
                "recovery behavior",
                "same functional behavior from the docs without rereading source",
                "A bare list of source identifiers",
                "Context atoms are not a shortcut for behavior coverage",
                "over-compressed",
            ),
        )

    def test_reconstruction_review_is_docs_only_and_source_fidelity_is_separate(self) -> None:
        text = refs(
            "service-logic-coverage.md",
            "docs-generation-flow.md",
            "reviewer-perspectives.md",
        )
        assert_all(
            self,
            text,
            (
                "fresh docs-only reviewer",
                "managed docs in scope",
                "approved criteria/project context",
                "Do not give it the source tree",
                "operation inventory",
                "source evidence packet",
                "actual source access",
                "must FAIL when it needs source",
                "do not create a separate probe artifact",
                "Partial reconstruction PASS applies only",
                "must not be reported as project-wide readiness",
            ),
        )
        self.assertNotIn("reconstruction-probe.json", text)

    def test_required_aids_keep_verification_conditions_inline(self) -> None:
        text = read(REFS / "atom-format-and-judgment.md")
        assert_all(
            self,
            text,
            (
                "confirmed required `Intent`",
                "`approved_required_change`",
                "observable verification condition",
                "in that same item",
                "Do not require a separate acceptance AID",
                "independently reviewable meaning",
            ),
        )

    def test_explicit_implementation_compliance_reuses_post_write_review(self) -> None:
        text = read(SKILL) + refs("docs-generation-flow.md", "change-judgment-policy.md")
        assert_all(
            self,
            text,
            (
                "Only Atomic Impl or an explicit docs/code compliance operation",
                ".stageflow/atomic-docs/requests/<request-id>/post-write-review.md",
                "## 구현 검증",
                "docs basis",
                "implementation basis",
                "관련 AID | 구현 근거 | 검증 근거 | 판정 또는 gap",
                "Normal docs generation",
                "project inventory",
                "`work-state.json`",
                "affected AID rows",
                "changed in-scope required AIDs",
                "drafts this section after implementation review",
                "finalizes the same section after final docs/code compliance",
            ),
        )
        self.assertNotIn("verification-trace.json", text)

    def test_source_discovery_includes_runtime_relevant_auxiliary_surfaces(self) -> None:
        text = refs(
            "service-logic-coverage.md",
            "source-baseline-and-change-plan.md",
            "refresh-flow.md",
        )
        for source_surface in (
            "DB and validation schemas",
            "migrations",
            "route configuration",
            "runtime settings",
            "behavior-describing tests",
        ):
            self.assertIn(source_surface, text)
        assert_all(
            self,
            text,
            (
                "supporting evidence rather than a substitute for reachable production behavior",
                "Exclude generated, build, vendor, formatting",
                "owned by a real `atom_key`/AID, recorded as a coverage gap",
            ),
        )

    def test_high_risk_behavior_requires_structured_coverage(self) -> None:
        text = read(REFS / "service-logic-coverage.md")
        for category in (
            "Account/auth/admin management",
            "delete/approve actions",
            "payment/refund behavior",
            "external integration",
            "persistence mutation",
            "idempotency",
            "failure recovery",
        ):
            self.assertIn(category, text)
        assert_all(
            self,
            text,
            (
                "payload/field matrix",
                "branch matrix",
                "state/persistence effect matrix",
                "failure/recovery matrix",
            ),
        )

    def test_inventory_is_operation_local_and_closes_to_atoms(self) -> None:
        text = read(REFS / "project-documents-and-inventory.md")
        assert_all(
            self,
            text,
            (
                "operation-local by default",
                "behavior-oriented, not method-oriented",
                "conditions and branches",
                "validation or permission checks",
                "state transitions",
                "persistence side effects",
                "error handling",
                "recovery behavior",
                "owning `atom_key`/AID",
                "delete or ignore the operation-local inventory",
            ),
        )

    def test_domain_bundles_use_one_writer_and_four_reviewers(self) -> None:
        flow = read(REFS / "docs-generation-flow.md")
        reviewers = read(REFS / "reviewer-perspectives.md")
        assert_all(
            self,
            flow,
            (
                "sequential queue",
                "exactly one writer and exactly four independent draft reviewers",
                "Do not run domain bundles in parallel by default",
                "Do not rerun unaffected PASS results",
                "Do not start the next bundle until all four perspectives PASS",
                "reopen that bundle",
            ),
        )
        for role in (
            "Domain Draft Atom Boundary / Context Hygiene Reviewer",
            "Domain Draft Source Closure / Fact Fidelity Reviewer",
            "Domain Draft Implementation Reconstruction / High-Risk Reviewer",
            "Domain Draft Reporting Reviewer",
        ):
            self.assertIn(role, reviewers)

    def test_reviewer_principle_files_and_answer_sheet_are_explicit(self) -> None:
        text = read(REFS / "reviewer-perspectives.md")
        for reference in (
            "atomic-document-contract.md",
            "atom-format-and-judgment.md",
            "atomization-criteria-contract.md",
            "source-convention-and-domain-policy.md",
            "service-logic-coverage.md",
            "change-judgment-policy.md",
            "source-baseline-and-change-plan.md",
            "docs-generation-flow.md",
            "project-documents-and-inventory.md",
        ):
            self.assertIn(reference, text)
        assert_all(
            self,
            text,
            (
                "principle files reviewed",
                "Can the same domain behavior be implemented from these docs alone?",
                "AID claim -> checked entry path -> null/blank/default/fallback/exception branch -> source evidence",
                "cannot replace a missing reviewer",
            ),
        )

        final_reconstruction = text.split(
            "### Final Implementation Reconstruction / High-Risk Reviewer", 1
        )[1].split("### Final Baseline / Reporting Reviewer", 1)[0]
        for reference in (
            "service-logic-coverage.md",
            "atom-format-and-judgment.md",
            "atomic-document-contract.md",
        ):
            self.assertIn(reference, final_reconstruction)

        assert_all(
            self,
            text,
            (
                "operation-state evidence for reporting or ownership checks",
                "Never provide operation-state evidence to a docs-only reconstruction reviewer",
            ),
        )

    def test_final_reviewers_are_cross_domain_not_duplicate_domain_reviews(self) -> None:
        text = refs("docs-generation-flow.md", "reviewer-perspectives.md")
        for role in (
            "Final Atom Boundary / Context Hygiene Reviewer",
            "Final Source Closure / Fact Fidelity Reviewer",
            "Final Implementation Reconstruction / High-Risk Reviewer",
            "Final Baseline / Reporting Reviewer",
        ):
            self.assertIn(role, text)
        assert_all(
            self,
            text,
            (
                "do not repeat every row-level or branch-level domain check",
                "Do not redo isolated domain matrices",
                "cross-domain ownership",
                "end-to-end flows that cross domains",
                "only reviewer perspective that can approve global baseline",
                "reopen the affected bundle",
            ),
        )

    def test_graph_impact_discovery_does_not_trust_existing_edges_alone(self) -> None:
        text = refs("atomic-graph.md", "reviewer-perspectives.md")
        assert_all(
            self,
            text,
            (
                "Existing graph edges are not proof",
                "domain/common context",
                "glossary meaning and source-of-truth rules",
                "shared payload/state/storage/permission/integration contracts",
                "operation-inventory ownership",
                "Do not create a separate impact-trace artifact",
                "uninspected boundaries",
            ),
        )
        self.assertNotIn("impact-trace.json", text)

    def test_required_subagents_are_authorized_inside_accepted_scope(self) -> None:
        text = read(REFS / "docs-generation-flow.md")
        assert_all(
            self,
            text,
            (
                "Accepted bootstrap scope authorizes criteria-review and revision cycles",
                "do not require separate approval merely to run",
                "deletion, migration, push, an external service call",
                "Do not stop because a required subagent was not named again",
                "is not a Goal-blocked state",
            ),
        )

    def test_goal_gate_precedes_docs_generation(self) -> None:
        text = read(REFS / "docs-generation-flow.md")
        assert_all(
            self,
            text,
            (
                "Bootstrap criteria drafting and criteria-review/revision do not require a Codex Goal",
                "call `create_goal` before creating project docs, inventory, atom files, graph edges",
                "source-to-docs-to-code reconstruction requirement",
                "If Goal creation is unavailable or fails, stop before docs generation",
                "Complete the Goal only after",
            ),
        )

    def test_global_baseline_is_full_project_only(self) -> None:
        baseline = read(REFS / "source-baseline-and-change-plan.md")
        flow = read(REFS / "docs-generation-flow.md")
        validation = read(REFS / "validation-contract.md")
        text = baseline + flow + validation
        assert_all(
            self,
            text,
            (
                '"version": "1"',
                '"source_commit": "<40-or-64-character-git-hash>"',
                '"coverage": "project-wide"',
                "Partial or targeted operations must not create, replace, or advance baseline metadata",
                "source_commit_observed",
                "Never use this operation-local value to advance",
                "four draft-review PASS results",
            ),
        )
        self.assertIn("or partial scope are invalid", validation)

    def test_judgment_policy_keeps_distinct_labels_and_evidence(self) -> None:
        text = refs("change-judgment-policy.md", "atom-format-and-judgment.md")
        for label in (
            "matches_confirmed_intent",
            "bug_or_regression",
            "missing_required_behavior",
            "unapproved_implemented_behavior",
            "out_of_scope_behavior",
            "confirmation_needed",
            "deferred_decision",
            "docs_stale",
        ):
            self.assertIn(label, text)
        assert_all(
            self,
            text,
            (
                "source evidence",
                "confirmed or inferred basis",
                "next action",
                "related AID values",
                "Do not collapse bug, missing required behavior",
            ),
        )

    def test_korean_docs_keep_fixed_identifiers_but_not_english_scaffolds(self) -> None:
        text = read(REFS / "language-policy.md")
        assert_all(
            self,
            text,
            (
                "Intent",
                "Current Implementation",
                "atom_key",
                "[AID:paid-order-processing.impl.003]",
                "Korean-First Template Policy",
                "판정 라벨",
                "영향받는 동작",
                "다음 조치",
                "No Example Leakage",
                "Do not copy reference example wording",
            ),
        )
        for forbidden in ("affected behavior", "next action", "source evidence", "judgment label"):
            self.assertIn(forbidden, text)

    def test_source_convention_remains_non_atom_interpretation_context(self) -> None:
        text = refs(
            "source-convention-and-domain-policy.md",
            "project-documents-and-inventory.md",
        )
        assert_all(
            self,
            text,
            (
                "project/source-convention.md",
                "non-atom document",
                "runtime-impacting conventions",
                "Non-runtime code style",
                "must also appear as natural-language behavior",
                "cannot support `bug_or_regression`",
            ),
        )

    def test_atomic_graph_uses_stable_keys_and_mutable_paths(self) -> None:
        text = read(REFS / "atomic-graph.md")
        assert_all(
            self,
            text,
            (
                "graph_edges",
                "target_key",
                "target_path",
                "reason",
                "target atom's stable frontmatter `atom_key`",
                "`target_path` is stale",
                "Graph edges may only target existing atom files",
                "Do not create a root graph output by default",
            ),
        )

    def test_stageflow_integration_respects_separate_gates(self) -> None:
        text = read(REFS / "stageflow-integration.md")
        assert_all(
            self,
            text,
            (
                "Respect Stageflow definition, implementation-plan, implementation, review, and approval gates",
                "Writing Stageflow request artifacts does not mean managed docs files are approved",
                "Source files are the default evidence source",
                "must not be used to bypass or satisfy Stageflow gates",
                "approved Stageflow artifact or user decision",
            ),
        )

    def test_validation_contract_points_to_plugin_bundled_read_only_tool(self) -> None:
        text = read(REFS / "validation-contract.md")
        self.assertTrue(VALIDATOR.is_file())
        assert_all(
            self,
            text,
            (
                "<plugin-root>/scripts/validate_atomic_docs.py",
                "--phase bootstrap",
                "--phase docs",
                "--phase baseline",
                "Never search for or invoke",
                "The validator is read-only",
                "semantic quality remains the responsibility",
            ),
        )


if __name__ == "__main__":
    unittest.main()
