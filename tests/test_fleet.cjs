// "Agents" tab (#fleet): every working lane with route, live status, last check-in and project count; a card opens the
// lane's projects and a project opens goal, done test, sub-agents, first 3 tasks, ETA, needs-Bennett and latest proof (W24).
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');
const DASH='3edcf5514fd3812ea137d3ce41dafab3';
function run(hash='',mutate=()=>{}){
 const DateFixed=class extends Date{constructor(...a){super(...(a.length?a:['2026-10-06T03:00:00Z']))}static now(){return Date.parse('2026-10-06T03:00:00Z')}};
 const element=()=>({innerHTML:'',textContent:'',style:{},addEventListener(){},classList:{toggle(){}}});
 const ids=['grok','dash','dot','asks','fleet','now','coceo','agents','devices','projects','tasks','caio','crons'],sections=ids.map(id=>({...element(),id}));
 const env={Date:DateFixed,URL,console,location:{href:'https://example.com/'+hash,hash,replace(){}},history:{replaceState(){}},document:{hidden:false,querySelectorAll:s=>s==='section'?sections:[],addEventListener(){}},setInterval(){},fetch:async()=>({ok:false}),sessionStorage:{getItem(){return null},setItem(){}}};
 ids.forEach((id,i)=>env[id]=sections[i]);['tabs','companies','fresh'].forEach(id=>env[id]=element());
 const fleet=JSON.parse(fs.readFileSync('agents48.json','utf8'));
 const data={primary_agents:[DASH],agents:[{url:DASH,Agent:'Dash',Projects:[],Device:[]}],devices:[],projects:[],checkins:[],
  report_coverage:{exhaustive:true,unique_rows:1,per_agent:{[DASH]:{agent_id:DASH,included:true,exhaustive:true,matching_rows:1,latest:{url:'r',Agent:[DASH],Logged:'2026-10-06T02:57:00Z',Time:'2026-10-06T02:57:00Z',Status:'WORKING',Device:[],Project:[]}}}},
  fleet};
 mutate(data);
 const src=fs.readFileSync('template.html','utf8').replace('__REPORT_STATUS__',fs.readFileSync('report_status.js','utf8')).replace('__AT__','2026-10-06T02:58:00Z').replace('__SNAP__',JSON.stringify(data));
 vm.createContext(env);vm.runInContext(src.match(/<script>([\s\S]*?)<\/script>/)[1],env);return {env,fleet};
}
const S=env=>vm.runInContext('S',env);
test('Grok, Dash, Dot are the first three tabs; Agents sits directly after Your asks, which stays the default view',()=>{
 const html=fs.readFileSync('template.html','utf8');
 assert.match(html,/const TABS=\[\["grok","Grok"\],\["dash","Dash"\],\["dot","Dot"\],\["asks","Your asks"\],\["fleet","Agents"\],/);
 assert.match(html,/<section id="grok"><\/section><section id="dash"><\/section><section id="dot"><\/section><section id="asks"><\/section><section id="fleet"><\/section>/);
 const {env}=run('');assert.equal(S(env).tab,'asks');
 assert.match(env.tabs.innerHTML,/^<a href="#grok" data-k="grok" class="">Grok<\/a><a href="#dash" data-k="dash" class="">Dash<\/a><a href="#dot" data-k="dot" class="">Dot<\/a><a href="#asks" data-k="asks" class="on">Your asks<\/a><a href="#fleet" data-k="fleet" class="">Agents<\/a>/);
 assert.equal(S(run('#fleet').env).tab,'fleet');
 for(const k of ['now','coceo','agents','devices','projects','tasks','caio','crons'])assert.match(html,new RegExp(`\\["${k}","`),'tab kept: '+k);
});
test('one card per lane with route, status, last check-in and project count; no invented check-ins',()=>{
 const {env,fleet}=run('#fleet');const h=env.fleet.innerHTML;
 assert.equal(fleet.lanes.length,10);assert.equal(fleet.projects.length,34);
 assert.equal((h.match(/class="fcard[^"]*" href="#fleet=/g)||[]).length,fleet.lanes.length);
 for(const l of fleet.lanes){
  const card=h.slice(h.indexOf(`data-lane="${l.key}"`));const one=card.slice(0,card.indexOf('</a>'));
  assert.ok(one.includes(l.lane.replace(/&/g,'&amp;')),'name '+l.lane);assert.ok(one.includes('Last check-in:'),'check-in line '+l.lane);
  const n=fleet.projects.filter(q=>q.lane===l.lane).length;assert.ok(one.includes(`${n} project${n===1?'':'s'} ›`),'count '+l.lane);
 }
 const dash=h.slice(h.indexOf('data-lane="dash"'));assert.match(dash.slice(0,dash.indexOf('</a>')),/Active now · Working[\s\S]*Last check-in: 3m ago · <span class="ts">2026-10-06T02:57:00Z<\/span>/);
 const laya=h.slice(h.indexOf('data-lane="laya"'));assert.match(laya.slice(0,laya.indexOf('</a>')),/Not checked in yet[\s\S]*Last check-in: pending first tick/);
 // Dot has a board row in real data but not in this fixture: it must say pending, not borrow another seat's time.
 const dot=h.slice(h.indexOf('data-lane="dot"'));assert.match(dot.slice(0,dot.indexOf('</a>')),/pending first tick/);
 assert.match(h,/10 agents · 34 projects/);
});
test('a lane card opens that lane\'s projects, each a big link to its detail',()=>{
 const {env,fleet}=run('#fleet=grok-a');const h=env.fleet.innerHTML;assert.equal(S(env).tab,'fleet');
 const mine=fleet.projects.filter(q=>q.lane==='Grok A');assert.ok(mine.length>=3);
 assert.match(h,/href="#fleet">‹ All agents<\/a>/);
 for(const q of mine)assert.ok(h.includes(`href="#fleet=grok-a/${q.id}"`),q.id);
 assert.equal((h.match(/class="fcard"/g)||[]).length,mine.length);
});
test('a project shows goal, done test, sub-agents, first 3 tasks, ETA, needs-Bennett and latest proof',()=>{
 const {env,fleet}=run('#fleet=grok-b/GB4');const h=env.fleet.innerHTML,q=fleet.projects.find(x=>x.id==='GB4');
 for(const t of ['Goal','Done when','Sub-agents','First 3 tasks','ETA','Needs Bennett','Latest proof'])assert.ok(h.includes(`<h3>${t}`),t);
 const e=s=>s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
 assert.ok(h.includes(e(q.goal)));assert.ok(h.includes(e(q.done_test)));
 for(const s of q.subagents)assert.ok(h.includes(`<li>${e(s)}</li>`),s);
 assert.equal((h.split('<h3>First 3 tasks</h3>')[1].split('</ol>')[0].match(/<li>/g)||[]).length,3);
 assert.match(h,new RegExp(`About ${q.eta_hours} hours · by 2026-10-0\\d \\d\\d:\\d\\d UTC`));
 assert.match(h,/<span class="st st-need">Needs Bennett<\/span>/);assert.match(h,/None yet · no check-in names GB4/);
 const plain=run('#fleet=grok-a/GA1').env.fleet.innerHTML;assert.match(plain,/Nothing in this project needs you/);assert.doesNotMatch(plain,/st-need">Needs Bennett/);
 const withProof=run('#fleet=grok-a/GA1',d=>{d.fleet.projects.find(x=>x.id==='GA1').latest_proof={text:'run 1',url:'https://example.com/r1'}}).env.fleet.innerHTML;
 assert.match(withProof,/<a class="ext" href="https:\/\/example.com\/r1"[^>]*>run 1<\/a>/);
});
test('agents data carries no emails, phone numbers, legal matter or token-shaped words',()=>{
 const raw=fs.readFileSync('agents48.json','utf8');
 assert.doesNotMatch(raw,/[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z]{2,}/);assert.doesNotMatch(raw,/\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}/);
 assert.doesNotMatch(raw,/legal|lawsuit|attorney|court/i);assert.doesNotMatch(raw,/s[k]-[A-Za-z0-9_-]{8,}/);
});
test('phone layout: cards and buttons are big tap targets and long routes wrap',()=>{
 const html=fs.readFileSync('template.html','utf8');
 assert.match(html,/\.fcard\{[^}]*min-height:64px[^}]*padding:16px[^}]*overflow-wrap:anywhere/);
 assert.match(html,/\.fbtn\{[^}]*min-height:44px/);
});

test('T23: Grok, Dash and Dot tabs show only their own lanes, live status and projects; Agents grid lists them first',()=>{
 const {env,fleet}=run('#dash');assert.equal(S(env).tab,'dash');
 const d=env.dash.innerHTML;assert.match(d,/data-lane="dash"/);assert.doesNotMatch(d,/data-lane="(dot|grok-a|laya)"/);
 assert.match(d,/Active now · Working[\s\S]*Last check-in: 3m ago · <span class="ts">2026-10-06T02:57:00Z<\/span>/);
 const nd=fleet.projects.filter(q=>q.lane==='Dash').length;assert.equal((d.match(/href="#fleet=dash\//g)||[]).length,nd);
 const g=run('#grok').env.grok.innerHTML;const gk=fleet.lanes.filter(l=>/^grok/.test(l.key));assert.ok(gk.length>0);
 for(const l of gk)assert.ok(g.includes(`data-lane="${l.key}"`),'grok lane '+l.key);assert.doesNotMatch(g,/data-lane="(dash|dot)"/);
 const t=run('#dot').env.dot.innerHTML;assert.match(t,/data-lane="dot"/);assert.match(t,/Last check-in: pending first tick/);
 const h=run('#fleet').env.fleet.innerHTML,order=[...h.matchAll(/data-lane="([a-z0-9-]+)"/g)].map(m=>m[1]);
 const rank=k=>/^grok/.test(k)?0:k==='dash'?1:k==='dot'?2:3;
 assert.deepEqual(order,[...order].sort((a,b)=>rank(a)-rank(b)));assert.equal(order.length,fleet.lanes.length);
 assert.equal(order.indexOf('dash')+1,order.indexOf('dot'));
});

// W43 (W29 fixes 1, 2, 4): Grok lanes are threads of the live Grok Web row, never the retired Heavy 4.7 rows.
const GW='3f1cf5514fd38132b072c4e7cc220cff',GA='3f1cf5514fd38106b7f7d96897094996';
const grokData=d=>{
 d.agents.push({url:GW,Agent:'Grok Web',Status:'🟡 Working',Projects:[],Device:[]},{url:GA,Agent:'Grok A (Heavy 4.7)',Status:'⛔ Retired',Projects:[],Device:[]});
 const row=(id,at,doing)=>({url:'r'+at,Agent:[id],Logged:at,Time:at,Status:'WORKING',Device:[],Project:[],'Doing now':doing});
 d.report_coverage.per_agent[GW]={agent_id:GW,included:true,exhaustive:true,matching_rows:2,latest:row(GW,'2026-10-06T02:50:00Z','A3 rows written')};
 d.report_coverage.per_agent[GA]={agent_id:GA,included:true,exhaustive:true,matching_rows:1,latest:row(GA,'2026-10-06T02:59:00Z','retired row write')};
 d.checkins=[row(GW,'2026-10-06T02:50:00Z','A3 rows written'),row(GW,'2026-10-06T02:40:00Z','B10 labels written'),row(GA,'2026-10-06T02:59:00Z','retired row write')];
};
test('Grok A/B/C/KB/E lanes read the live Grok Web row, never a retired Heavy 4.7 row',()=>{
 const raw=JSON.parse(fs.readFileSync('agents48.json','utf8'));
 const gk=raw.lanes.filter(l=>/^grok/.test(l.key));assert.deepEqual(gk.map(l=>l.thread),['A','B','C','KB','E']);
 for(const l of gk){assert.equal(l.board_agent,'Grok Web',l.key);assert.ok(l.thread_match,l.key)}
 assert.doesNotMatch(JSON.stringify(raw.lanes.map(l=>l.board_agent)),/Heavy 4\.7/);
 assert.deepEqual(raw.lanes.slice(0,7).map(l=>l.key),['grok-a','grok-b','grok-c','grok-kb','grok-e','dash','dot']);
 const h=run('#fleet',grokData).env.fleet.innerHTML,card=k=>{const c=h.slice(h.indexOf(`data-lane="${k}"`));return c.slice(0,c.indexOf('</a>'))};
 assert.match(card('grok-a'),/Last check-in: 10m ago · <span class="ts">2026-10-06T02:50:00Z<\/span>[\s\S]*tagged thread A/);assert.doesNotMatch(card('grok-a'),/02:59:00Z/);
 assert.match(card('grok-b'),/Last check-in: 20m ago · <span class="ts">2026-10-06T02:40:00Z<\/span>[\s\S]*tagged thread B/);
 assert.match(card('grok-e'),/Last check-in: 10m ago[\s\S]*shared Grok Web row; no check-in tagged thread E yet/);
 // A lane still pointed at a retired row says so instead of showing the retired row's time.
 const r=run('#fleet',d=>{grokData(d);d.fleet.lanes[0].board_agent='Grok A (Heavy 4.7)'}).env.fleet.innerHTML;
 const ra=r.slice(r.indexOf('data-lane="grok-a"'));assert.match(ra.slice(0,ra.indexOf('</a>')),/Retired board row · no live source/);
 assert.doesNotMatch(ra.slice(0,ra.indexOf('</a>')),/02:59:00Z/);
});
test('every one of the 34 projects shows status, hours left and latest proof (or says none yet)',()=>{
 const raw=JSON.parse(fs.readFileSync('agents48.json','utf8'));assert.equal(raw.projects.length,34);
 for(const q of raw.projects){assert.ok(String(q.status||'').trim(),'status '+q.id);assert.equal(typeof q.hours_left,'number','hours_left '+q.id);assert.ok('latest_proof' in q,'latest_proof '+q.id)}
 assert.ok(Date.parse(raw.window_end)>Date.parse(raw.updated));
 const {env,fleet}=run('#fleet=grok-a');const h=env.fleet.innerHTML,n=fleet.projects.filter(q=>q.lane==='Grok A').length;
 assert.equal((h.match(/Status: /g)||[]).length,n);assert.equal((h.match(/\d+\.\d h left/g)||[]).length,n);assert.equal((h.match(/Latest proof: /g)||[]).length,n);
 const d=run('#fleet=grok-a/GA1',x=>{const q=x.fleet.projects.find(p=>p.id==='GA1');q.status='Working · 2 check-ins';q.latest_proof={text:'Grok Web · 2026-10-06T02:50:00Z',url:'https://example.com/p'}}).env.fleet.innerHTML;
 assert.match(d,/<h3>Status<\/h3><p>Working · 2 check-ins<\/p>/);assert.match(d,/47\.9 h left in the 48-hour window/);assert.match(d,/href="https:\/\/example.com\/p"/);
 const g=run('#grok').env.grok.innerHTML;assert.match(g,/Status: Planned · no check-in names GA1 yet/);
});
