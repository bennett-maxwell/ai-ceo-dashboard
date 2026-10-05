const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');
const PRIMARY=['3edcf5514fd3812ea137d3ce41dafab3','3edcf5514fd381d7a91dd8a7bdcccb87','3edcf5514fd3816fb3a2cc308727bde6','3edcf5514fd38131bd00e1080bf6d826','3edcf5514fd381759f9bee1cfade7819','3edcf5514fd381ecb7a7f9c2f8411b1d'];
const DOT='3edcf5514fd381c18e9ad31f16369f38';
function run(at,complete=true,mutate=()=>{}){
 const DateFixed=class extends Date{constructor(...args){super(...(args.length?args:['2026-10-04T21:00:00Z']))}static now(){return Date.parse('2026-10-04T21:00:00Z')}};
 const element=()=>({innerHTML:'',textContent:'',style:{},addEventListener(){},classList:{toggle(){}}});
 const ids=['now','coceo','agents','devices','projects','tasks','caio','crons'],sections=ids.map(id=>({...element(),id}));
 const env={Date:DateFixed,URL,console,location:{href:'https://example.com/#agents',hash:'#agents',replace(){}},history:{replaceState(){}},document:{hidden:false,querySelectorAll:s=>s==='section'?sections:[],addEventListener(){}},setInterval:(f,ms)=>env.interval=ms,fetch:async()=>({ok:false}),sessionStorage:{getItem(){return null},setItem(){}}};
 ids.forEach((id,i)=>env[id]=sections[i]);['tabs','companies','fresh'].forEach(id=>env[id]=element());
 const data={primary_agents:PRIMARY,agents:[...PRIMARY,DOT].map((url,i)=>({url,Agent:i===6?'Dot':i===0?'Dash':i===4?'Grok ST':'Seat'+i,Projects:[],Device:[]})),devices:[],projects:[],checkins:[],report_coverage:{exhaustive:complete,unique_rows:230,unlinked_rows:1,per_agent:{}}};
 PRIMARY.forEach(id=>data.report_coverage.per_agent[id]={agent_id:id,included:true,exhaustive:complete,matching_rows:0,latest:null});
 const logged=Date.parse(at)<Date.parse('2026-10-04T20:59:30Z')?'2026-10-04T19:29:30Z':'2026-10-04T20:59:30Z';
 data.report_coverage.per_agent[PRIMARY[0]].latest={url:'dash-row',Agent:[PRIMARY[0]],Logged:logged,Time:'2026-10-05T02:59:00Z',Device:[],Project:[]};
 data.report_coverage.per_agent[PRIMARY[4]].latest={url:'grok-row',Agent:[PRIMARY[4]],Logged:'2026-10-02T23:10:00Z',Time:'2026-10-02T23:09:00Z',Device:[],Project:[]};
 data.report_coverage.per_agent[DOT]={agent_id:DOT,included:true,exhaustive:complete,matching_rows:1,latest:{url:'dot-row',Agent:[DOT],Logged:'2026-10-04T20:59:30Z',Time:'2026-10-04T20:59:00Z'}};
 mutate(data);
 let source=fs.readFileSync('template.html','utf8').replace('__REPORT_STATUS__',fs.readFileSync('report_status.js','utf8')).replace('__AT__',at).replace('__SNAP__',JSON.stringify(data));
 const script=source.match(/<script>([\s\S]*?)<\/script>/)[1];vm.createContext(env);vm.runInContext(script,env);return env;
}
test('stale full rendered board uses unavailable counts, not zero alive',()=>{
 const env=run('2026-10-04T19:30:35Z');assert.match(env.now.innerHTML,/Live status unavailable/);assert.match(env.now.innerHTML,/>–<\/b>/);assert.doesNotMatch(env.now.innerHTML,/agents alive|dead or blocked|never checked in/i);assert.equal(env.interval,60000);
 assert.match(env.agents.innerHTML,/Logged \(server\)/);assert.match(env.agents.innerHTML,/Time \(worker\)/);assert.match(env.agents.innerHTML,/future — unverified/);
});
test('fresh rendered board retains primary denominator and recovered Grok history',()=>{
 const env=run('2026-10-04T21:00:00Z');assert.match(env.agents.innerHTML,/Primary worker seats \(6\)/);assert.match(env.agents.innerHTML,/Additional registered agents \(1\)/);
 assert.match(env.now.innerHTML,/>0<\/b><span>validated worker reports/);assert.match(env.now.innerHTML,/>1<\/b><span>recent server receipts/);
 assert.match(env.agents.innerHTML,/2026-10-02T23:10:00Z/);assert.match(env.agents.innerHTML,/Never observed as of exhaustive/);assert.match(env.agents.innerHTML,/Unknown project\/task relation/);
});
test('incomplete source coverage cannot become authoritative zero',()=>{
 const env=run('2026-10-04T21:00:00Z',false);assert.match(env.now.innerHTML,/source coverage is incomplete/);assert.match(env.now.innerHTML,/>–<\/b>/);assert.match(env.agents.innerHTML,/Not included — coverage unknown/);
});
test('future Co-CEO receipt has anomaly text and never a green card',()=>{
 const env=run('2026-10-04T21:00:00Z',true,data=>data.coceo=[{Author:[DOT],Logged:'2026-10-05T03:00:00Z'}]);
 assert.doesNotMatch(env.coceo.innerHTML,/<div class="card g"><h3>Dot/);
 assert.match(env.coceo.innerHTML,/Invalid server receipt/);
});
test('stale or incomplete device evidence is unavailable rather than absence',()=>{
 for(const [at,complete] of [['2026-10-04T19:30:35Z',true],['2026-10-04T21:00:00Z',false]]){
  const env=run(at,complete,data=>data.devices=[{url:'device',Device:'Studio'}]);
  assert.match(env.devices.innerHTML,/Live status unavailable/);
  assert.doesNotMatch(env.devices.innerHTML,/No recent validated receipt/);
 }
});
test('snapshot older than thirty minutes cannot show current-zero counters',()=>{
 for(const at of ['2026-10-04T20:29:59.999Z','2026-10-04T20:23:00Z']){
  const env=run(at);assert.match(env.now.innerHTML,/Live status unavailable/);
  assert.match(env.now.innerHTML,/>–<\/b>/);assert.doesNotMatch(env.now.innerHTML,/>0<\/b><span>validated worker reports/);
  assert.match(env.fresh.textContent,/STALE/);
 }
});
test('project progress is reported and unverified while values stay intact',()=>{
 const env=run('2026-10-04T21:00:00Z',true,data=>data.projects=[{url:'p',Project:'Test',Company:'Test','Progress %':0},{url:'q',Project:'Unknown','Progress %':null}]);
 assert.match(env.now.innerHTML,/>0%<\/b><span>reported project progress · unverified/);
 assert.doesNotMatch(env.now.innerHTML,/verified project/);assert.match(env.projects.innerHTML,/no plan yet/);
});

test('all registered agents land in buckets that add up, and silent clocked-out seats count late',()=>{
 const env=run('2026-10-04T21:00:00Z',true,data=>{
  data.report_coverage.per_agent[PRIMARY[1]].latest={url:'clk',Agent:[PRIMARY[1]],Logged:'2026-10-01T20:00:30Z',Time:'2026-10-01T20:00:00Z',Status:'CLOCK-OUT'};
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
