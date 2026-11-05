"""Exercise setup ownership, conflict handling, relocation, and rollback."""
import json
import importlib.util
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
        self.temp = tempfile.TemporaryDirectory(prefix="opencode-setup-test-")
        self.root = Path(self.temp.name).resolve()
        self.repo = self.root / "relocated dotfiles"
        self.repo.mkdir()
        for name in ("opencode", "setup-opencode.sh"):
            source = SOURCE / name
            if source.is_dir():
                shutil.copytree(source, self.repo / name)
            elif source.exists():
                shutil.copy2(source, self.repo / name)
        (self.repo / "codex").mkdir()
        (self.repo / "codex/AGENTS.md").write_text("Shared instructions\n")
        shutil.copytree(SOURCE / "codex/agents", self.repo / "codex/agents")
        self.home = self.root / "home"
        self.home.mkdir()
        self.config = self.home / ".config/opencode"
        self.sources = self.root / "sources.json"
        self.sources.write_text(json.dumps({"skills": [], "protected_paths": [],
            "model": "openai/test-model", "context7": {"type": "remote",
            "url": "https://mcp.context7.com/mcp", "codemode": False}}))
        self.env = {k: v for k, v in os.environ.items() if k not in
                    ("XDG_CONFIG_HOME", "XDG_STATE_HOME", "OPENCODE_CONFIG", "OPENCODE_CONFIG_DIR")}

    def tearDown(self):
        self.temp.cleanup()

    def run_setup(self, *args, success=True):
        result = subprocess.run(["sh", str(self.repo / "setup-opencode.sh"),
            "--home", str(self.home), "--sources", str(self.sources), *args],
            env=self.env, text=True, capture_output=True)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        return result

    def manifest(self, result):
        return Path(json.loads(result.stdout)["manifest"])

    def test_dry_run_creates_nothing(self):
        self.run_setup("--dry-run")
        self.assertEqual(list(self.home.iterdir()), [])

    def test_relocated_source_and_rerun_preserve_user_configuration(self):
        first = self.run_setup()
        self.assertEqual((self.config / "AGENTS.md").resolve(), self.repo / "codex/AGENTS.md")
        config = self.config / "opencode.jsonc"
        config.write_text('{"user_owned": true}\n')
        before = config.stat().st_ino
        second = self.run_setup()
        self.assertEqual(config.read_text(), '{"user_owned": true}\n')
        self.assertEqual(config.stat().st_ino, before)
        self.assertEqual(json.loads(second.stdout)["created"], [])
        self.assertTrue(self.manifest(first).is_file())

    def test_broken_link_conflict_prevents_partial_install(self):
        self.config.mkdir(parents=True)
        (self.config / "opencode-compat.md").symlink_to(self.root / "missing")
        self.run_setup(success=False)
        self.assertFalse((self.config / "AGENTS.md").exists())
        self.assertFalse((self.config / "opencode.jsonc").exists())
        self.assertTrue((self.config / "opencode-compat.md").is_symlink())

    def test_missing_skill_prevents_partial_install(self):
        data = json.loads(self.sources.read_text())
        data["skills"] = [str(self.root / "missing-skill")]
        self.sources.write_text(json.dumps(data))
        self.run_setup(success=False)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_rollback_removes_only_unchanged_setup_owned_files(self):
        first = self.run_setup()
        config = self.config / "opencode.jsonc"
        config.write_text('{"changed": true}\n')
        extra = self.config / "personal.txt"
        extra.write_text("keep\n")
        rollback = self.run_setup("--rollback", str(self.manifest(first)))
        self.assertEqual(config.read_text(), '{"changed": true}\n')
        self.assertEqual(extra.read_text(), "keep\n")
        self.assertFalse((self.config / "AGENTS.md").is_symlink())
        self.assertIn(str(config), json.loads(rollback.stdout)["preserved"])

    def test_recreated_identical_file_is_not_rollback_owned(self):
        first = self.run_setup()
        config = self.config / "opencode.jsonc"
        replacement = self.config / "replacement"
        replacement.write_bytes(config.read_bytes())
        replacement.replace(config)
        self.run_setup("--rollback", str(self.manifest(first)))
        self.assertTrue(config.is_file())

    def test_symlinked_config_root_is_not_written_through(self):
        elsewhere = self.root / "elsewhere"
        elsewhere.mkdir()
        self.config.parent.mkdir()
        self.config.symlink_to(elsewhere, target_is_directory=True)
        self.run_setup(success=False)
        self.assertEqual(list(elsewhere.iterdir()), [])

    def test_app_replacement_during_creation_never_becomes_rollback_owned(self):
        spec = importlib.util.spec_from_file_location("setup_fixture", self.repo / "opencode/setup.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        create_file = module.write_new

        def app_replaces_created_config(path, text):
            result = create_file(path, text)
            if path.name == "opencode.jsonc":
                replacement = path.parent / "app-update"
                replacement.write_text('{"app_owned": true}\n')
                replacement.replace(path)
            return result

        arguments = ["setup.py", "--home", str(self.home), "--sources", str(self.sources)]
        with patch.object(module, "write_new", app_replaces_created_config), patch("sys.argv", arguments), patch.dict(os.environ, self.env, clear=True):
            installed = module.main()
        result = module.rollback(Path(installed["manifest"]), False)
        config = self.config / "opencode.jsonc"
        self.assertTrue(config.exists(), "Rollback removed an app replacement created during installation")
        self.assertEqual(config.read_text(), '{"app_owned": true}\n')
        self.assertIn(str(config), result["preserved"])


if __name__ == "__main__":
    unittest.main()
