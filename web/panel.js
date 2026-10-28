// Presentation groups are independent of the short audio chunks used for recognition.
function transcriptGroups(segments, seconds=60){
 const groups=[];
 for(const row of segments){let group=groups.at(-1);if(!group||row.start-group.start>=seconds){group={start:row.start,rows:[]};groups.push(group);}group.rows.push(row);}
 return groups;
}
function joinedText(parts){return parts.filter(Boolean).join(' ');}
function updateTranscript(root,groups,target,translate){
 const doc=root.ownerDocument;
 if(root.querySelector('.empty'))root.replaceChildren();
 groups.forEach((group,index)=>{
  let article=root.children[index];
  if(!article){article=doc.createElement('article');article.className='utterance';for(const name of ['stamp','original','translation']){const node=doc.createElement('div');node.className=name;article.append(node);}root.append(article);}
  const stamp=article.querySelector('.stamp'),original=article.querySelector('.original'),translated=article.querySelector('.translation');
  const seconds=Math.floor(group.start),label=`${Math.floor(seconds/60).toString().padStart(2,'0')}:${(seconds%60).toString().padStart(2,'0')}`;
  if(stamp.textContent!==label)stamp.textContent=label;
  const text=joinedText(group.rows.map(row=>row.text));if(original.textContent!==text)original.textContent=text;
  translated.hidden=!translate;
  const value=translate?joinedText(group.rows.map(row=>row.target===target?row.translation:row.translations?.[target])):'';
  if(translated.textContent!==value)translated.textContent=value;
 });
 while(root.children.length>groups.length)root.lastElementChild.remove();
}
function selectingTranscript(){const selection=window.getSelection();return selection&&!selection.isCollapsed&&$('transcript').contains(selection.anchorNode);}
function selectionText(selection){
 const output=[];
 for(let i=0;i<selection.rangeCount;i++){const range=selection.getRangeAt(i);const fragment=range.cloneContents();fragment.querySelectorAll('.stamp,.pending').forEach(el=>el.remove());const lines=[];for(const node of fragment.childNodes){if(node.nodeType===3){lines.push(node.textContent);}else{const blocks=node.querySelectorAll('.original,.translation');if(blocks.length)lines.push(...Array.from(blocks,el=>el.textContent));else lines.push(node.textContent);}}output.push(lines.join('\n').trim());}
 return output.filter(Boolean).join('\n\n');
}
const $=id=>document.getElementById(id);
let paragraphSeconds=Number(localStorage.getItem('recorder.paragraphSeconds'))||60;
if(![30,60,120].includes(paragraphSeconds))paragraphSeconds=60;
$('paragraph-length').value=String(paragraphSeconds);
const client=crypto.randomUUID();
let token='',view=null,stream=null,context=null,capture=null,sourceNode=null;
let sid=null,seq=0,pieces=[],sampleCount=0,silence=0,recording=false,paused=false,busy=false,stopping=false;
let flushAck=null;
let settingsChain=Promise.resolve();
let uploadChain=Promise.resolve(),uploadError=null,lastRender='',tab='transcript',polling=false,serviceId=null,settingsSession=null;
const autoStart=new URLSearchParams(location.search).get('start')==='1';let autoAttempted=false,requestSeen=false;
const labels={recording:'正在录音',paused:'已暂停',processing:'正在整理',complete:'录音已完成',error:'录音异常'};
async function api(path,body,retry=true){const res=await fetch('/api/'+path,{method:body===undefined?'GET':'POST',headers:body===undefined?{}:{'Content-Type':'application/json','X-Recorder-Token':token},body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(8000)});const data=await res.json();if(res.status===403&&body!==undefined&&retry){token=(await api('bootstrap')).token;return api(path,body,false);}if(!res.ok)throw Error(data.error||'请求失败');return data;}
function notice(message){$('notice').hidden=!message;$('notice').textContent=message||'';}
function timeLabel(seconds){const n=Math.floor(seconds);return `${Math.floor(n/60).toString().padStart(2,'0')}:${(n%60).toString().padStart(2,'0')}`;}
function summaryView(markdown){const content=document.createElement('div');content.id='summary-content';let table=null;for(const line of markdown.split('\n')){if(/^\s*\|/.test(line)){if(/^\s*\|[\s:|\-]+\|\s*$/.test(line))continue;if(!table){table=document.createElement('table');content.append(table);}const row=document.createElement('tr');for(const cell of line.trim().replace(/^\||\|$/g,'').split('|')){const td=document.createElement(table.rows.length?'td':'th');td.textContent=cell.trim().replace(/\*\*/g,'');row.append(td);}table.append(row);continue;}table=null;if(!line.trim())continue;const heading=line.match(/^(#{1,4})\s+(.*)/);const el=document.createElement(heading?'h'+Math.min(4,heading[1].length+1):'p');el.textContent=(heading?heading[2]:line).replace(/\*\*/g,'');content.append(el);}return content;}
function pcm16(float){const out=new Int16Array(float.length);for(let i=0;i<float.length;i++)out[i]=Math.max(-32768,Math.min(32767,Math.round(float[i]*32767)));return out;}
function flush(){if(!sampleCount)return;const combined=new Float32Array(sampleCount);let offset=0;for(const piece of pieces){combined.set(piece,offset);offset+=piece.length;}pieces=[];sampleCount=0;silence=0;const raw=pcm16(combined);const chunkSeq=seq++,sessionId=sid,ended=Date.now()/1000;
 uploadChain=uploadChain.then(async()=>{if(uploadError)throw uploadError;for(let attempt=0;attempt<3;attempt++){try{const res=await fetch(`/api/chunk?id=${encodeURIComponent(sessionId)}&seq=${chunkSeq}&ended=${ended}`,{method:'POST',headers:{'Content-Type':'application/octet-stream','X-Recorder-Token':token},body:raw});if(!res.ok){const e=await res.json();throw Error(e.error);}return;}catch(e){if(attempt===2){uploadError=e;notice('音频上传到本机服务失败。请保持页面打开；已有音频已保存。'+e.message);throw e;}await new Promise(r=>setTimeout(r,500));}}}).catch(e=>{uploadError=e;});
}
function samples(frame){if(!recording||paused)return;let data=frame;if(context.sampleRate!==16000){const ratio=context.sampleRate/16000;const length=Math.floor(frame.length/ratio);data=new Float32Array(length);for(let i=0;i<length;i++){let sum=0,count=0;for(let j=Math.floor(i*ratio);j<Math.floor((i+1)*ratio);j++){sum+=frame[j];count++;}data[i]=sum/Math.max(1,count);}}
 let energy=0;for(const x of data)energy+=x*x;const rms=Math.sqrt(energy/data.length);$('level').style.width=Math.min(100,rms*500)+'%';pieces.push(data);sampleCount+=data.length;silence=rms<.007?silence+data.length:0;
 if((sampleCount>=12800&&silence>=4000)||sampleCount>=38400)flush();
 if(uploadError&&!stopping){void pauseRecording();}
}
async function release(){recording=false;paused=false;stream?.getTracks().forEach(t=>t.stop());stream=null;capture?.disconnect();sourceNode?.disconnect();capture=null;sourceNode=null;if(context){await context.close();context=null;}$('level').style.width='0%';}
async function drainCapture(){if(!capture||paused)return;await new Promise(resolve=>{const timer=setTimeout(()=>{flushAck=null;resolve();},800);flushAck=()=>{clearTimeout(timer);flushAck=null;resolve();};capture.port.postMessage({type:'flush'});});}
async function startRecording(){if(busy||recording)return;busy=true;notice('');$('start').disabled=true;try{
 await settingsChain;
 stream=await navigator.mediaDevices.getUserMedia({audio:{channelCount:1,echoCancellation:true,noiseSuppression:true},video:false});
 context=new AudioContext({sampleRate:16000});await context.audioWorklet.addModule('/pcm-worklet.js');await context.resume();
 await api('start',{client,source:$('source').value,target:$('target').value,translation:$('translate').checked});
 view=await api('state');sid=view.session.id;seq=0;pieces=[];sampleCount=0;silence=0;uploadChain=Promise.resolve();uploadError=null;
 sourceNode=context.createMediaStreamSource(stream);capture=new AudioWorkletNode(context,'recorder-capture');capture.port.onmessage=e=>{if(e.data?.type==='flushed'){flushAck?.();}else{samples(e.data);}};sourceNode.connect(capture);capture.connect(context.destination);recording=true;paused=false;
 stream.getAudioTracks().forEach(track=>track.onended=()=>{if(recording&&!stopping){notice('麦克风已断开，正在保存已有内容。');void stopRecording();}});
 tab='transcript';render();
 }catch(e){await release();notice('无法开始录音：'+e.message);}finally{busy=false;render();}}
async function pauseRecording(){if(!recording||paused||busy)return;busy=true;try{stream.getAudioTracks().forEach(t=>t.enabled=false);await drainCapture();paused=true;await context.suspend();flush();await api('status',{id:sid,status:'paused'});}catch(e){notice(e.message);}finally{busy=false;await poll();}}
async function resumeRecording(){if(!recording||!paused||busy)return;busy=true;try{await context.resume();stream.getAudioTracks().forEach(t=>t.enabled=true);await api('status',{id:sid,status:'recording'});paused=false;}catch(e){notice(e.message);}finally{busy=false;await poll();}}
async function stopRecording(){if(!recording||stopping)return;stopping=true;busy=true;try{stream?.getTracks().forEach(t=>t.enabled=false);await drainCapture();paused=true;await context?.suspend();flush();await uploadChain;if(uploadError)notice('部分音频未成功保存，以下总结可能不完整。');await release();await api('finish',{id:sid});tab='summary';}catch(e){notice('停止时出错：'+e.message);}finally{stopping=false;busy=false;await poll();}}
function render(){const s=view?.session;const status=recording?(paused?'paused':'recording'):s?.status;const active=s&&['recording','paused','processing'].includes(s.status);
 document.body.classList.toggle('has-session',!!s);
 if(s&&settingsSession!==s.id&&!recording&&!busy){settingsSession=s.id;$('source').value=s.source;$('target').value=s.target;$('translate').checked=s.translation;}
 const statusLabel=labels[status]||'准备录音';if($('status').dataset.label!==statusLabel){$('status').dataset.label=statusLabel;$('status').textContent=statusLabel;const dot=document.createElement('i');$('status').prepend(dot);}$('status').classList.toggle('live',status==='recording');
 $('engine').textContent=view?.engine.status==='ready'?(view.engine.device==='cuda'?'GPU 低延迟转写':'CPU 本地转写'):view?.engine.status==='error'?'语音模型加载失败':'正在加载并预热语音模型…';
 $('start').disabled=busy||!!active||!!s?.pendingText||view?.engine.status!=='ready';$('pause').disabled=busy||!recording;$('pause').textContent=paused?'▶ 继续':'Ⅱ 暂停';$('stop').disabled=busy||!recording;$('source').disabled=!!active;
 $('target-field').hidden=!$('translate').checked;$('translation-hint').hidden=!$('translate').checked;
 $('translation-hint').textContent=`切换语言后，已有内容与后续内容都会使用新语言。${view?.engine.translationMode==='local'?'当前使用本地快速翻译。':'当前使用 GPT 翻译，网络请求可能需要较长时间。'}已翻译过的语言直接复用。`;
 const duration=s?s.samples/16000+sampleCount/16000:0;const hours=Math.floor(duration/3600);const minutes=Math.floor(duration/60)%60;const seconds=Math.floor(duration)%60;
 $('timer').textContent=`${String(hours).padStart(2,'0')}:${String(minutes).padStart(2,'0')}`;const small=document.createElement('span');small.textContent=':'+String(seconds).padStart(2,'0');$('timer').append(small);
 $('transcript').hidden=tab!=='transcript';$('summary').hidden=tab!=='summary';$('transcript-tab').classList.toggle('active',tab==='transcript');$('summary-tab').classList.toggle('active',tab==='summary');
 $('count').textContent=transcriptGroups(s?.segments||[],paragraphSeconds).length;
 const pending=(s?.pendingAsr||0)+(s?.pendingText||0);$('queue').hidden=false;
 const translationError=s?.segments.some(row=>row.translationStatus==='error');
 const captureLabel=status==='recording'?'正在录音 · ':status==='paused'?'已暂停 · ':'';
 $('queue').textContent=captureLabel+(pending?`正在处理：${s?.pendingAsr||0} 段转写 · ${s?.pendingText||0} 组翻译`:translationError?'部分译文未完成，原文已保留':status==='recording'?'文字持续更新':status==='paused'?'已收到的音频已保存':s?'文字已同步':'等待开始录音');
 const metrics=s?.metrics||{};$('latency').hidden=metrics.asrSeconds===undefined;$('latency').textContent=metrics.asrSeconds===undefined?'':`最近一段：识别 ${metrics.asrSeconds.toFixed(2)} 秒 · 排队 ${(metrics.queueSeconds||0).toFixed(2)} 秒${metrics.translationSeconds===undefined?'':` · 翻译 ${metrics.translationSeconds.toFixed(2)} 秒`}`;
 if(s){$('saved').textContent='已保存 '+timeLabel(s.samples/16000)+' 音频 · 本机';$('exports').hidden=false;$('notes').href=`/api/export/${s.id}/notes.md`;$('audio').href=`/api/export/${s.id}/audio.wav`;
  const key=JSON.stringify([s.id,s.segments,s.summaryStatus,s.summary,paragraphSeconds,$('target').value,$('translate').checked]);if(key!==lastRender&&!selectingTranscript()){lastRender=key;if(!s.segments.length){const empty=document.createElement('div');empty.className='empty';empty.textContent='正在等待语音，确认后的文字会显示在这里。';$('transcript').replaceChildren(empty);}if(s.segments.length)updateTranscript($('transcript'),transcriptGroups(s.segments,paragraphSeconds),$('target').value,$('translate').checked);
   if(s.summary){$('summary').replaceChildren(summaryView(s.summary));}else{const block=document.createElement('div');block.className='empty';block.textContent=s.summaryStatus==='running'?'Codex 正在整理总结…':s.summaryStatus==='error'?'自动总结未完成，转写仍已保存。可以重新生成总结，或在聊天里继续整理。':s.status==='processing'?'正在补齐转写与翻译，随后自动总结…':'结束录音后，自动整理摘要、要点和待办。';$('summary').replaceChildren(block);}}
  if(s.errors.length)notice(s.errors.join('\n'));
 }
 if(view?.engine.status==='error')notice(view.engine.error);
 $('retry-summary').hidden=tab!=='summary'||!s||s.status!=='complete';
}
async function poll(){if(polling)return;polling=true;try{view=await api('state');if(serviceId&&serviceId!==view.serviceId){token=(await api('bootstrap')).token;if(recording){await release();notice('本地服务已重启，麦克风已停止。请检查已保存的录音后重新开始。');}}serviceId=view.serviceId;await api('heartbeat',{client});if(recording){if(!busy){if(view.session?.desired==='stopped')void stopRecording();else if(view.session?.desired==='paused'&&!paused)void pauseRecording();else if(view.session?.desired==='recording'&&paused)void resumeRecording();}}
 render();if(!view.startRequested)requestSeen=false;if(((autoStart&&!autoAttempted)||(view.startRequested&&!requestSeen))&&view.engine.status==='ready'&&!recording&&!busy&&!['recording','paused','processing'].includes(view.session?.status)){autoAttempted=true;requestSeen=true;void startRecording();}
 }catch(e){notice('与本机服务连接中断：'+e.message);}finally{polling=false;}}
$('start').onclick=startRecording;$('pause').onclick=()=>paused?resumeRecording():pauseRecording();$('stop').onclick=stopRecording;
async function settings(){const desired={translation:$('translate').checked,target:$('target').value};render();if(view?.session){settingsChain=settingsChain.then(()=>api('settings',desired)).catch(e=>notice(e.message));await settingsChain;await poll();}}
$('translate').onchange=settings;$('target').onchange=settings;
$('retry-summary').onclick=async()=>{try{await api('retry-summary',{});await poll();}catch(e){notice(e.message);}};
$('transcript-tab').onclick=()=>{tab='transcript';render();};$('summary-tab').onclick=()=>{tab='summary';render();};
$('paragraph-length').onchange=()=>{paragraphSeconds=Number($('paragraph-length').value);localStorage.setItem('recorder.paragraphSeconds',String(paragraphSeconds));render();};
$('copy-original').onclick=async()=>{try{const text=transcriptGroups(view?.session?.segments||[],paragraphSeconds).map(group=>joinedText(group.rows.map(row=>row.text))).join('\n\n');if(!text){notice('当前没有可复制的文字。');return;}await navigator.clipboard.writeText(text);$('copy-original').textContent='已复制';setTimeout(()=>$('copy-original').textContent='复制原文',1500);}catch(e){notice('复制失败，请选中文字后按 Ctrl+C：'+e.message);}};
window.addEventListener('beforeunload',e=>{if(recording){e.preventDefault();e.returnValue='';}});
window.addEventListener('pagehide',()=>{stream?.getTracks().forEach(t=>t.stop());});
// Keep selected text stable while live updates arrive, and copy only the selected
// portion of original/translated text (never the timestamps or processing labels).
document.addEventListener('copy',event=>{const selection=window.getSelection();if(!selection||selection.isCollapsed||!selection.rangeCount)return;const root=$('transcript');let intersects=false;for(let i=0;i<selection.rangeCount;i++)intersects=selection.getRangeAt(i).intersectsNode(root)||intersects;if(intersects&&event.clipboardData){event.clipboardData.setData('text/plain',selectionText(selection));event.preventDefault();}});
(async()=>{try{token=(await api('bootstrap')).token;await poll();if(view?.session?.translation)await settings();setInterval(poll,300);setInterval(()=>{if(recording)render();},1000);}catch(e){notice(e.message);}})();
