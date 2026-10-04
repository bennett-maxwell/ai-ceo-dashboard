const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync('template.html','utf8');
const block=source.slice(source.indexOf('function freshness()'),source.indexOf('freshness();render();'));
function context(builtAt,hidden=false){
 const calls=[];
 const env={SNAP_AT:'2026-10-04T19:00:00Z',Date:class extends Date{static now(){return Date.parse('2026-10-04T19:21:00Z')}},URL,document:{hidden},fresh:{style:{}},ago:()=> '21m ago',location:{href:'https://example.com/dashboard/#projects',replace:url=>calls.push(url)},fetch:async(url,opts)=>{calls.push(opts);return {ok:true,json:async()=>({built_at:builtAt})}}};
 vm.createContext(env);vm.runInContext(block,env);return {env,calls};
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
 const {env}=context('2026-10-04T19:10:00Z');env.freshness();assert.match(env.fresh.textContent,/STALE/);assert.equal(env.fresh.style.color,'var(--red)');
});
