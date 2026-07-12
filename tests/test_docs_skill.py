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
        self.assertIn("development decisions, implementation review, and change-impact analysis", text)
        self.assertIn("they do not replace the source tree", text)
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

    def test_ui_metadata_matches_development_decision_goal(self) -> None:
        text = read(OPENAI_YAML)
        assert_all(
            self,
            text,
            (
                'display_name: "Atomic Docs"',
                'short_description: "Docs for development decisions and implementation review."',
                'default_prompt: "Use $atomic-docs',
                "product intent",
                "without mirroring the source tree",
            ),
        )

    def test_skill_does_not_use_source_replacement_as_quality_target(self) -> None:
        text = read(SKILL) + read(OPENAI_YAML) + "\n".join(
            read(path) for path in sorted(REFS.glob("*.md"))
        )
        assert_all(
            self,
            text,
            (
                "they do not replace the source tree",
                "decision completeness",
                "internal technical choices remain free",
            ),
        )
        for obsolete in (
            "same-functional-behavior reconstruction",
            "docs-only reconstruction reviewer",
            "implementation-reconstruction-ready",
            "exactly four independent draft reviewers",
        ):
            self.assertNotIn(obsolete, text)

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
                "glossary entry is too shallow to resolve",
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

    def test_aids_are_selective_instead_of_line_level_inventory(self) -> None:
        text = read(REFS / "atom-format-and-judgment.md")
        assert_all(
            self,
            text,
            (
                "durable, independently referenceable meaning",
                "Do not assign AIDs to routine explanatory prose",
                "mechanical source summaries",
                "every evidence row",
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
                "discovery candidate map proportional to the requested scope",
                "behavior-level `Atom 후보 맵`",
                "accepted-scope rules",
                "project-wide source feature inventory only when",
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

    def test_source_coverage_is_decision_complete_and_proportional(self) -> None:
        text = refs("service-logic-coverage.md", "atom-format-and-judgment.md")
        assert_all(
            self,
            text,
            (
                "durable development-decision standard",
                "must not rediscover from scattered code or invent during implementation",
                "observable verification condition",
                "related domains, shared contracts, graph relationships, and conflicts",
                "Do not narrate every function call",
                "Stop adding detail when every remaining choice is an internal technical choice",
                "Do not use atom count, file count, line count, or source-surface count",
                "Use tables or structured lists only when compact prose would obscure",
            ),
        )

    def test_semantic_reviewers_use_source_and_do_not_treat_source_access_as_failure(self) -> None:
        text = refs(
            "service-logic-coverage.md",
            "docs-generation-flow.md",
            "reviewer-perspectives.md",
        )
        assert_all(
            self,
            text,
            (
                "Reviewers may inspect source",
                "Source access is required when checking fidelity",
                "docs preserve the decisions needed for implementation, verification, and conflict analysis",
                "Do not FAIL merely because internal code structure",
                "Review must not fail merely because the reader needs source for internal mechanics",
            ),
        )
        self.assertNotIn("docs-only reviewer", text)

    def test_required_aids_keep_verification_conditions_inline(self) -> None:
        text = read(REFS / "atom-format-and-judgment.md")
        assert_all(
            self,
            text,
            (
                "changed in-scope required AID",
                "observable verification condition",
                "in that same item",
                "Historical descriptions outside the implementation scope",
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
                "behavior aggregate in the accepted scope",
                "do not require a separate inventory row or AID for every mechanical source surface",
            ),
        )

    def test_high_risk_behavior_adds_conditional_depth_and_review(self) -> None:
        text = read(REFS / "service-logic-coverage.md")
        for category in (
            "authentication, authorization, security, privacy",
            "money, billing, refund, settlement",
            "delete, approve, publish",
            "external integration, webhook, event delivery",
            "irreversible, high-impact, or concurrency-sensitive state transition",
            "shared payload, storage, permission, integration",
        ):
            self.assertIn(category, text)
        assert_all(
            self,
            text,
            (
                "Apply additional detail and the independent risk/contract reviewer",
                "Add a matrix only when the alternatives cannot be reviewed reliably in prose",
                "A trigger does not require unrelated detail",
                "Ordinary CRUD, reversible preference persistence",
                "authoritative local or user-approved provider evidence",
                "record `confirmation_needed`",
            ),
        )

    def test_inventory_is_operation_local_and_closes_to_atoms(self) -> None:
        text = read(REFS / "project-documents-and-inventory.md")
        assert_all(
            self,
            text,
            (
                "operation-local by default",
                "lightweight operation inventory",
                "grouped by meaningful behavior aggregate",
                "Do not require every inventory row",
                "Do not create one inventory row per route",
                "candidate or final owning `atom_key`",
                "delete or ignore the operation-local inventory",
            ),
        )

    def test_shared_owner_prepass_orders_queue_without_freezing_all_owners(self) -> None:
        text = refs(
            "project-documents-and-inventory.md",
            "atomic-graph.md",
            "docs-generation-flow.md",
        )
        assert_all(
            self,
            text,
            (
                "Ownership And Evidence Prepass",
                "shared payload, storage, permission, policy, integration, transaction",
                "confirm owners whose later change would reopen several bundles",
                "keep ordinary single-domain owners provisional",
                "shared-owner bundles before direct dependents",
                "Do not build a complete semantic graph or freeze every aggregate owner",
                "Reference count is a scheduling hint, not proof of ownership",
                "targeted single-domain operation checks only the target owner and adjacent contracts",
                "record its reviewed revision as the owner basis",
                "must not redefine the owner or shared contract silently",
            ),
        )

    def test_operation_evidence_index_is_reused_but_not_trusted_as_proof(self) -> None:
        text = refs(
            "project-documents-and-inventory.md",
            "docs-generation-flow.md",
            "reviewer-perspectives.md",
        )
        assert_all(
            self,
            text,
            (
                "operation-local `evidence.md`",
                "pin it to `source_commit_observed`",
                "reuse it as a source-navigation index",
                "Start from the operation evidence index",
                "Independently reopen changed or risk-bearing claims",
                "Do not reread every cited line mechanically",
            ),
        )

    def test_domain_bundles_use_one_writer_and_risk_scaled_review(self) -> None:
        flow = read(REFS / "docs-generation-flow.md")
        reviewers = read(REFS / "reviewer-perspectives.md")
        assert_all(
            self,
            flow,
            (
                "sequential queue",
                "Each domain bundle uses exactly one writer",
                "exactly one independent development-quality reviewer",
                "when a risk trigger applies",
                "exactly one independent risk/contract reviewer",
                "Ordinary CRUD or preference persistence is not a trigger by itself",
                "Do not run domain bundles in parallel by default",
                "change-type rerun routing",
                "every reviewer applicable to the active bundle PASSes",
                "reopen that bundle",
            ),
        )
        for role in (
            "Required Domain Development-Quality Reviewer",
            "Conditional Risk / Contract Reviewer",
            "Conditional Integration / Baseline Reviewer",
        ):
            self.assertIn(role, reviewers)

    def test_bundle_preflight_precedes_parallel_semantic_review(self) -> None:
        text = refs("docs-generation-flow.md", "validation-contract.md")
        assert_all(
            self,
            text,
            (
                "After each writer and before semantic review",
                "--expect-atom-key <key>",
                "scopes this preflight to the active bundle",
                "Unrelated pre-existing structural findings do not block the bundle",
                "Run unscoped docs validation after the accepted queue finishes",
                "Compare keys and dispositions, not raw document counts",
                "If preflight FAILs, return to the writer without spending a semantic review",
                "same revision and source basis",
                "in parallel",
                "This is not a project-wide semantic review",
            ),
        )

    def test_review_reruns_are_routed_by_change_type(self) -> None:
        text = read(REFS / "reviewer-perspectives.md")
        assert_all(
            self,
            text,
            (
                "Route reruns by what changed",
                "structural preflight only",
                "narrowed source-evidence check",
                "development-quality reviewer for affected bundle(s)",
                "risk/contract reviewer; also development reviewer",
                "Graph `reason` wording or inventory count alone",
                "Do not rerun unaffected PASS results",
            ),
        )

    def test_reviewer_principle_files_and_answer_sheet_are_explicit(self) -> None:
        text = read(REFS / "reviewer-perspectives.md")
        for reference in (
            "atomic-document-contract.md",
            "atom-format-and-judgment.md",
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
                "decision completeness",
                "proportional depth",
                "source fact fidelity",
                "accepted-scope closure",
                "cannot replace a required independent reviewer",
                "구현자가 임의로 정하면 안 되는 내용",
                "검증 가능한 결과",
                "Read only the additional principle files implicated by the bundle",
            ),
        )

        project_review = text.split(
            "## Conditional Integration / Baseline Reviewer", 1
        )[1].split("## Reviewer Selection Examples", 1)[0]
        for reference in (
            "service-logic-coverage.md",
            "source-baseline-and-change-plan.md",
            "atomic-graph.md",
        ):
            self.assertIn(reference, project_review)

        assert_all(
            self,
            text,
            (
                "Reviewers may inspect source",
                "Source access is required when checking fidelity",
                "`source basis`: the inspected commit or explicitly recorded source revision",
            ),
        )

    def test_integration_reviewer_scales_from_affected_closure_to_baseline(self) -> None:
        text = refs("docs-generation-flow.md", "reviewer-perspectives.md")
        assert_all(
            self,
            text,
            (
                "Run one integration reviewer",
                "inspect only the affected closure",
                "Independent changes in several domains do not require this reviewer",
                "expand the review to the whole project",
                "does not repeat complete domain review",
                "cross-domain ownership",
                "shared payload/state/storage/permission/integration contracts",
                "newly run domain review uses the operation's `source_commit_observed`",
                "Only the project-wide form of this reviewer can approve global baseline",
                "reopen the affected bundle",
            ),
        )

    def test_operation_profiles_keep_refresh_work_incremental(self) -> None:
        text = read(REFS / "refresh-flow.md")
        for profile in (
            "`initial-baseline`",
            "`baseline-diff-refresh`",
            "`change-impact-refresh`",
            "`targeted`",
            "`inspection`",
        ):
            self.assertIn(profile, text)
        assert_all(
            self,
            text,
            (
                "process every discovered bundle",
                "Start from `git diff <source_commit>..HEAD`",
                "process affected bundles only",
                "Do not run the initial-baseline procedure for an ordinary refresh",
                "Existing unchanged bundle PASS results remain reusable",
                "does not rerun unchanged domain reviewers at the new commit",
            ),
        )

    def test_baseline_diff_refresh_carries_only_proven_unaffected_reviews(self) -> None:
        text = refs(
            "refresh-flow.md",
            "source-baseline-and-change-plan.md",
            "reviewer-perspectives.md",
        )
        assert_all(
            self,
            text,
            (
                "complete old-to-new source diff",
                "impacted bundle reviews at the new commit",
                "carrying each unaffected bundle class",
                "trusted prior baseline",
                "Do not claim carried reviews ran at the new commit",
            ),
        )

    def test_repeated_no_progress_cycles_are_diagnosed_not_retried_blindly(self) -> None:
        text = read(REFS / "docs-generation-flow.md")
        assert_all(
            self,
            text,
            (
                "Do not use a fixed wall-clock timeout",
                "none of the planned artifact/evidence changes",
                "same blocking finding fingerprint recurs twice",
                "do not launch the same cycle again",
                "dependency-independent bundles",
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

    def test_compact_write_plan_reuses_prior_scope_approval(self) -> None:
        text = refs("docs-generation-flow.md", "source-baseline-and-change-plan.md")
        assert_all(
            self,
            text,
            (
                "Record a compact domain-grouped write plan",
                "lists only applicable items",
                "Do not add placeholder rows",
                "no second user approval is required",
                "inside the user-accepted docs scope and approved boundaries",
                "expands source/docs scope",
                "creates or moves a domain boundary",
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
                "decision-complete documentation requirement",
                "applicable domain/risk/project review gates",
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
                "required development-quality review and applicable risk review PASS",
                "project-wide integration/baseline reviewer PASSes",
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
                "--expect-atom-key",
                "valid standard YAML",
                "validated atom and AID totals",
                "unrelated pre-existing defects do not block the bundle",
                "invalid for bootstrap and baseline phases",
                "Never search for or invoke",
                "The validator is read-only",
                "semantic quality remains the responsibility",
            ),
        )


if __name__ == "__main__":
    unittest.main()
