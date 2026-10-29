import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
import records
import ai

class RecordTests(unittest.TestCase):
    def test_rejects_path_traversal(self):
        for sid in ('../x','',r'..\x','中文','a/b'):
            with self.assertRaises(ValueError):records.read_record('.',sid)

    def test_atomic_write_retries_windows_lock(self):
        root=Path(__file__).resolve().parents[1]/'data'
        root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as tmp:
            target=Path(tmp)/'notes.md'
            original=Path.replace
            calls=[]
            def replace(src,dest):
                calls.append(1)
                if len(calls)<3:raise PermissionError('locked')
                return original(src,dest)
            with patch.object(Path,'replace',replace),patch.object(records.time,'sleep'):
                records.atomic_text(target,'完整内容')
            self.assertEqual(target.read_text(encoding='utf-8'),'完整内容')
            self.assertEqual(len(calls),3)
            self.assertFalse(list(Path(tmp).glob('*.tmp')))

    def test_summary_retries_transient_failure(self):
        with patch.object(ai,'summarize',side_effect=[TimeoutError(), '# Recovered']),patch.object(ai.time,'sleep'):
            self.assertEqual(ai.summarize_reliably([],{},Path('.')),'# Recovered')

    def test_summary_does_not_retry_auth_failure(self):
        with patch.object(ai,'summarize',side_effect=RuntimeError('401')) as call:
            with self.assertRaises(RuntimeError):ai.summarize_reliably([],{},Path('.'))
            self.assertEqual(call.call_count,1)
