#!/bin/sh

set -eu

DOTFILES_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
CODEX_SETUP_HOME=${CODEX_SETUP_HOME:-$HOME}
CODEX_DIRECTORY="$CODEX_SETUP_HOME/.codex"
PERSONAL_AGENTS_DIRECTORY="$CODEX_SETUP_HOME/.agents"
BACKUP_ROOT=""

case "$CODEX_SETUP_HOME" in
  /*)
    ;;
  *)
    printf 'Codex setup home must be an absolute path: %s\n' "$CODEX_SETUP_HOME" >&2
    exit 1
    ;;
esac

if [ "$CODEX_SETUP_HOME" = "/" ]; then
  printf 'Refusing to use the filesystem root as the Codex setup home.\n' >&2
  exit 1
fi

ensure_backup_root() {
  if [ -z "$BACKUP_ROOT" ]; then
    BACKUP_ROOT="$CODEX_DIRECTORY/backups/dotfiles-migration-$(date '+%Y%m%d%H%M%S')-$$"
    mkdir -p "$BACKUP_ROOT"
  fi
}

backup_existing_path() {
  target_path=$1
  relative_path=${target_path#"$CODEX_SETUP_HOME"/}

  ensure_backup_root
  mkdir -p "$BACKUP_ROOT/$(dirname -- "$relative_path")"
  mv "$target_path" "$BACKUP_ROOT/$relative_path"
  printf 'Backed up %s to %s\n' "$target_path" "$BACKUP_ROOT/$relative_path"
}

link_managed_path() {
  source_path=$1
  target_path=$2

  [ -e "$source_path" ] || {
    printf 'Missing managed Codex source: %s\n' "$source_path" >&2
    exit 1
  }

  if [ -L "$target_path" ] && [ "$(readlink "$target_path")" = "$source_path" ]; then
    return
  fi

  if [ -e "$target_path" ] || [ -L "$target_path" ]; then
    backup_existing_path "$target_path"
  fi

  mkdir -p "$(dirname -- "$target_path")"
  ln -s "$source_path" "$target_path"
  printf 'Linked %s to %s\n' "$target_path" "$source_path"
}

mkdir -p "$CODEX_DIRECTORY" "$PERSONAL_AGENTS_DIRECTORY/plugins"

if [ -e "$CODEX_DIRECTORY/RTK.md" ] || [ -L "$CODEX_DIRECTORY/RTK.md" ]; then
  backup_existing_path "$CODEX_DIRECTORY/RTK.md"
fi

link_managed_path \
  "$DOTFILES_ROOT/codex/AGENTS.md" \
  "$CODEX_DIRECTORY/AGENTS.md"
link_managed_path \
  "$DOTFILES_ROOT/codex/agents" \
  "$CODEX_DIRECTORY/agents"
link_managed_path \
  "$DOTFILES_ROOT/codex/marketplace.json" \
  "$PERSONAL_AGENTS_DIRECTORY/plugins/marketplace.json"

if [ ! -e "$CODEX_DIRECTORY/config.toml" ] && [ ! -L "$CODEX_DIRECTORY/config.toml" ]; then
  cp "$DOTFILES_ROOT/codex/config.toml.template" "$CODEX_DIRECTORY/config.toml"
  chmod 600 "$CODEX_DIRECTORY/config.toml"
  printf 'Created machine-local Codex configuration at %s\n' "$CODEX_DIRECTORY/config.toml"
else
  printf 'Preserved existing machine-local Codex configuration at %s\n' "$CODEX_DIRECTORY/config.toml"
fi

printf 'Codex dotfiles setup complete. Restart Codex to reload configuration.\n'
