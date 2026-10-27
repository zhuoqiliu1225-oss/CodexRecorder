#!/usr/bin/env node
const fs = require('node:fs');
const path = require('node:path');
const {spawn} = require('node:child_process');
const root=path.resolve(__dirname,'..');
const settingsFile=path.join(root,'local.settings.json');
const settings=fs.existsSync(settingsFile)?JSON.parse(fs.readFileSync(settingsFile,'utf8').replace(/^\uFEFF/,'')):{};
const base=`http://127.0.0.1:${settings.port||18764}`;
async function getState(){return (await fetch(base+'/api/state',{signal:AbortSignal.timeout(2000)})).json();}
async function command(action){const auth=await (await fetch(base+'/api/bootstrap')).json();const res=await fetch(base+'/api/control',{method:'POST',headers:{'Content-Type':'application/json','X-Recorder-Token':auth.token},body:JSON.stringify({action})});const body=await res.json();if(!res.ok)throw Error(body.error);}
async function ensureServer(){try{return await getState();}catch{}
 let python=settings.python||path.join(root,'.venv','Scripts','python.exe');
 if(!fs.existsSync(python))throw Error('请先运行 scripts/setup.ps1，安装本地语音环境。');
 // pythonw avoids inheriting a Windows console-close event from the launcher.
 const windowless=path.join(path.dirname(python),'pythonw.exe');
 if(process.platform==='win32'&&fs.existsSync(windowless))python=windowless;
 const data=path.join(root,'data');fs.mkdirSync(data,{recursive:true});
 const out=fs.openSync(path.join(data,'service.log'),'a');
 const child=spawn(python,[path.join(root,'app','server.py')],{cwd:root,detached:true,windowsHide:true,stdio:['ignore',out,out]});child.unref();fs.closeSync(out);
 let failure;child.on('error',e=>{failure=e;});
 for(let i=0;i<40;i++){if(failure)throw failure;await new Promise(r=>setTimeout(r,250));try{return await getState();}catch{}}
 throw Error('本地录音服务未启动，请检查 data/service.log。');
}
(async()=>{const action=process.argv[2]||'status';if(!['start','stop','pause','resume','status','serve'].includes(action))throw Error('用法：node scripts/control.cjs start|stop|pause|resume|status|serve');
 if(action==='start'||action==='serve')await ensureServer();
 if(!['status','serve'].includes(action))await command(action);
 const state=await getState();
 const s=state.session;
 const session=process.argv.includes('--full')?s:s?{id:s.id,status:s.status,desired:s.desired,
   seconds:Math.round(s.samples/16000),segments:s.segments.length,pendingAsr:s.pendingAsr,
   pendingText:s.pendingText,summaryStatus:s.summaryStatus,errors:s.errors,
   notes:path.join(root,'data',s.id,'notes.md')}:null;
 console.log(JSON.stringify({url:base+(action==='start'?'/?start=1':'/'),engine:state.engine,session,clientConnected:state.clientConnected},null,2));
})().catch(e=>{console.error(e.message);process.exitCode=1;});
