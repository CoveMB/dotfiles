# Codex dotfiles

`setup-codex.sh` installs the portable, non-secret parts of the personal Codex setup.
It is safe to run more than once and is called by both new-computer install scripts.

## Managed files

- `AGENTS.md` contains global working instructions and canonical RTK usage guidance.
- `coordination-monitors.md` contains conditional monitor procedures. The global
  instructions require it only for recurring coordination monitor tasks, resolved
  beside the canonical `AGENTS.md` target; routine coding needs no extra read.
  It travels with the checkout and needs no separate setup link.
- `agents/` contains personal custom-agent definitions.
- `marketplace.json` exposes local personal plugins from repositories under
  `~/Code/CoveMB/`.
- `config.toml.template` contains portable Codex defaults. The setup script copies
  it to `~/.codex/config.toml` only when that file does not already exist.

The machine-local `~/.codex/RTK.md`, when retained, is a compatibility pointer to
the RTK section in `AGENTS.md`; it is not a second normative source. The setup
script backs up legacy RTK files rather than installing a separate copy.

Codex writes project trust, hook hashes, installed-plugin state, local paths, and
desktop state into `~/.codex/config.toml`. For that reason, the live file remains
machine-local rather than being symlinked into this public repository.

## Explicitly excluded

The setup does not track credentials, histories, memories, approval-generated
rules, sessions, logs, databases, worktrees, caches, attachments, browser or
Computer Use session state, native-host manifests, installed plugins, generated
marketplace snapshots, third-party or system skills, backups, or app-support data.
The local `movebook-ruleset` skill is also intentionally excluded.

`~/.codex/browser/config.toml`, `~/.codex/computer-use/config.json`, and
`~/.codex/config.json` are plugin or app-generated files, not portable personal
configuration. Empty `~/.codex/instructions.md` and inactive hook backups are also
excluded.

## Manual setup

From the dotfiles checkout:

```sh
./setup-codex.sh
```

Existing managed paths are moved into a timestamped directory under
`~/.codex/backups/` before symlinks are created. Existing `config.toml` files are
never overwritten. Restart Codex after setup so it reloads the configuration.

## Optional Ponytail plugin

Ponytail is installed as an explicit-only complexity-review tool. Its automatic
mode remains off, and its lifecycle hooks remain untrusted unless separately
reviewed and approved.

Create `~/.config/ponytail/config.json` with:

```json
{
  "defaultMode": "off"
}
```

Pin the marketplace catalog to v4.9.0, then install:

```sh
rtk codex plugin marketplace add DietrichGebert/ponytail --ref v4.9.0
rtk codex plugin add ponytail@ponytail --json
```

The upstream catalog currently declares the plugin source at `ref: main`, so
`--ref v4.9.0` pins the catalog snapshot but not necessarily the installed
plugin checkout. Record the installed cache `HEAD` and review
`v4.9.0..HEAD` before use. The initial 2026-08-22 installation resolved to the
clean upstream revision `2ed6c52c9d7e5e56942508591085fd45dea277d3`;
revalidate this on every reinstall or upgrade.

Restart Codex, leave the `SessionStart`, `SubagentStart`, and
`UserPromptSubmit` hooks untrusted, and invoke only `@ponytail-review` or
`@ponytail-audit` during the initial evaluation. Validate every finding against
current code before accepting it. Do not enable marketplace auto-updates; review
the resolved source revision and hook hashes before each manual upgrade.

To uninstall during this hook-free evaluation:

```sh
rtk codex plugin remove ponytail@ponytail --json
rtk codex plugin marketplace remove ponytail --json
```

Then remove `~/.config/ponytail/config.json` and restart Codex.
