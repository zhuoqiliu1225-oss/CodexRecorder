"""Play a synthetic WAV into the local wire protocol at realtime speed."""
import json
import os
from pathlib import Path
import time
import urllib.request
import numpy as np
from faster_whisper.audio import decode_audio

BASE=os.environ.get('RECORDER_URL','http://127.0.0.1:18765')
root=Path(__file__).resolve().parents[1]
token=json.load(urllib.request.urlopen(BASE+'/api/bootstrap'))['token']
def post(path,value,raw=False):
    req=urllib.request.Request(BASE+'/api/'+path,value if raw else json.dumps(value).encode(),headers={
        'Content-Type':'application/octet-stream' if raw else 'application/json','X-Recorder-Token':token})
    return json.load(urllib.request.urlopen(req))
def state():
    return json.load(urllib.request.urlopen(BASE+'/api/state'))
for _ in range(120):
    if state()['engine']['status']=='ready':
        break
    time.sleep(.25)
assert state()['engine']['status']=='ready'
audio=decode_audio(str(root/'verification'/'sample-en.wav'),sampling_rate=16000)
post('start',{'client':'latency-test','source':'en','translation':True,'target':'zh'})
sid=state()['session']['id']
started=time.monotonic()
first_text=None
first_translation=None
observations=[]
for seq,offset in enumerate(range(0,len(audio),38400)):
    pcm=(np.clip(audio[offset:offset+38400],-1,1)*32767).astype('<i2').tobytes()
    due=started+min(len(audio),offset+38400)/16000
    while time.monotonic()<due:
        post('heartbeat',{'client':'latency-test'})
        s=state()['session']
        if s['segments'] and first_text is None:
            first_text=round(time.monotonic()-started,3)
        if any(r.get('translation') for r in s['segments']) and first_translation is None:
            first_translation=round(time.monotonic()-started,3)
        time.sleep(min(.08,max(0,due-time.monotonic())))
    post(f'chunk?id={sid}&seq={seq}&ended={time.time()}',pcm,True)
post('finish',{'id':sid})
deadline=time.monotonic()+150
while time.monotonic()<deadline:
    s=state()['session']
    if s['segments'] and first_text is None:
        first_text=round(time.monotonic()-started,3)
    if any(r.get('translation') for r in s['segments']) and first_translation is None:
        first_translation=round(time.monotonic()-started,3)
    if not s['pendingAsr'] and not s['pendingText']:
        break
    time.sleep(.08)
result={'device':state()['engine'].get('device'),'firstTextSeconds':first_text,
    'firstTranslationSeconds':first_translation,'latestMetrics':s.get('metrics'),
    'segments':[{k:r.get(k) for k in ('text','translation')} for r in s['segments']],'errors':s['errors']}
(root/'verification'/'latency-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False),flush=True)
assert first_text and first_text<6,'GPU subtitle path should be faster than old six-second capture window'
assert first_translation,'No local translation'
assert not s['errors'],s['errors']
combined=' '.join(r['text'] for r in s['segments']).lower()
assert '500' in combined and '600' not in combined,'Short-window regression changed the budget'
assert 'alice' in combined and 'thursday' in combined,'Rolling context lost the test owner or deadline'
