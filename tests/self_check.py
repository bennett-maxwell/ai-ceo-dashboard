"""Render a fixture board and classify Rocky, Dot, Hank and Leo on the 6-minute window."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build

ROCKY, LEO, DOT, HANK = build.PRIMARY_AGENT_IDS[:4]
BUILT = "2026-10-05T19:20:00Z"
AGENTS = [
    {"url": ROCKY, "Agent": "Rocky", "Status": "🟢 Alive", "Platform": "Grok Bot", "Role": "Coordinator", "Device": [], "Projects": []},
    {"url": LEO, "Agent": "Leo", "Status": "⚪ Not tested", "Platform": "Grok company", "Role": "Chief of Staff", "Device": [], "Projects": []},
    {"url": DOT, "Agent": "Dot", "Status": "⚪ Not tested", "Platform": "ChatGPT", "Role": "CO-CEO", "Device": [], "Projects": []},
    {"url": HANK, "Agent": "Hank", "Status": "⚪ Not tested", "Platform": "Other", "Role": "HyperAgent", "Device": [], "Projects": []},
    {"url": build.PRIMARY_AGENT_IDS[4], "Agent": "Dash", "Status": "🟢 Alive", "Platform": "muse.ai", "Role": "Personal", "Device": [], "Projects": []},
    {"url": build.PRIMARY_AGENT_IDS[5], "Agent": "Mack CLI", "Status": "🟡 Working", "Platform": "Claude", "Role": "CO-CEO", "Device": [], "Projects": []},
]
REPORTS = [
    {"url": "rocky1", "Check-in": "Rocky · 13:18 MT", "Agent": [ROCKY], "Logged": "2026-10-05T19:18:00Z", "Time": "2026-10-05T19:18:00Z", "Status": "WORKING", "Doing now": "shipping", "Project": [], "Proof": None, "Device": [], "Blocker question": None},
    {"url": "dot1", "Check-in": "dot · 13:16 MT", "Agent": [DOT], "Logged": "2026-10-05T19:16:00Z", "Time": "2026-10-05T19:16:00Z", "Status": "WORKING", "Doing now": "MM review", "Project": [], "Proof": None, "Device": [], "Blocker question": "Need a route"},
    {"url": "hank1", "Check-in": "Hank · 13:05 MT · GRADE ACCEPT", "Agent": [HANK], "Logged": "2026-10-05T19:06:00Z", "Time": "2026-10-05T19:06:00Z", "Status": "FINISHED", "Doing now": "ACCEPT (Hank, independent)", "Project": [], "Proof": None, "Device": [], "Blocker question": None},
    {"url": "leo1", "Check-in": "Leo · 13:17 MT", "Agent": None, "Logged": "2026-10-05T19:17:00Z", "Time": "2026-10-05T19:17:00Z", "Status": "WORKING", "Doing now": "title-only check-in", "Project": [], "Proof": None, "Device": [], "Blocker question": None},
    {"url": "fin1", "Check-in": "Rocky · 13:19 MT", "Agent": [ROCKY], "Logged": "2026-10-05T19:19:00Z", "Time": "2026-10-05T19:19:00Z", "Status": "FINISHED", "Doing now": "lane closed", "Project": [], "Proof": "https://example.invalid/proof", "Device": [], "Blocker question": None},
]

def main():
    reports, coverage = build.report_coverage(REPORTS, AGENTS, [], [], cutoff=build.timestamp(BUILT))
    snap = {
        "agents": AGENTS, "devices": [], "projects": [
            {"url": "projg", "Project": "Green lane", "Company": "Advaita AI", "Status": "🟢 On track", "Progress %": 90, "Last %": 80, "Finish condition": "proof filed"},
            {"url": "projr", "Project": "Red lane", "Company": "Advaita AI", "Status": "🔴 Stuck", "Progress %": 10, "Last %": 10, "Finish condition": "need owner"},
        ],
        "checkins": [], "crons": [], "caio": [], "fat20": [], "coceo": [], "tasks": [],
        "aiceo": [{"url": "ace1", "Type": "Plan", "Status": "LIVE", "Seat": "Rocky", "Graded by": "Hank", "Date": "2026-10-05"}],
        "aiceo_status": "1 rows read",
        "aiceo_coverage": {"state": "available", "exhaustive": True, "public_rows": 1},
        "report_coverage": coverage,
        "primary_agents": list(build.PRIMARY_AGENT_IDS),
        "primary_agent_names": {i: build.aliases_for(i, AGENTS) for i in build.PRIMARY_AGENT_IDS},
        "needs_bennett": build.needs_bennett_rows(reports, AGENTS),
        "counts": {"agents": len(AGENTS), "tasks_total": 0, "tasks_open": 0, "checkins": len(reports), "checkins_feed_rows": len(reports), "aiceo": 1},
    }
    feed = build.collapse_heartbeats(reports)
    for row in feed:
        if build.is_finished_status(row.get("Status")):
            row["_finish"] = build.finish_label(row, reports, AGENTS)
    snap["checkins"] = feed
    html = build.render(snap, BUILT)
    site = ROOT / "site"
    site.mkdir(exist_ok=True)
    (site / "index.html").write_text(html)
    (site / "version.json").write_text(json.dumps({"built_at": BUILT}))
    js = f"""
const status=require({json.dumps(str(ROOT / "report_status.js"))});
const cov={json.dumps(coverage["per_agent"])};
const ids={json.dumps({"Rocky": ROCKY, "Leo": LEO, "Dot": DOT, "Hank": HANK})};
const built={json.dumps(BUILT)};
const now=Date.parse('2026-10-05T19:20:30Z');
for (const [name,id] of Object.entries(ids)) {{
  const r=status.evaluate(cov[id], built, now);
  console.log(name + "\\t" + r.bucket + "\\t" + r.cls + "\\t" + r.label + "\\t" + (cov[id] && cov[id].matched_by || ""));
}}
"""
    out = subprocess.check_output(["node", "-e", js], text=True)
    print("self-check classifications (build", BUILT, "window", status_window(), "min):")
    print(out.rstrip())
    expect = {"Rocky": "fresh", "Leo": "fresh", "Dot": "fresh", "Hank": "late"}
    got = {}
    for line in out.strip().splitlines():
        name, bucket, *_ = line.split("\t")
        got[name] = bucket
    html_text = html
    for name in expect:
        if name not in html_text:
            raise SystemExit(f"self-check: {name} missing from rendered HTML")
    if "Updated" not in html_text or 'id="aiceo"' not in html_text or "Needs Bennett" not in html_text:
        raise SystemExit("self-check: required page chrome missing")
    if "self-reported" not in html_text:
        raise SystemExit("self-check: FINISHED row was not labeled self-reported")
    if got != expect:
        raise SystemExit(f"self-check: expected {expect}, got {got}")
    print("wrote", site / "index.html")
    print("self-check: PASS")
    return 0

def status_window():
    return 6

if __name__ == "__main__":
    raise SystemExit(main())
