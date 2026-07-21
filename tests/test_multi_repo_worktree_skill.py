from __future__ import annotations

import ast
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills" / "multi-repo-worktree"
SKILL = SKILL_DIR / "SKILL.md"
REFERENCE = SKILL_DIR / "references" / "worktree-operations.md"
INSPECTOR = SKILL_DIR / "scripts" / "inspect_worktrees.py"
SLOT_MANIFEST = SKILL_DIR / "scripts" / "slot_manifest.py"
OPENAI_YAML = SKILL_DIR / "agents" / "openai.yaml"
PLUGIN_JSON = ROOT / ".codex-plugin" / "plugin.json"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class MultiRepoWorktreeSkillTests(unittest.TestCase):
    def test_skill_declares_explicit_only_multi_repo_scope(self) -> None:
        text = read(SKILL)

        self.assertIn("name: multi-repo-worktree", text)
        self.assertIn("Use only when the user explicitly invokes", text)
        self.assertIn("Do not use for ordinary Git, single-repo, or single-worktree requests", text)
        self.assertIn("multiple independent Git repositories", text)
        for keyword in ["`help`", "`status`", "`create`", "`submit`", "`pull`", "`sync`"]:
            self.assertIn(keyword, text)
        self.assertIn("$stageflow:multi-repo-worktree <keyword> [free-form intent]", text)
        self.assertIn("[$stageflow:multi-repo-worktree](...)", text)
        self.assertIn("references/worktree-operations.md", text)
        self.assertIn("scripts/inspect_worktrees.py", text)
        self.assertIn('python3 "<skill-dir>/scripts/inspect_worktrees.py"', text)
        self.assertIn("do not assume the current working directory is the plugin root", text)
        self.assertNotIn("**Setup**", text)
        self.assertNotIn("TODO", text)

    def test_skill_uses_intent_authorization_and_narrow_decision_gates(self) -> None:
        text = read(SKILL)

        self.assertIn("## Decision Contract", text)
        self.assertIn("fixed task branch", text)
        self.assertIn("explicit request to execute `create`, `submit`, `pull`, or `sync`", text)
        self.assertIn("inspection only, or dry-run is always read-only", text)
        self.assertIn("concise non-blocking commentary summary", text)
        self.assertIn("Do not ask the user to approve exact commands", text)
        self.assertIn("Ask one consolidated question only", text)
        self.assertIn("Persist repo-specific source branches and remotes at `create`", text)
        self.assertIn("Never write using inferred or ambiguous context", text)
        self.assertIn("Never reset, clean, force checkout, force push, rewrite history", text)
        self.assertIn("`sync` runs only in development worktrees", text)
        self.assertIn("missing/ambiguous remotes", text)
        for obsolete in [
            "Accept approval only after presenting that exact plan",
            "Approval applies only to the displayed batch",
            "Receive explicit approval after the exact plan",
            "approved-path Korean commits",
        ]:
            self.assertNotIn(obsolete, text)

    def test_reference_covers_required_operations(self) -> None:
        text = read(REFERENCE)

        for phrase in [
            "## Keyword Authorization And Decision Contract",
            "## Roles And Repeated-PR Flow",
            "## Permanent Slot Manifest",
            "## Read-Only Inspection And Status",
            "## Create",
            "## Submit Common Phase",
            "## Submit NONE And OPEN",
            "## Submit MERGED",
            "## Retry And Partial Results",
            "## Pull",
            "## Sync",
            "`help`",
            "`status`",
            "`create`",
            "`pull`",
            "`sync`",
            "Preflight the complete batch and classify every changed repo",
            "Do not turn the summary into an approval question",
            "Ask one consolidated question only",
            "inspection only, or dry-run remains read-only",
            "source branch",
            "development worktree",
            "Git does not retain a branch's creation parent",
            "merge --ff-only",
        ]:
            self.assertIn(phrase, text)

        for removed_heading in ["## Recycle", "## Integrate", "## Merge"]:
            self.assertNotIn(removed_heading, text)
        for obsolete in [
            "Receive explicit approval after the exact plan",
            "approved-Korean-commit-message",
            "approved-Korean-title",
            "Any drift requires a new plan and approval",
        ]:
            self.assertNotIn(obsolete, text)

    def test_permanent_pr_slot_workflow_has_explicit_roles_and_safety_gates(self) -> None:
        skill = read(SKILL)
        reference = read(REFERENCE)

        for phrase in [
            ".stageflow-worktrees/slots.json",
            "There is no `active`/`released` state",
            "create once -> develop -> submit -> user merges on GitHub",
            "Never enable auto-merge or run a remote PR merge command",
            "`pull` runs only in confirmed original/source worktrees",
            "`sync` runs only in development worktrees",
            "recovery-required",
            "never claim rollback",
        ]:
            self.assertIn(phrase, skill)

        for phrase in [
            "user merges PR 1 on GitHub",
            "Development user",
            "Original user",
            "GitHub user",
            "Generation `0` requires `pr: null`",
            "An exact repeated call is idempotent",
            "operation lock is separate from slot ownership",
            "same slot, worktrees, and task branches",
            '"schema_version": 3',
            '"source_branch": "feature-etc"',
            '"remote": "origin"',
            "selected legacy slot",
            "status`, inspection, and dry-run must leave manifest bytes unchanged",
        ]:
            self.assertIn(phrase, reference)

        for removed in [
            "stageflow-submitted-sha",
            "inspect_pr_submission.py",
            "gh pr merge",
            "--match-head-commit",
        ]:
            self.assertNotIn(removed, skill)
            self.assertNotIn(removed, reference)

        self.assertNotIn("scripts/inspect_pr_submission.py", skill)

    def test_submit_commits_in_korean_and_supports_chained_ready_prs(self) -> None:
        skill = read(SKILL)
        reference = read(REFERENCE)

        for phrase in [
            "Inspect staged, unstaged, and non-ignored untracked paths",
            "generated Korean commit message",
            'add -A --',
            'commit -m "<generated-Korean-commit-message>"',
            "Complete the local commit phase for every repo before the first remote write",
            "Do not pass `--draft`",
            "Do not advance generation or create another PR",
            "Only after every repo passes may one `record-batch` atomically advance",
            "Files changed",
            "Old commits from an earlier squash merge may remain",
            "Adopt only one ready OPEN result",
        ]:
            self.assertIn(phrase, reference)

        self.assertIn("task-related-path Korean commits", skill)
        self.assertIn("same-branch push", skill)
        self.assertIn("Korean ready PR creation or update", skill)
        self.assertIn("`OPEN` pushes to the same PR", skill)
        self.assertIn("`MERGED` fetches and pins the base", skill)
        self.assertIn("Never enable auto-merge or run a remote PR merge command", skill)
        self.assertIn("without rewriting its title/body", skill)
        self.assertIn("Never run `gh pr edit` during routine `submit`", reference)
        self.assertNotIn('git -C "<development-worktree>" add .', reference)

    def test_create_is_one_time_idempotent_initialization(self) -> None:
        skill = read(SKILL)
        reference = read(REFERENCE)

        self.assertIn("first initialization and exact idempotent retry", skill)
        self.assertIn("Never use it to start later work", skill)
        self.assertIn("Initialize the complete permanent manifest binding", skill)
        self.assertIn("Use `create` only for the first fixed bundle initialization", reference)
        self.assertIn("initialize --slot", reference)
        self.assertIn("worktree add -b", reference)
        self.assertIn("An exact retry may leave already-correct clean worktrees untouched", reference)
        self.assertIn("Never switch an existing slot to a new task branch", reference)
        self.assertNotIn("--preserve-repositories", reference)

    def test_pull_and_sync_have_separate_locations_and_update_rules(self) -> None:
        skill = read(SKILL)
        reference = read(REFERENCE)

        self.assertIn("`pull` runs only in confirmed original/source worktrees", skill)
        self.assertIn("fast-forward each source branch to its pinned SHA", skill)
        self.assertIn("Run only in the requested development worktree bundle", skill)
        self.assertIn("never switch or update an original worktree", skill)
        self.assertEqual(skill.count("refs/remotes/<remote>/<source-branch>"), 2)
        self.assertNotIn("`origin/<source>`", skill)
        self.assertIn("merge --ff-only \"<pinned-source-sha>\"", reference)
        self.assertIn("merge \"<pinned-source-sha>\"", reference)
        self.assertIn("Do not use plain `git pull`", reference)
        self.assertIn("The original worktree may remain intentionally stale", reference)
        self.assertIn("`sync` does not invoke `pull`", reference)

    def test_status_output_policy_uses_single_line_repo_summary(self) -> None:
        skill = read(SKILL)
        reference = read(REFERENCE)

        for text in [skill, reference]:
            self.assertIn("기준 폴더", text)
            self.assertIn("현재 브랜치", text)
            self.assertIn("변경상태", text)
            self.assertIn("dirty", text)
            self.assertIn("clean", text)

        self.assertIn("Do not use a Markdown table", skill)
        self.assertIn("원본 브랜치: feature-etc (추정)", skill)
        self.assertIn("majoong_events_api: 폴더 majoong_events_api / 현재 브랜치 feature-etc-docs / 변경상태 dirty", skill)
        self.assertIn("Do not use a Markdown table", reference)
        self.assertIn("<source-branch (추정)|확인 필요>", reference)
        self.assertIn("<repo>: 폴더 <relative-folder> / 현재 브랜치 <branch> / 변경상태 <dirty|clean>", reference)
        self.assertIn("Add each repo's manifest generation/current PR", reference)
        self.assertIn("Keep upstream, HEAD, locks, prunable state, and operation state out", reference)
        self.assertIn("filter to it and do not mix the workspace or sibling bundles", reference)

    def test_inspector_is_read_only_and_avoids_mutating_git_commands(self) -> None:
        text = read(INSPECTOR)
        tree = ast.parse(text)
        git_commands: list[tuple[str, ...]] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
                continue
            if node.func.id != "run_git" or len(node.args) < 2 or not isinstance(node.args[1], ast.List):
                continue
            values = tuple(
                item.value for item in node.args[1].elts if isinstance(item, ast.Constant) and isinstance(item.value, str)
            )
            if values:
                git_commands.append(values)

        forbidden = {"add", "merge", "rebase", "push", "pull", "fetch", "reset", "switch", "checkout"}
        self.assertFalse({command[0] for command in git_commands} & forbidden)
        self.assertNotIn(("branch", "-D"), git_commands)

        self.assertIn('"worktree", "list", "--porcelain"', text)
        self.assertIn('"status", "--porcelain"', text)
        self.assertIn('"rev-parse", "--show-toplevel"', text)
        self.assertIn('"rev-parse", "--git-path", name', text)
        self.assertIn('"operation_state": operation_state(path)', text)
        self.assertIn('key in {"locked", "prunable"}', text)
        self.assertIn('parser.add_argument("--bundle"', text)
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
    def test_inspector_filtered_output_uses_bundle_and_single_line_repos(self) -> None:
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
                [
                    sys.executable,
                    str(INSPECTOR),
                    "--root",
                    str(root),
                    "--max-depth",
                    "4",
                    "--bundle",
                    "worktrees/feature-etc-docs",
                ],
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
            self.assertNotIn("대상 묶음: workspace", output)

            json_result = subprocess.run(
                [
                    sys.executable,
                    str(INSPECTOR),
                    "--root",
                    str(root),
                    "--max-depth",
                    "4",
                    "--bundle",
                    str(bundle_repo.parent),
                    "--json",
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            bundle_data = json.loads(json_result.stdout)

            self.assertEqual([bundle["name"] for bundle in bundle_data["bundles"]], ["worktrees/feature-etc-docs"])
            self.assertEqual(bundle_data["bundles"][0]["items"][0]["operation_state"], "-")

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
    def test_inspector_reports_in_progress_merge(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "service-a"
            repo.mkdir()
            subprocess.run(["git", "init"], cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)
            subprocess.run(["git", "checkout", "-b", "main"], cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            tracked = repo / "tracked.txt"
            tracked.write_text("base\n", encoding="utf-8")
            subprocess.run(["git", "add", "tracked.txt"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-m", "base"], cwd=repo, check=True, stdout=subprocess.PIPE)
            subprocess.run(["git", "checkout", "-b", "topic"], cwd=repo, check=True, stdout=subprocess.PIPE)
            tracked.write_text("topic\n", encoding="utf-8")
            subprocess.run(["git", "commit", "-am", "topic"], cwd=repo, check=True, stdout=subprocess.PIPE)
            subprocess.run(["git", "checkout", "main"], cwd=repo, check=True, stdout=subprocess.PIPE)
            tracked.write_text("main\n", encoding="utf-8")
            subprocess.run(["git", "commit", "-am", "main"], cwd=repo, check=True, stdout=subprocess.PIPE)
            merge = subprocess.run(
                ["git", "merge", "topic"],
                cwd=repo,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertNotEqual(merge.returncode, 0)

            result = subprocess.run(
                [sys.executable, str(INSPECTOR), "--root", str(root), "--max-depth", "2", "--json"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            data = json.loads(result.stdout)

            self.assertEqual(data["groups"][0]["worktrees"][0]["operation_state"], "merge")

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
        self.assertIn('short_description: "Low-interruption permanent worktrees and chained PRs."', text)
        self.assertIn("Use $stageflow:multi-repo-worktree submit to publish the current", text)
        self.assertIn("allow_implicit_invocation: false", text)

    def test_plugin_manifest_exposes_multi_repo_worktree_prompt(self) -> None:
        manifest = json.loads(read(PLUGIN_JSON))
        interface = manifest["interface"]

        self.assertIn("multi-repo-worktree", interface["longDescription"])
        self.assertIn(
            "low-interruption permanent worktrees with one-time create, repeated same-branch submit",
            interface["longDescription"],
        )
        self.assertIn(
            "Use $stageflow:multi-repo-worktree submit to publish the current multi-repo worktree without routine re-approval.",
            interface["defaultPrompt"],
        )


class SlotManifestTests(unittest.TestCase):
    def run_manifest(self, root: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SLOT_MANIFEST), "--root", str(root), *arguments],
            check=check,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def test_initialize_is_exactly_idempotent_and_rejects_binding_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "worktrees" / "slot-1"
            first = self.run_manifest(
                root,
                "initialize",
                "--slot", "slot-1",
                "--path", str(path),
                "--repository", "service-a", "task-a", "main", "origin",
                "--repository", "service-b", "task-b", "main", "origin",
            )
            second = self.run_manifest(
                root,
                "initialize",
                "--slot", "slot-1",
                "--path", str(path),
                "--repository", "service-b", "task-b", "main", "origin",
                "--repository", "service-a", "task-a", "main", "origin",
            )
            self.run_manifest(root, "lock", "--slot", "slot-1", "--token", "submit-a")
            self.run_manifest(
                root,
                "record-batch",
                "--slot", "slot-1",
                "--token", "submit-a",
                "--expected-generation", "0",
                "--repository-pr", "service-a", "17",
            )
            after_pr = self.run_manifest(
                root,
                "initialize",
                "--slot", "slot-1",
                "--path", str(path),
                "--repository", "service-a", "task-a", "main", "origin",
                "--repository", "service-b", "task-b", "main", "origin",
            )
            conflict = self.run_manifest(
                root,
                "initialize",
                "--slot", "slot-1",
                "--path", str(path),
                "--repository", "service-a", "other-branch", "main", "origin",
                "--repository", "service-b", "task-b", "main", "origin",
                check=False,
            )

            self.assertEqual(json.loads(first.stdout)["result"], json.loads(second.stdout)["result"])
            self.assertEqual(
                json.loads(after_pr.stdout)["result"]["repositories"]["service-a"],
                {
                    "branch": "task-a",
                    "source_branch": "main",
                    "remote": "origin",
                    "generation": 1,
                    "pr": "17",
                },
            )
            self.assertEqual(conflict.returncode, 2)
            self.assertIn("permanent slot binding mismatch", conflict.stderr)
            result = json.loads(first.stdout)["result"]
            self.assertNotIn("owner", result)
            self.assertNotIn("state", result)
            self.assertEqual(
                result["repositories"]["service-a"],
                {
                    "branch": "task-a",
                    "source_branch": "main",
                    "remote": "origin",
                    "generation": 0,
                    "pr": None,
                },
            )

    def test_concurrent_conflicting_initializations_leave_one_valid_binding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "worktrees" / "slot-1"
            commands = [
                [
                    sys.executable,
                    str(SLOT_MANIFEST),
                    "--root",
                    str(root),
                    "initialize",
                    "--slot", "slot-1",
                    "--path", str(path),
                    "--repository", "service-a", branch, "main", "origin",
                ]
                for branch in ["task-a", "task-b"]
            ]
            processes = [
                subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                for command in commands
            ]
            results = [process.communicate(timeout=10) + (process.returncode,) for process in processes]

            self.assertEqual(sorted(result[2] for result in results), [0, 2])
            status = json.loads(self.run_manifest(root, "status", "--slot", "slot-1").stdout)["result"]
            self.assertIn(status["repositories"]["service-a"]["branch"], {"task-a", "task-b"})
            self.assertEqual(status["repositories"]["service-a"]["generation"], 0)

    def test_schema_v2_status_is_read_only_and_selected_slot_context_binding_is_atomic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / ".stageflow-worktrees"
            state.mkdir()
            manifest_path = state / "slots.json"
            manifest = {
                "schema_version": 2,
                "slots": {
                    "slot-1": {
                        "path": str((root / "worktrees" / "slot-1").resolve()),
                        "repositories": {
                            "service-a": {"branch": "task-a", "generation": 1, "pr": "17"},
                            "service-b": {"branch": "task-b", "generation": 1, "pr": "23"},
                        },
                    },
                    "slot-2": {
                        "path": str((root / "worktrees" / "slot-2").resolve()),
                        "repositories": {
                            "service-c": {"branch": "task-c", "generation": 0, "pr": None}
                        },
                    },
                },
            }
            manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
            before = manifest_path.read_bytes()

            status = json.loads(self.run_manifest(root, "status").stdout)["result"]
            self.assertEqual(status["schema_version"], 3)
            self.assertIsNone(status["slots"]["slot-1"]["repositories"]["service-a"]["source_branch"])
            self.assertIsNone(status["slots"]["slot-2"]["repositories"]["service-c"]["remote"])
            self.assertEqual(manifest_path.read_bytes(), before)

            locked_before_context = self.run_manifest(
                root, "lock", "--slot", "slot-1", "--token", "submit-a", check=False
            )
            self.assertEqual(locked_before_context.returncode, 2)
            self.assertIn("requires source context", locked_before_context.stderr)
            self.assertEqual(manifest_path.read_bytes(), before)

            incomplete = self.run_manifest(
                root,
                "bind-context",
                "--slot", "slot-1",
                "--repository-context", "service-a", "main", "origin",
                check=False,
            )
            self.assertEqual(incomplete.returncode, 2)
            self.assertIn("context must cover every repository", incomplete.stderr)
            self.assertEqual(manifest_path.read_bytes(), before)

            bound = self.run_manifest(
                root,
                "bind-context",
                "--slot", "slot-1",
                "--repository-context", "service-a", "main", "origin",
                "--repository-context", "service-b", "main", "upstream",
            )
            repeated = self.run_manifest(
                root,
                "bind-context",
                "--slot", "slot-1",
                "--repository-context", "service-b", "main", "upstream",
                "--repository-context", "service-a", "main", "origin",
            )
            self.assertEqual(json.loads(bound.stdout)["result"], json.loads(repeated.stdout)["result"])

            written = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(written["schema_version"], 3)
            self.assertEqual(
                written["slots"]["slot-1"]["repositories"]["service-a"]["source_branch"],
                "main",
            )
            self.assertEqual(
                written["slots"]["slot-1"]["repositories"]["service-b"]["remote"],
                "upstream",
            )
            self.assertIsNone(
                written["slots"]["slot-2"]["repositories"]["service-c"]["source_branch"]
            )
            self.assertIsNone(written["slots"]["slot-2"]["repositories"]["service-c"]["remote"])

            conflict_before = manifest_path.read_bytes()
            conflict = self.run_manifest(
                root,
                "bind-context",
                "--slot", "slot-1",
                "--repository-context", "service-a", "develop", "origin",
                "--repository-context", "service-b", "main", "upstream",
                check=False,
            )
            self.assertEqual(conflict.returncode, 2)
            self.assertIn("source context mismatch", conflict.stderr)
            self.assertEqual(manifest_path.read_bytes(), conflict_before)

    def test_initialize_enriches_exact_v2_binding_and_preserves_current_pr(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / ".stageflow-worktrees"
            state.mkdir()
            slot_path = (root / "worktrees" / "slot-1").resolve()
            manifest = {
                "schema_version": 2,
                "slots": {
                    "slot-1": {
                        "path": str(slot_path),
                        "repositories": {
                            "service-a": {"branch": "task-a", "generation": 1, "pr": "17"}
                        },
                    }
                },
            }
            (state / "slots.json").write_text(json.dumps(manifest), encoding="utf-8")

            enriched = self.run_manifest(
                root,
                "initialize",
                "--slot", "slot-1",
                "--path", str(slot_path),
                "--repository", "service-a", "task-a", "main", "origin",
            )
            identity = json.loads(enriched.stdout)["result"]["repositories"]["service-a"]
            self.assertEqual(identity["generation"], 1)
            self.assertEqual(identity["pr"], "17")
            self.assertEqual(identity["source_branch"], "main")
            self.assertEqual(identity["remote"], "origin")

            before = (state / "slots.json").read_bytes()
            mismatch = self.run_manifest(
                root,
                "initialize",
                "--slot", "slot-1",
                "--path", str(slot_path),
                "--repository", "service-a", "task-a", "develop", "origin",
                check=False,
            )
            self.assertEqual(mismatch.returncode, 2)
            self.assertIn("permanent slot binding mismatch", mismatch.stderr)
            self.assertEqual((state / "slots.json").read_bytes(), before)

    def test_manifest_lock_is_recoverable_after_holder_process_exits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            crash_while_locked = """
import os
import pathlib
import sys

module = {"__name__": "slot_manifest_crash_test"}
source = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
exec(compile(source, sys.argv[1], "exec"), module)
path = module["manifest_path"](pathlib.Path(sys.argv[2]))
with module["manifest_lock"](path, timeout_seconds=1.0):
    os._exit(0)
"""
            subprocess.run(
                [sys.executable, "-c", crash_while_locked, str(SLOT_MANIFEST), str(root)],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            lock_path = root / ".stageflow-worktrees" / "slots.json.lock"
            self.assertTrue(lock_path.exists())
            initialized = self.run_manifest(
                root,
                "initialize",
                "--slot", "slot-1",
                "--path", str(root / "worktrees" / "slot-1"),
                "--repository", "service-a", "task-a", "main", "origin",
            )
            self.assertEqual(json.loads(initialized.stdout)["result"]["path"], str(root / "worktrees" / "slot-1"))

    def test_operation_lock_is_exclusive_idempotent_and_exact_token_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "worktrees" / "slot-1"
            self.run_manifest(
                root,
                "initialize",
                "--slot", "slot-1",
                "--path", str(path),
                "--repository", "service-a", "task-a", "main", "origin",
            )
            first = self.run_manifest(root, "lock", "--slot", "slot-1", "--token", "submit-a")
            repeated = self.run_manifest(root, "lock", "--slot", "slot-1", "--token", "submit-a")
            competing = self.run_manifest(
                root, "lock", "--slot", "slot-1", "--token", "submit-b", check=False
            )
            wrong_unlock = self.run_manifest(
                root, "unlock", "--slot", "slot-1", "--token", "submit-b", check=False
            )
            status = self.run_manifest(root, "lock-status", "--slot", "slot-1")
            unlocked = self.run_manifest(
                root, "unlock", "--slot", "slot-1", "--token", "submit-a"
            )

            self.assertEqual(json.loads(first.stdout)["result"]["token"], "submit-a")
            self.assertEqual(json.loads(repeated.stdout)["result"]["token"], "submit-a")
            self.assertEqual(json.loads(status.stdout)["result"]["token"], "submit-a")
            self.assertEqual(json.loads(unlocked.stdout)["result"]["token"], "submit-a")
            self.assertEqual(competing.returncode, 2)
            self.assertIn("slot operation is locked", competing.stderr)
            self.assertEqual(wrong_unlock.returncode, 2)
            self.assertIn("token mismatch", wrong_unlock.stderr)

    def test_record_batch_requires_lock_and_advances_all_repositories_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "worktrees" / "slot-1"
            self.run_manifest(
                root,
                "initialize",
                "--slot", "slot-1",
                "--path", str(path),
                "--repository", "service-a", "task-a", "main", "origin",
                "--repository", "service-b", "task-b", "main", "origin",
            )
            no_lock = self.run_manifest(
                root,
                "record-batch",
                "--slot", "slot-1",
                "--token", "submit-a",
                "--expected-generation", "0",
                "--repository-pr", "service-a", "17",
                "--repository-pr", "service-b", "23",
                check=False,
            )
            self.run_manifest(root, "lock", "--slot", "slot-1", "--token", "submit-a")
            recorded = self.run_manifest(
                root,
                "record-batch",
                "--slot", "slot-1",
                "--token", "submit-a",
                "--expected-generation", "0",
                "--repository-pr", "service-a", "17",
                "--repository-pr", "service-b", "23",
            )

            self.assertEqual(no_lock.returncode, 2)
            self.assertIn("not locked", no_lock.stderr)
            result = json.loads(recorded.stdout)["result"]
            self.assertEqual(result["repositories"]["service-a"]["generation"], 1)
            self.assertEqual(result["repositories"]["service-a"]["pr"], "17")
            self.assertEqual(result["repositories"]["service-b"]["generation"], 1)
            self.assertEqual(result["repositories"]["service-b"]["pr"], "23")
            self.assertNotIn("subprocess", read(SLOT_MANIFEST))

    def test_record_batch_is_retry_idempotent_and_advances_next_pr(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "worktrees" / "slot-1"
            self.run_manifest(
                root,
                "initialize",
                "--slot", "slot-1",
                "--path", str(path),
                "--repository", "service-a", "task-a", "main", "origin",
            )
            self.run_manifest(root, "lock", "--slot", "slot-1", "--token", "submit-a")
            first = self.run_manifest(
                root,
                "record-batch",
                "--slot", "slot-1",
                "--token", "submit-a",
                "--expected-generation", "0",
                "--repository-pr", "service-a", "17",
            )
            repeated = self.run_manifest(
                root,
                "record-batch",
                "--slot", "slot-1",
                "--token", "submit-a",
                "--expected-generation", "0",
                "--repository-pr", "service-a", "17",
            )
            second = self.run_manifest(
                root,
                "record-batch",
                "--slot", "slot-1",
                "--token", "submit-a",
                "--expected-generation", "1",
                "--repository-pr", "service-a", "18",
            )

            self.assertEqual(json.loads(first.stdout)["result"], json.loads(repeated.stdout)["result"])
            identity = json.loads(second.stdout)["result"]["repositories"]["service-a"]
            self.assertEqual(
                identity,
                {
                    "branch": "task-a",
                    "source_branch": "main",
                    "remote": "origin",
                    "generation": 2,
                    "pr": "18",
                },
            )

    def test_record_batch_rejects_generation_or_repository_mismatch_without_partial_update(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "worktrees" / "slot-1"
            self.run_manifest(
                root,
                "initialize",
                "--slot", "slot-1",
                "--path", str(path),
                "--repository", "service-a", "task-a", "main", "origin",
                "--repository", "service-b", "task-b", "main", "origin",
            )
            self.run_manifest(root, "lock", "--slot", "slot-1", "--token", "submit-a")
            unknown = self.run_manifest(
                root,
                "record-batch",
                "--slot", "slot-1",
                "--token", "submit-a",
                "--expected-generation", "0",
                "--repository-pr", "service-a", "17",
                "--repository-pr", "missing", "23",
                check=False,
            )
            wrong_generation = self.run_manifest(
                root,
                "record-batch",
                "--slot", "slot-1",
                "--token", "submit-a",
                "--expected-generation", "1",
                "--repository-pr", "service-a", "17",
                check=False,
            )
            status = json.loads(self.run_manifest(root, "status", "--slot", "slot-1").stdout)["result"]

            self.assertEqual(unknown.returncode, 2)
            self.assertIn("no repository binding", unknown.stderr)
            self.assertEqual(wrong_generation.returncode, 2)
            self.assertIn("generation mismatch", wrong_generation.stderr)
            self.assertEqual(status["repositories"]["service-a"]["generation"], 0)
            self.assertIsNone(status["repositories"]["service-a"]["pr"])

    def test_legacy_lifecycle_manifest_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / ".stageflow-worktrees"
            state.mkdir()
            manifest = {
                "schema_version": 1,
                "slots": {
                    "slot-1": {
                        "owner": "task-a",
                        "path": str((root / "worktrees" / "slot-1").resolve()),
                        "repositories": {
                            "service-a": {
                                "branch": "task-a",
                                "pr": "17",
                                "head_sha": "a" * 40,
                                "pushed_sha": "a" * 40,
                            }
                        },
                        "state": "active",
                    }
                },
            }
            (state / "slots.json").write_text(json.dumps(manifest), encoding="utf-8")

            status = self.run_manifest(root, "status", "--slot", "slot-1", check=False)

            self.assertEqual(status.returncode, 2)
            self.assertIn("unsupported manifest schema: 1", status.stderr)
            self.assertIn("legacy active/released manifests require manual correction", status.stderr)

    def test_permanent_slot_rejects_a_different_path_or_repository_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = root / "worktrees" / "slot-1"
            replacement = root / "worktrees" / "other-slot"
            self.run_manifest(
                root,
                "initialize",
                "--slot", "slot-1",
                "--path", str(original),
                "--repository", "service-a", "task-a", "main", "origin",
            )
            path_result = self.run_manifest(
                root,
                "initialize",
                "--slot", "slot-1",
                "--path", str(replacement),
                "--repository", "service-a", "task-a", "main", "origin",
                check=False,
            )
            repositories_result = self.run_manifest(
                root,
                "initialize",
                "--slot", "slot-1",
                "--path", str(original),
                "--repository", "service-a", "task-a", "main", "origin",
                "--repository", "service-b", "task-b", "main", "origin",
                check=False,
            )

            self.assertEqual(path_result.returncode, 2)
            self.assertIn("permanent slot binding mismatch", path_result.stderr)
            self.assertEqual(repositories_result.returncode, 2)
            self.assertIn("permanent slot binding mismatch", repositories_result.stderr)
            status = json.loads(self.run_manifest(root, "status", "--slot", "slot-1").stdout)["result"]
            self.assertEqual(status["path"], str(original))

    def test_concurrent_operation_locks_allow_only_one_token(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_manifest(
                root,
                "initialize",
                "--slot", "slot-1",
                "--path", str(root / "worktrees" / "slot-1"),
                "--repository", "service-a", "task-a", "main", "origin",
            )
            commands = [
                [
                    sys.executable,
                    str(SLOT_MANIFEST),
                    "--root", str(root),
                    "lock",
                    "--slot", "slot-1",
                    "--token", token,
                ]
                for token in ["submit-a", "submit-b"]
            ]
            processes = [
                subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                for command in commands
            ]
            results = [process.communicate(timeout=10) + (process.returncode,) for process in processes]

            self.assertEqual(sorted(result[2] for result in results), [0, 2])
            lock = json.loads(self.run_manifest(root, "lock-status", "--slot", "slot-1").stdout)["result"]
            self.assertIn(lock["token"], {"submit-a", "submit-b"})

    def test_unpublished_lock_candidate_does_not_create_a_malformed_stale_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_manifest(
                root,
                "initialize",
                "--slot", "slot-1",
                "--path", str(root / "worktrees" / "slot-1"),
                "--repository", "service-a", "task-a", "main", "origin",
            )
            locks = root / ".stageflow-worktrees" / "operation-locks"
            locks.mkdir()
            (locks / "interrupted-candidate.tmp").write_text("{partial", encoding="utf-8")

            acquired = self.run_manifest(
                root, "lock", "--slot", "slot-1", "--token", "submit-a"
            )
            status = self.run_manifest(root, "lock-status", "--slot", "slot-1")

            self.assertEqual(json.loads(acquired.stdout)["result"]["token"], "submit-a")
            self.assertEqual(json.loads(status.stdout)["result"]["token"], "submit-a")
            source = read(SLOT_MANIFEST)
            self.assertIn("os.link(candidate, path)", source)
            self.assertNotIn("os.open(path, os.O_CREAT | os.O_EXCL", source)

    def test_lock_publish_failure_leaves_no_final_or_candidate_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            module: dict[str, object] = {"__name__": "slot_manifest_test"}
            exec(compile(read(SLOT_MANIFEST), str(SLOT_MANIFEST), "exec"), module)
            lock_path = module["operation_lock_path"](root, "slot-1")

            with mock.patch.object(module["os"], "link", side_effect=OSError("simulated crash")):
                with self.assertRaises(module["ManifestError"]):
                    module["acquire_operation_lock"](root, "slot-1", "submit-a")

            self.assertFalse(lock_path.exists())
            self.assertEqual(list(lock_path.parent.glob("*.tmp")), [])

    def test_schema_rejects_relative_paths_and_unexpected_lifecycle_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / ".stageflow-worktrees"
            state.mkdir()
            manifest = {
                "schema_version": 2,
                "slots": {
                    "slot-1": {
                        "path": "worktrees/slot-1",
                        "repositories": {
                            "service-a": {"branch": "task-a", "generation": 0, "pr": None}
                        },
                    }
                },
            }
            (state / "slots.json").write_text(json.dumps(manifest), encoding="utf-8")
            relative = self.run_manifest(root, "status", check=False)

            manifest["slots"]["slot-1"]["path"] = str((root / "worktrees" / "slot-1").resolve())
            manifest["slots"]["slot-1"]["state"] = "active"
            (state / "slots.json").write_text(json.dumps(manifest), encoding="utf-8")
            lifecycle = self.run_manifest(root, "status", check=False)

            self.assertEqual(relative.returncode, 2)
            self.assertIn("invalid path", relative.stderr)
            self.assertEqual(lifecycle.returncode, 2)
            self.assertIn("unexpected fields", lifecycle.stderr)

    def test_schema_rejects_boolean_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / ".stageflow-worktrees"
            state.mkdir()
            for generation, pr in [(True, "17"), (False, None)]:
                with self.subTest(generation=generation):
                    manifest = {
                        "schema_version": 2,
                        "slots": {
                            "slot-1": {
                                "path": str((root / "worktrees" / "slot-1").resolve()),
                                "repositories": {
                                    "service-a": {
                                        "branch": "task-a",
                                        "generation": generation,
                                        "pr": pr,
                                    }
                                },
                            }
                        },
                    }
                    (state / "slots.json").write_text(json.dumps(manifest), encoding="utf-8")
                    result = self.run_manifest(root, "status", check=False)

                    self.assertEqual(result.returncode, 2)
                    self.assertIn("invalid generation", result.stderr)

    def test_schema_v3_rejects_partial_or_empty_source_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / ".stageflow-worktrees"
            state.mkdir()
            manifest_path = state / "slots.json"
            base_identity = {
                "branch": "task-a",
                "source_branch": "main",
                "remote": "origin",
                "generation": 0,
                "pr": None,
            }
            for source_branch, remote, error in [
                (None, "origin", "bind source branch and remote together"),
                ("main", None, "bind source branch and remote together"),
                ("", "origin", "invalid source context"),
                ("main", "", "invalid source context"),
            ]:
                with self.subTest(source_branch=source_branch, remote=remote):
                    identity = dict(base_identity, source_branch=source_branch, remote=remote)
                    manifest = {
                        "schema_version": 3,
                        "slots": {
                            "slot-1": {
                                "path": str((root / "worktrees" / "slot-1").resolve()),
                                "repositories": {"service-a": identity},
                            }
                        },
                    }
                    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                    result = self.run_manifest(root, "status", check=False)
                    self.assertEqual(result.returncode, 2)
                    self.assertIn(error, result.stderr)

    def test_schema_version_must_be_an_exact_integer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / ".stageflow-worktrees"
            state.mkdir()
            manifest_path = state / "slots.json"
            for version in [True, 2.0, 3.0, "3"]:
                with self.subTest(version=version):
                    manifest_path.write_text(
                        json.dumps({"schema_version": version, "slots": {}}),
                        encoding="utf-8",
                    )
                    result = self.run_manifest(root, "status", check=False)
                    self.assertEqual(result.returncode, 2)
                    self.assertIn("unsupported manifest schema", result.stderr)

    def test_malformed_manifest_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / ".stageflow-worktrees"
            state.mkdir()
            (state / "slots.json").write_text("{broken", encoding="utf-8")
            result = self.run_manifest(root, "status", check=False)

            self.assertEqual(result.returncode, 2)
            self.assertIn("cannot read manifest", result.stderr)

@unittest.skipIf(shutil.which("git") is None, "git is required for same-branch PR flow tests")
class SameBranchFollowUpFlowTests(unittest.TestCase):
    def git(self, path: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(path), *arguments],
            check=check,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def test_squash_merged_base_leaves_only_next_work_in_three_dot_diff(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            subprocess.run(
                ["git", "init", "-b", "main", str(repo)],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.git(repo, "config", "user.name", "Stageflow Test")
            self.git(repo, "config", "user.email", "stageflow@example.invalid")
            (repo / "base.txt").write_text("base\n", encoding="utf-8")
            self.git(repo, "add", "base.txt")
            self.git(repo, "commit", "-m", "base")

            self.git(repo, "switch", "-c", "fixed-task")
            (repo / "a.txt").write_text("work A\n", encoding="utf-8")
            self.git(repo, "add", "a.txt")
            self.git(repo, "commit", "-m", "작업 A")

            self.git(repo, "switch", "main")
            (repo / "a.txt").write_text("work A\n", encoding="utf-8")
            self.git(repo, "add", "a.txt")
            self.git(repo, "commit", "-m", "작업 A 스쿼시 병합")
            pinned_base = self.git(repo, "rev-parse", "HEAD").stdout.strip()

            self.git(repo, "switch", "fixed-task")
            (repo / "b.txt").write_text("work B\n", encoding="utf-8")
            self.git(repo, "add", "b.txt")
            self.git(repo, "commit", "-m", "작업 B")
            self.git(repo, "merge", pinned_base, "-m", "기준 브랜치 main 동기화")

            ancestor = self.git(repo, "merge-base", "--is-ancestor", pinned_base, "HEAD", check=False)
            changed = self.git(repo, "diff", "--name-only", f"{pinned_base}...HEAD").stdout.splitlines()
            commits = self.git(repo, "log", "--format=%s", f"{pinned_base}..HEAD").stdout

            self.assertEqual(ancestor.returncode, 0)
            self.assertEqual(changed, ["b.txt"])
            self.assertIn("작업 A", commits)
            self.assertIn("작업 B", commits)

    def test_squash_merged_base_without_next_work_has_empty_three_dot_diff(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            subprocess.run(
                ["git", "init", "-b", "main", str(repo)],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.git(repo, "config", "user.name", "Stageflow Test")
            self.git(repo, "config", "user.email", "stageflow@example.invalid")
            (repo / "base.txt").write_text("base\n", encoding="utf-8")
            self.git(repo, "add", "base.txt")
            self.git(repo, "commit", "-m", "base")

            self.git(repo, "switch", "-c", "fixed-task")
            (repo / "a.txt").write_text("work A\n", encoding="utf-8")
            self.git(repo, "add", "a.txt")
            self.git(repo, "commit", "-m", "작업 A")

            self.git(repo, "switch", "main")
            (repo / "a.txt").write_text("work A\n", encoding="utf-8")
            self.git(repo, "add", "a.txt")
            self.git(repo, "commit", "-m", "작업 A 스쿼시 병합")
            pinned_base = self.git(repo, "rev-parse", "HEAD").stdout.strip()

            self.git(repo, "switch", "fixed-task")
            self.git(repo, "merge", pinned_base, "-m", "기준 브랜치 main 동기화")
            changed = self.git(repo, "diff", "--name-only", f"{pinned_base}...HEAD").stdout

            self.assertEqual(changed, "")
            self.assertEqual(
                self.git(repo, "merge-base", "--is-ancestor", pinned_base, "HEAD", check=False).returncode,
                0,
            )

    def test_deleted_remote_head_is_recreated_by_non_force_same_branch_push(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            remote = root / "remote.git"
            repo = root / "repo"
            subprocess.run(
                ["git", "init", "--bare", str(remote)],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            subprocess.run(
                ["git", "clone", str(remote), str(repo)],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.git(repo, "config", "user.name", "Stageflow Test")
            self.git(repo, "config", "user.email", "stageflow@example.invalid")
            self.git(repo, "switch", "-c", "main")
            (repo / "base.txt").write_text("base\n", encoding="utf-8")
            self.git(repo, "add", "base.txt")
            self.git(repo, "commit", "-m", "base")
            self.git(repo, "push", "-u", "origin", "main")

            self.git(repo, "switch", "-c", "fixed-task")
            (repo / "a.txt").write_text("work A\n", encoding="utf-8")
            self.git(repo, "add", "a.txt")
            self.git(repo, "commit", "-m", "작업 A")
            self.git(repo, "push", "-u", "origin", "fixed-task")

            self.git(repo, "switch", "main")
            (repo / "a.txt").write_text("work A\n", encoding="utf-8")
            self.git(repo, "add", "a.txt")
            self.git(repo, "commit", "-m", "작업 A 스쿼시 병합")
            self.git(repo, "push", "origin", "main")
            self.git(repo, "push", "origin", "--delete", "fixed-task")

            self.git(repo, "switch", "fixed-task")
            (repo / "b.txt").write_text("work B\n", encoding="utf-8")
            self.git(repo, "add", "b.txt")
            self.git(repo, "commit", "-m", "작업 B")
            self.git(repo, "fetch", "--prune", "origin")
            missing_remote_head = self.git(
                repo, "rev-parse", "--verify", "refs/remotes/origin/fixed-task", check=False
            )
            pinned_base = self.git(repo, "rev-parse", "refs/remotes/origin/main").stdout.strip()
            self.git(repo, "merge", pinned_base, "-m", "기준 브랜치 main 동기화")
            changed = self.git(repo, "diff", "--name-only", f"{pinned_base}...HEAD").stdout.splitlines()
            self.git(repo, "push", "origin", "HEAD:refs/heads/fixed-task")
            recreated = self.git(repo, "ls-remote", "--heads", "origin", "refs/heads/fixed-task").stdout

            self.assertNotEqual(missing_remote_head.returncode, 0)
            self.assertEqual(changed, ["b.txt"])
            self.assertIn(self.git(repo, "rev-parse", "HEAD").stdout.strip(), recreated)


@unittest.skipIf(shutil.which("git") is None, "git is required for pull/sync flow tests")
class PullAndSyncFlowTests(unittest.TestCase):
    def git(self, path: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(path), *arguments],
            check=check,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def configure(self, path: Path) -> None:
        self.git(path, "config", "user.email", "test@example.com")
        self.git(path, "config", "user.name", "Test User")

    def make_remote_fixture(self, root: Path) -> tuple[Path, Path, Path]:
        remote = root / "remote.git"
        seed = root / "seed"
        original = root / "original"
        subprocess.run(
            ["git", "init", "--bare", str(remote)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        subprocess.run(["git", "clone", str(remote), str(seed)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.configure(seed)
        self.git(seed, "switch", "-c", "main")
        (seed / "tracked.txt").write_text("base\n", encoding="utf-8")
        self.git(seed, "add", "tracked.txt")
        self.git(seed, "commit", "-m", "base")
        self.git(seed, "push", "-u", "origin", "main")
        subprocess.run(["git", "clone", "--branch", "main", str(remote), str(original)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.configure(original)
        return remote, seed, original

    def advance_remote(self, seed: Path, content: str) -> str:
        (seed / "tracked.txt").write_text(content, encoding="utf-8")
        self.git(seed, "commit", "-am", content.strip())
        self.git(seed, "push", "origin", "main")
        return self.git(seed, "rev-parse", "HEAD").stdout.strip()

    def test_pull_fetch_then_fast_forwards_only_the_original(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _, seed, original = self.make_remote_fixture(Path(tmp))
            remote_head = self.advance_remote(seed, "remote update\n")

            self.git(original, "fetch", "--prune", "origin")
            pinned = self.git(original, "rev-parse", "refs/remotes/origin/main").stdout.strip()
            self.assertEqual(pinned, remote_head)
            self.git(original, "merge", "--ff-only", pinned)

            self.assertEqual(self.git(original, "rev-parse", "HEAD").stdout.strip(), remote_head)
            self.assertEqual(self.git(original, "branch", "--show-current").stdout.strip(), "main")
            self.assertEqual(self.git(original, "status", "--porcelain").stdout, "")

    def test_pull_uses_the_manifest_remote_name_instead_of_literal_origin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _, seed, original = self.make_remote_fixture(Path(tmp))
            self.git(original, "remote", "rename", "origin", "upstream")
            remote_head = self.advance_remote(seed, "remote update\n")

            self.git(original, "fetch", "--prune", "upstream")
            pinned = self.git(
                original, "rev-parse", "refs/remotes/upstream/main"
            ).stdout.strip()
            self.assertEqual(pinned, remote_head)
            self.git(original, "merge", "--ff-only", pinned)

            self.assertEqual(self.git(original, "rev-parse", "HEAD").stdout.strip(), remote_head)
            self.assertEqual(self.git(original, "status", "--porcelain").stdout, "")

    def test_sync_fetches_in_derived_worktree_without_updating_original_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, seed, original = self.make_remote_fixture(root)
            derived = root / "derived"
            self.git(original, "worktree", "add", "-b", "task", str(derived), "main")
            original_head = self.git(original, "rev-parse", "HEAD").stdout.strip()
            remote_head = self.advance_remote(seed, "remote update\n")

            self.git(derived, "fetch", "--prune", "origin")
            pinned = self.git(derived, "rev-parse", "refs/remotes/origin/main").stdout.strip()
            self.assertEqual(pinned, remote_head)
            self.git(derived, "merge", pinned)

            self.assertEqual(self.git(derived, "rev-parse", "HEAD").stdout.strip(), remote_head)
            self.assertEqual(self.git(original, "rev-parse", "HEAD").stdout.strip(), original_head)
            self.assertEqual(self.git(original, "branch", "--show-current").stdout.strip(), "main")
            self.assertEqual(self.git(original, "status", "--porcelain").stdout, "")

    def test_sync_uses_the_manifest_remote_name_without_updating_original_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, seed, original = self.make_remote_fixture(root)
            self.git(original, "remote", "rename", "origin", "upstream")
            derived = root / "derived"
            self.git(original, "worktree", "add", "-b", "task", str(derived), "main")
            original_head = self.git(original, "rev-parse", "HEAD").stdout.strip()
            remote_head = self.advance_remote(seed, "remote update\n")

            self.git(derived, "fetch", "--prune", "upstream")
            pinned = self.git(
                derived, "rev-parse", "refs/remotes/upstream/main"
            ).stdout.strip()
            self.assertEqual(pinned, remote_head)
            self.git(derived, "merge", pinned)

            self.assertEqual(self.git(derived, "rev-parse", "HEAD").stdout.strip(), remote_head)
            self.assertEqual(self.git(original, "rev-parse", "HEAD").stdout.strip(), original_head)
            self.assertEqual(self.git(original, "status", "--porcelain").stdout, "")

    def test_pull_fast_forward_check_rejects_diverged_original(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _, seed, original = self.make_remote_fixture(Path(tmp))
            (original / "local.txt").write_text("local\n", encoding="utf-8")
            self.git(original, "add", "local.txt")
            self.git(original, "commit", "-m", "local")
            self.advance_remote(seed, "remote update\n")
            self.git(original, "fetch", "--prune", "origin")
            pinned = self.git(original, "rev-parse", "refs/remotes/origin/main").stdout.strip()

            ancestor = self.git(original, "merge-base", "--is-ancestor", "HEAD", pinned, check=False)
            merge = self.git(original, "merge", "--ff-only", pinned, check=False)

            self.assertNotEqual(ancestor.returncode, 0)
            self.assertNotEqual(merge.returncode, 0)

    def test_preflight_can_detect_dirty_and_wrong_location_before_fetch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, _, original = self.make_remote_fixture(root)
            derived = root / "derived"
            self.git(original, "worktree", "add", "-b", "task", str(derived), "main")
            (derived / "tracked.txt").write_text("dirty task change\n", encoding="utf-8")

            self.assertNotEqual(self.git(derived, "status", "--porcelain").stdout, "")
            self.assertEqual(self.git(derived, "branch", "--show-current").stdout.strip(), "task")
            self.assertEqual(self.git(original, "branch", "--show-current").stdout.strip(), "main")
            self.assertNotEqual(
                self.git(original, "branch", "--show-current").stdout.strip(),
                "task",
            )

    def test_sync_conflict_stops_in_derived_and_leaves_original_checkout_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, seed, original = self.make_remote_fixture(root)
            derived = root / "derived"
            self.git(original, "worktree", "add", "-b", "task", str(derived), "main")
            (derived / "tracked.txt").write_text("task change\n", encoding="utf-8")
            self.git(derived, "commit", "-am", "task change")
            original_head = self.git(original, "rev-parse", "HEAD").stdout.strip()
            original_content = (original / "tracked.txt").read_text(encoding="utf-8")
            remote_head = self.advance_remote(seed, "remote change\n")

            self.git(derived, "fetch", "--prune", "origin")
            pinned = self.git(derived, "rev-parse", "refs/remotes/origin/main").stdout.strip()
            self.assertEqual(pinned, remote_head)
            merge = self.git(derived, "merge", pinned, check=False)

            self.assertNotEqual(merge.returncode, 0)
            self.assertEqual(
                self.git(derived, "rev-parse", "-q", "--verify", "MERGE_HEAD").stdout.strip(),
                pinned,
            )
            self.assertEqual(self.git(original, "rev-parse", "HEAD").stdout.strip(), original_head)
            self.assertEqual(self.git(original, "branch", "--show-current").stdout.strip(), "main")
            self.assertEqual(self.git(original, "status", "--porcelain").stdout, "")
            self.assertEqual((original / "tracked.txt").read_text(encoding="utf-8"), original_content)


if __name__ == "__main__":
    unittest.main()
