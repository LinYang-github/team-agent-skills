from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "quality_gate",
    ROOT / "scripts" / "quality_gate.py",
)
assert SPEC and SPEC.loader
QUALITY_GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(QUALITY_GATE)
CONFIG = json.loads((ROOT / "quality-gates.json").read_text(encoding="utf-8"))


class QualityGateTests(unittest.TestCase):
    def test_accepts_valid_commit_message(self) -> None:
        self.assertEqual(
            QUALITY_GATE.validate_commit_message(
                "新增(hooks): 增加本地质量门禁\n",
                CONFIG,
            ),
            [],
        )

    def test_rejects_unstructured_commit_message(self) -> None:
        violations = QUALITY_GATE.validate_commit_message("update files\n", CONFIG)
        self.assertTrue(any("提交信息" in item for item in violations))

    def test_accepts_generated_merge_message(self) -> None:
        self.assertEqual(
            QUALITY_GATE.validate_commit_message(
                "Merge branch 'feature/example' into develop\n",
                CONFIG,
            ),
            [],
        )

    def test_validates_branch_names(self) -> None:
        self.assertEqual(
            QUALITY_GATE.validate_branch_name("feature/PROJ-123-local-hooks", CONFIG),
            [],
        )
        self.assertTrue(
            QUALITY_GATE.validate_branch_name("someone/random-work", CONFIG),
        )

    def test_uses_remote_branch_from_pre_push_input(self) -> None:
        line = f"refs/heads/feature/example {'1' * 40} refs/heads/develop {'2' * 40}\n"
        self.assertEqual(QUALITY_GATE.pushed_branches(line), ["develop"])

    def test_blocks_direct_push_to_protected_branch(self) -> None:
        with mock.patch.dict(os.environ, {"QUALITY_GATE_ALLOW_PROTECTED_PUSH": "0"}):
            violations = QUALITY_GATE.validate_push_branches(["develop"], CONFIG)
        self.assertTrue(any("受保护分支" in item for item in violations))

    def test_detects_forbidden_secret_file(self) -> None:
        self.assertTrue(
            QUALITY_GATE.matches_path("config/.env.production", CONFIG["forbidden_file_patterns"]),
        )
        self.assertTrue(
            QUALITY_GATE.matches_path("config/.env.example", CONFIG["allowed_file_patterns"]),
        )

    def test_detects_conflict_marker_and_private_key(self) -> None:
        content = (
            b"<<<<<<< HEAD\n-----BEGIN "
            + b"PRIVATE KEY-----\n=======\n>>>>>>> branch\n"
        )
        violations = QUALITY_GATE.content_violations("src/config.txt", content, CONFIG)
        self.assertTrue(any("冲突标记" in item for item in violations))
        self.assertTrue(any("private key" in item for item in violations))

    def test_detects_remote_frontend_asset(self) -> None:
        content = b'<script src="https://cdn.example.com/app.js"></script>'
        violations = QUALITY_GATE.content_violations("index.html", content, CONFIG)
        self.assertTrue(any("远程资源" in item for item in violations))

    def test_allows_backend_api_url_outside_resource_context(self) -> None:
        content = b'const api = "https://api.example.com/v1"'
        self.assertEqual(
            QUALITY_GATE.content_violations("src/api.ts", content, CONFIG),
            [],
        )

    def test_blocks_destructive_agent_command(self) -> None:
        violations = QUALITY_GATE.validate_agent_command("git reset --hard HEAD~1", CONFIG)
        self.assertTrue(any("高风险操作" in item for item in violations))

    def test_blocks_implicit_push_from_protected_branch(self) -> None:
        violations = QUALITY_GATE.validate_agent_command("git push", CONFIG, "develop")
        self.assertTrue(any("受保护分支" in item for item in violations))

    def test_reads_forbidden_file_from_git_index(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / ".env").write_text("PASSWORD=example\n", encoding="utf-8")
            subprocess.run(["git", "add", "-f", ".env"], cwd=root, check=True)
            violations = QUALITY_GATE.validate_staged_files(root, CONFIG)
        self.assertTrue(any("文件类型禁止提交" in item for item in violations))

    def test_agent_command_cli_strips_argument_separator(self) -> None:
        result = subprocess.run(
            [
                str(ROOT / "scripts" / "run-quality-gate.sh"),
                "agent-command",
                "--",
                "git",
                "reset",
                "--hard",
                "HEAD~1",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("高风险操作", result.stderr)


if __name__ == "__main__":
    unittest.main()
