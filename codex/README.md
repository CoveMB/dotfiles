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
- `marketplace.json` exposes local personal plugins from `~/Code/CoveMB/` and
  the existing `~/.codex/plugins/incremental-and-test-plans/` source directory.
  Restore those source directories before installing their plugins on a new machine.
- `config.toml.template` contains portable Codex defaults. The setup script copies
  it to `~/.codex/config.toml` only when that file does not already exist.
  The template intentionally keeps `gpt-6.2-sol`; an existing machine can select
  another model locally.

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

`~/.codex/browser/config.toml`, `~/.codex/computer-use/config.json`, and
`~/.codex/config.json` are plugin or app-generated files, not portable personal
configuration. Empty `~/.codex/instructions.md` and inactive hook backups are also
excluded.

## Manual setup

Install Codex, RTK, and Node.js 24 LTS before setup; Context7 runs through `npx`.
The macOS installer selects Node.js 24. The setup script only links and copies
configuration; it does not install applications or plugin source repositories.

From the dotfiles checkout:

```sh
./setup-codex.sh
```

Existing managed paths are moved into a timestamped directory under
`~/.codex/backups/` before symlinks are created. Existing `config.toml` files are
never overwritten. Restart Codex after setup so it reloads the configuration.

## Optional Ponytail plugin

Ponytail is explicit-only, as defined in `AGENTS.md`. Keep its automatic mode off
in `~/.config/ponytail/config.json`:

```json
{
  "defaultMode": "off"
}
```

The installation inspected on 2026-10-28 reports version 5.3.2 at source revision
`09c434ab73ca43761c5d8b0c5d341926c2fba710`. Its configured marketplace catalog is
still pinned to v4.9.0, while the plugin entry in the inspected source targets
`main`. A catalog pin therefore does not establish the installed plugin version.

The existing marketplace and installation commands are:

```sh
rtk codex plugin marketplace add DietrichGebert/ponytail --ref v4.9.0
rtk codex plugin add ponytail@ponytail --json
```

After reinstalling or upgrading, verify the installed manifest version and source
revision, and review any changes before use. These commands do not guarantee
restoration of the inspected 5.3.2 revision. Keep marketplace auto-updates off.

Automatic mode and lifecycle-hook trust are separate settings. Review and approve
hooks separately on each machine; do not copy saved hook trust hashes into these
dotfiles. Saved trust hashes alone do not establish review of the currently installed
hook contents. Invoke Ponytail only when explicitly requested and validate
its findings against the current code.

To uninstall:

```sh
rtk codex plugin remove ponytail@ponytail --json
rtk codex plugin marketplace remove ponytail --json
```

Then remove `~/.config/ponytail/config.json` and restart Codex.
