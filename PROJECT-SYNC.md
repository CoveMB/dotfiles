# Project lists shared from Codex

`sync-projects.py` copies the local Codex project folder list to OpenCode and
Antigravity. Codex remains the source. It does not synchronize conversations,
files, agent settings, credentials, permissions, cloud projects or Git state.
The command is on demand; no watcher, login item or scheduled task is installed.

## Preview and apply

Requires macOS, Python 3.11+, initialized desktop apps, and the OpenCode background
service. The adapters currently target OpenCode 2.2.5 and Antigravity 2.29.0;
application upgrades require review before another write.

From the dotfiles checkout, preview without changing application state:

```sh
rtk proxy python3 -B ./sync-projects.py
```

Save work and fully quit **both OpenCode and Antigravity** before applying:

```sh
rtk proxy python3 -B ./sync-projects.py --apply
```

This adds missing projects while preserving destination-only projects. To replace
OpenCode's visible project selection with Codex's current folders instead:

```sh
rtk proxy python3 -B ./sync-projects.py --replace-opencode
rtk proxy python3 -B ./sync-projects.py --replace-opencode --apply
```

Replacement hides old OpenCode entries from the visible selection. Their folders,
sessions and project registry records remain intact. Antigravity remains
additive in both modes; its existing project records are never rewritten.
Reopen the apps after success. Their sidebar ordering remains app-owned.

The command refuses to write when either desktop app is running, process state
cannot be inspected, OpenCode has an active session, another synchronization is
running, or the reviewed app versions have changed. Keep the OpenCode background
service available; if it is unavailable, open OpenCode, then quit its desktop
app before retrying. It never force-quits an app or starts an agent task.

## Ownership and implementation

| State | Treatment |
| --- | --- |
| `~/.codex/state_5.sqlite` | Read-only `projects` and `project_roots`; canonical absolute paths deduplicated |
| OpenCode native local service | Reads `/api/project`, resolves missing folders through `/api/location`; no model prompts |
| OpenCode desktop `drafts.sqlite` | Changes only the local `usedProjectIDs` and `lastProjectID` fields in the `opencode.global.dat` / `server` row, while the app is closed |
| `~/.gemini/config/projects/*.json` | Atomically adds missing Antigravity project records with empty explicit grants and inherited defaults |
| `~/.local/state/project-sync/` | Local previews, narrow before/after receipts, registration receipts and exclusive writer lock |

Both destinations keep internal state beyond their project registry. No supported
headless sidebar setter was established, and Antigravity's CLI project option
starts a session. The closed-app adapters therefore use the inspected native
storage contracts and stop on version changes. Do not hot-edit these files or
symlink the apps' databases together.

OpenCode folder resolution is the same native operation used when adding a
project. It can load the folder's existing configuration and integrations. It
does not request model execution. Use this sync only for trusted Codex project
folders; review any new project-local plugin or MCP configuration first.

Source folders must exist. Multi-root Codex projects require an explicit mapping
and stop the operation. Antigravity names cannot collide with an existing project
for a different folder. A source folder archived in OpenCode stops the preview
and apply before registration; review its archive state in OpenCode before retrying.
Existing Antigravity resources are checked before adding
duplicates. The v2 migration marker grants no permissions; new records have no
explicit allow rules and retain the app's global defaults.

Receipts contain project names, local paths and narrow selection fields, so keep
them outside Git. OpenCode service credentials are used only in memory for its
loopback API; remote server connection settings are neither logged nor backed up.

## Recovery

Each apply prints its recovery directory before native registrations or project
list writes. Successful completion creates `complete.json`. A failed or interrupted
apply can have partially registered projects or partially updated lists; inspect
the receipt before retrying.

With both desktop apps fully quit:

```sh
rtk proxy python3 -B ./sync-projects.py --rollback /absolute/recovery/directory --apply
```

Rollback restores OpenCode's selection only if it still matches the recorded
post-sync value. It removes a new Antigravity record only if its content and file
identity still match. Later edits or recreated files are preserved. OpenCode's
new registry rows and all sessions remain intact, including on rollback.
Do not modify destination records concurrently with rollback: ownership comparison
and removal are separate filesystem operations.
If interruption occurs between publishing an Antigravity record and recording
its file identity, rollback lists it under `unconfirmed_antigravity` and leaves
it untouched for inspection. Never delete an unconfirmed file automatically.

## Verification

```sh
rtk proxy python3 -B -m unittest discover -s tests -p sync_projects_test.py -v
```

Tests use real disposable SQLite databases and files to check preview behavior,
replacement/additive reruns, source and unrelated-state preservation, stale-state
refusal, name collisions, exclusive writes, atomic publication and guarded
rollback. Native app discovery after applying is separate evidence.

The `--home` option targets an explicit fixture home. It does not bypass app
process/version checks or grant authority to change another user's files.

## Optional section labels, colors and ordering

Preview the Codex presentation mapping as well as membership:

```sh
rtk proxy python3 -B ./sync-projects.py --sync-presentation
```

After reviewing the changes and fully quitting both destination desktop apps:

```sh
rtk proxy python3 -B ./sync-projects.py --sync-presentation --apply
```

Without this flag, the existing membership-only interface is unchanged. The
presentation preview includes a `pending` summary and explicit per-project
before/after values. Names are derived from Codex each time, so moving a project
between sections replaces its prefix rather than stacking another prefix.

| Source section | OpenCode color | Display label in both destinations |
| --- | --- | --- |
| Egeria | Blue | `[Egeria] name` |
| Plugins | Orange | `[Plugins] name` |
| External Plugins | Yellow | `[External Plugins] name` |
| Archives / Archive | Gray | Original section spelling in brackets |
| No custom section | Green | Original Codex name, without a prefix |

These prefixes are display metadata; folders, repositories, permissions and
conversation data are unchanged. Archives is a visual category, never an archive
operation. OpenCode native colors can replace automatic logos with colored
avatars; manual icon overrides stop presentation apply for review. Unknown new
custom sections require a color mapping, rather than silently receiving Green.

Antigravity follows Codex's flattened visible project order using Custom Order.
Destination-only projects retain their established relative order after source
projects. If several destination-only projects have no saved order, or activity sorting
is active for multiple destination-only projects, the command stops: native
ordering uses conversation activity, which this command does not inspect. Establish their custom order in Antigravity before retrying.

OpenCode's activity-based ordering remains unchanged. Neither app receives real
collapsible custom section headers; Antigravity project colors are unavailable
in this version. No plugin, app patch or timestamp manipulation is installed.

Presentation runs write v2 recovery records; the command still reads original
v1 membership receipts. Recovery restores matching owned metadata only and
preserves later user changes. Interrupted, unconfirmed presentation writes are
reported separately and retained for inspection. Existing Antigravity project
files are renamed through a field merge, not deleted during presentation rollback.

OpenCode uses its native sparse PATCH operation for names/colors. Installed
2.2.5 code explicitly maps empty-string resets to SQL NULL/response absence;
that restores originally absent metadata. Original literal empty-string values
are rejected because this API cannot restore them exactly. Omitted icon URL,
manual override, canonical folder and startup-command fields are preserved.
