"""Opt-in integration test using a synthetic, non-private WAV file."""
import json
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
from faster_whisper.audio import decode_audio

BASE='http://127.0.0.1:18764'
token=json.load(urllib.request.urlopen(BASE+'/api/bootstrap'))['token']
def post(path, value, raw=False):
    body=value if raw else json.dumps(value).encode()
    req=urllib.request.Request(BASE+'/api/'+path,body,headers={
        'Content-Type':'application/octet-stream' if raw else 'application/json',
        'X-Recorder-Token':token})
    return json.load(urllib.request.urlopen(req))
def state():
    return json.load(urllib.request.urlopen(BASE+'/api/state'))

audio=decode_audio(sys.argv[1],sampling_rate=16000)
post('start',{'client':'synthetic-smoke','source':'en','translation':True,'target':'zh'})
sid=state()['session']['id']
# Same wire protocol as the panel, with chunks bounded to six seconds.
for seq, offset in enumerate(range(0,len(audio),96000)):
    pcm=(np.clip(audio[offset:offset+96000],-1,1)*32767).astype('<i2').tobytes()
    post(f'chunk?id={sid}&seq={seq}',pcm,True)
post('finish',{'id':sid})
deadline=time.time()+240
previous=None
while time.time()<deadline:
    session=state()['session']
    progress=(session['status'],session['pendingAsr'],session['pendingText'],session['summaryStatus'])
    if progress!=previous:
        print(progress,flush=True)
        previous=progress
    if session['status']=='complete':
        result=Path('verification')/'pipeline-result.json'
        result.write_text(json.dumps(session,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'id':sid,'segments':session['segments'],'summary':session['summary'],
            'errors':session['errors']},ensure_ascii=False),flush=True)
        assert session['segments'], 'No speech recognized'
        assert any(s.get('translation') for s in session['segments']), 'No translation returned'
        assert session['summaryStatus']=='done', 'Summary failed'
        assert not session['errors'], session['errors']
        break
    time.sleep(1)
else:
    raise TimeoutError('Synthetic pipeline did not finish in four minutes')
