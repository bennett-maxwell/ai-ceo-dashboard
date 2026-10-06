// "Agents" tab (#fleet): every working lane with route, live status, last check-in and project count; a card opens the
// lane's projects and a project opens goal, done test, sub-agents, first 3 tasks, ETA, needs-Bennett and latest proof (W24).
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');
const DASH='3edcf5514fd3812ea137d3ce41dafab3';
function run(hash='',mutate=()=>{}){
 const DateFixed=class extends Date{constructor(...a){super(...(a.length?a:['2026-10-06T03:00:00Z']))}static now(){return Date.parse('2026-10-06T03:00:00Z')}};
 const element=()=>({innerHTML:'',textContent:'',style:{},addEventListener(){},classList:{toggle(){}}});
 const ids=['asks','fleet','now','coceo','agents','devices','projects','tasks','caio','crons'],sections=ids.map(id=>({...element(),id}));
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
test('Agents tab sits directly after Your asks, which stays first and default',()=>{
 const html=fs.readFileSync('template.html','utf8');
 assert.match(html,/const TABS=\[\["asks","Your asks"\],\["fleet","Agents"\],/);
 assert.match(html,/<section id="asks"><\/section><section id="fleet"><\/section>/);
 const {env}=run('');assert.equal(S(env).tab,'asks');
 assert.match(env.tabs.innerHTML,/^<a href="#asks" data-k="asks" class="on">Your asks<\/a><a href="#fleet" data-k="fleet" class="">Agents<\/a>/);
 assert.equal(S(run('#fleet').env).tab,'fleet');
 for(const k of ['now','coceo','agents','devices','projects','tasks','caio','crons'])assert.match(html,new RegExp(`\\["${k}","`),'tab kept: '+k);
});
test('one card per lane with route, status, last check-in and project count; no invented check-ins',()=>{
 const {env,fleet}=run('#fleet');const h=env.fleet.innerHTML;
 assert.equal(fleet.lanes.length,9);assert.equal(fleet.projects.length,34);
 assert.equal((h.match(/class="fcard[^"]*" href="#fleet=/g)||[]).length,fleet.lanes.length);
 for(const l of fleet.lanes){
  const card=h.slice(h.indexOf(`data-lane="${l.key}"`));const one=card.slice(0,card.indexOf('</a>'));
  assert.ok(one.includes(l.lane.replace(/&/g,'&amp;')),'name '+l.lane);assert.ok(one.includes('Last check-in:'),'check-in line '+l.lane);
  const n=fleet.projects.filter(q=>q.lane===l.lane).length;assert.ok(one.includes(`${n} project${n===1?'':'s'} ›`),'count '+l.lane);
 }
 const dash=h.slice(h.indexOf('data-lane="dash"'));assert.match(dash.slice(0,dash.indexOf('</a>')),/Active now · Working[\s\S]*Last check-in: 3m ago · 2026-10-06T02:57:00Z/);
 const laya=h.slice(h.indexOf('data-lane="laya"'));assert.match(laya.slice(0,laya.indexOf('</a>')),/Not checked in yet[\s\S]*Last check-in: pending first tick/);
 // Dot has a board row in real data but not in this fixture: it must say pending, not borrow another seat's time.
 const dot=h.slice(h.indexOf('data-lane="dot"'));assert.match(dot.slice(0,dot.indexOf('</a>')),/pending first tick/);
 assert.match(h,/9 agents · 34 projects/);
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
 assert.match(h,/<span class="st st-need">Needs Bennett<\/span>/);assert.match(h,/No proof yet · pending first tick/);
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
