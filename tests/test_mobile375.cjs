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
test('real 375 px layout in headless Chrome: intro below the bar after a jump; time on one line inside the gutter',{skip,timeout:60000},async()=>{
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
  const v={...jump,ts};
  sock.close();
  assert.equal(v.vw,375);assert.equal(v.docW,375,'no sideways scroll');
  assert.ok(v.introTop>=v.bar1,`intro top ${v.introTop} is below the tab bar bottom ${v.bar1}`);
  assert.ok(v.h2Top>=v.bar2,`lane heading top ${v.h2Top} is below the tab bar bottom ${v.bar2}`);
  assert.ok(v.ts.length>=1,'at least one lane shows a check-in time');
  for(const t of v.ts){assert.equal(t.lines,1,'check-in time renders on one line');assert.ok(t.right<=375-12,`check-in time right edge ${t.right} keeps a 12 px gutter`)}
 }finally{chrome.kill()}
});
