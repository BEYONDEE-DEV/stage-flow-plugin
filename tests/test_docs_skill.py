from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "atomic-docs" / "SKILL.md"
REFS = ROOT / "skills" / "atomic-docs" / "references"
OPENAI = ROOT / "skills" / "atomic-docs" / "agents" / "openai.yaml"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class AtomicDocsSkillTests(unittest.TestCase):
    def test_first_parent_source_baseline_with_real_git_history(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atomic-docs-history-") as directory:
            root = Path(directory)
            docs_origin = root / "docs-origin"
            project = root / "primary"

            def git(repository: Path, *args: str) -> str:
                return subprocess.run(
                    ["git", "-C", str(repository), *args],
                    text=True,
                    capture_output=True,
                    check=True,
                ).stdout.strip()

            def commit_file(repository: Path, path: str, content: str, message: str) -> str:
                target = repository / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
                git(repository, "add", path)
                git(repository, "commit", "-qm", message)
                return git(repository, "rev-parse", "HEAD")

            def selected_baseline(previous: str, target: str) -> str:
                latest = previous
                commits = git(
                    project,
                    "rev-list",
                    "--first-parent",
                    "--reverse",
                    f"{previous}..{target}",
                ).splitlines()
                for commit in commits:
                    parent = git(project, "rev-parse", f"{commit}^1")
                    changed = git(project, "diff", "--name-only", parent, commit).splitlines()
                    if any(
                        not (path.startswith("docs/") or path == "docs-repository")
                        for path in changed
                    ):
                        latest = commit
                return latest

            git(root, "init", "-q", "-b", "main", str(docs_origin))
            git(docs_origin, "config", "user.email", "docs@example.com")
            git(docs_origin, "config", "user.name", "Docs")
            commit_file(docs_origin, "atomic-docs.json", "{}\n", "docs config")

            git(root, "init", "-q", "-b", "main", str(project))
            git(project, "config", "user.email", "primary@example.com")
            git(project, "config", "user.name", "Primary")
            git(
                project,
                "-c",
                "protocol.file.allow=always",
                "submodule",
                "add",
                "-q",
                str(docs_origin),
                "docs-repository",
            )
            (project / "docs").mkdir()
            (project / "docs" / "atomic-docs.json").write_text("{}\n", encoding="utf-8")
            git(project, "add", ".gitmodules", "docs-repository", "docs/atomic-docs.json")
            git(project, "commit", "-qm", "setup outputs")
            setup = git(project, "rev-parse", "HEAD")

            source = commit_file(project, "src/base.py", "BASE = True\n", "source")
            config_only = commit_file(
                project,
                "docs/atomic-docs.json",
                '{"last_full_source_commit":"source"}\n',
                "config only",
            )
            self.assertEqual(selected_baseline(setup, config_only), source)
            self.assertEqual(selected_baseline(source, config_only), source)

            submodule = project / "docs-repository"
            git(submodule, "config", "user.email", "docs@example.com")
            git(submodule, "config", "user.name", "Docs")
            commit_file(submodule, "note.md", "updated\n", "docs update")
            git(project, "add", "docs-repository")
            git(project, "commit", "-qm", "gitlink only")
            gitlink_only = git(project, "rev-parse", "HEAD")
            self.assertEqual(selected_baseline(source, gitlink_only), source)

            git(project, "switch", "-q", "-c", "side")
            commit_file(project, "src/side.py", "SIDE = True\n", "side source")
            git(project, "switch", "-q", "main")
            commit_file(project, "src/main.py", "MAIN = True\n", "main source")
            git(project, "merge", "-q", "--no-ff", "side", "-m", "merge source branches")
            merge = git(project, "rev-parse", "HEAD")
            trailing_output = commit_file(
                project,
                "docs/atomic-docs.json",
                '{"last_full_source_commit":"merge"}\n',
                "trailing config",
            )
            self.assertEqual(selected_baseline(gitlink_only, trailing_output), merge)

    def test_changed_scope_fixture_observes_seed_one_hop_and_unmapped_boundaries(self) -> None:
        fixture = json.loads(
            (ROOT / "tests" / "fixtures" / "atomic-docs-changed-scope.json").read_text(
                encoding="utf-8"
            )
        )
        changed = set(fixture["changed_files"])
        atoms = fixture["atoms"]
        seeds = {
            atom["atom_key"]
            for atom in atoms
            if changed.intersection(atom["source_files"])
        }
        forward = {
            dependency
            for atom in atoms
            if atom["atom_key"] in seeds
            for dependency in atom["depends_on"]
        }
        reverse = {
            atom["atom_key"]
            for atom in atoms
            if seeds.intersection(atom["depends_on"])
        }
        mapped_files = {
            source
            for atom in atoms
            for source in atom["source_files"]
            if atom["atom_key"] in seeds
        }
        actual = {
            "seed_atoms": sorted(seeds),
            "adjacent_atoms": sorted((forward | reverse) - seeds),
            "unmapped_changed_files": sorted(changed - mapped_files),
            "uninspected_atoms": sorted(
                atom["atom_key"]
                for atom in atoms
                if atom["atom_key"] not in seeds | forward | reverse
            ),
        }
        self.assertEqual(actual, fixture["expected"])

    def test_skill_exposes_only_minimal_permanent_outputs(self) -> None:
        text = read(SKILL)
        for required in (
            "<docs-root>/atomic-docs.json",
            "project/project-goal.md",
            "project/project-glossary.md",
            "<docs-root>/<domain>/*-atom.md",
            "Do not create any other permanent Atomic Docs output",
            "does not create a Goal",
        ):
            self.assertIn(required, text)
        permanent_outputs = text.split("## Permanent Outputs", 1)[1].split("## Core Contract", 1)[0]
        self.assertNotIn(".stageflow/atomic-docs.json", permanent_outputs)

    def test_config_lives_with_docs_and_discovery_is_fail_closed(self) -> None:
        skill = read(SKILL)
        config = read(REFS / "docs-root-and-config.md")
        validation = read(REFS / "validation-contract.md")
        usage = read(ROOT / "USAGE.ko.md")

        for required in (
            "locate exactly one `atomic-docs.json`",
            "An explicit config path does not permit a second candidate",
            "One docs root belongs to one primary project",
            "validation and updates still run from the primary project",
        ):
            self.assertIn(required, skill)
        for required in (
            "`<docs-root>/atomic-docs.json`",
            "Its resolved directory must be the config file's parent",
            "Exactly one regular-file candidate is required",
            "does not permit another candidate elsewhere",
            "retired `.stageflow/atomic-docs.json` location",
            "opening the docs repository does not make standalone validation or update supported",
        ):
            self.assertIn(required, config)
        for required in (
            "--config <docs-root>/atomic-docs.json",
            "Before parsing JSON",
            "Exactly one regular-file candidate must exist even when `--config` is supplied",
            "parent equal to resolved `docs_root`",
        ):
            self.assertIn(required, validation)
        self.assertIn("<docs-root>/atomic-docs.json", usage)
        self.assertIn("Submodule 방식에서는 config가 문서 저장소에 함께 보이지만", usage)

    def test_atom_contract_is_exact(self) -> None:
        text = read(REFS / "atomic-document-contract.md")
        for required in (
            "atom_key",
            "depends_on",
            "`Purpose`",
            "`Boundaries`",
            "`Contracts`",
            "`Implementation`",
            "`Sources`",
            "`Changes`",
            "`Open Questions`",
            "`- 없음`",
            "[RID:<atom_key>.<lower-kebab-slug>]",
            "There is no RID reference token",
        ):
            self.assertIn(required, text)
        for legacy in ("Intent", "Outcomes", "Current Implementation", "Planned Changes", "Gaps"):
            self.assertNotIn(f"`{legacy}`", text)

    def test_glossary_contract_is_a_general_project_dictionary(self) -> None:
        skill = read(SKILL)
        contract = read(REFS / "atomic-document-contract.md")
        validation = read(REFS / "validation-contract.md")
        for required in (
            "general project glossary",
            "a new developer must understand",
            "even when a term belongs to only one Atom",
            "Use only `Term` and `Definition`",
            "without adding ownership, source, evidence, or control columns",
            "do not invent artificial terms",
        ):
            self.assertIn(required, skill)
        for required in (
            "This is a general project glossary",
            "| Term | Definition |",
            "Terms owned by one Atom still qualify",
            "user roles and actors",
            "core domain entities",
            "business actions, workflows, states, and results",
            "project-specific identifiers, acronyms, aliases",
            "a concise, non-circular explanation",
            "do not invent artificial names",
            "Do not put source locators, ownership metadata, source-of-truth claims, or review evidence",
        ):
            self.assertIn(required, contract)
        glossary_section = contract.split("## Project Glossary", 1)[1].split("## Atom", 1)[0]
        for retired_column in (
            "| Term | Meaning | Scope Or Owner |",
            "`Scope Or Owner`",
            "`Source Of Truth`",
            "`Do Not Confuse With`",
        ):
            self.assertNotIn(retired_column, glossary_section)
        self.assertNotIn("At least two Atom responsibilities", glossary_section)
        self.assertIn("unique non-empty `Term` and `Definition` cells", validation)
        self.assertIn("glossary coverage or definition accuracy", validation)

    def test_writer_and_reviewer_share_minimal_decision_contract(self) -> None:
        skill = read(SKILL)
        contract = read(REFS / "atomic-document-contract.md")
        flow = read(REFS / "refresh-flow.md")
        reviewer = read(REFS / "reviewer-perspectives.md")
        skill_flat = " ".join(skill.split())
        contract_flat = " ".join(contract.split())
        flow_flat = " ".join(flow.split())
        reviewer_flat = " ".join(reviewer.split())

        for required in (
            "project-level outcomes observable by the intended human or system consumers",
            "natural owning Atom",
            "must survive an implementation change",
            "domain-specific result or additional condition",
            "Do not create a shared Atom solely to deduplicate mechanics",
        ):
            self.assertIn(required, skill_flat)

        for required in (
            "project-level outcomes observable by the intended human or system consumers",
            "Do not assume every project has a human UI",
            "must survive a change of implementation",
            "natural Atom that owns the rule",
            "domain-specific consequence or additional condition",
            "Classify content by meaning, not vocabulary",
            "put it in `Implementation` or omit it",
        ):
            self.assertIn(required, contract_flat)

        for required in (
            "selected and directly inspected scope",
            "instead of expanding automatically",
            "project-level observable outcomes",
            "natural Atom owner without inventing a shared hub",
            "Separate contracts that must survive implementation changes",
            "Remove copied generic mechanics",
        ):
            self.assertIn(required, flow_flat)

        for required in (
            "Return `FAIL` when a material project `Success` statement",
            "generic rule with a natural owning Atom is materially copied",
            "`Contracts` contains current mechanics",
            "Do not require an artificial shared Atom",
            "domain-specific consequence or additional condition",
            "reject an item merely because it mentions a route",
            "whether another consumer can observe or rely on it",
        ):
            self.assertIn(required, reviewer_flat)

    def test_config_is_exact_v2_without_baseline_artifact(self) -> None:
        text = read(REFS / "docs-root-and-config.md")
        for required in (
            '"version": 2',
            '"storage_mode"',
            '"docs_root"',
            '"source_root"',
            '"language"',
            '"last_full_source_commit": null',
            '"auxiliary_sources"',
            "All seven top-level keys are required",
            "Do not add a separate baseline file",
            "below the Git top level",
        ):
            self.assertIn(required, text)

    def test_operations_are_small_and_changed_scope_is_one_hop(self) -> None:
        skill = read(SKILL)
        flow = read(REFS / "refresh-flow.md")
        for required in (
            "`inspect`",
            "`update all`",
            "`update changed`",
            "`update targeted`",
            "direct `depends_on`",
            "direct reverse dependents",
            "Never claim complete transitive closure",
        ):
            self.assertIn(required, skill)
        for required in (
            "seed Atoms",
            "direct dependency and reverse-dependent Atom keys",
            "boundaries not inspected",
            "not proof of complete closure",
        ):
            self.assertIn(required, flow)

    def test_successful_changed_update_advances_existing_commit_key(self) -> None:
        skill = read(SKILL)
        config = read(REFS / "docs-root-and-config.md")
        flow = read(REFS / "refresh-flow.md")
        usage = read(ROOT / "USAGE.ko.md")

        for required in (
            "advance that same commit key to the latest first-parent source-impact commit",
            "Preserve the previous `last_full_source_commit`",
            "Set `last_full_source_commit` to the latest first-parent source-impact commit even when the successful source-impact result required no docs edit",
            "restore the previous commit value",
        ):
            self.assertIn(required, skill)
        for required in (
            "latest reconciled source-impact commit on the primary HEAD's first-parent history",
            "Do not add a separate baseline file, primary-project pointer, copied config, or incremental-cursor file",
            "A reviewed conclusion that no managed-doc edit is needed is still a successful changed update",
        ):
            self.assertIn(required, config)
        for required in (
            "capture target primary `HEAD`",
            "including for a successful no-doc result",
            "Restore the previous commit value",
        ):
            self.assertIn(required, flow)
        self.assertIn("다음 실행은 그 이후 source 변경만 확인합니다", usage)
        self.assertNotIn("last_processed_source_commit", skill + config + flow)

    def test_changed_update_distinguishes_source_impact_from_own_outputs(self) -> None:
        skill = read(SKILL)
        config = read(REFS / "docs-root-and-config.md")
        flow = read(REFS / "refresh-flow.md")
        reviewer = read(REFS / "reviewer-perspectives.md")

        for required in (
            "`<docs-root>/atomic-docs.json`",
            "config-only changes",
            "configured documentation-submodule gitlink",
            "If any config field other than `last_full_source_commit` changed",
            "If no first-parent source-impact commit remains",
            "include its changed docs in bounded semantic reconciliation instead of guessing who wrote them",
            "A pre-existing dirty value or document is not an approved write-set exception",
        ):
            self.assertIn(required, skill)
        for required in (
            "repository-mode config diff is baseline-only when `last_full_source_commit` is the only changed field",
            "Any other config field change stops changed processing",
            "containing documentation-submodule gitlink",
            "retain the previous baseline",
            "without inferring authorship or acceptance",
        ):
            self.assertIn(required, config)
        for required in (
            "When only Atomic Docs config/docs/gitlink output remains",
            "Every changed primary-source file must receive a reliable source-impact classification",
            "material changed file cannot be classified reliably",
            "Pre-existing dirty state stops the update",
        ):
            self.assertIn(required, flow)
        self.assertIn("source-impact no-doc result", reviewer)
        self.assertIn("the reason no managed-doc edit is needed", reviewer)
        self.assertIn("old-to-new documentation-submodule commit diff", reviewer)
        self.assertNotIn("known accepted", skill + config + flow)

        start_clean = skill.index("Before writing, separately require")
        source_diff = skill.index("Walk the target's first-parent history")
        baseline_write = skill.index("Set `last_full_source_commit` to the latest first-parent source-impact commit")
        final_validation = skill.index("Then validate the final config and docs state", baseline_write)
        self.assertLess(start_clean, source_diff)
        self.assertLess(source_diff, baseline_write)
        self.assertLess(baseline_write, final_validation)

    def test_source_baseline_uses_first_parent_and_ignores_trailing_outputs(self) -> None:
        skill = read(SKILL)
        config = read(REFS / "docs-root-and-config.md")
        flow = read(REFS / "refresh-flow.md")
        usage = read(ROOT / "USAGE.ko.md")

        for required in (
            "not on the target's first-parent history",
            "compare each commit with its first parent",
            "A merge is source-impact when it changes a non-output path compared with its first parent",
            "Do not advance it to trailing config/docs/gitlink-only commits",
        ):
            self.assertIn(required, skill)
        for required in (
            "Walk its first-parent history",
            "compare each commit with its first parent",
            "including source brought in from the merged branch",
            "trailing output-only commits do not advance it",
        ):
            self.assertIn(required, config)
        for required in (
            "A merge that differs from its first parent on a non-output path is source-impact",
            "Select the latest first-parent commit",
            "Never advance it to trailing config/docs/gitlink-only commits",
        ):
            self.assertIn(required, flow)
        self.assertIn("first-parent 이력에서 마지막 source-impact commit", usage)

    def test_single_bounded_reviewer_has_one_correction(self) -> None:
        text = read(REFS / "reviewer-perspectives.md")
        for required in (
            "one independent semantic reviewer",
            "complete managed-docs diff",
            "development",
            "faithful",
            "`Boundaries`",
            "`depends_on`",
            "corrects the findings once",
            "same reviewer",
            "stop and ask the user",
            "Run structural validation on the corrected docs",
            "final reviewed docs",
        ):
            self.assertIn(required, text)
        self.assertIn("Do not add another reviewer, audit, challenge", text)
        self.assertIn("Do not persist review metadata or state", text)
        for required in (
            "project goal and the selected Atom/source scope",
            "needed by a new developer is omitted",
            "circular, vague, source-symbol-only",
            "artificial terms are invented",
            "does not need cross-Atom use",
            "contains only `Term` and `Definition`",
        ):
            self.assertIn(required, text)

    def test_existing_delete_or_merge_needs_exact_key_approval(self) -> None:
        text = read(SKILL) + read(REFS / "refresh-flow.md")
        self.assertIn("exact source and target `atom_key` list", text)
        self.assertIn("explicit user approval", text)
        self.assertIn("Use Git for recovery", text)
        self.assertIn("create no separate recovery artifact", text)

    def test_reference_surface_is_exactly_seven_files(self) -> None:
        expected = {
            "atomic-document-contract.md",
            "docs-root-and-config.md",
            "language-policy.md",
            "refresh-flow.md",
            "reviewer-perspectives.md",
            "stageflow-integration.md",
            "validation-contract.md",
        }
        self.assertEqual({path.name for path in REFS.glob("*.md")}, expected)

    def test_retired_control_vocabulary_is_not_an_active_contract(self) -> None:
        text = "\n".join(read(path) for path in [SKILL, *sorted(REFS.glob("*.md"))])
        for retired in (
            "context_selection.version",
            "acceptance fingerprint",
            "basis revision",
            "semantic closure",
            "persistent reviewer",
            "blind terminal challenger",
            "operation-events.jsonl",
            "source-baseline.json",
            "[AID-REF:",
        ):
            self.assertNotIn(retired, text)

    def test_metadata_and_manifest_describe_new_commands(self) -> None:
        metadata = read(OPENAI)
        manifest = json.loads(read(ROOT / ".codex-plugin" / "plugin.json"))
        self.assertIn('display_name: "Atomic Docs"', metadata)
        self.assertIn("inspect or update purpose, boundaries, contracts", metadata)
        prompts = manifest["interface"]["defaultPrompt"]
        self.assertIn("Use atomic-docs update all to create source-guided project documentation.", prompts)
        self.assertIn("Use atomic-docs update changed to refresh affected Atom files.", prompts)
        usage = read(ROOT / "USAGE.ko.md")
        self.assertIn("별도 request/work/review operation 디렉터리를 만들지 않습니다", usage)


if __name__ == "__main__":
    unittest.main()
