#!/bin/sh
set -eu
DOTFILES_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec python3 "$DOTFILES_ROOT/opencode/setup.py" "$@"
