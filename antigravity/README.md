# Antigravity shared configuration

Python 3.11+ and RTK are local prerequisites. This entrypoint generates native
Antigravity rules, skill discovery entries and four child role definitions from
reviewed local inputs. It does not install apps, run another host's installer,
change accounts/models, initialize MCP, or edit app-owned settings.

Keep the shared `codex/AGENTS.md` and role TOML files as the authoring sources.
Generated rules are independent regular files. Each numbered section is delivered
once, including the trailing Context7 policy. Removing the generated header through
`<!-- canonical-body -->` and joining bodies in filename order reconstructs the
original source bytes. Source-relative links retain their canonical origin.

## Prepare and qualify

Supply an absolute local JSON file with `skills` (exact complete skill directories)
and `role_tools` (`read` and `write` arrays of **observed native tool IDs**).
The optional `roles` list selects from the four canonical role identities (all
four by default for qualification). Use `roles: []` to withhold unqualified roles
entirely from discovery; failed native boundaries must not be promoted.
This selects new outputs; it does not remove previously installed definitions.
Existing definitions need a separately reviewed removal using their ownership
records and a fresh discovery check before claiming those roles are disabled.
Bind `resources` as an absolute-file-path to SHA-256 map for the complete reviewed
package closure, including entrypoints and required sibling references, scripts,
templates and licenses outside individual skill directories. Every selected skill
entrypoint must be in that inventory. The installer verifies every bound file
before mutation and again before publication; missing or changed files abort.
Missing resources, metadata collisions, unsupported tool IDs and destination
conflicts stop installation. Sources must be complete reviewed bundles; a bare
SKILL.md is insufficient for a skill with sibling resources.

Start in a disposable project's `.agents` folder. Inspect native discovery and
permissions before any provider request. Global promotion requires the capability
checks in `capabilities.md`; failed or unexercised boundaries remain deferred.

```sh
rtk proxy sh ./setup-antigravity.sh --sources /absolute/inputs.json --config-dir /absolute/pilot/.agents --state-dir /absolute/recovery --dry-run
rtk proxy sh ./setup-antigravity.sh --sources /absolute/inputs.json --config-dir /absolute/pilot/.agents --state-dir /absolute/recovery
```

`--home` supports isolated home fixtures. The default destination is
`~/.gemini/config`; the default state root is `~/.local/state/antigravity-setup`.
Protected canonical sources and existing Codex/OpenCode configuration cannot be
output or recovery destinations, including through directory symlinks.
Protected path names are reserved case-insensitively, including future descendants,
so macOS case aliases cannot bypass the guard.
The script preflights the entire addition set, stages complete bytes with private
permissions, records inode/hash ownership, then publishes exclusively. A journal
exists before any discovery file is exposed. Keep the returned manifest path.
Existing identical outputs are preserved; modified/recreated outputs are conflicts.
No update watcher or reverse synchronization exists.

The app-owned `config.json` and existing `mcp_config.json` are always left alone by
the installer. Permission changes require an exact reviewed native diff. Initialize
an empty MCP file only as a separate guarded merge after backing up its original
bytes; expose only the verified Context7 documentation tools and no credentials.

## Recovery and refresh

```sh
rtk proxy sh ./setup-antigravity.sh --rollback /absolute/recovery/manifest.json --dry-run
rtk proxy sh ./setup-antigravity.sh --rollback /absolute/recovery/manifest.json
```

Rollback validates all targets before mutation and preserves changed or recreated
files. Unchanged files are moved into retained `.rollback-*` recovery directories
beside their original location. These preserve writes through open descriptors;
inspect their returned paths before any separately authorized cleanup. App settings
and MCP merges have separate reverse diffs; never reset all permissions or restore
an entire settings file over concurrent changes. The canonical source and the other
hosts' instruction links are outside rollback ownership.

For refresh, freeze a reviewed candidate, rerender into a new fixture, inspect its
minimal destination diff and requalify affected capabilities. Merge existing
destinations deliberately; the absent-file installer does not overwrite them.

## Validation

```sh
rtk proxy python3 -B -m unittest discover -s tests -p setup_antigravity_test.py -v
rtk proxy python3 -B -m unittest discover -s tests -p setup_opencode_test.py -v
rtk proxy sh tests/setup_codex_test.sh
```

Filesystem tests establish local generation/recovery behavior. Native discovery,
effective permissions, provider operation, role restrictions and skill routing
need separate observed evidence. Never infer every workflow works from a catalog.
