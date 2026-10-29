import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
import records
spec=importlib.util.spec_from_file_location('skill_setup',Path(__file__).resolve().parents[1]/'scripts/install_skill.py')
installer=importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)

class PlatformTests(unittest.TestCase):
    def test_mac_folder_path_is_one_argument(self):
        with patch.object(records.sys,'platform','darwin'),patch.object(records.subprocess,'Popen') as launch:
            records.open_folder(Path('/Users/example/Folder with spaces'))
            self.assertEqual(launch.call_args.args[0],['open',str(Path('/Users/example/Folder with spaces'))])

    def test_personal_skill_install_and_unrelated_folder_protection(self):
        scratch=Path(__file__).resolve().parents[1]/'data'
        scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as tmp:
            dest=Path(tmp)/'codex-recorder'
            installer.install(dest)
            installer.install(dest)
            self.assertIn('name: codex-recorder',(dest/'SKILL.md').read_text(encoding='utf-8'))
            self.assertIn('projectRoot',(dest/'installation.json').read_text(encoding='utf-8'))
            other=Path(tmp)/'unrelated';other.mkdir()
            (other/'SKILL.md').write_text('user skill',encoding='utf-8')
            with self.assertRaises(ValueError):installer.install(other)
            self.assertEqual((other/'SKILL.md').read_text(encoding='utf-8'),'user skill')
