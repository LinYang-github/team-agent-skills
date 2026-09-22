---
name: plugin-packager
description: Assemble the skills, MCP services, MCP Apps, business workbench entries, and optional agents of an existing product project into a Claude-format plugin directory and ZIP for HuiMate/DSH import. Use when a product team wants to package or update its integration for this platform.
---

# Package a product plugin

Produce a self-contained plugin directory and an importable ZIP from the target project's real capabilities. This skill is a portable authoring tool; it is not itself the product plugin being built. Its scripts require Python 3.10+ and the standard library only.

## Establish the delivery

Read the target project's instructions, integration documentation, service entry points, existing skills, agents and release scripts. Identify the requested product, version and capabilities from those sources. Ask only for release metadata or capability choices that cannot be established from the project or request.

Read [the delivery contract](references/delivery-contract.md) before editing. It contains the supported layout, complete examples, parameter handling and current host limitations. Treat project-specific business rules as owned by that project; do not invent new endpoints, tools or business procedures.

Distinguish what is already implemented from what still needs development. A configuration file cannot create an MCP service or interactive page. If a required capability is missing, report that gap; do not ship a placeholder as working functionality or silently remove the capability. Developing that service is a separate scope decision.

## Prepare the plugin directory

Use the project's established release-source location, or a dedicated `plugin/` directory when none exists. Work in an isolated staging copy when updating a release. Do not ZIP the whole repository. Preserve user changes and any existing access restrictions.

- Create `.claude-plugin/plugin.json` with real identity, version and description. Include only capabilities actually supplied. Keep this plugin's name stable across updates.
- Copy each complete product skill directory, including referenced scripts, templates and documentation. Do not include repository-maintenance skills or this packaging skill unless the requested product actually distributes them.
- Put ordinary service connections in `.mcp.json`. Put services requiring interactive MCP Apps pages in root `.mcpapps.json`; reference that file through `plugin.json.mcpServers`. A service offering both ordinary tools and a page belongs in `.mcpapps.json` once.
- When the product has an existing business workbench, include root `.workbenches.json` following [the workbench contract](references/workbenches.md). Generate its identity and resolver binding from the real product; package it once with the MCP/Skills. Do not add a second upload or copy the business application into the host.
- Put optional product agents in `agents/`. Preserve required permissions; an unsupported restriction is a compatibility blocker, not a reason to delete the restriction. Prefer standard `model: inherit` when the product does not require a particular model.
- Declare install-time values with `userConfig`, mark secrets sensitive, and use `${user_config.KEY}` references. Do not ship credentials, local account files or machine-specific absolute paths. Include a README describing service deployment, runtime prerequisites, configuration and verification steps.
- For bundled programs, preserve their required files and licenses, and refer to them through `${CLAUDE_PLUGIN_ROOT}`. Build them using the product's release process before packaging. Keep remote deployments and system dependencies in that product's normal distribution process.

Do not add a private `mcpApps` manifest field, MCP Apps page catalog, dependency format or ZIP-specific manifest. Marketplace publication is optional: a single-plugin ZIP needs no `marketplace.json`. When a marketplace entry is requested, use the standard example in the reference; do not publish or install into another system merely to produce the files.

## Validate and package

Resolve the script from this skill's actual location, independent of the current working directory. Paths below are placeholders; quote actual paths that contain spaces.

```sh
python3 /path/to/plugin-packager/scripts/plugin_package.py validate /path/to/product/plugin
python3 /path/to/plugin-packager/scripts/plugin_package.py pack /path/to/product/plugin --output /path/to/releases/product-1.0.0.zip
```

The output path must be outside the plugin directory and must not already exist. Validation and packing read the source without modifying it; neither command executes bundled programs or contacts services. Both report JSON on stdout and return a nonzero status on failure. Fix the reported input problem and re-run; do not bypass the validator or silently strip required metadata.

The script checks the supported delivery layout, declared files, parameters, connection conflicts, known host restrictions, local Markdown links and ZIP limits. It accepts simple scalar YAML frontmatter (including block text) or a JSON object inside the YAML frontmatter delimiters. For more complex YAML, preserve all fields when converting to the equivalent JSON object, or report that this validator cannot check it. This is a tool limitation, not a new plugin protocol.

Inspect the final capability list and warnings. Read the generated ZIP to confirm that the manifest, dotfiles and complete attachments are present. Keep validation reports outside the plugin directory. Credentials can be hidden in arbitrary source files: review the prepared tree as well as the script's checks.

## Report the result and evidence

Deliver the plugin directory and ZIP location, version, SHA-256, included capabilities, required configuration and external prerequisites. State any blockers or excluded capabilities and why.

Separate these results:

1. **Packaging checks:** files, references and ZIP constraints.
2. **Platform import checks:** actual preview, install and capability discovery, if a test platform is available and its use is authorized.
3. **Runtime checks:** real connection, tool execution, model use and page interaction, only when actually performed.

Do not present offline checks as successful service or UI validation. Leave unavailable checks explicit. The skill does not require access to the platform repository, a deployed instance, or any particular coding-agent tool.
