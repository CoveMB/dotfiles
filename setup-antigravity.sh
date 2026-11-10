#!/bin/sh
set -eu
DOTFILES_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec python3 -B "$DOTFILES_ROOT/antigravity/setup.py" "$@"
