# Claude Code Parity Implementation Plan

> **For agentic workers:** Coordinator follows the orchestration section. Workers implement only their assigned task, in their assigned worktree, and report changed files, commands, results and open risks. Independent read-only review precedes any live apply or commit.

**Goal:** Give Claude Code the same global instructions, roles, skills, plugins, permissions and defaults as Codex, with portable files owned by this repository and linked into `~/.claude`, mirroring the existing Codex and OpenCode setups.

**Architecture:** `codex/AGENTS.md` stays the single canonical global instruction file; `~/.claude/CLAUDE.md` is a symlink to it. A Claude-specific compatibility rule, generated role files and shared skills are linked from the checkout. `~/.claude/settings.json` stays machine-local (Claude rewrites it, and symlinked settings files have known defects), seeded from a template exactly like `codex/config.toml.template`. MCP registration goes through the `claude mcp` CLI, never by editing `~/.claude.json`.

**Tech Stack:** POSIX sh (setup, matching `setup-codex.sh`), Python 3.11+ standard library (`tomllib` role rendering, matching `opencode/setup.py`), Claude Code CLI, RTK.

**Spec:** Chat of 2026-11-10 and the decisions below.

## Approved decisions

| Topic | Decision |
| --- | --- |
| Global instructions | `~/.claude/CLAUDE.md` -> `~/Code/dotfiles/codex/AGENTS.md` (same file Codex and OpenCode use) |
| Default model | `"model": "opus"`, `"effortLevel": "xhigh"`; roles use `model: opus`, `effort: xhigh` |
| Network | Open network (Codex `network_access = true` parity) |
| Read-only roles | No shell (OpenCode precedent) |
| Project list sync | Claude excluded from `sync-projects.py`; no writes to `~/.claude.json` trust records |
| Commit/PR attribution | Removed: `"attribution": {"commit": "", "pr": ""}` |

## Global constraints

- Preserve existing staged, unstaged, untracked and committed work. `main` currently has uncommitted OpenCode, Antigravity, Ollama and docs work; the user decides how it is committed before the Claude branch starts.
- No commit, push, publication or live `~/.claude` mutation without explicit user approval of that step.
- Repository is public: templates contain no secrets, credentials, trust hashes or absolute personal paths (`$HOME` placeholders, rendered at setup).
- Codex and OpenCode configuration stay byte-identical unless a task explicitly scopes a change (Task A5 only).
- Never run the default `rtk init --global`: it appends `@RTK.md` to `~/.claude/CLAUDE.md`, i.e. the shared `codex/AGENTS.md`.
- Static checks do not prove Claude discovery or behavior; Task C evidence and Task D checks are separate.

## Target layout

| `~/.claude` path | Source in checkout | Mechanism |
| --- | --- | --- |
| `CLAUDE.md` | `codex/AGENTS.md` | symlink |
| `rules/claude-compat.md` | `claude/claude-compat.md` | symlink (file) |
| `agents/` | `claude/agents/` (generated from `codex/agents/*.toml`) | symlink (dir) |
| `skills/<name>` | `skills/<name>` | per-skill symlinks (never the whole dir: claude.ai sync writes there) |
| `hooks/` scripts | `claude/hooks/` | symlinks |
| `settings.json` | `claude/settings.json.template` | copy when absent; otherwise print a diff for manual merge |
| user MCP (`~/.claude.json`) | — | `claude mcp add --scope user context7 -- npx -y @upstash/context7-mcp` when `claude mcp get context7` fails |

## Settings mapping (template content)

| Codex | Claude |
| --- | --- |
| `model`, `model_reasoning_effort = xhigh` | `"model": "opus"`, `"effortLevel": "xhigh"` |
| `approval_policy = on-request`, `approvals_reviewer = auto_review` | `permissions.defaultMode`: `"auto"` if present in installed version, else `"default"` (Task C) |
| `sandbox_mode = workspace-write` + `network_access = true` | `"sandbox": {"enabled": true, "autoAllowBashIfSandboxed": true, "network": {"allowedDomains": ["*"]}}` — wildcard-all unverified; fallback chosen in Task C |
| `rules/rtk-workflow.rules` (21 rules) | `permissions.allow` `Bash(rtk … *)` equivalents; force-push/branch-delete allowance kept as the user approved it in Codex |
| `web_search = live` | allow `WebSearch`, `WebFetch` |
| context7 MCP | CLI registration above; allow `mcp__context7__*` |
| `.env` ask rules (OpenCode) | `permissions.ask`: `Read(**/.env)`, `Read(**/.env.*)`; allow `Read(**/.env.example)` |
| `memories = true` | `"autoMemoryEnabled": true` (no import of Codex memories) |
| `shell_environment_policy.set.VOLTA_FEATURE_PNPM` | `"env": {"VOLTA_FEATURE_PNPM": "1"}` |
| `notify` turn-ended | `Stop` hook (optional, macOS notification) |
| `git-commit-instructions` | line in `claude-compat.md` |
| shared-file protection | `permissions.deny`: `Edit(~/.claude/CLAUDE.md)`, `Write(~/.claude/CLAUDE.md)` (Write/Edit replace symlinks with regular files) |
| project AGENTS.md discovery | `pluginConfigs."cc-plugin-agents-md@builtin".options.instructionFiles = "claude-md-and-agents-md"` |
| RTK | `PreToolUse` `Bash` hook pointing to RTK's rewrite script (hook-only install, Task C) |
| `max_depth = 1`, 2 concurrent | native depth 1; concurrency stays an instruction in `claude-compat.md` |

Excluded: credentials, histories, sessions, memories, automations, `rules/default.rules`, hook trust, project trust, desktop UI state.

## Plugins and skills

| Item | Claude treatment |
| --- | --- |
| material-code-review, ponytail, superpowers, caveman | Already Claude plugins. `extraKnownMarketplaces` + `enabledPlugins`. Ponytail keeps `defaultMode: off`, explicit-only; caveman Lite/Full mapping per AGENTS.md |
| humanizer, accessible-reading-writing, research-skills (29), incremental-and-test-plans | Add `.claude-plugin/plugin.json` + `marketplace.json` via each repo's packager; new reviewed export, Codex stays on its current export until separately refreshed |
| cleanup-resources | Claude manifest; explicit-only (`disable-model-invocation`) as in OpenCode |
| recursive-mode | Deferred (bootstrap rewrites shared instructions) |
| consulting | Not exposed while disabled in Codex |
| context7-mcp, obsidian-bases, gh-address-comments | Move to `skills/` in this repo; link into `~/.agents/skills` and `~/.claude/skills` |
| documents/spreadsheets/pdf/presentations, browser, computer-use, visualize, codex-security, CodeRabbit, Zotero, GitHub, Drive | Stay in Codex; Claude equivalents are a later, separate decision |

## Task A — dotfiles branch `claude-parity` (sequential, one implementation_worker)

- [ ] A1 `claude/claude-compat.md`: Agent tool + four role IDs, built-in Explore/Plan start without CLAUDE.md, Skill tool, `mcp__context7__*` names, `/loop`/scheduled tasks for coordination monitors, `claude`-prefixed names treated like `codex`-prefixed ones, no Codex sandbox-equivalence claims, at most two concurrent children, commit-message instruction.
- [ ] A2 `claude/render_agents.py` → `claude/agents/{bounded_explorer,mechanical_mapper,quality_reviewer,implementation_worker}.md` with a generated header. Read-only roles: `tools: Read, Grep, Glob, WebFetch, WebSearch, mcp__context7__resolve-library-id, mcp__context7__query-docs`; `disallowedTools: Bash, Edit, Write, NotebookEdit, Agent`. Worker: `disallowedTools: Agent`. All: `model: opus`, `effort: xhigh`, body = `developer_instructions`. Add `--check` mode; test fails on drift.
- [ ] A3 `claude/settings.json.template` per the mapping, values chosen from Task C evidence.
- [ ] A4 `setup-claude.sh` (`CLAUDE_SETUP_HOME`, absolute-path and `/` guards, `link_managed_path` + timestamped backups under `~/.claude/backups/dotfiles-migration-*`, template copy only when absent, idempotent MCP registration, `--dry-run`) and `tests/setup_claude_test.sh` (fixture home, link targets, rerun no-op, existing-file backup, settings preserved).
- [ ] A5 Skills consolidation (touches Codex layout — needs approval): move the three personal skills into `skills/`, extend `setup-codex.sh` to link `~/.agents/skills/<name>` with backup; extend `tests/setup_codex_test.sh`. Verify Codex and OpenCode still discover them.
- [ ] A6 Call `setup-claude.sh` from `mac.dotfile.sh` after `setup-codex.sh`; `claude/README.md` (managed files, exclusions, rollback); link from README.md.
- [ ] Run `tests/setup_claude_test.sh`, `tests/setup_codex_test.sh`, `render_agents.py --check`, and the existing OpenCode/Antigravity suites once after the batch.

## Task B — plugin repositories (independent; one worktree per repo)

- [ ] B1 humanizer, B2 accessible-reading-writing, B3 research-skills, B4 incremental-and-test-plans, B5 cleanup-resources: add Claude manifests to the packager output, follow `material-code-review` as the in-house pattern, run each repo's validator/packaging tests, produce a new dated reviewed export. Preserve dirty checkouts and unmerged branches.

## Task C — verification spikes (read-only to real state; `CLAUDE_CONFIG_DIR` fixture)

- [ ] Symlinked `CLAUDE.md`, `rules/` file, `agents/` dir and per-skill links are discovered (`/memory`, `/agents`, `/skills`).
- [ ] `allowedDomains: ["*"]` accepted and effective (sandboxed `curl` to an unlisted host). Fallback order: documented all-domains form → `sandbox.network` broad wildcard list → sandbox for filesystem only with network prompts handled by auto mode.
- [ ] `defaultMode: "auto"` available; empty-string `attribution` hides trailer and PR line.
- [ ] RTK hook-only install path (`rtk init --help`); whether permission rules match the pre- or post-rewrite command.
- [ ] Local directory marketplace source format; plugins listed by relative path load in place.
- [ ] Record version, commands and observations outside Git.

## Task D — live apply (human-gated)

- [ ] Prereqs: Claude Code CLI installed and signed in; RTK and Node 24 present.
- [ ] Inspect home for stale links created by the pre-fix install loop (`~/.install.sh`, `~/.setup-*.sh`, `~/.sync-projects.py`, `~/.setup_files.py`, `~/.PROJECT-SYNC.md`, …); removal is a separate user-approved step.
- [ ] `./setup-claude.sh --dry-run`, review, apply; install marketplaces/plugins; restart Claude Code.
- [ ] Checks: `/memory` shows AGENTS.md, `/agents` shows four roles, `/skills`, `/plugin`, `/permissions`, `claude mcp list`, one real Context7 query, RTK audit shows rewrites, a test commit has no co-author trailer, `codex` and OpenCode configs unchanged (hash compare).

## Task E — review and commit

- [ ] quality_reviewer (fresh context) on Task A diff; material-code-review on the same change; separate reviewer per Task B repo. Fix confirmed material findings, rerun affected checks.
- [ ] Commit per repo on user approval; push only when asked.

## Orchestration

**Coordinator:** Codex (has the four roles, saved RTK approvals and orchestration rules) until Claude Code is bootstrapped; after Task D, Claude Code can coordinate follow-ups using the same roles.

| Wave | Parallel tracks (max 2 children) | Gate before next wave |
| --- | --- | --- |
| 0 | — (user: commit/branch existing work, install Claude Code) | Clean branch point; Claude Code signed in |
| 1 | C spikes (bounded_explorer, read-only) ‖ A1+A2 (implementation_worker) | Spike evidence fixes A3 values |
| 2 | A3→A4 (implementation_worker) ‖ B1–B5 one repo at a time (implementation_worker, own worktree) | A tests green; each B validator green |
| 3 | A5 (needs approval) → A6 | Codex/OpenCode discovery unchanged |
| 4 | E reviews: quality_reviewer on A ‖ quality_reviewer on current B repo | Material findings resolved |
| 5 | D live apply (coordinator with user) | All D checks recorded |
| 6 | E commits (user approval) | — |

Write scopes are disjoint between tracks (dotfiles worktree vs. each plugin repo worktree). Within Task A, writes are sequential. Every worker receives: task ID, write scope, non-goals, this plan path, acceptance checks, and the owning coordinator thread as its return route.

## Done outside this plan (2026-11-10)

- `install.sh` / `mac.dotfile.sh`: symlink loop now skips `*.sh`, `*.py`, `*.md` with a portable `case`. The previous quoted `=~` pattern is literal in bash, so every script and Python file was linked into `$HOME`. Removed the broken `ln -s "$PWD/.p10k.zsh" "~/"` line; the loop already links `p10k.zsh` as `~/.p10k.zsh`. Fixture run under sh and bash links only the eight dotfiles.
