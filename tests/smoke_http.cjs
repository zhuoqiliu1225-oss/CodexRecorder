// Non-mutating checks for local HTTP boundaries and export path validation.
const assert=require('node:assert/strict');
const base='http://127.0.0.1:18764';
(async()=>{
 const state=await fetch(base+'/api/state');assert.equal(state.status,200);
 const rejected=await fetch(base+'/api/control',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'stop'})});assert.equal(rejected.status,403);
 const auth=await (await fetch(base+'/api/bootstrap')).json();
 const origin=await fetch(base+'/api/control',{method:'POST',headers:{'Content-Type':'application/json','Origin':'https://example.com','X-Recorder-Token':auth.token},body:JSON.stringify({action:'stop'})});assert.equal(origin.status,403);
 const invalid=await fetch(base+'/api/export/invalid/secret.txt');assert.equal(invalid.status,404);
 const missing=await fetch(base+'/api/export/nonexistent/notes.md');assert.equal(missing.status,404);
 const js=await fetch(base+'/panel.js');assert.equal(js.status,200);assert.match(js.headers.get('Content-Type'),/javascript/);
 assert.match(js.headers.get('Content-Security-Policy'),/frame-ancestors 'none'/);
 console.log('PASS: local state, token check, origin check, export allowlist, JS and CSP');
})().catch(e=>{console.error(e);process.exitCode=1;});
