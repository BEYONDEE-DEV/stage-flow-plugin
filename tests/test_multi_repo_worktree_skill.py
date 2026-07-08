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
        self.assertIn("setup, status, worktree creation, merge-back, or sync-derived", text)
        self.assertIn("references/worktree-operations.md", text)
        self.assertIn("scripts/inspect_worktrees.py", text)
        self.assertNotIn("TODO", text)

    def test_skill_records_source_and_derived_branch_safety_rules(self) -> None:
        text = read(SKILL)

        self.assertIn("creation/source branches", text)
        self.assertIn("derived branches", text)
        self.assertIn("Before any write operation", text)
        self.assertIn("repository list, source branch, derived branch, upstream, dirty state", text)
        self.assertIn("Do not run destructive commands", text)
        self.assertIn("Prefer merge", text)
        self.assertIn("explicit approval", text)

    def test_reference_covers_required_operations(self) -> None:
        text = read(REFERENCE)

        for phrase in [
            "## Setup",
            "## Current State",
            "## Worktree Creation",
            "## Merge Back To Source",
            "## Sync Source Changes Into Derived Branches",
            "source branch",
            "derived branch",
            "same branch name appears in several repositories",
            "Ask before any command that writes Git state",
            "Stop when source and derived branch relationship is unclear",
        ]:
            self.assertIn(phrase, text)

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

    def test_openai_metadata_is_explicit_only(self) -> None:
        text = read(OPENAI_YAML)

        self.assertIn('display_name: "Multi Repo Worktree"', text)
        self.assertIn('short_description: "Multi-repo worktree coordination."', text)
        self.assertIn("Use $multi-repo-worktree", text)
        self.assertIn("allow_implicit_invocation: false", text)

    def test_plugin_manifest_exposes_multi_repo_worktree_prompt(self) -> None:
        manifest = json.loads(read(PLUGIN_JSON))
        interface = manifest["interface"]

        self.assertIn("multi-repo-worktree", interface["longDescription"])
        self.assertIn(
            "Use multi-repo-worktree to inspect and coordinate a multi-repo Git worktree bundle.",
            interface["defaultPrompt"],
        )


if __name__ == "__main__":
    unittest.main()
