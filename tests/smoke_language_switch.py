"""Use only the synthetic session from smoke_latency.py, on the isolated port."""
import json
import os
from pathlib import Path
import time
import urllib.request

BASE=os.environ.get('RECORDER_URL','http://127.0.0.1:18765')
token=json.load(urllib.request.urlopen(BASE+'/api/bootstrap'))['token']
def state():
    return json.load(urllib.request.urlopen(BASE+'/api/state'))['session']
def settings(target):
    req=urllib.request.Request(BASE+'/api/settings',json.dumps({'translation':True,'target':target}).encode(),
        headers={'Content-Type':'application/json','X-Recorder-Token':token})
    return json.load(urllib.request.urlopen(req))
def wait_translated(target,timeout=120):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        s=state()
        if all(r['target']==target and r['translationStatus']=='done' and r['translation'] for r in s['segments']):
            return s
        if any(r.get('translationStatus')=='error' for r in s['segments']):
            raise RuntimeError(s['errors'])
        time.sleep(.1)
    raise TimeoutError('History translation did not complete')
s=state()
assert all(r['language']=='en' for r in s['segments']),'This test requires the synthetic English fixture'
start=time.monotonic()
settings('es')
spanish=wait_translated('es')
cloud_seconds=time.monotonic()-start
assert all('es' in r['translations'] for r in spanish['segments'])
settings('en')
english=wait_translated('en')
assert all(r['text']==r['translation'] for r in english['segments'])
start=time.monotonic()
settings('es')
cached=wait_translated('es',5)
cache_seconds=time.monotonic()-start
assert [r['translation'] for r in cached['segments']]==[r['translation'] for r in spanish['segments']]
result={'rows':len(cached['segments']),'historyTranslationSeconds':round(cloud_seconds,3),
    'cachedSwitchSeconds':round(cache_seconds,3),'target':cached['target'],'translations':[r['translation'] for r in cached['segments']]}
(Path(__file__).resolve().parents[1]/'verification'/'language-switch-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False),flush=True)
