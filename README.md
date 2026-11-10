## Toolset

- [oh-my-zsh](http://ohmyz.sh/)
- [git](https://git-scm.com/)

## Project list sync

Use [the project sync command](PROJECT-SYNC.md) to copy local Codex project
folders to OpenCode and Antigravity. Preview from this checkout:

```sh
rtk proxy python3 -B ./sync-projects.py
```

The default is read-only. The guide covers applying with both desktop apps
closed, replacing OpenCode's visible list, and guarded rollback.

Add `--sync-presentation` to preview Codex section labels, OpenCode colors and
Antigravity custom order. The [guide](PROJECT-SYNC.md#optional-section-labels-colors-and-ordering)
describes supported features and guarded recovery.
