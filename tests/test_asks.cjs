// "Your asks" tab: Bennett's one view of every ask, its owner, its status and proof (W18). Also the W10 R11 rules:
// no row shows more than 4 numbers, and agent/project chips are real links.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');
const AG='3edcf5514fd3812ea137d3ce41dafab3',PJ='c'.repeat(32),LANEP='d'.repeat(32),DEV='e'.repeat(32);
function run(hash='',mutate=()=>{}){
 const DateFixed=class extends Date{constructor(...a){super(...(a.length?a:['2026-10-06T03:00:00Z']))}static now(){return Date.parse('2026-10-06T03:00:00Z')}};
 const element=()=>({innerHTML:'',textContent:'',style:{},addEventListener(){},classList:{toggle(){}}});
 const ids=['grok','dash','dot','asks','fleet','now','coceo','agents','devices','projects','tasks','caio','crons'],sections=ids.map(id=>({...element(),id}));
 const env={Date:DateFixed,URL,console,location:{href:'https://example.com/'+hash,hash,replace(){}},history:{replaceState(){}},document:{hidden:false,querySelectorAll:s=>s==='section'?sections:[],addEventListener(){}},setInterval(){},fetch:async()=>({ok:false}),sessionStorage:{getItem(){return null},setItem(){}}};
 ids.forEach((id,i)=>env[id]=sections[i]);['tabs','companies','fresh'].forEach(id=>env[id]=element());
 const asks=JSON.parse(fs.readFileSync('asks.json','utf8'));
 const data={primary_agents:[AG],agents:[{url:AG,Agent:'Dash',Projects:[PJ],Device:[DEV]}],devices:[{url:DEV,Device:'Studio'}],
  projects:[{url:PJ,Project:'Some Project',Status:'🟡 Moving',_edited:'2026-10-06T02:00:00Z'},{url:LANEP,Project:'H1 · Dash check-in fields',Status:'🔴 Stuck',_edited:'2026-10-06T02:30:00Z'}],
  caio:[{url:'f'.repeat(32),Division:'Ops',Projects:[PJ]}],checkins:[],
  report_coverage:{exhaustive:true,unique_rows:1,per_agent:{[AG]:{agent_id:AG,included:true,exhaustive:true,matching_rows:1,latest:{url:'r',Agent:[AG],Logged:'2026-10-06T02:57:00Z',Time:'2026-10-06T02:57:00Z',Status:'BLOCKED','Blocker question':'Need a key',Device:[DEV],Project:[PJ]}}}},
  asks:{asks:asks.asks,lanes:asks.lanes,needs_you:asks.needs_you,updated:asks.updated,sources:asks.sources}};
 mutate(data);
 const src=fs.readFileSync('template.html','utf8').replace('__REPORT_STATUS__',fs.readFileSync('report_status.js','utf8')).replace('__AT__','2026-10-06T02:58:00Z').replace('__SNAP__',JSON.stringify(data));
 vm.createContext(env);vm.runInContext(src.match(/<script>([\s\S]*?)<\/script>/)[1],env);return {env,asks};
}
const S=env=>vm.runInContext('S',env);
test('Grok, Dash, Dot lead the tabs; Your asks stays the default landing view, and #asks opens it',()=>{
 const html=fs.readFileSync('template.html','utf8');
 assert.match(html,/const TABS=\[\["grok","Grok"\],\["dash","Dash"\],\["dot","Dot"\],\["asks","Your asks"\],\["fleet","Agents"\],\["now","Now"\]/);
 assert.match(html,/<main><div id="pagewarn"><\/div><section id="grok"><\/section><section id="dash"><\/section><section id="dot"><\/section><section id="asks">/);
 const {env}=run('');assert.equal(S(env).tab,'asks');assert.match(env.tabs.innerHTML,/^<a href="#grok" data-k="grok" class="">Grok<\/a><a href="#dash" data-k="dash" class="">Dash<\/a><a href="#dot" data-k="dot" class="">Dot<\/a><a href="#asks" data-k="asks" class="on">Your asks<\/a>/);
 assert.equal(S(run('#asks').env).tab,'asks');assert.equal(S(run('#now').env).tab,'now');
});
test('top line, counts and the three sections render with one row per ask and per lane',()=>{
 const {env,asks}=run('');const h=env.asks.innerHTML;
 assert.match(h,/Start here: everything you asked for, who owns it, and whether it's done\./);
 const n=k=>asks.asks.filter(a=>a.status===k).length;
 const counts=h.match(/<p class="counts"[^>]*>[\s\S]*?<\/p>/g).map(p=>p.replace(/<[^>]+>/g,''));
 assert.equal(counts[0],`${asks.asks.length} asks · Done ${n('Done')} · In progress ${n('In progress')} · Needs you ${n('Needs you')}`);
 assert.equal(counts[1],`Unproved ${n('Unproved')} · Not started ${n('Not started')}`);
 assert.match(h,/A\. Everything you asked for/);assert.match(h,/B\. Every lane and who owns it/);assert.match(h,/C\. Needs you/);
 for(const c of ['#','Your ask','Owner','Lane','Status','Proof','Last update'])assert.ok(h.includes(`<th>${c}</th>`),c);
 assert.equal((h.match(/data-l="Your ask"/g)||[]).length,asks.asks.length);
 assert.equal((h.match(/data-l="What it does"/g)||[]).length,asks.lanes.length);
 assert.ok(asks.needs_you.length>=1&&asks.needs_you.length<=5);
 assert.ok(h.includes('fki-doctor'));
});
test('each status has its own color and every Done ask carries proof',()=>{
 const {env,asks}=run('');const h=env.asks.innerHTML;
 const cls={'Done':'st-done','In progress':'st-prog','Needs you':'st-need','Not started':'st-not','Unproved':'st-unp'};
 for(const [s,c] of Object.entries(cls))assert.ok(h.includes(`<span class="st ${c}">${s}</span>`),s);
 assert.equal(new Set(Object.values(cls)).size,5);
 for(const a of asks.asks){assert.ok(Object.keys(cls).includes(a.status),'status '+a.status);if(a.status==='Done')assert.ok((a.proof?.text||'').trim()||a.proof?.url,'Done without proof: #'+a.n)}
});
test('lane rows merge live board status and link to the project',()=>{
 const {env}=run('');const h=env.asks.innerHTML;
 assert.match(h,new RegExp(`<a class="lk" href="#project=${LANEP}">H1</a>`));
 const row=h.slice(h.indexOf(`#project=${LANEP}`));assert.match(row.slice(0,400),/st-stuck">Stuck/);
 assert.match(h,/not on the board yet/);
});
test('asks data carries no emails or phone numbers',()=>{
 const raw=fs.readFileSync('asks.json','utf8');
 assert.doesNotMatch(raw,/[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z]{2,}/);assert.doesNotMatch(raw,/\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}/);
});
test('R11: no KPI row shows more than 4 numbers',()=>{
 const {env}=run('#now');const h=env.now.innerHTML;
 const rows=h.split('<div class="kpis"').slice(1).map(r=>r.split('</div></div>')[0]);assert.ok(rows.length>=3);
 for(const r of rows)assert.ok((r.match(/<div class="kpi">/g)||[]).length<=4,'row with >4 tiles');
 const {env:e2}=run('');for(const p of e2.asks.innerHTML.match(/<p class="counts"[^>]*>[\s\S]*?<\/p>/g))assert.ok(((p.replace(/<[^>]+>/g,'')).match(/\d+/g)||[]).length<=4);
});
test('R11: device here-chips, blocker titles and CAIO project chips are real links',()=>{
 const {env}=run('#now');
 assert.match(env.devices.innerHTML,new RegExp(`<a class="chip" href="#agent=${AG}">`));
 assert.match(env.now.innerHTML,new RegExp(`<div class="card r"><h3><a class="lk" href="#agent=${AG}">Dash</a></h3>`));
 assert.match(env.caio.innerHTML,new RegExp(`<a class="chip" href="#project=${PJ}">🧭 Some Project</a>`));
 assert.doesNotMatch(env.devices.innerHTML+env.caio.innerHTML,/<span class="chip">/);
});
