from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]


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
        shutil.copytree(SOURCE_ROOT / "workspace-template", self.root)
        shutil.copytree(SOURCE_ROOT / ".agents", self.root / ".agents")
        (self.root / ".codex/agents").mkdir(parents=True)
        shutil.copytree(
            SOURCE_ROOT / ".codex/agents",
            self.root / ".codex/agents",
            dirs_exist_ok=True,
        )
        shutil.copytree(SOURCE_ROOT / "tools", self.root / "tools")
        empty_template = Path(self.temp_dir.name) / "empty-git-template"
        empty_template.mkdir()
        run(self.root, "git", "init", "--template", str(empty_template), "-b", "main")
        run(self.root, "git", "config", "user.name", "Workspace Test")
        run(self.root, "git", "config", "user.email", "workspace-test@example.invalid")
        run(self.root, "git", "config", "commit.gpgsign", "false")
        run(self.root, "git", "config", "core.hooksPath", ".git/disabled-hooks")
        run(self.root, "git", "add", "-f", ".")
        run(self.root, "git", "commit", "--no-verify", "-m", "ops: seed workspace")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

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
