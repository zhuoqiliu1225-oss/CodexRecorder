import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
import ai


class CodexDiscoveryTests(unittest.TestCase):
    def test_configured_cli_preferred(self):
        with patch.object(ai.shutil,'which',return_value='configured.exe'):
            self.assertEqual(ai.resolve_codex({'codex':'preferred'}),'configured.exe')

    def test_stale_configuration_falls_back_to_path(self):
        with patch.object(ai.shutil,'which',side_effect=[None,'current.exe']):
            self.assertEqual(ai.resolve_codex({'codex':'deleted.exe'}),'current.exe')

    def test_desktop_update_with_stale_path(self):
        scratch=Path(__file__).resolve().parents[1]/'data'
        scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as folder:
            root=Path(folder)/'OpenAI'/'Codex'/'bin'
            for name,stamp in [('old',100),('new',200)]:
                exe=root/name/'codex.exe'
                exe.parent.mkdir(parents=True)
                exe.write_bytes(b'fixture')
                os.utime(exe,(stamp,stamp))
            with patch.dict(os.environ,{'LOCALAPPDATA':folder}),patch.object(ai.shutil,'which',return_value=None):
                self.assertEqual(Path(ai.resolve_codex({'codex':'deleted.exe'})),root/'new'/'codex.exe')

    def test_missing_cli_reports_installation_not_login(self):
        with patch.dict(os.environ,{'LOCALAPPDATA':''}),patch.object(ai.shutil,'which',return_value=None):
            with self.assertRaisesRegex(RuntimeError,'安装'):
                ai.resolve_codex({})
