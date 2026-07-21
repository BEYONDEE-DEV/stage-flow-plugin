from __future__ import annotations

import ast
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
        self.assertIn("help, status, create, submit, pull, and sync", text)
        self.assertIn("$stageflow:multi-repo-worktree <keyword> [free-form intent]", text)
        self.assertIn("[$stageflow:multi-repo-worktree](...)", text)
        self.assertIn("references/worktree-operations.md", text)
        self.assertIn("scripts/inspect_worktrees.py", text)
        self.assertIn('python3 "<skill-dir>/scripts/inspect_worktrees.py"', text)
        self.assertIn("do not assume the current working directory is the plugin root", text)
        self.assertNotIn("**Setup**", text)
        self.assertNotIn("TODO", text)

    def test_skill_records_source_and_derived_branch_safety_rules(self) -> None:
        text = read(SKILL)

        self.assertIn("source branch as a repo-specific, user-confirmed fact", text)
        self.assertIn("task branches", text)
        self.assertIn("Git does not record the branch from which another branch was originally created", text)
        self.assertIn("Before any Git write", text)
        self.assertIn("Accept approval only after presenting that exact plan", text)
        self.assertIn("Approval applies only to the displayed batch", text)
        self.assertIn("Never execute a write using an inferred or ambiguous source branch", text)
        self.assertIn("Never reset, clean, force checkout, force push, or delete a branch", text)
        self.assertIn("`sync` runs only in development worktrees", text)
        self.assertIn("explicit approval", text)
        self.assertIn("missing or ambiguous remotes", text)

    def test_reference_covers_required_operations(self) -> None:
        text = read(REFERENCE)

        for phrase in [
            "## Keyword And Approval Contract",
            "## Read-Only Inspection And Status",
            "## Create",
            "## Pull",
            "## Sync",
            "`help`",
            "`status`",
            "`create`",
            "`pull`",
            "`sync`",
            "## Submit",
            "## Partial Results And Reporting",
            "Preflight the complete batch",
            "Receive explicit approval after the exact plan",
            "source branch",
            "derived worktree",
            "List repos independently even when branch names match",
            "Git does not retain a branch's creation parent",
            "Fast-forward one repo at a time",
        ]:
            self.assertIn(phrase, text)

        for removed_heading in ["## Recycle", "## Integrate", "## Merge"]:
            self.assertNotIn(removed_heading, text)

    def test_simplified_pr_slot_workflow_has_explicit_roles_and_safety_gates(self) -> None:
        skill = read(SKILL)
        reference = read(REFERENCE)

        for phrase in [
            ".stageflow-worktrees/slots.json",
            "Only the exact active owner",
            "safe released-slot reuse",
            "GitHub PR merge is manual and outside this skill",
            "Never enable auto-merge or run a PR merge command",
            "`pull` runs only in confirmed original/source worktrees",
            "`sync` runs only in development worktrees",
            "recovery-required",
            "never claim rollback",
        ]:
            self.assertIn(phrase, skill)

        for phrase in [
            "user merges the PR on GitHub",
            "Development owner",
            "Original owner",
            "GitHub user",
            "Same-owner claim is idempotent",
            "wrong-owner release",
            "Correction recovery",
            "minimal repository branch/PR identity",
            "The user merges on GitHub outside this skill",
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

    def test_submit_stops_at_regular_pr_and_releases_after_complete_success(self) -> None:
        skill = read(SKILL)
        reference = read(REFERENCE)

        for phrase in [
            "Write the PR title and explanatory prose in Korean",
            "Record only branch and PR identity",
            "After every repo succeeds, release the slot",
            "partial push, PR, or record failure keeps the slot active",
            "Do not pass `--draft`, run `gh pr ready`, create submitted-SHA comments",
            "The user merges on GitHub outside this skill",
        ]:
            self.assertIn(phrase, reference)

        self.assertIn("Show exact pushes and Korean PR titles/bodies before approval", skill)
        self.assertIn("record only repository branch/PR identity", skill)
        self.assertIn("Never enable auto-merge or merge a PR", skill)
        self.assertNotIn("submitted SHA", skill)

    def test_create_has_actionable_empty_reuse_and_correction_flows(self) -> None:
        skill = read(SKILL)
        reference = read(REFERENCE)

        self.assertIn("switches an existing released clean slot to a new branch", skill)
        self.assertIn("Claim before the first approved add/switch", skill)
        self.assertIn("Existing released-slot reuse", reference)
        self.assertIn(
            'switch -c "<new-task-branch>" "<confirmed-source-start-point>"',
            reference,
        )
        self.assertIn('switch "<recorded-pr-branch>"', reference)
        self.assertIn("Require the recorded local branch HEAD to equal that pinned PR-head SHA", reference)
        self.assertIn("worktree add -b", reference)
        self.assertIn("A partial add/switch keeps ownership active", reference)
        self.assertIn("--preserve-repositories", reference)

    def test_pull_and_sync_have_separate_locations_and_update_rules(self) -> None:
        skill = read(SKILL)
        reference = read(REFERENCE)

        self.assertIn("`pull` runs only in confirmed original/source worktrees", skill)
        self.assertIn("fast-forward each source branch to its pinned SHA", skill)
        self.assertIn("Run only in the requested development worktree bundle", skill)
        self.assertIn("never switch or update an original worktree", skill)
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
        self.assertIn("Show each participating repo on one line", reference)
        self.assertIn("Make `폴더` relative to `기준 폴더`", reference)
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
        self.assertIn('short_description: "Safe multi-repo worktree and PR coordination."', text)
        self.assertIn("Use $stageflow:multi-repo-worktree status", text)
        self.assertIn("allow_implicit_invocation: false", text)

    def test_plugin_manifest_exposes_multi_repo_worktree_prompt(self) -> None:
        manifest = json.loads(read(PLUGIN_JSON))
        interface = manifest["interface"]

        self.assertIn("multi-repo-worktree", interface["longDescription"])
        self.assertIn(
            "help, status, create, submit, pull, and sync keywords",
            interface["longDescription"],
        )
        self.assertIn(
            "Use $stageflow:multi-repo-worktree status to inspect a multi-repo Git worktree or PR slot bundle.",
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

    def test_claim_is_idempotent_for_exact_owner_and_rejects_other_owner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "worktrees" / "slot-1"
            first = self.run_manifest(
                root, "claim", "--slot", "slot-1", "--owner", "task-a", "--path", str(path)
            )
            second = self.run_manifest(
                root, "claim", "--slot", "slot-1", "--owner", "task-a", "--path", str(path)
            )
            conflict = self.run_manifest(
                root,
                "claim",
                "--slot",
                "slot-1",
                "--owner",
                "task-b",
                "--path",
                str(path),
                check=False,
            )

            self.assertEqual(json.loads(first.stdout)["result"], json.loads(second.stdout)["result"])
            self.assertEqual(conflict.returncode, 2)
            self.assertIn("owner mismatch", conflict.stderr)

    def test_concurrent_claims_have_one_owner_and_leave_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "worktrees" / "slot-1"
            commands = [
                [
                    sys.executable,
                    str(SLOT_MANIFEST),
                    "--root",
                    str(root),
                    "claim",
                    "--slot",
                    "slot-1",
                    "--owner",
                    owner,
                    "--path",
                    str(path),
                ]
                for owner in ["task-a", "task-b"]
            ]
            processes = [
                subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                for command in commands
            ]
            results = [process.communicate(timeout=10) + (process.returncode,) for process in processes]

            self.assertEqual(sorted(result[2] for result in results), [0, 2])
            status = json.loads(self.run_manifest(root, "status", "--slot", "slot-1").stdout)["result"]
            self.assertIn(status["owner"], {"task-a", "task-b"})
            self.assertEqual(status["state"], "active")

    def test_only_active_exact_owner_can_record_and_release(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "worktrees" / "slot-1"
            self.run_manifest(root, "claim", "--slot", "slot-1", "--owner", "task-a", "--path", str(path))

            integration_release = self.run_manifest(
                root, "release", "--slot", "slot-1", "--owner", "integration", check=False
            )
            self.assertEqual(integration_release.returncode, 2)

            self.run_manifest(
                root,
                "record",
                "--slot",
                "slot-1",
                "--owner",
                "task-a",
                "--repo",
                "service-a",
                "--branch",
                "task-a",
                "--pr",
                "17",
            )
            released = self.run_manifest(
                root, "release", "--slot", "slot-1", "--owner", "task-a"
            )
            stale_release = self.run_manifest(
                root, "release", "--slot", "slot-1", "--owner", "task-a", check=False
            )

            result = json.loads(released.stdout)["result"]
            self.assertEqual(result["state"], "released")
            self.assertEqual(result["repositories"]["service-a"]["pr"], "17")
            self.assertEqual(stale_release.returncode, 2)
            self.assertIn("not active", stale_release.stderr)

    def test_released_slot_can_be_claimed_by_new_owner_without_branch_deletion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "worktrees" / "slot-1"
            self.run_manifest(root, "claim", "--slot", "slot-1", "--owner", "task-a", "--path", str(path))
            self.run_manifest(
                root,
                "record",
                "--slot", "slot-1",
                "--owner", "task-a",
                "--repo", "service-a",
                "--branch", "task-a",
                "--pr", "17",
            )
            self.run_manifest(root, "release", "--slot", "slot-1", "--owner", "task-a")
            claimed = self.run_manifest(
                root, "claim", "--slot", "slot-1", "--owner", "task-b", "--path", str(path)
            )
            old_owner = self.run_manifest(
                root, "release", "--slot", "slot-1", "--owner", "task-a", check=False
            )

            result = json.loads(claimed.stdout)["result"]
            self.assertEqual(result["owner"], "task-b")
            self.assertEqual(result["repositories"], {})
            self.assertEqual(old_owner.returncode, 2)
            self.assertNotIn("subprocess", read(SLOT_MANIFEST))

    def test_record_stays_active_until_release_and_correction_owner_can_resubmit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "worktrees" / "slot-1"
            self.run_manifest(root, "claim", "--slot", "slot-1", "--owner", "task-a", "--path", str(path))
            self.run_manifest(
                root,
                "record",
                "--slot", "slot-1",
                "--owner", "task-a",
                "--repo", "service-a",
                "--branch", "task-a",
                "--pr", "17",
            )

            active = json.loads(self.run_manifest(root, "status", "--slot", "slot-1").stdout)["result"]
            self.assertEqual(active["state"], "active")

            self.run_manifest(root, "release", "--slot", "slot-1", "--owner", "task-a")
            recovered = self.run_manifest(
                root,
                "claim",
                "--slot", "slot-1",
                "--owner", "correction-a",
                "--path", str(path),
                "--preserve-repositories",
            )
            self.assertEqual(
                json.loads(recovered.stdout)["result"]["repositories"]["service-a"],
                {"branch": "task-a", "pr": "17"},
            )
            self.run_manifest(
                root,
                "record",
                "--slot", "slot-1",
                "--owner", "correction-a",
                "--repo", "service-a",
                "--branch", "task-a",
                "--pr", "17",
            )
            corrected = json.loads(
                self.run_manifest(root, "release", "--slot", "slot-1", "--owner", "correction-a").stdout
            )["result"]

            self.assertEqual(corrected["state"], "released")
            self.assertEqual(
                corrected["repositories"]["service-a"],
                {"branch": "task-a", "pr": "17"},
            )

    def test_correction_preserve_requires_released_repository_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "worktrees" / "slot-1"
            missing = self.run_manifest(
                root,
                "claim",
                "--slot", "slot-1",
                "--owner", "correction-a",
                "--path", str(path),
                "--preserve-repositories",
                check=False,
            )

            self.assertEqual(missing.returncode, 2)
            self.assertIn("missing slot", missing.stderr)
            self.assertFalse((root / ".stageflow-worktrees" / "slots.json").exists())

            self.run_manifest(
                root,
                "claim",
                "--slot", "slot-1",
                "--owner", "task-a",
                "--path", str(path),
            )
            active_empty = self.run_manifest(
                root,
                "claim",
                "--slot", "slot-1",
                "--owner", "task-a",
                "--path", str(path),
                "--preserve-repositories",
                check=False,
            )
            self.assertEqual(active_empty.returncode, 2)
            self.assertIn("no repository identity", active_empty.stderr)

            self.run_manifest(root, "release", "--slot", "slot-1", "--owner", "task-a")
            released_empty = self.run_manifest(
                root,
                "claim",
                "--slot", "slot-1",
                "--owner", "correction-a",
                "--path", str(path),
                "--preserve-repositories",
                check=False,
            )
            self.assertEqual(released_empty.returncode, 2)
            self.assertIn("no repository identity", released_empty.stderr)

    def test_legacy_sha_fields_are_read_but_next_record_replaces_them(self) -> None:
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

            status = json.loads(self.run_manifest(root, "status", "--slot", "slot-1").stdout)["result"]
            self.assertEqual(status["repositories"]["service-a"]["head_sha"], "a" * 40)
            updated = self.run_manifest(
                root,
                "record",
                "--slot", "slot-1",
                "--owner", "task-a",
                "--repo", "service-a",
                "--branch", "task-a",
                "--pr", "17",
            )
            self.assertEqual(
                json.loads(updated.stdout)["result"]["repositories"]["service-a"],
                {"branch": "task-a", "pr": "17"},
            )

    def test_released_fixed_slot_rejects_a_different_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = root / "worktrees" / "slot-1"
            replacement = root / "worktrees" / "other-slot"
            self.run_manifest(root, "claim", "--slot", "slot-1", "--owner", "task-a", "--path", str(original))
            self.run_manifest(root, "release", "--slot", "slot-1", "--owner", "task-a")
            result = self.run_manifest(
                root,
                "claim",
                "--slot",
                "slot-1",
                "--owner",
                "task-b",
                "--path",
                str(replacement),
                check=False,
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("fixed slot path mismatch", result.stderr)
            status = json.loads(self.run_manifest(root, "status", "--slot", "slot-1").stdout)["result"]
            self.assertEqual(status["path"], str(original))

    def test_malformed_manifest_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / ".stageflow-worktrees"
            state.mkdir()
            (state / "slots.json").write_text("{broken", encoding="utf-8")
            result = self.run_manifest(root, "status", check=False)

            self.assertEqual(result.returncode, 2)
            self.assertIn("cannot read manifest", result.stderr)


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
