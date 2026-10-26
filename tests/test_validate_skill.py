"""Exercise validation in a standalone copy with controlled tool availability."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class StandaloneValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "repo"
        shutil.copytree(ROOT, self.root, symlinks=True, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        self.bin = Path(self.temp.name) / "bin"
        self.bin.mkdir()
        self.log = Path(self.temp.name) / "calls"
        self.defs = Path(self.temp.name) / "definitions.luau"
        self.defs.write_text("-- stub\n")

    def tool(self, name, status=0):
        executable = self.bin / name
        executable.write_text(f'#!/bin/sh\nprintf "%s\\n" "{name}" >> "$TEST_CALLS"\nexit {status}\n')
        executable.chmod(0o755)

    def run_validator(self, definitions=True):
        env = os.environ.copy()
        env.update(PATH=str(self.bin), TEST_CALLS=str(self.log))
        env.pop("ROBLOX_LUAU_DEFINITIONS", None)
        if definitions:
            env["ROBLOX_LUAU_DEFINITIONS"] = str(self.defs)
        return subprocess.run(
            [sys.executable, str(self.root / "tests/validate_skill.py")],
            cwd=self.root, env=env, capture_output=True, text=True,
        )

    def calls(self):
        return self.log.read_text().splitlines() if self.log.exists() else []

    def test_standalone_with_all_tools_and_definitions_passes(self):
        for name in ("stylua", "selene", "luau-lsp"):
            self.tool(name)
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(len(self.calls()), 15)
        self.assertIn("passed all validation checks", result.stdout)

    def test_missing_tool_and_definitions_are_incomplete_but_other_tools_run(self):
        self.tool("stylua")
        self.tool("luau-lsp")
        result = self.run_validator(definitions=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("selene not found", result.stdout)
        self.assertIn("Roblox definitions missing", result.stdout)
        self.assertNotIn("passed all validation checks", result.stdout)
        self.assertEqual(self.calls(), ["stylua"] * 5)

    def test_tool_failure_propagates_without_skipping_other_tools(self):
        self.tool("stylua", status=7)
        self.tool("selene")
        self.tool("luau-lsp")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("stylua probe 1: exit 7", result.stdout)
        self.assertEqual(len(self.calls()), 15)
        self.assertNotIn("passed all validation checks", result.stdout)


if __name__ == "__main__":
    unittest.main()
