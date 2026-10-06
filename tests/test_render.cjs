const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');
// Primary seats per build.py PRIMARY_AGENT_IDS (Agents-DB ids checked 2026-10-06): Dash, Dot, Hank, Mack.
const DASH='3edcf5514fd3812ea137d3ce41dafab3',DOT='3edcf5514fd381c18e9ad31f16369f38',HANK='3edcf5514fd3815aa780ca4aff45c771',MACK='3edcf5514fd381d7a91dd8a7bdcccb87';
const GRANT='3edcf5514fd38131bd00e1080bf6d826',GROKST='3edcf5514fd381759f9bee1cfade7819';
const PRIMARY=[DASH,DOT,HANK,MACK];
const PROJ='aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa1',PROJ2='aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa2',DEV='bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb1';
function run(at,complete=true,mutate=()=>{}){
 const DateFixed=class extends Date{constructor(...args){super(...(args.length?args:['2026-10-04T21:00:00Z']))}static now(){return Date.parse('2026-10-04T21:00:00Z')}};
 const element=()=>({innerHTML:'',textContent:'',style:{},addEventListener(){},classList:{toggle(){}}});
 const ids=['asks','now','coceo','agents','devices','projects','tasks','caio','crons'],sections=ids.map(id=>({...element(),id}));
 const env={Date:DateFixed,URL,console,location:{href:'https://example.com/#agents',hash:'#agents',replace(){}},history:{replaceState(){}},document:{hidden:false,querySelectorAll:s=>s==='section'?sections:[],addEventListener(){}},setInterval:(f,ms)=>env.interval=ms,fetch:async()=>({ok:false}),sessionStorage:{getItem(){return null},setItem(){}}};
 ids.forEach((id,i)=>env[id]=sections[i]);['tabs','companies','fresh'].forEach(id=>env[id]=element());
 const data={primary_agents:PRIMARY,agents:[[DASH,'Dash'],[DOT,'Dot'],[HANK,'Hank'],[MACK,'Claude MB CLI'],[GRANT,'Grok MB (Grant)'],[GROKST,'Grok ST','⛔ Retired']].map(([url,Agent,Status])=>({url,Agent,Status,Projects:[],Device:[]})),devices:[],projects:[],checkins:[],report_coverage:{exhaustive:complete,unique_rows:230,unlinked_rows:1,per_agent:{}}};
 PRIMARY.forEach(id=>data.report_coverage.per_agent[id]={agent_id:id,included:true,exhaustive:complete,matching_rows:0,latest:null});
 const logged=Date.parse(at)<Date.parse('2026-10-04T20:59:30Z')?'2026-10-04T19:29:30Z':'2026-10-04T20:59:30Z';
 data.report_coverage.per_agent[PRIMARY[0]].latest={url:'dash-row',Agent:[PRIMARY[0]],Logged:logged,Time:'2026-10-05T02:59:00Z',Device:[],Project:[]};
 data.report_coverage.per_agent[GRANT]={agent_id:GRANT,included:true,exhaustive:complete,matching_rows:1,latest:{url:'grok-row',Agent:[GRANT],Logged:'2026-10-02T23:10:00Z',Time:'2026-10-02T23:09:00Z',Device:[],Project:[]}};
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
 const env=run('2026-10-04T21:00:00Z');assert.match(env.agents.innerHTML,/Primary worker seats \(4\)/);assert.match(env.agents.innerHTML,/Additional registered agents \(1\)/);
 assert.doesNotMatch(env.agents.innerHTML,/Grok ST/,'retired seats are never shown as registered workers');
 assert.match(env.now.innerHTML,/>1<\/b><span>validated worker reports/);assert.match(env.now.innerHTML,/>2<\/b><span>recent server receipts/);
 assert.match(env.agents.innerHTML,/2026-10-02T23:10:00Z/);assert.match(env.agents.innerHTML,/Never observed as of exhaustive/);
 assert.match(env.agents.innerHTML,/No project linked/);assert.match(env.agents.innerHTML,/No device linked/);assert.doesNotMatch(env.agents.innerHTML,/Unknown project\/task relation|Unknown device relation/);
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
  data.report_coverage.per_agent[MACK].latest={url:'clk',Agent:[MACK],Logged:'2026-10-01T20:00:30Z',Time:'2026-10-01T20:00:00Z',Status:'CLOCK-OUT'};
  data.counts={agents:6,tasks_total:56,tasks_open:47,checkins:1215,checkins_feed_rows:300};
 });
 const box=env.now.innerHTML.slice(env.now.innerHTML.indexOf('id="buckets"'));
 const nums=[...box.matchAll(/<b[^>]*>(\d+)<\/b>/g)].slice(0,7).map(m=>+m[1]);
 assert.match(env.now.innerHTML,/All registered agents \(5, retired excluded\)/);
 assert.equal(nums.length,7);assert.equal(nums.reduce((a,b)=>a+b,0),5);
 assert.ok(nums[3]>=1,'clocked-out seat silent 3 days must count late');
 assert.match(env.now.innerHTML,/Buckets add up to 5/);
 assert.match(env.now.innerHTML,/1215/);assert.match(env.tasks.innerHTML,/56 rows read from Notion/);
});
test('collapsed heartbeat rows show their repeat count',()=>{
 const env=run('2026-10-04T21:00:00Z',true,data=>{data.checkins=[{url:'c1',Agent:[PRIMARY[0]],Logged:'2026-10-04T20:59:30Z',Time:'2026-10-04T20:59:00Z','Doing now':'Heartbeat',_repeats:12,_first_logged:'2026-10-04T20:30:00Z'}];data.report_coverage.collapsed_repeats=11});
 assert.match(env.now.innerHTML+env.agents.innerHTML,/×12 identical reports since 2026-10-04T20:30:00Z/);
});
test('twenty-minute publication age cannot substantiate current six-minute counters',()=>{
 const env=run('2026-10-04T20:40:00Z');
 assert.match(env.now.innerHTML,/Live status unavailable: this snapshot is older than 15 minutes and cannot substantiate current 6-minute worker evidence/);
 assert.match(env.agents.innerHTML,/Live status unavailable/);
 assert.doesNotMatch(env.now.innerHTML,/>0<\/b><span>validated worker reports/);
 assert.match(env.now.innerHTML,/>–<\/b>/);
});
test('AI CEO unavailable coverage is visible and never presented as an empty board',()=>{
 const env=run('2026-10-04T21:00:00Z',true,data=>{data.aiceo=[];data.aiceo_coverage={state:'unavailable',exhaustive:false,public_rows:null};data.aiceo_status='AI CEO board not readable with the build token (HTTP 404); not published.'});
 assert.match(env.caio.innerHTML,/source coverage unavailable/);
 assert.match(env.caio.innerHTML,/zero rows must not be interpreted as an empty source/);
 assert.match(env.caio.innerHTML,/HTTP 404/);
 assert.match(env.caio.innerHTML,/Historical AI CEO coverage/);
 assert.match(env.caio.innerHTML,/legacy Plan\/Audit\/Run history, separate from the current command-center hub/);
});
test('C01 render: a 4-minute-old snapshot with a 1-minute-old Dot report keeps per-agent labels',()=>{
 const env=run('2026-10-04T20:56:00Z',true,data=>{data.report_coverage.per_agent[DOT].latest={url:'dot-row',Agent:[DOT],Logged:'2026-10-04T20:55:20Z',Time:'2026-10-04T20:55:00Z'}});
 assert.equal((env.agents.innerHTML.match(/Live status unavailable/g)||[]).length,0);
 assert.match(env.agents.innerHTML,/Fresh worker report/);
 assert.match(env.now.innerHTML,/>1<\/b><span>validated worker reports ≤6m/);
 assert.doesNotMatch(env.now.innerHTML,/Live status unavailable/);
});
test('C03 render: empty relations say No project linked / No device linked; linked relations show resolved names',()=>{
 const env=run('2026-10-04T21:00:00Z',true,data=>{
  data.projects=[{url:PROJ,Project:'AI CEO dashboard',Status:'Active'}];data.devices=[{url:DEV,Device:'Mac Studio'}];
  data.checkins=[{url:'c-linked',Agent:[DOT],Logged:'2026-10-04T20:59:30Z',Time:'2026-10-04T20:59:00Z',Status:'WORKING','Doing now':'linked row',Project:[PROJ],Device:[DEV]},
                 {url:'c-empty',Agent:[DASH],Logged:'2026-10-04T20:58:30Z',Time:'2026-10-04T20:58:00Z',Status:'WORKING','Doing now':'empty row',Project:[],Device:[]}];
  data.report_coverage.per_agent[DOT].latest=Object.assign({},data.checkins[0]);
 });
 const rows=env.now.innerHTML.split('<tr>');const linked=rows.find(r=>r.includes('linked row')),empty=rows.find(r=>r.includes('empty row'));
 assert.match(linked,new RegExp('<a class="lk" href="#project='+PROJ+'">AI CEO dashboard</a><br>Mac Studio'));assert.match(empty,/No project linked<br>No device linked/);
 const dot=env.agents.innerHTML.split('<div class="card').find(c=>c.includes('href="#agent='+DOT+'">Dot</a></h3>'));
 assert.match(dot,/🧭 AI CEO dashboard/);assert.match(dot,/💻 Mac Studio/);
 const hank=env.agents.innerHTML.split('<div class="card').find(c=>c.includes('href="#agent='+HANK+'">Hank</a></h3>'));
 assert.match(hank,/🧭 No project linked/);assert.match(hank,/💻 No device linked/);
 assert.doesNotMatch(env.now.innerHTML+env.agents.innerHTML,/Unknown project\/task relation|Unknown device relation/);
});
test('C03 render: projects show No status for a blank Status and the last linked check-in age or No check-in linked',()=>{
 const env=run('2026-10-04T21:00:00Z',true,data=>{
  data.projects=[{url:PROJ,Project:'Linked project',Status:''},{url:PROJ2,Project:'Unlinked project',Status:'Active'}];
  data.project_checkins={[PROJ]:{latest_logged:'2026-10-04T20:30:00Z',rows:3}};
 });
 const rows=env.projects.innerHTML.split('<tr>');const a=rows.find(r=>r.includes('Linked project')),b=rows.find(r=>r.includes('Unlinked project'));
 assert.match(a,/<td>No status<\/td>/);assert.match(a,/30m ago · 3 linked/);
 assert.match(b,/<td>Active<\/td>/);assert.match(b,/No check-in linked</);
 assert.match(env.projects.innerHTML,/<th>Status<\/th><th>Last linked check-in<\/th>/);
 const partial=run('2026-10-04T21:00:00Z',false,data=>{data.projects=[{url:PROJ2,Project:'Unlinked project'}];data.project_checkins={}});
 assert.match(partial.projects.innerHTML,/No check-in linked \(scan incomplete\)/);
 const old=run('2026-10-04T21:00:00Z',true,data=>{data.projects=[{url:PROJ2,Project:'Unlinked project'}]});
 assert.match(old.projects.innerHTML,/Check-in links not in this snapshot/);
});
test('C12 render: PICKED_UP, PICKED-UP, PICKED and PICKEDUP display and count as PICKED UP',()=>{
 const variants=['PICKED_UP','PICKED-UP','PICKED','PICKEDUP','PICKED UP','picked up'];
 const env=run('2026-10-04T21:00:00Z',true,data=>{
  data.checkins=variants.map((st,i)=>({url:'p'+i,Agent:[DOT],Logged:`2026-10-04T20:5${i}:00Z`,Time:`2026-10-04T20:5${i}:00Z`,Status:st,'Doing now':'variant '+i}));
  data.counts={agents:6,tasks_total:0,tasks_open:0,checkins:12,checkins_feed_rows:6,checkin_status:{'PICKED_UP':2,'PICKED-UP':1,'PICKED':1,'PICKEDUP':1,'PICKED UP':3,'WORKING':4}};
 });
 const shown=[...env.now.innerHTML.matchAll(/<td>(PICKED[^<]*|picked[^<]*)<\/td>/g)].map(m=>m[1]);
 assert.equal(shown.length,6);assert.ok(shown.every(x=>x==='PICKED UP'),shown.join('|'));
 assert.match(env.now.innerHTML,/id="status-counts">Reported status across scanned check-ins: PICKED UP 8 · WORKING 4\./);
 assert.doesNotMatch(env.now.innerHTML,/PICKED_UP|PICKED-UP|PICKEDUP/);
});

test('projects fold into Older after 7 idle days or Done; lanes, project agents and blockers render',()=>{
 const [P1,P2,P3,P4]=['a','b','c','d'].map(c=>c.repeat(32));
 const env=run('2026-10-04T21:00:00Z',true,data=>{
  data.projects=[{url:P1,Project:'Lane One',Status:'🟢 On track',Agents:[PRIMARY[0]],_edited:'2026-10-04T10:00:00Z'},
   {url:P2,Project:'Shipped Thing',Status:'✅ Done',Agents:[],_edited:'2026-10-04T10:00:00Z'},
   {url:P3,Project:'Old Idea',Status:'🟡 Moving',Agents:[PRIMARY[0]],_edited:'2026-09-01T10:00:00Z'},
   {url:P4,Project:'Stuck Lane',Status:'🔴 Stuck',Agents:[],_edited:'2026-09-01T10:00:00Z'}];
  data.project_checkins={[P3]:{latest_logged:'2026-09-20T10:00:00Z',rows:1},[P4]:{latest_logged:'2026-10-03T10:00:00Z',rows:2}};
  data.agents[0].Projects=[P1,P3];
  data.report_coverage.per_agent[PRIMARY[0]].latest['Blocker question']='Which ad account should be used?';
 });
 assert.match(env.projects.innerHTML,/Active projects \(2\)/);assert.match(env.projects.innerHTML,/Older projects \(2\)/);
 assert.ok(env.projects.innerHTML.indexOf('Older projects')<env.projects.innerHTML.indexOf('Old Idea'));
 assert.ok(env.projects.innerHTML.indexOf('Older projects')>env.projects.innerHTML.indexOf('Lane One'));
 assert.match(env.projects.innerHTML,new RegExp('href="#agent='+PRIMARY[0]+'">Dash'));
 assert.match(env.agents.innerHTML,/🧭 Lane One/);assert.doesNotMatch(env.agents.innerHTML,/Old Idea/);
 assert.doesNotMatch(env.agents.innerHTML,/Grok ST/);
 assert.match(env.now.innerHTML,/Which ad account should be used\?/);const older=env.now.innerHTML.indexOf('Older blockers');assert.ok(older>0,'stale blocked project folds into Older blockers');assert.ok(env.now.innerHTML.indexOf('Stuck Lane')>older,'Stuck Lane (35 h idle) is not a current block');
});
test('6 h rule: a blocked project with activity 3 h ago is a current block, one idle 7 h is folded',()=>{
 const [P5,P6]=['e','f'].map(c=>c.repeat(32));
 const env=run('2026-10-04T21:00:00Z',true,data=>{
  data.projects=[{url:P5,Project:'Fresh Block',Status:'🔴 Stuck',Agents:[],_edited:'2026-10-04T18:00:00Z'},{url:P6,Project:'Idle Block',Status:'🔴 Stuck',Agents:[],_edited:'2026-10-04T14:00:00Z'}];
 });
 const h=env.now.innerHTML,older=h.indexOf('Older blockers');
 assert.match(h,/blocked projects \(1\)/);assert.ok(h.indexOf('Fresh Block')>0&&h.indexOf('Fresh Block')<older);assert.ok(h.indexOf('Idle Block')>older);
});
