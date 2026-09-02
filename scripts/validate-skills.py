#!/usr/bin/env python3
"""Validate team Skill structure and installer syntax without installing anything."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
MANIFEST = ROOT / "manifest.yaml"
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def frontmatter(text: str, source: Path) -> str:
    if not text.startswith("---\n") or text.count("---\n") < 2:
        fail(f"{source.relative_to(ROOT)} 缺少有效 YAML frontmatter")
    return text.split("---\n", 2)[1]


def scalar(text: str, key: str) -> str | None:
    match = re.search(
        rf"^{re.escape(key)}:\s*[\"']?([^\n\"']+)[\"']?\s*$",
        text,
        re.MULTILINE,
    )
    return match.group(1).strip() if match else None


def parse_manifest(text: str) -> dict[str, dict[str, object]]:
    records: dict[str, dict[str, object]] = {}
    blocks = re.findall(
        r"(?ms)^  - name:\s*([a-z0-9-]+)\s*\n(.*?)(?=^  - name:|\Z)",
        text,
    )
    for name, block in blocks:
        if name in records:
            fail(f"manifest.yaml 重复登记 Skill：{name}")
        version = scalar(block, "    version")
        if not version or not SEMVER.fullmatch(version):
            fail(f"manifest.yaml 中 {name} 的版本不是语义化版本：{version!r}")
        dependencies = re.findall(
            r"^      -\s*([a-z0-9-]+)\s*$",
            block,
            re.MULTILINE,
        )
        records[name] = {"version": version, "depends_on": dependencies}
    return records


def validate_agent_metadata(skill: Path) -> None:
    metadata = skill / "agents" / "openai.yaml"
    if not metadata.is_file():
        print(f"WARNING: {skill.name} 未提供 agents/openai.yaml，跳过 Agent 展示元数据检查。")
        return
    text = metadata.read_text(encoding="utf-8")
    for key in ("display_name", "short_description", "default_prompt"):
        if not re.search(rf"^\s{{2}}{key}:\s*.+$", text, re.MULTILINE):
            fail(f"{metadata.relative_to(ROOT)} 缺少 {key}")


def validate_local_links(files: list[Path]) -> int:
    checked = 0
    link_pattern = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
    for source in files:
        text = source.read_text(encoding="utf-8")
        for raw_target in link_pattern.findall(text):
            target = raw_target.strip().strip("<>")
            if not target or target.startswith(("#", "http://", "https://", "mailto:")):
                continue
            if "<" in target or ">" in target:
                continue
            target = unquote(target.split("#", 1)[0].split("?", 1)[0])
            destination = (source.parent / target).resolve()
            if not destination.exists():
                fail(f"{source.relative_to(ROOT)} 包含失效链接：{raw_target}")
            checked += 1
    return checked


skill_dirs = sorted(
    path
    for path in SKILLS.iterdir()
    if path.is_dir() and (path / "SKILL.md").is_file()
) if SKILLS.is_dir() else []
if not skill_dirs:
    fail("没有发现 skills/*/SKILL.md")

manifest_text = MANIFEST.read_text(encoding="utf-8") if MANIFEST.is_file() else ""
manifest = parse_manifest(manifest_text)
directory_names = {path.name for path in skill_dirs}
if set(manifest) != directory_names:
    fail(
        "manifest.yaml 与技能目录不一致："
        f"目录={sorted(directory_names)}，清单={sorted(manifest)}"
    )

for name, record in manifest.items():
    for dependency in record["depends_on"]:
        if dependency == name:
            fail(f"manifest.yaml 中 {name} 不能依赖自身")
        if dependency not in manifest:
            fail(f"manifest.yaml 中 {name} 依赖未登记的 Skill：{dependency}")

for skill in skill_dirs:
    skill_file = skill / "SKILL.md"
    text = skill_file.read_text(encoding="utf-8")
    header = frontmatter(text, skill_file)
    declared_name = scalar(header, "name")
    if declared_name != skill.name:
        fail(
            f"{skill_file.relative_to(ROOT)} 的 name={declared_name!r}，"
            f"应与目录名 {skill.name!r} 一致"
        )
    if not scalar(header, "description"):
        fail(f"{skill_file.relative_to(ROOT)} 缺少 description frontmatter")

    metadata_version = scalar(header, "  version")
    if metadata_version and metadata_version != manifest[skill.name]["version"]:
        fail(
            f"{skill.name} 的 SKILL.md 版本 {metadata_version} "
            f"与 manifest.yaml 版本 {manifest[skill.name]['version']} 不一致"
        )

    package_file = skill / "package.json"
    if package_file.is_file():
        package = json.loads(package_file.read_text(encoding="utf-8"))
        if package.get("version") != manifest[skill.name]["version"]:
            fail(
                f"{package_file.relative_to(ROOT)} 版本 {package.get('version')!r} "
                f"与 manifest.yaml 版本 {manifest[skill.name]['version']} 不一致"
            )

    validate_agent_metadata(skill)

readme = (ROOT / "README.md").read_text(encoding="utf-8")
for name in sorted(manifest):
    if f"`{name}`" not in readme:
        fail(f"README.md 未列出 manifest.yaml 中的 Skill：{name}")

markdown_files = [ROOT / "README.md", ROOT / "CONTRIBUTING.md"]
markdown_files.extend(sorted((ROOT / "docs").glob("*.md")))
markdown_files.extend(sorted(SKILLS.glob("**/*.md")))
checked_links = validate_local_links(markdown_files)

shells = sorted((ROOT / "scripts").glob("*.sh"))
for script in shells:
    result = subprocess.run(
        ["bash", "-n", str(script)],
        capture_output=True,
        text=True,
    )
    if result.returncode:
        fail(f"Shell 语法错误：{script.name}\n{result.stderr.strip()}")

pwsh = shutil.which("pwsh") or shutil.which("powershell")
if pwsh:
    print(f"PowerShell 检查工具：{pwsh}；已保留为静态检查入口，未执行安装脚本。")
else:
    print("未发现 PowerShell，跳过 Windows 脚本执行检查。")

print(f"Skill 数量：{len(skill_dirs)}")
print(f"本地 Markdown 链接：{checked_links}，有效性检查通过")
print(f"Shell 安装脚本：{len(shells)}，语法检查通过")
print("Skill 结构校验通过")
