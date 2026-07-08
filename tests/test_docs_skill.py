from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS_SKILL = ROOT / "skills" / "atomic-docs" / "SKILL.md"
DOCS_REFS = ROOT / "skills" / "atomic-docs" / "references"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def read_refs(*names: str) -> str:
    return "\n".join(read(DOCS_REFS / name) for name in names)


def section(text: str, heading: str) -> str:
    lines = text.splitlines()
    start = None
    start_level = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        level = len(stripped) - len(stripped.lstrip("#"))
        title = stripped[level:].strip()
        if title == heading:
            start = index
            start_level = level
            break
    if start is None or start_level is None:
        raise AssertionError(f"Missing markdown section: {heading}")

    end = len(lines)
    for index in range(start + 1, len(lines)):
        stripped = lines[index].strip()
        if not stripped.startswith("#"):
            continue
        level = len(stripped) - len(stripped.lstrip("#"))
        if level <= start_level:
            end = index
            break
    return "\n".join(lines[start:end])


def read_atomic_contract_bundle() -> str:
    return read_refs(
        "atomic-document-contract.md",
        "atomization-criteria-contract.md",
        "source-convention-and-domain-policy.md",
        "service-logic-coverage.md",
        "atom-format-and-judgment.md",
    )


class DocsSkillTests(unittest.TestCase):
    def test_docs_skill_entry_references_required_contracts(self) -> None:
        text = read(DOCS_SKILL)
        self.assertIn("name: atomic-docs", text)
        self.assertIn("create, update, inspect, refresh, and manage", text)
        for reference in [
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
            "project-documents-and-inventory.md",
            "source-baseline-and-change-plan.md",
            "change-judgment-policy.md",
            "atomic-graph.md",
            "stageflow-integration.md",
        ]:
            self.assertIn(reference, text)
        self.assertIn("Do not assume a hardcoded `docs/` root", text)
        self.assertIn("source-code commit hash baseline", text)
        self.assertIn("Respect Stageflow gates", text)
        self.assertIn("language policy", text)
        self.assertIn("controlled judgment labels", text)
        self.assertIn("stale installed cache path", text)
        self.assertIn("fresh cachebuster", text)
        self.assertIn("storage-mode-aware", text)
        self.assertIn("Ask the user to choose `submodule` or `repository` storage mode", text)
        self.assertIn("repository-local managed docs root", text)
        self.assertIn("`.stageflow/atomic-docs.json`", text)
        self.assertIn("service logic as natural-language source-of-truth docs", text)
        self.assertIn("meaningful service logic in natural language", text)
        self.assertIn("endpoint lists, controller summaries, service class summaries", text)
        self.assertIn("not as the docs themselves or direct code suitability evidence", text)
        self.assertIn("domain partitioning criteria and a candidate or approved domain map", text)
        self.assertIn("project/project-goal.md", text)
        self.assertIn("project/project-glossary.md", text)
        self.assertIn("project/service-logic-inventory.md", text)
        self.assertIn("explicitly retained `project/service-logic-inventory.md` coverage index", text)
        self.assertIn("`.stageflow/atomic-docs/`", text)
        self.assertIn("not a Stageflow workflow request", text)
        self.assertIn("non-atom project documents with separate writing and review rules", text)
        self.assertIn("Legacy `project-goal-atom.md` and `project-glossary-atom.md` are migration candidates", text)
        self.assertIn("durable domain/category boundary map, behavior-level atom candidate map", text)
        self.assertIn("Do not put leaf workflow or behavior candidates directly in the domain map", text)
        self.assertIn("full discovery candidate map, and accepted-scope rules", text)
        self.assertIn("Do not encode operation-local write scope, bundle queue, writer/reviewer status, or post-write gate result", text)
        self.assertIn("Broad domains or broad category groupings are never valid", text)
        self.assertIn("After rejecting a broad source root or category/root surface", text)
        self.assertIn("promote that aggregate to a concrete domain candidate or concrete split proposal", text)
        self.assertIn("Use hybrid domain naming", text)
        self.assertIn("start from project-native feature/root language", text)
        self.assertIn("AI-renamed abstract labels", text)
        self.assertIn("stable frontmatter `atom_key`", text)
        self.assertIn("summarize its contents for the user with project-native feature candidates, capability/common promotion proposals", text)
        self.assertIn("Keep source conventions separate from service logic atoms", text)
        self.assertIn("project/source-convention.md", text)
        self.assertIn("do not mix non-runtime conventions into service logic atoms", text)
        self.assertIn("do not give these non-atom project documents `atom_key`, AID, `graph_edges`, or atom required sections", text)
        self.assertIn("post-write consistency and source fact review", text)
        self.assertIn("before reporting completion or presenting the docs as judgment-ready", text)

    def test_atomic_docs_reference_files_stay_under_200_lines(self) -> None:
        for path in sorted(DOCS_REFS.glob("*.md")):
            line_count = len(read(path).splitlines())
            self.assertLessEqual(line_count, 200, f"{path.name} has {line_count} lines")

    def test_language_policy_chooses_user_or_existing_docs_language(self) -> None:
        text = read(DOCS_REFS / "language-policy.md")
        self.assertIn("language explicitly requested by the user", text)
        self.assertIn("dominant language already used", text)
        self.assertIn("current conversation language", text)
        self.assertIn("default to Korean", text)
        self.assertIn("managed docs prose, docs change plans", text)
        for fixed_term in [
            "Intent",
            "Rules",
            "Current Implementation",
            "Planned Changes",
            "Gaps",
            "atom_key",
            "graph_edges",
            "storage_mode",
            "docs_root",
            "source-code identifiers",
            "[AID:paid-order-processing.impl.003]",
            "option labels",
            "Stageflow artifact",
        ]:
            self.assertIn(fixed_term, text)
        self.assertIn("Do not translate code identifiers or schema keys", text)
        self.assertIn("Do not translate or localize AID tokens", text)
        self.assertIn("Korean docs must preserve `[AID:...]` exactly", text)
        self.assertIn("ask before writing confirmed docs", text)
        self.assertIn("leftover English filler text", text)
        self.assertIn("Korean-First Template Policy", text)
        self.assertIn("Korean-first writing templates", text)
        self.assertIn("Do not draft an English skeleton first and then translate it into Korean", text)
        self.assertIn("criteria documents must also use Korean visible section headings and field labels", text)
        self.assertIn("Do not use English visible labels such as `Purpose`, `Approval Status`", text)
        self.assertIn("Preserve only fixed atom section headings, frontmatter keys, controlled judgment labels, AID tokens, and source identifiers", text)
        self.assertIn("`atom_key` values", text)
        self.assertIn("judgment-bearing prose under fixed atom sections such as `Planned Changes` and `Gaps` must also use Korean-visible field labels", text)
        self.assertIn("do not write English scaffold labels such as `affected behavior`, `next action`, `basis`, `source evidence`, `judgment label`", text)
        self.assertIn("`conditions/branches`, `validation/guard`, `state transition`, `persistence side effect`, `external call`, or `error/recovery`", text)
        for korean_gap_label in [
            "`판정 라벨`",
            "`영향받는 동작`",
            "`다음 조치`",
            "`근거`",
            "`소스 근거`",
            "`조건/분기`",
            "`검증/가드`",
            "`상태 전이`",
            "`저장 효과`",
            "`외부 호출`",
            "`실패/복구`",
            "`관련 AID`",
        ]:
            self.assertIn(korean_gap_label, text)
        for korean_subheading in [
            "### 동작 흐름",
            "### 관찰된 판단 규칙",
            "### 상태와 저장 효과",
            "### 외부 연동과 이벤트",
            "### 실패와 복구 동작",
            "### Source Evidence",
        ]:
            self.assertIn(korean_subheading, text)
        self.assertIn("translated English", text)
        self.assertIn("English-first scaffold", text)
        self.assertIn("No Example Leakage", text)
        self.assertIn("Do not copy reference example wording", text)
        self.assertIn("Controlled judgment labels, fixed headings, schema keys", text)
        self.assertIn("change plan and managed docs prose should use the user/artifact language", text)

    def test_atomic_docs_uses_user_facing_terms_before_raw_config(self) -> None:
        skill = read(DOCS_SKILL)
        language = read(DOCS_REFS / "language-policy.md")
        docs_root = read(DOCS_REFS / "docs-root-and-config.md")
        criteria = read(DOCS_REFS / "criteria-flow.md")

        self.assertIn("explain storage and write scope in plain user terms before showing raw config keys", skill)
        self.assertIn("Do not present first setup as only `storage mode: repository`, `docs root: docs`, or `작성/갱신: ...`", skill)
        self.assertIn("별도 submodule 없이 현재 repository 안에 문서를 저장합니다", skill)
        self.assertIn("문서 작성 기준 초안", skill)

        self.assertIn("User-Facing Terminology Policy", language)
        self.assertIn("쉬운 설명 + 원문 식별자", language)
        for required_mapping in [
            "`storage_mode`: `문서 저장 방식`",
            "`repository`: `현재 프로젝트 안의 폴더에 저장`",
            "`submodule`: `별도 문서 저장소/submodule에 저장`",
            "`docs_root` and managed docs root: `문서 저장 위치`",
            "`.stageflow/atomic-docs.json`: `atomic docs 설정 파일`",
            "`project/atomization-criteria.md`: `문서 작성 기준 초안`",
            "`bootstrap`: `첫 설정 단계` or `처음 준비 단계`",
        ]:
            self.assertIn(required_mapping, language)
        self.assertIn("unexplained standalone lines", language)
        self.assertIn("raw config summaries such as `storage mode: repository`, `docs root: docs`, or `작성/갱신: .stageflow/atomic-docs.json`", language)

        for text in [docs_root, criteria]:
            self.assertIn("atomic docs 설정 파일", text)
            self.assertIn("문서 작성 기준 초안", text)
        self.assertIn("현재 프로젝트 안의 폴더에 문서를 저장", docs_root)
        self.assertIn("별도 문서 저장소/submodule에 문서를 저장", docs_root)
        self.assertIn("first setup step before real atom document writing", criteria)
        self.assertIn("첫 설정 단계", criteria)
        self.assertIn("Do not summarize this first step only as raw key-value lines", criteria)

    def test_atomic_docs_separates_operation_state_from_durable_docs(self) -> None:
        skill = read(DOCS_SKILL)
        criteria = read_refs("atomization-criteria-contract.md", "criteria-flow.md")
        generation = read(DOCS_REFS / "docs-generation-flow.md")
        inventory = read(DOCS_REFS / "project-documents-and-inventory.md")
        baseline = read(DOCS_REFS / "source-baseline-and-change-plan.md")
        stageflow = read(DOCS_REFS / "stageflow-integration.md")

        for state_path in [
            ".stageflow/atomic-docs/index.json",
            ".stageflow/atomic-docs/sessions/<session-id>/current.json",
            ".stageflow/atomic-docs/requests/<request-id>/state.json",
            ".stageflow/atomic-docs/requests/<request-id>/work-state.json",
        ]:
            self.assertIn(state_path, generation)
        self.assertIn("not the managed docs root", generation)
        self.assertIn("not a Stageflow workflow request artifact", generation)
        self.assertIn("not direct code suitability evidence", skill)

        self.assertIn("not in durable criteria or durable domain approval status", criteria)
        self.assertIn("must not become the live progress ledger for the current run", criteria)
        self.assertIn("live bundle queue, active domain bundle, writer/reviewer PASS/FAIL log", criteria)

        self.assertIn("operation-local by default", inventory)
        self.assertIn("Write or retain `<doc-root>/project/service-logic-inventory.md` only when the accepted scope explicitly asks for a final coverage index", inventory)
        self.assertIn("delete or ignore the operation-local inventory", inventory)
        self.assertIn("Only copy a service logic inventory into `<doc-root>/project/service-logic-inventory.md`", generation)

        self.assertIn("Store the post-write gate result under `.stageflow/atomic-docs/requests/<request-id>/post-write-review.md`", generation)
        self.assertIn("Do not write `docs/project/post-write-review.md`", generation)
        self.assertIn("post-write gate stored under `.stageflow/atomic-docs/requests/<request-id>/post-write-review.md`", baseline)

        self.assertIn("`.stageflow/atomic-docs/` and `.stageflow/atomic-docs.json` is owned by the atomic-docs skill", stageflow)
        self.assertIn("must not be used to bypass or satisfy Stageflow gates", stageflow)

    def test_plugin_manifest_exposes_docs_skill_prompts(self) -> None:
        manifest = read(ROOT / ".codex-plugin" / "plugin.json")
        self.assertIn('"skills": "./skills/"', manifest)
        self.assertIn("Documentation", manifest)
        self.assertIn("expose an atomic-docs skill", manifest)
        self.assertIn("Use atomic-docs to create storage-mode-aware project documentation.", manifest)
        self.assertIn("Use atomic-docs to refresh atom files from source-code changes.", manifest)
        self.assertNotIn("refresh atomic.md docs", manifest)
        self.assertIn("Use atomic-docs to inspect intent, implementation, planned changes, and gaps.", manifest)

    def test_docs_root_contract_supports_storage_mode_selection(self) -> None:
        text = read(DOCS_REFS / "docs-root-and-config.md")
        self.assertIn("Do not assume a hardcoded `docs/` root", text)
        self.assertIn("ask the user to choose a storage mode", text)
        self.assertIn("Supported storage modes are `submodule` and `repository`", text)
        self.assertIn("`.stageflow/atomic-docs.json`", text)
        self.assertIn("storage-mode contract", text)
        self.assertIn("inspect `.gitmodules`", text)
        self.assertIn("exactly one candidate, still ask the user to confirm", text)
        self.assertIn("For `repository` mode", text)
        self.assertIn("repository-local managed docs root", text)
        self.assertIn("This root does not need to appear in `.gitmodules`", text)
        self.assertIn("Do not infer `submodule` mode merely because `.gitmodules` exists", text)
        self.assertIn("Do not infer `repository` mode merely because a `docs/` directory exists", text)
        for field in ["storage_mode", "docs_root", "source_root", "baseline_metadata_path"]:
            self.assertIn(field, text)
        self.assertIn('"storage_mode": "submodule"', text)
        self.assertIn('"storage_mode": "repository"', text)
        self.assertIn('"baseline_metadata_path": "source-baseline.json"', text)
        self.assertIn("docs-root-relative path", text)
        self.assertIn("The default is `source-baseline.json`", text)
        self.assertIn("resolves to `docs/source-baseline.json`, not `docs/docs/source-baseline.json`", text)
        self.assertIn("source repository root used for diffs", text)
        self.assertIn("Do not silently create a real submodule", text)
        self.assertIn("repository-local docs directory", text)
        self.assertIn("accepted the docs-root setup scope and config write", text)
        self.assertIn("explicitly selects a storage mode, selects a managed docs root", text)
        self.assertIn("paired draft criteria document allowed by `criteria-flow.md`", text)

    def test_docs_skill_requires_write_approval_for_managed_state(self) -> None:
        text = read(DOCS_SKILL)
        self.assertIn("accepted the explicit docs operation scope and change plan", text)
        self.assertIn("limited draft write action", text)
        self.assertIn("accepted bootstrap scope", text)
        self.assertIn("project/atomization-criteria.md", text)
        for write_target in [
            "managed docs",
            "atom files",
            "graph corrections",
            "source-baseline metadata",
            "`.stageflow/atomic-docs.json`",
        ]:
            self.assertIn(write_target, text)
        self.assertIn("Stageflow plan approval as separate from managed-docs-root approval", text)
        self.assertIn("Write only the paths and actions accepted by the user", text)

    def test_docs_skill_uses_file_first_criteria_before_subagent_writing_and_review(self) -> None:
        text = read(DOCS_SKILL)
        self.assertIn("first atomic-docs write action", text)
        self.assertIn("limited draft creation or update", text)
        self.assertIn("user conversation criteria, prohibitions, atomization concerns", text)
        self.assertIn("criteria-review/revision cycles until the criteria draft has no blocking structure issues", text)
        self.assertIn("run an independent criteria-review subagent", text)
        self.assertIn("revise `project/atomization-criteria.md` until the reviewer reports no blocking issues", text)
        self.assertIn("criteria document itself as the center of user revision and approval after criteria-review PASS", text)
        self.assertIn("Do not start domain atom writing or domain writer/reviewer subagent work until the criteria document is approved", text)
        self.assertIn("Use only an approved criteria document as required input", text)
        self.assertIn("Do not require a Codex Goal for bootstrap criteria draft creation or criteria-review subagents", text)
        self.assertIn("current request already accepted bootstrap scope", text)
        self.assertIn("summarize the written criteria, provide the `project/atomization-criteria.md` path", text)
        self.assertIn("ask the user to inspect it", text)
        self.assertIn("proceed only after the user confirms the content has no issue or approves it", text)
        self.assertIn("shared quality standard plus role mapping", text)
        self.assertIn("not divergent role-specific checklists", text)
        self.assertIn("separate full discovery candidates from accepted write scope rules", text)
        self.assertIn("keep operation-local scope out of durable criteria and domain approval status", text)
        self.assertIn("domain/category boundary decisions, behavior-level atom candidates, accepted-scope rules, and open blockers", text)
        self.assertIn("separate project-native feature candidates, capability/common promotion proposals", text)
        self.assertIn("prefer stable language that project maintainers already recognize", text)
        self.assertIn("keep leaf workflow or behavior candidates out of the domain/category boundary map", text)
        self.assertIn("remove cache paths, reset/delete notes, reviewer agent names", text)
        self.assertIn("reject broad domains or broad category groupings", text)
        self.assertIn("After criteria approval and accepted docs write scope", text)
        self.assertIn("create or reuse a Codex Goal before starting docs generation work", text)

    def test_atomic_document_contract_sections_and_boundaries(self) -> None:
        text = read_atomic_contract_bundle()
        self.assertIn("<doc-root>/<domain-path>/<file-slug>-atom.md", text)
        self.assertIn("<doc-root>/project/atomization-criteria.md", text)
        self.assertIn("criteria document is not an atom", text)
        self.assertIn("category or subdomain segments", text)
        self.assertIn("mutable placement path, not atom identity", text)
        self.assertIn("frontmatter `atom_key`", text)
        self.assertIn("stable atom identity", text)
        self.assertIn("lower-kebab-case", text)
        self.assertIn("unchanged by category moves, domain-path moves, file-slug changes", text)
        self.assertIn("legacy fallback", text)
        self.assertIn("Every atom file must end with `-atom.md`", text)
        self.assertIn("globally unique", text)
        self.assertNotIn("<doc-root>/<domain>/<atomic-target>/atomic.md", text)
        for section in ["Intent", "Rules", "Current Implementation", "Planned Changes", "Gaps"]:
            self.assertIn(section, text)
        self.assertIn("marked as inferred", text)
        self.assertIn("Do not put per-atomic freshness/status fields inside atom files", text)
        self.assertIn("Do not store per-file commit status", text)
        self.assertNotIn("<doc-root>/<domain>/current-state", text)

    def test_change_judgment_policy_labels_and_priority(self) -> None:
        text = read(DOCS_REFS / "change-judgment-policy.md")
        self.assertIn("Change Judgment Policy", text)
        self.assertIn("does not add top-level per-atom status fields", text)
        for label in [
            "matches_confirmed_intent",
            "bug_or_regression",
            "missing_required_behavior",
            "unapproved_implemented_behavior",
            "out_of_scope_behavior",
            "confirmation_needed",
            "docs_stale",
        ]:
            self.assertIn(label, text)
        self.assertIn("Apply the first matching judgment", text)
        self.assertIn("docs baseline is older", text)
        self.assertIn("relevant `Intent`, `Rules`, requirement, boundary, or source mapping is inferred or ambiguous", text)
        self.assertIn("confirmed non-goal, excluded behavior, adjacent-domain boundary, or policy boundary", text)
        self.assertIn("confirmed required behavior is missing", text)
        self.assertIn("conflicts with confirmed `Intent`, `Rules`, acceptance criteria", text)
        self.assertIn("inferred `Intent` or inferred `Rules` alone", text)
        self.assertIn("Explanatory prose in this file is not reusable managed-docs content", text)

    def test_change_judgment_policy_evidence_and_planned_change_types(self) -> None:
        text = read(DOCS_REFS / "change-judgment-policy.md")
        for required in [
            "atom path, stable `atom_key` when available, related AID values, source evidence, judgment label, reason",
            "confirmed `Intent`",
            "approved required `Planned Changes`",
            "non-goals",
            "excluded behavior",
            "source baseline metadata",
            "not the absence of a `Gaps` item",
        ]:
            self.assertIn(required, text)
        for planned_type in [
            "approved_required_change",
            "approved_optional_change",
            "tentative_future_change",
            "implemented_pending_confirmation",
        ]:
            self.assertIn(planned_type, text)
        self.assertIn("Do not collapse bug, missing required behavior, unapproved implementation, out-of-scope behavior", text)

    def test_atomization_criteria_document_contract_is_persisted(self) -> None:
        text = read_atomic_contract_bundle()
        self.assertIn("Atomization Criteria Document", text)
        self.assertIn("<doc-root>/project/atomization-criteria.md", text)
        self.assertIn("Existing `<doc-root>/project/atomization-criteria-atom.md` files are legacy artifacts", text)
        self.assertIn("first atomic-docs write action", text)
        self.assertIn("draft criteria document is a review artifact", text)
        self.assertIn("승인 상태: 초안, 사용자 승인 대기", text)
        self.assertIn("승인 상태: 사용자 승인 완료", text)
        self.assertIn("must not be used as the required input for domain writer subagents", text)
        self.assertIn("Record user-conversation criteria in the draft before code exploration", text)
        self.assertIn("do not copy illustrative wording from skill references", text)
        self.assertIn("must not follow the `*-atom.md` path contract", text)
        self.assertIn("required atom sections `Intent`, `Rules`, `Current Implementation`, `Planned Changes`, and `Gaps`", text)
        for section in [
            "목적",
            "승인 상태",
            "문서 루트와 작업 범위",
            "도메인 분할 기준",
            "후보/승인 도메인 맵",
            "Atom 후보 맵",
            "Atom화 관점",
            "서비스 로직 커버리지 요구사항",
            "작성/리뷰 공통 품질 기준",
            "서브에이전트 역할 분담",
            "판정 라벨 사용 기준",
            "미해결 질문과 승인 차단 항목",
        ]:
            self.assertIn(section, text)
        self.assertIn("Do not use English visible criteria headings", text)
        self.assertIn("in Korean managed docs", text)
        for perspective in [
            "domain capability",
            "entry surface",
            "service/application flow",
            "state transition",
            "policy/rule",
            "integration contract",
            "persistence/side effect",
            "core business term",
            "failure/recovery",
        ]:
            self.assertIn(perspective, text)
        for required_detail in [
            "Atom 후보 기준",
            "소스 근거로만 둘 기준",
            "해당 없음 사유",
            "분리/병합 기준",
            "소스 근거 요구사항",
            "미해결 질문",
        ]:
            self.assertIn(required_detail, text)
        self.assertIn("every entry under `Atom화 관점` with these exact visible subfields", text)
        self.assertIn("Do not accept one-line perspective summaries", text)
        self.assertIn("missing one of the required Korean subfields", text)
        self.assertIn("empty or placeholder-only", text)
        self.assertIn("uses English visible labels for criteria sections or fields", text)
        self.assertIn("concrete `해당 없음 사유` or `미해결 질문`", text)
        for domain_detail in [
            "domain partitioning criteria",
            "candidate or approved domain map",
            "candidate or approved domain map that records only durable domain or category boundaries",
            "not behavior-level atom candidates",
            "project-native feature/root language as the default starting point",
            "full discovery candidate map separated from accepted-scope rules",
            "accepted-scope rules that explain how a later write scope is chosen",
            "domain name",
            "승인 상태",
            "소유 동작",
            "제외 동작",
            "인접 도메인 경계",
            "함께 변경되는 이유",
            "소스 근거",
            "근거 성격",
            "미해결 질문",
            "`candidate`, `approved`, `rejected`, and `needs_confirmation`",
        ]:
            self.assertIn(domain_detail, text)
        for hybrid_field in [
            "`project-native name`",
            "`source feature root`",
            "`optional capability alias`",
            "`promotion reason`",
            "`approval state`",
        ]:
            self.assertIn(hybrid_field, text)
        for state_rule in [
            "`candidate` means a narrow durable boundary candidate",
            "`approved` means the user approved that durable boundary as part of the criteria's durable domain map",
            "It does not mean the domain is inside the current operation's accepted write scope",
            "Current accepted write scope is operation-local",
            "`.stageflow/atomic-docs/requests/<request-id>/work-state.json`",
            "must not become the live progress ledger for the current run",
            "`needs_confirmation` means there is source evidence and boundary rationale",
            "`rejected` means a broad, unsupported, excluded, or otherwise invalid grouping",
            "Broad domains and broad category groupings are unconditional criteria-review failures",
            "only as `rejected` with the reason, or replace it with concrete split proposals",
            "source identifiers alone are not valid domain-boundary evidence",
            "identifier-only evidence",
            "durable domain approval status is used to encode operation-local write scope",
        ]:
            self.assertIn(state_rule, text)
        for atom_candidate_rule in [
            "a separate `Atom 후보 맵` or `Atom 후보/분할 제안` area",
            "behavior-level atom candidates",
            "each atom candidate with `candidate atom_key`, tentative path or slug, owning domain/category path, source evidence, split/merge reason, and unresolved question",
            "The `후보/승인 도메인 맵` must not contain leaf behavior entries",
            "unless the entry is framed as a durable domain/category boundary",
            "put the behavior under `Atom 후보 맵` or a concrete split proposal",
        ]:
            self.assertIn(atom_candidate_rule, text)
        self.assertIn("Existing `<doc-root>/project/project-goal-atom.md` and `<doc-root>/project/project-glossary-atom.md` files are legacy artifacts", text)
        self.assertIn("do not use those paths as defaults for new project goal or glossary work", text)
        self.assertIn("one shared writer/reviewer quality standard", text)
        self.assertIn("atom candidate map use", text)
        self.assertIn("frontmatter `atom_key`", text)
        self.assertIn("AID assignment with `[AID:<atom_key>.<section-code>.<NNN>]`", text)
        self.assertIn("graph `target_key`/`target_path` rules", text)
        self.assertIn("shared atom identity rules", text)
        self.assertIn("graph `target_key` as the target atom's `atom_key`", text)
        self.assertIn("graph `target_path` as a mutable locator", text)
        self.assertIn("subagent role mapping", text)
        self.assertIn("must not maintain separate writer-only and reviewer-only quality rules", text)
        self.assertIn("single acceptance standard", text)
        self.assertIn("Every writer obligation must be reviewable by the same shared criterion", text)
        self.assertIn("every reviewer FAIL condition must map to the same shared criterion or an explicit phase gate", text)
        self.assertIn("Do not add hidden reviewer-only quality bars or writer-only obligations", text)
        self.assertIn("writer and reviewer rules appear as divergent role-specific checklists", text)
        self.assertIn("full discovery candidates, approved domain/category boundaries, accepted-scope rules, and behavior-level atom candidates are mixed together", text)
        self.assertIn("leaf behavior candidate appears directly in the domain/category boundary map", text)
        self.assertIn("shared quality criteria omit frontmatter `atom_key`, AID, graph `target_key`, or graph `target_path` rules", text)
        self.assertIn("remove one-off operation logs such as plugin cache paths, reset/delete notes, reviewer agent names", text)
        self.assertIn("transient \"currently none\" or `현재 없음` status notes", text)
        self.assertIn("not fixed document types", text)
        self.assertIn("Do not accept a criteria document that only lists perspective names or domain names", text)
        self.assertNotIn("endpoint document", text)

    def test_atomic_document_contract_defines_project_documents_as_non_atoms(self) -> None:
        text = read(DOCS_REFS / "atomic-document-contract.md")
        self.assertIn("Project Document Contract", text)
        for project_doc in [
            "<doc-root>/project/atomization-criteria.md",
            "<doc-root>/project/project-goal.md",
            "<doc-root>/project/project-glossary.md",
            "<doc-root>/project/service-logic-inventory.md",
            "<doc-root>/project/source-convention.md",
        ]:
            self.assertIn(project_doc, text)
        self.assertIn("Project documents are non-atom documents", text)
        self.assertIn("must not follow the `*-atom.md` path contract", text)
        self.assertIn("must not require frontmatter `atom_key`", text)
        self.assertIn("must not require AID values", text)
        self.assertIn("must not use `graph_edges`", text)
        self.assertIn("must not require the atom sections `Intent`, `Rules`, `Current Implementation`, `Planned Changes`, and `Gaps`", text)
        self.assertIn("Existing `<doc-root>/project/project-goal-atom.md` and `<doc-root>/project/project-glossary-atom.md` are legacy project-document artifacts", text)
        self.assertIn("propose a migration or update to `project/project-goal.md` and `project/project-glossary.md`", text)
        self.assertIn("service or product purpose, target users or callers, success criteria, non-goals", text)
        self.assertIn("config paths, baseline metadata paths, cache paths, reset notes, deletion notes, reviewer logs", text)
        for glossary_field in [
            "meaning",
            "owning domain",
            "actor/system action",
            "source of truth",
            "stored vs computed",
            "related rules/status",
            "aliases",
            "forbidden conflations",
            "uncertainty",
        ]:
            self.assertIn(glossary_field, text)
        for inventory_field in [
            "source identifiers",
            "conditions/branches",
            "validation/guard",
            "state transition",
            "persistence side effect",
            "external call",
            "error/recovery",
            "basis",
            "owning atom_key",
            "related AID",
            "judgment label",
        ]:
            self.assertIn(inventory_field, text)
        self.assertIn("One-line behavior summaries are not enough for baseline readiness", text)
        self.assertIn("runtime-impacting behavior without a related atom_key/AID or a coverage gap", text)
        self.assertIn("Fail when a project document directly claims code is implemented, missing, buggy, matching, or out of scope", text)

    def test_atomic_document_contract_defines_source_convention_document_format(self) -> None:
        text = read_atomic_contract_bundle()
        self.assertIn("Source Convention Document", text)
        self.assertIn("<doc-root>/project/source-convention.md", text)
        self.assertIn("source convention document is not a service-logic atom", text)
        self.assertIn("not direct code suitability evidence", text)
        self.assertIn("must not follow the `*-atom.md` path contract", text)
        self.assertIn("frontmatter `atom_key`, or AID policy", text)
        self.assertIn("not a graph target", text)
        for section in [
            "목적",
            "승인 상태",
            "적용 범위",
            "소스 구조 관례",
            "동작 영향 관례",
            "비동작 코드 스타일",
            "Formatter / Linter / Static Check 근거",
            "서비스 로직 Atom과의 경계",
            "리뷰 기준",
            "미해결 질문",
        ]:
            self.assertIn(section, text)
        self.assertIn("not a general style guide for its own sake", text)
        self.assertIn("source interpretation conventions", text)
        self.assertIn("runtime-impacting conventions", text)
        self.assertIn("non-runtime code style", text)
        self.assertIn("formatter, linter, or static-check evidence", text)
        self.assertIn("Non-runtime code style belongs only in `project/source-convention.md`", text)
        self.assertIn("Runtime-impacting conventions may be summarized", text)
        self.assertIn("actual code judgment basis must also appear as natural-language behavior", text)
        for judgment_label in [
            "bug_or_regression",
            "missing_required_behavior",
            "matches_confirmed_intent",
            "unapproved_implemented_behavior",
            "out_of_scope_behavior",
        ]:
            self.assertIn(judgment_label, text)
        self.assertIn("source convention document alone cannot support", text)
        self.assertIn("request moving that material to `project/source-convention.md`", text)
        self.assertIn("coverage gap or `confirmation_needed`", text)

    def test_atomic_document_contract_supports_code_judgment_evidence(self) -> None:
        text = read_atomic_contract_bundle()
        self.assertIn("Judgment Evidence Policy", text)
        self.assertIn("required, optional, excluded, or boundary-defining", text)
        self.assertIn("acceptance criteria", text)
        self.assertIn("source-observed implementation facts with source evidence", text)
        for planned_type in [
            "approved_required_change",
            "approved_optional_change",
            "tentative_future_change",
            "implemented_pending_confirmation",
        ]:
            self.assertIn(planned_type, text)
        self.assertIn("one judgment label from `change-judgment-policy.md`", text)
        self.assertIn("Do not add top-level per-atom status fields", text)
        self.assertIn("lack of a `Gaps` item", text)
        self.assertIn("Approved project documents may provide context such as non-goals or terminology boundaries", text)
        self.assertIn("domain context atoms must preserve excluded behavior and adjacent-domain boundaries", text)
        self.assertIn("A service judgment still needs service logic atom content, source evidence, baseline metadata, and a controlled judgment label", text)

    def test_atomic_document_contract_requires_atom_line_ids(self) -> None:
        text = read_atomic_contract_bundle()
        self.assertIn("Atom Line ID Policy", text)
        self.assertIn("Every `*-atom.md` file must assign a stable unique ID", text)
        self.assertIn("judgment-relevant meaning line", text)
        self.assertIn("[AID:<atom_key>.<section-code>.<NNN>]", text)
        self.assertIn("[AID:paid-order-processing.impl.003]", text)
        for section_code in ["`intent`", "`rules`", "`impl`", "`plan`", "`gap`", "`source`"]:
            self.assertIn(section_code, text)
        self.assertIn("`- [AID:...] 내용`", text)
        self.assertIn("`[AID:...] 내용`", text)
        self.assertIn("an `AID` column for tables", text)
        self.assertIn("globally unique across the docs set", text)
        self.assertIn("New AID values use the target atom's stable `atom_key`", text)
        for excluded in [
            "frontmatter",
            "`graph_edges`",
            "blank lines",
            "section headings",
            "code fence markers",
            "purely structural Markdown",
        ]:
            self.assertIn(excluded, text)
        self.assertIn("Project documents such as `project/atomization-criteria.md`, `project/project-goal.md`, `project/project-glossary.md`, `project/service-logic-inventory.md`, and `project/source-convention.md` are not atoms", text)
        self.assertIn("not required to use AID values", text)
        self.assertIn("keep its existing AID", text)
        self.assertIn("category/domain-path move", text)
        self.assertIn("Category moves, file renames, path drift, and atom slug changes are not AID change reasons", text)
        self.assertIn("Assign new AID values only to newly introduced meaning lines", text)
        self.assertIn("Do not renumber existing AID values", text)
        self.assertIn("record the migration explicitly", text)
        self.assertIn("use frontmatter `atom_key` for current identity", text)

    def test_atomic_document_contract_requires_service_logic_natural_language_coverage(self) -> None:
        text = read_atomic_contract_bundle()
        self.assertIn("Service Logic Natural-Language Coverage", text)
        self.assertIn("natural-language service logic standard", text)
        self.assertIn("meaningful application, service, and domain logic", text)
        for required_behavior in [
            "conditions",
            "branches",
            "state transitions",
            "validation",
            "permission checks",
            "policy rules",
            "transaction or idempotency behavior",
            "persistence side effects",
            "external calls",
            "emitted events",
            "error handling",
            "recovery behavior",
        ]:
            self.assertIn(required_behavior, text)
        self.assertIn("endpoint lists, controller lists, service class names, method names", text)
        self.assertIn("source evidence only until the atom explains in natural language", text)
        self.assertIn("A bare list of source identifiers, endpoints, controllers, service classes, or methods is not sufficient", text)
        for korean_subheading in [
            "### 동작 흐름",
            "### 관찰된 판단 규칙",
            "### 상태와 저장 효과",
            "### 외부 연동과 이벤트",
            "### 실패와 복구 동작",
            "### Source Evidence",
        ]:
            self.assertIn(korean_subheading, text)
        self.assertIn("input conditions, branches or refusals, state changes, stored or external effects, and failure results", text)
        self.assertIn("translated English skeleton", text)
        self.assertIn("method-call sequence", text)
        self.assertIn("service logic coverage gaps", text)

    def test_atomic_docs_requires_source_to_docs_to_code_reconstruction_readiness(self) -> None:
        skill = read(DOCS_SKILL)
        contract = read(DOCS_REFS / "service-logic-coverage.md")
        criteria = read(DOCS_REFS / "criteria-flow.md")
        generation = read(DOCS_REFS / "docs-generation-flow.md")
        inventory = read(DOCS_REFS / "project-documents-and-inventory.md")
        baseline = read(DOCS_REFS / "source-baseline-and-change-plan.md")

        self.assertIn("source-to-docs-to-code implementation reconstruction standard", skill)
        self.assertIn("same functional behavior can be implemented from the docs", skill)
        self.assertIn("implementation-reconstruction-ready", skill)

        self.assertIn("Implementation Reconstruction Coverage", contract)
        self.assertIn("same functional behavior from the docs", contract)
        self.assertIn("pixel-perfect visual design", contract)
        for frontend_detail in [
            "app shell behavior",
            "route/hash/query handling",
            "selected entity and persistence",
            "form field matrix",
            "collection editor behavior",
            "readiness blocker order",
            "detail routes",
            "basic design/state presentation",
        ]:
            self.assertIn(frontend_detail, contract)
        for backend_detail in [
            "API contract",
            "request/response payload",
            "authorization/authentication",
            "transaction or idempotency behavior",
            "persistence mutation/read model",
            "async job/event behavior",
            "error/retry/recovery semantics",
        ]:
            self.assertIn(backend_detail, contract)
        self.assertIn("one-line inventory", contract)
        self.assertIn("unresolved `confirmation_needed`", contract)
        self.assertIn("must make implementation reconstruction coverage an explicit shared standard before user approval", contract)
        self.assertIn("applicable frontend/UI coverage, backend/API/service/job/integration coverage, explicit not-applicable reasons", contract)
        self.assertIn("omits implementation reconstruction coverage, applicable or not-applicable frontend/UI coverage, backend/API/service/job/integration coverage", contract)

        self.assertIn("implementation reconstruction coverage", criteria)
        self.assertIn("The `서비스 로직 커버리지 요구사항` and `작성/리뷰 공통 품질 기준` sections must carry the implementation reconstruction standard", criteria)
        self.assertIn("applicable frontend/UI coverage, backend/API/service/job/integration coverage, explicit not-applicable reasons", criteria)
        self.assertIn("treats shallow source-observed inventory as enough for docs-only implementation", criteria)

        self.assertIn("implementation reconstruction coverage map", generation)
        self.assertIn("fail shallow source-observed inventory", generation)
        self.assertIn("Frontend/UI blockers include missing app shell, routing, selected entity, forms, collection editors, detail routes, empty/error states, or basic design/state presentation", generation)
        self.assertIn("Backend/API/service/job/integration blockers include missing API contracts", generation)
        self.assertIn("source-observed inventory rather than implementation-reconstruction-ready docs", generation)

        self.assertIn("reconstruction-critical fields", inventory)
        self.assertIn("entry/screen/route or API/job entry", inventory)
        self.assertIn("UI basic design/state presentation", inventory)
        self.assertIn("backend service/DB/DTO behavior", inventory)
        self.assertIn("operation-local by default", inventory)
        self.assertIn(".stageflow/atomic-docs/requests/<request-id>/inventory.md", inventory)
        self.assertIn("final coverage index", inventory)

        self.assertIn("judgment-ready and implementation-reconstruction-ready scope", baseline)
        self.assertIn("implementation reconstruction readiness for the accepted scope", baseline)
        self.assertIn("frontend/UI coverage, backend/API/service coverage", baseline)
        self.assertIn("post-write gate stored under `.stageflow/atomic-docs/requests/<request-id>/post-write-review.md`", baseline)
        self.assertIn("do not call the scope implementation-reconstruction-ready", baseline)

    def test_atomic_docs_requires_source_discovery_closure(self) -> None:
        skill = read(DOCS_SKILL)
        service = read(DOCS_REFS / "service-logic-coverage.md")
        inventory = read(DOCS_REFS / "project-documents-and-inventory.md")
        generation = read(DOCS_REFS / "docs-generation-flow.md")
        domain = read(DOCS_REFS / "source-convention-and-domain-policy.md")
        criteria = read(DOCS_REFS / "atomization-criteria-contract.md")

        closure_section = section(service, "Source Discovery Closure Gate")
        inventory_section = section(inventory, "Service Logic Inventory")

        for required in [
            "source discovery closure",
            "source surface or aggregate",
            "`atom_key`/AID",
            "coverage gap",
            "`out_of_scope`",
            "not-applicable",
            "Unmapped or orphan source behavior",
        ]:
            self.assertIn(required, skill + "\n" + closure_section)

        for required in [
            "source discovery closure table",
            "source feature inventory aggregate has no disposition",
            "source discovery closure/disposition",
            "row-level closure",
            "route/controller/service/policy/persistence/workflow aggregate",
        ]:
            self.assertIn(required, generation + "\n" + criteria + "\n" + inventory_section)

        self.assertIn("Rejected broad roots need concrete aggregate disposition", domain)
        for disposition in [
            "atom candidate",
            "concrete split proposal",
            "coverage gap",
            "`out_of_scope`",
            "not-applicable item",
        ]:
            self.assertIn(disposition, domain)

    def test_atomic_docs_requires_high_risk_atom_matrices(self) -> None:
        text = "\n".join(
            [
                read(DOCS_SKILL),
                read(DOCS_REFS / "service-logic-coverage.md"),
                read(DOCS_REFS / "docs-generation-flow.md"),
            ]
        ).lower()

        for category in [
            "account/auth/admin management",
            "delete/approve",
            "payment/refund",
            "external integration",
            "persistence mutation",
            "idempotency",
            "failure recovery",
        ]:
            self.assertIn(category, text)

        for matrix in [
            "payload/field matrix",
            "branch matrix",
            "state/persistence effect matrix",
            "failure/recovery matrix",
            "not-applicable reason",
        ]:
            self.assertIn(matrix, text)

    def test_atomic_docs_reviewer_answer_sheet_and_claim_audit(self) -> None:
        generation = read(DOCS_REFS / "docs-generation-flow.md")
        service = read(DOCS_REFS / "service-logic-coverage.md")
        review_section = section(generation, "Domain Subagent Workflow")

        for required in [
            "reviewer answer sheet",
            "same functional behavior can be implemented from docs alone",
            "fields/branches/validation/state/failure details still require source",
            "source identifiers appear without natural-language behavior",
            "`AID claim -> checked entry path -> null/blank/default/fallback/exception branch -> source evidence`",
        ]:
            self.assertIn(required, review_section)

        fidelity_section = section(service, "Source Fact Fidelity Gate")
        for branch in [
            "null handling",
            "blank handling",
            "default value fallback",
            "explicit exception branches",
            "persistence calls",
        ]:
            self.assertIn(branch, fidelity_section)

    def test_atomic_docs_criteria_lifecycle_and_baseline_scope_guard(self) -> None:
        skill = read(DOCS_SKILL)
        generation = read(DOCS_REFS / "docs-generation-flow.md")
        criteria = read(DOCS_REFS / "atomization-criteria-contract.md")
        baseline = read(DOCS_REFS / "source-baseline-and-change-plan.md")

        for required in [
            "criteria lifecycle reconciliation",
            "after criteria approval",
            "after docs generation",
            "draft/future/pending/current-run state",
            "atomic-docs operation state",
            "stale draft/future/pending/current-run state",
        ]:
            self.assertIn(required, skill + "\n" + generation)

        self.assertIn("remove obsolete draft-only or pending-approval blockers", criteria)
        self.assertIn("Approved criteria should contain durable criteria", criteria)

        for required in [
            "partial scope from project-wide scope",
            "accepted scope",
            "source commit baseline",
            "operation-local post-write PASS",
            "implementation-reconstruction readiness",
            "must not be treated as matching confirmed intent",
            "`docs_stale`",
        ]:
            self.assertIn(required, baseline)

    def test_atomic_docs_quality_gate_rejects_shallow_and_over_compressed_atoms(self) -> None:
        skill = read(DOCS_SKILL)
        contract = read_atomic_contract_bundle()
        generation = read(DOCS_REFS / "docs-generation-flow.md")

        self.assertIn("Do not use atom count or line count as a quality proxy", skill)
        self.assertIn("Do not use atom count, file count, or line count as a quality threshold", contract)
        self.assertIn("Review the density of reconstruction-critical decisions", contract)
        for shallow_marker in [
            "Shallow atom review must fail",
            "forms, editors, routes, access guards, payloads, validations, readiness, save/delete behavior, API/service contracts, or state transitions",
            "concrete fields, branches, rules, payload shape, contract semantics, state effects, or failure outcomes",
            "`field matrix`, `payload`, `validation`, `contract`, `readiness`, or `state transition`",
            "A sentence such as \"handles local validation\", \"maps payload\", or \"calls the API\" is not enough",
        ]:
            self.assertIn(shallow_marker, contract)
        for split_marker in [
            "Split over-compressed atoms",
            "An atom is over-compressed",
            "independent entry points, user actions, save/delete scopes, API contracts, state transitions, persistence effects, or failure/recovery paths",
            "Use context atoms for broad boundaries",
            "Choose split boundaries from implementation and judgment independence",
            "not from a project-specific domain list",
        ]:
            self.assertIn(split_marker, skill + "\n" + contract)
        self.assertIn("Reviewer subagents must also fail shallow behavior atoms", generation)
        self.assertIn("They must fail over-compressed atoms", generation)
        self.assertIn("Review FAIL is not a completion state", generation)
        self.assertIn("rerun the same relevant review until PASS", generation)
        self.assertIn("Do not report the docs operation as complete, judgment-ready, or implementation-reconstruction-ready before that PASS", generation)

    def test_atomic_document_contract_requires_source_fact_fidelity(self) -> None:
        text = read(DOCS_REFS / "service-logic-coverage.md")
        self.assertIn("Source Fact Fidelity Gate", text)
        self.assertIn("actually reachable through the inspected entry path", text)
        self.assertIn("Do not simplify a branch into the behavior that a field annotation, method name, service class name, or DTO type seems to imply", text)
        for source_detail in [
            "endpoint or caller binding",
            "validator activation",
            "service guard",
            "null handling",
            "blank handling",
            "optional dependency fallback",
            "default value fallback",
            "explicit exception branches",
            "runtime exception possibility",
            "transaction mode",
            "persistence calls",
        ]:
            self.assertIn(source_detail, text)
        self.assertIn("Do not rewrite an allowed fallback path as a guaranteed validation failure", text)
        self.assertIn("do not describe a behavior as safe or recovered when the source can throw an unhandled runtime exception", text)
        self.assertIn("a request field annotation is not enough to claim that the endpoint rejects the request", text)
        self.assertIn("source evidence, confirmed or inferred basis, affected behavior, next action", text)
        self.assertIn("related stable `atom_key` and AID values", text)

    def test_judgment_items_use_korean_labels_in_korean_docs(self) -> None:
        contract = read(DOCS_REFS / "atom-format-and-judgment.md")
        policy = read(DOCS_REFS / "change-judgment-policy.md")
        language = read(DOCS_REFS / "language-policy.md")
        combined = contract + "\n" + policy + "\n" + language

        self.assertIn("For Korean managed docs, write judgment-bearing `Gaps`, `Planned Changes`, change plan items, and review findings with Korean-visible field labels", contract)
        self.assertIn("For Korean managed docs, keep the controlled judgment label unchanged but write the visible field labels and explanation prose in Korean", policy)
        for korean_label in [
            "`판정 라벨`",
            "`관련 atom_key`",
            "`관련 AID`",
            "`소스 근거`",
            "`근거`",
            "`영향받는 동작`",
            "`다음 조치`",
            "`조건/분기`",
            "`검증/가드`",
            "`상태 전이`",
            "`저장 효과`",
            "`외부 호출`",
            "`실패/복구`",
        ]:
            self.assertIn(korean_label, combined)
        for english_label in [
            "`affected behavior`",
            "`next action`",
            "`basis`",
            "`source evidence`",
            "`judgment label`",
            "`conditions/branches`",
            "`validation/guard`",
            "`state transition`",
            "`persistence side effect`",
            "`external call`",
            "`error/recovery`",
        ]:
            self.assertIn(english_label, combined)
        self.assertIn("Do not use English scaffold labels", contract)
        self.assertIn("Do not write English scaffold labels", policy)
        self.assertIn("as the visible prose structure", language)

    def test_atomic_document_contract_separates_goal_scope_from_judgment_evidence(self) -> None:
        text = read(DOCS_REFS / "service-logic-coverage.md")
        self.assertIn("Atomic Docs Goal Boundary", text)
        self.assertIn("execution scope for performing the accepted docs operation", text)
        self.assertIn("does not replace criteria approval, accepted docs write scope", text)
        self.assertIn("judgment labels, source evidence, user review, or source-baseline metadata", text)
        self.assertIn("Do not write Goal status or Goal completion as atom-level status", text)
        self.assertIn("Code suitability judgments still come from approved criteria, generated atoms, source evidence", text)

    def test_atomic_document_contract_rejects_evasive_split_or_identifier_only_coverage(self) -> None:
        text = read_atomic_contract_bundle()
        self.assertIn("Do not leave an evasive split or coverage gap", text)
        self.assertIn("in place of documenting inspected service logic", text)
        self.assertIn("proposed owners, unresolved question, and the behavior already observed", text)
        self.assertIn("Do not use source identifiers without natural-language behavior as proof", text)

    def test_domain_boundary_policy_uses_general_quality_gate(self) -> None:
        text = read(DOCS_REFS / "source-convention-and-domain-policy.md")
        self.assertIn("Domain Boundary Quality Gate", text)
        self.assertIn("durable ownership boundary", text)
        for criterion in [
            "product or business capability",
            "user-visible workflow",
            "operational responsibility",
            "integration contract",
            "shared policy or platform concern",
        ]:
            self.assertIn(criterion, text)
        for required_boundary in [
            "the behavior the domain owns",
            "the behavior the domain excludes",
            "the adjacent-domain boundary",
            "why the atom files in the domain tend to change together",
        ]:
            self.assertIn(required_boundary, text)
        self.assertIn("documentation section type, lifecycle state, task status, freshness state, review state", text)
        self.assertIn("temporary work grouping, code-layer grouping, screen grouping, category grouping, or generic catch-all bucket", text)
        self.assertIn("category grouping", text)
        self.assertIn("criteria-review must fail it unless it is recorded as `rejected` broad grouping", text)
        self.assertIn("split proposal based on observed capabilities", text)
        self.assertIn("does not account for obvious concrete aggregates underneath it", text)
        self.assertIn("no route/controller/service/policy/persistence/workflow evidence supports a durable lower-level boundary", text)
        self.assertNotIn("Do not use document state names such as", text)

    def test_hybrid_domain_naming_policy_prefers_project_native_language(self) -> None:
        text = read(DOCS_REFS / "source-convention-and-domain-policy.md")
        self.assertIn("Hybrid Domain Naming Policy", text)
        self.assertIn("Use a hybrid domain naming model", text)
        self.assertIn("Start with project-native feature/root language", text)
        self.assertIn("project-native feature/root language as the default starting point", text)
        for field in [
            "`project-native name`",
            "`source feature root`",
            "`optional capability alias`",
            "`promotion reason`",
            "`approval state`",
        ]:
            self.assertIn(field, text)
        self.assertIn("AI-renamed domain labels are not valid default domain names", text)
        self.assertIn("must not silently rename that root into a new abstract capability label", text)
        self.assertIn("user approval or user vocabulary", text)
        self.assertIn("existing managed-docs-root terminology", text)
        self.assertIn("durable ownership evidence showing the capability crosses multiple source feature roots", text)
        self.assertIn("cross-feature ownership, shared persistence or state, shared policy, or shared recovery question", text)
        self.assertIn("Without that evidence, keep the project-native feature/root name", text)
        self.assertIn("Broad source feature roots", text)
        self.assertIn("category/root surfaces or split proposals", text)
        self.assertIn("Atom candidates must point their owning domain/category path at an approved or candidate hybrid boundary", text)
        self.assertIn("AI-renamed label that lacks user/source trace or promotion evidence", text)
        self.assertIn("the codebase's own stable feature/root language is still the default naming input", text)
        self.assertIn("Prefer project/user business language for the promoted aggregate", text)
        self.assertIn("do not default to technical labels such as `configuration`", text)

    def test_domain_discovery_promotes_concrete_aggregates_under_broad_roots(self) -> None:
        text = read(DOCS_REFS / "source-convention-and-domain-policy.md")
        self.assertIn("When a broad source root or category/root surface is rejected", text)
        self.assertIn("still inspect below it for concrete business aggregates", text)
        for evidence in [
            "routes",
            "controllers",
            "service methods",
            "policy rules",
            "persistence side effects",
            "user-visible workflow steps",
        ]:
            self.assertIn(evidence, text)
        self.assertIn("Promote that aggregate to a concrete domain candidate or concrete split proposal", text)
        self.assertIn("owned behavior, excluded behavior, adjacent boundary, and unresolved questions", text)

    def test_core_business_term_coverage_gate_prevents_parent_term_gaps(self) -> None:
        text = read(DOCS_REFS / "source-convention-and-domain-policy.md")
        self.assertIn("Core Business Term Coverage Gate", text)
        for evidence_source in [
            "type/interface names",
            "collection keys",
            "UI titles",
            "API payloads",
            "existing domain atoms",
        ]:
            self.assertIn(evidence_source, text)
        self.assertIn("source-repeated business nouns", text)
        self.assertIn("`project/project-glossary.md`", text)
        self.assertIn("appropriate domain atom", text)
        self.assertIn("Do not document a derived concept while its parent business term is missing or underdefined", text)
        self.assertIn("Do not force admin, operator, or screen-centric language", text)
        self.assertIn("services, libraries, jobs, agents, or APIs", text)
        self.assertIn("caller, service, job, policy, or system flow", text)
        self.assertIn("UI or command entry point", text)
        for coverage_item in [
            "business meaning",
            "owning domain",
            "primary actor, user, or system action",
            "source of truth",
            "stored input fields versus API/computed output fields",
            "related status, hold, deduction, threshold, display, or availability rules",
            "aliases, related source identifiers, forbidden conflations, and uncertainty",
        ]:
            self.assertIn(coverage_item, text)
        self.assertIn("change plan or `Gaps`", text)

    def test_refresh_flow_contract_uses_source_baseline_and_change_plan(self) -> None:
        text = read_refs(
            "refresh-flow.md",
            "source-baseline-and-change-plan.md",
            "project-documents-and-inventory.md",
        )
        self.assertIn("one source-code commit hash", text)
        self.assertIn("metadata at the managed docs root", text)
        self.assertIn("git diff <stored-source-hash>..HEAD", text)
        self.assertIn("classify the finding as `docs_stale`", text)
        self.assertIn("map baseline diffs to affected atoms", text)
        self.assertIn("changed source behavior files", text)
        self.assertIn("auxiliary files by default unless the user requested", text)
        self.assertIn("source-to-atom seed discovery", text)
        self.assertIn("domain-grouped change plan", text)
        self.assertIn("new domains, category or domain-path moves, atom splits, atom merges, and split proposals", text)
        self.assertIn("category or domain-path moves", text)
        self.assertIn("atom identity changes", text)
        self.assertIn("`atom_key` preservation", text)
        self.assertIn("implemented-plan candidates", text)
        self.assertIn("rename/merge proposals", text)
        self.assertIn("source-baseline metadata updates and docs-root config writes", text)
        self.assertIn("Update the docs-root source commit baseline metadata only after confirmed docs writes", text)
        self.assertIn("post-write review passes", text)
        self.assertIn("judgment-ready scope", text)
        self.assertIn("must not be used to claim a project-wide judgment-ready baseline", text)
        self.assertIn("core business terms that require glossary or domain atom coverage", text)
        self.assertIn("parent business terms missing or underdefined in the glossary", text)
        self.assertIn("Build an operation-local service logic inventory", text)
        self.assertIn("operation-local service logic inventory items", text)
        self.assertIn("accepted change plan defines the only paths and write actions", text)
        self.assertIn("Do not write atom files, graph corrections, source-baseline metadata", text)

    def test_refresh_flow_creates_draft_criteria_before_subagents(self) -> None:
        text = read_refs(
            "criteria-flow.md",
            "docs-generation-flow.md",
        )
        self.assertIn("Atomization Criteria File-First Flow", text)
        self.assertIn("검토된 Atom화 관점", text)
        self.assertIn("project/atomization-criteria.md", text)
        self.assertIn("legacy `<doc-root>/project/atomization-criteria-atom.md` exists", text)
        self.assertIn("first atomic-docs write action", text)
        self.assertIn("limited draft creation or update", text)
        self.assertIn("draft criteria write action", text)
        self.assertIn("docs root config write when needed", text)
        self.assertIn("confirms both the storage mode and managed docs root", text)
        self.assertIn("`.stageflow/atomic-docs.json`", text)
        self.assertIn("current user request explicitly asks to start, redo, regenerate, or recreate atomic docs", text)
        self.assertIn("do not stop at an approval request", text)
        self.assertIn("then run the Criteria Structure Review Gate and stop for user review only after criteria-review PASS", text)
        self.assertIn("must not also create project goal, project glossary, common context, common policy atoms, domain atoms", text)
        self.assertIn("domain writer/reviewer subagent work, service logic inventory, or source baseline metadata", text)
        self.assertIn("record criteria already stated in the user conversation", text)
        self.assertIn("use code exploration to enrich the criteria document itself", text)
        self.assertIn("not just the change plan", text)
        self.assertIn("first create a source feature inventory from project-native feature/root language", text)
        self.assertIn("scan for route/controller/service/policy/persistence/workflow aggregates beneath broad source roots", text)
        self.assertIn("Use project-native feature/root names as the default domain candidate language", text)
        self.assertIn("capability/common promotion proposals separately", text)
        self.assertIn("durable domain/category boundaries, behavior-level atom candidates", text)
        self.assertIn("full discovery candidate map, and accepted-scope rules separate", text)
        self.assertIn("current per-run accepted write scope is operation-local", text)
        self.assertIn("`.stageflow/atomic-docs/requests/<request-id>/work-state.json`", text)
        self.assertIn("Leaf workflows, policies, states, or service behaviors belong in `Atom 후보 맵`", text)
        self.assertIn("Criteria Structure Review Gate", text)
        self.assertIn("Before asking the user to approve the criteria document, satisfy the Criteria Structure Review Gate", text)
        self.assertIn("Use an independent criteria-review subagent", text)
        self.assertIn("allowed before criteria approval and does not require a Codex Goal", text)
        self.assertIn("any `Atom화 관점` entry is missing one of the required Korean subfields", text)
        self.assertIn("`Atom 후보 기준`, `소스 근거로만 둘 기준`, `해당 없음 사유`, `분리/병합 기준`, `소스 근거 요구사항`, or `미해결 질문`", text)
        self.assertIn("empty, placeholder-only, or a one-line summary", text)
        self.assertIn("Korean managed criteria docs use English visible labels for criteria sections or fields", text)
        self.assertIn("concrete `해당 없음 사유` or `미해결 질문`", text)
        self.assertIn("the criteria draft lacks a source feature inventory before proposing domain names", text)
        self.assertIn("omits the route/controller/service/policy/persistence/workflow aggregate scan", text)
        self.assertIn("the domain map is missing, source-unsupported", text)
        self.assertIn("obvious concrete aggregates beneath it are missing from the domain map", text)
        self.assertIn("AI-renamed domain label that replaces project-native feature/root language", text)
        self.assertIn("without user approval, existing docs terminology, or durable promotion evidence", text)
        self.assertIn("feature-root flow is renamed into an abstract capability label", text)
        self.assertIn("`project-native name`, `source feature root`, `optional capability alias`, `promotion reason`, and `approval state`", text)
        self.assertIn("full discovery candidates, approved domain/category boundaries, accepted-scope rules, and atom candidate map entries are mixed together", text)
        self.assertIn("durable domain approval status is used to encode operation-local write scope", text)
        self.assertIn("live bundle queue, active domain bundle, writer/reviewer PASS/FAIL log", text)
        self.assertIn("leaf behavior, workflow, policy, state-transition, endpoint, or service-method candidates are listed directly in the domain/category boundary map", text)
        self.assertIn("a broad domain or broad category grouping is marked `candidate`, `approved`, or `needs_confirmation`", text)
        self.assertIn("broad source feature root is marked as an approved domain instead of a category/root surface or split proposal", text)
        self.assertIn("capability/common promotion lacks cross-feature ownership, shared persistence/state, shared policy, or shared recovery question evidence", text)
        self.assertIn("category or subdomain structure hides a broad domain", text)
        self.assertIn("domain-boundary evidence is only source identifiers", text)
        self.assertIn("observed behavior summary, excluded behavior, adjacent boundary", text)
        self.assertIn("required atom identity rules: frontmatter `atom_key`, AID format `[AID:<atom_key>.<section-code>.<NNN>]`", text)
        self.assertIn("graph `target_key` as the target atom's `atom_key`", text)
        self.assertIn("graph `target_path` as a mutable locator", text)
        self.assertIn("criteria state semantics for `candidate`, `approved`, `rejected`, or `needs_confirmation`", text)
        self.assertIn("writer and reviewer rules are written as divergent role-specific checklists", text)
        self.assertIn("any reviewer FAIL condition lacks a matching shared criterion or explicit phase gate", text)
        self.assertIn("any writer obligation is not reviewable by the same shared criterion", text)
        self.assertIn("unapproved destructive claims about legacy artifacts", text)
        self.assertIn("one-off draft operation logs such as cache paths, reset/delete notes, reviewer agent names", text)
        self.assertIn("transient `현재 없음` status", text)
        self.assertIn("revise only `project/atomization-criteria.md`", text)
        self.assertIn("rerun the criteria-review subagent", text)
        self.assertIn("reports no blocking issues", text)
        self.assertIn("ready for user review and possible approval", text)
        self.assertIn("does not approve the criteria automatically", text)
        self.assertIn("tell the user the criteria document path", text)
        self.assertIn("summarize the actual written content", text)
        self.assertIn("ask the user to inspect the file and approve it or request changes", text)
        self.assertIn("docs root and accepted-scope rules, domain partitioning criteria, project-native feature candidates, capability/common promotion proposals", text)
        self.assertIn("candidate or approved domain/category boundary map, atom candidate map", text)
        self.assertIn("shared writer/reviewer quality criteria", text)
        self.assertIn("as separate items", text)
        self.assertIn("Do not treat the summary as a substitute for the file", text)
        self.assertIn("a concise Korean summary of what was written", text)
        self.assertIn("Do not proceed to criteria approval state update, Codex Goal creation, service logic inventory", text)
        self.assertIn("until the user confirms the criteria content has no issue or explicitly approves it", text)
        self.assertIn("draft review artifact", text)
        self.assertIn("must not be used as the required input for domain writer subagents", text)
        self.assertIn("candidate names as confirmed domain structure before criteria approval", text)
        self.assertIn("Broad discoveries are not candidates", text)
        self.assertIn("the criteria draft must still show what happened to the concrete aggregates below it", text)
        self.assertIn("Do not let `configuration` or another technical bucket name replace user-visible", text)
        self.assertIn("도메인 분할 기준", text)
        self.assertIn("후보/승인 도메인 맵", text)
        self.assertIn("Atom 후보 맵", text)
        self.assertIn("Domain Subagent Workflow", text)
        self.assertIn("only after the criteria document is approved", text)
        self.assertIn("Each writer subagent must read the approved criteria document", text)
        self.assertIn("maps its output to the same `작성/리뷰 공통 품질 기준` used by reviewers", text)
        self.assertIn("operation-local service logic inventory plus a judgment-labeled domain evidence packet", text)
        self.assertIn("judgment-labeled domain evidence packet", text)
        self.assertIn("atom candidates with stable `atom_key` values", text)
        self.assertIn("graph candidates with `target_key`/`target_path` relationships", text)
        self.assertIn("stable AID assignments for each meaning line", text)
        self.assertIn("change-judgment-policy.md", text)
        self.assertIn("No Example Leakage rule", text)
        self.assertIn("same approved criteria document, `작성/리뷰 공통 품질 기준`", text)
        self.assertIn("must not invent hidden reviewer-only quality bars", text)
        self.assertIn("fails the packet or draft only when a shared criterion or explicit phase gate is not satisfied", text)
        self.assertIn("the domain map is missing or unsupported", text)
        self.assertIn("category structure hides a broad domain", text)
        self.assertIn("meaningful source behavior is missing from the inventory", text)
        self.assertIn("source identifiers appear without natural-language behavior", text)
        self.assertIn("reference example prose appears without user/source trace", text)
        self.assertIn("Korean-first templates", text)
        self.assertIn("Do not produce an English skeleton and translate it afterward", text)
        self.assertIn("Korean docs retain English template residue", text)
        self.assertIn("translated-English phrasing", text)
        self.assertIn("English placeholders", text)
        self.assertIn("English scaffold labels in `Gaps` or review findings", text)
        self.assertIn("`affected behavior`, `next action`, `basis`, `source evidence`, or `judgment label`", text)
        self.assertIn("method-call-sequence-only `Current Implementation`", text)
        self.assertIn("any judgment-relevant meaning line is missing an AID", text)
        self.assertIn("any AID is duplicated across the docs set", text)
        self.assertIn("existing AID values are renumbered instead of preserved", text)
        self.assertIn("judgment-bearing lines or source evidence lines have no AID", text)
        self.assertIn("change plans or review findings omit related AID values", text)
        self.assertIn("cannot explain the implemented behavior from the docs alone", text)
        self.assertIn("cannot be used as code judgment criteria", text)
        self.assertIn("judgment labels are absent or unsupported", text)
        self.assertIn("missing required behavior is confused with out-of-scope behavior", text)
        self.assertIn("candidate domains are treated as confirmed without approval", text)
        self.assertIn("a new atom is missing frontmatter `atom_key`", text)
        self.assertIn("an `atom_key` is duplicated across the docs set", text)
        self.assertIn("an `atom_key` changes only because of category move, file rename, or path drift", text)
        self.assertIn("graph `target_key` does not reference a target atom's `atom_key`", text)
        self.assertIn("stale `target_path` is not corrected", text)
        self.assertIn("independent review subagents", text)
        self.assertIn("It fails the packet or draft only when a shared criterion or explicit phase gate is not satisfied", text)
        self.assertIn("rerun review", text)

    def test_criteria_handoff_requires_decision_ready_summary_and_user_actions(self) -> None:
        skill = read(DOCS_SKILL)
        criteria = read(DOCS_REFS / "criteria-flow.md")

        for required in [
            "decision-ready summary before asking for criteria approval",
            "do not ask with only the criteria document path and an approval request",
            "문서 작성 기준에서 정한 핵심 원칙",
            "도메인/범위 후보",
            "실제 atom 후보 또는 분리 후보",
            "아직 불확실한 점과 승인 차단 항목",
            "지금 승인하면 허용되는 것과 아직 허용되지 않는 것",
        ]:
            self.assertIn(required, skill)

        self.assertIn("Do not ask for criteria approval with only the criteria document path and a generic approval request", criteria)
        self.assertIn("The approval-request summary must be decision-ready", criteria)
        for required in [
            "문서 작성 기준에서 정한 핵심 원칙",
            "도메인/범위 후보",
            "실제 atom 후보 또는 분리 후보",
            "아직 불확실한 점과 승인 차단 항목",
            "지금 승인하면 허용되는 것과 아직 허용되지 않는 것",
        ]:
            self.assertIn(required, criteria)

        self.assertIn("문서 작성 기준 승인은 완료됐고, 아직 실제 서비스 로직 문서는 작성하지 않았다", skill)
        self.assertIn("문서 작성 기준 승인은 완료됐고, 아직 실제 서비스 로직 문서는 작성하지 않았다", criteria)
        for next_action in [
            "전체 문서 작성 시작",
            "특정 도메인만 작성",
            "특정 기능/흐름만 작성",
            "기준을 더 수정",
        ]:
            self.assertIn(next_action, skill)
            self.assertIn(next_action, criteria)
        self.assertIn("Do not present `Goal Gate` as the primary next action", skill)
        self.assertIn("Do not present `Goal Gate` as the primary next action", criteria)
        self.assertIn("Mention the Codex Goal only as an internal requirement or brief note", criteria)

    def test_domain_subagent_workflow_uses_sequential_writer_reviewer_bundles(self) -> None:
        skill = read(DOCS_SKILL)
        generation = read(DOCS_REFS / "docs-generation-flow.md")
        combined = skill + "\n" + generation

        for required in [
            "sequential domain-bundle queue",
            "exactly one writer subagent and exactly one independent reviewer subagent",
            "Do not run multiple domain bundles in parallel by default",
            "rerun the same reviewer cycle until PASS",
            "Do not start the next domain bundle",
            "Only a PASSed domain bundle can become input for the next bundle",
            "reopen the affected earlier bundle",
            "Rerun any dependent later bundles whose PASS basis changed",
            "After every accepted domain bundle PASSes, the main agent, not a domain reviewer, runs the Post-Write Consistency Review Gate",
            "Domain reviewers own their bundle's PASS",
            "the main post-write gate owns cross-domain connectivity",
        ]:
            self.assertIn(required, combined)

        self.assertIn("After criteria approval and Goal handoff, process multi-domain docs generation as a sequential domain-bundle queue", skill)
        self.assertIn("Run the main post-write gate only after every accepted domain bundle has PASSed", skill)
        self.assertIn("blocks a domain bundle only when the unresolved decision prevents that bundle from being implementation-reconstruction-ready or judgment-ready", generation)
        self.assertIn("Other uncertainty may remain as a labeled gap with source evidence and next action", generation)

    def test_refresh_flow_requires_goal_after_criteria_approval_before_docs_generation(self) -> None:
        text = read_refs(
            "docs-generation-flow.md",
            "source-baseline-and-change-plan.md",
        )
        self.assertIn("Atomic Docs Goal Gate", text)
        self.assertIn("Bootstrap criteria draft creation and the Criteria Structure Review Gate do not require a Codex Goal", text)
        self.assertIn("run criteria-review/revision cycles for that criteria draft", text)
        self.assertIn("then stop for user review after criteria-review PASS", text)
        self.assertIn("After the criteria document is approved and the user accepts a docs write scope, call Codex `create_goal`", text)
        for blocked_work in [
            "project document writing",
            "common or domain atom writing",
            "service logic inventory creation",
            "domain writer or reviewer subagent execution",
            "graph edge writing",
            "source-baseline metadata updates",
        ]:
            self.assertIn(blocked_work, text)
        for objective_part in [
            "approved criteria document path",
            "docs root",
            "accepted docs write scope",
            "natural-language service logic coverage requirement",
            "writer/reviewer cycle",
            "completion condition",
        ]:
            self.assertIn(objective_part, text)
        self.assertIn("If `create_goal` is unavailable or fails, do not start docs generation", text)
        self.assertIn("project documents, common/domain atoms, service logic inventory", text)
        self.assertIn("domain writer/reviewer subagents", text)
        self.assertIn("Complete the Goal only after the accepted docs operation is actually complete", text)
        self.assertIn("waiting for user input, blocked by review FAIL", text)
        self.assertIn("Atomic Docs Goal Gate status", text)

    def test_refresh_flow_uses_source_convention_document_as_separate_scope(self) -> None:
        text = read_refs(
            "docs-generation-flow.md",
            "project-documents-and-inventory.md",
            "source-baseline-and-change-plan.md",
        )
        self.assertIn("Source Convention Document Flow", text)
        self.assertIn("separate write scope for `<doc-root>/project/source-convention.md`", text)
        self.assertIn("not part of the pre-approval criteria bootstrap scope", text)
        self.assertIn("Do not create `project/source-convention.md` during criteria bootstrap", text)
        self.assertIn("only after the criteria document is approved", text)
        self.assertIn("accepted docs write scope includes the source convention document", text)
        self.assertIn("Atomic Docs Goal Gate is satisfied", text)
        self.assertIn("Use it as source interpretation context, not as service behavior evidence", text)
        self.assertIn("separate non-runtime code style from runtime-impacting conventions", text)
        self.assertIn("relevant service logic atom must still record the natural-language behavior and source evidence", text)
        self.assertIn("fail or request correction when a service logic atom mixes in simple code convention", text)
        self.assertIn("move it to `project/source-convention.md`", text)
        self.assertIn("missing from the relevant service logic atom", text)
        self.assertIn("source convention document creation or update at `project/source-convention.md`", text)

    def test_refresh_flow_requires_service_logic_inventory_and_atom_mapping(self) -> None:
        text = read(DOCS_REFS / "project-documents-and-inventory.md")
        self.assertIn("Service Logic Inventory", text)
        self.assertIn("behavior-oriented, not method-oriented", text)
        self.assertIn("meaningful runtime behavior rather than by endpoint, controller, service class, method, or file", text)
        for inventory_field in [
            "inspected source identifiers",
            "natural-language behavior",
            "conditions and branches",
            "validation or permission checks",
            "state transitions",
            "persistence side effects",
            "integration calls",
            "emitted events",
            "error handling",
            "recovery behavior",
            "candidate owning atom key",
            "candidate or assigned AID",
        ]:
            self.assertIn(inventory_field, text)
        self.assertIn("Map every meaningful application, service, and domain logic item to an owning atom", text)
        self.assertIn("record a coverage gap with source evidence and `confirmation_needed`", text)
        self.assertIn("only lists source files, endpoints, controllers, service classes, or method names", text)
        self.assertIn("A service logic inventory that only summarizes source files or behaviors in one line", text)
        self.assertIn("not sufficient input for domain atom drafting, reviewer PASS, Goal completion, or baseline metadata update", text)

    def test_refresh_flow_requires_post_write_consistency_and_source_fact_review(self) -> None:
        text = read(DOCS_REFS / "docs-generation-flow.md")
        self.assertIn("Post-Write Consistency Review Gate", text)
        self.assertIn("after atom files, service logic inventories, graph edges, or partial-scope docs are written", text)
        self.assertIn("before reporting the docs operation as complete", text)
        self.assertIn("Re-read the criteria document, accepted write scope, written atom files", text)
        self.assertIn("approved criteria document still contains pending-approval blockers", text)
        self.assertIn("stale next-step wording for work that has already happened", text)
        self.assertIn("completed Goal/inventory/writer/reviewer work described as future work", text)
        self.assertIn("Partial scope is allowed", text)
        self.assertIn("atomic-docs operation state as the current accepted write scope, not as durable domain approval status", text)
        self.assertIn("accepted partial-scope review target", text)
        self.assertIn("complete project-wide code judgment baseline", text)
        self.assertIn("The gate must also review project documents", text)
        self.assertIn("project documents require or imitate atom-only structure", text)
        self.assertIn("`project-goal.md` contains docs-operation metadata", text)
        self.assertIn("`project-glossary.md` uses one-line-only term definitions", text)
        self.assertIn("retained `project/service-logic-inventory.md` lacks behavior-level fields", text)
        self.assertIn("`project/source-convention.md` records runtime-impacting conventions without related atom_key/AID", text)
        self.assertIn("project documents directly assert code judgment labels without service logic atom evidence", text)
        self.assertIn("Candidate or `needs_confirmation` domain output may remain a provisional review target", text)
        self.assertIn("not project-wide judgment-ready", text)
        self.assertIn("Source Fact Fidelity Gate", text)
        self.assertIn("source path validates, refuses, defaults, falls back, stores, stays read-only, catches, recovers, or can fail", text)
        self.assertIn("Do not update source-baseline metadata, complete the Codex Goal, or present the docs as judgment-ready", text)

    def test_refresh_flow_reviewer_checks_source_fact_assertions_without_overfitting(self) -> None:
        text = read(DOCS_REFS / "docs-generation-flow.md")
        self.assertIn("Do not re-list every source identifier as a substitute for checking facts", text)
        for reviewed_assertion in [
            "validation",
            "refusal",
            "defaulting",
            "fallback",
            "exception behavior",
            "read-only behavior",
            "storage effects",
            "external effects",
        ]:
            self.assertIn(reviewed_assertion, text)
        self.assertIn("source-vs-doc mismatches", text)
        self.assertIn("confusing declarative annotations with actual controller or service guard behavior", text)
        self.assertIn("omitting source-observed null or blank handling", text)
        self.assertIn("omitting optional dependency fallback", text)
        self.assertIn("omitting default value fallback", text)
        self.assertIn("omitting runtime exception possibilities", text)
        self.assertNotIn("eventProductOptionId", text)
        self.assertNotIn("catalog-purchase-preview", text)

    def test_refresh_flow_requires_criteria_change_plan_entries(self) -> None:
        text = read(DOCS_REFS / "source-baseline-and-change-plan.md")
        self.assertIn("limited first write action for draft criteria creation or update", text)
        self.assertIn("whether the criteria document is draft or approved", text)
        self.assertIn("user-conversation criteria that must be recorded in the criteria document", text)
        self.assertIn("source exploration results that update the criteria document", text)
        self.assertIn("project document creation, update, or legacy migration actions", text)
        self.assertIn("`project/project-goal.md`, `project/project-glossary.md`, `project/source-convention.md`, and `project/service-logic-inventory.md` only when the user explicitly retains a final coverage index", text)
        self.assertIn("atomic-docs operation state updates under `.stageflow/atomic-docs/requests/<request-id>/`", text)
        self.assertIn("judgment labels for review findings", text)
        self.assertIn("matches_confirmed_intent", text)
        self.assertIn("unapproved_implemented_behavior", text)
        self.assertIn("out_of_scope_behavior", text)
        self.assertIn("AID assignments for new or changed atom meaning lines", text)
        self.assertIn("explicit AID migrations", text)
        self.assertIn("related AID values for judgment labels, review findings, coverage gaps, and source evidence mappings", text)
        self.assertIn("candidate owning atom key", text)
        self.assertIn("legacy slug-derived fallback migrations", text)
        self.assertIn("`target_key`/`target_path` consistency", text)
        self.assertIn("judgment-ready partial scope or a project-wide judgment-ready baseline", text)

    def test_refresh_flow_rejects_generic_or_absence_based_judgment(self) -> None:
        text = read(DOCS_REFS / "source-baseline-and-change-plan.md")
        self.assertIn("Inferred `Intent` or inferred `Rules` alone cannot create confirmed required behavior", text)
        self.assertIn("use `confirmation_needed`", text)
        self.assertIn("Do not write a generic gap", text)
        self.assertIn("missing required behavior, unapproved implementation, out-of-scope behavior, stale docs", text)
        self.assertIn("Do not classify behavior as healthy only because no related gap exists", text)
        self.assertIn("Source behavior absent from the docs is not implicitly correct", text)
        self.assertIn("coverage gap, `confirmation_needed`, or `docs_stale`", text)

    def test_change_judgment_policy_requires_natural_language_docs_for_matching(self) -> None:
        text = read(DOCS_REFS / "change-judgment-policy.md")
        self.assertIn("natural-language behavior with source evidence", text)
        self.assertIn("source identifier, endpoint list, controller list, service class summary, method name", text)
        self.assertIn("service logic is absent from natural-language docs", text)
        self.assertIn("do not classify it as matching", text)
        self.assertIn("Record a coverage gap or `confirmation_needed`", text)
        self.assertIn("related AID values", text)
        self.assertIn("specific AID lines", text)
        self.assertIn("stable `atom_key`", text)
        self.assertIn("path-only or slug-only references are insufficient", text)
        self.assertIn("`matches_confirmed_intent`, `bug_or_regression`, and `missing_required_behavior`", text)
        self.assertIn("AID-backed natural-language service logic", text)

    def test_docs_skill_prevents_reference_example_leakage(self) -> None:
        combined = "\n".join(
            read(path)
            for path in [
                DOCS_REFS / "atomic-document-contract.md",
                DOCS_REFS / "atomization-criteria-contract.md",
                DOCS_REFS / "source-convention-and-domain-policy.md",
                DOCS_REFS / "service-logic-coverage.md",
                DOCS_REFS / "atom-format-and-judgment.md",
                DOCS_REFS / "refresh-flow.md",
                DOCS_REFS / "criteria-flow.md",
                DOCS_REFS / "docs-generation-flow.md",
                DOCS_REFS / "project-documents-and-inventory.md",
                DOCS_REFS / "source-baseline-and-change-plan.md",
                DOCS_REFS / "change-judgment-policy.md",
            ]
        )
        self.assertNotIn("endpoint-based document structure", combined)
        self.assertNotIn("vague service state-transition split gaps", combined)
        self.assertNotIn("resource deduction", combined)
        self.assertNotIn("this service's detailed state transitions should be split into separate atoms", combined)
        self.assertIn("Do not copy reference example wording", read(DOCS_REFS / "language-policy.md"))

    def test_atomicity_policy_rejects_vague_split_gap(self) -> None:
        text = read(DOCS_REFS / "atom-format-and-judgment.md")
        self.assertIn("Do not write a vague split gap", text)
        for required in [
            "candidate atom keys",
            "tentative paths or slugs",
            "owning domain path",
            "source files/classes/functions or other source identifiers",
            "the split criterion",
            "each candidate atom's behavior/state/rule responsibility",
            "unresolved questions",
        ]:
            self.assertIn(required, text)

    def test_atomic_graph_contract_fields_and_traversal(self) -> None:
        text = read(DOCS_REFS / "atomic-graph.md")
        self.assertIn("graph_edges", text)
        for field in ["type", "target_key", "target_path", "reason"]:
            self.assertIn(field, text)
        self.assertIn("`target_key` is the target atom's stable frontmatter `atom_key`", text)
        self.assertIn("not the atom file slug, category path, domain path, or filename", text)
        self.assertIn("Duplicate `atom_key` values and duplicate graph `target_key` references", text)
        self.assertIn("Do not silently auto-prefix", text)
        self.assertIn("legacy fallback", text)
        self.assertIn("`target_path` is a mutable locator", text)
        self.assertIn("same `atom_key`", text)
        self.assertIn("correct the path", text)
        self.assertIn("controlled vocabulary", text)
        self.assertIn("directional", text)
        self.assertIn("explicit inverse edges only when", text)
        self.assertIn("may only target existing atom files", text)
        self.assertIn("existing target `*-atom.md` file", text)
        self.assertIn("criteria document at `project/atomization-criteria.md` is not an atom file", text)
        self.assertIn("must not be used as a `graph_edges` source or target", text)
        self.assertIn("Do not assign atom line IDs to `graph_edges`", text)
        self.assertIn("AID values belong to judgment-relevant meaning lines", text)
        self.assertIn("Stop when no further modification candidates appear", text)
        self.assertIn("Do not create a root graph output by default", text)
        self.assertIn("not strength or priority fields", text)
        self.assertIn("Do not add relationship strength, priority", text)

    def test_stageflow_integration_contract_respects_gates_and_source_evidence(self) -> None:
        text = read(DOCS_REFS / "stageflow-integration.md")
        self.assertIn("Respect Stageflow definition", text)
        self.assertIn("implementation-plan gate passes", text)
        self.assertIn("Source files are the default evidence source", text)
        self.assertIn("Stageflow artifacts are not the default docs refresh evidence source", text)
        self.assertIn("modify only files inside the configured managed docs root", text)
        self.assertIn("prioritize the current explicit user-requested scope", text)
        self.assertIn("Stageflow plan approval alone is not managed-docs-root approval", text)
        self.assertIn("names the affected docs paths and write actions", text)
        self.assertIn("Gaps", text)
        self.assertIn("Use a Stageflow artifact as required behavior evidence only when", text)
        self.assertIn("approved definition", text)
        self.assertIn("approved implementation plan", text)
        self.assertIn("Draft artifacts, workflow notes, review comments, pending plans", text)
        self.assertIn("not confirmed requirements", text)
        self.assertIn("move the confirmed implemented behavior from `Planned Changes` to `Current Implementation`", text)
        self.assertIn("judgment label from `change-judgment-policy.md`", text)


if __name__ == "__main__":
    unittest.main()
