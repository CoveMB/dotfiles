# Codex dotfiles

`setup-codex.sh` installs the portable, non-secret parts of the personal Codex setup.
It is safe to run more than once and is called by both new-computer install scripts.

## Managed files

- `AGENTS.md` contains global working instructions and the RTK usage guidance.
- `agents/` contains personal custom-agent definitions.
- `marketplace.json` exposes local personal plugins from repositories under
  `~/Code/CoveMB/`.
- `config.toml.template` contains portable Codex defaults. The setup script copies
  it to `~/.codex/config.toml` only when that file does not already exist.

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
