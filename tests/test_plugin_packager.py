from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PluginPackagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="plugin-packager-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.skill = self.root / "copied skill"
        shutil.copytree(ROOT / "skills" / "plugin-packager", self.skill)
        self.product = self.root / "product release"
        self.output = self.root / "product.zip"
        self.put(".claude-plugin/plugin.json", json.dumps({"name": "product", "version": "1.0.0", "description": "Synthetic product"}))
        self.put("skills/guide/SKILL.md", "---\nname: guide\ndescription: Read the product guide.\n---\n[Usage](references/usage.md)\n")
        self.put("skills/guide/references/usage.md", "Synthetic usage.\n")

    def put(self, name: str, content: str) -> None:
        path = self.product / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def run_packager(self, action: str = "pack") -> tuple[int, dict]:
        command = [sys.executable, "-I", str(self.skill / "scripts" / "plugin_package.py"), action, str(self.product)]
        if action == "pack":
            command.extend(["--output", str(self.output)])
        result = subprocess.run(command, cwd=self.root, capture_output=True, text=True, check=False)
        self.assertEqual(result.stderr, "")
        return result.returncode, json.loads(result.stdout)

    def test_portable_package_preserves_resources_and_checksum(self) -> None:
        self.put("skills/guide/.keep", "hidden resource")
        code, report = self.run_packager()
        self.assertEqual(code, 0)
        self.assertEqual(report["capabilities"], {"skills": ["guide"], "agents": [], "mcp": [], "mcpApps": []})
        self.assertEqual(report["sha256"], hashlib.sha256(self.output.read_bytes()).hexdigest())
        with zipfile.ZipFile(self.output) as archive:
            self.assertIn(".claude-plugin/plugin.json", archive.namelist())
            self.assertEqual(archive.read("skills/guide/.keep"), b"hidden resource")
            self.assertEqual(archive.read("skills/guide/references/usage.md"), b"Synthetic usage.\n")
        self.assertEqual(self.run_packager("validate")[1]["sha256"], report["sha256"])

    def test_mixed_connections_and_required_configuration(self) -> None:
        self.put(".claude-plugin/plugin.json", json.dumps({
            "name": "product", "version": "1.0.0", "description": "Synthetic product",
            "mcpServers": ["./.mcp.json", "./.mcpapps.json"],
            "userConfig": {"token": {"type": "string", "title": "Token", "description": "User-issued token", "required": True, "sensitive": True}},
        }))
        self.put(".mcp.json", json.dumps({"mcpServers": {"api": {"type": "http", "url": "https://example.invalid/api", "headers": {"Authorization": "Bearer ${user_config.token}"}}}}))
        self.put(".mcpapps.json", json.dumps({"mcpServers": {"app": {"command": "python3", "args": ["${CLAUDE_PLUGIN_ROOT}/server.py"]}}}))
        self.put("server.py", "raise RuntimeError('validation must not execute this service')\n")
        code, report = self.run_packager()
        self.assertEqual(code, 0)
        self.assertEqual(report["capabilities"]["mcp"], ["api"])
        self.assertEqual(report["capabilities"]["mcpApps"], ["app"])
        self.assertEqual(report["requiredConfig"], ["token"])

    def test_missing_attachment_does_not_create_archive(self) -> None:
        (self.product / "skills/guide/references/usage.md").unlink()
        code, report = self.run_packager()
        self.assertEqual(code, 1)
        self.assertIn("Missing referenced", report["error"])
        self.assertFalse(self.output.exists())

    def test_rejects_escaping_resource_link(self) -> None:
        self.put("skills/guide/SKILL.md", "---\nname: guide\ndescription: Read guide.\n---\n[Outside](../../../outside.md)\n")
        (self.root / "outside.md").write_text("outside", encoding="utf-8")
        code, report = self.run_packager()
        self.assertEqual(code, 1)
        self.assertIn("escapes", report["error"])
        self.assertFalse(self.output.exists())

    def test_rejects_credential_file_without_echoing_content(self) -> None:
        self.put(".env", "TOKEN=synthetic-private-value\n")
        code, report = self.run_packager()
        self.assertEqual(code, 1)
        self.assertIn("credential file", report["error"])
        self.assertNotIn("synthetic-private-value", json.dumps(report))
        self.assertFalse(self.output.exists())

    def test_existing_release_is_not_overwritten(self) -> None:
        self.assertEqual(self.run_packager()[0], 0)
        original = self.output.read_bytes()
        self.put("skills/guide/references/usage.md", "Changed usage.\n")
        self.assertEqual(self.run_packager()[0], 1)
        self.assertEqual(self.output.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
