#!/usr/bin/env python3
"""Offline authoring checks and ZIP production; Python 3.10+, standard library only."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import textwrap
import unicodedata
from urllib.parse import unquote, urlsplit
import zipfile

MIB = 1024 * 1024
LIMITS = {"zip": 25 * MIB, "file": 25 * MIB, "expanded": 100 * MIB, "files": 2000}
NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
VERSION = re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?\Z")
PARAM = re.compile(r"\$\{user_config\.([^}]+)\}")
FORBIDDEN_DIRS = {".git", "node_modules", ".cache", "__pycache__", ".dsh", ".data"}


class Invalid(ValueError):
    pass


def require(condition: object, message: str) -> None:
    if not condition:
        raise Invalid(message)


def object_pairs(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        require(key not in result, "Duplicate JSON/frontmatter key")
        result[key] = value
    return result


def json_value(text: str, label: str):
    def constant(_: str):
        raise Invalid(f"{label}: non-finite JSON number")
    try:
        return json.loads(text, object_pairs_hook=object_pairs, parse_constant=constant)
    except json.JSONDecodeError as error:
        raise Invalid(f"{label}: invalid JSON at line {error.lineno}") from None


def nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def safe_name(name: str) -> None:
    require(bool(name) and not name.startswith("/") and "\\" not in name
            and not re.match(r"^[A-Za-z]:", name)
            and not any(ord(c) < 32 for c in name)
            and all(p not in ("", ".", "..") for p in name.split("/")),
            f"Unsafe package path: {name!r}")


def tree(root: Path) -> dict[str, tuple[bytes, int]]:
    require(root.is_dir() and not root.is_symlink(), "Input must be a real plugin directory, not a link")
    files: dict[str, tuple[bytes, int]] = {}
    identities: set[str] = set()
    total = 0

    def visit(directory: Path) -> None:
        nonlocal total
        for item in sorted(directory.iterdir()):
            relative = item.relative_to(root).as_posix()
            safe_name(relative)
            identity = unicodedata.normalize("NFC", relative).lower()
            require(identity not in identities, f"Case/Unicode-colliding path: {relative}")
            identities.add(identity)
            info = item.lstat()
            require(stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode), f"Links/special files are not supported: {relative}")
            if stat.S_ISDIR(info.st_mode):
                require(item.name not in FORBIDDEN_DIRS, f"Remove development data from the release tree: {relative}")
                visit(item)
                continue
            forbidden = (item.name == ".env" or (item.name.startswith(".env.") and item.name != ".env.example")
                         or item.name == ".local-test-accounts.jsonl" or item.suffix.lower() in {".pem", ".key", ".p12", ".pfx"})
            require(not forbidden, f"Potential credential file cannot be packaged: {relative}")
            require(info.st_size <= LIMITS["file"], f"File exceeds 25 MiB: {relative}")
            total += info.st_size
            require(total <= LIMITS["expanded"], "Expanded package exceeds 100 MiB")
            require(len(files) < LIMITS["files"], "Package exceeds 2000 file entries")
            # Check the opened file too: never follow a replaced final symlink.
            fd = os.open(item, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
            with os.fdopen(fd, "rb") as stream:
                current = os.fstat(stream.fileno())
                require(stat.S_ISREG(current.st_mode) and (current.st_dev, current.st_ino) == (info.st_dev, info.st_ino), f"Source changed during packaging: {relative}")
                content = stream.read(LIMITS["file"] + 1)
                require(len(content) == info.st_size and stream.read(1) == b"", f"Source changed during packaging: {relative}")
            files[relative] = (content, 0o755 if info.st_mode & 0o111 else 0o644)

    visit(root)
    return files


def scalar(value: str, label: str):
    value = value.strip()
    if value.startswith('"'):
        return json_value(value, label)
    if value.startswith("'"):
        require(value.endswith("'") and len(value) > 1, f"{label}: unclosed quoted scalar")
        return value[1:-1].replace("''", "'")
    value = value.split(" #", 1)[0].rstrip()
    require(value and value[0] not in "[{&*!>|" and ": " not in value, f"{label}: complex YAML is not supported; preserve metadata as a JSON object inside frontmatter")
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    if value.lower() in ("null", "~"):
        return None
    if re.fullmatch(r"-?\d+(?:\.\d+)?", value):
        return float(value) if "." in value else int(value)
    return value


def frontmatter(text: str, label: str) -> dict:
    match = re.match(r"\A---\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|$)", text, re.S)
    require(match is not None, f"{label}: missing or unclosed frontmatter")
    body = match.group(1)
    if body.lstrip().startswith("{"):
        result = json_value(body, label)
    else:
        pairs = []
        lines = body.splitlines()
        index = 0
        while index < len(lines):
            line = lines[index]
            index += 1
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            field = re.fullmatch(r"([A-Za-z][A-Za-z0-9_-]*):\s*(.*)", line)
            require(field is not None, f"{label}: complex YAML is not supported; preserve metadata as a JSON object inside frontmatter")
            key, value = field.groups()
            if re.fullmatch(r"[|>][-+]?", value):
                block = []
                while index < len(lines) and (not lines[index].strip() or lines[index].startswith(" ")):
                    block.append(lines[index]); index += 1
                parsed = textwrap.dedent("\n".join(block)).strip()
            else:
                parsed = scalar(value, label)
            pairs.append((key, parsed))
        result = object_pairs(pairs)
    require(isinstance(result, dict), f"{label}: frontmatter must be an object")
    require(nonempty(result.get("name")) and NAME.fullmatch(result["name"]) and len(result["name"]) <= 64, f"{label}: require a kebab-case name, at most 64 characters")
    require(nonempty(result.get("description")), f"{label}: require a nonempty description")
    require(bool(text[match.end():].strip()), f"{label}: instruction body is empty")
    return result


class Package:
    def __init__(self, root: Path):
        self.files = tree(root)
        self.warnings: list[str] = []
        self.manifest = self.read_json(".claude-plugin/plugin.json")
        self.options: dict = {}

    def text(self, path: str) -> str:
        require(path in self.files, f"Missing file: {path}")
        try:
            return self.files[path][0].decode("utf-8")
        except UnicodeDecodeError:
            raise Invalid(f"{path}: expected UTF-8") from None

    def read_json(self, path: str) -> dict:
        data = json_value(self.text(path), path)
        require(isinstance(data, dict), f"{path}: require a JSON object")
        return data

    def path(self, value: object) -> str:
        require(nonempty(value), "Component paths must be nonempty strings")
        clean = value.removeprefix("${CLAUDE_PLUGIN_ROOT}/").removeprefix("./").rstrip("/")
        safe_name(clean)
        require("${" not in clean, "Component paths cannot depend on runtime parameters")
        require(clean in self.files or any(p.startswith(clean + "/") for p in self.files), f"Missing referenced path: {clean}")
        return clean

    def selection(self, key: str, defaults: list[str]) -> list[str]:
        declared = self.manifest.get(key)
        if declared is None:
            return defaults
        values = declared if isinstance(declared, list) else [declared]
        return list(dict.fromkeys(self.path(value) for value in values))

    def parameters(self) -> None:
        raw = self.manifest.get("userConfig", {})
        require(isinstance(raw, dict), "userConfig must be an object")
        self.options = raw
        for key, option in raw.items():
            require(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key) and isinstance(option, dict), "Invalid userConfig declaration")
            kind = option.get("type")
            require(kind in ("string", "number", "boolean", "directory", "file"), f"userConfig.{key}: unsupported type")
            require(nonempty(option.get("title")) and nonempty(option.get("description")), f"userConfig.{key}: title and description required")
            for flag in ("required", "sensitive", "multiple"):
                require(flag not in option or type(option[flag]) is bool, f"userConfig.{key}.{flag}: expected boolean")
            require(not option.get("multiple") or kind == "string", f"userConfig.{key}: multiple requires string type")
            choices = option.get("options")
            require(choices is None or (kind == "string" and isinstance(choices, list) and all(isinstance(v, str) for v in choices)), f"userConfig.{key}: invalid options")
            for bound in ("min", "max"):
                require(bound not in option or (kind == "number" and type(option[bound]) in (int, float) and math.isfinite(option[bound])), f"userConfig.{key}: invalid {bound}")
            require(not ("min" in option and "max" in option) or option["min"] <= option["max"], f"userConfig.{key}: min exceeds max")
            if "default" not in option:
                continue
            require(not option.get("sensitive"), f"userConfig.{key}: do not distribute sensitive defaults")
            default = option["default"]
            valid = (isinstance(default, list) and all(isinstance(v, str) for v in default)) if option.get("multiple") else (type(default) in (int, float) and math.isfinite(default) if kind == "number" else type(default) is bool if kind == "boolean" else isinstance(default, str))
            require(valid, f"userConfig.{key}: invalid default type")
            require(not option.get("required") or default not in ("", []), f"userConfig.{key}: required default is empty")
            require(choices is None or all(v in choices for v in (default if isinstance(default, list) else [default])), f"userConfig.{key}: default outside options")
            if kind == "number":
                require(option.get("min", -math.inf) <= default <= option.get("max", math.inf), f"userConfig.{key}: default outside bounds")

    def references(self, value: object) -> None:
        if isinstance(value, dict):
            for nested in value.values(): self.references(nested)
        elif isinstance(value, list):
            for nested in value: self.references(nested)
        elif isinstance(value, str):
            for key in PARAM.findall(value):
                require(key in self.options, f"Undeclared userConfig parameter: {key}")
                require(not self.options[key].get("multiple"), f"userConfig.{key}: MCP array substitution is unsupported")
            if "${CLAUDE_PLUGIN_ROOT}" in value:
                for token in re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}(?:/[^\s\"']*)?", value):
                    if token == "${CLAUDE_PLUGIN_ROOT}": continue
                    if "${" in token[len("${CLAUDE_PLUGIN_ROOT}"):]:
                        self.warnings.append("A runtime-dependent bundled path needs manual verification")
                    else:
                        self.path(token)

    def markdown_links(self) -> None:
        for path in self.files:
            if not path.endswith(".md"): continue
            text = re.sub(r"(?ms)^\s*(`{3,}|~{3,})[^\n]*\n.*?^\s*\1\s*$", "", self.text(path))
            links = [m.group(1) or m.group(2) for m in re.finditer(r"!?\[[^\]\n]*\]\(\s*(?:<([^>]+)>|([^\s)]+))(?:\s+['\"][^\n]*?['\"])?\s*\)", text)]
            links += [m.group(1) or m.group(2) for m in re.finditer(r"(?m)^\s{0,3}\[[^\]\n]+\]:\s*(?:<([^>]+)>|(\S+))", text)]
            for target in links:
                if target.startswith("#") or re.match(r"^[A-Za-z][\w+.-]*:", target): continue
                target = unquote(target.split("#", 1)[0].split("?", 1)[0])
                require(not target.startswith("/") and "\\" not in target, f"{path}: local link must be relative")
                parts = list(PurePosixPath(path).parent.parts)
                for part in target.split("/"):
                    if part in ("", "."): continue
                    if part == "..":
                        require(parts, f"{path}: link escapes plugin root")
                        parts.pop()
                    else: parts.append(part)
                if parts: self.path("/".join(parts))

    def skills_and_agents(self) -> dict[str, list[str]]:
        inventory: dict[str, list[str]] = {"skills": [], "agents": []}
        for component in inventory:
            defaults = [component] if any(p.startswith(component + "/") for p in self.files) else []
            roots = self.selection(component, defaults)
            require(all(r == component or r.startswith(component + "/") for r in roots), f"{component}: use the conventional {component}/ layout for this packager")
            candidates = [p for p in self.files if p.startswith(component + "/") and
                          (p.endswith("/SKILL.md") and len(PurePosixPath(p).parts) == 3 if component == "skills" else p.endswith(".md"))]
            if component == "skills":
                # A SKILL.md below a discovered skill may be a template attachment.
                # A category collection with no owning skill is outside this tool's layout.
                for path in self.files:
                    if path.startswith("skills/") and path.endswith("/SKILL.md"):
                        owner = "/".join(PurePosixPath(path).parts[:2]) + "/SKILL.md"
                        require(owner in candidates, f"{path}: use skills/<name>/SKILL.md")
            names = set()
            for path in candidates:
                require(any(path == r or path.startswith(r + "/") for r in roots), f"Undiscovered {component} file: {path}")
                metadata = frontmatter(self.text(path), path)
                name = metadata["name"]
                require(name not in names, f"Duplicate {component} name: {name}")
                names.add(name)
                if component == "skills":
                    require(name == PurePosixPath(path).parent.name, f"{path}: name must match its directory")
                    require("allowed-tools" not in metadata, f"{path}: Skill allowed-tools is not enforced by this host; do not remove required restrictions")
                    for flag in ("disable-model-invocation", "user-invocable"):
                        require(flag not in metadata or type(metadata[flag]) is bool, f"{path}: {flag} requires a boolean in this delivery subset")
                else:
                    require(not ({"tools", "disallowedTools"} & metadata.keys()), f"{path}: tools/disallowedTools are not enforced by this host")
                    require(metadata.get("model", "inherit") == "inherit", f"{path}: this packager supports model: inherit; custom routes require separate host validation")
                    require(not (metadata.keys() - {"name", "description", "model"}), f"{path}: unsupported Agent execution metadata")
                inventory[component].append(name)
            for selected in roots:
                require(any(p == selected or p.startswith(selected + "/") for p in candidates), f"{selected}: no discoverable {component} files")
        require("SKILL.md" not in self.files, "Use skills/<name>/SKILL.md, not a root skill tied to the install directory name")
        return inventory

    def connections(self) -> dict[str, list[str]]:
        defaults = [".mcp.json"] if ".mcp.json" in self.files else []
        paths = list(dict.fromkeys(defaults + self.selection("mcpServers", defaults)))
        require(".mcpapps.json" not in self.files or ".mcpapps.json" in paths, "Reference .mcpapps.json through plugin.json.mcpServers")
        require(all(p in (".mcp.json", ".mcpapps.json") for p in paths), "Use .mcp.json and .mcpapps.json file references in this delivery subset")
        seen: set[str] = set()
        fingerprints: set[str] = set()
        inventory: dict[str, list[str]] = {"mcp": [], "mcpApps": []}
        for path in paths:
            data = self.read_json(path)
            servers = data.get("mcpServers")
            require(isinstance(servers, dict) and servers, f"{path}: nonempty mcpServers object required")
            require(not (data.keys() - {"mcpServers", "$schema"}), f"{path}: unsupported top-level fields")
            for key, server in servers.items():
                require(nonempty(key) and key not in seen, f"Duplicate or empty MCP service key: {key}")
                seen.add(key)
                require(isinstance(server, dict), f"{key}: require an MCP server object")
                require(not (server.keys() - {"type", "command", "args", "env", "cwd", "url", "headers"}), f"{key}: unsupported connection options; OAuth, filters and timeout overrides are outside this delivery subset")
                transport = server.get("type", "stdio" if "command" in server else "http")
                require(transport in ("stdio", "http", "sse"), f"{key}: unsupported transport")
                require(path != ".mcpapps.json" or transport != "sse", f"{key}: MCP Apps does not support SSE")
                if transport == "stdio":
                    command = server.get("command")
                    require(nonempty(command) and "url" not in server and "headers" not in server, f"{key}: stdio requires command without HTTP fields")
                    require(not command.startswith("/") and not re.match(r"^[A-Za-z]:", command) and "\\" not in command, f"{key}: machine-specific command path is not portable")
                    require("/" not in command or command.startswith("${CLAUDE_PLUGIN_ROOT}/"), f"{key}: bundled executable must use CLAUDE_PLUGIN_ROOT")
                    require(isinstance(server.get("args", []), list) and all(isinstance(v, str) for v in server.get("args", [])), f"{key}: args must be strings")
                    if "cwd" in server:
                        require(isinstance(server["cwd"], str) and server["cwd"].startswith("${CLAUDE_PLUGIN_ROOT}"), f"{key}: cwd must refer to the plugin tree")
                else:
                    require(nonempty(server.get("url")) and not ({"command", "args", "env", "cwd"} & server.keys()), f"{key}: HTTP requires url without stdio fields")
                    url = server["url"]
                    require("${" not in PARAM.sub("parameter", url), f"{key}: malformed or unsupported endpoint variable")
                    parsed = urlsplit(url)
                    require(url.startswith("${user_config.") or (parsed.scheme in ("http", "https") and parsed.hostname), f"{key}: invalid MCP endpoint")
                    require(not parsed.username and not parsed.password, f"{key}: endpoint must not embed credentials")
                for field in ("env", "headers"):
                    values = server.get(field, {})
                    require(isinstance(values, dict) and all(isinstance(v, str) for v in values.values()), f"{key}: {field} must contain strings")
                    for name, value in values.items():
                        if re.search(r"token|secret|password|authorization|api[-_]?key|cookie", name, re.I):
                            refs = PARAM.findall(value)
                            require(refs and all(self.options.get(r, {}).get("sensitive") for r in refs), f"{key}: credential fields must reference sensitive userConfig values")
                self.references(server)
                fingerprint = json.dumps({**server, "type": transport}, sort_keys=True)
                require(fingerprint not in fingerprints, f"{key}: identical service configuration is declared twice; keep one connection")
                fingerprints.add(fingerprint)
                inventory["mcpApps" if path == ".mcpapps.json" else "mcp"].append(key)
        return inventory

    def validate(self) -> dict:
        manifest = self.manifest
        require(nonempty(manifest.get("name")) and NAME.fullmatch(manifest["name"]) and len(manifest["name"]) <= 64, "plugin.json: require a kebab-case name, at most 64 characters")
        version = manifest.get("version")
        match = VERSION.fullmatch(version) if isinstance(version, str) else None
        require(match and (not match[4] or all(not s.isdigit() or s == "0" or not s.startswith("0") for s in match[4].split("."))), "plugin.json: require a semantic version")
        require(nonempty(manifest.get("description")), "plugin.json: release description required")
        require("mcpApps" not in manifest, "Do not invent mcpApps; use the .mcpapps.json file convention")
        require(not ({"hooks", "commands", "lspServers", "outputStyles", "settings", "monitors", "themes"} & manifest.keys()), "Executable components outside Skill/MCP/Apps/Agent need separate validation")
        for path in self.files:
            require(path not in {"plugin.json", "mcp.json", ".lsp.json", "marketplace.json", ".claude-plugin/marketplace.json"}
                    and not path.startswith((".plugin/", ".codex-plugin/", ".cursor-plugin/", "hooks/", "commands/", "lsp/")), f"Outside the single Claude plugin delivery subset: {path}")
        dependencies = manifest.get("dependencies", [])
        require(isinstance(dependencies, list), "dependencies must be an array")
        for dependency in dependencies:
            require(nonempty(dependency) or (isinstance(dependency, dict) and nonempty(dependency.get("name")) and ("version" not in dependency or nonempty(dependency["version"]))), "Invalid plugin dependency declaration")
        if dependencies: self.warnings.append("Dependency versions and enabled state require platform validation")
        if "README.md" not in self.files: self.warnings.append("Add README.md with deployment, configuration and verification steps")
        self.parameters()
        inventory = {**self.skills_and_agents(), **self.connections()}
        require(any(inventory.values()), "No supported capabilities found")
        self.markdown_links()
        return {"ok": True, "name": manifest["name"], "version": version, "capabilities": inventory,
                "requiredConfig": [k for k, v in self.options.items() if v.get("required")],
                "files": len(self.files), "expandedBytes": sum(len(data) for data, _ in self.files.values()),
                "warnings": sorted(set(self.warnings)), "verification": "offline packaging only; services, models and pages not executed"}

    def archive(self) -> bytes:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=False) as archive:
            for path, (content, mode) in sorted(self.files.items()):
                entry = zipfile.ZipInfo(path, date_time=(1980, 1, 1, 0, 0, 0))
                entry.create_system = 3
                entry.external_attr = (stat.S_IFREG | mode) << 16
                entry.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(entry, content)
        result = buffer.getvalue()
        require(len(result) <= LIMITS["zip"], "Compressed ZIP exceeds 25 MiB")
        return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("validate").add_argument("directory", type=Path)
    pack = sub.add_parser("pack")
    pack.add_argument("directory", type=Path)
    pack.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        package = Package(args.directory.absolute())
        result = package.validate()
        archive = package.archive()
        result.update(zipBytes=len(archive), sha256=hashlib.sha256(archive).hexdigest())
        if args.action == "pack":
            output = args.output.absolute()
            require(not output.resolve().is_relative_to(args.directory.resolve()), "ZIP output must be outside the plugin directory")
            require(output.suffix.lower() == ".zip", "Output must be a .zip file")
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("xb") as stream:
                try: stream.write(archive)
                except BaseException:
                    stream.close(); output.unlink(); raise
            result["output"] = str(output)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (Invalid, OSError, ValueError, zipfile.LargeZipFile) as error:
        # Never dump configuration objects or credential values on errors.
        message = str(error) if isinstance(error, Invalid) else f"{type(error).__name__}: could not read input or create a new ZIP; check paths and permissions"
        print(json.dumps({"ok": False, "error": message}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
