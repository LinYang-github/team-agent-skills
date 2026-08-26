#!/usr/bin/env python3
"""Validate team skill structure and installer syntax without installing anything."""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
MANIFEST = ROOT / "manifest.yaml"

def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)

skill_dirs = sorted(
    path for path in SKILLS.iterdir()
    if path.is_dir() and (path / "SKILL.md").is_file()
) if SKILLS.is_dir() else []
if not skill_dirs:
    fail("没有发现 skills/*/SKILL.md")

manifest_text = MANIFEST.read_text(encoding="utf-8") if MANIFEST.is_file() else ""
manifest_names = set(re.findall(r"^\s*- name: ([a-z0-9-]+)\s*$", manifest_text, re.MULTILINE))
if manifest_names != {path.name for path in skill_dirs}:
    fail(f"manifest.yaml 与技能目录不一致：目录={sorted(path.name for path in skill_dirs)}，清单={sorted(manifest_names)}")

for skill in skill_dirs:
    text = (skill / "SKILL.md").read_text(encoding="utf-8")
    frontmatter = text.split("---\n", 2)[1] if text.startswith("---\n") and text.count("---\n") >= 2 else ""
    if not re.search(r"^name:\s*.+$", frontmatter, re.MULTILINE):
        fail(f"{skill.name}/SKILL.md 缺少 name frontmatter")
    if not re.search(r"^description:\s*.+$", frontmatter, re.MULTILINE):
        fail(f"{skill.name}/SKILL.md 缺少 description frontmatter")

shells = sorted((ROOT / "scripts").glob("*.sh"))
for script in shells:
    result = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True)
    if result.returncode:
        fail(f"Shell 语法错误：{script.name}\n{result.stderr.strip()}")

pwsh = shutil.which("pwsh") or shutil.which("powershell")
if pwsh:
    print(f"PowerShell 检查工具：{pwsh}；已保留为静态检查入口，未执行安装脚本。")
else:
    print("未发现 PowerShell，跳过 Windows 脚本执行检查。")

print(f"Skill 数量：{len(skill_dirs)}")
print(f"Shell 安装脚本：{len(shells)}，语法检查通过")
print("Skill 结构校验通过")
