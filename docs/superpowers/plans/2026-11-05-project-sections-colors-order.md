# Project Sections, Colors and Order Implementation Plan

> **For agentic workers:** Use `superpowers:executing-plans` to implement the tasks below with TDD, then obtain an independent read-only review before a live attempt. Implementation, independent review and native acceptance are complete. The user approved the final live preview and restarts; the reviewed command was applied successfully.

**Goal:** Extend the existing dotfiles command to reflect Codex project sections, the requested colors, and the visible project order wherever the destination supports them.

**Architecture:** Keep Codex read-only. Add one opt-in `--sync-presentation` mode to `sync-projects.py`, preserving the current membership-only interface. Use native OpenCode metadata and Antigravity names/order; represent unavailable custom sections with readable project-name prefixes. Keep backups and recovery evidence outside Git.

**Tech stack:** Existing Python 3.11+ standard-library command, SQLite, JSON, loopback HTTP, macOS process checks, unittest. No new dependency, plugin, daemon or application patch.

**Spec:** The user's palette and requirements below, plus `PROJECT-SYNC.md` for the existing membership, permission and recovery boundaries.

## Requirements and verified disposition

Checked against installed OpenCode **2.2.5**, Antigravity **2.29.0**, current Codex state, Antigravity's native menus and current primary documentation on 5 November 2026.

| Source category | Current projects | Requested color | OpenCode value |
| --- | ---: | --- | --- |
| Egeria | 3 | Blue | `blue` |
| Plugins | 7 | Orange | `orange` |
| External Plugins | 3 | Yellow | `yellow` |
| Archives | 2 | Grey | `gray` |
| Not in a custom section | 8 | Green | `green` |

The current Codex section is named **Archives**; accept the user's **Archive** spelling as the same palette category without renaming Codex. Color values identify native theme colors, not a promise of identical RGB rendering across themes.

| Capability | OpenCode 2.2.5 | Antigravity 2.29.0 | Planned treatment |
| --- | --- | --- | --- |
| Custom sections containing projects | No equivalent native control established | No equivalent native control established | Prefix grouped display names: `[Egeria] egeria-scaffold`, `[Plugins] humanizer-plugin`, etc. Ungrouped names keep their base label |
| Project color | All five requested colors supported | No native project-color field/control established | Set OpenCode `icon.color`; report Antigravity color as unavailable |
| Project order | GUI sorts by activity | Native Custom Order available | Match Codex's flattened visible project order in Antigravity; leave OpenCode activity data intact |
| Collapsible custom section headers | Not established | Not established | Do not claim prefixes provide collapsible sections |

Antigravity inspection: **Display Options → Group By** offered **Project, Status, None**. **Sort Projects** showed **Custom Order**. Its project menu offered copy name, project settings, reveal folder and delete, without a custom-section action. Installed frontend code has project ordering and conversation grouping, but no custom project-section or project-color owner was established. These findings are bounded to the inspected version, not claims about every future release.

Creating dummy projects as headings would create real project records. Combining several repositories into one Antigravity project would change agent context and permissions. Neither represents a harmless sidebar section, so neither is included. Public plugin documentation did not establish a supported extension point for inserting custom headers into the built-in project list. A separate custom UI or app modification is outside this small sync command.

### Primary and installed-source evidence

- [OpenCode project metadata API](https://opencode.ai/v2/docs/api/#project): native project name and icon metadata. The installed `Project.Icon` schema contains `url`, `override` and `color`.
- Installed OpenCode archive, `out/renderer/assets/main-DH32_HOX.js`: `qZ` accepts `blue`, `orange`, `yellow`, `gray` and `green`; `KZ` gives a manual icon override precedence over color. Its project list sorts by `time.active`.
- [Antigravity changelog](https://antigravity.google/docs/changelog): version 2.24.0 documents separate project sorting with Custom Order; native UI confirms it in 2.29.0.
- Installed Antigravity frontend: `projectsOrder` is a serialized JSON array of project IDs; `projectsFolderSortBy` selects project sorting and defaults to `custom`. Conversation sorting is separate and must not change.
- [Antigravity project model](https://antigravity.google/docs/projects/) and [plugin capabilities](https://antigravity.google/docs/build-plugins): neither provided a supported custom project-section contract in this investigation.

## Global constraints

- The user approved implementation and independent review. Do not change live application settings, rename live destination projects, restart apps, commit or push without the final live-preview approval.
- Preserve all existing staged, unstaged, untracked and committed work. Keep the existing checkout and exact unrelated dirty-file contents.
- Preserve the current command's preview default, add-only membership behavior, explicit `--replace-opencode`, loopback-only transport, proxy/redirect refusal, app/version/session gates and exclusive writer lock.
- `--sync-presentation` without `--apply` previews membership, names, colors, order and unsupported capabilities. Existing invocations without the new flag retain membership-only behavior.
- Change only display metadata and the narrowly owned Antigravity project-order settings. Do not change folder paths, repository names, branches, settings, commands, permission grants, credentials or conversations.
- **Archives is a display category.** It never sets an archived flag, hides a project or deletes data.
- Never change activity timestamps to fake an OpenCode order. Do not patch installed app bundles or introduce a custom sidebar plugin.
- Current OpenCode manual icon overrides: none among the 23 local projects. Some projects have automatic icons. Native color selection can replace automatic imagery with a colored avatar; include that visual change in preview. If a manual override appears before apply and masks the requested color, stop and report it rather than remove the override silently.
- Unknown new custom sections need an explicit color mapping. Green applies to genuinely unsectioned projects, not silently to an unmapped custom section.
- Keep source aliases, account identifiers, runtime files and receipts out of Git. Parse only the metadata needed for local project identities and discard account/user fields.

## Review focus

1. Codex section order, group membership and project identity are separate from database position; legacy IDs and ChatGPT-backed aliases must resolve to the same local folder.
2. Section names, colors and destination names can change between preview and apply; do not apply a stale presentation plan or repeatedly add prefixes.
3. Native metadata patch/reset semantics and icon precedence must be qualified; rollback must restore prior display values without overwriting unrelated fields.
4. Antigravity stores UI settings as strings inside JSON; restore only the owned order/sort fields, retaining unrelated state and destination-only projects.
5. An interruption or later user edit must leave a useful receipt and preserve uncertain/newer state; app updates must stop unsupported adapters.

Each risk has behavioral tests in the owning task below. Static/fixture tests remain separate from native appearance/order acceptance.

## Task 1: Read Codex layout and preview the proposed presentation

**Files:** modify `sync-projects.py` and `tests/sync_projects_test.py`.

**Interfaces:** add `source_layout(locations, projects) -> list[dict]`. Each result contains the existing source project ID/canonical folder, base name, custom section ID/name or none, desired display name, desired color and visible position. `build_plan` includes this layout and exact destination-field diffs only in `--sync-presentation` mode.

- [x] Write tests first for section membership, local/ChatGPT alias resolution, visible ordering, duplicate aliases, ungrouped projects and the exact five-color mapping. Run the new tests and verify RED before implementation.
- [x] Resolve local identities using `projects.metadata["codex.localProjectId"]`. Decode `codex.chatGptBacking` when it is itself JSON text and use only its `projectId` for `chatgpt:project:...` aliases. Never carry `accountId` or `userId` into a plan or receipt.
- [x] Select the sole section collection that resolves against the current local project aliases. If multiple account collections are ambiguous, stop with a sanitized diagnostic; never guess or export account keys.
- [x] Read Codex's existing `sidebar-custom-sections-v3`, `sectionOrder`, section `itemKeys`, `unified-sidebar-project-order-v1` and pinned project placement. Filter to known local folders; ignore individual chat/thread entries. Do not treat collapse state as hiding a project.
- [x] Flatten visible sections in Codex order. Custom sections use their `itemKeys` order; the ordinary Projects group uses the global manual project order filtered to unsectioned local folders. Resolve pinned appearances without duplicating folders. Conflicting custom-section membership or unresolved local project references stop presentation apply with diagnostics.
- [x] Current expected group flow is **Egeria → Plugins → ordinary Projects → External Plugins → Archives**. Do not hard-code this flow: read it each run. The ordinary group currently contains eight unsectioned projects and sits between Plugins and External Plugins.
- [x] Derive grouped names once from Codex's base name: `[Section] base-name`. Moving to another section replaces the prefix; moving out removes the sync-owned prefix. Never derive the next label by prefixing the already-prefixed destination name.
- [x] Add `--sync-presentation`; without it retain the existing membership contract. Preview lists before/after names/colors, actual Antigravity order, automatic-icon effects and unsupported native section/color/order capabilities.
- [x] Run the new source-layout tests to GREEN and retain the original membership tests.

**Acceptance:** the current 23 local projects resolve once each; 15 receive section labels and their category colors; eight remain unprefixed and receive Green in OpenCode. Tests cover moving/renaming sections, both Archive spellings, future unmapped sections, aliases, pinned items, Unicode labels, stale/invalid state and a relocated fixture home.

## Task 2: Apply only presentation that each destination supports

**Files:** modify `sync-projects.py`, `tests/sync_projects_test.py`, `PROJECT-SYNC.md` and the existing README command entry.

**Interfaces:** consume Task 1's layout; extend the existing transport for sparse project metadata updates. Add guarded Antigravity name/order updates and reuse existing closed-app/version/session gates.

- [x] Write failing tests for a native-shaped OpenCode patch, nested icon-field preservation, native reset/rollback behavior, Antigravity project-name updates, exact custom order and preservation of unrelated fields.
- [x] Qualify native OpenCode metadata merge/reset semantics before a real apply. Update only `name` and `icon.color`; preserve canonical directory, startup commands, icon URL/override and unrelated fields. Capture original presence/value distinctly. If the API cannot restore the original representation, stop before changing that field and report the limitation rather than invent a null/empty-string reset.
- [x] Preserve existing native-project lookup and archive checks. Do not register duplicates merely because a display name has changed. Stop on a manual icon override that would defeat the requested visual color.
- [x] In Antigravity, atomically change only each matched existing project's `name`, retaining its ID, resources, settings and grants. Add missing projects through the already reviewed adapter. Stop on a destination name collision or a changed source/destination snapshot.
- [x] With Antigravity closed, merge only `projectsOrder` and `projectsFolderSortBy` into `app_storage.json`. The former is JSON text containing the ordered destination IDs; the latter is the string `custom`. Preserve field absence in receipts, file permissions and every unrelated setting, including conversation ordering and collapse state.
- [x] Put matched source projects in flattened Codex order. Append destination-only projects in their previous relative order; do not delete, recolor or rename them. Include unlisted destination IDs using the app's existing fallback ordering instead of losing them.
- [x] Keep OpenCode ordering unchanged and explicitly report it as unavailable. No Antigravity project color or collapsible custom sections are claimed.
- [x] Run affected tests to GREEN. Document preview/apply examples with `--sync-presentation` and the destination limitations.

**Acceptance:** repeated presentation sync makes no further changes, grouped labels remain readable without color, Green is applied only to unsectioned source projects, and changes never alter agent context or repository data. Native API reset qualification is a required gate, not an assumed success.

## Task 3: Extend recovery before enabling live writes

**Files:** modify `sync-projects.py`, `tests/sync_projects_test.py` and `PROJECT-SYNC.md`.

**Interfaces:** new presentation runs write `project-sync/v2` receipts with per-field before/after values; rollback continues to accept existing `project-sync/v1` membership receipts.

- [x] Write RED tests for interrupted metadata/name/order updates, absent fields, later user edits, partial recovery and v1 rollback compatibility.
- [x] Record narrow intent and original field state before every external/local mutation. Record confirmed after-state and identity after success. Do not copy an entire database or credential-bearing server record into the receipt.
- [x] Rollback metadata/names/order only when their current owned values match this run's recorded after-state. Merge back original fields and preserve unrelated concurrent changes. Restore original absent values using the qualified native route.
- [x] Preserve changed/recreated Antigravity records and uncertain ownership; report unmatched intents. Do not delete an existing project file just to undo a name change. Preserve newly registered OpenCode records/history as the current rollback already does.
- [x] Retain the final process check before ownership comparison and the documented restriction on concurrent destination writers. Stop on changed app versions or incompatible state schemas.
- [x] Verify GREEN for recovery tests, then run the coherent Python suite and existing Codex setup regression once after the batch. Run `git diff --check`; report actual exits, warnings and log paths.

**Acceptance:** partial application is inspectable/recoverable, v1 receipts still work, and newer user metadata is never silently overwritten in recovery.

## Task 4: Independent review, then native acceptance

- [x] Recheck the exact owned diff and protected-file hashes. Independent reviewer remains read-only and examines the whole presentation change, especially identity mapping, alias privacy, resets, JSON-string encoding and recovery.
- [x] Resolve verified material findings with reproducing RED → GREEN tests. Reuse unchanged review coverage; do not add unrelated refactors or repeat successful checks without changed inputs.
- [x] Produce a concrete preview for all 23 current folders, including current→desired OpenCode colors. Existing manual destination colors will be replaced by the user-requested mapping only after this preview is accepted.
- [x] Obtain approval for the final live metadata/name/order changes and any required app restart. Earlier permission to apply membership and briefly restart apps was for that completed run; it is not a standing grant for this new presentation update.
- [x] Apply through the reviewed command with both desktop apps closed and the existing active-session check satisfied. Reopen apps and verify five OpenCode colors, all grouped prefixes, Antigravity custom order, ungrouped Green, and preservation of custom icons/settings where applicable.
- [x] Confirm a post-restart preview reports zero pending presentation or membership changes. Keep native visual/order acceptance separate from fixture-test results. Persist the successful receipt outside Git.

Proposed commands after implementation and review, from the dotfiles checkout:

```sh
rtk proxy python3 -B ./sync-projects.py --sync-presentation
rtk proxy python3 -B ./sync-projects.py --sync-presentation --apply
```

No commit, push, plugin/skill change, source instruction change or automatic schedule is included.

## Plan review and handoff

The palette is fixed as requested. The recommended fallback is display-name prefixes in both destinations, native colors only in OpenCode, and native custom order only in Antigravity. Real collapsible custom project sections remain unavailable in the inspected versions.

The user approved these label changes and limitations. Inline TDD implementation and independent review are complete. The separately approved live preview has now been applied and verified.

## Implementation checkpoint before independent review

- Source-layout tests were written first and failed for missing layout/CLI support; source mapping then passed all seven initial cases. Metadata, aliases, section order, pinned deduplication, moves and palette are implemented without exporting account/user fields.
- Destination tests were written before native PATCH, JSON-field merge, order and v2 recovery. Further RED→GREEN regressions protect newly-created grouped project rollback, identity captured from the writer FD, repeated-run pending summaries and active-session recovery gates.
- Current sync suite: 37 tests passed. Full repository Python suite: 64 tests passed, zero warnings. Existing Codex setup shell regression passed. Full outputs are retained in local temporary evidence outside Git.
- The native reset qualification is from installed OpenCode source: optional sparse fields preserve other metadata; empty string maps to SQL NULL/response absence. Literal old empty-string values are rejected. Native runtime/visual acceptance is still separate and pending.
- Ruling: native Antigravity fallback for multiple destination-only projects missing from saved order requires conversation activity. Stop instead of reading conversation summaries or inventing order. This costs support for that ambiguous case until the user establishes Custom Order.
- Four implementation/documentation paths were updated. At this checkpoint no live project presentation changes had run; the following review and native acceptance records supersede that status.
- One unrelated Antigravity test file changed outside this task's write scope. It was preserved. Its current 14-test suite passed separately with an unchanged input hash during that run.

## Independent review completion

- The independent reviewer assessed the exact baseline-to-candidate diff for all four owned code/test/guide paths, including identity mapping, ordering, reset semantics and recovery. Native contract evidence and test logs were inspected; no app calls or code edits were made by the reviewer.
- One P2 finding was retained: when activity sorting is active, multiple destination-only Antigravity projects cannot safely be appended using a stale saved custom order.
- The regression failed for both Last Updated and Last User Prompt before the fix. The smallest guard now stops that case before mutations. The zero/one destination-only case remains supported and is tested. Targeted GREEN passed. No other material findings were retained.
- Final repository Python suite: **66 tests passed**, zero warnings, exit 0. Test input hashes were unchanged throughout the run. Existing Codex setup regression passed on unchanged inputs; `git diff --check` passed.
- Read-only real-state preview passed: 23 source folders; OpenCode colors Blue3/Orange7/Yellow3/Gray2/Green8; 15 section-name prefixes in each app; Antigravity order update; zero membership additions. Three automatic OpenCode icons would become colored avatars; no manual overrides are present.
- A reviewable local preview was prepared outside Git and subsequently approved by the user with “Yes—apply and verify”.
- Ruling: ambiguous activity-sorted or unsaved destination-only ordering stops rather than reading conversation metadata. This limits that case until the user establishes Custom Order. Legacy literal empty-string OpenCode metadata similarly stops because native reset cannot restore it exactly.
- Implementation and independent review are complete. The separate native acceptance result is recorded below. No commits, pushes, plugin changes, instruction changes or schedules were created.

## Native acceptance completed

- Explicit final approval: **Yes—apply and verify**. Both desktop apps were quit normally before applying the reviewed command; OpenCode had no active sessions.
- Apply exited **0**. Recovery receipt: `/Users/CoveMB/.local/state/project-sync/20261105-134321-7b4f6662`. Narrow before/after journals and `native-verification.json` are retained there outside Git.
- OpenCode was reopened. Its native screenshot shows Blue3, Orange7, Yellow3, Grey2 and Green8, with all 15 grouped labels and eight unprefixed labels. Antigravity was reopened; its native project list shows all 23 labels in Codex's flattened visible order.
- Post-restart read-only preview exited **0**, with zero pending OpenCode presentation changes, Antigravity names/order changes or membership additions.
- Before reopening, all unrelated project fields and Antigravity UI fields matched their pre-apply hashes; Codex source was unchanged. After reopening, Antigravity non-name project fields and unrelated UI fields still match. OpenCode's 22 inactive rows still match; pipeFlow records native reopening activity at 18:44:38 UTC while its metadata update remains 18:43:23 UTC. The sync does not manipulate activity to impose order.
- Final implementation/test/guide hashes still match the independently reviewed candidate. Native acceptance is separate from the 66-test fixture suite. Changes remain local and uncommitted.
