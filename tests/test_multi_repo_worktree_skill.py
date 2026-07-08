from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills" / "multi-repo-worktree"
SKILL = SKILL_DIR / "SKILL.md"
REFERENCE = SKILL_DIR / "references" / "worktree-operations.md"
INSPECTOR = SKILL_DIR / "scripts" / "inspect_worktrees.py"
OPENAI_YAML = SKILL_DIR / "agents" / "openai.yaml"
PLUGIN_JSON = ROOT / ".codex-plugin" / "plugin.json"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class MultiRepoWorktreeSkillTests(unittest.TestCase):
    def test_skill_declares_explicit_only_multi_repo_scope(self) -> None:
        text = read(SKILL)

        self.assertIn("name: multi-repo-worktree", text)
        self.assertIn("Use only when the user explicitly invokes", text)
        self.assertIn("Do not apply it implicitly", text)
        self.assertIn("ordinary Git, single-repo, or single-worktree questions", text)
        self.assertIn("multiple independent Git repositories", text)
        self.assertIn("help, status, create, merge, and sync", text)
        self.assertIn("$multi-repo-worktree <keyword> [free-form intent]", text)
        self.assertIn("references/worktree-operations.md", text)
        self.assertIn("scripts/inspect_worktrees.py", text)
        self.assertNotIn("**Setup**", text)
        self.assertNotIn("merge-back", text)
        self.assertNotIn("sync-derived", text)
        self.assertNotIn("TODO", text)

    def test_skill_records_source_and_derived_branch_safety_rules(self) -> None:
        text = read(SKILL)

        self.assertIn("creation/source branches", text)
        self.assertIn("derived branches", text)
        self.assertIn("Before any write operation", text)
        self.assertIn("Never execute `create`, `merge`, or `sync` commands before explaining", text)
        self.assertIn("repository list, source branch, derived branch, upstream, dirty state", text)
        self.assertIn("Do not run destructive commands", text)
        self.assertIn("Prefer merge", text)
        self.assertIn("explicit approval", text)

    def test_reference_covers_required_operations(self) -> None:
        text = read(REFERENCE)

        for phrase in [
            "## Keyword Contract",
            "## Status",
            "## Create",
            "## Merge",
            "## Sync",
            "`help`",
            "`status`",
            "`create`",
            "`merge`",
            "`sync`",
            "Do not expose `setup`, `merge-back`, or `sync-derived`",
            "Explain the exact repo list, branch mapping, command order, and risks",
            "Ask for explicit approval",
            "source branch",
            "derived branch",
            "same branch name appears in several repositories",
            "Ask before any command that writes Git state",
            "Stop when source and derived branch relationship is unclear",
        ]:
            self.assertIn(phrase, text)

    def test_status_output_policy_uses_single_line_repo_summary(self) -> None:
        skill = read(SKILL)
        reference = read(REFERENCE)

        for text in [skill, reference]:
            self.assertIn("기준 폴더", text)
            self.assertIn("현재 브랜치", text)
            self.assertIn("변경상태", text)
            self.assertIn("dirty", text)
            self.assertIn("clean", text)

        self.assertIn("User-facing status output must not use Markdown tables", skill)
        self.assertIn("원본 브랜치: feature-etc (추정)", skill)
        self.assertIn("majoong_events_api: 폴더 majoong_events_api / 현재 브랜치 feature-etc-docs / 변경상태 dirty", skill)
        self.assertIn("User-facing `status` output must avoid Markdown tables", reference)
        self.assertIn("<source-branch (추정)|확인 필요>", reference)
        self.assertIn("<repo>: 폴더 <relative-folder> / 현재 브랜치 <branch> / 변경상태 <dirty|clean>", reference)
        self.assertIn("Show each repo on one line", reference)
        self.assertIn("Show `폴더` as the path relative to `기준 폴더`", reference)
        self.assertIn("Do not print extra workspace path or repository-count headers", reference)
        self.assertIn("append `(추정)`", reference)
        self.assertIn("Do not put `upstream`, `HEAD`, or risk notes into the primary repo line", reference)

    def test_inspector_is_read_only_and_avoids_mutating_git_commands(self) -> None:
        text = read(INSPECTOR)

        forbidden = [
            '"add"',
            '"merge"',
            '"rebase"',
            '"push"',
            '"pull"',
            '"fetch"',
            '"reset"',
            '"switch"',
            '"checkout"',
            '"branch", "-D"',
        ]
        for token in forbidden:
            self.assertNotIn(token, text)

        self.assertIn('"worktree", "list", "--porcelain"', text)
        self.assertIn('"status", "--porcelain"', text)
        self.assertIn('"rev-parse", "--show-toplevel"', text)
        self.assertIn('"GIT_OPTIONAL_LOCKS"] = "0"', text)
        self.assertIn('"git", "--no-optional-locks"', text)
        self.assertNotIn("repo별 다름", text)

    @unittest.skipIf(shutil.which("git") is None, "git is required for inspector smoke test")
    def test_inspector_reports_git_repo_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "service-a"
            repo.mkdir()
            subprocess.run(["git", "init"], cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            result = subprocess.run(
                [sys.executable, str(INSPECTOR), "--root", str(root), "--max-depth", "2", "--json"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            data = json.loads(result.stdout)

            self.assertEqual(data["repository_group_count"], 1)
            self.assertGreaterEqual(data["worktree_count"], 1)
            self.assertEqual(data["groups"][0]["worktrees"][0]["dirty"], "clean")

    @unittest.skipIf(shutil.which("git") is None, "git is required for inspector smoke test")
    def test_inspector_default_output_uses_bundle_and_single_line_repos(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "service-a"
            repo.mkdir()
            subprocess.run(["git", "init"], cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)
            subprocess.run(["git", "checkout", "-b", "feature-etc"], cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (repo / "README.md").write_text("hello\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            bundle_repo = root / "worktrees" / "feature-etc-docs" / "service-a"
            subprocess.run(
                ["git", "worktree", "add", "-b", "feature-etc-docs", str(bundle_repo), "feature-etc"],
                cwd=repo,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            result = subprocess.run(
                [sys.executable, str(INSPECTOR), "--root", str(root), "--max-depth", "4"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            output = result.stdout

            self.assertIn("대상 묶음: worktrees/feature-etc-docs", output)
            self.assertIn("원본 브랜치: feature-etc (추정)", output)
            self.assertIn(f"기준 폴더: {bundle_repo.parent}", output)
            self.assertIn(
                "service-a: 폴더 service-a / 현재 브랜치 feature-etc-docs / 변경상태 clean",
                output,
            )
            self.assertNotIn("| Worktree Path |", output)
            self.assertNotIn("| --- |", output)
            self.assertNotIn("Upstream", output)
            self.assertNotIn("Workspace:", output)
            self.assertNotIn("Repository groups:", output)
            self.assertNotIn("Worktrees:", output)

            bundle_result = subprocess.run(
                [sys.executable, str(INSPECTOR), "--root", str(bundle_repo.parent), "--max-depth", "2"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            bundle_output = bundle_result.stdout

            self.assertIn("대상 묶음: worktrees/feature-etc-docs", bundle_output)
            self.assertIn("원본 브랜치: 확인 필요", bundle_output)
            self.assertIn(f"기준 폴더: {bundle_repo.parent}", bundle_output)
            self.assertIn(
                "service-a: 폴더 service-a / 현재 브랜치 feature-etc-docs / 변경상태 clean",
                bundle_output,
            )
            self.assertNotIn("outside workspace", bundle_output)
            self.assertNotIn("폴더 /", bundle_output)
            self.assertNotIn("Workspace:", bundle_output)

    @unittest.skipIf(shutil.which("git") is None, "git is required for inspector smoke test")
    def test_inspector_requires_confirmation_when_any_bundle_source_is_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            root = parent / "workspace"
            root.mkdir()

            repo_a = root / "service-a"
            repo_a.mkdir()
            subprocess.run(["git", "init"], cwd=repo_a, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_a, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_a, check=True)
            subprocess.run(["git", "checkout", "-b", "feature-base"], cwd=repo_a, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (repo_a / "README.md").write_text("hello\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=repo_a, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=repo_a, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                [
                    "git",
                    "worktree",
                    "add",
                    "-b",
                    "feature-docs",
                    str(root / "worktrees" / "feature-docs" / "service-a"),
                    "feature-base",
                ],
                cwd=repo_a,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            repo_b = parent / "external-service-b"
            repo_b.mkdir()
            subprocess.run(["git", "init"], cwd=repo_b, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_b, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_b, check=True)
            subprocess.run(["git", "checkout", "-b", "other-base"], cwd=repo_b, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (repo_b / "README.md").write_text("hello\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=repo_b, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=repo_b, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                [
                    "git",
                    "worktree",
                    "add",
                    "-b",
                    "feature-docs-b",
                    str(root / "worktrees" / "feature-docs" / "service-b"),
                    "other-base",
                ],
                cwd=repo_b,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            result = subprocess.run(
                [sys.executable, str(INSPECTOR), "--root", str(root), "--max-depth", "4"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            output = result.stdout
            bundle_section = output.split("대상 묶음: worktrees/feature-docs", maxsplit=1)[1]
            bundle_section = bundle_section.split("\n\n대상 묶음:", maxsplit=1)[0]

            self.assertIn("원본 브랜치: 확인 필요", bundle_section)
            self.assertIn("service-a: 폴더 service-a / 현재 브랜치 feature-docs / 변경상태 clean", bundle_section)
            self.assertIn("service-b: 폴더 service-b / 현재 브랜치 feature-docs-b / 변경상태 clean", bundle_section)
            self.assertNotIn("원본 브랜치: feature-base (추정)", bundle_section)

    @unittest.skipIf(shutil.which("git") is None, "git is required for inspector smoke test")
    def test_inspector_requires_confirmation_for_ambiguous_workspace_siblings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "service-a"
            repo.mkdir()
            subprocess.run(["git", "init"], cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)
            subprocess.run(["git", "checkout", "-b", "feature-base"], cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (repo / "README.md").write_text("hello\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                ["git", "worktree", "add", "-b", "other-base", str(root / "service-a-alt"), "feature-base"],
                cwd=repo,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            subprocess.run(
                [
                    "git",
                    "worktree",
                    "add",
                    "-b",
                    "feature-docs",
                    str(root / "worktrees" / "feature-docs" / "service-a"),
                    "feature-base",
                ],
                cwd=repo,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            result = subprocess.run(
                [sys.executable, str(INSPECTOR), "--root", str(root), "--max-depth", "4"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            output = result.stdout
            bundle_section = output.split("대상 묶음: worktrees/feature-docs", maxsplit=1)[1]
            bundle_section = bundle_section.split("\n\n대상 묶음:", maxsplit=1)[0]

            self.assertIn("원본 브랜치: 확인 필요", bundle_section)
            self.assertNotIn("원본 브랜치: feature-base (추정)", bundle_section)
            self.assertNotIn("원본 브랜치: other-base (추정)", bundle_section)

    def test_openai_metadata_is_explicit_only(self) -> None:
        text = read(OPENAI_YAML)

        self.assertIn('display_name: "Multi Repo Worktree"', text)
        self.assertIn('short_description: "Multi-repo worktree coordination."', text)
        self.assertIn("Use $multi-repo-worktree status", text)
        self.assertIn("allow_implicit_invocation: false", text)

    def test_plugin_manifest_exposes_multi_repo_worktree_prompt(self) -> None:
        manifest = json.loads(read(PLUGIN_JSON))
        interface = manifest["interface"]

        self.assertIn("multi-repo-worktree", interface["longDescription"])
        self.assertIn("help, status, create, merge, and sync keywords", interface["longDescription"])
        self.assertIn(
            "Use multi-repo-worktree status to inspect a multi-repo Git worktree bundle.",
            interface["defaultPrompt"],
        )


if __name__ == "__main__":
    unittest.main()
