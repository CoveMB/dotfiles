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
import tomllib
import uuid


ROOT = Path(__file__).resolve().parents[1]
ROLES = ("bounded_explorer", "mechanical_mapper", "quality_reviewer", "implementation_worker")


def absolute(value):
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise ValueError(f"Expected an absolute path: {value}")
    return path


def fingerprint(path):
    metadata = path.lstat()
    result = {"device": metadata.st_dev, "inode": metadata.st_ino,
              "mode": stat.S_IMODE(metadata.st_mode)}
    if path.is_symlink():
        result.update(type="symlink", target=os.readlink(path))
    elif path.is_file():
        result.update(type="file", sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    else:
        raise ValueError(f"Expected file or link: {path}")
    return result


def no_link_parents(path):
    for parent in (path, *path.parents):
        if parent.is_symlink():
            raise ValueError(f"Refusing to write through directory symlink: {parent}")
        if parent.exists() and not parent.is_dir():
            raise ValueError(f"Not a directory: {parent}")


def write_new(path, text):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    metadata = os.fstat(descriptor)
    with os.fdopen(descriptor, "w") as output:
        output.write(text)
    # A concurrent app replacement must never become setup-owned through a
    # later pathname lookup. Bind the created inode and intended bytes instead.
    return {"device": metadata.st_dev, "inode": metadata.st_ino,
            "mode": stat.S_IMODE(metadata.st_mode), "type": "file",
            "sha256": hashlib.sha256(text.encode()).hexdigest()}


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
            if candidate.is_dir():
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
    removed, preserved = [], []
    for entry in reversed(manifest["created"]):
        path = absolute(entry["path"])
        if path.parent != config_root or path.name not in ("AGENTS.md", "opencode-compat.md", "opencode.jsonc"):
            raise ValueError(f"Rollback path outside setup ownership: {path}")
        if not os.path.lexists(path):
            continue
        if fingerprint(path) != entry["fingerprint"]:
            preserved.append(str(path))
            continue
        removed.append(str(path))
        if not dry_run:
            path.unlink()
    return {"removed": removed, "preserved": preserved, "dry_run": dry_run}


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
        print(json.dumps(main(), indent=2))
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"OpenCode setup stopped: {error}", file=sys.stderr)
        sys.exit(1)
