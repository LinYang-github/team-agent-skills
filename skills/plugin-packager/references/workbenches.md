# HuiMate business workbench entries

This is a HuiMate extension, not a Claude plugin or MCP Apps standard. It requires a host version that implements this contract. Packaging success alone does not prove target-host support.

An optional root `.workbenches.json` declares existing business webpages. Installed/enabled plugin state controls their sidebar entries. Clicking uses the current HuiMate project session's existing right pane. The domain service, not the host or packager, owns the page and business operations.

```json
{
  "version": 1,
  "workbenches": [{
    "id": "example.catalog",
    "title": "Example catalog",
    "launch": {
      "kind": "mcp",
      "server": "example-api",
      "tool": "resolve_catalog_view",
      "arguments": {"mode": "hosted", "intent": "edit", "projectId": "${user_config.catalog}"}
    },
    "page": {"path": "/catalog/", "loopback": true}
  }]
}
```

`server` must be an ordinary MCP key declared by this same plugin. The real tool must be read-only and return `structuredContent.url`; no model call or guessed URL is used. Configure the service once through existing userConfig. Names, version and tools must come from the product. Do not ship the example as a capability it does not implement.

A workbench-only product may instead use `launch: {"kind":"http","url":"${user_config.resolver_url}","arguments":{}}`. This performs a bounded POST to an existing read-only resolver returning `{ "url": "https://business.example/catalog/" }`. The URL must match the page policy. This requires no artificial MCP or Skill.

`page.path` is an exact fixed absolute URL pathname. Specify either `page.origins` (exact HTTP(S) origins, optionally referencing a declared non-sensitive parameter) or `page.loopback: true`. Loopback permits only HTTP localhost, 127.0.0.1 or [::1], for installed local runtimes with dynamic ports. It is not a policy for remote hosts. Resolver POST redirects are rejected; the policy validates the returned launch URL, not all subsequent iframe navigation. A response may include `expiresAt`; expired responses are refused.

There are at most 32 entries per package. IDs must be stable and unique, titles nonempty. Only launch arguments, HTTP URL and exact origins accept `${user_config.KEY}` scalar references. Declare every parameter, do not use sensitive or list values here, and never embed credentials. Runtime prerequisites and business data remain outside the plugin snapshot. Catalog scope is a domain value, not automatically the HuiMate project name.

For ordinary management entries, no resource-selection schema is needed. If the product separately implements resource selection, keep its actual selection contracts with that integration; do not invent selection behavior through this file. This file does not replace MCP Apps discovery or bundle a second copy of the webpage.

Validate and pack with the normal commands, inspect `capabilities.workbenches` and verify `.workbenches.json` survives ZIP import. Then test actual configure/enable, sidebar discovery, right-pane page, service failure, disable/uninstall and update behavior on the authorized target host. No-workbench plugins keep their existing behavior.
