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
        self.assertIn("do not replace the source tree", text)
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

    def test_direct_references_separate_normative_owners_from_flow_consumers(self) -> None:
        skill = read(SKILL)
        criteria_flow = read(REFS / "criteria-flow.md")
        criteria_contract = read(REFS / "atomization-criteria-contract.md")
        document_contract = read(REFS / "atomic-document-contract.md")
        project_flow = read(REFS / "project-documents-and-inventory.md")
        source_policy = read(REFS / "source-convention-and-domain-policy.md")
        generation_flow = read(REFS / "docs-generation-flow.md")
        reviewer_policy = read(REFS / "reviewer-perspectives.md")
        baseline_policy = read(REFS / "source-baseline-and-change-plan.md")
        atom_format = read(REFS / "atom-format-and-judgment.md")
        judgment_policy = read(REFS / "change-judgment-policy.md")

        assert_all(
            self,
            skill,
            (
                "Treat each direct reference as the detailed owner",
                "must point to the detailed owner instead of independently redefining",
                "normative criteria structure",
                "normative reviewer selection",
                "normative judgment labels",
            ),
        )

        self.assertIn("owns bootstrap sequencing", criteria_flow)
        self.assertIn("normative owner of the small durable criteria", criteria_contract)
        self.assertNotIn("FAIL only for missing or contradictory durable rules", criteria_flow)
        self.assertIn("The independent criteria reviewer checks only", criteria_contract)

        self.assertIn("structural owner of paths", document_contract)
        self.assertNotIn("Project document review rules:", document_contract)
        self.assertIn("project/atomization-criteria-atom.md", document_contract)
        self.assertIn("do not use it as the default path for new criteria work", document_contract)
        self.assertIn("owns when non-atom project documents are created", project_flow)
        self.assertIn("treats docs config, baseline/cache paths", project_flow)
        self.assertIn("not synchronized to real `atom_key` and existing AID references", project_flow)
        self.assertIn("Do not create or advance baseline metadata", project_flow)
        self.assertIn("normative owner of source-convention content", source_policy)

        self.assertIn(
            "owns Atomic Docs operation state from bootstrap through post-approval execution",
            generation_flow,
        )
        self.assertNotIn("new atom, `atom_key`, `Intent`", generation_flow)
        self.assertIn("normative owner of semantic reviewer selection", reviewer_policy)
        self.assertIn("normative owner of global source-baseline schema", baseline_policy)

        self.assertIn("owns where a judgment may appear inside an atom", atom_format)
        self.assertNotIn("Each judgment-bearing item must include:", atom_format)
        self.assertIn("normative owner of controlled judgment", judgment_policy)

        for path in sorted(REFS.glob("*.md")):
            self.assertIn("## Responsibility", read(path), f"{path.name} has no owner boundary")

        owner_links = {
            "criteria-flow.md": ("atomization-criteria-contract.md",),
            "atomic-document-contract.md": (
                "project-documents-and-inventory.md",
                "atomization-criteria-contract.md",
                "source-convention-and-domain-policy.md",
                "atom-format-and-judgment.md",
                "change-judgment-policy.md",
            ),
            "project-documents-and-inventory.md": (
                "atomic-document-contract.md",
                "source-convention-and-domain-policy.md",
            ),
            "refresh-flow.md": (
                "source-convention-and-domain-policy.md",
                "source-baseline-and-change-plan.md",
                "change-judgment-policy.md",
            ),
            "docs-generation-flow.md": (
                "refresh-flow.md",
                "reviewer-perspectives.md",
                "source-baseline-and-change-plan.md",
            ),
            "source-baseline-and-change-plan.md": (
                "refresh-flow.md",
                "reviewer-perspectives.md",
                "change-judgment-policy.md",
            ),
            "service-logic-coverage.md": (
                "atom-format-and-judgment.md",
                "change-judgment-policy.md",
                "docs-generation-flow.md",
            ),
            "atom-format-and-judgment.md": ("change-judgment-policy.md",),
        }
        for consumer, owners in owner_links.items():
            consumer_text = read(REFS / consumer)
            for owner in owners:
                self.assertIn(owner, consumer_text, f"{consumer} does not route to {owner}")

        unique_rules = {
            "The independent criteria reviewer checks only:": "atomization-criteria-contract.md",
            "project/atomization-criteria-atom.md` is a legacy path": "atomic-document-contract.md",
            "project-goal.md` treats docs config, baseline/cache paths": "project-documents-and-inventory.md",
            "For an existing approved docs set, select one profile before detailed source discovery": "refresh-flow.md",
            "| Change after review | Required rerun |": "reviewer-perspectives.md",
            "Create the first baseline only when": "source-baseline-and-change-plan.md",
            "Document until the applicable questions can be answered": "service-logic-coverage.md",
            "Each atom file must preserve these sections": "atom-format-and-judgment.md",
            "Apply the first matching judgment that is supported by evidence": "change-judgment-policy.md",
        }
        reference_text = {path.name: read(path) for path in REFS.glob("*.md")}
        for marker, owner in unique_rules.items():
            locations = [name for name, text in reference_text.items() if marker in text]
            self.assertEqual([owner], locations, f"{marker!r} has ambiguous owners: {locations}")

    def test_ui_metadata_matches_development_decision_goal(self) -> None:
        text = read(OPENAI_YAML)
        assert_all(
            self,
            text,
            (
                'display_name: "Atomic Docs"',
                'short_description: "Source-guided implementation context for development decisions."',
                'default_prompt: "Use $atomic-docs',
                "classify candidates as write, merge, or drop",
                "without mirroring source mechanics",
            ),
        )

    def test_skill_uses_implementation_context_not_behavior_specification_as_quality_target(self) -> None:
        text = read(SKILL) + read(OPENAI_YAML) + "\n".join(
            read(path) for path in sorted(REFS.glob("*.md"))
        )
        assert_all(
            self,
            text,
            (
                "useful implementation context",
                "not a product-behavior specification",
                "Exact fields, branches, state mechanics, and failure paths may remain in source",
                "docs-only implementation is not the review target",
            ),
        )
        for obsolete in (
            "same-functional-behavior reconstruction",
            "docs-only reconstruction reviewer",
            "implementation-reconstruction-ready",
            "exactly four independent draft reviewers",
            "FAIL when a developer still must invent product behavior",
            "product behavior is unambiguous, verification can be derived",
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
                "소스를 도메인 경계 수준으로 살펴 도메인 구성을 제안",
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
                "request lookup only",
                "the active request pointer only",
                "request lifecycle and session/Goal links only",
                "the only owner of operation profile",
                "Do not duplicate queue position, source basis, agent identity, or reviewer state",
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
                "glossary meaning is too shallow to resolve",
                "project/atomization-criteria-atom.md",
                "reviewer logs, or operation status",
                "competing source-unverifiable purpose interpretations",
                "only a source identifier list",
                "Do not create or advance baseline metadata",
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
                "Outcomes",
                "Boundaries",
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
                "Do not clean up, remove, or renumber existing AIDs automatically",
            ),
        )

    def test_aids_are_selective_instead_of_line_level_inventory(self) -> None:
        text = refs(
            "atom-format-and-judgment.md",
            "change-judgment-policy.md",
            "source-baseline-and-change-plan.md",
        )
        assert_all(
            self,
            text,
            (
                "actual downstream reference need",
                "downstream reference must already exist or be named by the accepted operation",
                "possible future reuse alone is insufficient",
                "Do not preallocate one for every `Outcome`, `Boundary`, or `Rule`",
                "Do not assign an AID merely because a statement is durable",
                "Plain `Current Implementation` observations",
                "inventory/evidence rows",
                "may contain zero AIDs",
                "does not create an AID merely to make the judgment possible",
                "exact owning section",
                "affected behavior",
            ),
        )

    def test_atom_sections_have_single_information_owners(self) -> None:
        text = refs(
            "atom-format-and-judgment.md",
            "service-logic-coverage.md",
        )
        assert_all(
            self,
            text,
            (
                "not a completeness checklist",
                "Why does this atom exist?",
                "What smallest normal result helps orient a reader",
                "Which important ownership, inclusion/exclusion",
                "Which non-obvious rule, invariant, refusal",
                "A second specification of complete fields",
                "A complete restatement of the owning rule",
                "another section needs a short reference, not a paraphrase",
            ),
        )

    def test_source_established_current_contract_does_not_need_blanket_confirmation(self) -> None:
        text = read(SKILL) + refs(
            "service-logic-coverage.md",
            "atom-format-and-judgment.md",
            "change-judgment-policy.md",
            "language-policy.md",
            "source-baseline-and-change-plan.md",
        )
        assert_all(
            self,
            text,
            (
                "source-established current contract",
                "may be documented without separate user approval",
                "AI authorship alone does not make the meaning inferred",
                "Reachability or repetition alone does not make behavior a normal contract",
                "`Outcomes`, `Boundaries`, and `Rules`",
                "`Current Implementation` `Source Evidence`",
                "global source baseline or operation-local `source_commit_observed`",
                "general absence of user approval is not enough",
                "does not mean product policy approval",
                "without creating a judgment item for every observed behavior",
            ),
        )

    def test_observed_defects_do_not_become_normal_contract_or_audit_output(self) -> None:
        text = refs(
            "atom-format-and-judgment.md",
            "service-logic-coverage.md",
            "reviewer-perspectives.md",
            "change-judgment-policy.md",
        )
        assert_all(
            self,
            text,
            (
                "Do not promote an observed anomaly",
                "non-blocking non-obvious observation in `Current Implementation`",
                "contradicts an approved requirement or source-established current contract",
                "observed defect promoted to a normal `Outcome` or required `Rule`",
                "detailed attack paths, fixture combinations, and non-blocking defect inventories",
                "require separately accepted scope",
                "specific confirmed approval-before-implementation requirement",
            ),
        )

    def test_boundary_graph_and_gap_ownership_do_not_repeat_atom_meaning(self) -> None:
        text = refs(
            "atomic-document-contract.md",
            "atomic-graph.md",
            "atom-format-and-judgment.md",
        )
        assert_all(
            self,
            text,
            (
                "A domain context atom owns domain-wide purpose",
                "behavior atom's `Boundaries` section owns only a local distinction",
                "Graph frontmatter owns the machine-traversable type",
                "not the source of truth for a natural-language boundary",
                "point to the owning AID or section",
                "Do not repeat the behavior narrative",
            ),
        )

    def test_compact_criteria_contains_only_durable_rules(self) -> None:
        text = refs("atomization-criteria-contract.md", "criteria-flow.md")
        skill = read(SKILL)
        for heading in (
            "목적과 승인 상태",
            "문서 저장 위치와 적용 범위",
            "도메인과 문서 분리 기준",
            "문서 깊이와 식별 기준",
            "작성과 검토 기준",
            "프로젝트 예외와 미해결 결정",
        ):
            self.assertIn(heading, text)
        assert_all(
            self,
            text,
            (
                "normative owner of the small durable criteria document",
                "Do not copy the complete skill reference contracts into criteria",
                "candidate or approved domain maps",
                "atom candidate or split-proposal maps",
                "perspective result tables or source-feature inventories",
                "existing approved criteria file",
                "valid superset",
            ),
        )
        self.assertNotIn("관점 | 적용 상태 | 프로젝트 근거/후보", text)
        self.assertIn(
            "the criteria file owns only its own draft/approved marker",
            skill,
        )

    def test_domain_proposal_precedes_approval_and_atom_discovery_follows(self) -> None:
        text = refs(
            "atomization-criteria-contract.md",
            "criteria-flow.md",
            "project-documents-and-inventory.md",
            "source-convention-and-domain-policy.md",
        )
        assert_all(
            self,
            text,
            (
                "project-wide bootstrap discovery considers every project-native feature area only to domain-boundary depth",
                "first place where source-derived domain candidates are recorded; Atom candidates still do not exist",
                "Do not create `evidence.md`, candidate `atom_key` values",
                "After combined approval and Goal handoff, expand only approved domains",
                "Never copy the candidate map into criteria",
                "project-native name",
                "concrete durable responsibilities",
            ),
        )

    def test_bootstrap_review_and_combined_user_handoff_are_gated(self) -> None:
        text = read(REFS / "criteria-flow.md")
        assert_all(
            self,
            text,
            (
                "one independent bootstrap reviewer",
                "reuse it for revision cycles",
                "until both PASS",
                "do not approve either one",
                "문서 작성 기준의 핵심 원칙",
                "도메인 후보별 책임, 제외 범위, 인접 경계와 대표 소스 근거",
                "승인 가능한 도메인과 소유권 결정이 필요한 도메인",
                "실제로 작성할 도메인 선택",
                "criteria, source-supported domain boundaries, and selected domain write scope",
                "Partial approval is valid",
                "문서 작성 기준과 선택한 도메인 경계는 승인됐고, 아직 실제 Atom 문서는 작성하지 않았다",
                "Do not ask for the same write scope again",
            ),
        )

    def test_unresolved_domain_isolated_from_approved_domain_scope(self) -> None:
        text = refs(
            "criteria-flow.md",
            "source-convention-and-domain-policy.md",
            "docs-generation-flow.md",
        )
        assert_all(
            self,
            text,
            (
                "update that domain to `needs_confirmation` in `work-state.json`",
                "blocks only that domain",
                "independently valid domains remain eligible for approval",
                "put only their approved tentative domain paths in accepted scope",
                "Keep unselected and `needs_confirmation` domains outside that scope",
                "Do not create Atom candidates for `candidate`, unselected, `rejected`, or `needs_confirmation` domains",
            ),
        )

    def test_source_docs_select_high_value_context_and_leave_exact_behavior_in_source(self) -> None:
        text = refs("service-logic-coverage.md", "atom-format-and-judgment.md")
        assert_all(
            self,
            text,
            (
                "Implementation Context Selection",
                "shared or external contract",
                "non-obvious implementation constraint",
                "Do not select a behavior merely because a route, field, branch, state",
                "are not a completion checklist",
                "does not need an observable verification target",
                "do not narrate every function call",
                "Stop adding detail once the reader can navigate to source",
                "Exact fields, payload mappings, ordinary branches",
                "Do not use atom count, file count, line count, or source-surface count",
                "Use tables or structured lists only when compact prose would obscure",
            ),
        )
        for obsolete in (
            "For each meaningful behavior aggregate in the accepted scope",
            "Maintain closure from each meaningful behavior aggregate",
            "until each meaningful product or operational aggregate has a disposition",
        ):
            self.assertNotIn(obsolete, text)

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
                "orient source inspection and expose the important constraints",
                "Do not FAIL because general docs omit ordinary fields",
                "Reopening source for exact behavior is expected",
            ),
        )
        self.assertNotIn("docs-only reviewer", text)

    def test_context_review_fails_misleading_omissions_not_ordinary_detail_omissions(self) -> None:
        text = refs(
            "service-logic-coverage.md",
            "project-documents-and-inventory.md",
            "reviewer-perspectives.md",
        )
        assert_all(
            self,
            text,
            (
                "hides a known shared/external contract, owner, or non-obvious constraint",
                "whose omission makes the atom's stated scope misleading",
                "ordinary fields, inputs/outputs, branches, states, failures",
                "A developer needing source to determine exact product behavior is expected",
                "Ordinary source behavior that never became a candidate needs no row or disposition",
            ),
        )

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

    def test_general_atoms_skip_verification_targets_but_implementation_basis_keeps_them(self) -> None:
        text = read(SKILL) + refs(
            "atom-format-and-judgment.md",
            "service-logic-coverage.md",
            "reviewer-perspectives.md",
        )
        assert_all(
            self,
            text,
            (
                "do not require a verification target for every observed behavior",
                "only for an approved implementation-basis change",
                "changed in-scope required AID",
                "observable verification condition",
                "Cartesian products of inputs, states, failures",
                "do not preserve them in managed docs",
                "matrix must itself express a product or contract decision",
                "does not need an observable verification target",
            ),
        )

    def test_ordinary_judgment_section_trace_does_not_weaken_compliance(self) -> None:
        text = refs(
            "atom-format-and-judgment.md",
            "change-judgment-policy.md",
            "source-baseline-and-change-plan.md",
        )
        assert_all(
            self,
            text,
            (
                "stable `atom_key`, the exact owning section, and the affected behavior",
                "unambiguous natural-language basis",
                "Path-only, slug-only, identifier-only",
                "use `confirmation_needed` or a coverage gap instead of a stronger judgment",
                "explicit compliance operations continue to require AID-backed rows",
                "changed in-scope required decisions",
                "does not create an AID merely to make the judgment possible",
                "does not redefine controlled labels or their precedence",
            ),
        )

    def test_gap_creation_and_merging_preserve_independent_risk(self) -> None:
        text = read(SKILL) + refs(
            "atom-format-and-judgment.md",
            "change-judgment-policy.md",
            "reviewer-perspectives.md",
        )
        assert_all(
            self,
            text,
            (
                "not a gap by itself",
                "prevents a stronger implementation or review judgment",
                "one judgment label",
                "one unresolved decision",
                "compatible resolution",
                "different labels",
                "independently resolvable behavior",
                "high-risk contracts",
                "verification outcomes",
            ),
        )

    def test_current_implementation_stops_before_source_replacement(self) -> None:
        text = read(SKILL) + refs(
            "atom-format-and-judgment.md",
            "service-logic-coverage.md",
            "reviewer-perspectives.md",
        )
        assert_all(
            self,
            text,
            (
                "without replacing source inspection",
                "query predicate",
                "possible exploit/test scenario",
                "Record execution order only when",
                "complete method-call sequence",
                "substitute for reopening source",
                "source-level mechanics whose only value is specification completeness",
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
                "selected context candidate may span routes",
                "do not require a separate inventory row or AID for each surface",
            ),
        )

    def test_high_risk_review_checks_selected_context_without_starting_an_audit(self) -> None:
        text = refs(
            "service-logic-coverage.md",
            "docs-generation-flow.md",
            "reviewer-perspectives.md",
        )
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
                "selected context candidate or approved implementation-basis change",
                "Source presence alone does not start a risk audit",
                "Do not discover or preserve every adverse branch",
                "Require an adverse outcome and verification target only for an approved implementation-basis requirement",
                "Ordinary CRUD, reversible preference persistence",
                "authoritative local or user-approved provider evidence",
                "Record `confirmation_needed` only when",
                "candidate ID, planned `atom_key`, trigger, and selected contract basis",
                "domain-level risk category",
                "cannot expand managed-doc scope",
                "empty trigger list is not self-validating",
                "rerun both development and applicable risk reviews against the same corrected revision",
                "never reuse the old FAIL as PASS",
                "A version-1 operation reruns selection preflight first",
                "legacy operation uses its recorded unversioned correction/preflight contract instead",
            ),
        )

    def test_inventory_is_operation_local_and_tracks_only_selected_context(self) -> None:
        text = read(REFS / "project-documents-and-inventory.md")
        assert_all(
            self,
            text,
            (
                "operation-local by default",
                "Pre-Approval Domain Proposal",
                "first place where source-derived domain candidates are recorded",
                "도메인 후보 | 책임 | 제외 범위 | 인접 경계 | 대표 소스 근거 | 상태/미해결 질문",
                "Do not add `atom_key`, AID, split proposals",
                "Post-Approval Context Inventory",
                "After combined approval and Goal handoff",
                "grouped by durable domain and selected implementation-context candidate",
                "disposition: write|merge|drop",
                "candidate_id",
                "exact approved tentative domain path",
                "selection_basis",
                "merge_target_atom_key",
                "domain context atom and have no separate behavior candidate",
                "Do not require every inventory row",
                "Do not create one inventory row per route",
                "candidate or final owning `atom_key`",
                "Ordinary source behavior that never became a candidate needs no row or disposition",
                "must not search for or disposition every source behavior",
                "delete or ignore the operation-local inventory",
            ),
        )

    def test_candidate_admission_drops_source_obvious_and_dormant_detail(self) -> None:
        text = refs(
            "service-logic-coverage.md",
            "project-documents-and-inventory.md",
        )
        assert_all(
            self,
            text,
            (
                "`write`: the candidate has an independent durable purpose",
                "`merge`: the context is useful but has no independent ownership",
                "`drop`: reopening source is sufficient",
                "Dormant or unreachable code is `drop` by default",
                "constrains a reachable consumer",
                "approved activation change",
                "possible future use or destructive method name is not enough",
                "must not turn an unselected fact into required managed-doc detail",
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
                "smallest authoritative source locators",
                "one concise relevance statement per row",
                "## <candidate_id>",
                "pass only active `write` and targeting `merge` sections to the writer",
                "Do not preserve field lists, parser algorithms, payload mappings",
                "Start from the operation evidence index",
                "Independently reopen changed or risk-bearing claims",
                "Do not reread every cited line mechanically",
            ),
        )

    def test_domain_bundles_reuse_persistent_writer_and_reviewers(self) -> None:
        flow = read(REFS / "docs-generation-flow.md")
        reviewers = read(REFS / "reviewer-perspectives.md")
        assert_all(
            self,
            flow,
            (
                "sequential queue",
                "One bundle may own several atoms",
                "Create one writer and one independent development-quality reviewer for the operation",
                "record their agent IDs in `work-state.json`",
                "Reuse them for every sequential selected bundle",
                "create one risk/contract reviewer and reuse it",
                "same-role replacement using a role-filtered compact handoff",
                "replacement writer receives only accepted scope",
                "omit `drop` records and evidence",
                "not the writer's private reasoning conversation",
                "Ordinary CRUD, preference persistence, or a risk-shaped source surface is not a trigger by itself",
                "Do not run domain bundles in parallel by default",
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
        text = refs(
            "docs-generation-flow.md",
            "reviewer-perspectives.md",
            "validation-contract.md",
        )
        assert_all(
            self,
            text,
            (
                "After each writer and before semantic review",
                "--phase selection --request-id <request-id>",
                "Build the queue only from `write` keys and the targets consumed by `merge`",
                "repair operation state, inventory, evidence locators, queue, or risk references",
                "--expect-atom-key <key>",
                "scopes this preflight to the active bundle",
                "Unrelated pre-existing structural findings do not block the bundle",
                "Run unscoped docs validation after the accepted queue finishes",
                "rerun version-1 selection when candidate, evidence, queue, or risk input changed",
                "Compare planned selected keys, not raw source or document counts",
                "send managed Atom content or structure to the writer",
                "repair operation state, expected keys, paths, inventory, or evidence projection through their owning flow without a writer",
                "same revision and source basis",
                "in parallel",
                "This is not a project-wide semantic review",
                "do not blanket-rerun the writer",
                "Rerun the writer only when selected output or documented meaning changes",
                "project-wide view exposes a local defect",
                "apply the rerun table below",
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

    def test_first_pass_review_routes_meaning_structure_and_source_locators(self) -> None:
        flow = read(REFS / "docs-generation-flow.md")
        text = read(REFS / "reviewer-perspectives.md")
        self.assertIn("authoritative change-type table in `reviewer-perspectives.md`", flow)
        self.assertNotIn("new atom, `atom_key`, `Intent`", flow)
        assert_all(
            self,
            text,
            (
                "Intent, important context, rule/contract, ownership, approved verification condition, or judgment label",
                "Atom boundary, owner, edge type/target",
                "Markdown formatting, graph path repair",
                "structural preflight only",
                "Source locator/evidence index correction with unchanged documented claim",
                "version-1 selection preflight or the legacy recorded preflight",
                "narrowed source-evidence check",
                "reviews every selected domain bundle for `initial-baseline`",
                "Targeted structural-only single-domain change",
            ),
        )

    def test_reviewers_fail_repeated_meaning_without_demanding_risk_copies(self) -> None:
        text = read(REFS / "reviewer-perspectives.md")
        assert_all(
            self,
            text,
            (
                "one meaning has one complete owner",
                "substantive repetition across sections",
                "A short reference plus the minimum local reading context is not duplication",
                "Do not FAIL a general context atom merely because an unmentioned refusal",
                "docs-only implementation is not the review target",
                "Before failing for an omitted source fact",
                "If it would be `drop`, omission is correct",
            ),
        )

    def test_reviewer_corrections_remove_or_generalize_before_precision(self) -> None:
        text = read(REFS / "reviewer-perspectives.md")
        assert_all(
            self,
            text,
            (
                "Each blocking finding records",
                "Different findings in one report may use different modes",
                "`remove`: the claim, paragraph, or Atom lacks a durable selection basis",
                "`generalize`: the underlying context is useful",
                "`correct_selected_claim`: a retained important claim is false",
                "Do not choose `correct_selected_claim` for a finding until removal and generalization",
                "rerun selection preflight",
            ),
        )

    def test_reviewers_fail_over_documentation_costs(self) -> None:
        text = read(REFS / "reviewer-perspectives.md")
        assert_all(
            self,
            text,
            (
                "specify every behavior",
                "gap economy",
                "Cartesian test plan",
                "mechanical AID allocation",
                "Current Implementation` written as a source substitute",
                "product-behavior specification",
                "concrete test cases",
            ),
        )

    def test_operation_reports_scale_without_blocking_or_fabricated_eta(self) -> None:
        text = read(REFS / "docs-generation-flow.md")
        assert_all(
            self,
            text,
            (
                "Report domain count, bundle count, risk-bundle count, shared-owner count",
                "short non-blocking user update",
                "Do not invent an ETA",
                "After two bundles complete",
                "measured completed/remaining bundle counts",
                "This is informational and does not pause the queue",
            ),
        )

    def test_reviewer_reports_are_findings_only_and_tables_are_conditional(self) -> None:
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
                "Findings-Only Report Contract",
                "Every PASS report contains only",
                "검토 범위 | source/revision | verdict | 확인한 대표 근거 | 재실행 필요 여부",
                "A FAIL report adds only blocking findings",
                "do not repeat it in every PASS report",
                "context usefulness",
                "proportional depth",
                "source fact fidelity",
                "selected-scope trace",
                "cannot replace a required independent reviewer",
                "Do not persist an answer sheet for an ordinary development PASS",
                "Persist a decision comparison table only when",
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
                "inspected commit and bundle attempt",
            ),
        )

    def test_integration_reviewer_scales_from_affected_closure_to_baseline(self) -> None:
        flow = read(REFS / "docs-generation-flow.md")
        text = read(REFS / "reviewer-perspectives.md")
        self.assertIn("selected by `reviewer-perspectives.md`", flow)
        assert_all(
            self,
            text,
            (
                "Run one integration/baseline reviewer only when",
                "review only the affected closure",
                "Do not add this reviewer merely because several independent bundles changed",
                "expand the review to the whole project",
                "Do not repeat unchanged domain detail",
                "cross-domain ownership",
                "shared payload/state/storage/permission/integration contracts",
                "Every newly run domain review uses the operation's `source_commit_observed`",
                "latest selection preflight matches the final queue",
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
                "Consider every project-native feature area",
                "select durable high-value context bundles",
                "Do not turn source exploration into a behavior-disposition inventory",
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
                "Accepted bootstrap scope authorizes domain-proposal discovery plus criteria and boundary review/revision cycles",
                "do not require separate approval merely to run",
                "unapproved existing-Atom delete/merge",
                "Current-operation output correction and an exact previously approved action do not need repeated approval",
                "Do not stop because a required subagent was not named again",
                "is not a Goal-blocked state",
            ),
        )

    def test_managed_artifact_corrections_reuse_only_exact_approval(self) -> None:
        text = refs(
            "docs-generation-flow.md",
            "reviewer-perspectives.md",
            "project-documents-and-inventory.md",
            "atomic-graph.md",
            "source-baseline-and-change-plan.md",
            "validation-contract.md",
        )
        assert_all(
            self,
            text,
            (
                "operation_created_artifacts",
                "whole-Atom `remove`",
                "operation's fixed managed-docs revision",
                "current managed-docs Git HEAD/index",
                "Do not mark the Goal blocked or ask for deletion approval",
                "approved_existing_actions",
                "complete mutation closure before asking once",
                "Reusing the exact approved action requires no second approval",
                "action_execution",
                "never overwrite the newer content during automatic recovery",
                "Keep the backticked candidate ID and `drop` reason in inventory",
                "complete pre-mutation `work-state.json`",
                "partial hand-built or selection-invalid state extract",
                "keep every unrelated top-level owner unchanged",
                "restorable version-1 routing contract",
                "unique candidate/artifact/action identities",
                "exactly match every unrelated top-level owner",
                "status-specific allowed/forbidden keys",
                "JSON value is `null`",
                "created_attempt_id",
                "--require-actions-final",
                "must have disjoint paths and keys",
                "incoming edge to its `atom_key`",
                "once approved, do not ask again for the same fingerprint",
                "operation_created_artifacts` contains one record",
                "approved_existing_actions` is immutable",
                "Selection validation is the request-bound structural postcondition",
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
                "prior scope approval authorizes the plan",
                "user-approved domain boundaries",
                "newly found domain",
                "requires affected boundary review and user approval",
                "expands source/docs scope",
                "moves/deletes/merges an existing domain boundary",
                "existing Atom delete/merge",
                "same fingerprint",
                "ambiguous boundary requiring user judgment",
            ),
        )

    def test_goal_gate_precedes_docs_generation(self) -> None:
        text = read(REFS / "docs-generation-flow.md")
        assert_all(
            self,
            text,
            (
                "Bootstrap criteria drafting, domain-proposal discovery, and bootstrap review/revision do not require a Codex Goal",
                "call `create_goal` before creating detailed `evidence.md`, Atom/context candidates",
                "approved tentative domain paths",
                "implementation-context selection requirement",
                "applicable domain/risk/project review gates",
                "If Goal creation is unavailable or fails, preserve the approved criteria",
                "retry the same Goal objective without asking for approval again",
                "Complete the Goal only after",
            ),
        )

    def test_bootstrap_state_transitions_into_approved_goal_scope(self) -> None:
        text = read(REFS / "docs-generation-flow.md")
        assert_all(
            self,
            text,
            (
                "the Goal link stays empty before combined approval and Goal success",
                "the only owner of operation profile, bootstrap discovery scope, domain candidate status, accepted scope",
                "`work-state.json` is the authoritative owner of domain candidate status",
                "the inventory status column only mirrors it for user review",
                "Before combined approval, keep accepted scope and execution profile empty",
                "set only user-selected valid tentative domain paths to `approved` and accepted scope",
                "After Goal success, expand the same `inventory.md`",
                "A caller session may link to the request but must not duplicate or replace",
            ),
        )

    def test_first_setup_stops_before_atom_seed_discovery(self) -> None:
        text = read(REFS / "refresh-flow.md")
        assert_all(
            self,
            text,
            (
                "If first setup lacks combined approval, route to `criteria-flow.md` and stop after its domain-only proposal",
                "after accepted scope and Goal handoff",
                "Use source-to-atom seed discovery only inside the approved domain paths and after Goal handoff",
            ),
        )

    def test_domain_candidate_status_has_one_authoritative_owner(self) -> None:
        text = refs("criteria-flow.md", "project-documents-and-inventory.md")
        assert_all(
            self,
            text,
            (
                "update that domain to `needs_confirmation` in `work-state.json`, then synchronize the inventory projection",
                "Any status mismatch is a bootstrap review FAIL",
                "`work-state.json` is authoritative for `candidate|approved|rejected|needs_confirmation`",
                "inventory status column is a user-review projection",
            ),
        )

    def test_active_goal_scope_cannot_expand_in_place(self) -> None:
        text = read(REFS / "docs-generation-flow.md")
        assert_all(
            self,
            text,
            (
                "its approved domain paths and accepted scope are immutable",
                "A same-path boundary clarification may continue",
                "Put independent new scope in a follow-up Atomic Docs request/Goal",
                "Never create a second Goal while the first is active",
            ),
        )

    def test_partial_project_wide_approval_becomes_targeted_execution(self) -> None:
        text = refs("criteria-flow.md", "docs-generation-flow.md", "refresh-flow.md")
        assert_all(
            self,
            text,
            (
                "Project-wide bootstrap discovery does not imply `initial-baseline`",
                "partial domain approval selects `targeted`",
                "cannot create or advance a global baseline",
                "every required project domain is approved",
                "baseline creation was explicitly included in the combined approval",
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
                "retained managed-doc claims were reviewed at that revision",
                "does not mean every product behavior, field, branch, state, or failure is documented",
                "Baseline PASS does not mean product policy approval",
                "Do not create new provisional atoms for `candidate`, unselected, or `needs_confirmation` domains",
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
                "intent, outcome, boundary, rule, current implementation, planned change, or gap",
                "Do not collapse bug, missing required behavior",
            ),
        )

    def test_source_conflict_routing_covers_every_semantic_owner(self) -> None:
        baseline = read(REFS / "source-baseline-and-change-plan.md")
        text = read(REFS / "change-judgment-policy.md")
        self.assertIn("conflict, planned-change, and gap classification follow", baseline)
        assert_all(
            self,
            text,
            (
                "conflicts with confirmed `Intent`, `Outcomes`, `Boundaries`, or `Rules`",
                "preserve it as `bug_or_regression` or the first other supported label",
                "Do not classify behavior as healthy only because no related gap exists",
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
            "atomic-document-contract.md",
        )
        assert_all(
            self,
            text,
            (
                "project/source-convention.md",
                "non-atom document",
                "runtime-impacting conventions",
                "important context for that atom's stated scope",
                "include its AID when one exists",
                "do not create an atom, AID, or gap solely because a runtime convention exists",
                "Non-runtime code style",
                "no coverage gap is required",
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
                "`graph_edges: []` is valid",
                "shared contract, cross-domain dependency/conflict/replacement",
                "Do not add same-domain `related_to` edges merely for navigation",
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
                "remove the completed delta from `Planned Changes`",
                "keep the durable requirement in its owning `Outcomes`, `Boundaries`, or `Rules` section",
                "add only the concise source realization to `Current Implementation`",
            ),
        )
        self.assertNotIn("move the confirmed implemented behavior", text)

    def test_validation_contract_points_to_plugin_bundled_read_only_tool(self) -> None:
        text = read(REFS / "validation-contract.md")
        self.assertTrue(VALIDATOR.is_file())
        assert_all(
            self,
            text,
            (
                "<plugin-root>/scripts/validate_atomic_docs.py",
                "--phase bootstrap",
                "--phase selection",
                "--request-id <request-id>",
                "--phase docs",
                "--phase baseline",
                "--expect-atom-key",
                "valid standard YAML",
                "validated atom and AID totals",
                "unrelated pre-existing defects do not block the bundle",
                "valid only for docs",
                "every candidate has a unique ID",
                "without duplicate JSON keys",
                "no tab characters, fenced or indented code (including inside blockquote or list containers), multiline inline code, or raw HTML-like syntax",
                "every risk trigger resolves its candidate and output/merge target",
                '"context_selection"',
                '"candidate_id"',
                "legacy active request without this version",
                "continues its existing unversioned state",
                "scope expansion still follows its normal approval and Goal boundary",
                "whether a candidate's `write|merge|drop` selection",
                "Never search for or invoke",
                "The validator is read-only",
                "semantic quality remains the responsibility",
            ),
        )

    def test_selection_contract_is_new_operation_only_and_legacy_work_is_not_migrated(self) -> None:
        text = read(SKILL) + refs(
            "docs-generation-flow.md",
            "reviewer-perspectives.md",
            "validation-contract.md",
        )
        assert_all(
            self,
            text,
            (
                "selection contract version 1",
                "legacy active operation without this version",
                "continues its recorded unversioned flow and in-scope corrections without migration",
                "do not invoke version-1 validation or add version-1 fields",
                "legacy operation uses its recorded unversioned correction/preflight contract",
                "version-1 selection preflight or the legacy recorded preflight",
            ),
        )

    def test_normal_operation_links_risk_before_selection_validation(self) -> None:
        text = read(SKILL)
        self.assertLess(
            text.index("link applicable risk triggers"),
            text.index("then run selection validation"),
        )


if __name__ == "__main__":
    unittest.main()
