"""Generate isolated Antigravity additions; preserve app-owned settings and other hosts."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import tomllib
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from setup_files import fingerprint, no_link_parents, write_new

ROLES = ("bounded_explorer", "mechanical_mapper", "quality_reviewer", "implementation_worker")
READ_TOOLS = {"read_file"}
WRITE_TOOLS = {"edit_file", "write_file", "run_command"}


def absolute(value):
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise ValueError(f"Expected absolute path: {value}")
    return path


def protected_paths(home):
    actual = Path.home()
    return [ROOT / "codex", ROOT / "opencode", home / ".codex", home / ".agents",
            home / ".config/opencode", actual / ".codex", actual / ".agents",
            actual / ".config/opencode"]


def check_destination(path, protected):
    no_link_parents(path)
    # macOS normally resolves .CODEX and .codex to the same directory while
    # Path.resolve preserves their spelling. Conservatively reserve case variants
    # on every host, including not-yet-created protected descendants.
    resolved = Path(str(path.resolve()).casefold())
    for source in protected:
        source = Path(str(source.resolve()).casefold())
        if resolved == source or source in resolved.parents or resolved in source.parents:
            raise ValueError(f"Destination overlaps protected source: {path}")


def skill_name(path):
    text = (path / "SKILL.md").read_text()
    if not text.startswith("---\n") or "\n---" not in text[4:]:
        raise ValueError(f"Missing skill metadata: {path}")
    metadata = text[4:].split("\n---", 1)[0]
    match = re.search(r"(?m)^name:\s*([^\n]+)", metadata)
    name = match[1].strip().strip("\"'") if match else path.name
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        raise ValueError(f"Invalid skill identity: {name}")
    return name


def verify_inputs(inputs):
    for value, expected in inputs.items():
        path = absolute(value)
        if not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError(f"Invalid reviewed resource hash: {path}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Reviewed resource changed: {path}")


def render(sources):
    origin = ROOT / "codex/AGENTS.md"
    content = origin.read_bytes()
    starts = [m.start() for m in re.finditer(rb"(?m)^## ([0-9]+)\. ", content)]
    if not starts:
        raise ValueError("Canonical instructions need numbered section boundaries")
    cuts = [0, *starts[1:], len(content)]
    files, inputs = {}, {str(origin): hashlib.sha256(content).hexdigest()}
    ranges = []
    for index, (start, end) in enumerate(zip(cuts, cuts[1:]), 1):
        name = f"rules/shared-instructions-{index:02d}.md"
        prefix = ("---\ntrigger: always_on\ndescription: Shared instructions section " + str(index) +
                  ".\n---\n\nGenerated from " + str(origin) + ". Resolve source-relative references "
                  "and canonical-target wording from " + str(origin.parent) +
                  ". Do not edit or synchronize back.\n<!-- canonical-body -->\n").encode()
        output = prefix + content[start:end]
        if len(output) >= 24000:
            raise ValueError(f"Rule exceeds native byte limit: {name}")
        files[name] = output.decode()
        ranges.append({"file": name, "start": start, "end": end})
    adapter = ROOT / "antigravity/antigravity-compat.md"
    adapter_bytes = adapter.read_bytes()
    files["rules/antigravity-compat.md"] = adapter_bytes.decode()
    inputs[str(adapter)] = hashlib.sha256(adapter_bytes).hexdigest()
    resources = {str(absolute(path).resolve(strict=True)): digest
                 for path, digest in sources.get("resources", {}).items()}
    verify_inputs(resources)
    inputs.update(resources)
    skills, seen = [], set()
    for value in sources.get("skills", []):
        path = absolute(value).resolve(strict=True)
        name = skill_name(path)
        if str((path / "SKILL.md").resolve()) not in resources:
            raise ValueError(f"Skill requires a reviewed resource inventory: {path}")
        if name in seen:
            raise ValueError(f"Duplicate skill identity: {name}")
        seen.add(name)
        skills.append({"path": str(path)})
    files["skills.json"] = json.dumps({"entries": skills}, indent=2) + "\n"
    tools = sources["role_tools"]
    read = tools["read"]
    write = tools["write"]
    if not set(read) <= READ_TOOLS or not set(write) <= WRITE_TOOLS:
        raise ValueError("Unknown or unsafe role tool identifier")
    roles = sources.get("roles", list(ROLES))
    if not isinstance(roles, list) or len(set(roles)) != len(roles) or not set(roles) <= set(ROLES):
        raise ValueError("Unknown or duplicate role identity")
    for role in roles:
        path = ROOT / "codex/agents" / (role + ".toml")
        role_bytes = path.read_bytes()
        source = tomllib.loads(role_bytes.decode())
        if source["name"] != role:
            raise ValueError(f"Unexpected canonical role: {path}")
        inputs[str(path)] = hashlib.sha256(role_bytes).hexdigest()
        allowed = read + (write if role == "implementation_worker" else [])
        files["agents/" + role + ".md"] = ("---\nname: " + role + "\ndescription: " +
            json.dumps(source["description"]) + "\nmainAgent: false\nsubagent: true\nmodel: inherit\n"
            "commandExecutionPolicy: sandbox\ninheritMcp: false\ninheritCustomizations: true\ntools:\n" +
            "".join("  - " + name + "\n" for name in allowed) + "---\n\n" + source["developer_instructions"])
    return files, inputs, ranges


def owned_names(names):
    allowed = {"skills.json", "rules/antigravity-compat.md", *("agents/" + r + ".md" for r in ROLES)}
    for name in names:
        if name not in allowed and not re.fullmatch(r"rules/shared-instructions-[0-9]{2}\.md", name):
            raise ValueError(f"Path outside setup ownership: {name}")


def rollback(manifest_path, home, dry_run):
    record = json.loads(manifest_path.read_text())
    if record.get("format") != "antigravity-setup/v1":
        raise ValueError("Unrecognized recovery manifest")
    config = absolute(record["config_root"])
    check_destination(config, protected_paths(home))
    entries = record["created"]
    names = []
    for entry in entries:
        path = absolute(entry["path"])
        names.append(str(path.relative_to(config)))
        no_link_parents(path.parent)
    owned_names(names)
    removed, preserved, recovery = [], [], []
    for entry in reversed(entries):
        path = Path(entry["path"])
        if not os.path.lexists(path):
            continue
        if fingerprint(path) != entry["fingerprint"]:
            preserved.append(str(path))
            continue
        if dry_run:
            removed.append(str(path))
            continue
        # Move first and retain the inode so concurrent replacements and writes
        # through open descriptors stay recoverable. Never unlink app data.
        backup = Path(tempfile.mkdtemp(prefix=".rollback-", dir=path.parent)) / path.name
        path.rename(backup)
        recovery.append({"path": str(path), "backup": str(backup)})
        if fingerprint(backup) != entry["fingerprint"]:
            preserved.append(str(path))
            try:
                os.link(backup, path, follow_symlinks=False)
            except FileExistsError:
                pass
        else:
            removed.append(str(path))
    return {"removed": removed, "preserved": preserved, "recovery": recovery, "dry_run": dry_run}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", default=str(Path.home()))
    parser.add_argument("--config-dir")
    parser.add_argument("--state-dir")
    parser.add_argument("--sources")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--rollback", type=Path)
    args = parser.parse_args()
    home = absolute(args.home).resolve(strict=True)
    if args.rollback:
        return rollback(args.rollback, home, args.dry_run)
    config = absolute(args.config_dir or str(home / ".gemini/config"))
    state = absolute(args.state_dir or str(home / ".local/state/antigravity-setup"))
    protected = protected_paths(home)
    check_destination(config, protected)
    check_destination(state, protected)
    sources = json.loads(absolute(args.sources).read_text())
    files, inputs, ranges = render(sources)
    protected.extend(absolute(value) for value in sources.get("skills", []))
    check_destination(config, protected)
    check_destination(state, protected)
    owned_names(files)
    planned = []
    for name, text in files.items():
        path = config / name
        no_link_parents(path.parent)
        if os.path.lexists(path):
            if path.is_symlink() or not path.is_file() or path.read_bytes() != text.encode() or path.stat().st_nlink != 1:
                raise ValueError(f"Destination conflict; preserve and review: {path}")
        else:
            planned.append(name)
    result = {"created": [], "planned": [str(config / n) for n in planned], "dry_run": args.dry_run,
              "inputs": inputs, "instruction_ranges": ranges}
    if args.dry_run or not planned:
        return result
    verify_inputs(inputs)
    state.mkdir(mode=0o700, parents=True, exist_ok=True)
    run = state / ("setup-" + uuid.uuid4().hex)
    run.mkdir(mode=0o700)
    record = {"format": "antigravity-setup/v1", "config_root": str(config), "status": "prepared",
              "created": [], "inputs": inputs, "instruction_ranges": ranges}
    # Stage complete files and journal their actual inodes BEFORE publication.
    # An interrupted write never reaches discovery; a publication failure already
    # has durable ownership evidence, including all potentially published paths.
    for index, name in enumerate(planned):
        stage = run / str(index)
        evidence = write_new(stage, files[name])
        record["created"].append({"path": str(config / name), "stage": str(stage), "fingerprint": evidence})
    manifest = run / "manifest.json"
    write_new(manifest, json.dumps(record, indent=2) + "\n")
    verify_inputs(inputs)
    for entry in record["created"]:
        path = Path(entry["path"])
        no_link_parents(path.parent)
        path.parent.mkdir(parents=True, exist_ok=True)
        os.link(entry["stage"], path)
        Path(entry["stage"]).unlink()
        result["created"].append(str(path))
    record["status"] = "installed"
    update = run / "manifest.next"
    write_new(update, json.dumps(record, indent=2) + "\n")
    update.replace(manifest)
    result["manifest"] = str(manifest)
    return result


if __name__ == "__main__":
    try:
        print(json.dumps(main(), indent=2))
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Antigravity setup stopped: {error}", file=sys.stderr)
        sys.exit(1)
