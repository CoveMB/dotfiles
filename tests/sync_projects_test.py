"""Real SQLite/filesystem checks for project synchronization and recovery."""

import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from contextlib import closing
from unittest.mock import patch
import urllib.request
import io


SOURCE = Path(__file__).resolve().parents[1] / "sync-projects.py"
if not SOURCE.exists():
    SOURCE = Path(__file__).with_name("sync-projects.py")
spec = importlib.util.spec_from_file_location("project_sync", SOURCE)
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class Service:
    def __init__(self, entries=None):
        self.entries = entries or []
        self.calls = []
        self.active = {}

    def get(self, route, query=None):
        self.calls.append((route, query))
        if route == "/api/info":
            return {"version": "2.2.5"}
        if route == "/api/session/active":
            return {"data": self.active}
        if route == "/api/project":
            return self.entries
        if route == "/api/location":
            directory = query["location[directory]"]
            entry = {"id": "new-" + Path(directory).name, "canonical": directory, "time": {}}
            self.entries.append(entry)
            return {"project": entry}
        raise AssertionError(route)


class ProjectSyncTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.locations = sync.paths(self.home)
        for path in self.locations.values():
            path.parent.mkdir(parents=True, exist_ok=True)
        self.locations["antigravity"].mkdir()
        self.first = self.home / "project one"
        self.second = self.home / "project-two"
        self.first.mkdir()
        self.second.mkdir()
        with closing(sqlite3.connect(self.locations["source"])) as connection, connection:
            connection.executescript("CREATE TABLE projects(id TEXT,name TEXT,position INTEGER);"
                                     "CREATE TABLE project_roots(project_id TEXT,position INTEGER,path TEXT);")
            connection.executemany("INSERT INTO projects VALUES(?,?,?)", [("one", "One", 0), ("two", "Two", 1)])
            connection.executemany("INSERT INTO project_roots VALUES(?,?,?)", [("one", 0, str(self.first)), ("two", 0, str(self.second))])
        with closing(sqlite3.connect(self.locations["opencode_database"])) as connection, connection:
            connection.execute("CREATE TABLE project(id TEXT,worktree TEXT,time_archived INTEGER)")
            connection.execute("INSERT INTO project VALUES(?,?,NULL)", ("old-only", str(self.home / "old")))
        self.ui = {"usedProjectIDs": {"local": ["old-only"], "remote": ["remote-id"]},
                   "lastProjectID": {"local": "old-only"}, "list": [{"password": "private-secret"}],
                   "unrelated": {"keep": True}}
        with closing(sqlite3.connect(self.locations["opencode_ui"])) as connection, connection:
            connection.execute("CREATE TABLE state(name TEXT,key TEXT,value TEXT,updated_at INTEGER)")
            connection.execute("INSERT INTO state VALUES(?,?,?,0)", (sync.STORE_NAME, sync.STORE_KEY, json.dumps(self.ui)))
        self.old_gravity = self.locations["antigravity"] / "existing.json"
        sync.write_new_json(self.old_gravity, {"id": "existing", "name": "Existing",
            "projectResources": {"resources": [{"folderUri": self.first.as_uri()}]},
            "permissionGrants": {"custom": "preserve"}})
        self.closed = patch.object(sync, "ensure_apps_closed")
        self.closed.start()
        self.addCleanup(self.closed.stop)
        self.version = patch.object(sync, "check_antigravity_version")
        self.version.start()
        self.addCleanup(self.version.stop)

    def state(self):
        with closing(sqlite3.connect(self.locations["opencode_ui"])) as connection, connection:
            return json.loads(connection.execute("SELECT value FROM state").fetchone()[0])

    def test_preview_has_no_writes_and_reports_replacement(self):
        before = {key: path.read_bytes() for key, path in self.locations.items() if path.is_file()}
        plan = sync.build_plan(self.locations, replace=True)
        self.assertEqual(plan["opencode_hide"], [str(self.home / "old")])
        self.assertEqual([item["name"] for item in plan["antigravity_add"]], ["Two"])
        self.assertEqual(before, {key: self.locations[key].read_bytes() for key in before})
        self.assertFalse(self.locations["records"].exists())

    def test_replace_preserves_source_history_other_state_and_permissions(self):
        original_source = self.locations["source"].read_bytes()
        original_registry = self.locations["opencode_database"].read_bytes()
        original_gravity = self.old_gravity.read_bytes()
        result = sync.apply(self.locations, sync.build_plan(self.locations, True), Service())
        self.assertEqual(self.state()["usedProjectIDs"]["local"], ["new-project one", "new-project-two"])
        self.assertEqual(self.state()["usedProjectIDs"]["remote"], ["remote-id"])
        self.assertEqual(self.state()["list"], self.ui["list"])
        self.assertEqual(self.state()["unrelated"], self.ui["unrelated"])
        self.assertEqual(original_source, self.locations["source"].read_bytes())
        self.assertEqual(original_registry, self.locations["opencode_database"].read_bytes())
        self.assertEqual(original_gravity, self.old_gravity.read_bytes())
        self.assertEqual(result["antigravity_added"], 1)
        for path in Path(result["receipt"]).glob("*.json"):
            self.assertNotIn("private-secret", path.read_text())

    def test_add_only_rerun_does_not_duplicate_projects(self):
        service = Service()
        first = sync.apply(self.locations, sync.build_plan(self.locations), service)
        expected = self.state()
        second = sync.apply(self.locations, sync.build_plan(self.locations), service)
        self.assertEqual(expected, self.state())
        self.assertEqual(second["antigravity_added"], 0)
        self.assertEqual(first["opencode_selected"], 3)

    def test_rollback_preserves_later_user_changes(self):
        result = sync.apply(self.locations, sync.build_plan(self.locations, True), Service())
        created = next(path for path in self.locations["antigravity"].glob("*.json") if path != self.old_gravity)
        created.write_text(created.read_text() + "\n")
        changed = sync.read_selection(self.locations["opencode_ui"])
        replacement = json.loads(json.dumps(changed))
        replacement["usedProjectIDs"]["value"].append("user-added")
        sync.replace_selection(self.locations["opencode_ui"], changed, replacement)
        restored = sync.rollback(self.locations, Path(result["receipt"]))
        self.assertFalse(restored["restored_opencode"])
        self.assertTrue(created.exists())
        self.assertEqual(len(restored["preserved"]), 2)

    def test_rollback_restores_only_owned_selection_and_files(self):
        result = sync.apply(self.locations, sync.build_plan(self.locations, True), Service())
        restored = sync.rollback(self.locations, Path(result["receipt"]))
        self.assertTrue(restored["restored_opencode"])
        self.assertEqual(self.state(), self.ui)
        self.assertEqual(list(self.locations["antigravity"].glob("*.json")), [self.old_gravity])

    def test_rollback_preserves_file_replaced_during_final_process_check(self):
        result = sync.apply(self.locations, sync.build_plan(self.locations, True), Service())
        created = next(path for path in self.locations["antigravity"].glob("*.json") if path != self.old_gravity)
        changed = []
        def replace_after_ui_restore():
            if self.state() == self.ui and not changed:
                replacement = created.with_suffix(".replacement")
                replacement.write_bytes(created.read_bytes() + b"\n")
                replacement.replace(created)
                changed.append(True)
        with patch.object(sync, "ensure_apps_closed", side_effect=replace_after_ui_restore):
            restored = sync.rollback(self.locations, Path(result["receipt"]))
        self.assertEqual(changed, [True])
        self.assertTrue(created.exists(), "Rollback removed a later replacement")
        self.assertIn(str(created), restored["preserved"])

    def test_recreated_identical_file_is_not_removed(self):
        result = sync.apply(self.locations, sync.build_plan(self.locations, True), Service())
        created = next(path for path in self.locations["antigravity"].glob("*.json") if path != self.old_gravity)
        replacement = created.with_suffix(".replacement")
        replacement.write_bytes(created.read_bytes())
        replacement.replace(created)
        sync.rollback(self.locations, Path(result["receipt"]))
        self.assertTrue(created.exists())

    def test_stale_selection_stops_without_overwrite(self):
        before = sync.read_selection(self.locations["opencode_ui"])
        wrong = json.loads(json.dumps(before))
        wrong["usedProjectIDs"]["value"] = ["unexpected"]
        with self.assertRaisesRegex(ValueError, "changed"):
            sync.replace_selection(self.locations["opencode_ui"], wrong, before)
        self.assertEqual(self.state(), self.ui)

    def test_missing_or_multiple_source_roots_stop(self):
        self.second.rmdir()
        with self.assertRaises(FileNotFoundError):
            sync.build_plan(self.locations)
        self.second.mkdir()
        with closing(sqlite3.connect(self.locations["source"])) as connection, connection:
            connection.execute("INSERT INTO project_roots VALUES(?,?,?)", ("one", 1, str(self.second)))
        with self.assertRaisesRegex(ValueError, "Multi-folder"):
            sync.build_plan(self.locations)

    def test_archived_source_project_stops_before_registration(self):
        with closing(sqlite3.connect(self.locations["opencode_database"])) as connection, connection:
            connection.execute("UPDATE project SET worktree=?,time_archived=123 WHERE id='old-only'",
                               (str(self.first),))
        service = Service()  # The native list endpoint excludes archived records.
        with self.assertRaisesRegex(ValueError, "archived"):
            sync.apply(self.locations, sync.build_plan(self.locations), service)
        self.assertEqual(service.calls, [])
        self.assertEqual(self.state(), self.ui)
        self.assertEqual(list(self.locations["antigravity"].glob("*.json")), [self.old_gravity])
        self.assertFalse(self.locations["records"].exists())

    def test_active_sessions_stop_before_destination_writes(self):
        service = Service()
        service.active = {"session": "running"}
        with self.assertRaisesRegex(ValueError, "active sessions"):
            sync.apply(self.locations, sync.build_plan(self.locations), service)
        self.assertEqual(self.state(), self.ui)
        self.assertFalse(self.locations["records"].exists())

    def test_nonlocal_endpoint_rejected_without_request(self):
        sync.write_new_json(self.locations["service"], {"url": "http://example.com", "password": "secret"})
        with self.assertRaisesRegex(ValueError, "loopback"):
            sync.OpenCodeService(self.locations["service"])

    def test_existing_project_name_collision_stops_before_writes(self):
        data = sync.read_json(self.old_gravity)
        data["name"] = "Two"
        self.old_gravity.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "name collision"):
            sync.build_plan(self.locations)
        self.assertEqual(self.state(), self.ui)

    def test_exclusive_lock_rejects_second_writer(self):
        with sync.mutation_lock(self.locations["records"]):
            with self.assertRaisesRegex(ValueError, "in progress"):
                with sync.mutation_lock(self.locations["records"]):
                    self.fail("Second writer obtained lock")

    def test_atomic_publish_never_overwrites_existing_file(self):
        before = self.old_gravity.read_bytes()
        with self.assertRaises(FileExistsError):
            sync.write_new_json(self.old_gravity, {"replacement": True})
        self.assertEqual(before, self.old_gravity.read_bytes())

    def test_proxy_environment_cannot_receive_local_service_credentials(self):
        sync.write_new_json(self.locations["service"], {"url": "http://127.0.0.1:12345", "password": "secret"})
        destinations = []
        def transport(handler, request):
            destinations.append(request.host)
            response = io.BytesIO(b'{"ok":true}')
            response.code, response.msg = 200, "OK"
            response.info = lambda: {}
            return response
        with patch.dict("os.environ", {"http_proxy": "http://proxy.invalid:8080", "no_proxy": ""}):
            service = sync.OpenCodeService(self.locations["service"])
            with patch.object(urllib.request.HTTPHandler, "http_open", transport):
                self.assertEqual(service.get("/api/info"), {"ok": True})
        self.assertEqual(destinations, ["127.0.0.1:12345"])

    def test_legacy_selection_requires_migration(self):
        value = dict(self.ui, projects={"local": [{"worktree": "/old"}]})
        with self.assertRaisesRegex(ValueError, "legacy"):
            sync.selection(value)

    def test_interrupted_publish_is_reported_and_preserved(self):
        result = sync.apply(self.locations, sync.build_plan(self.locations, True), Service())
        record = Path(result["receipt"])
        receipt = next(record.glob("antigravity-*.json"))
        created = Path(sync.read_json(receipt)["path"])
        receipt.unlink()  # Simulate interruption after atomic publication but before its receipt.
        restored = sync.rollback(self.locations, record)
        self.assertEqual(restored["unconfirmed_antigravity"], [str(created)])
        self.assertTrue(created.exists())


class PresentationTest(unittest.TestCase):
    setUp = ProjectSyncTest.setUp
    state = ProjectSyncTest.state

    def layout_fixture(self, section="Egeria"):
        with closing(sqlite3.connect(self.locations["source"])) as connection, connection:
            connection.execute("ALTER TABLE projects ADD COLUMN metadata TEXT")
            for identifier in ["one", "two"]:
                metadata = {"codex.localProjectId": "legacy-" + identifier,
                            "codex.chatGptBacking": json.dumps({"projectId": "g-p-" + identifier,
                                                                "accountId": "private-account", "userId": "private-user"})}
                connection.execute("UPDATE projects SET metadata=? WHERE id=?", (json.dumps(metadata), identifier))
        data = {"sections": [{"id": "group", "name": section, "itemKeys": ["codex:project:legacy-one"]}],
                "sectionOrder": ["custom:group", "threads", "pinned"]}
        self.global_state = self.home / ".codex/.codex-global-state.json"
        self.global_state.write_text(json.dumps({"electron-persisted-atom-state": {
            "sidebar-custom-sections-v3": {"private-account": data},
            "unified-sidebar-project-order-v1": ["chatgpt:project:g-p-two", "chatgpt:project:g-p-one"],
            "unified-sidebar-pinned-order-v1": []}}))
        return sync.source_projects(self.locations["source"])

    def layout(self, projects):
        self.assertTrue(callable(getattr(sync, "source_layout", None)), "source_layout is not implemented")
        return sync.source_layout(self.locations, projects)

    def edit_layout(self, change):
        data = sync.read_json(self.global_state)
        change(data["electron-persisted-atom-state"])
        self.global_state.write_text(json.dumps(data))

    def test_source_layout_resolves_aliases_orders_groups_and_excludes_account_data(self):
        result = self.layout(self.layout_fixture())
        self.assertEqual([(r["id"],r["display_name"],r["color"],r["position"]) for r in result],
                         [("one", "[Egeria] One", "blue", 0), ("two", "Two", "green", 1)])
        self.assertNotIn("private-account", json.dumps(result))
        self.assertNotIn("private-user", json.dumps(result))

    def test_source_layout_uses_all_requested_section_colors(self):
        projects = self.layout_fixture()
        for section, color in [("Egeria","blue"),("Plugins","orange"),("External Plugins","yellow"),
                               ("Archive","gray"),("Archives","gray")]:
            self.edit_layout(lambda a: a["sidebar-custom-sections-v3"]["private-account"]["sections"][0].update(name=section))
            self.assertEqual(self.layout(projects)[0]["color"], color)

    def test_pinned_alias_deduplicates_project_without_losing_section(self):
        projects = self.layout_fixture()
        def change(a):
            a["sidebar-custom-sections-v3"]["private-account"]["sectionOrder"] = ["pinned", "threads", "custom:group"]
            a["unified-sidebar-pinned-order-v1"] = ["chatgpt:thread:ignored", "chatgpt:project:g-p-one"]
        self.edit_layout(change)
        result = self.layout(projects)
        self.assertEqual([r["id"] for r in result], ["one", "two"])
        self.assertEqual(result[0]["display_name"], "[Egeria] One")

    def test_source_section_move_removes_old_prefix(self):
        projects = self.layout_fixture()
        self.assertEqual(self.layout(projects)[0]["display_name"], "[Egeria] One")
        self.edit_layout(lambda a: a["sidebar-custom-sections-v3"]["private-account"]["sections"][0].update(name="Plugins"))
        self.assertEqual(self.layout(projects)[0]["display_name"], "[Plugins] One")
        self.edit_layout(lambda a: a["sidebar-custom-sections-v3"]["private-account"]["sections"][0].update(itemKeys=[]))
        self.assertEqual([r["display_name"] for r in self.layout(projects)], ["Two", "One"])

    def test_unmapped_section_and_conflicting_membership_stop(self):
        projects = self.layout_fixture("New Group")
        with self.assertRaisesRegex(ValueError, "color mapping"):
            self.layout(projects)
        def change(a):
            d=a["sidebar-custom-sections-v3"]["private-account"]
            d["sections"][0]["name"]="Egeria"
            d["sections"].append({"id":"other","name":"Plugins","itemKeys":["chatgpt:project:g-p-one"]})
            d["sectionOrder"].append("custom:other")
        self.edit_layout(change)
        with self.assertRaisesRegex(ValueError, "multiple custom sections"):
            self.layout(projects)

    def test_ambiguous_accounts_and_unresolved_local_references_stop(self):
        projects = self.layout_fixture()
        self.edit_layout(lambda a: a["sidebar-custom-sections-v3"].update(another=a["sidebar-custom-sections-v3"]["private-account"]))
        with self.assertRaisesRegex(ValueError, "section collection"):
            self.layout(projects)
        def change(a):
            a["sidebar-custom-sections-v3"].pop("another")
            a["sidebar-custom-sections-v3"]["private-account"]["sections"][0]["itemKeys"].append("codex:project:missing")
        self.edit_layout(change)
        with self.assertRaisesRegex(ValueError, "Unresolved local"):
            self.layout(projects)

    def destination_fixture(self):
        projects = self.layout_fixture()
        with closing(sqlite3.connect(self.locations["opencode_database"])) as connection, connection:
            for column in ["name", "icon_color", "icon_url", "icon_url_override"]:
                connection.execute("ALTER TABLE project ADD COLUMN " + column + " TEXT")
            connection.executemany("INSERT INTO project(id,worktree) VALUES(?,?)", [("oc-one",str(self.first)),("oc-two",str(self.second))])
            connection.execute("UPDATE project SET icon_url='automatic-logo' WHERE id='oc-one'")
        self.locations["antigravity_state"].write_text(json.dumps({"projectsOrder":json.dumps(["existing"]),
                                                                 "other":"private-secret"}))
        return projects

    def presentation_plan(self):
        self.assertIn("presentation", sync.build_plan(self.locations, presentation=True))
        return sync.build_plan(self.locations, presentation=True)

    def presentation_service(self):
        entries=[{"id":"oc-one","canonical":str(self.first),"icon":{"url":"automatic-logo"},"commands":{"start":"keep"},"time":{}},
                 {"id":"oc-two","canonical":str(self.second),"time":{}}]
        database=self.locations['opencode_database']
        class MetadataService(Service):
            def patch(self, route, payload):
                project=next(p for p in self.entries if route.endswith('/'+p['id']))
                self.calls.append((route,payload))
                if "name" in payload:
                    if payload["name"]:project["name"]=payload["name"]
                    else:project.pop("name",None)
                if "icon" in payload:
                    icon=project.setdefault("icon",{})
                    for key,value in payload["icon"].items():
                        if value:icon[key]=value
                        else:icon.pop(key,None)
                with closing(sqlite3.connect(database)) as connection, connection:
                    connection.execute('UPDATE project SET name=?,icon_color=? WHERE id=?',
                                       (project.get('name'),project.get('icon',{}).get('color'),project['id']))
                return project
        return MetadataService(entries)

    def test_presentation_preview_reports_colors_names_order_and_icon_effect(self):
        self.destination_fixture()
        plan=self.presentation_plan()["presentation"]
        self.assertIn("opencode",plan,"Presentation destination preview is not implemented")
        self.assertEqual([x["after"]["color"] for x in plan["opencode"]], ["blue","green"])
        self.assertEqual(plan["opencode"][0]["after"]["name"],"[Egeria] One")
        self.assertTrue(plan["opencode"][0]["hides_automatic_icon"])
        self.assertEqual(plan["antigravity"][0]["after"],"[Egeria] One")
        self.assertEqual(plan["order_directories"],[str(self.first.resolve()),str(self.second.resolve())])
        self.assertFalse(self.locations["records"].exists())

    def test_presentation_apply_and_rollback_preserve_sparse_metadata_and_settings(self):
        self.destination_fixture();service=self.presentation_service();before=self.old_gravity.read_bytes()
        self.assertTrue(callable(getattr(sync,"apply_presentation",None)),"presentation apply is not implemented")
        plan=self.presentation_plan();result=sync.apply(self.locations,plan,service)
        self.assertEqual(service.entries[0]["name"],"[Egeria] One")
        self.assertEqual(service.entries[0]["icon"],{"url":"automatic-logo","color":"blue"})
        self.assertEqual(service.entries[0]["commands"],{"start":"keep"})
        self.assertEqual(sync.read_json(self.old_gravity)["permissionGrants"],{"custom":"preserve"})
        state=sync.read_json(self.locations["antigravity_state"])
        self.assertEqual(state["projectsFolderSortBy"],"custom")
        order=json.loads(state["projectsOrder"])
        self.assertEqual(order[0],"existing");self.assertEqual(len(order),2)
        restored=sync.rollback(self.locations,Path(result["receipt"]),service)
        self.assertNotIn("name",service.entries[0]);self.assertNotIn("color",service.entries[0]["icon"])
        self.assertEqual(sync.read_json(self.old_gravity),json.loads(before))
        self.assertEqual(sync.read_json(self.locations["antigravity_state"]),{"projectsOrder":json.dumps(["existing"]),"other":"private-secret"})
        self.assertEqual(restored["presentation_restored"],4)
        for file in Path(result["receipt"]).glob('presentation-*.json'):
            self.assertNotIn("private-secret",file.read_text())

    def test_presentation_preserves_later_user_metadata_on_rollback(self):
        self.destination_fixture();service=self.presentation_service()
        self.assertTrue(callable(getattr(sync,"apply_presentation",None)),"presentation apply is not implemented")
        result=sync.apply(self.locations,self.presentation_plan(),service)
        service.entries[0]["name"]="My later name"
        old=sync.read_json(self.old_gravity);old["name"]="My later folder";self.old_gravity.write_text(json.dumps(old))
        restored=sync.rollback(self.locations,Path(result["receipt"]),service)
        self.assertEqual(service.entries[0]["name"],"My later name")
        self.assertEqual(sync.read_json(self.old_gravity)["name"],"My later folder")
        self.assertGreaterEqual(len(restored["preserved"]),2)

    def test_manual_icon_and_multiple_unlisted_destination_projects_stop(self):
        self.destination_fixture()
        with closing(sqlite3.connect(self.locations["opencode_database"])) as connection, connection:
            connection.execute("UPDATE project SET icon_url_override='manual-logo' WHERE id='oc-one'")
        with self.assertRaisesRegex(ValueError,"manual icon"):
            self.presentation_plan()
        with closing(sqlite3.connect(self.locations["opencode_database"])) as connection, connection:
            connection.execute("UPDATE project SET icon_url_override=NULL")
        for identifier in ['extra-a','extra-b']:
            directory=self.home/identifier;directory.mkdir()
            sync.write_new_json(self.locations['antigravity']/(identifier+'.json'),{'id':identifier,'name':identifier,
                'projectResources':{'resources':[{'folderUri':directory.as_uri()}]}})
        with self.assertRaisesRegex(ValueError,"destination-only order"):
            self.presentation_plan()

    def test_new_grouped_antigravity_project_is_removed_by_owned_rollback(self):
        self.destination_fixture();service=self.presentation_service()
        def change(a):
            d=a['sidebar-custom-sections-v3']['private-account']
            d['sections'].append({'id':'plugins','name':'Plugins','itemKeys':['codex:project:legacy-two']})
            d['sectionOrder'].append('custom:plugins')
        self.edit_layout(change)
        result=sync.apply(self.locations,self.presentation_plan(),service)
        self.assertEqual(len(list(self.locations['antigravity'].glob('*.json'))),2)
        sync.rollback(self.locations,Path(result['receipt']),service)
        self.assertEqual(list(self.locations['antigravity'].glob('*.json')),[self.old_gravity])

    def test_interrupted_metadata_patch_reports_uncertain_ownership(self):
        self.destination_fixture();service=self.presentation_service();original=sync.write_new_json
        def interrupt(path,value):
            if path.name.startswith('presentation-confirmed-'):
                raise OSError('Injected receipt interruption')
            return original(path,value)
        with patch.object(sync,'write_new_json',side_effect=interrupt):
            with self.assertRaisesRegex(OSError,'Injected'):
                sync.apply(self.locations,self.presentation_plan(),service)
        receipt=next(p for p in self.locations['records'].iterdir() if p.is_dir())
        restored=sync.rollback(self.locations,receipt,service)
        self.assertEqual(len(restored['unconfirmed_presentation']),1)
        self.assertEqual(service.entries[0]['name'],'[Egeria] One')

    def test_atomic_metadata_write_does_not_adopt_a_later_replacement(self):
        self.destination_fixture();original=sync.os.replace
        def replace_then_user_edit(source,target):
            original(source,target)
            if Path(target)==self.old_gravity:
                newer=self.old_gravity.with_suffix('.newer')
                newer.write_text(json.dumps({'id':'existing','name':'Later user record'}))
                original(newer,target)
        with patch.object(sync.os,'replace',side_effect=replace_then_user_edit):
            identity=sync.replace_json_fields(self.old_gravity,
                {'name':{'present':True,'value':'Existing'}},
                {'name':{'present':True,'value':'[Egeria] One'}})
        self.assertNotEqual(identity['inode'],self.old_gravity.stat().st_ino,
                            'Writer adopted a later replacement as its own')

    def test_repeated_presentation_preview_reports_zero_pending_changes(self):
        self.destination_fixture();service=self.presentation_service()
        sync.apply(self.locations,self.presentation_plan(),service)
        presentation=self.presentation_plan()['presentation']
        self.assertIn('pending',presentation,'Presentation change summary is not implemented')
        self.assertEqual(presentation['pending'],{'opencode':0,'antigravity_names':0,'antigravity_order':False})

    def test_stale_section_plan_stops_before_any_destination_mutation(self):
        self.destination_fixture();service=self.presentation_service();plan=self.presentation_plan()
        self.edit_layout(lambda a:a['sidebar-custom-sections-v3']['private-account']['sections'][0].update(name='Plugins'))
        with self.assertRaisesRegex(ValueError,'changed since planning'):
            sync.apply(self.locations,plan,service)
        self.assertEqual(service.calls,[])
        self.assertEqual(self.state(),self.ui)
        self.assertFalse(self.locations['records'].exists())

    def test_unicode_base_labels_and_empty_metadata_restore_limits(self):
        self.destination_fixture()
        with closing(sqlite3.connect(self.locations['source'])) as connection, connection:
            connection.execute("UPDATE projects SET name='Équipe' WHERE id='one'")
        self.assertEqual(self.presentation_plan()['presentation']['layout'][0]['display_name'],'[Egeria] Équipe')
        with closing(sqlite3.connect(self.locations['opencode_database'])) as connection, connection:
            connection.execute("UPDATE project SET icon_color='' WHERE id='oc-one'")
        with self.assertRaisesRegex(ValueError,'empty-string'):
            self.presentation_plan()

    def test_active_background_session_blocks_presentation_rollback(self):
        self.destination_fixture();service=self.presentation_service()
        result=sync.apply(self.locations,self.presentation_plan(),service)
        service.active={'session':'running'}
        with self.assertRaisesRegex(ValueError,'active sessions'):
            sync.rollback(self.locations,Path(result['receipt']),service)
        self.assertEqual(service.entries[0]['name'],'[Egeria] One')
        self.assertEqual(sync.read_json(self.old_gravity)['name'],'[Egeria] One')

    def test_activity_sort_blocks_multiple_destination_only_projects_even_if_listed(self):
        self.destination_fixture()
        for identifier in ['extra-a','extra-b']:
            folder=self.home/identifier;folder.mkdir()
            sync.write_new_json(self.locations['antigravity']/(identifier+'.json'),{'id':identifier,'name':identifier,
                'projectResources':{'resources':[{'folderUri':folder.as_uri()}]}})
        for mode in ['last_updated','last_user_prompt']:
            with self.subTest(mode=mode):
                self.locations['antigravity_state'].write_text(json.dumps({
                    'projectsOrder':json.dumps(['extra-a','extra-b','existing']), 'projectsFolderSortBy':mode}))
                with self.assertRaisesRegex(ValueError,'destination-only order'):
                    self.presentation_plan()
        self.assertEqual(self.state(),self.ui)
        self.assertFalse(self.locations['records'].exists())

    def test_activity_sort_allows_zero_or_one_destination_only_project(self):
        self.destination_fixture()
        self.locations['antigravity_state'].write_text(json.dumps({'projectsFolderSortBy':'last_updated'}))
        self.assertEqual(self.presentation_plan()['presentation']['order_extras'],[])
        folder=self.home/'extra';folder.mkdir()
        sync.write_new_json(self.locations['antigravity']/'extra.json',{'id':'extra','name':'Extra',
            'projectResources':{'resources':[{'folderUri':folder.as_uri()}]}})
        self.assertEqual(self.presentation_plan()['presentation']['order_extras'],['extra'])

    def test_sparse_patch_uses_loopback_transport_and_native_reset_strings(self):
        sync.write_new_json(self.locations['service'],{'url':'http://127.0.0.1:12345','password':'secret'})
        service=sync.OpenCodeService(self.locations['service'])
        self.assertTrue(callable(getattr(service,'patch',None)),"PATCH transport is not implemented")
        requests=[]
        def transport(handler,request):
            requests.append((request.method,request.host,json.loads(request.data)))
            response=io.BytesIO(b'{}');response.code,response.msg=200,'OK';response.info=lambda:{}
            return response
        with patch.object(urllib.request.HTTPHandler,'http_open',transport):
            service.patch('/api/project/example',{'name':'','icon':{'color':''}})
        self.assertEqual(requests,[('PATCH','127.0.0.1:12345',{'name':'','icon':{'color':''}})])

    def test_presentation_cli_is_opt_in_and_preview_is_read_only(self):
        self.destination_fixture()
        args=[sync.sys.executable,"-B",str(SOURCE),"--home",str(self.home)]
        plain=sync.subprocess.run(args,capture_output=True,text=True)
        self.assertEqual(plain.returncode,0,plain.stderr)
        self.assertNotIn("presentation",json.loads(plain.stdout))
        result=sync.subprocess.run(args+["--sync-presentation"],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        data=json.loads(result.stdout)
        self.assertEqual(data["format"],"project-sync/v2")
        self.assertIn("presentation",data)
        self.assertEqual(self.state(),self.ui)
        self.assertFalse(self.locations["records"].exists())


if __name__ == "__main__":
    unittest.main()
