from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts import build_release

SOURCE_ROOT = Path(__file__).resolve().parents[1]
SOURCE_VERSION = json.loads((SOURCE_ROOT / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8"))[
    "version"
]


def run(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=root,
        check=check,
        text=True,
        capture_output=True,
    )


class WorkspaceLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        if shutil.which("git") is None:
            self.skipTest("git is required for lifecycle tests")
        temp_base = Path(tempfile.gettempdir()).resolve()
        try:
            temp_base.relative_to(SOURCE_ROOT)
        except ValueError:
            safe_temp_base: Path | None = None
        else:
            safe_temp_base = SOURCE_ROOT.parent
        self.temp_dir = tempfile.TemporaryDirectory(
            prefix="minius-workspace-test-",
            dir=safe_temp_base,
        )
        self.root = Path(self.temp_dir.name) / "workspace"
        self._extract_workspace(self.root)
        initialized = run(
            self.root,
            sys.executable,
            "scripts/init_workspace.py",
            "--memory-mode",
            "local-git",
            "--git-name",
            "Workspace Test",
            "--git-email",
            "workspace-test@example.invalid",
        )
        self.assertIn("initialized:", initialized.stdout)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _extract_workspace(self, target: Path) -> None:
        output = Path(self.temp_dir.name) / "release"
        result = build_release.build_release(
            SOURCE_ROOT,
            output,
            version=SOURCE_VERSION,
            run_external_checks=False,
        )
        target.mkdir(parents=True)
        with zipfile.ZipFile(result.archive) as archive:
            archive.extractall(target)

    def test_init_creates_standalone_main_without_remote(self) -> None:
        self.assertEqual(run(self.root, "git", "branch", "--show-current").stdout.strip(), "main")
        self.assertEqual(run(self.root, "git", "rev-list", "--count", "HEAD").stdout.strip(), "1")
        self.assertEqual(run(self.root, "git", "remote").stdout.strip(), "")
        self.assertEqual(
            run(self.root, "git", "config", "--local", "--get", "minius.memoryMode").stdout.strip(),
            "local-git",
        )
        self.assertEqual(run(self.root, "git", "status", "--porcelain").stdout.strip(), "")

    def test_init_is_idempotent(self) -> None:
        before = run(self.root, "git", "rev-parse", "HEAD").stdout.strip()
        repeated = run(
            self.root,
            sys.executable,
            "scripts/init_workspace.py",
            "--memory-mode",
            "local-git",
        )
        self.assertIn("already initialized:", repeated.stdout)
        self.assertEqual(run(self.root, "git", "rev-parse", "HEAD").stdout.strip(), before)

    def test_init_refuses_parent_repository(self) -> None:
        parent = Path(self.temp_dir.name) / "parent-repository"
        parent.mkdir()
        run(parent, "git", "init", "-b", "main")
        nested = parent / "workspace"
        self._extract_workspace(nested)
        blocked = run(
            nested,
            sys.executable,
            "scripts/init_workspace.py",
            "--git-name",
            "Workspace Test",
            "--git-email",
            "workspace-test@example.invalid",
            check=False,
        )
        self.assertEqual(blocked.returncode, 1)
        self.assertIn("inside another Git repository", blocked.stderr)
        self.assertFalse((nested / ".git").exists())

    def test_private_approved_requires_acknowledgment(self) -> None:
        candidate = Path(self.temp_dir.name) / "private-candidate"
        self._extract_workspace(candidate)
        blocked = run(
            candidate,
            sys.executable,
            "scripts/init_workspace.py",
            "--memory-mode",
            "private-approved",
            "--git-name",
            "Workspace Test",
            "--git-email",
            "workspace-test@example.invalid",
            check=False,
        )
        self.assertEqual(blocked.returncode, 1)
        self.assertIn("--acknowledge-private-approved", blocked.stderr)
        self.assertFalse((candidate / ".git").exists())

    def test_local_git_mode_tracks_new_matter_after_explicit_add(self) -> None:
        candidate = Path(self.temp_dir.name) / "local-git-candidate"
        self._extract_workspace(candidate)
        run(
            candidate,
            sys.executable,
            "scripts/init_workspace.py",
            "--memory-mode",
            "local-git",
            "--git-name",
            "Workspace Test",
            "--git-email",
            "workspace-test@example.invalid",
        )
        run(
            candidate,
            sys.executable,
            "scripts/new_matter.py",
            "--id",
            "synthetic-local",
            "--title",
            "Synthetic local matter",
            "--classification",
            "PUBLIC",
        )
        status = run(candidate, "git", "status", "--porcelain").stdout
        self.assertIn("matters/synthetic-local/", status)
        self.assertIn("memory/CURRENT.md", status)

    def test_untracked_mode_keeps_synthetic_lifecycle_out_of_git(self) -> None:
        candidate = Path(self.temp_dir.name) / "untracked-candidate"
        self._extract_workspace(candidate)
        run(
            candidate,
            sys.executable,
            "scripts/init_workspace.py",
            "--memory-mode",
            "untracked",
            "--git-name",
            "Workspace Test",
            "--git-email",
            "workspace-test@example.invalid",
        )
        run(
            candidate,
            sys.executable,
            "scripts/new_matter.py",
            "--id",
            "synthetic-untracked",
            "--title",
            "Synthetic untracked matter",
            "--classification",
            "PUBLIC",
        )
        self.assertEqual(run(candidate, "git", "status", "--porcelain").stdout.strip(), "")
        blocked_worktree = run(
            candidate,
            sys.executable,
            "scripts/start_session.py",
            "--slug",
            "worktree-check",
            "--matter",
            "synthetic-untracked",
            "--worktree",
            str(Path(self.temp_dir.name) / "untracked-worktree"),
            check=False,
        )
        self.assertEqual(blocked_worktree.returncode, 1)
        self.assertIn("requires local-git or private-approved", blocked_worktree.stderr)
        started = run(
            candidate,
            sys.executable,
            "scripts/start_session.py",
            "--slug",
            "local-branch",
            "--matter",
            "synthetic-untracked",
            "--create-branch",
        )
        self.assertIn("Git mode: untracked", started.stdout)
        self.assertEqual(run(candidate, "git", "status", "--porcelain").stdout.strip(), "")

    def create_committed_matter(self, matter_id: str = "2026-001") -> None:
        result = run(
            self.root,
            "python3",
            "scripts/new_matter.py",
            "--id",
            matter_id,
            "--title",
            "Тестове питання",
            "--classification",
            "INTERNAL",
        )
        self.assertIn("created matter", result.stdout)
        run(self.root, "git", "add", "-f", "matters", "memory")
        run(
            self.root,
            "git",
            "commit",
            "--no-verify",
            "-m",
            f"matter: initialize {matter_id}",
        )

    def test_branch_session_roundtrip_preserves_metadata(self) -> None:
        self.create_committed_matter()
        start = run(
            self.root,
            "python3",
            "scripts/start_session.py",
            "--slug",
            "first-review",
            "--matter",
            "2026-001",
            "--objective",
            "Проверить lifecycle",
            "--create-branch",
        )
        session_id = next(
            line.split(":", 1)[1].strip()
            for line in start.stdout.splitlines()
            if line.startswith("session:")
        )
        branch = run(self.root, "git", "branch", "--show-current").stdout.strip()
        self.assertEqual(branch, "session/" + session_id[:8] + "-first-review")

        finish = run(
            self.root,
            "python3",
            "scripts/finish_session.py",
            "--session",
            session_id,
            "--summary",
            "Lifecycle проверен.",
            "--next-action",
            "Продолжить исследование.",
            "--tests",
            "Smoke test passed.",
        )
        self.assertIn("No commit or push was executed.", finish.stdout)

        session_path = self.root / "memory/sessions" / f"{session_id}.md"
        text = session_path.read_text(encoding="utf-8")
        self.assertIn(f"- **Branch:** {branch}", text)
        self.assertIn("- **Ended (UTC):** 20", text)
        self.assertIn("Lifecycle проверен.", text)
        self.assertIn("active_sessions: []", (self.root / "memory/index.yaml").read_text())
        current = (self.root / "memory/CURRENT.md").read_text(encoding="utf-8")
        self.assertIn(f"**Session:** `{session_id}`", current)
        self.assertNotIn(f"`{session_id}` — `{branch}`", current)

    def test_parallel_worktree_gets_own_session_memory(self) -> None:
        self.create_committed_matter("2026-002")
        worktree = Path(self.temp_dir.name) / "parallel-worktree"
        start = run(
            self.root,
            "python3",
            "scripts/start_session.py",
            "--slug",
            "case-law",
            "--matter",
            "2026-002",
            "--worktree",
            str(worktree),
        )
        self.assertTrue(worktree.is_dir())
        self.assertEqual(run(self.root, "git", "branch", "--show-current").stdout.strip(), "main")
        self.assertEqual(
            run(worktree, "git", "branch", "--show-current").stdout.strip(),
            "session/"
            + next(
                line.split(":", 1)[1].strip()[:8]
                for line in start.stdout.splitlines()
                if line.startswith("session:")
            )
            + "-case-law",
        )
        logs = list((worktree / "memory/sessions").glob("*--case-law.md"))
        self.assertEqual(len(logs), 1)
        self.assertIn(str(worktree), logs[0].read_text(encoding="utf-8"))

    def test_finish_session_rejects_arbitrary_workspace_file(self) -> None:
        agents_path = self.root / "AGENTS.md"
        before = agents_path.read_bytes()
        result = run(
            self.root,
            "python3",
            "scripts/finish_session.py",
            "--session",
            "AGENTS.md",
            "--summary",
            "Must not be written.",
            "--next-action",
            "None.",
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(agents_path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
