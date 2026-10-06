// ⭐ Big projects tab (IVAN, 2026-10-06, Bennett voice order: "Projects page by category and priority").
// Reads 🧭 Projects rows where "Big project" is checked; build.py publishes Category, Priority and Big project.
// Loaded into the same <script> as template.html (build.py render), so it boots after the page script has run.
const BIG_PRI=["P0 · Now","P1 · This week","P2 · Next","P3 · Later"];
const BIG_CAT=["Dashboard & Command","Fleet & Agents","Skills & Harness","Sales & Revenue","Marketing & Content","Trail & Memory","Org & Backbone","Personal & Legal"];
function bigRag(s){s=String(s||"");return /stuck/i.test(s)?["🔴","r"]:/on track/i.test(s)?["🟢","g"]:/moving/i.test(s)?["🟡","y"]:/done/i.test(s)?["✅","g"]:["⚪",""]}
function renderBig(){
 const el=typeof document.getElementById==="function"?document.getElementById("big"):(typeof big!=="undefined"?big:null);if(!el)return;
 const P=S.data.projects||[],A=S.data.agents||[],PC=S.data.project_checkins||{},Am=byId(A);
 const coOK=p=>S.co==="All companies"||(p&&p.Company===S.co);
 const agentsOf=p=>{const id=pid(p.url);return[...new Set(rel(p.Agents).concat(A.filter(a=>rel(a.Projects).includes(id)).map(a=>pid(a.url))))]};
 const lastT=p=>{const e=PC[pid(p.url)];return e&&e.latest_logged?ReportStatus.time(e.latest_logged):null};
 const isLive=p=>{const t=lastT(p),n=Date.parse(SNAP_AT);return t!=null&&Number.isFinite(n)&&n-t<=3600000};
 const isBig=p=>p&&p["Big project"]==="__YES__"&&coOK(p);
 const BIG=P.filter(p=>isBig(p)&&!closedP(p)),DONE=P.filter(p=>isBig(p)&&closedP(p));
 const card=p=>{const [d,c]=bigRag(p.Status),ag=lk("agent",Am,agentsOf(p),"Agent").join(""),t=lastT(p);
  return`<div class="card ${c}"><h3>${d} <a class="lk" href="#project=${pid(p.url)}">${esc(p.Project)}</a></h3><div style="display:flex;gap:8px;align-items:center">${prog(p["Progress %"])}</div><div class="meta">${esc(p.Category||"No category")}${p.Company?" · "+esc(p.Company):""} · ${isLive(p)?'<b style="color:var(--green)">Active</b>':"Not active in last hour"}</div><div class="chips">${ag||'<span class="meta">no agent linked</span>'}</div><div class="meta">Last check-in: ${t!=null?esc(ago(PC[pid(p.url)].latest_logged)):"none linked"}</div><div class="doing">${esc(p["Finish condition"]||"No finish condition yet")}</div></div>`};
 const catRows=BIG_CAT.concat(["No category"]).map(c=>{const L=BIG.filter(p=>(p.Category||"No category")===c);if(!L.length)return"";const ps=L.map(p=>p["Progress %"]).filter(v=>v!=null&&v!==""&&Number.isFinite(+v)).map(Number),avg=ps.length?Math.round(ps.reduce((a,b)=>a+b,0)/ps.length):null;
  return`<tr><td><b>${esc(c)}</b></td><td class="mono">${L.length}</td><td class="mono">${L.filter(p=>/stuck/i.test(p.Status||"")).length}</td><td class="mono">${L.filter(isLive).length}</td><td style="display:flex;gap:8px;align-items:center">${prog(avg)}</td></tr>`}).join("");
 const groups=BIG_PRI.map(k=>[k,BIG.filter(p=>p.Priority===k)]).concat([["No priority",BIG.filter(p=>!BIG_PRI.includes(p.Priority))]]).filter(x=>x[1].length);
 el.innerHTML=`<h2>⭐ Big projects (${BIG.length})</h2><p class="sub">Live from 🧭 Projects where Big project is checked. Agents update the Notion row; this page rebuilds about every 5 minutes. Active = a check-in linked to the project in the last hour.</p>
<h2>By category</h2><div class="wrap"><table><tr><th>Category</th><th>Projects</th><th>Stuck</th><th>Active</th><th>Avg progress</th></tr>${catRows||'<tr><td colspan="5">No big projects tagged yet.</td></tr>'}</table></div>
${groups.map(([k,L])=>`<h2>${esc(k)} (${L.length})</h2><div class="grid">${L.slice().sort((a,b)=>BIG_CAT.indexOf(a.Category)-BIG_CAT.indexOf(b.Category)).map(card).join("")}</div>`).join("")||'<div class="empty">No big projects tagged yet.</div>'}
${DONE.length?`<details><summary>Finished big projects (${DONE.length})</summary><div class="grid">${DONE.map(card).join("")}</div></details>`:""}`;
}
function bigBoot(){
 if(!TABS.some(t=>t[0]==="big")){const i=TABS.findIndex(t=>t[0]==="now");TABS.splice(i<0?TABS.length:i+1,0,["big","⭐ Big projects"])}
 if(typeof document.getElementById==="function"&&!document.getElementById("big")&&typeof document.createElement==="function"){const s=document.createElement("section");s.id="big";const ref=document.getElementById("coceo");ref&&ref.parentNode?ref.parentNode.insertBefore(s,ref):document.querySelector("main").appendChild(s)}
 const base=render;render=function(){base();renderBig()};
 route();render();
}
if(typeof setTimeout==="function")setTimeout(bigBoot,0);
