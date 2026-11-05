# OpenCode compatibility

Apply the shared global AGENTS.md and applicable project instructions. This file
maps host-dependent operations; it does not grant additional authority.

- Use native `read`, `glob`, `grep`, `edit`, `write`, `patch`, `shell`, `skill`,
  and `subagent` tools when available. Prefix shell commands with `rtk` as the
  shared instructions require. Never pretend a Codex-only API exists here.
- The four native subagent IDs are `bounded_explorer`, `mechanical_mapper`,
  `quality_reviewer`, and `implementation_worker`. Use the matching role and
  preserve separate, fresh-context review assignments. Launch at most two
  children concurrently. This is an orchestration rule; the host enforces depth
  one, not a concurrency limit. Children may not launch children.
- Read-only roles cannot run shell commands or modify files. The coordinator
  supplies needed diffs, test results, and controller outputs with provenance.
  Do not weaken a role's permissions to work around this boundary.
- Codex threads, automations, memory, computer-use APIs, approvals, and trust
  records remain owned by Codex. Do not import them, duplicate schedules, or
  claim Codex sandbox guarantees. OpenCode shell approval is an actual host
  boundary even when the underlying task is authorized.
- Shared sources, canonical targets and linked skill bundles are inputs. Do not
  edit them through aliases or scripts. Do not use a protected source directory
  as a writable OpenCode workspace. Edit policies cover absolute external
  paths; location-relative paths and shell execution are not an OS sandbox.
  Ask before shell execution and edits; never save broad interpreter or RTK
  approvals merely to reduce prompts.
- Load skills by their native directory ID. A reference such as
  `superpowers:systematic-debugging` means the installed native
  `systematic-debugging` skill, if present. Check discovery instead of guessing.
  Resolve bundled references and scripts relative to their declaring skill or
  package, never the active project directory. Keep all evidence/output in the
  assigned task workspace; shared source directories are not output locations.
- Use Context7's native resolve-library-id and query-docs tools. Keep Code Mode
  disabled for that MCP server because `execute` is denied in this pilot. Query
  public documentation without sending private source or credentials.
- Ponytail is explicit-only and defaults to off. A skill naming it does not
  invoke it. If a required workflow gate conflicts with that rule, report the
  unresolved obligation; do not mark the gate passed. Never create persistent
  `.ponytail-active` state or change shared defaults without explicit consent.
  Its help must describe this skills-only integration, not stock claims of
  automatic Full activation or slash commands. `ponytail-gain` describes a
  historical Claude benchmark, not measured OpenCode savings.
- Superpowers role references map to the four native roles above. Preserve
  independent, fresh-context reviewers and their distinct assignments. Native
  subagent launch/return is available; persistent resumption and history APIs
  must be verified before use. Use the existing manual-return path when needed.
  Do not edit Codex configuration to satisfy a Superpowers model instruction.
  Use a concise checklist if a native todo tool is not exposed. Brainstorming's
  browser companion is unavailable in this pilot; use text or a requested
  manual handoff. Diagnosing Superpowers requires a user-selected accessible
  transcript, not an unrequested search through another app's history.
- Material review and simplification are limited by their source to trusted
  workspaces and trusted changes in OpenCode. Do not use them for untrusted PRs
  or claim global registration enforces source identity. Preserve both gates.
- `gh-address-comments` uses existing authentication and bounded shell approval;
  its Codex escalation wording does not authorize login, scope changes, replies
  or other external writes. Obsidian Bases authoring does not establish native
  rendering. `task-disk-review` keeps OpenCode-managed resources report-only.
- Caveman Lite and Full use normal Caveman, as specified in shared AGENTS.md.
  Cavecrew task names map to the existing native roles there; do not import
  Haiku, automatic Ultra voice, or another delegation/model policy. Native
  usage reports may describe observed usage, never invented token savings.
- Caveman compression is a separate, currently unqualified backend workflow;
  normal Caveman activation does not authorize it. Before execution, obtain
  approval for the exact file, provider/model, data transmission and output
  location. Do not install dependencies, authenticate, or fall back to another
  provider automatically. Work on an authorized task-local copy; shared inputs
  and resolved symlink targets must not be overwritten without separate scope.
  Its optional OpenCode subprocess does not establish this pilot's permission
  isolation or inherit the configured Copilot provider/model/reasoning.
- Recursive Mode bootstrap and Codex-only installers remain in Codex until a
  host-specific bootstrap is reviewed. Do not run installers that rewrite
  `.codex/AGENTS.md`, root AGENTS.md, or other shared host instructions.
- Documents, spreadsheets, presentations, image generation, browser/computer
  control, and hosted account services remain in Codex for this phase. A skill
  describing one of those tools does not make it available in OpenCode.
- Global instructions are shared once through AGENTS.md. OpenCode's project
  discovery differs from Codex: inspect nested instructions explicitly when
  precedence matters; AGENTS.override.md and Codex fallback names are not
  automatically equivalent. Preserve the stricter applicable scope while
  surfacing a real contradiction to the user.
- Use the configured provider/model and xhigh reasoning. Do not silently switch
  provider/model when authentication or model availability fails. Keep replies
  concise and pragmatic, with normal prose when evidence or nuance matters.

See README.md in this file's canonical source directory for setup ownership,
updates, rollback, and the capability disposition.
