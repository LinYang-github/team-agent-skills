# Product plugin delivery contract

This reference travels with the skill. Baseline: HuiMate integration of `dsh-agent-plugins-market` 0.7.1 (`78925f69776de1a4684ef0a047607a167d402b6f`), DSH 0.1.5-rc.1 and Uni Editor 0.3.2. It describes the tested delivery subset, not full Claude CLI behavior. Check the target platform's release notes before relying on newer features.

Authoritative formats: [Claude plugin reference](https://code.claude.com/docs/en/plugins-reference), [Claude marketplaces](https://code.claude.com/docs/en/plugin-marketplaces), [Agent Skills](https://agentskills.io/specification), [MCP Apps](https://github.com/modelcontextprotocol/ext-apps/blob/main/specification/2026-01-26/apps.mdx).

## Layout

```text
plugin/
  .claude-plugin/plugin.json
  .mcp.json                         # only if ordinary services exist
  .mcpapps.json                     # only if Apps services exist
  skills/product-guide/SKILL.md
  skills/product-guide/references/usage.md
  agents/reviewer.md                # optional
  server/                          # optional bundled runtime and assets
  README.md
```

Omit absent capabilities and their manifest references. The packager uses this conventional layout: skills are immediate subdirectories of `skills/`, agents are Markdown files in `agents/`. Manifest paths may select these directories or individual contained files. Other Claude components, custom layouts and complex frontmatter are outside this tool's validated subset; rejection does not mean they are invalid in Claude.

The single-plugin ZIP starts with `.claude-plugin/plugin.json` at its root. The platform also accepts one wrapper folder, but the script produces the simpler root form. Neither the ZIP nor the source directory contains a marketplace, a second product, or a root `plugin.json` that could select a different dialect.

## Manifest and connections

An illustrative mixed plugin (replace metadata and supply the real skill, agent and services):

```json
{
  "name": "example-product",
  "version": "1.0.0",
  "description": "Use the product's implemented tools and interactive workspace",
  "author": { "name": "Product Team" },
  "license": "UNLICENSED",
  "skills": "./skills/",
  "agents": ["./agents/reviewer.md"],
  "mcpServers": ["./.mcp.json", "./.mcpapps.json"],
  "userConfig": {
    "api_url": { "type": "string", "title": "API MCP endpoint", "description": "Deployed ordinary MCP endpoint", "required": true },
    "app_url": { "type": "string", "title": "Apps MCP endpoint", "description": "Deployed MCP Apps endpoint", "required": true },
    "token": { "type": "string", "title": "Access token", "description": "Issued by the product service", "sensitive": true, "required": true }
  }
}
```

`.mcp.json`:

```json
{
  "mcpServers": {
    "product-api": {
      "type": "http",
      "url": "${user_config.api_url}",
      "headers": { "Authorization": "Bearer ${user_config.token}" }
    }
  }
}
```

`.mcpapps.json` uses exactly the same `mcpServers` structure:

```json
{
  "mcpServers": {
    "product-app": {
      "type": "http",
      "url": "${user_config.app_url}",
      "headers": { "Authorization": "Bearer ${user_config.token}" }
    }
  }
}
```

If one service provides both the tools and the page, remove the separate ordinary connection and its parameter. Keep only `.mcpapps.json` and its manifest reference. Distinct service keys must identify distinct intended connections; different authentication for the same URL may legitimately need separate connections.

For a local service, use a real runtime executable and bundled entry point:

```json
{
  "mcpServers": {
    "product-app": {
      "command": "node",
      "args": ["${CLAUDE_PLUGIN_ROOT}/server/index.mjs"],
      "env": { "PRODUCT_TOKEN": "${user_config.token}" }
    }
  }
}
```

The target machine must provide the documented runtime. A source checkout, missing dependency, undeployed URL or static HTML example is not a running service. Bundle built runtime assets within the platform limits, or distribute the service separately through the product's usual release mechanism.

## MCP Apps requirements

`.mcpapps.json` is the only platform-specific delivery convention. Claude's standard path reference can read the file as ordinary MCP configuration; another client may not implement its Apps classification.

The MCP service must advertise the page association in tools (standard `_meta.ui.resourceUri`), serve its `ui://` resource with `text/html;profile=mcp-app`, and implement the applicable MCP Apps communication. The resource is read over MCP; a local HTML file in the ZIP alone is insufficient. The host discovers actual tools/pages after connecting. Do not put Uni Editor, host plugin IDs or an invented page list into the product manifest.

Current Apps support: stdio and Streamable HTTP (`type: "http"`) with optional request headers. OAuth, SSE, tool filtering and startup-timeout overrides are not supported by this Apps integration. A declared service with no discovered page is not a working App. Browser sandbox/CSP and service deployment still need real acceptance testing.

## Parameters and agents

`userConfig` supports string, number, boolean, directory and file values, plus required/default/sensitive/options/multiple/min/max. Use a title and description. `multiple` is for strings; options constrain strings; min/max constrain numbers. Secrets have no shipped defaults and are entered at installation time. Parameter values are stored by the host, not in the distribution.

`${user_config.KEY}` is consumed in MCP connection fields. Every key must be declared. Array substitution into MCP fields is unsupported. `${CLAUDE_PLUGIN_ROOT}` resolves to the installed plugin copy; do not use a developer's absolute path. Runtime data belongs outside this read-only delivery tree. The validator checks literal bundled paths and reports dynamic-path checks it cannot perform.

An optional agent can use ordinary scalar YAML:

```yaml
---
name: reviewer
description: Review outputs using the product's documented criteria
model: inherit
---
Read the product guidance and report evidence and unresolved issues.
```

The host cannot enforce Claude agent `tools` or `disallowedTools`, and rejects those declarations. It also rejects `opus`, `sonnet` and `haiku` aliases. This packager accepts only inherited models; a custom model route needs separate host-specific validation. Do not remove permission requirements just to make an agent pass. Other Claude agent execution options may not be consumed; the packager reports them as unsupported rather than claiming they work.

Skill frontmatter must contain a matching kebab-case name and nonempty description. Skill `allowed-tools` is not enforced by this host's Skill discovery/provider, so the validator refuses to ship it as an effective restriction. The portable validator accepts flat scalar YAML, block descriptions, or a JSON object between `---` lines (JSON is valid YAML). It does not implement general YAML. Preserve metadata when changing syntax; never strip capability restrictions to bypass a check.

Plugin `dependencies` describe other plugins, not operating-system or service prerequisites. The host checks enabled dependencies and semver constraints. The portable validator checks their shape only; resolving dependency versions requires platform installation. The README must name any required plugins.

## Packaging checks and boundaries

The script requires a name, semantic version and description for an identifiable release; some are optional in the broader Claude format. It reads conventional Skill/MCP/Apps/Agent components and fails explicitly on unsupported executable components (hooks, commands or LSP), rather than claiming to validate them.

Limits match the current importer: ZIP at most 25 MiB, each uncompressed file at most 25 MiB, total uncompressed bytes at most 100 MiB, at most 2000 file entries. ZIP64, links, special files, unsafe paths and case/Unicode-colliding names are rejected. The script stores file entries only, with UTF-8 names and executable permissions, and verifies ZIP size even for `validate`.

Prepare a clean release tree: `.git`, `node_modules`, caches, environment files with actual values, private-key files and local test-account records are refused. `.env.example` is allowed only with placeholders; the author must review it. The tool checks obvious literal credentials in connection authentication fields, not arbitrary secret leakage across all source text.

Literal local Markdown links outside code fences are checked for an existing contained file. External links and heading anchors are not verified. Bare prose paths and dynamically built paths need author review. JSON/configuration errors do not echo secret values.

Only declared/default supported components enter the reported inventory. An unreachable Skill or agent file is an error. The script never modifies the source, installs dependencies, starts a service or publishes a release. Keep the source stable while validating and packing; output is written exclusively after checks, never over an existing file.

## Optional marketplace entry

A marketplace is a separate catalog of available plugins. When requested, add an entry to the organization's existing standard `.claude-plugin/marketplace.json`, outside the single-plugin ZIP:

```json
{
  "name": "product-plugins",
  "owner": { "name": "Product Team" },
  "plugins": [
    { "name": "example-product", "source": "./plugins/example-product" }
  ]
}
```

The referenced directory must contain the complete product plugin. Follow the existing catalog's versioning and review process. Creating this file does not upload a ZIP, install a plugin, deploy the service or authorize publication.
