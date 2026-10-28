// Full-panel browser regression using synthetic state; no microphone or AI.
// Run: node tests/live_layout.cjs, then open http://127.0.0.1:18766/.
const http=require('node:http');
const fs=require('node:fs');
const path=require('node:path');
const root=path.join(__dirname,'../web');
let tick=0;
const probe=`<script>
setTimeout(()=>{
 const ids=['queue','transcript','saved'],samples=[];let count=0;
 const timer=setInterval(()=>{
  samples.push(ids.map(id=>{const r=document.getElementById(id).getBoundingClientRect();return [r.top,r.height]}));
  if(++count<50)return;
  clearInterval(timer);const delta=Math.max(...samples.flatMap(sample=>sample.flatMap((rect,i)=>rect.map((v,j)=>Math.abs(v-samples[0][i][j])))));
  const queue=document.getElementById('queue'),result=document.createElement('div');result.id='layout-result';result.setAttribute('role','status');
  result.textContent=(delta===0&&queue.textContent===RecorderI18n.t('正在录音 · 转写与翻译持续更新')?'PASS':'FAIL')+': 50 live samples; max panel movement '+delta+'px; status '+queue.textContent;
  document.body.append(result);
 },100);
},800);
</script>`;
http.createServer((req,res)=>{
 res.setHeader('Cache-Control','no-store');
 if(req.url==='/api/bootstrap'){res.setHeader('Content-Type','application/json');return res.end(JSON.stringify({token:'fixture'}));}
 if(req.url==='/api/state'){
  tick++;const segments=Array.from({length:Math.min(8,tick)},(_,i)=>({id:String(i),start:i*62,text:'Synthetic original speech. '.repeat(3),target:'zh',translation:tick%3===0?'多行合成译文用于验证页面不会被上下顶动。'.repeat(30):'',provisional:tick%2===0,translationStatus:tick%3===0?'done':'pending'}));
  res.setHeader('Content-Type','application/json');return res.end(JSON.stringify({serviceId:'fixture',startRequested:false,engine:{status:'ready',device:'cuda',translationMode:'local'},languages:{zh:'简体中文',en:'English'},session:{id:'fixture',status:'recording',desired:'recording',source:'en',target:'zh',translation:true,samples:tick*16000,segments,pendingAsr:tick%2,pendingText:tick%3,summaryStatus:'idle',summary:'',errors:[],metrics:{asrSeconds:tick%2?.01:10,queueSeconds:0,translationSeconds:tick%2?.1:12}}}));
 }
 if(req.url.startsWith('/api/')){res.setHeader('Content-Type','application/json');return res.end('{"ok":true}');}
 const name=req.url==='/'?'index.html':req.url.slice(1);
 if(!['index.html','panel.js','panel.css','i18n.js'].includes(name)){res.statusCode=404;return res.end();}
 res.setHeader('Content-Type',name.endsWith('.js')?'text/javascript':name.endsWith('.css')?'text/css':'text/html; charset=utf-8');
 let content=fs.readFileSync(path.join(root,name));
 if(name==='index.html')content=content.toString().replace('</body>',probe+'</body>');
 res.end(content);
}).listen(18766,'127.0.0.1',()=>console.log('Synthetic full-panel layout test: http://127.0.0.1:18766/'));
