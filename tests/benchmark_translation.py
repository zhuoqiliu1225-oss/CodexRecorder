"""Measure local multilingual translation on synthetic sentences."""
import json
import os
from pathlib import Path
import sys
import time

root=Path(__file__).resolve().parents[1]
settings=json.loads((root/'local.settings.json').read_text(encoding='utf-8-sig'))
handles=[]
for directory in settings.get('cuda_library_dirs',[]):
    handles.append(os.add_dll_directory(directory))
    os.environ['PATH']=directory+os.pathsep+os.environ.get('PATH','')
sys.path.insert(0,str(root/'app'))
from local_translation import MultilingualTranslator
started=time.perf_counter()
translator=MultilingualTranslator(root/'models'/'m2m100','cuda')
loaded=time.perf_counter()-started
results=[]
cases=[('en','es','We will launch the first version next Friday. The budget is $500.'),
       ('zh','en','我们计划下周五发布第一个版本，预算是500美元。'),
       ('zh','ja','我们计划下周五发布第一个版本，预算是500美元。'),
       ('zh','ko','我们计划下周五发布第一个版本，预算是500美元。'),
       ('zh','fr','我们计划下周五发布第一个版本，预算是500美元。'),
       ('zh','de','我们计划下周五发布第一个版本，预算是500美元。'),
       ('zh','es','我们计划下周五发布第一个版本，预算是500美元。')]
for source,target,text in cases:
    started=time.perf_counter()
    value=translator.translate(text,source,target)
    results.append({'source':source,'target':target,'seconds':round(time.perf_counter()-started,3),'translation':value})
    assert value and '500' in value,(target,value)
result={'loadSeconds':round(loaded,3),'results':results}
(root/'verification'/'local-translation-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False),flush=True)
