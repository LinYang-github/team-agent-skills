#!/usr/bin/env python3
"""Compile the shared JSON policy into dependency-free POSIX shell data."""
from __future__ import annotations

import argparse
import json
import re
import shlex
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def posix_ere(pattern: str) -> str:
    """Accept a conservative, portable subset; never silently change semantics."""
    if "[[" in pattern:
        raise ValueError(f"分支正则含非便携字符类：{pattern}")
    re.compile(pattern)
    converted = pattern.replace("(?:", "(")
    if "(?" in converted or re.search(r"[?*+}][?+]", converted):
        raise ValueError(f"分支正则含 POSIX ERE 不支持的分组或量词：{pattern}")
    in_class = False
    index = 0
    while index < len(converted):
        char = converted[index]
        if char == "\\":
            index += 1
            if index == len(converted) or converted[index] not in r".^$[](){}*+?|\\":
                raise ValueError(f"分支正则含非便携转义：{pattern}")
        elif char == "[":
            if in_class or converted[index + 1:index + 2] == "]":
                raise ValueError(f"分支正则含非便携字符类：{pattern}")
            in_class = True
        elif char == "]":
            in_class = False
        elif char == "{" and not in_class:
            interval = re.match(r"\{([0-9]+)(?:,([0-9]*))?\}", converted[index:])
            if not interval or any(int(n) > 255 for n in interval.groups() if n):
                raise ValueError(f"分支正则含非便携重复区间：{pattern}")
        elif ord(char) < 32 or ord(char) > 126:
            raise ValueError(f"分支正则必须使用可打印 ASCII：{pattern}")
        index += 1
    return converted


def octal_string(value: str) -> str:
    # POSIX printf, including on Git for Windows; no locale-dependent escape syntax.
    return "$(printf '" + "".join(f"\\{byte:03o}" for byte in value.encode()) + "')"


def generate(config: dict) -> str:
    if config.get("schema_version") != 1:
        raise ValueError("不支持的 quality-gates.json 配置版本")
    for key in ("branch_patterns", "commit_types", "protected_branches"):
        if not isinstance(config.get(key), list) or not all(
            isinstance(item, str) and item and "\n" not in item and "\0" not in item
            for item in config[key]
        ):
            raise ValueError(f"{key} 必须为非空字符串数组")
    maximum = config.get("commit_subject_max_length")
    if type(maximum) is not int or maximum < 1:
        raise ValueError("commit_subject_max_length 必须为正整数")
    # Python str.isspace / splitlines semantics, independent of libc's [:space:].
    whitespace = "".join(chr(i) for i in range(0x3100) if chr(i).isspace() and i != 10)
    line_breaks = "\r\v\f\x1c\x1d\x1e\x85\u2028\u2029"
    types = "|".join(re.sub(r"([.^$\[\](){}*+?|\\])", r"\\\1", t)
                     for t in config["commit_types"])
    return "\n".join([
        "# 由 scripts/generate-git-rules.py 生成，勿手改。",
        "# 规则来源：quality-gates.json；运行生成脚本后提交此文件。",
        "RULE_BRANCH_PATTERNS=" + shlex.quote("\n".join(posix_ere(p) for p in config["branch_patterns"])),
        "RULE_COMMIT_TYPES=" + shlex.quote(types),
        f"RULE_COMMIT_MAX_LENGTH={maximum}",
        "RULE_PROTECTED_BRANCHES=" + shlex.quote("\n".join(config["protected_branches"])),
        "RULE_WHITESPACE=" + octal_string(whitespace),
        "RULE_LINE_BREAKS=" + octal_string(line_breaks),
        "",
    ])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "quality-gates.json")
    parser.add_argument("--output", type=Path, default=ROOT / "hooks/lib/rules.generated.sh")
    args = parser.parse_args()
    try:
        content = generate(json.loads(args.config.read_text(encoding="utf-8")))
        args.output.write_text(content, encoding="utf-8", newline="\n")
    except (ValueError, OSError, re.error) as exc:
        parser.exit(1, f"规则生成失败：{exc}\n")


if __name__ == "__main__":
    main()
