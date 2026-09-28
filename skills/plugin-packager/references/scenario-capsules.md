# Scenario capsule delivery and registration

## Supported boundary

Baseline: HuiMate source commit `78f272f12df7b90649b3a2413d1433a1f9bbb2de`. Recheck the target release before promising different behavior. This is source verification, not evidence that a deployed instance has been exercised.

A Claude-format plugin ZIP can carry capsule YAML as ordinary attachments. Import preserves those files, but does **not** discover or register them as home-page scenario capsules. The capsule service reads only the absolute paths in the administrator's `huimate-scenario-capsules-host.config.files` configuration. Installing, enabling, updating or uninstalling a product plugin does not manage this separate registration.

Implementation evidence at this baseline:

- [ZIP extraction](https://github.com/WuFuxiu/HuiMate/blob/78f272f12df7b90649b3a2413d1433a1f9bbb2de/packages/agent-plugins-market/src/zip.ts) preserves ordinary archive files; [installation](https://github.com/WuFuxiu/HuiMate/blob/78f272f12df7b90649b3a2413d1433a1f9bbb2de/packages/agent-plugins-market/src/installation.ts) copies the plugin tree into an installation snapshot.
- [Capsule service](https://github.com/WuFuxiu/HuiMate/blob/78f272f12df7b90649b3a2413d1433a1f9bbb2de/packages/scenario-capsules/src/index.ts) constructs its registry from `config.files`; [registry](https://github.com/WuFuxiu/HuiMate/blob/78f272f12df7b90649b3a2413d1433a1f9bbb2de/packages/scenario-capsules/src/registry.ts) reads that list, validates YAML and checks available Skills. It does not scan installed product plugins.

Do not invent a `capsules` manifest field, `.capsules.json` discovery convention, or installation hook. If automatic registration from plugin import is a requirement, report the missing host capability; adding it is a separate implementation scope.

## Prepare and validate the attachments

Use the target release's capsule [format](https://github.com/WuFuxiu/HuiMate/blob/78f272f12df7b90649b3a2413d1433a1f9bbb2de/packages/scenario-capsules/FORMAT.md), [schema](https://github.com/WuFuxiu/HuiMate/blob/78f272f12df7b90649b3a2413d1433a1f9bbb2de/packages/scenario-capsules/schema.json) and repository-local [creation skill](https://github.com/WuFuxiu/HuiMate/blob/78f272f12df7b90649b3a2413d1433a1f9bbb2de/skills/scenario-capsule-creator/SKILL.md). That skill's validator depends on the HuiMate checkout; copying its entry point alone does not make it portable.

Keep YAML under a documented attachment directory, for example `capsules/`. This directory is an authoring convention, not a host discovery path. Include the parent/category YAML when children refer to it, and list all delivered files in the product README. Never include credentials or the author's machine-specific paths.

Check these consumer-facing constraints:

- `schemaVersion` is `huimate.scenario-capsules.v1`; each file contains one YAML document of at most 1 MiB. Unknown fields, duplicate mapping keys, aliases, tags and merge keys are rejected.
- Capsule IDs must be unique across all registered files. `parentId` supports at most two directory levels; parent and child may be in separate files but must be validated together.
- `sources.*.skill` is the actual callable Skill name visible to the target session, which may differ from source frontmatter after installation. Verify installed names before declaring readiness.
- Workflow capsules reference real domain templates with exact versions. Static YAML checks do not prove external templates, nodes, ports or pages exist. A click fills an editable instruction; it does not send or execute business nodes.

When a matching HuiMate checkout is available, run from its root, replacing the example paths with all related prepared YAML files:

```sh
bash scripts/node.sh skills/scenario-capsule-creator/scripts/validate.ts /path/to/product/plugin/capsules/category.yaml /path/to/product/plugin/capsules/scenarios.yaml
```

If that validator is unavailable, report capsule validation as not performed; do not substitute `plugin_package.py validate` for it. The Python packager checks the plugin tree and ZIP constraints, not the capsule schema or registration. Run the normal plugin validate/pack commands afterward and inspect the ZIP to confirm the YAML attachments are present.

## Administrator registration

Put these steps in the delivered product README. Packaging alone does not authorize changing a running host.

1. Import the product plugin and configure/enable its required Skills and services through the normal plugin workflow.
2. Copy the delivered YAML into an administrator-managed deployment location on the machine running the HuiMate Host. Use a stable location independent of temporary upload directories and generated installation snapshot paths.
3. Merge the files' absolute paths into the active profile's existing `cordis.patch.yml` entry. Preserve other capsule paths and settings; do not add a duplicate entry or replace the entire profile. The following illustrates the entry shape, using a deployment placeholder:

```yaml
- id: huimate-scenario-capsules-host
  config:
    files:
      - /absolute/deployment/capsules/category.yaml
      - /absolute/deployment/capsules/scenarios.yaml
```

Apply the changed host configuration through the deployment's normal configuration/restart procedure. The registry captures its path list when the service is constructed; file-content hot reads do not imply newly added paths are picked up without applying configuration. Contents of already registered files are re-read on every list query and message admission, so content edits need no restart.

Check the home-page capsule list in the intended session and its diagnostics. Confirm grouping, required Skills, selection mode and editable input text. Duplicate IDs and missing Skills make entries unavailable; do not claim a successful import alone proves availability. Test real model/template/page behavior separately when authorized.

For upgrades, explicitly update and revalidate the administrator-managed YAML. To withdraw capsules cleanly, remove their paths from the registration and apply the host configuration, handling dependent child entries as well. Removing only the files also disables the entries but leaves missing-file diagnostics; disabling or uninstalling the product plugin does not remove this registration. Already admitted messages retain their configuration snapshot.

Report four distinct results: YAML validation, ZIP attachment preservation, administrator registration/UI availability, and real runtime verification. Mark any unperformed step explicitly.
