// Run only with an explicitly started, paused test recording in the panel.
const {execFile}=require('node:child_process');
const {promisify}=require('node:util');
const path=require('node:path');
const assert=require('node:assert/strict');
const run=promisify(execFile);
const root=path.resolve(__dirname,'..');
async function state(){return (await fetch('http://127.0.0.1:18764/api/state')).json();}
async function command(action){await run(process.execPath,[path.join(root,'scripts/control.cjs'),action],{cwd:root,windowsHide:true});}
async function waitFor(predicate){for(let i=0;i<80;i++){const s=await state();if(predicate(s.session))return s.session;await new Promise(r=>setTimeout(r,100));}throw Error('Panel did not acknowledge control');}
(async()=>{
 const before=(await state()).session;
 assert.equal(before.status,'paused','Start and pause a test recording first');
 await command('resume');
 const resumed=await waitFor(s=>s.status==='recording');
 assert.equal(resumed.id,before.id);
 await command('stop');
 const stopped=await waitFor(s=>['processing','complete'].includes(s.status));
 assert.equal(stopped.id,before.id);
 console.log(JSON.stringify({id:stopped.id,resumeAcknowledged:true,stopAcknowledged:true,
     status:stopped.status,samples:stopped.samples,errors:stopped.errors},null,2));
})().catch(e=>{console.error(e.message);process.exitCode=1;});
