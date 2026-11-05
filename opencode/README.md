# OpenCode alongside Codex

This setup targets the OpenCode 2.2 desktop app. It shares the existing global
instructions and four role prompts, while rendering native OpenCode settings.
Codex TOML, authentication, saved approvals, memory, chats and schedules remain
independently owned. The setup never calls the full-machine installers.

See [capabilities.md](capabilities.md) for each plugin/skill's sharing boundary.
The two material command aliases load their canonical skills; they contain no
embedded shell execution and retain the original workflow gates.

## Install

Requires Python 3.11+, an installed OpenCode app, RTK, and reviewed complete skill
bundles at durable local paths. The desktop app's bundled CLI is sufficient;
a separate CLI installation or shell PATH change is unnecessary.

Create a **local, untracked** input file outside this repository:

```json
{
  "model": "github-copilot/gpt-6.1-terra",
  "skills": [],
  "protected_paths": [],
  "context7": {
    "type": "remote",
    "url": "https://mcp.context7.com/mcp",
    "oauth": false,
    "codemode": false
  }
}
```

Set `model` to a provider/model actually available through your own OpenCode
connection. Finish with a small native provider request: catalog presence alone
does not prove account-level model support. Do not copy a Codex login file.
Each `skills` entry is an absolute
path to one reviewed skill directory containing SKILL.md, with its complete
parent package retained for references and helpers. Native IDs are directory
names; duplicates are rejected. Existing `~/.agents/skills` content is already
discovered and must not be registered again. `protected_paths` contains any
additional shared package roots/settings that must remain inputs.

Run from the durable dotfiles checkout:

```sh
rtk proxy sh ./setup-opencode.sh --sources /absolute/local-inputs.json --dry-run
rtk proxy sh ./setup-opencode.sh --sources /absolute/local-inputs.json
```

The helper creates only `AGENTS.md` and `opencode-compat.md` links and, when
absent, a machine-local `opencode.jsonc`. It derives source links from the current
checkout and keeps the live JSON separate because the app can manage it.
All link conflicts, broken links, missing sources and symlinked destination
directories stop before creating destinations. An existing regular
`opencode.json` or `opencode.jsonc` is preserved: manually review/merge an update
instead of assuming rerunning the helper refreshes it.

Global destinations follow `XDG_CONFIG_HOME` and `XDG_STATE_HOME` when set.
`--home`, `--config-dir` and `--state-dir` support disposable fixtures or an
explicit destination. Nonempty `OPENCODE_CONFIG` or `OPENCODE_CONFIG_DIR` stops
installation until their precedence is reviewed. Do not repurpose HOME or
CODEX_HOME for tests. The helper performs no network access or package installs.

## Ownership and updates

| Input | Treatment |
| --- | --- |
| `codex/AGENTS.md` | Shared once via the OpenCode global link |
| `codex/agents/*.toml` | Read description/prompt only; translate to four native agents during seeding |
| `opencode.json.template` | Portable baseline; local model, skills, policies and MCP registration are rendered |
| `opencode-compat.md` | OpenCode-specific tool and workflow mapping |
| Plugin packages | Reviewed immutable clean exports; never broad links to mutable caches |
| Local inputs/setup records | Outside Git, authentication and application discovery directories |

Refresh clean plugin exports from reviewed commits using each repository's
packager. Preserve dirty checkouts and unmerged branches. Inspect delivered
files, not merely `.gitignore`: Codex's installer can copy VCS/evaluation files
from an overly broad source. Reinstall enabled local plugin IDs through the
supported lifecycle; preserve marketplace identity and disabled/experimental
states. Keep a separate old runtime export and exact source-registration backup
before replacement. A same-version source refresh needs an explicit reinstall.

After source changes, rerender in a fixture and review the minimal diff against
the live configuration. Rerunning setup intentionally does not overwrite user
configuration. Recheck app-native discovery, permissions and provider selection;
schema parsing alone is insufficient. No automatic reverse synchronization is
installed. Source paths and hashes belong in the local setup record.

## Permission limits

Shell, edits and external-directory access ask for approval. Code Mode and
browser control are disabled in this pilot. The three read-only roles deny
shell, edits, delegation and unlisted tools. The implementation role also cannot
delegate. The coordinator uses no more than two children; only depth one is
enforced by native configuration.

Protected absolute paths are denied through `tool.use` policies, including
aliases and resolved targets. Internal paths may be location-relative, so these
policies do not provide a universal filesystem boundary if a protected package
itself becomes the active workspace. Do not open shared configuration/package
roots for writable OpenCode work. Shell runs with user authority, and approved
commands can bypass normal edit tools. Do not claim Codex sandbox equivalence.

## Rollback

Successful setup prints an ownership manifest under the resolved state directory.
Preview and then remove only unchanged additions:

```sh
rtk proxy sh ./setup-opencode.sh --rollback /absolute/setup-manifest.json --dry-run
rtk proxy sh ./setup-opencode.sh --rollback /absolute/setup-manifest.json
```

Rollback checks type, device/inode, mode, link target or content hash. Modified
or recreated files and unrelated files are retained. Empty created directories
and the recovery record remain. It does not uninstall plugins, reverse manual
merges, or remove app state. Plugin rollback is a separate supported reinstall
from the recorded clean previous runtime source; never reset the whole cache.

## Verification

```sh
rtk proxy python3 -B -m unittest discover -s tests -p setup_opencode_test.py -v
```

Tests exercise dry runs, relocation, conflicts, missing inputs, reruns and guarded
rollback against real disposable files. App-native permission/discovery checks,
provider authentication, MCP connection and model behavior are separate evidence.
Use separate worktrees for concurrent writers; never let both apps mutate the
same checkout simultaneously.
