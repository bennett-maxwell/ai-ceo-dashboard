const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');
const PRIMARY=['3edcf5514fd381659d38cbb6d9a1a51a','3edcf5514fd38108b4f4e2d2e319ebe2','3edcf5514fd381c18e9ad31f16369f38','3edcf5514fd3815aa780ca4aff45c771','3edcf5514fd3812ea137d3ce41dafab3','3edcf5514fd381d7a91dd8a7bdcccb87'];
const EXTRA='3edcf5514fd3811ebc43c50933e8a73b';
const NAMES=['Rocky','Leo','Dot','Hank','Dash','Mack CLI'];
function run(at,complete=true,mutate=()=>{}){
 const DateFixed=class extends Date{constructor(...args){super(...(args.length?args:['2026-10-04T21:00:00Z']))}static now(){return Date.parse('2026-10-04T21:00:00Z')}};
 const element=()=>({innerHTML:'',textContent:'',style:{},value:'',addEventListener(){},classList:{toggle(){}}});
 const ids=['now','coceo','agents','devices','projects','tasks','caio','aiceo','crons'],sections=ids.map(id=>({...element(),id}));
 const env={Date:DateFixed,URL,console,location:{href:'https://example.com/#agents',hash:'#agents',replace(){}},history:{replaceState(){}},document:{hidden:false,querySelectorAll:s=>s==='section'?sections:[],addEventListener(){}},setInterval:(f,ms)=>env.interval=ms,fetch:async()=>({ok:false}),sessionStorage:{getItem(){return null},setItem(){}}};
 ids.forEach((id,i)=>env[id]=sections[i]);['tabs','companies','fresh','clock','search'].forEach(id=>env[id]=element());
 const data={primary_agents:PRIMARY,agents:[...PRIMARY,EXTRA].map((url,i)=>({url,Agent:i===6?'Cursor CEO':NAMES[i],Projects:[],Device:[]})),devices:[],projects:[],checkins:[],report_coverage:{exhaustive:complete,unique_rows:230,unlinked_rows:1,per_agent:{}}};
 PRIMARY.forEach(id=>data.report_coverage.per_agent[id]={agent_id:id,included:true,exhaustive:complete,matching_rows:0,latest:null});
 const logged=Date.parse(at)<Date.parse('2026-10-04T20:59:30Z')?'2026-10-04T19:29:30Z':'2026-10-04T20:59:30Z';
 data.report_coverage.per_agent[PRIMARY[0]].latest={url:'rocky-row',Agent:[PRIMARY[0]],Logged:logged,Time:'2026-10-04T20:59:00Z',Device:[],Project:[],'Check-in':'Rocky · 14:59 MT'};
 data.report_coverage.per_agent[PRIMARY[0]].matching_rows=1;
 data.report_coverage.per_agent[PRIMARY[4]].latest={url:'dash-old',Agent:[PRIMARY[4]],Logged:'2026-10-02T23:10:00Z',Time:'2026-10-02T23:09:00Z',Device:[],Project:[]};
 data.report_coverage.per_agent[PRIMARY[4]].matching_rows=1;
 data.report_coverage.per_agent[EXTRA]={agent_id:EXTRA,included:true,exhaustive:complete,matching_rows:1,latest:{url:'extra-row',Agent:[EXTRA],Logged:'2026-10-04T20:59:30Z',Time:'2026-10-04T20:59:00Z'}};
 mutate(data);
 let source=fs.readFileSync('template.html','utf8').replace('__REPORT_STATUS__',fs.readFileSync('report_status.js','utf8')).replace('__AT__',at).replace('__SNAP__',JSON.stringify(data));
 const script=source.match(/<script>([\s\S]*?)<\/script>/)[1];vm.createContext(env);vm.runInContext(script,env);return env;
}
test('stale full rendered board uses unavailable counts, not zero alive',()=>{
 const env=run('2026-10-04T20:29:35Z');assert.match(env.now.innerHTML,/Live status unavailable/);assert.match(env.now.innerHTML,/>–<\/b>/);assert.doesNotMatch(env.now.innerHTML,/agents alive|dead or blocked|never checked in/i);assert.equal(env.interval,60000);
 assert.match(env.agents.innerHTML,/Logged \(server\)/);assert.match(env.agents.innerHTML,/Time \(worker\)/);
 assert.match(env.clock.textContent,/Updated/);
});
test('fresh rendered board retains primary denominator and recovered history',()=>{
 const env=run('2026-10-04T21:00:00Z');assert.match(env.agents.innerHTML,/Primary worker seats \(6\)/);assert.match(env.agents.innerHTML,/Additional registered agents \(1\)/);
 assert.match(env.now.innerHTML,/>1<\/b><span>check-ins since last build/);assert.match(env.now.innerHTML,/>1<\/b><span>recent server receipts/);
 assert.match(env.agents.innerHTML,/2026-10-02T23:10:00Z/);assert.match(env.agents.innerHTML,/Never observed as of exhaustive/);assert.match(env.agents.innerHTML,/Unknown project\/task relation/);
 assert.match(env.agents.innerHTML,/Rocky/);assert.match(env.agents.innerHTML,/Leo/);assert.match(env.agents.innerHTML,/Dot/);assert.match(env.agents.innerHTML,/Hank/);
});
test('incomplete source coverage cannot become authoritative zero',()=>{
 const env=run('2026-10-04T21:00:00Z',false);assert.match(env.now.innerHTML,/source coverage is incomplete/);assert.match(env.now.innerHTML,/>–<\/b>/);assert.match(env.agents.innerHTML,/Not included — coverage unknown/);
});
test('future Co-CEO receipt has anomaly text and never a green card',()=>{
 const env=run('2026-10-04T21:00:00Z',true,data=>data.coceo=[{Author:[PRIMARY[2]],Logged:'2026-10-05T03:00:00Z'}]);
 assert.doesNotMatch(env.coceo.innerHTML,/<div class="card g"><h3>Dot/);
 assert.match(env.coceo.innerHTML,/Invalid server receipt/);
});
test('stale or incomplete device evidence is unavailable rather than absence',()=>{
 for(const [at,complete] of [['2026-10-04T20:29:35Z',true],['2026-10-04T21:00:00Z',false]]){
  const env=run(at,complete,data=>data.devices=[{url:'device',Device:'Studio'}]);
  assert.match(env.devices.innerHTML,/Live status unavailable/);
  assert.doesNotMatch(env.devices.innerHTML,/No recent validated receipt/);
 }
});
test('snapshot older than thirty minutes cannot show current-zero counters',()=>{
 for(const at of ['2026-10-04T20:29:59.999Z','2026-10-04T20:23:00Z']){
  const env=run(at);assert.match(env.now.innerHTML,/Live status unavailable/);
  assert.match(env.now.innerHTML,/>–<\/b>/);assert.doesNotMatch(env.now.innerHTML,/>0<\/b><span>check-ins since last build/);
  assert.match(env.fresh.textContent,/STALE/);
  assert.match(env.clock.textContent,/Updated/);
 }
});
test('project progress is reported and unverified while values stay intact',()=>{
 const env=run('2026-10-04T21:00:00Z',true,data=>data.projects=[{url:'p',Project:'Test',Company:'Test','Progress %':0},{url:'q',Project:'Unknown','Progress %':null}]);
 assert.match(env.now.innerHTML,/>0%<\/b><span>reported project progress · unverified/);
 assert.doesNotMatch(env.now.innerHTML,/verified project/);assert.match(env.projects.innerHTML,/no plan yet/);
 assert.match(env.projects.innerHTML,/Priority/);assert.match(env.projects.innerHTML,/North Star/);
});

test('all registered agents land in buckets that add up, and silent clocked-out seats count late',()=>{
 const env=run('2026-10-04T21:00:00Z',true,data=>{
  data.report_coverage.per_agent[PRIMARY[5]].latest={url:'clk',Agent:[PRIMARY[5]],Logged:'2026-10-01T20:00:30Z',Time:'2026-10-01T20:00:00Z',Status:'CLOCK-OUT'};
  data.counts={agents:7,tasks_total:56,tasks_open:47,checkins:1215,checkins_feed_rows:300};
 });
 const box=env.now.innerHTML.slice(env.now.innerHTML.indexOf('id="buckets"'));
 const nums=[...box.matchAll(/<b[^>]*>(\d+)<\/b>/g)].slice(0,7).map(m=>+m[1]);
 assert.match(env.now.innerHTML,/All registered agents \(7, retired excluded\)/);
 assert.equal(nums.length,7);assert.equal(nums.reduce((a,b)=>a+b,0),7);
 assert.ok(nums[3]>=1,'clocked-out seat silent 3 days must count late');
 assert.match(env.now.innerHTML,/Buckets add up to 7/);
 assert.match(env.now.innerHTML,/1215/);assert.match(env.tasks.innerHTML,/56 rows read from Notion/);
});
test('collapsed heartbeat rows show their repeat count',()=>{
 const env=run('2026-10-04T21:00:00Z',true,data=>{data.checkins=[{url:'c1',Agent:[PRIMARY[0]],Logged:'2026-10-04T20:59:30Z',Time:'2026-10-04T20:59:00Z','Doing now':'Heartbeat',_repeats:12,_first_logged:'2026-10-04T20:30:00Z'}];data.report_coverage.collapsed_repeats=11});
 assert.match(env.now.innerHTML+env.agents.innerHTML,/×12 identical reports since 2026-10-04T20:30:00Z/);
});
test('ten-minute publication age can still show check-ins since that build',()=>{
 const env=run('2026-10-04T20:50:00Z');
 assert.match(env.now.innerHTML,/check-ins since last build/);
 assert.doesNotMatch(env.now.innerHTML,/cannot substantiate current three-minute/);
 assert.match(env.clock.textContent,/Updated 10 min ago/);
});
test('AI CEO unavailable coverage is visible on CAIO and the AI CEO tab',()=>{
 const env=run('2026-10-04T21:00:00Z',true,data=>{data.aiceo=[];data.aiceo_coverage={state:'unavailable',exhaustive:false,public_rows:null};data.aiceo_status='Historical AI CEO coverage not readable with the build connection (HTTP 404); not published.'});
 assert.match(env.caio.innerHTML,/source coverage unavailable/);
 assert.match(env.caio.innerHTML,/zero rows must not be interpreted as an empty source/);
 assert.match(env.caio.innerHTML,/HTTP 404/);
 assert.match(env.caio.innerHTML,/Historical AI CEO coverage/);
 assert.match(env.caio.innerHTML,/legacy Plan\/Audit\/Run history, separate from the current command-center hub/);
 assert.match(env.aiceo.innerHTML,/Type, Status, Seat, Graded by, Date/);
 assert.match(env.aiceo.innerHTML,/HTTP 404/);
});
test('Needs Bennett cards open the source Notion row and finished work is self-reported',()=>{
 const need='bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb1';
 const env=run('2026-10-04T21:00:00Z',true,data=>{
  data.needs_bennett=[{url:need,Agent:[PRIMARY[0]],'Blocker question':'Need a grader','Doing now':'blocked',Logged:'2026-10-04T20:59:00Z',need:'blocker'}];
  data.checkins=[{url:'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa3',Agent:[PRIMARY[0]],Status:'FINISHED','Doing now':'lane closed',_finish:'self-reported'}];
 });
 assert.match(env.now.innerHTML,/Needs Bennett/);
 assert.match(env.now.innerHTML,/Need a grader/);
 assert.match(env.now.innerHTML,new RegExp('app.notion.com/'+need));
 assert.match(env.now.innerHTML,/self-reported/);
});
test('search filters projects by agent and device and sorts green first',()=>{
 const green='aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa1',red='aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa2';
 const env=run('2026-10-04T21:00:00Z',true,data=>{
  data.projects=[{url:red,Project:'Red Lane',Company:'Advaita AI','Progress %':10,'Finish condition':'ship'},{url:green,Project:'Green Lane',Company:'Advaita AI','Progress %':90,'Finish condition':'done'}];
  data.checkins=[{url:'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa4',Agent:[PRIMARY[0]],Project:[green],Device:[],Logged:'2026-10-04T20:59:00Z','Doing now':'on green'}];
  data.devices=[{url:'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5',Device:'MacBook'}];
 });
 const greenAt=env.projects.innerHTML.indexOf('Green Lane'),redAt=env.projects.innerHTML.indexOf('Red Lane');
 assert.ok(greenAt>=0&&redAt>greenAt,'green project must sort above red');
 env.S.q='Rocky';env.render();
 assert.match(env.projects.innerHTML,/Green Lane/);
 assert.doesNotMatch(env.projects.innerHTML,/Red Lane/);
});
