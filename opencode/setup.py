"""Seed OpenCode additions without overwriting existing configuration.

Python 3.11+; no network, package installation, authentication, or Codex writes.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import tomllib
import uuid


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from setup_files import fingerprint, no_link_parents, write_new
ROLES = ("bounded_explorer", "mechanical_mapper", "quality_reviewer", "implementation_worker")


def absolute(value):
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise ValueError(f"Expected an absolute path: {value}")
    return path


def render_config(home, config_root, sources):
    config = json.loads((ROOT / "opencode/opencode.json.template").read_text())
    model = sources["model"]
    if not isinstance(model, str) or model.count("/") != 1 or "#" in model:
        raise ValueError("model must be a verified provider/model without a variant suffix")
    provider, model_id = model.split("/")
    config["model"] = model
    config["providers"] = {provider: {"models": {model_id: {"settings": {"reasoningEffort": "xhigh"}}}}}
    config["instructions"] = [str(config_root / "opencode-compat.md")]
    config["skills"] = []
    seen = set()
    for value in sources.get("skills", []):
        path = absolute(value).resolve(strict=True)
        if not (path / "SKILL.md").is_file():
            raise ValueError(f"Missing skill entrypoint: {path}")
        if path.name in seen:
            raise ValueError(f"Duplicate native skill ID: {path.name}")
        seen.add(path.name)
        config["skills"].append(str(path))
    context7 = sources.get("context7")
    if context7:
        if context7.get("codemode") is not False:
            raise ValueError("Context7 must set codemode:false while execute is denied")
        config["mcp"] = {"servers": {"context7": context7}}
    config["agents"] = {}
    for role in ROLES:
        source = tomllib.loads((ROOT / "codex/agents" / f"{role}.toml").read_text())
        readonly = role != "implementation_worker"
        rules = [{"action": "*", "resource": "*", "effect": "deny"}]
        for action in ("read", "glob", "grep", "skill", "webfetch", "websearch", "context7_*"):
            rules.append({"action": action, "resource": "*", "effect": "allow"})
        rules.append({"action": "external_directory", "resource": "*", "effect": "ask"})
        for pattern in ("*.env", "*.env.*"):
            rules.append({"action": "read", "resource": pattern, "effect": "ask"})
        rules.append({"action": "read", "resource": "*.env.example", "effect": "allow"})
        if not readonly:
            rules.extend({"action": action, "resource": "*", "effect": "ask"} for action in ("edit", "shell"))
        config["agents"][role] = {"mode": "subagent", "description": source["description"],
            "model": model, "system": source["developer_instructions"], "permissions": rules}
        config["permissions"].append({"action": "subagent", "resource": role, "effect": "allow"})
    protected = [ROOT / "codex", home / ".codex", home / ".agents", ROOT / "opencode"]
    protected.extend(absolute(value) for value in sources.get("protected_paths", []))
    protected.extend(Path(value) for value in config["skills"])
    patterns = set()
    for path in protected:
        for candidate in (path, path.resolve()):
            patterns.add(str(candidate))
            patterns.add(str(candidate) + "/*")
    config["policies"].extend({"action": "tool.use", "resource": "edit:" + pattern, "effect": "deny"}
                              for pattern in sorted(patterns))
    return json.dumps(config, indent=2) + "\n"


def rollback(manifest_path, dry_run):
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("format") != "opencode-setup/v1":
        raise ValueError("Unrecognized rollback manifest")
    config_root = absolute(manifest["config_root"])
    no_link_parents(config_root)
    entries = []
    for entry in reversed(manifest["created"]):
        path = absolute(entry["path"])
        if path.parent != config_root or path.name not in ("AGENTS.md", "opencode-compat.md", "opencode.jsonc"):
            raise ValueError(f"Rollback path outside setup ownership: {path}")
        entries.append((path, entry["fingerprint"]))
    removed, preserved, recovery, errors = [], [], [], []
    recovery_root = None
    for path, expected in entries:
        try:
            if not os.path.lexists(path):
                continue
            if fingerprint(path) != expected:
                preserved.append(str(path))
                continue
            if dry_run:
                removed.append(str(path))
                continue
            if recovery_root is None:
                recovery_root = Path(tempfile.mkdtemp(prefix=".rollback-", dir=config_root))
            backup = recovery_root / path.name
            path.rename(backup)
        except (OSError, ValueError) as error:
            preserved.append(str(path))
            errors.append({"path": str(path), "error": str(error)})
            continue
        # The pathname may have changed after inspection. Move first, inspect
        # the actual entry, and retain it even if an open app descriptor writes
        # later. Recovery lives on the same filesystem and is never deleted.
        item = {"path": str(path), "backup": str(backup), "restored": False}
        recovery.append(item)
        try:
            owned = fingerprint(backup) == expected
        except (OSError, ValueError) as error:
            owned = False
            item["inspection_error"] = str(error)
        if owned:
            removed.append(str(path))
            continue
        preserved.append(str(path))
        try:
            # Exclusive creation preserves any newer destination. Keep the
            # recovery entry too; unsupported hard links require manual recovery.
            os.link(backup, path, follow_symlinks=False)
            item["restored"] = True
        except (OSError, NotImplementedError) as error:
            item["restore_error"] = str(error)
    return {"removed": removed, "preserved": preserved, "recovery": recovery,
            "errors": errors, "dry_run": dry_run}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", default=str(Path.home()))
    parser.add_argument("--config-dir")
    parser.add_argument("--state-dir")
    parser.add_argument("--sources", help="Local JSON containing reviewed skill paths, model, and Context7 registration")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--rollback", type=Path)
    args = parser.parse_args()
    if args.rollback:
        return rollback(args.rollback, args.dry_run)
    home = absolute(args.home).resolve(strict=True)
    config_root = absolute(args.config_dir or str(absolute(os.environ.get("XDG_CONFIG_HOME", str(home / ".config"))) / "opencode"))
    state_root = absolute(args.state_dir or str(absolute(os.environ.get("XDG_STATE_HOME", str(home / ".local/state"))) / "opencode-setup"))
    if os.environ.get("OPENCODE_CONFIG") or os.environ.get("OPENCODE_CONFIG_DIR"):
        raise ValueError("Review OPENCODE_CONFIG/OPENCODE_CONFIG_DIR precedence before installing global configuration")
    no_link_parents(config_root)
    no_link_parents(state_root)
    if not args.sources:
        raise ValueError("Supply --sources with reviewed local inputs; see opencode/README.md")
    sources = json.loads(absolute(args.sources).read_text())
    rendered = render_config(home, config_root, sources)
    targets = {"AGENTS.md": ROOT / "codex/AGENTS.md", "opencode-compat.md": ROOT / "opencode/opencode-compat.md"}
    planned = []
    for name, target in targets.items():
        if not target.is_file():
            raise ValueError(f"Missing source: {target}")
        path = config_root / name
        if os.path.lexists(path):
            if not path.is_symlink() or os.readlink(path) != str(target):
                raise ValueError(f"Destination conflict; preserve and resolve manually: {path}")
        else:
            planned.append((path, target))
    config = config_root / "opencode.jsonc"
    alternate = config_root / "opencode.json"
    for path in (config, alternate):
        if os.path.lexists(path) and (path.is_symlink() or not path.is_file()):
            raise ValueError(f"Unrecognized existing configuration: {path}")
    if not config.exists() and not alternate.exists():
        planned.append((config, None))
    result = {"created": [], "planned": [str(path) for path, _ in planned], "dry_run": args.dry_run}
    if args.dry_run or not planned:
        return result
    config_root.mkdir(parents=True, exist_ok=True)
    state_root.mkdir(parents=True, exist_ok=True)
    manifest_path = state_root / ("setup-" + uuid.uuid4().hex + ".json")
    manifest = {"format": "opencode-setup/v1", "source_root": str(ROOT), "config_root": str(config_root), "created": []}
    # Keep a recovery record before creating destinations; update after each successful creation.
    write_new(manifest_path, json.dumps(manifest, indent=2) + "\n")
    for path, target in planned:
        if target is None:
            created_fingerprint = write_new(path, rendered)
        else:
            path.symlink_to(target)
            created_fingerprint = fingerprint(path)
            if created_fingerprint.get("target") != str(target):
                raise ValueError(f"Link changed during creation; preserve and inspect: {path}")
        manifest["created"].append({"path": str(path), "fingerprint": created_fingerprint})
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    result.update(created=[item["path"] for item in manifest["created"]], manifest=str(manifest_path))
    return result


if __name__ == "__main__":
    try:
        result = main()
        print(json.dumps(result, indent=2))
        if result.get("errors") or any("restore_error" in item for item in result.get("recovery", [])):
            sys.exit(1)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"OpenCode setup stopped: {error}", file=sys.stderr)
        sys.exit(1)
