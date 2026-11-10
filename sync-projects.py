#!/usr/bin/env python3
"""Copy local Codex project folders to OpenCode and Antigravity, on demand."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import base64
import plistlib
import sys
import tempfile
import fcntl
from contextlib import contextmanager


FORMAT = "project-sync/v1"
PRESENTATION_FORMAT = "project-sync/v2"
SECTION_COLORS = {"egeria": "blue", "plugins": "orange", "external plugins": "yellow",
                  "archive": "gray", "archives": "gray"}
STORE_NAME = "opencode.global.dat"
STORE_KEY = "server"


def read_json(path):
    return json.loads(path.read_text())


def write_new_json(path, value):
    data = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()
    descriptor, temporary = tempfile.mkstemp(prefix=".project-sync-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
            stat = os.fstat(stream.fileno())
        os.link(temporary, path)  # Atomic publication; refuses an existing destination.
    finally:
        os.unlink(temporary)
    return {"device": stat.st_dev, "inode": stat.st_ino,
            "sha256": hashlib.sha256(data).hexdigest()}


def fingerprint(path):
    if path.is_symlink() or not path.is_file():
        return None
    stat = path.stat()
    return {"device": stat.st_dev, "inode": stat.st_ino,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


@contextmanager
def connect(path, writable=False):
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"Missing or linked database: {path}")
    connection = sqlite3.connect(path.as_uri() + ("?mode=rw" if writable else "?mode=ro"),
                                 uri=True, timeout=5)
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def paths(home):
    return {
        "source": home / ".codex/state_5.sqlite",
        "source_state": home / ".codex/.codex-global-state.json",
        "antigravity_state": home / "Library/Application Support/Antigravity/app_storage.json",
        "opencode_database": home / ".local/share/opencode/opencode.db",
        "opencode_ui": home / "Library/Application Support/ai.opencode.desktop/drafts.sqlite",
        "service": home / ".local/state/opencode/service.json",
        "antigravity": home / ".gemini/config/projects",
        "records": home / ".local/state/project-sync",
    }


def source_projects(database):
    with connect(database) as connection:
        rows = connection.execute(
            "SELECT p.id,p.name,r.path FROM projects p "
            "LEFT JOIN project_roots r ON r.project_id=p.id "
            "ORDER BY p.position,r.position").fetchall()
    projects, identifiers, folders = [], set(), set()
    for row in rows:
        if row["id"] in identifiers:
            raise ValueError(f"Multi-folder Codex project requires an explicit mapping: {row['name']}")
        identifiers.add(row["id"])
        if not row["path"] or not Path(row["path"]).is_absolute():
            raise ValueError(f"Project has no absolute local folder: {row['name']}")
        directory = Path(row["path"]).resolve(strict=True)
        if not directory.is_dir():
            raise ValueError(f"Project folder is not a directory: {directory}")
        if str(directory) in folders:
            continue
        folders.add(str(directory))
        projects.append({"id": row["id"], "name": row["name"] or directory.name,
                         "directory": str(directory)})
    if not projects:
        raise ValueError("Codex has no local projects; refusing an empty destination update")
    return projects


def source_layout(locations, projects):
    """Read only the local identities, section membership and visible project order."""
    by_id = {project["id"]: project for project in projects}
    aliases = {}
    with connect(locations["source"]) as connection:
        rows = connection.execute("SELECT id,metadata FROM projects").fetchall()
    for row in rows:
        if row["id"] not in by_id:
            continue
        metadata = json.loads(row["metadata"] or "{}")
        keys = ["codex:project:" + row["id"]]
        local = metadata.get("codex.localProjectId")
        if isinstance(local, str):
            keys.append("codex:project:" + local)
        backing = metadata.get("codex.chatGptBacking")
        if isinstance(backing, str):
            backing = json.loads(backing)
        if isinstance(backing, dict) and isinstance(backing.get("projectId"), str):
            keys.append("chatgpt:project:" + backing["projectId"])
        for key in keys:
            if key in aliases and aliases[key] != row["id"]:
                raise ValueError("Conflicting local project aliases")
            aliases[key] = row["id"]

    atoms = read_json(locations["source_state"])["electron-persisted-atom-state"]
    collections = atoms["sidebar-custom-sections-v3"]
    matches = [data for data in collections.values() if any(
        key in aliases for section in data["sections"] for key in section.get("itemKeys", []))]
    if not matches and len(collections) == 1:
        matches = list(collections.values())
    if len(matches) != 1:
        raise ValueError("Cannot select a unique Codex section collection")
    collection = matches[0]

    def resolve(key):
        if not isinstance(key, str):
            raise ValueError("Invalid Codex project reference")
        if key.startswith("codex:project:") and key not in aliases:
            raise ValueError("Unresolved local project reference; refresh Codex layout")
        return aliases.get(key)

    memberships, sections = {}, {}
    for section in collection["sections"]:
        identifier, name = section["id"], section["name"]
        if identifier in sections or not isinstance(name, str) or not name.strip():
            raise ValueError("Invalid or duplicate Codex section")
        members = list(dict.fromkeys(project_id for key in section.get("itemKeys", [])
                                     if (project_id := resolve(key)) is not None))
        if members and name.casefold().strip() not in SECTION_COLORS:
            raise ValueError(f"Custom section needs a color mapping: {name}")
        sections[identifier] = members
        for project_id in members:
            if project_id in memberships:
                raise ValueError("Project belongs to multiple custom sections")
            memberships[project_id] = (identifier, name)

    global_order = list(dict.fromkeys(project_id for key in atoms["unified-sidebar-project-order-v1"]
                                     if (project_id := resolve(key)) is not None))
    pinned = [project_id for key in atoms.get("unified-sidebar-pinned-order-v1", [])
              if (project_id := resolve(key)) is not None]
    ordered = []
    for token in collection["sectionOrder"]:
        if token == "pinned":
            ordered.extend(pinned)
        elif token == "threads":
            ordered.extend(project_id for project_id in global_order if project_id not in memberships)
        elif token.startswith("custom:"):
            if token[7:] not in sections:
                raise ValueError("Codex section order contains an unknown section")
            ordered.extend(sections[token[7:]])
    ordered = list(dict.fromkeys(ordered))
    if set(ordered) != set(by_id):
        raise ValueError("Codex visible layout does not cover every local project; refresh its sidebar")
    result = []
    for position, project_id in enumerate(ordered):
        project = by_id[project_id]
        section_id, section_name = memberships.get(project_id, (None, None))
        result.append({**project, "section_id": section_id, "section_name": section_name,
                       "display_name": f"[{section_name}] {project['name']}" if section_name else project["name"],
                       "color": SECTION_COLORS[section_name.casefold().strip()] if section_name else "green",
                       "position": position})
    return result


def fields(value, keys):
    return {key: {"present": key in value, "value": value.get(key)} for key in keys}


def metadata_fields(project):
    return {"name": project.get("name"), "color": (project.get("icon") or {}).get("color")}


def presentation_plan(locations, layout):
    with connect(locations["opencode_database"]) as connection:
        records = [dict(row) for row in connection.execute(
            "SELECT id,worktree,name,icon_color,icon_url,icon_url_override FROM project")]
    by_directory = {str(Path(row["worktree"]).resolve()): row for row in records}
    gravity = antigravity_projects(locations["antigravity"])
    state_path = locations["antigravity_state"]
    if fingerprint(state_path) is None:
        raise ValueError("Antigravity UI state must be an initialized regular file")
    state = read_json(state_path)
    saved_order = json.loads(state.get("projectsOrder", "[]"))
    if not isinstance(saved_order, list) or not all(isinstance(item, str) for item in saved_order):
        raise ValueError("Unsupported Antigravity projectsOrder schema")
    source_paths = {row["directory"] for row in layout}
    source_gravity_ids = {Path(entry["path"]).stem for entry in gravity
                          if source_paths.intersection(entry["directories"])}
    destination_only = {Path(entry["path"]).stem for entry in gravity
                        if Path(entry["path"]).stem not in source_gravity_ids}
    if len(destination_only) > 1 and state.get("projectsFolderSortBy", "custom") != "custom":
        raise ValueError("Cannot preserve destination-only order under activity sorting; establish Custom Order first")
    unlisted = [Path(entry["path"]).stem for entry in gravity
                if Path(entry["path"]).stem not in source_gravity_ids
                and Path(entry["path"]).stem not in saved_order]
    if len(unlisted) > 1:
        raise ValueError("Cannot preserve destination-only order without conversation metadata; establish Custom Order first")
    extras = unlisted + [item for item in saved_order if item not in source_gravity_ids]
    opencode, antigravity, names, matched_files = [], [], set(), set()
    for row in layout:
        existing = by_directory.get(row["directory"])
        before = {"name": existing["name"], "color": existing["icon_color"]} if existing else {"name": None, "color": None}
        if "" in before.values():
            raise ValueError("Cannot exactly restore legacy empty-string OpenCode metadata")
        if existing and existing["icon_url_override"]:
            raise ValueError("A manual icon overrides the requested project color; review it first")
        rendered_name = before["name"] or Path(row["directory"]).name
        after = {"name": row["display_name"] if rendered_name != row["display_name"] else before["name"],
                 "color": row["color"]}
        opencode.append({"id": existing["id"] if existing else None, "directory": row["directory"],
                         "before": before, "after": after,
                         "hides_automatic_icon": bool(existing and existing["icon_url"])})
        matches = [entry for entry in gravity if row["directory"] in entry["directories"]]
        if len(matches) > 1 or (matches and matches[0]["path"] in matched_files):
            raise ValueError("Antigravity project resources need an explicit one-project mapping")
        existing_gravity = matches[0] if matches else None
        if existing_gravity:
            matched_files.add(existing_gravity["path"])
        name = row["display_name"]
        if name in names:
            raise ValueError("Destination project display names would collide")
        names.add(name)
        antigravity.append({"directory": row["directory"],
                            "path": existing_gravity["path"] if existing_gravity else None,
                            "before": existing_gravity["name"] if existing_gravity else row["name"],
                            "after": name})
    if any(entry["name"] in names for entry in gravity if entry["path"] not in matched_files):
        raise ValueError("An Antigravity destination-only project name would collide")
    desired_ids = [Path(row["path"]).stem if row["path"] else None for row in antigravity] + list(dict.fromkeys(extras))
    pending = {"opencode": sum(row["before"] != row["after"] for row in opencode),
               "antigravity_names": sum(row["before"] != row["after"] for row in antigravity),
               "antigravity_order": (None in desired_ids or saved_order != desired_ids
                                      or state.get("projectsFolderSortBy") != "custom")}
    return {"layout": layout, "pending": pending, "opencode": opencode, "antigravity": antigravity,
            "order_directories": [row["directory"] for row in layout],
            "order_extras": list(dict.fromkeys(extras)),
            "ui_before": fields(state, ["projectsOrder", "projectsFolderSortBy"]),
            "unavailable": ["OpenCode custom sections and manual order",
                            "Antigravity custom sections and project colors"]}


def replace_json_fields(path, expected, replacement, identity=None):
    """Merge owned fields only; desktop apps and other destination writers must stay closed."""
    ensure_apps_closed()
    before_identity = fingerprint(path)
    if before_identity is None or (identity and any(before_identity[k] != identity[k] for k in ("device", "inode"))):
        raise ValueError("Destination file was replaced or is not a regular file")
    data = read_json(path)
    if fields(data, expected) != expected:
        raise ValueError("Destination presentation changed; refusing to overwrite it")
    for key, field in replacement.items():
        if field["present"]:
            data[key] = field["value"]
        else:
            data.pop(key, None)
    encoded = (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode()
    descriptor, temporary = tempfile.mkstemp(prefix=".project-sync-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            os.fchmod(stream.fileno(), path.stat().st_mode & 0o777)
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
            stat = os.fstat(stream.fileno())
            owned_identity = {"device": stat.st_dev, "inode": stat.st_ino,
                              "sha256": hashlib.sha256(encoded).hexdigest()}
        ensure_apps_closed()
        if fingerprint(path) != before_identity:
            raise ValueError("Destination file changed during presentation update")
        os.replace(temporary, path)
        return owned_identity
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def patch_metadata(service, project_id, before, after):
    current = next((entry for entry in service.get("/api/project") if entry["id"] == project_id), None)
    if current is None or metadata_fields(current) != before:
        raise ValueError("OpenCode metadata changed; refusing to overwrite it")
    payload = {}
    if before["name"] != after["name"]:
        payload["name"] = after["name"] if after["name"] is not None else ""
    if before["color"] != after["color"]:
        payload["icon"] = {"color": after["color"] if after["color"] is not None else ""}
    if payload:
        ensure_apps_closed()
        service.patch("/api/project/" + urllib.parse.quote(project_id, safe=""), payload)
    current = next((entry for entry in service.get("/api/project") if entry["id"] == project_id), None)
    if current is None or metadata_fields(current) != after:
        raise ValueError("OpenCode did not retain the requested project metadata")


def apply_presentation(locations, presentation, record_dir, service):
    """Journal each narrow change before mutation; uncertain outcomes remain inspectable."""
    known = {str(Path(entry["canonical"]).resolve()): entry for entry in service.get("/api/project")}
    gravity = antigravity_projects(locations["antigravity"])
    actions = []
    for entry in presentation["opencode"]:
        current = known.get(entry["directory"])
        if current is None or metadata_fields(current) != entry["before"]:
            raise ValueError("OpenCode presentation snapshot changed")
        if (current.get("icon") or {}).get("override"):
            raise ValueError("A manual icon appeared before applying presentation")
        if entry["before"] != entry["after"]:
            actions.append({"kind": "opencode", "id": current["id"],
                            "before": entry["before"], "after": entry["after"]})
    destination_ids = []
    for entry in presentation["antigravity"]:
        matches = [item for item in gravity if entry["directory"] in item["directories"]]
        if len(matches) != 1 or matches[0]["name"] != entry["before"]:
            raise ValueError("Antigravity presentation snapshot changed")
        target = Path(matches[0]["path"])
        destination_ids.append(target.stem)
        if entry["before"] != entry["after"]:
            actions.append({"kind": "json", "path": str(target),
                            "before": {"name": {"present": True, "value": entry["before"]}},
                            "after": {"name": {"present": True, "value": entry["after"]}}})
    ui_after = {"projectsOrder": {"present": True, "value": json.dumps(destination_ids + presentation["order_extras"])},
                "projectsFolderSortBy": {"present": True, "value": "custom"}}
    if presentation["ui_before"] != ui_after:
        actions.append({"kind": "json", "path": str(locations["antigravity_state"]),
                        "before": presentation["ui_before"], "after": ui_after})
    for index, action in enumerate(actions):
        ensure_apps_closed()
        write_new_json(record_dir / f"presentation-intent-{index:03}.json", action)
        if action["kind"] == "opencode":
            patch_metadata(service, action["id"], action["before"], action["after"])
            confirmed = action
        else:
            identity = replace_json_fields(Path(action["path"]), action["before"], action["after"])
            confirmed = {**action, "identity": identity}
        write_new_json(record_dir / f"presentation-confirmed-{index:03}.json", confirmed)
    updated_identities = {read_json(path)["path"]: read_json(path)["identity"]
                          for path in record_dir.glob("presentation-confirmed-*.json")
                          if read_json(path)["kind"] == "json"}
    for receipt in record_dir.glob("antigravity-*.json"):
        entry = read_json(receipt)
        write_new_json(record_dir / ("presentation-created-" + receipt.stem.removeprefix("antigravity-") + ".json"),
                       {"path": entry["path"], "fingerprint": updated_identities.get(entry["path"], entry["fingerprint"])})


def rollback_presentation(locations, record_dir, service, preserved):
    restored, uncertain = 0, []
    created_paths = {read_json(receipt)["path"] for receipt in record_dir.glob("antigravity-*.json")}
    for intent in sorted(record_dir.glob("presentation-intent-*.json"), reverse=True):
        confirmed = intent.with_name(intent.name.replace("-intent-", "-confirmed-"))
        if not confirmed.exists():
            uncertain.append(intent.name)
            continue
        action = read_json(confirmed)
        try:
            if action["kind"] == "opencode":
                service = service or OpenCodeService(locations["service"])
                patch_metadata(service, action["id"], action["after"], action["before"])
            elif action["kind"] == "json":
                path = Path(action["path"])
                if str(path) in created_paths:
                    continue  # Membership rollback owns deletion of this newly created record.
                if path != locations["antigravity_state"] and (path.parent != locations["antigravity"] or path.suffix != ".json"):
                    raise ValueError("Presentation receipt points outside owned destinations")
                replace_json_fields(path, action["after"], action["before"], action["identity"])
            else:
                raise ValueError("Unsupported presentation receipt kind")
            restored += 1
        except (ValueError, OSError):
            preserved.append(confirmed.name)
    return {"presentation_restored": restored, "unconfirmed_presentation": uncertain}


def ensure_apps_closed():
    try:
        result = subprocess.run(["/bin/ps", "-axo", "comm="], capture_output=True,
                                text=True, check=True)
    except (OSError, subprocess.CalledProcessError) as error:
        raise ValueError("Cannot verify closed desktop apps; no project-list update permitted") from error
    running = [name for name in ("OpenCode", "Antigravity")
               if any(f"/{name}.app/Contents/" in line for line in result.stdout.splitlines())]
    if running:
        raise ValueError("Save your work and fully quit these apps before applying: " + ", ".join(running))


def check_antigravity_version():
    for name, expected in (("Antigravity", "2.29.0"), ("OpenCode", "2.2.5")):
        info = Path(f"/Applications/{name}.app/Contents/Info.plist")
        version = plistlib.loads(info.read_bytes()).get("CFBundleShortVersionString")
        if version != expected:
            raise ValueError(f"The {name} project-list adapter requires review after an app version change (expected {expected})")


@contextmanager
def mutation_lock(directory):
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(directory / ".lock", os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("Another project synchronization is in progress") from None
        yield
    finally:
        os.close(descriptor)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        raise ValueError("Refusing an OpenCode service redirect")


class OpenCodeService:
    def __init__(self, metadata):
        data = read_json(metadata)
        parsed = urllib.parse.urlsplit(data["url"])
        if (parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost", "::1")
                or parsed.username or parsed.password or parsed.path not in ("", "/")
                or parsed.query or parsed.fragment):
            raise ValueError("OpenCode service must be a local loopback HTTP endpoint")
        self.url = data["url"].rstrip("/")
        self.authorization = "Basic " + base64.b64encode(
            ("opencode:" + data["password"]).encode()).decode()
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect)

    def get(self, route, query=None):
        return self.request("GET", route, query=query)

    def patch(self, route, payload):
        return self.request("PATCH", route, payload=payload)

    def request(self, method, route, query=None, payload=None):
        url = self.url + route
        if query:
            url += "?" + urllib.parse.urlencode(query)
        request = urllib.request.Request(url, method=method,
            data=json.dumps(payload).encode() if payload is not None else None,
            headers={"Authorization": self.authorization, "Content-Type": "application/json"})
        try:
            with self.opener.open(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            raise ValueError(f"OpenCode {route} returned HTTP {error.code}") from None
        except urllib.error.URLError:
            raise ValueError("OpenCode background service is unavailable; start OpenCode, then quit its desktop window") from None


def registry_projects(database):
    with connect(database) as connection:
        return [dict(row) for row in connection.execute(
            "SELECT id,worktree,time_archived FROM project")]


def selection(value):
    if value.get("projects", {}).get("local"):
        raise ValueError("OpenCode still has legacy project selection; let the app migrate it before synchronizing")
    result = {}
    for key in ("usedProjectIDs", "lastProjectID"):
        mapping = value.get(key)
        if not isinstance(mapping, dict):
            raise ValueError(f"Unsupported OpenCode state schema: {key}")
        result[key] = {"present": "local" in mapping, "value": mapping.get("local")}
    ids = result["usedProjectIDs"]["value"]
    if ids is not None and (not isinstance(ids, list) or not all(isinstance(item, str) for item in ids)):
        raise ValueError("Unsupported OpenCode usedProjectIDs schema")
    return result


def read_selection(database):
    with connect(database) as connection:
        row = connection.execute("SELECT value FROM state WHERE name=? AND key=?",
                                 (STORE_NAME, STORE_KEY)).fetchone()
    if row is None:
        raise ValueError("OpenCode desktop project state has not been initialized")
    return selection(json.loads(row["value"]))


def replace_selection(database, expected, replacement):
    ensure_apps_closed()
    with connect(database, writable=True) as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute("SELECT value FROM state WHERE name=? AND key=?",
                                 (STORE_NAME, STORE_KEY)).fetchone()
        if row is None:
            raise ValueError("OpenCode desktop state disappeared")
        value = json.loads(row["value"])
        if selection(value) != expected:
            raise ValueError("OpenCode project selection changed; refusing to overwrite it")
        for key, field in replacement.items():
            if field["present"]:
                value[key]["local"] = field["value"]
            else:
                value[key].pop("local", None)
        ensure_apps_closed()
        connection.execute("UPDATE state SET value=?,updated_at=? WHERE name=? AND key=?",
                           (json.dumps(value, separators=(",", ":")), int(time.time() * 1000),
                            STORE_NAME, STORE_KEY))


def resource_directories(project):
    resources = project.get("projectResources", {}).get("resources", [])
    if not isinstance(resources, list):
        raise ValueError("Unsupported Antigravity resource schema")
    result = set()
    for resource in resources:
        uri = resource.get("folderUri") or resource.get("gitFolder", {}).get("folderUri")
        if not uri:
            continue
        parsed = urllib.parse.urlsplit(uri)
        if parsed.scheme == "file" and parsed.netloc in ("", "localhost"):
            result.add(str(Path(urllib.parse.unquote(parsed.path)).resolve()))
    return result


def antigravity_projects(directory):
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError(f"Antigravity project registry is missing or linked: {directory}")
    result = []
    for path in sorted(directory.glob("*.json")):
        if path.is_symlink():
            raise ValueError(f"Linked Antigravity project record: {path}")
        data = read_json(path)
        if data.get("id") != path.stem:
            raise ValueError(f"Antigravity project identity does not match its filename: {path.name}")
        result.append({"path": str(path), "name": data.get("name"),
                       "directories": sorted(resource_directories(data))})
    return result


def antigravity_payload(project, identifier):
    directory = Path(project["directory"])
    resource = {"folderUri": directory.as_uri()}
    if (directory / ".git").exists():
        resource = {"gitFolder": resource}
    return {"id": identifier, "name": project["name"],
            "projectResources": {"resources": [resource]},
            "permissionGrants": {"v2Migrated": True}, "settings": {},
            "isWorkspaceOnly": False}


def build_plan(locations, replace=False, presentation=False):
    source = source_projects(locations["source"])
    known = registry_projects(locations["opencode_database"])
    before = read_selection(locations["opencode_ui"])
    existing_gravity = antigravity_projects(locations["antigravity"])
    gravity_folders = {folder for entry in existing_gravity for folder in entry["directories"]}
    gravity_names = {entry["name"] for entry in existing_gravity}
    for project in source:
        if project["directory"] in gravity_folders:
            continue
        if project["name"] in gravity_names:
            raise ValueError(f"Antigravity already has a different folder named {project['name']}; resolve that name collision first")
        gravity_names.add(project["name"])
    known_by_path = {str(Path(entry["worktree"]).resolve()): entry for entry in known}
    for project in source:
        entry = known_by_path.get(project["directory"])
        if entry is not None and entry["time_archived"] is not None:
            raise ValueError(f"An intended OpenCode project is archived: {project['directory']}")
    existing_ids = before["usedProjectIDs"]["value"] or []
    desired_paths = {project["directory"] for project in source}
    hidden = [entry["worktree"] for entry in known
              if replace and entry["id"] in existing_ids
              and str(Path(entry["worktree"]).resolve()) not in desired_paths]
    plan = {"format": FORMAT, "mode": "replace-opencode" if replace else "add-only",
            "source": source, "opencode_before": before,
            "opencode_register": [project["directory"] for project in source
                                   if project["directory"] not in known_by_path],
            "opencode_hide": hidden,
            "antigravity_add": [project for project in source if project["directory"] not in gravity_folders],
            "antigravity_preserved_records": len(existing_gravity)}
    if presentation:
        plan["format"] = PRESENTATION_FORMAT
        plan["presentation"] = presentation_plan(locations, source_layout(locations, source))
    return plan


def apply(locations, plan, service=None):
    ensure_apps_closed()
    check_antigravity_version()
    if source_projects(locations["source"]) != plan["source"]:
        raise ValueError("Codex project list changed since planning")
    if read_selection(locations["opencode_ui"]) != plan["opencode_before"]:
        raise ValueError("OpenCode project list changed since planning")
    current_plan = build_plan(locations, plan["mode"] == "replace-opencode", "presentation" in plan)
    if current_plan != plan:
        raise ValueError("Destination project records changed since planning; preview again")
    service = service or OpenCodeService(locations["service"])
    if service.get("/api/info")["version"] != "2.2.5":
        raise ValueError("This OpenCode desktop adapter requires review after an app version change (expected 2.2.5)")
    if service.get("/api/session/active").get("data"):
        raise ValueError("OpenCode has active sessions; wait before synchronizing projects")
    locations["records"].mkdir(parents=True, exist_ok=True, mode=0o700)
    record_dir = locations["records"] / (time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8])
    record_dir.mkdir(mode=0o700)
    write_new_json(record_dir / "plan.json", plan)
    print(f"Recovery record: {record_dir}", file=sys.stderr)
    known = service.get("/api/project")
    by_path = {str(Path(entry["canonical"]).resolve()): entry for entry in known}
    desired = []
    for project in plan["source"]:
        entry = by_path.get(project["directory"])
        if entry is None:
            resolved = service.get("/api/location", {"location[directory]": project["directory"]})
            entry = resolved["project"]
            if str(Path(entry["canonical"]).resolve()) != project["directory"]:
                raise ValueError("OpenCode resolved a different canonical folder; project-list changes stopped")
            write_new_json(record_dir / ("registered-" + str(len(desired)) + ".json"),
                           {"id": entry["id"], "directory": project["directory"]})
        if entry.get("time", {}).get("archived") is not None:
            raise ValueError(f"An intended OpenCode project is archived: {project['directory']}")
        desired.append(entry["id"])
    desired = list(dict.fromkeys(desired))
    before = plan["opencode_before"]
    prior_ids = before["usedProjectIDs"]["value"] or []
    after_ids = desired if plan["mode"] == "replace-opencode" else list(dict.fromkeys(prior_ids + desired))
    previous_last = before["lastProjectID"]["value"]
    after = {"usedProjectIDs": {"present": True, "value": after_ids},
             "lastProjectID": {"present": True, "value": previous_last if previous_last in after_ids else after_ids[0]}}
    write_new_json(record_dir / "opencode-selection.json", {"before": before, "after": after})
    ensure_apps_closed()
    replace_selection(locations["opencode_ui"], before, after)
    existing = {folder for entry in antigravity_projects(locations["antigravity"])
                for folder in entry["directories"]}
    for project in plan["antigravity_add"]:
        if project["directory"] in existing:
            continue
        ensure_apps_closed()
        identifier = str(uuid.uuid4())
        target = locations["antigravity"] / (identifier + ".json")
        payload = antigravity_payload(project, identifier)
        write_new_json(record_dir / ("intent-" + identifier + ".json"),
                       {"path": str(target), "project": payload})
        expected = write_new_json(target, payload)
        write_new_json(record_dir / ("antigravity-" + identifier + ".json"),
                       {"path": str(target), "fingerprint": expected})
        existing.add(project["directory"])
    final = read_selection(locations["opencode_ui"])
    if final != after:
        raise ValueError(f"OpenCode selection changed during synchronization; inspect {record_dir}")
    if "presentation" in plan:
        apply_presentation(locations, plan["presentation"], record_dir, service)
    write_new_json(record_dir / "complete.json", {"format": plan["format"], "opencode_selected": len(after_ids),
                                                "antigravity_added": len(list(record_dir.glob('antigravity-*.json')))})
    return {"receipt": str(record_dir), "opencode_selected": len(after_ids),
            "antigravity_added": len(list(record_dir.glob("antigravity-*.json")))}


def rollback(locations, record_dir, service=None):
    ensure_apps_closed()
    check_antigravity_version()
    plan = read_json(record_dir / "plan.json")
    if plan.get("format") not in (FORMAT, PRESENTATION_FORMAT):
        raise ValueError("Unrecognized project-sync receipt")
    result = {"restored_opencode": False, "removed_antigravity": [], "preserved": [],
              "unconfirmed_antigravity": []}
    if plan.get("format") == PRESENTATION_FORMAT:
        service = service or OpenCodeService(locations["service"])
        if service.get("/api/info")["version"] != "2.2.5":
            raise ValueError("OpenCode service version changed before presentation rollback")
        if service.get("/api/session/active").get("data"):
            raise ValueError("OpenCode has active sessions; wait before presentation rollback")
        result.update(rollback_presentation(locations, record_dir, service, result["preserved"]))
    receipt = record_dir / "opencode-selection.json"
    if receipt.exists():
        value = read_json(receipt)
        if read_selection(locations["opencode_ui"]) == value["after"]:
            replace_selection(locations["opencode_ui"], value["after"], value["before"])
            result["restored_opencode"] = True
        else:
            result["preserved"].append("OpenCode selection changed after synchronization")
    for receipt in record_dir.glob("antigravity-*.json"):
        entry = read_json(receipt)
        presentation_owner = record_dir / ("presentation-created-" + receipt.stem.removeprefix("antigravity-") + ".json")
        if plan.get("format") == PRESENTATION_FORMAT and presentation_owner.exists():
            refreshed = read_json(presentation_owner)
            if refreshed["path"] != entry["path"]:
                raise ValueError("Presentation ownership does not match the created project")
            entry = refreshed
        target = Path(entry["path"])
        if target.parent != locations["antigravity"] or target.suffix != ".json":
            raise ValueError("Receipt points outside the Antigravity project registry")
        ensure_apps_closed()
        if fingerprint(target) == entry["fingerprint"]:
            target.unlink()
            result["removed_antigravity"].append(str(target))
        else:
            result["preserved"].append(str(target))
    for intent in record_dir.glob("intent-*.json"):
        identifier = intent.stem.removeprefix("intent-")
        if (record_dir / ("antigravity-" + identifier + ".json")).exists():
            continue
        target = Path(read_json(intent)["path"])
        if target.parent != locations["antigravity"]:
            raise ValueError("Intent points outside the Antigravity project registry")
        if target.exists() or target.is_symlink():
            result["unconfirmed_antigravity"].append(str(target))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, default=Path.home(), help="Use a separate home for fixtures")
    parser.add_argument("--sync-presentation", action="store_true", help="Preview/sync Codex section labels, supported colors and order")
    parser.add_argument("--apply", action="store_true", help="Apply after both desktop apps are fully quit")
    parser.add_argument("--replace-opencode", action="store_true", help="Replace visible OpenCode selection only")
    parser.add_argument("--rollback", type=Path, help="Restore unchanged project-list changes from this receipt")
    args = parser.parse_args()
    locations = paths(args.home.expanduser().resolve())
    try:
        if args.rollback:
            if not args.apply:
                raise ValueError("Rollback requires --apply and both desktop apps closed")
            ensure_apps_closed()
            with mutation_lock(locations["records"]):
                result = rollback(locations, args.rollback.expanduser().resolve())
        else:
            plan = build_plan(locations, args.replace_opencode, args.sync_presentation)
            if args.apply:
                ensure_apps_closed()
                with mutation_lock(locations["records"]):
                    result = apply(locations, plan)
            else:
                result = plan
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except (ValueError, OSError, sqlite3.Error, KeyError) as error:
        parser.exit(1, f"Project sync stopped: {error}\n")


if __name__ == "__main__":
    main()
