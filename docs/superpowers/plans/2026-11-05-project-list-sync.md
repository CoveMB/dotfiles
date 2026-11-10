# Project List Sync Implementation Plan

> **For agentic workers:** Use executing-plans for implementation and one independent read-only review before any real preview or apply. Follow the checked steps below.

**Goal:** Persist a discoverable on-demand command in dotfiles that reads Codex local projects and updates OpenCode and Antigravity safely.

**Architecture:** Retain the existing Python standard-library command and guarded destination adapters. Codex remains read-only; preview is the default, OpenCode visible-list replacement is explicit, and Antigravity is additive. Keep runtime state and narrow recovery receipts outside the repository.

**Tech Stack:** Python 3.11+, SQLite, urllib, macOS process checks and filesystem operations; unittest against disposable databases/files.

**Spec:** `PROJECT-SYNC.md` and the user's approved Codex-to-two-destinations scope in this chat.

## Global constraints

- Preserve existing staged, unstaged, untracked and committed work. Current branch is main; no commit, push, stash, reset or cleanup is included. The user subsequently explicitly approved a normal OpenCode quit/apply/reopen for verification.
- Keep `sync-projects.py`, `PROJECT-SYNC.md`, and `tests/sync_projects_test.py` as the durable command, usage guide and tests. Add a link from README.md and this plan under docs/superpowers/plans/.
- OpenCode2.2.5 and Antigravity2.29.0 adapters require review after version changes; do not bypass their guards.
- Do not alter source folders, conversations, permission grants, credentials or unrelated settings. Apply requires both desktop apps closed and no active OpenCode sessions.
- The existing draft and 16 tests predate this request. Preserve them as the baseline; do not describe their creation as test-first. Every new behavior fix must have a reproducing RED run before implementation and a GREEN run after it.
- Do not run the command against real app state until independent review is resolved. Permission to interrupt a running app remains outstanding.

## Review focus

- Partial execution/recovery: interruption must not turn a later user file into owned cleanup.
- Native HTTP contracts: response identity/canonical-path checks must preserve all intended folders.
- Process/version checks: unavailable inspection must stop application writes.
- Privacy: loopback credentials must not traverse proxies, redirects, logs or receipts.
- Persistence: command/tests/guide must work from the dotfiles checkout without temporary-source dependencies.

## Task 1: Finish and verify the durable command

**Files:** `sync-projects.py`, `tests/sync_projects_test.py`, `PROJECT-SYNC.md`, `README.md`, this plan.

**Interfaces:** Keep the current preview, `--apply`, `--replace-opencode`, `--rollback`, and explicit fixture `--home` interface; change only what a verified material defect requires.

- [x] Verify branch/status and record hashes for existing owned files and unrelated dirty paths.
- [x] Inspect the existing command, tests, repository patterns and native-contract evidence.
- [x] Complete the independent material review of the exact candidate before live use.
- [x] For each accepted finding, add a behavioral regression to `tests/sync_projects_test.py`, run that test, and retain the actual failure/exit status outside Git. Expected: failure caused by the verified defect.
- [x] Implement the smallest fix in `sync-projects.py`; run the affected test. Expected: success with the original failing behavior now protected.
- [x] Add README discovery and update the existing guide for any behavior change. No text-matching tests for prose.
- [x] Run the final coherent sync suite and existing setup checks once, capturing real exits and warnings. Resolve/report failures; preserve unrelated implementation work.
- [x] Confirm only allowed paths changed and all unrelated dirty-file hashes match the initial baseline.
- [x] Have the independent reviewer confirm affected fixes against RED/GREEN evidence and final files. Do not repeat unchanged generic coverage.

## Task 2: Try only the reviewed candidate

- [x] After review passes, run the installed command's read-only preview; inspect intended additions/replacement and confirm Codex remains the source.
- [x] Check app/version/session prerequisites. If both apps are already closed, apply only the previously approved project-list scope after preserving narrow recovery records. If an app is running, report the concrete remaining shutdown action and wait for permission or the user's manual closure.
- [x] After an authorized apply, check actual destination readback/native loading and preservation of existing records. Report any limit separately from unit tests.

## Execution evidence

- Independent review verified two P2 defects: archived-source selection and rollback replacement during the final process check.
- `test_archived_source_project_stops_before_registration`: RED, exit 1, `ValueError not raised`; only fixture state was changed by the failing implementation.
- `test_rollback_preserves_file_replaced_during_final_process_check`: RED, exit 1, `Rollback removed a later replacement`; fixture-only.
- Minimal fixes: reject archived source paths during preflight; perform the last process check before comparing rollback ownership.
- Targeted GREEN: `rtk proxy python3 -B -m unittest discover -s tests -p sync_projects_test.py -k archived_source -k final_process_check -v` — 2 tests passed, exit 0.
- Ruling: preserve the earlier draft and original 16 tests; the new corrections are test-first. Rewriting or deleting existing user-owned implementation merely to claim retroactive TDD would add risk without improving behavior.
- README now links the durable command guide. No runtime state, credential or local receipt is stored in Git.
- Full suite: 31 Python tests passed, exit 0, zero warnings; `bash tests/setup_codex_test.sh` passed, exit 0.
- Independent affected-fix review: both findings resolved; no material improvements recommended. No test reruns by the reviewer.
- Reviewed native preview: exit 0; 23 source folders; 18 OpenCode registrations and 18 Antigravity additions; only Default Project hidden; five Antigravity records preserved. No live list writes.
- Current prerequisite check: OpenCode2.2.5 is running; Antigravity2.29.0 is closed. Live apply and native loading are pending permission to briefly quit OpenCode or the user's manual closure. Neither app was interrupted.
- Preservation: the four unrelated dirty files match their initial hashes. All changes remain local and uncommitted.

## Authorized first-run completion

- User explicitly approved quitting OpenCode, applying the backed-up change and opening both apps for verification.
- Source/preview still matched the reviewed 23-folder scope and there were zero active OpenCode sessions. OpenCode quit normally; Antigravity was already closed.
- `rtk proxy python3 -B ./sync-projects.py --replace-opencode --apply` exited 0: 23 OpenCode projects selected, 18 Antigravity projects added. Narrow recovery records were saved outside Git.
- Both apps reopened successfully. Their native accessibility trees displayed all 23 source project names; Antigravity's screenshot was also inspected. No agent prompt was submitted.
- Post-startup preview exited 0 with zero OpenCode registrations, zero Antigravity additions and zero hidden projects remaining. Both destination folder sets exactly match Codex.
- All five existing Antigravity project files remained byte-for-byte unchanged. Codex's logical project set and all four unrelated dirty-file hashes were preserved.
- Implementation and tests were unchanged during live verification, so the already-passing 31-test suite and Codex regression were not rerun. No further action is pending. The command remains on demand and uncommitted.
