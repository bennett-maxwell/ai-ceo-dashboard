const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync('template.html','utf8');
const block=source.slice(source.indexOf('function snapshotAge(at)'),source.lastIndexOf('\nfreshness();render();'));
function context(builtAt,hidden=false){
 const calls=[];
 const env={ReportStatus:require('../report_status.js'),SNAP_AT:'2026-10-04T19:00:00Z',Date:class extends Date{static now(){return Date.parse('2026-10-04T19:21:00Z')}},URL,document:{hidden},fresh:{style:{}},S:{co:'Advaita AI'},sessionStorage:new Map(),ago:()=> '21m ago',location:{href:'https://example.com/dashboard/#projects',replace:url=>calls.push(url)},fetch:async(url,opts)=>{calls.push(opts);return {ok:true,json:async()=>({built_at:builtAt})}}};
 env.sessionStorage.getItem=k=>env.sessionStorage.get(k);env.sessionStorage.setItem=(k,v)=>env.sessionStorage.set(k,v);vm.createContext(env);vm.runInContext(block,env);return {env,calls};
}
test('new snapshot bypasses cache and preserves current tab',async()=>{
 const {env,calls}=context('2026-10-04T19:10:00Z');await env.refreshSnapshot();
 assert.equal(calls[0].cache,'no-store');assert.equal(new URL(calls[1]).hash,'#projects');assert.equal(new URL(calls[1]).searchParams.get('snapshot'),'2026-10-04T19:10:00Z');
});
test('same or older snapshot does not reload',async()=>{
 for(const time of ['2026-10-04T19:00:00Z','2026-10-04T18:00:00Z']){const {env,calls}=context(time);await env.refreshSnapshot();assert.equal(calls.length,1)}
});
test('hidden tab skips poll; offline retains snapshot',async()=>{
 const {env,calls}=context('2026-10-04T19:10:00Z',true);await env.refreshSnapshot();assert.equal(calls.length,0);env.document.hidden=false;env.fetch=async()=>{throw Error('offline')};await env.refreshSnapshot();assert.equal(calls.length,0);
});
test('old data visibly marked stale',()=>{
 const {env}=context('2026-10-04T19:10:00Z');env.SNAP_AT='2026-10-04T18:50:59Z';env.freshness();assert.match(env.fresh.textContent,/STALE/);assert.equal(env.fresh.style.color,'var(--red)');
});

test('future and invalid build timestamps fail closed',()=>{
 for(const at of ['garbage','2026-10-04T19:22:00Z']){
  const {env}=context(at);env.SNAP_AT=at;env.freshness();
  assert.match(env.fresh.textContent,/INVALID TIMESTAMP/);assert.equal(env.fresh.style.color,'var(--red)');
 }
});
test('invalid and future manifest timestamps never reload',async()=>{
 for(const at of ['garbage','2026-10-04T19:22:00Z']){
  const {env,calls}=context(at);await env.refreshSnapshot();assert.equal(calls.length,1);
 }
});
test('repeated checks and cached old HTML get one reload per version',async()=>{
 const {env,calls}=context('2026-10-04T19:10:00Z');
 await env.refreshSnapshot();await env.refreshSnapshot();assert.equal(calls.filter(x=>typeof x==='string').length,1);
 const {env:cached,calls:cachedCalls}=context('2026-10-04T19:10:00Z');
 cached.location.href=calls[1];await cached.refreshSnapshot();assert.equal(cachedCalls.length,1);
 assert.equal(new URL(calls[1]).searchParams.get('company'),'Advaita AI');
});
test('concurrent polls share one request and later versions can reload',async()=>{
 const {env,calls}=context('2026-10-04T19:10:00Z');
 await Promise.all([env.refreshSnapshot(),env.refreshSnapshot()]);assert.equal(calls.length,2);
 env.fetch=async()=>({ok:true,json:async()=>({built_at:'2026-10-04T19:20:00Z'})});
 await env.refreshSnapshot();assert.equal(calls.filter(x=>typeof x==='string').length,2);
});

test('invalid or future URL and storage watermarks do not suppress valid refresh',async()=>{
 for(const stamp of ['garbage','2099-01-01T00:00:00Z']){
  const {env,calls}=context('2026-10-04T19:10:00Z');
  env.location.href='https://example.com/dashboard/?snapshot='+stamp+'#projects';
  env.sessionStorage.setItem('dashboard-refresh:/dashboard/',stamp);
  await env.refreshSnapshot();assert.equal(calls.filter(x=>typeof x==='string').length,1);
 }
});
test('invalid embedded snapshot recovers once per valid manifest without loops',async()=>{
 for(const at of ['invalid','2099-01-01T00:00:00Z']){
  const {env,calls}=context('2026-10-04T19:10:00Z');env.SNAP_AT=at;
  await env.refreshSnapshot();await env.refreshSnapshot();assert.equal(calls.filter(x=>typeof x==='string').length,1);
  const {env:cached,calls:again}=context('2026-10-04T19:10:00Z');cached.SNAP_AT=at;cached.location.href=calls[1];await cached.refreshSnapshot();assert.equal(again.length,1);
 }
});

test('build age is always shown and a 21-minute-old build is not stale',()=>{
 const {env}=context('2026-10-04T19:10:00Z');env.freshness();
 assert.match(env.fresh.textContent,/^Built 21m ago · 2026-10-04T19:00:00Z$/);assert.doesNotMatch(env.fresh.textContent,/STALE/);assert.equal(env.fresh.style.color,'var(--mute)');
});
