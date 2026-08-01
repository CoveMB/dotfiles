#!/bin/sh

set -eu

DOTFILES_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
TEST_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/dotfiles-codex-test.XXXXXX")
CODEX_SETUP_HOME="$TEST_ROOT/home"

cleanup() {
  case "$TEST_ROOT" in
    "${TMPDIR:-/tmp}"/dotfiles-codex-test.*|/tmp/dotfiles-codex-test.*)
      rm -rf "$TEST_ROOT"
      ;;
    *)
      printf 'Refusing to remove unexpected test path: %s\n' "$TEST_ROOT" >&2
      ;;
  esac
}

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  exit 1
}

assert_symlink_target() {
  link_path=$1
  expected_target=$2

  [ -L "$link_path" ] || fail "$link_path is not a symbolic link"
  [ "$(readlink "$link_path")" = "$expected_target" ] ||
    fail "$link_path does not point to $expected_target"
}

file_mode() {
  if stat -c '%a' "$1" >/dev/null 2>&1; then
    stat -c '%a' "$1"
  else
    stat -f '%Lp' "$1"
  fi
}

run_setup() {
  CODEX_SETUP_HOME="$CODEX_SETUP_HOME" "$DOTFILES_ROOT/setup-codex.sh"
}

trap cleanup EXIT HUP INT TERM

mkdir -p "$CODEX_SETUP_HOME"

if (cd "$TEST_ROOT" && CODEX_SETUP_HOME="relative-home" "$DOTFILES_ROOT/setup-codex.sh" >/dev/null 2>&1); then
  fail "setup accepted a relative target home"
fi

run_setup

assert_symlink_target \
  "$CODEX_SETUP_HOME/.codex/AGENTS.md" \
  "$DOTFILES_ROOT/codex/AGENTS.md"
assert_symlink_target \
  "$CODEX_SETUP_HOME/.codex/agents" \
  "$DOTFILES_ROOT/codex/agents"
assert_symlink_target \
  "$CODEX_SETUP_HOME/.agents/plugins/marketplace.json" \
  "$DOTFILES_ROOT/codex/marketplace.json"

[ -f "$CODEX_SETUP_HOME/.codex/config.toml" ] || fail "config.toml was not bootstrapped"
[ ! -L "$CODEX_SETUP_HOME/.codex/config.toml" ] || fail "config.toml must remain machine-local"
cmp -s \
  "$DOTFILES_ROOT/codex/config.toml.template" \
  "$CODEX_SETUP_HOME/.codex/config.toml" || fail "config.toml does not match the template"
[ "$(file_mode "$CODEX_SETUP_HOME/.codex/config.toml")" = "600" ] ||
  fail "config.toml permissions are not 600"

printf 'machine-local = true\n' >"$CODEX_SETUP_HOME/.codex/config.toml"
run_setup
grep -q '^machine-local = true$' "$CODEX_SETUP_HOME/.codex/config.toml" ||
  fail "existing config.toml was overwritten"

CONFLICT_HOME="$TEST_ROOT/conflict-home"
mkdir -p "$CONFLICT_HOME/.codex/agents" "$CONFLICT_HOME/.agents/plugins"
printf 'original instructions\n' >"$CONFLICT_HOME/.codex/AGENTS.md"
printf 'legacy RTK instructions\n' >"$CONFLICT_HOME/.codex/RTK.md"
printf 'original agent\n' >"$CONFLICT_HOME/.codex/agents/original.toml"
printf 'original marketplace\n' >"$CONFLICT_HOME/.agents/plugins/marketplace.json"

CODEX_SETUP_HOME="$CONFLICT_HOME" "$DOTFILES_ROOT/setup-codex.sh"

assert_symlink_target \
  "$CONFLICT_HOME/.codex/AGENTS.md" \
  "$DOTFILES_ROOT/codex/AGENTS.md"
assert_symlink_target \
  "$CONFLICT_HOME/.codex/agents" \
  "$DOTFILES_ROOT/codex/agents"
assert_symlink_target \
  "$CONFLICT_HOME/.agents/plugins/marketplace.json" \
  "$DOTFILES_ROOT/codex/marketplace.json"

BACKUP_ROOT=$(find "$CONFLICT_HOME/.codex/backups" -mindepth 1 -maxdepth 1 -type d | head -n 1)
[ -n "$BACKUP_ROOT" ] || fail "conflicting files were not backed up"
grep -q '^original instructions$' "$BACKUP_ROOT/.codex/AGENTS.md" ||
  fail "AGENTS.md backup is missing"
grep -q '^legacy RTK instructions$' "$BACKUP_ROOT/.codex/RTK.md" ||
  fail "legacy RTK.md backup is missing"
[ ! -e "$CONFLICT_HOME/.codex/RTK.md" ] || fail "legacy RTK.md remains active"
grep -q '^original agent$' "$BACKUP_ROOT/.codex/agents/original.toml" ||
  fail "agents backup is missing"
grep -q '^original marketplace$' "$BACKUP_ROOT/.agents/plugins/marketplace.json" ||
  fail "marketplace backup is missing"

BACKUP_COUNT_BEFORE=$(find "$CONFLICT_HOME/.codex/backups" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')
CODEX_SETUP_HOME="$CONFLICT_HOME" "$DOTFILES_ROOT/setup-codex.sh"
BACKUP_COUNT_AFTER=$(find "$CONFLICT_HOME/.codex/backups" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')
[ "$BACKUP_COUNT_BEFORE" = "$BACKUP_COUNT_AFTER" ] ||
  fail "idempotent rerun created an unnecessary backup"

grep -q 'setup-codex\.sh' "$DOTFILES_ROOT/install.sh" ||
  fail "Linux installer does not invoke setup-codex.sh"
grep -q 'setup-codex\.sh' "$DOTFILES_ROOT/mac.dotfile.sh" ||
  fail "macOS installer does not invoke setup-codex.sh"
if grep -q 'rtk init -g --codex' "$DOTFILES_ROOT/mac.dotfile.sh"; then
  fail "macOS installer still asks RTK to mutate the managed global AGENTS.md"
fi

printf 'PASS: Codex dotfiles setup is portable, recoverable, and idempotent\n'
