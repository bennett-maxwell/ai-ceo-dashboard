const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');
const DASH='3edcf5514fd3812ea137d3ce41dafab3';
const P0='aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa1',P1='aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa2',PX='aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa3';
function run(){
 const DateFixed=class extends Date{constructor(...a){super(...(a.length?a:['2026-10-06T19:30:00Z']))}static now(){return Date.parse('2026-10-06T19:30:00Z')}};
 const el=()=>({innerHTML:'',textContent:'',style:{},addEventListener(){},classList:{toggle(){}}});
 const ids=['grok','dash','dot','asks','fleet','now','big','coceo','agents','devices','projects','tasks','caio','crons'],sec=ids.map(id=>({...el(),id}));
 const env={Date:DateFixed,URL,console,location:{href:'https://example.com/#big',hash:'#big',replace(){}},history:{replaceState(){}},document:{hidden:false,querySelectorAll:s=>s==='section'?sec:[],addEventListener(){}},setInterval(){},setTimeout:f=>{env._boot=f},fetch:async()=>({ok:false}),sessionStorage:{getItem(){return null},setItem(){}}};
 ids.forEach((id,i)=>env[id]=sec[i]);['tabs','companies','fresh'].forEach(id=>env[id]=el());
 const data={primary_agents:[DASH],agents:[{url:DASH,Agent:'Dash',Projects:[],Device:[]}],devices:[],checkins:[],
  projects:[{url:P0,Project:'Voice board',Status:'🟡 Moving','Progress %':20,Category:'Dashboard & Command',Priority:'P0 · Now','Big project':'__YES__',Agents:[DASH],Company:'Advaita AI'},
            {url:P1,Project:'Trail backfill',Status:'🔴 Stuck',Category:'Trail & Memory',Priority:'P2 · Next','Big project':'__YES__',Agents:[]},
            {url:PX,Project:'Small row',Status:'🟡 Moving','Big project':'__NO__'}],
  project_checkins:{[P0]:{latest_logged:'2026-10-06T19:10:00Z',rows:3}},
  report_coverage:{exhaustive:true,unique_rows:1,unlinked_rows:0,per_agent:{[DASH]:{agent_id:DASH,included:true,exhaustive:true,matching_rows:0,latest:null}}}};
 const src=fs.readFileSync('template.html','utf8').replace('__REPORT_STATUS__',fs.readFileSync('report_status.js','utf8')+'\n'+fs.readFileSync('big.js','utf8')).replace('__AT__','2026-10-06T19:30:00Z').replace('__SNAP__',JSON.stringify(data));
 vm.createContext(env);vm.runInContext(src.match(/<script>([\s\S]*?)<\/script>/)[1],env);env._boot();return env;
}
test('Big projects tab groups by priority and category, shows live state',()=>{
 const env=run(),h=env.big.innerHTML;
 assert.match(h,/Big projects \(2\)/);
 assert.match(h,/P0 · Now \(1\)/);assert.match(h,/P2 · Next \(1\)/);
 assert.ok(h.indexOf('P0 · Now')<h.indexOf('P2 · Next'),'P0 renders above P2');
 assert.match(h,/Dashboard &amp; Command/);assert.match(h,/Trail &amp; Memory/);
 assert.match(h,/Voice board/);assert.doesNotMatch(h,/Small row/,'non-big rows stay off this tab');
 assert.match(h,/>Active</);assert.match(h,/Not active in last hour/);
 assert.match(h,/🔴/);assert.match(h,/Dash/);
 assert.match(env.tabs.innerHTML,/⭐ Big projects/);
 assert.ok(env.tabs.innerHTML.indexOf('Now')<env.tabs.innerHTML.indexOf('Big projects'),'tab sits right after Now');
});
test('build.py publishes the fields the Big projects tab reads',()=>{
 const b=fs.readFileSync('build.py','utf8');for(const f of ['Category','Priority','Big project'])assert.match(b,new RegExp('"projects": \\([^)]*"'+f+'"'));
 assert.match(b,/Path\("big\.js"\)\.read_text\(\)/);
});
