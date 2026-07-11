from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK_PATH = ROOT / "workspace-template/.codex/hooks/session_start_memory.py"


def load_hook() -> object:
    spec = importlib.util.spec_from_file_location("session_start_memory", HOOK_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load SessionStart hook.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SessionStartHookTests(unittest.TestCase):
    def test_read_limited_rejects_symlink_outside_workspace(self) -> None:
        hook = load_hook()
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "workspace"
            root.mkdir()
            outside = base / "outside.txt"
            outside.write_text("must not be loaded", encoding="utf-8")
            link = root / "CURRENT.md"
            try:
                link.symlink_to(outside)
            except OSError as error:
                self.skipTest(f"symlink unavailable: {error}")
            result = hook.read_limited(link, 100, root)  # type: ignore[attr-defined]
            self.assertEqual(result, "")

    def test_read_limited_caps_context(self) -> None:
        hook = load_hook()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            current = root / "CURRENT.md"
            current.write_text("x" * 20, encoding="utf-8")
            result = hook.read_limited(current, 5, root)  # type: ignore[attr-defined]
            self.assertEqual(result, "xxxxx\n...[truncated by SessionStart hook]")


if __name__ == "__main__":
    unittest.main()
