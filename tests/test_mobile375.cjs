// 375 px phone fixes (W39 probe, fixed by W54):
// (a) the sticky tab bar (46 px tall at 375 px) covered the section intro line after an anchor jump;
// (b) the ISO "Last check-in" time broke mid-string ("2026-10-" / "06T03:57...") and ran to the right edge.
// The first two tests run everywhere. The third measures real layout in headless Chrome over the DevTools
// protocol when Chrome and a global WebSocket are available, and is skipped otherwise.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),os=require('node:os');
const {spawn}=require('node:child_process');
const DASH='3edcf5514fd3812ea137d3ce41dafab3',LOG='2026-10-06T03:26:00.000Z';
const html=fs.readFileSync('template.html','utf8');
const css=html.slice(html.indexOf('<style>'),html.indexOf('</style>'));
function page(){
 const fleet=JSON.parse(fs.readFileSync('agents48.json','utf8'));
 const data={primary_agents:[DASH],agents:[{url:DASH,Agent:'Dash',Projects:[],Device:[]}],devices:[],projects:[],checkins:[],
  tracked_work:{label:'CEO clock-in repair',progress:10,progress_state:'SOURCED',status:'WORKING',as_of:'2026-10-06T03:45:00Z',freshness:'FRESH',checkin_status:'WORKING',checkin_logged:'2026-10-06T03:45:00Z',checkin_state:'MATCHED',project_progress:25,project_progress_state:'SOURCED',project_status:'MOVING',project_as_of:LOG,project_freshness:'FRESH',mismatch:true},
  asks:{asks:['DONE','IN PROGRESS','NEEDS YOU','UNPROVED','NOT STARTED','UNKNOWN'].map((status,n)=>({n:n+1,ask:`Ask ${n+1}`,owner:'Owner',lane:'Lane',status,updated:'today'})),lanes:[],needs_you:[]},
  report_coverage:{exhaustive:true,unique_rows:1,per_agent:{[DASH]:{agent_id:DASH,included:true,exhaustive:true,matching_rows:1,latest:{url:'r',Agent:[DASH],Logged:LOG,Time:LOG,Status:'WORKING',Device:[],Project:[]}}}},fleet};
 return html.replace('__REPORT_STATUS__',fs.readFileSync('report_status.js','utf8')).replace('__AT__','2026-10-06T03:47:00Z').replace('__SNAP__',JSON.stringify(data));
}
function render(hash){
 const DateFixed=class extends Date{constructor(...a){super(...(a.length?a:['2026-10-06T03:47:00Z']))}static now(){return Date.parse('2026-10-06T03:47:00Z')}};
 const element=()=>({innerHTML:'',textContent:'',style:{},addEventListener(){},classList:{toggle(){}}});
 const ids=['grok','dash','dot','asks','fleet','now','coceo','agents','devices','projects','tasks','caio','crons'],sections=ids.map(id=>({...element(),id}));
 const env={Date:DateFixed,URL,console,location:{href:'https://example.com/'+hash,hash,replace(){}},history:{replaceState(){}},document:{hidden:false,querySelectorAll:s=>s==='section'?sections:[],addEventListener(){}},setInterval(){},fetch:async()=>({ok:false}),sessionStorage:{getItem(){return null},setItem(){}}};
 ids.forEach((id,i)=>env[id]=sections[i]);['tabs','companies','fresh'].forEach(id=>env[id]=element());
 vm.createContext(env);vm.runInContext(page().match(/<script>([\s\S]*?)<\/script>/)[1],env);return env;
}
test('anchor jumps clear the sticky tab bar: html scroll-padding-top is at least the 46 px bar plus a gap',()=>{
 assert.match(css,/nav\{position:sticky;top:0/,'tab bar is sticky');
 const m=css.match(/html\{[^}]*scroll-padding-top:(\d+)px/);
 assert.ok(m,'html scroll-padding-top is set');assert.ok(+m[1]>=52,`scroll-padding-top ${m&&m[1]}px clears the 46 px bar`);
});
test('the check-in time is one unbreakable unit on every lane head (Grok, Dash, Dot sections and Agents detail)',()=>{
 assert.match(css,/\.ts\{[^}]*white-space:nowrap/,'.ts never wraps');
 const env=render('#dash');
 assert.match(env.dash.innerHTML,new RegExp('Last check-in: \\d+m ago · <span class="ts">'+LOG.replace(/\./g,'\\.')+'</span>'));
 const det=render('#fleet=dash').fleet.innerHTML;
 assert.match(det,new RegExp('Last check-in: \\d+m ago · <span class="ts">'+LOG.replace(/\./g,'\\.')+'</span>'));
 assert.doesNotMatch(env.dash.innerHTML+det,/Last check-in: [^<]*· 2026-/,'no bare ISO time left after the separator');
});
const CHROME=[process.env.CHROME_BIN,'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome','/usr/bin/google-chrome','/usr/bin/google-chrome-stable','/usr/bin/chromium','/usr/bin/chromium-browser'].find(p=>p&&fs.existsSync(p));
const skip=!CHROME?'no Chrome binary':typeof WebSocket!=='function'?'no global WebSocket in this Node':false;
test('real 375 px and desktop Chrome: tab visibility, progress card and ask counts match visible rows',{skip,timeout:60000},async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'dash375-'));fs.writeFileSync(path.join(dir,'page.html'),page());
 const args=['--headless=new','--remote-debugging-port=0','--user-data-dir='+path.join(dir,'prof'),'--no-first-run','--no-default-browser-check'];
 if(process.platform==='linux')args.push('--no-sandbox','--disable-gpu','--disable-dev-shm-usage');
 const chrome=spawn(CHROME,[...args,'about:blank'],{stdio:['ignore','ignore','pipe']});
 try{
  const ws=await new Promise((res,rej)=>{let b='';const t=setTimeout(()=>rej(new Error('Chrome did not start')),45000);chrome.stderr.on('data',d=>{b+=d;const m=b.match(/ws:\/\/\S+/);if(m){clearTimeout(t);res(m[0])}})});
  const sock=new WebSocket(ws);await new Promise((r,j)=>{sock.onopen=r;sock.onerror=j});
  let n=0;const pend={};sock.onmessage=e=>{const m=JSON.parse(e.data);if(m.id&&pend[m.id]){pend[m.id](m);delete pend[m.id]}};
  const send=(method,params={},sessionId)=>new Promise(r=>{const i=++n;pend[i]=r;sock.send(JSON.stringify({id:i,method,params,sessionId}))});
  const {result:{targetId}}=await send('Target.createTarget',{url:'about:blank'});
  const {result:{sessionId}}=await send('Target.attachToTarget',{targetId,flatten:true});
  const S=(m,p)=>send(m,p,sessionId);
  await S('Emulation.setDeviceMetricsOverride',{width:375,height:812,deviceScaleFactor:2,mobile:true});
  const go=async(hash,expr)=>{await S('Page.navigate',{url:'file://'+path.join(dir,'page.html')+'#'+hash});await new Promise(r=>setTimeout(r,1500));return (await S('Runtime.evaluate',{returnByValue:true,expression:expr})).result.result.value};
  const jump=await go('grok',`(()=>{const bar=()=>document.querySelector('nav').getBoundingClientRect().bottom,o={vw:innerWidth,docW:document.documentElement.scrollWidth};
   const i=document.querySelector('#grok .start');i.scrollIntoView();o.introTop=i.getBoundingClientRect().top;o.bar1=bar();
   const h=document.querySelector('#grok h2.fh');h.scrollIntoView();o.h2Top=h.getBoundingClientRect().top;o.bar2=bar();return o})()`);
  const ts=await go('dash',`[...document.querySelectorAll('#dash .fmeta')].filter(e=>e.textContent.startsWith('Last check-in')).map(e=>{const s=e.querySelector('.ts');if(!s)return{lines:0,right:0};const rg=document.createRange();rg.selectNodeContents(s);const rs=[...rg.getClientRects()];return{lines:rs.length,right:Math.max(...rs.map(x=>x.right))}})`);
  const mobileNow=await go('now',`(()=>{const card=document.querySelector('#now .tracked-work');return{cardDisplay:getComputedStyle(card).display,cardText:card.innerText,nowDisplay:getComputedStyle(document.querySelector('#now')).display,asksDisplay:getComputedStyle(document.querySelector('#asks')).display}})()`);
  const askView=await go('asks',`(()=>({summary:[...document.querySelectorAll('#asks .counts')].map(x=>x.innerText).join(' · '),rows:[...document.querySelectorAll('#asks tbody tr td[data-l="Status"]')].map(x=>x.innerText),asksDisplay:getComputedStyle(document.querySelector('#asks')).display,nowDisplay:getComputedStyle(document.querySelector('#now')).display}))()`);
  await S('Emulation.setDeviceMetricsOverride',{width:1280,height:900,deviceScaleFactor:1,mobile:false});
  const desktopNow=await go('now',`(()=>{const card=document.querySelector('#now .tracked-work');return{cardDisplay:getComputedStyle(card).display,cardText:card.innerText,nowDisplay:getComputedStyle(document.querySelector('#now')).display,asksDisplay:getComputedStyle(document.querySelector('#asks')).display}})()`);
  const future=await go('now',`(()=>{S.data.tracked_work.as_of='2099-01-01T00:00:00Z';render();return document.querySelector('#now .tracked-work').innerText})()`);
  const missing=await go('now',`(()=>{S.data.tracked_work.as_of=null;render();return document.querySelector('#now .tracked-work').innerText})()`);
  const projectFuture=await go('now',`(()=>{S.data.tracked_work.project_as_of='2099-01-01T00:00:00Z';render();return document.querySelector('#now .tracked-work').innerText})()`);
  const projectMissing=await go('now',`(()=>{S.data.tracked_work.project_as_of=null;render();return document.querySelector('#now .tracked-work').innerText})()`);
  const projectInvalid=await go('now',`(()=>{S.data.tracked_work.project_as_of='not-a-date';render();return document.querySelector('#now .tracked-work').innerText})()`);
  const independent=await go('now',`(()=>{const w=S.data.tracked_work;w.as_of=new Date(Date.now()-10*60*1000).toISOString();w.project_as_of=new Date(Date.now()-60*1000).toISOString();render();const reportOld=document.querySelector('#now .tracked-work').innerText;w.as_of=new Date(Date.now()-60*1000).toISOString();w.project_as_of=new Date(Date.now()-10*60*1000).toISOString();render();return JSON.stringify({reportOld,projectOld:document.querySelector('#now .tracked-work').innerText})})()`);
  const v={...jump,ts,mobileNow,askView,desktopNow,future,missing,projectFuture,projectMissing,projectInvalid,independent};
  sock.close();
  assert.equal(v.vw,375);assert.equal(v.docW,375,'no sideways scroll');
  assert.ok(v.introTop>=v.bar1,`intro top ${v.introTop} is below the tab bar bottom ${v.bar1}`);
  assert.ok(v.h2Top>=v.bar2,`lane heading top ${v.h2Top} is below the tab bar bottom ${v.bar2}`);
  assert.ok(v.ts.length>=1,'at least one lane shows a check-in time');
  for(const t of v.ts){assert.equal(t.lines,1,'check-in time renders on one line');assert.ok(t.right<=375-12,`check-in time right edge ${t.right} keeps a 12 px gutter`)}
  for(const view of [v.mobileNow,v.desktopNow]){assert.equal(view.cardDisplay,'block');assert.equal(view.nowDisplay,'block');assert.equal(view.asksDisplay,'none');assert.match(view.cardText,/Current report progress: 10%/);assert.match(view.cardText,/STALE/);assert.match(view.cardText,/Project-recorded: 25%/)}
  assert.equal(v.askView.asksDisplay,'block');assert.equal(v.askView.nowDisplay,'none');
  assert.deepEqual(v.askView.rows,['Done','In progress','Needs you','Unproved','Not started','Unknown']);
  assert.match(v.askView.summary,/Done 1 · In progress 1 · Needs you 1/);assert.match(v.askView.summary,/Unproved 1 · Not started 1 · Stuck 0 · Unknown 1/);
  assert.match(v.future,/Current report progress: UNKNOWN · UNKNOWN · report logged UNKNOWN · UNKNOWN/);
  assert.match(v.missing,/Current report progress: UNKNOWN · UNKNOWN · report logged UNKNOWN · UNKNOWN/);
  assert.match(v.projectFuture,/Project-recorded: UNKNOWN · UNKNOWN · project edited UNKNOWN · UNKNOWN/);
  assert.match(v.projectMissing,/Project-recorded: UNKNOWN · UNKNOWN · project edited UNKNOWN · UNKNOWN/);
  assert.match(v.projectInvalid,/Project-recorded: UNKNOWN · UNKNOWN · project edited UNKNOWN · UNKNOWN/);
  const reportCases=JSON.parse(v.independent);
  assert.match(reportCases.reportOld,/Current report progress: 10% · WORKING · report logged [^·]+ · STALE/);
  assert.match(reportCases.reportOld,/Project-recorded: 25% · MOVING · project edited [^·]+ · FRESH/);
  assert.match(reportCases.projectOld,/Project-recorded: 25% · MOVING · project edited [^·]+ · STALE/);
  assert.match(reportCases.projectOld,/Current report progress: 10% · WORKING · report logged [^·]+ · FRESH/);
  assert.match(v.mobileNow.cardText,/Current report progress: 10%[^\n]+STALE/);
  assert.match(v.mobileNow.cardText,/Project-recorded: 25%[^\n]+STALE/);
 }finally{chrome.kill()}
});
