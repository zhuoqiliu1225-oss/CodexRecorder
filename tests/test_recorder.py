import json
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'app'))
from server import Recorder
import ai

TEST_TEMP = Path(__file__).resolve().parents[1]/'data'/'test-tmp'
TEST_TEMP.mkdir(parents=True, exist_ok=True)


class RecorderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=TEST_TEMP)
        self.app = Recorder(Path(self.temp.name))
        self.app.engine = {'status':'ready','error':''}
        self.session = self.app.start({'source':'en','target':'zh','client':'test'})

    def tearDown(self):
        if self.app.writer:
            self.app.writer.close()
        self.app.session = None
        self.temp.cleanup()

    def test_duplicate_upload_is_idempotent_and_wav_is_valid(self):
        pcm = b'\x01\x00'*16000
        sid = self.session['id']
        self.app.ingest(sid,0,pcm)
        self.app.ingest(sid,0,pcm)
        self.assertEqual(self.session['samples'],16000)
        self.assertEqual(self.session['pendingAsr'],1)
        self.app.writer.close()
        self.app.writer = None
        with wave.open(str(self.app.data/sid/'audio.wav')) as reader:
            self.assertEqual(reader.getnframes(),16000)
            self.assertEqual(reader.getframerate(),16000)
            self.assertEqual(reader.readframes(16000),pcm)

    def test_out_of_order_audio_is_rejected_before_writing(self):
        with self.assertRaises(ValueError):
            self.app.ingest(self.session['id'],2,b'\0\0'*10)
        self.assertEqual(self.session['samples'],0)
        with self.assertRaises(ValueError):
            self.app.ingest(self.session['id'],0,b'\0')

    def test_failed_chunk_save_does_not_advance_audio_or_pending_jobs(self):
        with patch.object(Path,'write_bytes',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                self.app.ingest(self.session['id'],0,b'\0\0'*100)
        self.assertEqual(self.session['samples'],0)
        self.assertEqual(self.session['nextSeq'],0)
        self.assertEqual(self.session['pendingAsr'],0)
        self.assertTrue(self.app.asr_queue.empty())

    def test_cannot_replace_an_active_session(self):
        with self.assertRaises(ValueError):
            self.app.start({})

    def test_finish_keeps_audio_and_blocks_further_uploads(self):
        self.app.ingest(self.session['id'],0,b'\0\0'*100)
        self.app.finish(self.session['id'])
        self.assertEqual(self.session['status'],'processing')
        self.assertIsNone(self.app.writer)
        with self.assertRaises(ValueError):
            self.app.ingest(self.session['id'],1,b'\0\0'*100)
        # Let the finalizer exit cleanly.
        self.session['pendingAsr']=0

    def test_export_preserves_original_and_translation(self):
        self.session['segments']=[{'start':65,'text':'Original <script>', 'translation':'译文','target':'zh'}]
        self.session['summary']='摘要'
        self.app.save()
        notes=(self.app.data/self.session['id']/'notes.md').read_text(encoding='utf-8')
        self.assertIn('[01:05] Original <script>',notes)
        self.assertIn('译文',notes)
        self.assertIn('摘要',notes)

    def test_restart_recovers_interrupted_session_without_claiming_completion(self):
        self.app.ingest(self.session['id'],0,b'\0\0'*320)
        self.app.writer.close()
        self.app.writer=None
        restored=Recorder(Path(self.temp.name))
        self.assertEqual(restored.session['id'],self.session['id'])
        self.assertEqual(restored.session['samples'],320)
        self.assertEqual(restored.session['status'],'complete')
        self.assertEqual(restored.session['summaryStatus'],'error')
        self.assertTrue(restored.session['errors'])
        self.assertEqual(restored.session['pendingAsr'],0)
        self.assertIsNone(restored.writer)

    def add_source_rows(self):
        self.session['segments']=[{'id':'0-0','start':0,'text':'Hello','language':'en','target':'zh','translation':'','translationStatus':'off'},
                                  {'id':'0-1','start':1,'text':'你好','language':'zh','target':'zh','translation':'','translationStatus':'off'}]

    @patch('ai.translate_many')
    def test_language_change_retranslates_history_and_reuses_cached_language(self, translate):
        self.add_source_rows()
        self.app.update_settings(True,'ja')
        revision=self.session['translationRevision']
        translate.return_value={'0-0':'こんにちは','0-1':'こんにちは'}
        with patch.object(self.app,'local_translation',return_value=None):
            self.app.translate_rows(self.session['id'],['0-0','0-1'],'ja',revision)
        self.assertTrue(all(r['translationStatus']=='done' for r in self.session['segments']))
        self.app.update_settings(True,'en')
        self.assertEqual(self.session['segments'][0]['translation'],'Hello')
        self.app.update_settings(True,'ja')
        self.assertTrue(all(r['translation']=='こんにちは' for r in self.session['segments']))
        self.assertEqual(translate.call_count,1)

    @patch('ai.translate_many')
    def test_old_language_in_flight_cannot_overwrite_new_language(self, translate):
        self.add_source_rows()
        self.app.update_settings(True,'ja')
        revision=self.session['translationRevision']
        def switch_then_return(*args):
            self.app.update_settings(True,'de')
            return {'0-0':'obsolete','0-1':'obsolete'}
        translate.side_effect=switch_then_return
        with patch.object(self.app,'local_translation',return_value=None):
            self.app.translate_rows(self.session['id'],['0-0','0-1'],'ja',revision)
        self.assertTrue(all(r['target']=='de' and r['translation']=='' for r in self.session['segments']))

    @patch('ai.translate_many')
    def test_disabling_translation_skips_stale_queue(self, translate):
        self.add_source_rows()
        self.app.update_settings(True,'ja')
        revision=self.session['translationRevision']
        self.app.update_settings(False,'ja')
        self.app.translate_rows(self.session['id'],['0-0'],'ja',revision)
        translate.assert_not_called()
        self.assertTrue(all(r['translationStatus']=='off' for r in self.session['segments']))

    def test_future_asr_rows_use_latest_language(self):
        self.app.update_settings(True,'de')
        rows=[{'id':'1-0','text':'Next sentence','language':'en','target':'','translation':'','translationStatus':'off'}]
        self.session['segments'].extend(rows)
        self.app.schedule_translation(rows)
        self.assertEqual(rows[0]['target'],'de')
        self.assertEqual(rows[0]['translationRevision'],self.session['translationRevision'])

    def test_enabling_translation_backfills_history_even_with_same_target(self):
        self.add_source_rows()
        self.app.update_settings(True,'zh')
        self.assertEqual(self.session['segments'][0]['translationStatus'],'pending')
        self.assertEqual(self.session['segments'][1]['translation'],'你好')

    def test_stopping_seals_draft_and_schedules_its_translation(self):
        self.session['translation']=True
        self.session['segments']=[{'id':'last','utterance':'u0','start':0,'text':'Last words','language':'en',
            'target':'','translation':'','translationStatus':'off','provisional':True}]
        self.app.asr_window={'sid':self.session['id'],'id':'u0','pcm':b''}
        self.app.schedule_translation(self.session['segments'])
        self.assertEqual(self.session['segments'][0]['translationStatus'],'waiting')
        self.app.seal_window(self.session['id'])
        self.assertFalse(self.session['segments'][0]['provisional'])
        self.assertEqual(self.session['segments'][0]['translationStatus'],'pending')
        self.assertEqual(self.session['pendingText'],1)

    def test_slow_summary_does_not_block_history_translation(self):
        self.add_source_rows()
        self.session['status']='processing'
        entered=threading.Event()
        release=threading.Event()
        def slow_summary(*_):
            entered.set()
            release.wait(3)
            return 'Synthetic summary'
        with patch('ai.summarize',side_effect=slow_summary), patch.object(self.app,'local_translation',return_value='こんにちは'):
            threading.Thread(target=self.app.summary_worker,daemon=True).start()
            threading.Thread(target=self.app.text_worker,daemon=True).start()
            self.app.summary_queue.put(self.session['id'])
            self.assertTrue(entered.wait(2))
            self.app.update_settings(True,'ja')
            deadline=time.monotonic()+2
            while self.session['pendingText'] and time.monotonic()<deadline:
                time.sleep(.01)
            try:
                self.assertEqual(self.session['pendingText'],0)
                self.assertTrue(all(r['translation']=='こんにちは' for r in self.session['segments']))
                self.assertFalse(release.is_set())
            finally:
                release.set()
                self.app.summary_queue.join()


class CodexAdapterTests(unittest.TestCase):
    @patch('ai.run_codex',return_value='{"translations":[{"id":"a","text":"Hola"}]}')
    def test_batch_translation_rejects_missing_rows(self, _):
        with self.assertRaises(RuntimeError):
            ai.translate_many([{'id':'a','text':'Hello'},{'id':'b','text':'Bye'}],'Spanish',{},TEST_TEMP)

    @patch('ai.shutil.which',return_value='codex.exe')
    @patch('ai.subprocess.Popen')
    def test_language_change_cancels_running_cli(self, popen, _):
        process=popen.return_value
        process.poll.return_value=None
        process.communicate.side_effect=[subprocess.TimeoutExpired('codex',.2),('','')]
        checks=iter([False,False,True])
        with self.assertRaises(ai.Cancelled):
            ai.run_codex('synthetic text',{},TEST_TEMP,cancelled=lambda:next(checks))
        process.kill.assert_called_once()
    @patch('ai.shutil.which',return_value='codex.exe')
    @patch('ai.subprocess.run')
    def test_failure_is_not_reported_as_a_translation(self, run, _):
        run.return_value.returncode=1
        run.return_value.stdout=json.dumps({'type':'turn.failed','error':{'message':'limit reached'}})
        with tempfile.TemporaryDirectory(dir=TEST_TEMP) as folder:
            with self.assertRaises(RuntimeError):
                ai.run_codex('source',{},Path(folder))

    @patch('ai.shutil.which',return_value='codex.exe')
    @patch('ai.subprocess.run')
    def test_only_final_agent_message_is_returned_and_no_key_is_forwarded(self, run, _):
        run.return_value.returncode=0
        run.return_value.stdout='\n'.join(json.dumps(e) for e in [
            {'type':'item.completed','item':{'type':'reasoning','text':'internal'}},
            {'type':'item.completed','item':{'type':'agent_message','text':'translation'}}])
        with patch.dict('os.environ',{'OPENAI_API_KEY':'test-not-real','CODEX_API_KEY':'test-not-real'}):
            with tempfile.TemporaryDirectory(dir=TEST_TEMP) as folder:
                self.assertEqual(ai.run_codex('source',{},Path(folder)),'translation')
        self.assertNotIn('OPENAI_API_KEY',run.call_args.kwargs['env'])
        self.assertNotIn('CODEX_API_KEY',run.call_args.kwargs['env'])


if __name__=='__main__':
    unittest.main()
