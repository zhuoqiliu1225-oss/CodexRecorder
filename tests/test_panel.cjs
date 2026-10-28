const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
// Load presentation helpers without initializing microphone access or polling.
const source=fs.readFileSync(path.join(__dirname,'../web/panel.js'),'utf8');
const helpers=source.slice(0,source.indexOf('const $='));
const context=vm.createContext({});
vm.runInContext(helpers,context);
const rows=[0,2,5,12,29,30,32,59,60].map((start,i)=>({start,text:`word${i}`}));
const groups=context.transcriptGroups(rows);
assert.equal(groups.length,3);
assert.equal(groups[0].rows.length,5);
assert.equal(groups[1].rows.length,3);
assert.equal(groups[2].start,60);
assert.equal(context.joinedText(groups.flatMap(group=>group.rows.map(row=>row.text))),rows.map(row=>row.text).join(' '));
assert.equal(context.transcriptGroups([]).length,0);
assert.equal(context.transcriptGroups([{start:0},{start:90}]).length,2);
assert.equal(context.joinedText(['translated',undefined,'next']),'translated next');
console.log('PASS: 30-second display groups preserve text and do not wait for a full group.');
if(process.argv.includes('--browser')){
 const http=require('node:http');
 const copyHandler=source.slice(source.indexOf("document.addEventListener('copy'"),source.lastIndexOf('(async()=>'));
 const fixture=`<!doctype html><meta charset="utf-8"><title>Recorder copy tests</title>
 <div id="transcript"><article><div class="stamp">00:00</div><div class="original">Hello world</div><div class="translation">你好世界</div><div class="translation pending">处理中</div></article><article><div class="stamp">00:30</div><div class="original">Next paragraph</div></article></div><pre id="result">Running</pre>
 <script>${helpers}const $=id=>document.getElementById(id);${copyHandler}
 try{const s=getSelection(),root=$('transcript');function copy(range){s.removeAllRanges();s.addRange(range);const data=new DataTransfer();document.dispatchEvent(new ClipboardEvent('copy',{clipboardData:data,cancelable:true,bubbles:true}));return data.getData('text/plain');}
 let r=document.createRange();r.selectNodeContents(root);let value=copy(r);if(value!=='Hello world\\n你好世界\\nNext paragraph')throw Error('Whole selection: '+value);
 r=document.createRange();const text=root.querySelector('.original').firstChild;r.setStart(text,1);r.setEnd(text,5);value=copy(r);if(value!=='ello')throw Error('Partial selection: '+value);
 s.removeAllRanges();$('result').textContent='PASS: whole paragraphs exclude timestamps and pending labels; partial selection copies only selected text.';}catch(e){$('result').textContent='FAIL: '+e.message;}
 </script>`;
 http.createServer((req,res)=>{res.setHeader('Content-Type','text/html; charset=utf-8');res.end(fixture);}).listen(18766,'127.0.0.1',()=>console.log('Browser copy test: http://127.0.0.1:18766/'));
}
