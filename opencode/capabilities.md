# Capability disposition

This is the approved first-phase integration boundary. Installed versions, exact
commits, paths and observed results belong in the machine-local setup record.
Discovery and static validation do not prove native model behavior.

| Capability | OpenCode treatment | Codex treatment |
| --- | --- | --- |
| Humanizer: editorial, faithful, plain-language | Complete shared skills; preserve source-handling rules | Refresh enabled local package from reviewed main |
| Accessibility: dictation, low-load companion, prose repair, reading reducer | Complete shared skills/resources | Refresh enabled local package from reviewed main |
| Research: all 29 skills including orchestrator | Use the repository's **full portable** exporter; retain shared resources and helpers. Do not combine the 28 standalone exports with a native orchestrator | Refresh complete native package from reviewed main |
| Incremental plan and test design | Share complete latest-main bundle and native host compatibility reference; preserve gates and three independent reports | Refresh main; leave unmerged portability branch untouched |
| Material review and simplification | Complete canonical sibling bundles; trusted workspaces/changes only. Do not import generated command-wrapper skills | Refresh native package; native installer regenerates two command wrappers |
| Cleanup / task-disk-review | Explicit-only. Complete runtime package; OpenCode-managed resources report-only; destructive cleanup remains a human action | Refresh production identity only; preserve experimental registrations and disabled aliases |
| Recursive Mode: nine skills | Defer bootstrap activation until shared-instruction writes are adapted and tested | Refresh latest upstream runtime with existing Codex packaging metadata |
| Caveman 4.0.1 | Legacy Lite/Full map to normal Caveman; Ultra/Mega remain explicit-only. Cavecrew uses existing roles/models. Compression backend remains separately qualified and authorized | Restore the same marketplace identity; install the reviewed package without the broad upstream installer |
| Superpowers: 15 skills | Complete skills-only bundle; translate tools/roles in opencode-compat.md. No bootstrap hook. Browser companion unavailable; history requires a selected transcript | Leave account-managed installation unchanged |
| Ponytail: six skills | Isolated skills-only copy; add `disable-model-invocation: true` to every SKILL.md. Preserve README, license and gain's cited benchmark. No native plugin/hooks, persistent state or automatic Full mode | Leave installation and default-off configuration unchanged |
| Obsidian Bases | Share complete personal bundle; rendering acceptance separate | Unchanged |
| GitHub comment helper | Share complete personal bundle; existing gh authentication and bounded shell approval, no automatic login or replies | Unchanged |
| Context7 | Reuse already shared discovery skill; separate native MCP registration with `codemode:false`. No copied credential | Existing registration unchanged |
| Documents, PDF, spreadsheets, presentations, artifact templates, visualization | Keep in Codex for this phase; do not copy skills whose required host tools are absent | Existing app/runtime-managed installations unchanged |
| Browser, Chrome, computer use, unified computer use, app tools | Disabled/deferred in this OpenCode pilot | Existing integrations unchanged |
| CodeRabbit, Zotero, GitHub connector, Google Drive, Spotify, Security, Pages, Sites, plugin management, work pets | Keep hosted/account integrations in Codex. A surviving legacy configuration flag is not proof of an available integration | Preserve current account/plugin state; do not reinstall from unrelated local repositories |
| Consulting | Do not expose while disabled | Preserve disabled state |
| System image generation, OpenAI docs, skill creator/installer | Keep host-specific entrypoints in Codex until individually adapted; ordinary public documentation remains available through native tools | Unchanged |
| movebook-ruleset and dev-workflow | Intentionally absent; no recovery or replacement | Leave deleted |
| Credentials, saved approvals, trust hashes, memory, chats and automations | Separate app ownership; no import | Unchanged |

All installed and discovered skill IDs must be checked for collisions. Do not
register both standalone and full bundles, both canonical material skills and
generated wrappers, or Context7 twice. Native OpenCode IDs use directory names,
without Codex marketplace/plugin prefixes. Keep the complete immutable source
bundle even when registering individual skill roots.

The local setup input file is an allowlist, not an automatic scan of every cache
or repository. Adding a package later requires reviewing its invocation policy,
dependencies, tool assumptions and write locations first.
