from __future__ import annotations

import importlib.util
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SH = shutil.which("sh") or "sh"
RULES = ROOT / "hooks/lib/git-rules.sh"
INSTALL = ROOT / "hooks/lib/install-git-hooks.sh"
SPEC = importlib.util.spec_from_file_location("git_rules_quality_gate", ROOT / "scripts/quality_gate.py")
assert SPEC and SPEC.loader
QUALITY_GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(QUALITY_GATE)
GEN_SPEC = importlib.util.spec_from_file_location("generate_git_rules", ROOT / "scripts/generate-git-rules.py")
assert GEN_SPEC and GEN_SPEC.loader
GENERATOR = importlib.util.module_from_spec(GEN_SPEC)
GEN_SPEC.loader.exec_module(GENERATOR)
CONFIG = json.loads((ROOT / "quality-gates.json").read_text(encoding="utf-8"))
PLUGIN_VERSION = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))["version"]


class ShellRulesTests(unittest.TestCase):
    def setUp(self) -> None:
        # Keep every test artifact in this worktree; never install into a real home.
        self.temp = tempfile.TemporaryDirectory(prefix="git-rules-test-", dir=ROOT)
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull,
                    "GIT_CONFIG_NOSYSTEM": "1", "TMPDIR": str(self.work),
                    "QUALITY_GATE_ALLOW_PROTECTED_PUSH": "0"}
        for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR"):
            self.env.pop(name, None)

    def run_sh(self, *args: str, stdin: str = "", cwd: Path | None = None,
               env: dict | None = None) -> subprocess.CompletedProcess:
        return subprocess.run([SH, *map(str, args)], input=stdin, cwd=cwd or self.work,
                              env=env or self.env, capture_output=True, text=True,
                              encoding="utf-8", timeout=30)

    def git(self, repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", str(repo), *args], env=self.env,
                              capture_output=True, text=True, encoding="utf-8",
                              check=check, timeout=30)

    def repository(self, name: str = "repo with spaces") -> Path:
        repo = self.work / name
        repo.mkdir()
        self.git(repo, "init", "-q")
        self.git(repo, "config", "user.name", "Team Test")
        self.git(repo, "config", "user.email", "test@example.invalid")
        self.git(repo, "config", "commit.gpgsign", "false")
        self.git(repo, "checkout", "-q", "-b", "feature/test-hooks")
        return repo

    def test_branch_parity(self) -> None:
        branches = ["main", "develop", "master", "", "feature/a", "feature/abc-def",
                    "feature/PROJ-123-add-login", "fix/p9-0-a", "refactor/ab-123-a0",
                    "docs/api", "test/a1", "chore/9", "release/v1.0.0", "hotfix/1.0-rc_1",
                    "release/A", "hotfix/x..", "feature/中文", "feature/Upper", "Feature/a",
                    "feature/a_b", "feature/a.b", "feature/-a", "feature/a-", "feature/a--b",
                    "feature/a/b", "feature/123-a", "feature/PROJ-123", "feature/PROJ-123-A",
                    "fix/ABC_DEF-1-test", "fix/A-1-test", "fix/1A-1-test", "fix/A1-12-test",
                    "fix/a-01-test", "feature/", "/feature/a", "release/", "hotfix/_x",
                    "hotfix/.x", "release/a/b", "feature/a\n", "feature/a\nbad", "main\nbad",
                    "develop ", " feature/a", "feature/é", "release/É", "-bad", "feature/" + "a" * 100]
        self.assertGreaterEqual(len(branches), 40)
        for branch in branches:
            with self.subTest(branch=branch):
                expected = 2 if QUALITY_GATE.validate_branch_name(branch, CONFIG) else 0
                result = self.run_sh(RULES, "branch", branch)
                self.assertEqual(result.returncode, expected, result.stderr)

    def test_commit_parity(self) -> None:
        messages = ["", "\n", "# comment", "# comment\n\n", "new files", "新增: 你好",
                    "新增(api): 支持登录", "修复(api)!: 修复登录", "规范!: 统一代码规范",
                    "新增: 好", "新增: a", "新增: ab", "新增:  a", "新增: ab  ",
                    "新增:ab", "新增： 你好", "feat: add login", "新增(): 支持登录",
                    "新增(a)b): 支持登录", "新增(a(b): 支持登录", "新增( 范围 ): 支持登录",
                    "新增!!: 支持登录", "新增!: 支持登录", " 新增: 支持登录 ",
                    "\n#comment\n新增: 支持登录\n\nbody", " #comment\n新增: 支持登录",
                    "#comment\ninvalid\n新增: 支持登录", "新增: 支持登录\r\nbody",
                    "新增:\t支持登录", "新增:\u00a0支持登录", "\u3000新增: 支持登录\u3000",
                    "新增: \u200b好", "新增: a\u001fb", "新增:\u001f支持登录",
                    "新增:\u2003支持登录", "新增: 😀😀", "新增: e\u0301",
                    "新增: " + "中" * 67, "新增: " + "中" * 68, "新增: " + "中" * 69,
                    "新增: " + "a" * 68, "新增: " + "a" * 69,
                    "修复(范围): " + "中" * 64, "修复(范围): " + "中" * 65,
                    "新增: 好\n新增: 支持登录", "MERGE branch", "Merge", "Revert", "fixup!", "合并:"]
        messages += ["新增: a\0b", "新增(\0): 支持登录", "新增: " + "中" * 67 + "\0",
                     "新增: " + "中" * 68 + "\0"]
        messages += [prefix + "长" * 100 for prefix in ("Merge ", "Revert ", "fixup! ", "squash! ", "合并:")]
        messages += [sep + "新增: 支持登录" for sep in ("\v", "\f", "\x1c", "\x1d", "\x1e", "\x85", "\u2028", "\u2029")]
        messages += [f"{t}: 支持登录" for t in CONFIG["commit_types"]]
        message_file = self.work / "message.txt"
        self.assertGreaterEqual(len(messages), 40)
        for message in messages:
            with self.subTest(message=message):
                message_file.write_bytes(message.encode("utf-8"))
                expected = 2 if QUALITY_GATE.validate_commit_message(message, CONFIG) else 0
                result = self.run_sh(RULES, "commit-msg", message_file)
                self.assertEqual(result.returncode, expected, result.stderr)

    def test_push_parity_and_remote_destination(self) -> None:
        lines = [f"refs/heads/feature/valid {'1' * 40} refs/heads/{b} {'2' * 40}\n"
                 for b in ("main", "develop", "feature/valid", "bad", "fix/PROJ-1-abc", "release/1.0")]
        lines += [f"(delete) {'0' * 40} refs/heads/main {'2' * 40}\n",
                  f"refs/tags/v1 {'1' * 40} refs/tags/v1 {'0' * 40}\n",
                  "malformed\n", lines[2].rstrip(), "".join(lines), lines[2] + lines[0],
                  lines[0].replace(" ", "\u2003"), lines[0].replace("\n", "\r\n"),
                  lines[0].replace("refs/heads/feature/valid", "bad\u00a0ref"),
                  lines[0].replace("refs/heads/main", "refs/hea\0ds/main")]
        for allow in ("0", "1"):
            for data in lines:
                with self.subTest(data=data, allow=allow):
                    with mock.patch.dict(os.environ, {"QUALITY_GATE_ALLOW_PROTECTED_PUSH": allow}):
                        expected = bool(QUALITY_GATE.validate_push_branches(QUALITY_GATE.pushed_branches(data), CONFIG))
                    result = self.run_sh(RULES, "pre-push", stdin=data,
                                         env={**self.env, "QUALITY_GATE_ALLOW_PROTECTED_PUSH": allow})
                    self.assertEqual(result.returncode, 2 if expected else 0, result.stderr)

    def agent(self, command: str, repo: Path | None = None, *, camel: bool = False,
              env: dict | None = None) -> subprocess.CompletedProcess:
        payload = {"hook_event_name": "PreToolUse", "tool_name": "Bash",
                   "cwd": str(repo or self.work),
                   "toolInput" if camel else "tool_input": {"command": command}}
        return self.run_sh(RULES, "agent-command", stdin=json.dumps(payload), env=env)

    def test_agent_commands_both_protocols(self) -> None:
        cases = [
            ("git checkout -b bad", 2), ("git checkout -B Bad", 2),
            ("git checkout -b feature/good", 0), ("git checkout -bfix/good", 0),
            ("git switch -c BAD", 2), ("git switch -C BAD", 2),
            ("git switch --create wrong", 2), ("git switch --create=feature/good", 0),
            ("git switch --force-create=wrong", 2), ("git branch wrong", 2),
            ("git branch feature/good HEAD", 0), ("git branch --list wrong", 0),
            ("git branch -d wrong", 0), ("git checkout main", 0),
            ('git commit -m "新增(认证): 支持中文登录"', 0),
            ('git commit --message="修复: 修复登录"', 0),
            ('git commit -am "修复: 修复登录"', 0), ('git commit -am bad', 2),
            ('git commit -m "新增: 支持 \\\"引号\\\" 和中文"', 0),
            ("git commit -m '新增: 支持 && 引号'", 0),
            ("git commit -m 'Merge branch foo'", 0),
            ("git commit -m bad", 2), ("git commit --message bad", 2),
            ("git status && git commit -m 'bad'", 2),
            ("git commit -m '新增: 支持登录' && git switch -c Bad", 2),
            ("git commit -m '新增: 支持登录' -m 'body'", 0),
            ("git push origin main", 2), ("git push origin develop", 2),
            ("git push origin HEAD:main", 2), ("git push origin HEAD:refs/heads/develop", 2),
            ("git push origin +HEAD:main", 2), ("git push origin feature/good", 0),
            ("git push origin :main", 0), ("git push --delete origin main", 0),
            ('echo "git push origin main"', 0), ('echo "git checkout -b bad"', 0),
            ("git status; git checkout -b bad", 2),
            ("git status\ngit switch -c bad", 2),
            ("sh -c 'git switch -c bad'", 2), ("command git branch bad", 2),
            ("echo ok # git branch bad", 0), ("git status", 0), ("ls -la", 0),
        ]
        for camel in (False, True):
            for command, expected in cases:
                with self.subTest(command=command, camel=camel):
                    result = self.agent(command, camel=camel)
                    self.assertEqual(result.returncode, expected, result.stderr)

    def test_agent_implicit_push_workdir_and_configured_destination(self) -> None:
        repo = self.repository()
        self.git(repo, "commit", "--allow-empty", "-m", "测试: 创建初始提交")
        self.git(repo, "checkout", "-q", "-B", "main")
        self.assertEqual(self.agent("git push", repo).returncode, 2)
        self.assertEqual(self.agent("git push origin HEAD", repo).returncode, 2)
        self.assertEqual(self.agent("git push --all origin", repo).returncode, 2)
        self.assertEqual(self.agent("git push --tags origin", repo).returncode, 0)
        self.assertEqual(self.agent("git push", repo, env={**self.env, "QUALITY_GATE_ALLOW_PROTECTED_PUSH": "1"}).returncode, 0)
        self.git(repo, "checkout", "-q", "-B", "feature/good")
        self.git(repo, "config", "remote.origin.push", "HEAD:refs/heads/develop")
        self.assertEqual(self.agent("git push origin", repo).returncode, 2)
        self.assertEqual(self.agent("git push", repo).returncode, 2)
        payload = {"tool_input": {"cmd": "git push origin main", "workdir": str(repo)}}
        self.assertEqual(self.run_sh(RULES, "agent-command", stdin=json.dumps(payload)).returncode, 2)
        self.assertEqual(self.agent(f'git -C "{repo}" push origin main').returncode, 2)

    def test_agent_invalid_json_is_configuration_error(self) -> None:
        result = self.run_sh(RULES, "agent-command", stdin="not JSON")
        self.assertEqual(result.returncode, 1)
        self.assertIn("JSON", result.stderr)
        self.assertIn("无效", result.stderr)
        result = self.run_sh(RULES, "agent-command", stdin='{"tool_input": "invalid"}')
        self.assertEqual(result.returncode, 1)

    def test_no_perl_fails_open_but_git_rules_still_enforce(self) -> None:
        tools = self.work / "path without perl"
        tools.mkdir()
        for name in ("dirname", "wc", "tr", "grep", "sed"):
            (tools / name).symlink_to(shutil.which(name))
        env = {**self.env, "PATH": str(tools)}
        result = self.agent("git commit -m bad", env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("未找到 Perl", result.stderr)
        message = self.work / "bad-message"
        message.write_text("bad", encoding="utf-8")
        self.assertEqual(self.run_sh(RULES, "commit-msg", message, env=env).returncode, 2)

    def test_install_commit_push_uninstall(self) -> None:
        repo = self.repository()
        cache = self.work / "plugin cache"
        shutil.copytree(ROOT / "hooks", cache / "hooks")
        shutil.copyfile(ROOT / "package.json", cache / "package.json")
        result = self.run_sh(cache / "hooks/lib/install-git-hooks.sh", repo)
        self.assertEqual(result.returncode, 0, result.stderr)
        shutil.rmtree(cache)
        hooks = repo / ".git/hooks"
        self.assertEqual((hooks / ".team-standards-version").read_text().strip(), PLUGIN_VERSION)
        # Removing the plugin source after installation must not break installed hooks.
        installed = (hooks / "commit-msg").read_text()
        self.assertNotIn(str(ROOT), installed)
        bad = self.git(repo, "commit", "--allow-empty", "-m", "bad", check=False)
        self.assertNotEqual(bad.returncode, 0)
        self.assertIn("提交信息", bad.stderr)
        good = self.git(repo, "commit", "--allow-empty", "-m", "测试: 验证独立钩子", check=False)
        self.assertEqual(good.returncode, 0, good.stderr)
        remote = self.work / "remote.git"
        subprocess.run(["git", "init", "--bare", "-q", str(remote)], env=self.env, check=True)
        self.git(repo, "remote", "add", "origin", str(remote))
        blocked = self.git(repo, "push", "origin", "HEAD:main", check=False)
        self.assertNotEqual(blocked.returncode, 0)
        self.assertIn("受保护分支", blocked.stderr)
        self.assertEqual(self.git(repo, "push", "origin", "HEAD:feature/good", check=False).returncode, 0)
        self.assertEqual(self.run_sh(INSTALL, repo).returncode, 0)
        unrelated = hooks / "pre-commit"
        unrelated.write_text("# unrelated\n")
        result = self.run_sh(INSTALL, "--uninstall", repo)
        self.assertEqual(result.returncode, 0, result.stderr)
        for name in ("commit-msg", "pre-push", ".team-standards-version", "team-standards"):
            self.assertFalse((hooks / name).exists())
        self.assertTrue(unrelated.exists())
        self.assertEqual(self.git(repo, "commit", "--allow-empty", "-m", "bad", check=False).returncode, 0)

    def test_install_refuses_foreign_library_and_symlink(self) -> None:
        repo = self.repository()
        hooks = repo / ".git/hooks"
        library = hooks / "team-standards"
        library.mkdir()
        (library / "user-file").write_text("keep")
        result = self.run_sh(INSTALL, repo)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((library / "user-file").read_text(), "keep")
        shutil.rmtree(library)
        target = self.work / "user-hook"
        target.write_text("keep")
        (hooks / "commit-msg").symlink_to(target)
        result = self.run_sh(INSTALL, repo)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(target.read_text(), "keep")

    def test_shell_syntax_and_configuration_errors(self) -> None:
        for path in (RULES, INSTALL, ROOT / "hooks/agent-command", ROOT / "hooks/session-start", ROOT / "hooks/run-hook.cmd"):
            with self.subTest(path=path):
                result = self.run_sh("-n", path)
                self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.run_sh(RULES, "unknown").returncode, 1)
        self.assertEqual(self.run_sh(RULES, "commit-msg", self.work / "missing").returncode, 1)

    def test_husky_and_existing_hooks_are_never_overwritten(self) -> None:
        repo = self.repository()
        self.git(repo, "config", "core.hooksPath", ".husky/_")
        result = self.run_sh(INSTALL, repo)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("core.hooksPath", result.stderr)
        self.assertFalse((repo / ".git/hooks/commit-msg").exists())
        self.git(repo, "config", "--unset", "core.hooksPath")
        original = repo / ".git/hooks/pre-push"
        original.write_text("#!/bin/sh\necho custom\n")
        for args in ((repo,), ("--uninstall", repo)):
            result = self.run_sh(INSTALL, *args)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(original.read_text(), "#!/bin/sh\necho custom\n")
            self.assertFalse((repo / ".git/hooks/commit-msg").exists())

    def test_session_start_silent_outside_repo_and_syncs_only_older(self) -> None:
        outside = self.work / "outside"
        outside.mkdir()
        # A directory inside the worktree is still a Git directory; set ceiling.
        env = {**self.env, "GIT_CEILING_DIRECTORIES": str(self.work)}
        result = self.run_sh(ROOT / "hooks/session-start", cwd=outside, env=env)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""))
        repo = self.repository()
        result = self.run_sh(ROOT / "hooks/session-start", cwd=repo)
        self.assertEqual(len(result.stdout.splitlines()), 1)
        self.assertIn("install-git-hooks.sh", result.stdout)
        # 提示只能请模型转告用户，不能让模型自行安装。
        self.assertIn("未经用户明确同意，不要自行执行", result.stdout)
        self.assertEqual(self.run_sh(INSTALL, repo).returncode, 0)
        marker = repo / ".git/hooks/.team-standards-version"
        for version, expected in (("0.0.0", PLUGIN_VERSION), (PLUGIN_VERSION, PLUGIN_VERSION), ("999.0.0", "999.0.0")):
            marker.write_text(version + "\n")
            result = self.run_sh(ROOT / "hooks/session-start", cwd=repo)
            self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""))
            self.assertEqual(marker.read_text().strip(), expected)

    def test_generated_rules_are_current(self) -> None:
        output = self.work / "generated.sh"
        result = subprocess.run([sys.executable, str(ROOT / "scripts/generate-git-rules.py"), "--output", str(output)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(output.read_bytes(), (ROOT / "hooks/lib/rules.generated.sh").read_bytes())

    def test_generator_rejects_non_ere_patterns(self) -> None:
        for pattern in (r"^feature/\w+$", r"^(?=feature/).*$", r"^a+?$", r"^(a)\1$", r"^a++$", r"^\Afoo$", r"[[:alpha:]]", r"^a{,3}$", r"^a{256}$"):
            with self.subTest(pattern=pattern), self.assertRaises((ValueError, re.error)):
                GENERATOR.posix_ere(pattern)

    def test_manifest_versions_and_paths(self) -> None:
        versions = []
        for filename in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json", "package.json"):
            manifest = json.loads((ROOT / filename).read_text())
            self.assertEqual(manifest["name"], "team-standards")
            versions.append(manifest["version"])
            if filename != "package.json":
                self.assertEqual(manifest["skills"], "./skills/")
                self.assertEqual(manifest["hooks"], "./hooks/hooks.json")
        for filename in (".agents/plugins/marketplace.json", ".claude-plugin/marketplace.json"):
            manifest = json.loads((ROOT / filename).read_text())
            self.assertEqual(manifest["name"], "team-agent-skills")
            entry, = manifest["plugins"]
            self.assertEqual(entry["name"], "team-standards")
            source = entry["source"]
            self.assertEqual(source["url"] if isinstance(source, dict) else source, "./")
            versions.append(entry["version"])
        self.assertRegex(PLUGIN_VERSION, r"^[0-9]+\.[0-9]+\.[0-9]+$")
        self.assertEqual(set(versions), {PLUGIN_VERSION})
        package = json.loads((ROOT / "package.json").read_text())
        self.assertTrue(package["private"])
        self.assertNotIn("scripts", package)

    def test_polyglot_entry_preserves_blocking_exit(self) -> None:
        payload = json.dumps({"tool_input": {"command": "git switch -c bad"}})
        result = self.run_sh(ROOT / "hooks/run-hook.cmd", "agent-command", stdin=payload)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("分支名", result.stderr)



class PluginVersionBumpTests(unittest.TestCase):
    """scripts/check-plugin-version-bump.sh：改了钩子复制文件就必须升版本号。"""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        # 在 pre-push 等 Git 钩子里运行时会继承 GIT_DIR 等变量，必须清掉，
        # 否则测试提交会写进真实仓库。
        self.env = {k: v for k, v in os.environ.items()
                    if k not in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR")}
        self.env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        script_dir = self.repo / "scripts"
        script_dir.mkdir()
        shutil.copy(ROOT / "scripts" / "check-plugin-version-bump.sh", script_dir)
        (self.repo / "hooks" / "lib").mkdir(parents=True)
        self.write_version("0.1.0")
        (self.repo / "hooks" / "lib" / "git-rules.sh").write_text("v1\n")
        self.git("init", "-q", "-b", "develop")
        self.git("add", "-A")
        self.git("commit", "-qm", "base")
        self.git("update-ref", "refs/remotes/origin/develop", "HEAD")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def git(self, *args: str) -> None:
        subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "core.hooksPath=/dev/null", *args],
            cwd=self.repo, env=self.env, check=True, capture_output=True,
        )

    def write_version(self, version: str) -> None:
        (self.repo / "package.json").write_text('{\n  "name": "team-standards",\n  "version": "%s"\n}\n' % version)

    def check(self) -> subprocess.CompletedProcess:
        return subprocess.run(["sh", "scripts/check-plugin-version-bump.sh"], cwd=self.repo,
                              env=self.env, capture_output=True, encoding="utf-8", errors="replace")

    def commit_change(self, path: str) -> None:
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("changed\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "change")

    def test_rejects_hook_change_without_version_bump(self) -> None:
        self.commit_change("hooks/lib/git-rules.sh")
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("hooks/lib/git-rules.sh", result.stderr)

    def test_accepts_hook_change_with_version_bump(self) -> None:
        self.write_version("0.1.1")
        self.commit_change("hooks/lib/git-rules.sh")
        self.assertEqual(self.check().returncode, 0)

    def test_rejects_rules_config_change_without_bump(self) -> None:
        self.commit_change("quality-gates.json")
        self.assertEqual(self.check().returncode, 1)

    def test_ignores_unrelated_change(self) -> None:
        self.commit_change("skills/demo/SKILL.md")
        self.assertEqual(self.check().returncode, 0)

    def test_skips_without_base_ref(self) -> None:
        self.git("update-ref", "-d", "refs/remotes/origin/develop")
        result = self.check()
        self.assertEqual(result.returncode, 0)
        self.assertIn("跳过", result.stderr)


if __name__ == "__main__":
    unittest.main()
