"""Opt-in timing on synthetic speech, never live microphone input."""
import argparse
import gc
import json
import os
from pathlib import Path
import statistics
import time

parser=argparse.ArgumentParser()
parser.add_argument('--device',choices=['cpu','cuda'],required=True)
args=parser.parse_args()
root=Path(__file__).resolve().parents[1]
settings=json.loads((root/'local.settings.json').read_text(encoding='utf-8-sig'))
handles=[]
for directory in settings.get('cuda_library_dirs',[]):
    if os.name=='nt':
        handles.append(os.add_dll_directory(directory))
    os.environ['PATH']=directory+os.pathsep+os.environ.get('PATH','')
from faster_whisper import WhisperModel
from faster_whisper.audio import decode_audio
audio=decode_audio(str(root/'verification'/'sample-en.wav'),sampling_rate=16000)[:96000]
started=time.perf_counter()
model=WhisperModel(settings['model'],device=args.device,
    compute_type='float16' if args.device=='cuda' else 'int8',cpu_threads=4)
load=time.perf_counter()-started
times=[]
for _ in range(2):
    started=time.perf_counter()
    segments,_info=model.transcribe(audio,language='en',beam_size=1,vad_filter=True,
        condition_on_previous_text=False,vad_parameters={'min_silence_duration_ms':350})
    text=' '.join(s.text for s in segments)
    times.append(round(time.perf_counter()-started,3))
result={'device':args.device,'audioSeconds':len(audio)/16000,'loadSeconds':round(load,3),
        'inferenceSeconds':times,'text':text}
(root/'verification'/f'benchmark-{args.device}.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result),flush=True)
