(function(root){
 "use strict";
 const WORKER_MAX_AGE_MS=3*60000,SNAPSHOT_MAX_AGE_MS=10*60000;
 function time(value){
  if(typeof value!=="string")return null;
  const m=value.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2})(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})$/);
  if(!m||+m[2]<1||+m[2]>12||+m[3]<1||+m[3]>new Date(Date.UTC(+m[1],+m[2],0)).getUTCDate()||+m[4]>23||+m[5]>59||+(m[6]||0)>59)return null;
  const t=Date.parse(value);return Number.isFinite(t)?t:null;
 }
 function snapshot(at,now=Date.now()){
  const built=time(at),age=built==null?null:now-built;
  return {available:age!=null&&age>=0&&age<=SNAPSHOT_MAX_AGE_MS,age,built};
 }
 function evaluate(coverage,builtAt,now=Date.now()){
  const last=coverage?.latest||null,view=snapshot(builtAt,now);
  const result={last,process:"Unknown — no runtime proof",cls:"",color:"var(--gray)",label:"Not included — coverage unknown",workerFresh:false,receiptRecent:false,worker:"Unverified",receipt:"Unknown",coverage:coverage||null};
  if(!coverage?.included||coverage.exhaustive!==true)return result;
  if(!last){result.label=view.available?"Never observed as of exhaustive snapshot query":"Live status unavailable — stale or invalid snapshot";return result}
  const logged=time(last.Logged),worker=time(last.Time);
  const validLogged=logged!=null&&logged<=now&&view.built!=null&&logged<=view.built;
  result.receipt=validLogged?(now-logged<=WORKER_MAX_AGE_MS?"Recent server receipt":"Old server receipt"):"Invalid server receipt";
  result.receiptRecent=view.available&&validLogged&&now-logged<=WORKER_MAX_AGE_MS;
  let problem=null;
  if(!validLogged)problem="Invalid Logged timestamp";
  else if(!Array.isArray(last.Agent)||!last.Agent.includes(coverage.agent_id))problem="Agent binding unverified";
  else if(worker==null)problem="Worker Time missing or invalid";
  else if(worker>logged||worker>now)problem="Worker Time future — unverified";
  else if(coverage.latest_replayed)problem="Replayed worker Time — unverified";
  if(problem){result.worker=problem;result.label=problem;result.cls="y";result.color="var(--yellow)"}
  else if(now-worker<=WORKER_MAX_AGE_MS){result.worker="Fresh worker report (≤3m)";result.workerFresh=view.available;result.label=result.worker;result.cls=view.available?"g":"";result.color=view.available?"var(--green)":"var(--gray)"}
  else{result.worker="Stale worker report (>3m)";result.label=result.worker;result.cls="y";result.color="var(--yellow)"}
  if(!view.available){result.label="Live status unavailable — stale or invalid snapshot";result.workerFresh=false;result.receiptRecent=false;result.cls="";result.color="var(--gray)"}
  return result;
 }
 const api={time,snapshot,evaluate,WORKER_MAX_AGE_MS,SNAPSHOT_MAX_AGE_MS};
 if(typeof module!=="undefined"&&module.exports)module.exports=api;else root.ReportStatus=api;
})(globalThis);
