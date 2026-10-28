"""Local recorder service. Audio capture stays in the Codex browser panel."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import json
import argparse
import os
import queue
import secrets
import threading
import time
import uuid
import wave
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ai

LANGUAGES = {'zh': '简体中文', 'en': 'English', 'ja': '日本語', 'ko': '한국어',
             'fr': 'Français', 'de': 'Deutsch', 'es': 'Español'}


class Recorder:
    def __init__(self, root=ROOT, settings=None):
        self.root = Path(root)
        self.settings = settings or {}
        self.data = self.root / self.settings.get('data_dir','data')
        self.data.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.token = secrets.token_urlsafe(32)
        self.session = None
        self.writer = None
        self.asr_queue = queue.Queue()
        self.text_queue = queue.LifoQueue()
        self.summary_queue = queue.Queue()
        self.model = None
        self.engine = {'status': 'loading', 'error': ''}
        self.last_seen = 0
        self.last_panel_seen = 0
        self.client = None
        self.start_requested = False
        self.asr_window = None
        self.restore_latest()

    def restore_latest(self):
        candidates = sorted(self.data.glob('*/session.json'), key=lambda p:p.stat().st_mtime, reverse=True)
        for path in candidates:
            try:
                s = json.loads(path.read_text(encoding='utf-8'))
                if s.get('id') != path.parent.name or not isinstance(s.get('segments'), list):
                    continue
                interrupted = s.get('status') in ('recording','paused','processing') or s.get('pendingAsr',0)>0 or s.get('pendingText',0)>0
                if interrupted:
                    s['status'] = 'complete'
                    s['desired'] = 'stopped'
                    s['pendingAsr'] = s['pendingText'] = 0
                    s['summaryStatus'] = 'done' if s.get('summary') else 'error'
                    s['errors'].append('服务曾中断，已恢复保存的录音记录。部分音频可能尚未转写，请保留原始录音。')
                    for row in s['segments']:
                        if row.get('translationStatus')=='pending':
                            row['translationStatus']='error'
                self.session = s
                s.setdefault('translationRevision',0)
                s.setdefault('metrics',{})
                for row in s['segments']:
                    row.setdefault('translations',{})
                    if row.get('translation') and row.get('translationStatus')=='done':
                        row['translations'][row['target']]=row['translation']
                if interrupted:
                    self.save()
                return
            except (ValueError, OSError, KeyError, TypeError):
                continue

    def launch(self):
        threading.Thread(target=self.asr_worker, daemon=True).start()
        threading.Thread(target=self.text_worker, daemon=True).start()
        threading.Thread(target=self.summary_worker, daemon=True).start()
        threading.Thread(target=self.watchdog, daemon=True).start()

    def snapshot(self):
        with self.lock:
            return json.loads(json.dumps({'engine': self.engine, 'session': self.session,
                'languages': LANGUAGES, 'startRequested': self.start_requested,
                'clientConnected': time.time()-self.last_panel_seen < 5,
                'serviceId': self.token[:12]}, ensure_ascii=False))

    def save(self):
        if not self.session:
            return
        dest = self.data / self.session['id']
        dest.mkdir(exist_ok=True)
        temp = dest / 'session.tmp'
        temp.write_text(json.dumps(self.session, ensure_ascii=False, indent=2), encoding='utf-8')
        temp.replace(dest / 'session.json')
        lines = ['# '+self.session['title'], '']
        for s in self.session['segments']:
            lines += [f"[{int(s['start']//60):02}:{int(s['start']%60):02}] {s['text']}", '']
            if s.get('translation'):
                lines += [f"{LANGUAGES.get(s.get('target'), '')}：{s['translation']}", '']
        if self.session.get('summary'):
            lines += ['---', '', self.session['summary']]
        temp = dest / 'notes.tmp'
        temp.write_text('\n'.join(lines), encoding='utf-8')
        temp.replace(dest / 'notes.md')

    def start(self, body):
        with self.lock:
            if self.engine['status'] != 'ready':
                raise ValueError('语音模型尚未就绪。')
            if self.session and (self.session['status'] not in ('complete', 'error') or self.session.get('pendingText',0)):
                raise ValueError('当前录音尚未结束。')
            source = body.get('source', 'auto')
            target = body.get('target', 'zh')
            if source not in ('auto', *LANGUAGES) or target not in LANGUAGES:
                raise ValueError('不支持的语言。')
            sid = time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8]
            stamp=time.localtime()
            title=f'录音 {stamp.tm_mon:02d}月{stamp.tm_mday:02d}日 {stamp.tm_hour:02d}:{stamp.tm_min:02d}'
            self.session = {'id': sid, 'title': title,
                'status': 'recording', 'desired': 'recording', 'source': source,
                'target': target, 'translation': bool(body.get('translation', False)),
                'samples': 0, 'nextSeq': 0, 'pendingAsr': 0, 'pendingText': 0,
                'segments': [], 'errors': [], 'summary': '', 'summaryStatus': 'idle',
                'createdAt': time.time(), 'translationRevision':0, 'metrics':{}}
            dest = self.data / sid
            dest.mkdir()
            self.writer = wave.open(str(dest / 'audio.wav'), 'wb')
            self.writer.setnchannels(1)
            self.writer.setsampwidth(2)
            self.writer.setframerate(16000)
            self.client = body.get('client')
            self.last_seen = time.time()
            self.start_requested = False
            self.asr_window = None
            self.save()
            return self.session

    def ingest(self, sid, seq, pcm, captured_at=None):
        with self.lock:
            s = self.session
            if not s or s['id'] != sid or s['status'] not in ('recording', 'paused'):
                raise ValueError('录音会话已结束。')
            if seq < s['nextSeq']:
                return  # A retried upload must not duplicate audio.
            if seq != s['nextSeq'] or not pcm or len(pcm)%2 or len(pcm)>512000:
                raise ValueError('音频片段序号或格式错误。')
            chunk_dir = self.data / sid / 'chunks'
            chunk_dir.mkdir(exist_ok=True)
            chunk_file = chunk_dir / f'{seq:08}.pcm'
            chunk_file.write_bytes(pcm)
            self.writer.writeframes(pcm)
            self.writer._file.flush()
            start = s['samples']/16000
            s['samples'] += len(pcm)//2
            s['nextSeq'] += 1
            s['pendingAsr'] += 1
            now=time.time()
            self.asr_queue.put((sid, seq, start, chunk_file, s['source'], now, captured_at or now))
            self.save()

    def schedule_translation(self, rows):
        s=self.session
        target=s['target']
        revision=s.get('translationRevision',0)
        pending=[]
        for row in rows:
            cache=row.setdefault('translations',{})
            if row.get('translation') and row.get('translationStatus')=='done':
                cache[row['target']]=row['translation']
            row['target']=target
            row['translationRevision']=revision
            if not s['translation']:
                row['translation']=''
                row['translationStatus']='off'
            elif row.get('language')==target:
                row['translation']=row['text']
                row['translationStatus']='done'
            elif target in cache:
                row['translation']=cache[target]
                row['translationStatus']='done'
            elif row.get('provisional') and not (hasattr(self,'_multilingual') or (self.settings.get('translation_model') and row.get('language')=='en' and target=='zh')):
                row['translation']=''
                row['translationStatus']='waiting'
            else:
                row['translation']=''
                row['translationStatus']='pending'
                pending.append(row['id'])
        # A batch covers multiple historical rows instead of launching Codex per sentence.
        for offset in range(0,len(pending),12):
            s['pendingText']+=1
            self.text_queue.put(('translate',s['id'],pending[offset:offset+12],target,revision))

    def update_settings(self, enabled, target):
        with self.lock:
            if not self.session or target not in LANGUAGES:
                raise ValueError('录音或目标语言无效。')
            s=self.session
            if s['translation']==bool(enabled) and s['target']==target:
                # Selecting the same target can retry failed rows without invalidating successful cache.
                rows=[r for r in s['segments'] if r.get('translationStatus') in ('error','off') or r.get('target')!=target]
                self.schedule_translation(rows)
            else:
                s['translationRevision']=s.get('translationRevision',0)+1
                s['translation']=bool(enabled)
                s['target']=target
                self.schedule_translation(s['segments'])
            self.save()

    def translation_current(self, sid, target, revision):
        with self.lock:
            s=self.session
            return bool(s and s['id']==sid and s['translation'] and s['target']==target and s.get('translationRevision',0)==revision)

    def translate_rows(self, sid, ids, target, revision):
        if not self.translation_current(sid,target,revision):
            return
        with self.lock:
            rows=[r for r in self.session['segments'] if r['id'] in set(ids) and r.get('translationRevision')==revision and r.get('translationStatus')=='pending']
        def cancelled():
            if not self.translation_current(sid,target,revision):
                return True
            with self.lock:
                return not any(r['id'] in ids for r in self.session['segments'])
        values={}
        cloud=[]
        started=time.perf_counter()
        for row in rows:
            if cancelled():
                return
            value=self.local_translation(row['text'],row.get('language'),target)
            if value is None:
                cloud.append(row)
            else:
                values[row['id']]=value
        if cloud:
            values.update(ai.translate_many(cloud,LANGUAGES[target],self.settings,self.data/'ai-runtime',cancelled))
        with self.lock:
            if cancelled():
                return
            for row in rows:
                if row['id'] in values and any(r is row for r in self.session['segments']):
                    row['translation']=values[row['id']]
                    row.setdefault('translations',{})[target]=values[row['id']]
                    row['translationStatus']='done'
            self.session.setdefault('metrics',{})['translationSeconds']=round(time.perf_counter()-started,3)
            self.save()

    def seal_window(self, sid):
        with self.lock:
            window=self.asr_window
            if not window or window['sid']!=sid or not self.session or self.session['id']!=sid:
                return
            rows=[r for r in self.session['segments'] if r.get('utterance')==window['id']]
            for row in rows:
                row['provisional']=False
            self.schedule_translation([r for r in rows if r.get('translationStatus')=='waiting'])
            self.asr_window=None

    def finish(self, sid):
        with self.lock:
            s = self.session
            if not s or s['id'] != sid:
                raise ValueError('录音会话不存在。')
            if s['status'] in ('processing', 'complete', 'error'):
                return
            s['status'] = 'processing'
            s['desired'] = 'stopped'
            s['pendingAsr']+=1
            self.asr_queue.put(('seal',sid))
            if self.writer:
                self.writer.close()
                self.writer = None
            self.save()
        threading.Thread(target=self.finalize, args=(sid,), daemon=True).start()

    def finalize(self, sid):
        while True:
            with self.lock:
                s = self.session
                if not s or s['id'] != sid:
                    return
                if not s['pendingAsr'] and not s['pendingText']:
                    s['summaryStatus'] = 'running'
                    self.save()
                    self.summary_queue.put(sid)
                    return
            time.sleep(.25)

    def asr_worker(self):
        try:
            import numpy as np
            import ctranslate2
            from faster_whisper import WhisperModel
            self._dll_handles=[]
            for directory in self.settings.get('cuda_library_dirs',[]):
                if os.name=='nt':
                    self._dll_handles.append(os.add_dll_directory(directory))
                os.environ['PATH']=directory+os.pathsep+os.environ.get('PATH','')
            device=self.settings.get('device','auto')
            if device=='auto':
                device='cuda' if ctranslate2.get_cuda_device_count() else 'cpu'
            def load(device):
                model=WhisperModel(self.settings.get('model','base'),device=device,
                    compute_type='float16' if device=='cuda' else 'int8',cpu_threads=4,
                    download_root=str(self.root/'models'))
                # Warm GPU kernels before advertising ready, so the first spoken sentence is not the warm-up.
                if device=='cuda':
                    segments,_=model.transcribe(np.zeros(16000,dtype=np.float32),language='en',beam_size=1,vad_filter=False)
                    list(segments)
                return model
            warning=''
            try:
                self.model=load(device)
            except Exception:
                if device!='cuda':
                    raise
                device='cpu'
                warning='GPU 初始化失败，已回退到 CPU。'
                self.model=load(device)
            translation_mode='gpt'
            if self.settings.get('multilingual_model'):
                try:
                    from local_translation import MultilingualTranslator
                    path=self.root/self.settings['multilingual_model']
                    self._multilingual=MultilingualTranslator(path,device)
                    self._multilingual.translate('Hello.','en','zh')
                    translation_mode='local'
                except Exception:
                    self.multilingual_failed=True
                    warning+=' 本地多语种翻译未就绪，使用现有翻译适配器或 GPT。'
            with self.lock:
                self.engine = {'status': 'ready', 'error': '', 'device':device,'warning':warning,'translationMode':translation_mode}
        except Exception as exc:
            with self.lock:
                self.engine = {'status': 'error', 'error': str(exc)[:300]}
            return
        while True:
            job=self.asr_queue.get()
            if job[0]=='seal':
                with self.lock:
                    self.seal_window(job[1])
                    self.session['pendingAsr']-=1
                    self.save()
                self.asr_queue.task_done()
                continue
            sid, seq, start, chunk_file, source, queued_at, captured_at = job
            try:
                infer_started=time.perf_counter()
                queue_wait=max(0,time.time()-queued_at)
                pcm = chunk_file.read_bytes()
                if self.asr_window and (self.asr_window['sid']!=sid or len(self.asr_window['pcm'])+len(pcm)>384000):
                    self.seal_window(self.asr_window['sid'])
                if self.asr_window is None:
                    self.asr_window={'sid':sid,'id':f'u{seq}','start':start,'pcm':b''}
                window=self.asr_window
                window['pcm']+=pcm
                audio = np.frombuffer(window['pcm'], dtype='<i2').astype(np.float32)/32768
                duration=len(audio)/16000
                if float(np.sqrt(np.mean(audio*audio))) > .002:
                    segments, info = self.model.transcribe(audio, language=None if source=='auto' else source,
                        beam_size=1, vad_filter=True, condition_on_previous_text=False,
                        vad_parameters={'min_silence_duration_ms': 350})
                    rows = [{'id': f'{seq}-{i}', 'start': round(window['start']+seg.start, 2),
                        'end': round(window['start']+seg.end, 2), 'text': seg.text.strip(),
                        'language': info.language, 'target': '', 'translation': '',
                        'translationStatus': 'off', 'translations':{},'utterance':window['id'],
                        'provisional':seg.end>duration-.35}
                        for i, seg in enumerate(segments) if seg.text.strip()]
                else:
                    rows = []
                with self.lock:
                    s = self.session
                    if s and s['id'] == sid:
                        previous=[r for r in s['segments'] if r.get('utterance')==window['id']]
                        unused=list(previous)
                        published=[]
                        schedule=[]
                        for row in rows:
                            match=next((old for old in unused if old['text']==row['text']),None)
                            if match:
                                unused.remove(match)
                                match.update({k:row[k] for k in ('start','end','provisional')})
                                published.append(match)
                                if match.get('translationStatus')=='waiting' and not match['provisional']:
                                    schedule.append(match)
                            else:
                                published.append(row)
                                schedule.append(row)
                        s['segments']=[r for r in s['segments'] if r.get('utterance')!=window['id']]+published
                        self.schedule_translation(schedule)
                        s.setdefault('metrics',{}).update({'asrSeconds':round(time.perf_counter()-infer_started,3),
                            'queueSeconds':round(queue_wait,3),'afterCaptureSeconds':round(max(0,time.time()-captured_at),3)})
            except Exception as exc:
                with self.lock:
                    self.session['errors'].append('转写失败：'+str(exc)[:200])
            finally:
                with self.lock:
                    self.session['pendingAsr'] -= 1
                    self.save()
                self.asr_queue.task_done()

    def local_translation(self, text, source, target):
        if hasattr(self,'_multilingual'):
            return self._multilingual.translate(text,source,target)
        model_path = self.settings.get('translation_model')
        if not model_path or source != 'en' or target != 'zh':
            return None
        if not hasattr(self, '_translator'):
            import ctranslate2
            import sentencepiece
            p = Path(model_path)
            self._tokenizer = sentencepiece.SentencePieceProcessor(model_proto=(p/'sentencepiece.model').read_bytes())
            self._translator = ctranslate2.Translator(str(p/'model'), device='cpu', compute_type='int8', intra_threads=2)
        tokens = self._tokenizer.encode(text, out_type=str)
        batches = [tokens[i:i+120] for i in range(0, len(tokens), 120)]
        result = self._translator.translate_batch(batches, beam_size=3, max_decoding_length=384)
        return ''.join(self._tokenizer.decode(x.hypotheses[0]).replace('\u2581', ' ').strip() for x in result)

    def text_worker(self):
        while True:
            while self.engine['status']=='loading':
                time.sleep(.05)
            job = self.text_queue.get()
            kind, sid = job[:2]
            jobs=[job]
            if kind=='translate':
                while len(jobs)<8:
                    try:
                        other=self.text_queue.get_nowait()
                    except queue.Empty:
                        break
                    if other[0]=='translate' and (other[1],other[3],other[4])==(sid,job[3],job[4]):
                        jobs.append(other)
                    else:
                        self.text_queue.put(other)
                        self.text_queue.task_done()
                        break
            try:
                if kind == 'translate':
                    self.translate_rows(sid,list(dict.fromkeys(r for j in jobs for r in j[2])),job[3],job[4])
            except ai.Cancelled:
                pass
            except Exception as exc:
                with self.lock:
                    if kind=='translate' and self.translation_current(sid,job[3],job[4]):
                        self.session['errors'].append('翻译失败：'+str(exc)[:300])
                        ids={r for j in jobs for r in j[2]}
                        for row in self.session['segments']:
                            if row['id'] in ids and row.get('translationRevision')==job[4]:
                                row['translationStatus']='error'
            finally:
                with self.lock:
                    if kind=='translate':
                        self.session['pendingText'] -= len(jobs)
                    self.save()
                for _ in jobs:
                    self.text_queue.task_done()

    def summary_worker(self):
        while True:
            sid=self.summary_queue.get()
            try:
                with self.lock:
                    if not self.session or self.session['id']!=sid:
                        continue
                    rows=[dict(r) for r in self.session['segments']]
                value=ai.summarize(rows,self.settings,self.data/'ai-runtime')
                with self.lock:
                    if self.session and self.session['id']==sid:
                        self.session['summary']=value
                        self.session['summaryStatus']='done'
                        self.session['errors']=[e for e in self.session['errors'] if not e.startswith('总结失败：')]
                        self.session['status']='complete'
                        self.save()
            except Exception as exc:
                with self.lock:
                    if self.session and self.session['id']==sid:
                        self.session['errors'].append('总结失败：'+str(exc)[:300])
                        self.session['summaryStatus']='error'
                        self.session['status']='complete'
                        self.save()
            finally:
                self.summary_queue.task_done()

    def watchdog(self):
        while True:
            time.sleep(2)
            with self.lock:
                s = self.session
                sid = s['id'] if s and s['status'] in ('recording', 'paused') and time.time()-self.last_seen>15 else None
                if sid:
                    s['errors'].append('录音面板连接中断，已保存收到的音频并结束会话。')
            if sid:
                self.finish(sid)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    @property
    def app(self):
        return self.server.recorder

    def allowed(self, write=False):
        host = self.headers.get('Host', '')
        expected = f'127.0.0.1:{self.server.server_port}'
        origin = self.headers.get('Origin')
        if host != expected or (origin and origin != 'http://'+expected):
            self.reply({'error': '只接受本机同源请求'}, 403)
            return False
        if write and not secrets.compare_digest(self.headers.get('X-Recorder-Token', ''), self.app.token):
            self.reply({'error': '本机会话凭据无效'}, 403)
            return False
        return True

    def reply(self, value, status=200, mime='application/json; charset=utf-8'):
        raw = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; media-src 'self' blob:; frame-ancestors 'none'")
        self.end_headers()
        try:
            self.wfile.write(raw)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        if not self.allowed():
            return
        path = urlparse(self.path).path
        if path in ('/', '/panel.js', '/panel.css', '/i18n.js', '/pcm-worklet.js'):
            name = 'index.html' if path=='/' else path[1:]
            mime = {'html':'text/html; charset=utf-8', 'js':'text/javascript; charset=utf-8', 'css':'text/css; charset=utf-8'}[name.rsplit('.',1)[1]]
            self.reply((ROOT/'web'/name).read_bytes(), mime=mime)
        elif path == '/api/state':
            self.reply(self.app.snapshot())
        elif path == '/api/bootstrap':
            self.reply({'token': self.app.token})
        elif path.startswith('/api/export/'):
            parts = path.split('/')
            if len(parts)!=5 or not all(c.isalnum() or c=='-' for c in parts[3]) or parts[4] not in ('audio.wav', 'notes.md', 'session.json'):
                self.reply({'error':'不存在'},404)
                return
            file = self.app.data/parts[3]/parts[4]
            if file.is_file():
                self.reply(file.read_bytes(), mime='audio/wav' if file.suffix=='.wav' else 'text/plain; charset=utf-8')
            else:
                self.reply({'error':'不存在'},404)
        else:
            self.reply({'error':'不存在'},404)

    def do_POST(self):
        if not self.allowed(write=True):
            return
        try:
            size = int(self.headers.get('Content-Length','0'))
            if not 0 < size <= 512000:
                raise ValueError('请求体大小不合适。')
            raw = self.rfile.read(size)
            parsed = urlparse(self.path)
            if parsed.path == '/api/chunk':
                params = parse_qs(parsed.query)
                captured=float(params.get('ended',[time.time()])[0])
                if abs(captured-time.time())>120:
                    captured=time.time()
                self.app.ingest(params['id'][0], int(params['seq'][0]), raw,captured)
            else:
                body = json.loads(raw)
                with self.app.lock:
                    s = self.app.session
                    if parsed.path == '/api/start':
                        self.app.start(body)
                    elif parsed.path == '/api/heartbeat':
                        self.app.last_panel_seen = time.time()
                        if self.app.client == body.get('client'):
                            self.app.last_seen = time.time()
                    elif parsed.path == '/api/control':
                        action = body.get('action')
                        if action == 'start':
                            self.app.start_requested = True
                        elif action in ('pause','resume','stop') and s and s['status'] in ('recording','paused'):
                            s['desired'] = {'pause':'paused','resume':'recording','stop':'stopped'}[action]
                        else:
                            raise ValueError('当前状态不支持此操作。')
                    elif parsed.path == '/api/status' and s and body.get('id')==s['id']:
                        if body.get('status') not in ('recording','paused') or s['status'] not in ('recording','paused'):
                            raise ValueError('状态不匹配。')
                        s['status'] = body['status']
                        s['desired'] = body['status']
                    elif parsed.path == '/api/settings' and s:
                        self.app.update_settings(body.get('translation'),body.get('target'))
                    elif parsed.path == '/api/retry-summary' and s and s['status']=='complete':
                        s['summaryStatus'] = 'running'
                        s['status'] = 'processing'
                        self.app.summary_queue.put(s['id'])
                    elif parsed.path == '/api/finish':
                        self.app.finish(body.get('id'))
                    else:
                        raise ValueError('未知请求或会话不存在。')
                    if parsed.path != '/api/heartbeat':
                        self.app.save()
            self.reply({'ok':True})
        except (ValueError, KeyError, TypeError) as exc:
            self.reply({'error': str(exc)[:200]},400)
        except Exception:
            self.reply({'error':'本地服务出错，已收到的音频保留在 data 目录。'},500)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int)
    parser.add_argument('--data-dir')
    args=parser.parse_args()
    settings_path = ROOT/'local.settings.json'
    settings = json.loads(settings_path.read_text(encoding='utf-8-sig')) if settings_path.exists() else {}
    port = args.port or settings.get('port',18764)
    if args.data_dir:
        settings['data_dir']=args.data_dir
    app = Recorder(settings=settings)
    server = ThreadingHTTPServer(('127.0.0.1',port), Handler)
    server.recorder = app
    app.launch()
    (app.data/'service.json').write_text(json.dumps({'port':port,'pid':os.getpid()}),encoding='utf-8')
    print(f'Recorder ready: http://127.0.0.1:{port}/', flush=True)
    try:
        server.serve_forever()
    finally:
        if app.writer:
            app.writer.close()
        server.server_close()

if __name__ == '__main__':
    main()
