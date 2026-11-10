"""Behavioral checks for Antigravity's isolated, recoverable configuration export."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parents[1]


class SetupTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="antigravity-setup-test-")
        self.root = Path(self.temp.name).resolve()
        self.repo = self.root / "relocated dotfiles"
        self.repo.mkdir()
        for name in ("antigravity", "setup-antigravity.sh", "setup_files.py"):
            source = SOURCE / name
            if source.is_dir():
                shutil.copytree(source, self.repo / name)
            elif source.exists():
                shutil.copy2(source, self.repo / name)
        (self.repo / "codex").mkdir()
        self.original = b"Preamble\n\n## 1. First\nKeep me.\n\n## 2. Last\nTail instruction.\n"
        (self.repo / "codex/AGENTS.md").write_bytes(self.original)
        shutil.copytree(SOURCE / "codex/agents", self.repo / "codex/agents")
        self.home = self.root / "home"
        self.home.mkdir()
        self.config = self.home / "pilot/.agents"
        self.state = self.home / "recovery"
        self.sources = self.root / "sources.json"
        self.sources.write_text(json.dumps({"skills": [], "role_tools": {
            "read": ["read_file"],
            "write": ["edit_file", "write_file", "run_command"]}}))

    def tearDown(self):
        self.temp.cleanup()

    def run_setup(self, *extra, success=True):
        result = subprocess.run(["sh", str(self.repo / "setup-antigravity.sh"),
            "--home", str(self.home), "--config-dir", str(self.config),
            "--state-dir", str(self.state), "--sources", str(self.sources), *extra],
            text=True, capture_output=True)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        if not success:
            self.assertIn("Antigravity setup stopped:", result.stderr)
        return json.loads(result.stdout) if result.returncode == 0 else result

    def load_module(self):
        spec = importlib.util.spec_from_file_location("antigravity_fixture", self.repo / "antigravity/setup.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_dry_run_and_lossless_relocated_install(self):
        self.run_setup("--dry-run")
        self.assertEqual(list(self.home.iterdir()), [])
        result = self.run_setup()
        manifest = json.loads(Path(result["manifest"]).read_text())
        bodies = []
        for rule in sorted(self.config.glob("rules/shared-instructions-*.md")):
            self.assertFalse(rule.is_symlink())
            self.assertEqual(rule.stat().st_nlink, 1)
            self.assertLess(len(rule.read_bytes()), 24000)
            bodies.append(rule.read_bytes().split(b"<!-- canonical-body -->\n", 1)[1])
        self.assertEqual(b"".join(bodies), self.original)
        self.assertEqual((self.repo / "codex/AGENTS.md").read_bytes(), self.original)
        self.assertEqual(self.run_setup()["created"], [])
        self.assertEqual(manifest["format"], "antigravity-setup/v1")
        self.assertFalse((self.config / "config.json").exists())
        self.assertFalse((self.config / "mcp_config.json").exists())

    def test_conflict_and_missing_skill_preflight_create_nothing(self):
        self.config.mkdir(parents=True)
        (self.config / "skills.json").write_text("user data")
        self.run_setup(success=False)
        self.assertEqual(list(self.config.iterdir()), [self.config / "skills.json"])
        self.assertFalse(self.state.exists())
        (self.config / "skills.json").unlink()
        self.sources.write_text(json.dumps({"skills": [str(self.root / "missing")]}))
        self.run_setup(success=False)
        self.assertEqual(list(self.config.iterdir()), [])

    def test_protected_and_symlinked_destinations_are_rejected(self):
        for forbidden in (self.home / ".codex", self.home / ".config/opencode", self.repo / "codex"):
            self.config = forbidden
            self.run_setup(success=False)
            self.assertFalse((forbidden / "skills.json").exists())
        real = self.home / "real"
        real.mkdir()
        link = self.home / "linked"
        link.symlink_to(real)
        self.config = link / "config"
        self.run_setup(success=False)
        self.assertEqual(list(real.iterdir()), [])

    def test_case_aliases_of_protected_roots_are_rejected(self):
        for target in (self.home / ".CODEX", self.home / ".CODEX/nested",
                       self.home / ".CONFIG/OPENCODE", self.repo / "CODEX"):
            self.config = target
            self.run_setup(success=False)
            self.assertFalse((target / "skills.json").exists())

    def test_oversized_section_is_rejected_before_writes(self):
        (self.repo / "codex/AGENTS.md").write_text("## 1. Large\n" + "x" * 24000)
        self.run_setup(success=False)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_duplicate_metadata_names_are_rejected(self):
        import hashlib
        paths = []
        for name in ("a", "b"):
            path = self.root / name
            path.mkdir()
            (path / "SKILL.md").write_text("---\nname: duplicate\ndescription: sample\n---\nText\n")
            paths.append(str(path))
        resources = {str(Path(p) / "SKILL.md"): hashlib.sha256((Path(p) / "SKILL.md").read_bytes()).hexdigest() for p in paths}
        self.sources.write_text(json.dumps({"skills": paths, "resources": resources}))
        result = self.run_setup(success=False)
        self.assertIn("Duplicate skill identity", result.stderr)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_unverified_write_capable_tool_cannot_enter_readonly_roles(self):
        data = json.loads(self.sources.read_text())
        data["role_tools"]["read"].append("run_command")
        self.sources.write_text(json.dumps(data))
        self.run_setup(success=False)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_missing_or_changed_bound_resource_blocks_all_publication(self):
        import hashlib
        package = self.root / "complete-package"
        skill = package / "skills/example"
        skill.mkdir(parents=True)
        entry = skill / "SKILL.md"
        entry.write_text("---\nname: example\ndescription: sample\n---\nRead ../../policy.md\n")
        policy = package / "policy.md"
        policy.write_text("Keep this required sibling resource.")
        data = json.loads(self.sources.read_text())
        data["skills"] = [str(skill)]
        data["resources"] = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (entry, policy)}
        self.sources.write_text(json.dumps(data))
        policy.unlink()
        self.run_setup(success=False)
        self.assertEqual(list(self.home.iterdir()), [])
        policy.write_text("A different unreviewed policy.")
        self.run_setup(success=False)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_skill_without_a_bound_resource_inventory_is_rejected(self):
        skill = self.root / "example"
        skill.mkdir()
        (skill / "SKILL.md").write_text("---\nname: example\ndescription: sample\n---\nText\n")
        data = json.loads(self.sources.read_text())
        data["skills"] = [str(skill)]
        self.sources.write_text(json.dumps(data))
        self.run_setup(success=False)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_role_and_adapter_hashes_bind_the_bytes_actually_rendered(self):
        import hashlib
        module = self.load_module()
        sources = json.loads(self.sources.read_text())
        targets = [self.repo / "codex/agents/bounded_explorer.toml",
                   self.repo / "antigravity/antigravity-compat.md"]
        read_text = Path.read_text
        before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in targets}

        def edit_after_read(path, *args, **kwargs):
            text = read_text(path, *args, **kwargs)
            if path in targets:
                path.write_text(text + "\n# Concurrent source edit\n")
            return text

        with patch.object(Path, "read_text", edit_after_read):
            _, inputs, _ = module.render(sources)
        for path, digest in before.items():
            self.assertEqual(inputs[path], digest, "Manifest hash described bytes other than the rendered source")

    def test_unqualified_roles_can_be_withheld_from_discovery(self):
        data = json.loads(self.sources.read_text())
        data["roles"] = []
        self.sources.write_text(json.dumps(data))
        self.run_setup()
        self.assertFalse((self.config / "agents").exists())
        self.assertTrue((self.config / "rules/shared-instructions-01.md").exists())

    def test_unknown_role_is_rejected_before_publication(self):
        data = json.loads(self.sources.read_text())
        data["roles"] = ["unreviewed_role"]
        self.sources.write_text(json.dumps(data))
        self.run_setup(success=False)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_modified_and_recreated_outputs_survive_rollback(self):
        result = self.run_setup()
        changed = self.config / "skills.json"
        changed.write_text("user data")
        identical = self.config / "agents/quality_reviewer.md"
        replacement = identical.with_suffix(".new")
        replacement.write_bytes(identical.read_bytes())
        replacement.replace(identical)
        rolled = self.run_setup("--rollback", result["manifest"])
        self.assertEqual(changed.read_text(), "user data")
        self.assertTrue(identical.exists())
        self.assertIn(str(changed), rolled["preserved"])
        self.assertIn(str(identical), rolled["preserved"])
        self.assertFalse((self.config / "rules/shared-instructions-01.md").exists())

    def test_rollback_rejects_forged_protected_target(self):
        result = self.run_setup()
        record = Path(result["manifest"])
        manifest = json.loads(record.read_text())
        manifest["created"][0]["path"] = str(self.home / ".codex/config.toml")
        record.write_text(json.dumps(manifest))
        self.run_setup("--rollback", str(record), success=False)
        self.assertTrue((self.config / "skills.json").exists())

    def test_partial_write_keeps_ownership_and_recovery(self):
        module = self.load_module()
        publish = module.os.link
        count = 0

        def fail_second(source, destination, **kwargs):
            nonlocal count
            count += 1
            if count == 2:
                raise OSError("fixture publication failure")
            return publish(source, destination, **kwargs)

        args = ["setup.py", "--home", str(self.home), "--config-dir", str(self.config),
                "--state-dir", str(self.state), "--sources", str(self.sources)]
        with patch("sys.argv", args), patch.object(module.os, "link", fail_second):
            with self.assertRaises(OSError):
                module.main()
        manifests = list(self.state.glob("setup-*/manifest.json"))
        self.assertEqual(len(manifests), 1)
        manifest = json.loads(manifests[0].read_text())
        self.assertEqual(manifest["status"], "prepared")
        self.assertTrue(manifest["created"])
        self.run_setup("--rollback", str(manifests[0]))
        self.assertFalse((self.config / "skills.json").exists())


if __name__ == "__main__":
    unittest.main()
