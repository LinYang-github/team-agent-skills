#!/usr/bin/env python3
"""Run deterministic local quality gates shared by Agent and Git hooks."""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any

CONFIG_NAME = "quality-gates.json"
ZERO_SHA = "0" * 40
REMOTE_ASSET_CONTEXT = re.compile(
    r"(?:\b(?:src|href)\s*=|\burl\s*\(|@import\b)[^\n]*?(https?://[^\s\"')>]+)",
    re.IGNORECASE,
)
CONFLICT_MARKER = re.compile(r"^(?:<<<<<<< .+|=======|>>>>>>> .+)$", re.MULTILINE)


def error(message: str) -> None:
    print(f"[ERROR] {message}", file=sys.stderr)


def info(message: str) -> None:
    print(f"[PASS] {message}")


def git(root: Path, *args: str, text: bool = True) -> str | bytes:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=text,
        check=False,
    )
    if result.returncode:
        stderr = result.stderr.strip() if text else result.stderr.decode(errors="replace").strip()
        raise RuntimeError(f"git {' '.join(args)} failed: {stderr}")
    return result.stdout


def repository_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError("当前目录不在 Git 仓库中")
    return Path(result.stdout.strip()).resolve()


def load_config(root: Path) -> dict[str, Any]:
    configured = os.environ.get("QUALITY_GATES_CONFIG")
    path = Path(configured).expanduser() if configured else root / CONFIG_NAME
    if not path.is_absolute():
        path = root / path
    if not path.is_file():
        raise RuntimeError(f"缺少质量门禁配置：{path}")
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"无法读取质量门禁配置 {path}: {exc}") from exc
    if config.get("schema_version") != 1:
        raise RuntimeError(f"不支持的质量门禁配置版本：{config.get('schema_version')!r}")
    validate_patterns(config)
    return config


def validate_patterns(config: dict[str, Any]) -> None:
    pattern_groups = [
        config.get("branch_patterns", []),
        [item.get("pattern", "") for item in config.get("secret_patterns", [])],
        [item.get("pattern", "") for item in config.get("forbidden_content_patterns", [])],
        [item.get("pattern", "") for item in config.get("blocked_command_patterns", [])],
        config.get("remote_asset_allowlist", []),
    ]
    for pattern in (item for group in pattern_groups for item in group):
        try:
            re.compile(pattern)
        except re.error as exc:
            raise RuntimeError(f"无效正则表达式 {pattern!r}: {exc}") from exc


def matches_path(path: str, patterns: list[str]) -> bool:
    normalized = path.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    basename = PurePosixPath(normalized).name
    return any(
        fnmatch.fnmatchcase(normalized, pattern) or fnmatch.fnmatchcase(basename, pattern)
        for pattern in patterns
    )


def validate_branch_name(branch: str, config: dict[str, Any]) -> list[str]:
    if branch in config.get("protected_branches", []):
        return []
    if any(re.fullmatch(pattern, branch) for pattern in config.get("branch_patterns", [])):
        return []
    return [f"分支名不符合约定：{branch}"]


def validate_commit_message(message: str, config: dict[str, Any]) -> list[str]:
    subject = next(
        (line.strip() for line in message.splitlines() if line.strip() and not line.startswith("#")),
        "",
    )
    if not subject:
        return ["提交信息不能为空"]
    generated_prefixes = ("Merge ", "Revert ", "fixup! ", "squash! ", "合并:")
    if subject.startswith(generated_prefixes):
        return []

    types = "|".join(re.escape(item) for item in config.get("commit_types", []))
    pattern = re.compile(rf"^(?:{types})(?:\([^)]+\))?!?:\s+\S.+$")
    violations: list[str] = []
    if not types or not pattern.fullmatch(subject):
        violations.append("提交信息应使用“<类型>(<范围>): <动作摘要>”格式")
    max_length = int(config.get("commit_subject_max_length", 72))
    if len(subject) > max_length:
        violations.append(f"提交摘要超过 {max_length} 个字符：{len(subject)}")
    return violations


def staged_paths(root: Path) -> list[str]:
    output = git(
        root,
        "diff",
        "--cached",
        "--name-only",
        "--diff-filter=ACMR",
        "-z",
        text=False,
    )
    assert isinstance(output, bytes)
    return [item.decode("utf-8", errors="surrogateescape") for item in output.split(b"\0") if item]


def staged_bytes(root: Path, path: str) -> bytes:
    output = git(root, "show", f":{path}", text=False)
    assert isinstance(output, bytes)
    return output


def content_violations(path: str, content: bytes, config: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    if b"\0" in content:
        return violations
    text = content.decode("utf-8", errors="replace")

    if CONFLICT_MARKER.search(text):
        violations.append(f"{path}: 包含未解决的冲突标记")

    for item in config.get("secret_patterns", []):
        if re.search(item["pattern"], text):
            violations.append(f"{path}: 疑似包含敏感信息（{item['name']}）")

    for item in config.get("forbidden_content_patterns", []):
        if re.search(item["pattern"], text, re.MULTILINE):
            violations.append(f"{path}: 包含禁止内容（{item['name']}）")

    extension = PurePosixPath(path).suffix.lower()
    if extension in config.get("remote_asset_extensions", []):
        allowlist = config.get("remote_asset_allowlist", [])
        for match in REMOTE_ASSET_CONTEXT.finditer(text):
            url = match.group(1)
            if not any(re.search(pattern, url) for pattern in allowlist):
                violations.append(f"{path}: 引用了未列入白名单的远程资源 {url}")

    return violations


def validate_staged_files(root: Path, config: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    allowed = config.get("allowed_file_patterns", [])
    forbidden = config.get("forbidden_file_patterns", [])
    max_size = int(config.get("max_file_size_bytes", 5 * 1024 * 1024))

    diff_check = subprocess.run(
        ["git", "diff", "--cached", "--check"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if diff_check.returncode:
        violations.append(diff_check.stdout.strip() or "暂存区存在空白或冲突标记问题")

    for path in staged_paths(root):
        if matches_path(path, forbidden) and not matches_path(path, allowed):
            violations.append(f"{path}: 文件类型禁止提交")
            continue
        content = staged_bytes(root, path)
        if len(content) > max_size:
            violations.append(f"{path}: 文件大小 {len(content)} 字节，超过限制 {max_size} 字节")
        violations.extend(content_violations(path, content, config))
    return violations


def current_branch(root: Path) -> str:
    output = git(root, "branch", "--show-current")
    assert isinstance(output, str)
    return output.strip()


def pushed_branches(stdin: str) -> list[str]:
    branches: list[str] = []
    for line in stdin.splitlines():
        parts = line.split()
        if len(parts) != 4:
            continue
        _local_ref, local_sha, remote_ref, _remote_sha = parts
        if local_sha == ZERO_SHA or not remote_ref.startswith("refs/heads/"):
            continue
        branch = remote_ref.removeprefix("refs/heads/")
        branches.append(branch)
    return branches


def validate_push_branches(branches: list[str], config: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    protected = set(config.get("protected_branches", []))
    allow_protected = os.environ.get("QUALITY_GATE_ALLOW_PROTECTED_PUSH") == "1"
    for branch in branches:
        if branch in protected and not allow_protected:
            violations.append(f"禁止直接推送受保护分支：{branch}，请通过合并请求进入")
            continue
        violations.extend(validate_branch_name(branch, config))
    return violations


def validate_agent_command(
    command: str,
    config: dict[str, Any],
    branch: str = "",
) -> list[str]:
    violations: list[str] = []
    for item in config.get("blocked_command_patterns", []):
        if re.search(item["pattern"], command):
            violations.append(f"命令包含高风险操作：{item['name']}")

    protected = "|".join(re.escape(item) for item in config.get("protected_branches", []))
    is_push = bool(re.search(r"\bgit\s+push\b", command))
    if protected and re.search(
        rf"\bgit\s+push\b[^\n]*(?:\s|:|/)(?:{protected})(?:\s|$)",
        command,
    ):
        violations.append("命令尝试直接推送受保护分支")
    elif is_push and branch in config.get("protected_branches", []):
        violations.append(f"命令尝试从受保护分支 {branch} 直接推送")
    return violations


def run_commands(root: Path, commands: list[str], stage: str) -> list[str]:
    violations: list[str] = []
    for command in commands:
        print(f"[RUN] {command}")
        result = subprocess.run(command, cwd=root, shell=True, check=False)
        if result.returncode:
            violations.append(f"{stage} 命令失败（退出码 {result.returncode}）：{command}")
    return violations


def report(violations: list[str]) -> int:
    if not violations:
        info("本地质量门禁通过")
        return 0
    for violation in violations:
        error(violation)
    print(f"[BLOCKED] 共发现 {len(violations)} 个问题。", file=sys.stderr)
    return 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="stage", required=True)
    subparsers.add_parser("pre-commit", help="检查暂存文件")
    commit_parser = subparsers.add_parser("commit-msg", help="检查提交信息")
    commit_parser.add_argument("message_file", type=Path)
    subparsers.add_parser("pre-push", help="检查分支并运行推送前命令")
    command_parser = subparsers.add_parser("agent-command", help="检查 Agent 即将执行的命令")
    command_parser.add_argument("command", nargs=argparse.REMAINDER)
    subparsers.add_parser("check", help="运行当前仓库的完整本地检查")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        root = repository_root()
        config = load_config(root)
        violations: list[str] = []

        if args.stage == "pre-commit":
            violations.extend(validate_staged_files(root, config))
            violations.extend(run_commands(root, config.get("commands", {}).get("pre_commit", []), "pre-commit"))
        elif args.stage == "commit-msg":
            violations.extend(validate_commit_message(args.message_file.read_text(encoding="utf-8"), config))
        elif args.stage == "pre-push":
            branches = pushed_branches(sys.stdin.read()) or [current_branch(root)]
            violations.extend(validate_push_branches(branches, config))
            if not violations:
                violations.extend(run_commands(root, config.get("commands", {}).get("pre_push", []), "pre-push"))
        elif args.stage == "agent-command":
            command_parts = args.command[1:] if args.command[:1] == ["--"] else args.command
            violations.extend(
                validate_agent_command(
                    " ".join(command_parts).strip(),
                    config,
                    current_branch(root),
                )
            )
        elif args.stage == "check":
            branch = current_branch(root)
            if branch:
                violations.extend(validate_branch_name(branch, config))
            violations.extend(validate_staged_files(root, config))
            violations.extend(run_commands(root, config.get("commands", {}).get("pre_push", []), "check"))
        return report(violations)
    except (OSError, RuntimeError, ValueError) as exc:
        error(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
