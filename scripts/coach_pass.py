#!/usr/bin/env python3
"""COACH pass writer for the six live seats (COACH-LOOP-48H-20261006 Section B).

Runs in GitHub Actions (.github/workflows/coach.yml) so coaching no longer depends on a local Claude session.
Each run:
  1. stops (exit 0, one log line) at or after STOP_AT;
  2. reads the Agents data source and drops any seat whose Status matches retired|inactive, and always drops Mack;
  3. reads the last 15 min of Check-ins and the existing COACH rows in the Co-CEO Channel;
  4. numbers the pass from the existing COACH rows (highest "pass #n" + 1);
  5. skips a seat that already has a COACH row from the last 8 min (dedupe);
  6. writes one DISPATCH row per remaining seat: title "COACH · <seat> · HH:MM MT · pass #n" plus the five lines
     LAST / NOW / IMPROVE / PROOF DUE / NEXT in Strategy note (same format as pass #1 at 03:27Z).
--dry-run prints the rows it would write and writes nothing. Standard library only. The token comes from the
NOTION_TOKEN environment variable and is never printed.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.request

NOTION_VERSION = "2025-09-03"
DS_AGENTS = "a2ee467b26574173b36edf538f6e35e3"
DS_CHECKINS = "adb5ca487d474f4e8ca72b449c91fa41"
DS_COCEO = "c1880491d8e743218fbc5299db8dfd5f"
AUTHOR_ID = "3edcf5514fd381d7a91dd8a7bdcccb87"  # the coach author used by pass #1 (Mack seat); never a recipient
LOOP_URL = "https://app.notion.com/p/3f1cf5514fd381c084bdfb57ffbe1cb0"  # COACH-LOOP-48H-20261006
STOP_AT = dt.datetime(2026, 10, 7, 0, 0, tzinfo=dt.timezone.utc)
WINDOW_MIN = 15
DEDUPE_MIN = 8
MT_OFFSET = dt.timedelta(hours=-6)  # Mountain Daylight Time
RETIRED_RE = re.compile(r"retired|inactive", re.I)
MACK_RE = re.compile(r"\bmack\b|claude mb cli", re.I)
MACK_IDS = {"3edcf5514fd381d7a91dd8a7bdcccb87", "3f1cf5514fd38105aca9e742e07e34c5"}


def u(page_id):
    return "https://app.notion.com/p/" + page_id


# The six live seats. Lane units come from COACH-LOOP-48H-20261006 Sections B/C (Lane 1-4).
SEATS = [
    {"seat": "Dash", "agent": "3edcf5514fd3812ea137d3ce41dafab3", "project": "3f1cf5514fd38181afd4c553983269a3",
     "now": "G1 fill Project relation on blank rows " + u("3f1cf5514fd38181afd4c553983269a3")
            + " - done when the next 5 blank rows have a Project relation and the remaining count is posted.",
     "next": "W7 Project/Device fill " + u("3f1cf5514fd3814c8b8cd6c94278fd72")},
    {"seat": "Dot", "agent": "3edcf5514fd381c18e9ad31f16369f38", "project": "3efcf5514fd381228aeeff2ddd75e95b",
     "now": "next open Projects Master row without a review (Weekly Creative Engine "
            + u("37bcf5514fd381dc8f93ca0e2d774db9")
            + ") - done when one page holds task-review + red-team + postmortem and it is handed to Hank.",
     "next": "Consultant LTFU + Monthly Webinar Cadence " + u("37bcf5514fd381aeb83df4d26c9d6008")},
    {"seat": "Grok Web", "agent": "3f1cf5514fd38132b072c4e7cc220cff", "project": "3efcf5514fd3814d91d4da955f76077a",
     "now": "Lane 3 revenue unit: Advaita LinkedIn Scraper " + u("384cf5514fd381d6ab42cf07c2114e2d")
            + " - done when one draft-only output (0 sends) is the Proof URL on a Check-in with Project = Sales process.",
     "next": "Hub Marketing (Stuck 0%) " + u("3edcf5514fd3819f859dc25f9e6d4bbc")},
    {"seat": "Gemma (Studio)", "agent": "3f1cf5514fd38105a1b6ea01505d07dc", "project": "3efcf5514fd3812f9f4de16270aa5f2d",
     "now": "Lane 4 Advaita Vision merge - " + u("338cf5514fd381c19054da41ec108b0d") + " vs "
            + u("33bcf5514fd38199bcaacfd57c65a85a") + " vs " + u("3d8cf5514fd381e8ad98d6d172566a65")
            + " - done when one merged outline with conflicts flagged is the Proof URL of a Check-in row.",
     "next": "LM1 line 4 'Rubric fails: <seat> R<n>' " + u("3f1cf5514fd38176a575dd4e7db972cc")},
    {"seat": "Qwen (Studio)", "agent": "3f1cf5514fd38183b2ced112573c6664", "project": "3efcf5514fd3811aa943f4d3433e5609",
     "now": "Lane 4 Trail day-brief - next backfill day (walking back from 2026-07-21): one 5-line brief (asks / done /"
            " unproved / decisions / repeats) as a Check-in on Trail history " + u("3efcf5514fd3811aa943f4d3433e5609")
            + "; done when that row lands.",
     "next": "the day before it, same project"},
    {"seat": "Laya (Studio)", "agent": "3f1cf5514fd38118b905e9be079bd60b", "project": "3efcf5514fd3812f9f4de16270aa5f2d",
     "now": "Lane 4 Mkt&CRM brief - classify the next All Marketing & CRM Projects row (collection"
            " 2f5cf551-4fd3-804f-82cb-000b9863e87c): lane + duplicate-of-Master yes/no; done when the label lands as a Check-in row.",
     "next": "the following Mkt&CRM row, same label"},
]


def norm(i):
    return (i or "").replace("-", "")


def iso(t):
    return t.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def parse_t(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def plain(prop):
    if not prop:
        return ""
    t = prop.get("type")
    v = prop.get(t)
    if t in ("title", "rich_text"):
        return "".join(x.get("plain_text", "") or x.get("text", {}).get("content", "") for x in v or [])
    if t in ("select", "status"):
        return (v or {}).get("name", "")
    if t == "relation":
        return ",".join(norm(x["id"]) for x in v or [])
    if t == "url":
        return v or ""
    return ""


def http_api(method, path, body=None):
    token = os.environ.get("NOTION_TOKEN", "").strip()
    if not token:
        raise RuntimeError("NOTION_TOKEN is not set")
    req = urllib.request.Request(
        "https://api.notion.com/v1/" + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": "Bearer " + token, "Notion-Version": NOTION_VERSION,
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return {"_http_error": e.code, "_body": e.read().decode("utf-8", "replace")[:400]}


def query_all(api, ds, body):
    out, body = [], dict(body)
    while True:
        r = api("POST", "data_sources/%s/query" % ds, body)
        if "_http_error" in r:
            raise RuntimeError("query %s failed: HTTP %s %s" % (ds, r["_http_error"], r.get("_body", "")))
        out += r.get("results", [])
        if not r.get("has_more"):
            return out
        body["start_cursor"] = r["next_cursor"]


def eligible_seats(seats, agents):
    """Drop Mack and every seat whose Agents Status matches retired|inactive. agents: {agent_id: (name, status)}."""
    keep = []
    for s in seats:
        name, status = agents.get(norm(s["agent"]), (s["seat"], ""))
        if norm(s["agent"]) in MACK_IDS or MACK_RE.search(s["seat"]) or MACK_RE.search(name):
            continue
        if RETIRED_RE.search(status):
            continue
        keep.append(s)
    return keep


def next_pass_number(coach_rows):
    nums = []
    for p in coach_rows:
        m = re.search(r"pass #(\d+)", plain(p["properties"].get("Entry")))
        if m:
            nums.append(int(m.group(1)))
    if nums:
        return max(nums) + 1
    return len(coach_rows) // 6 + 1


def recently_coached(seat, coach_rows, now):
    cut = now - dt.timedelta(minutes=DEDUPE_MIN)
    for p in coach_rows:
        if norm(seat["agent"]) in plain(p["properties"].get("Dispatched to")).split(",") \
                and parse_t(p["created_time"]) >= cut:
            return True
    return False


def last_line(rows):
    if not rows:
        return "LAST: MISSED - 0 Check-in rows in the last %d min." % WINDOW_MIN, "R1"
    n = len(rows)
    st = {}
    for p in rows:
        s = plain(p["properties"].get("Status")) or "blank"
        st[s] = st.get(s, 0) + 1
    no_proj = sum(1 for p in rows if not plain(p["properties"].get("Project")))
    no_dev = sum(1 for p in rows if not plain(p["properties"].get("Device")))
    no_trail = sum(1 for p in rows if not plain(p["properties"].get("Trail key")))
    no_url = sum(1 for p in rows if not plain(p["properties"].get("Proof")).startswith("http"))
    newest = plain(rows[0]["properties"].get("Check-in"))[:80]
    gaps = []
    if no_proj:
        gaps.append("no Project %d/%d" % (no_proj, n))
    if no_dev:
        gaps.append("no Device %d/%d" % (no_dev, n))
    if no_url:
        gaps.append("Proof not a URL %d/%d" % (no_url, n))
    if no_trail:
        gaps.append("no Trail key %d/%d" % (no_trail, n))
    line = "LAST: %d rows in %d min (%s); newest '%s'; %s. Score pending (Hank)." % (
        n, WINDOW_MIN, ", ".join("%s %d" % kv for kv in sorted(st.items())), newest,
        "; ".join(gaps) if gaps else "Project, Device, Proof URL and Trail key on every row")
    r = "R1" if (no_proj or no_dev) else "R2" if no_url else "R10" if no_trail else "R4"
    return line, r


IMPROVE = {
    "R1": "IMPROVE: R1 - every row carries Project + Device (the host that ran it); a row without them does not count.",
    "R2": "IMPROVE: R2 - Proof must be a URL a human can open that shows this tick's change, not a latency string or queue id.",
    "R10": "IMPROVE: R10 - fill Trail key on every row.",
    "R4": "IMPROVE: R4 - write 'Better than last: <one fix>' in Doing now.",
}


def build_rows(now, seats, checkins, coach_rows):
    n = next_pass_number(coach_rows)
    mt = now + MT_OFFSET
    hm, due = mt.strftime("%H:%M"), (mt + dt.timedelta(minutes=15)).strftime("%H:%M")
    out, skipped = [], []
    for s in seats:
        if recently_coached(s, coach_rows, now):
            skipped.append(s["seat"])
            continue
        mine = [p for p in checkins if norm(s["agent"]) in plain(p["properties"].get("Agent")).split(",")]
        last, r = last_line(mine)
        now_line = ("NOW: smallest shippable piece of " if not mine else "NOW: ") + s["now"]
        title = "COACH · %s · %s MT · pass #%d" % (s["seat"], hm, n)
        lines = [last, now_line, IMPROVE[r],
                 "PROOF DUE: %s MT -> Check-in row with Proof URL + Project link" % due,
                 "NEXT: " + s["next"]]
        out.append({"seat": s["seat"], "agent": norm(s["agent"]), "project": s["project"], "title": title,
                    "note": "\n".join([title] + lines)})
    return out, skipped


def page_body(row):
    def rt(s):
        return [{"type": "text", "text": {"content": s[i:i + 1900]}} for i in range(0, len(s), 1900)]
    return {"parent": {"type": "data_source_id", "data_source_id": DS_COCEO},
            "properties": {"Entry": {"title": rt(row["title"])}, "Type": {"select": {"name": "DISPATCH"}},
                           "Dispatched to": {"relation": [{"id": row["agent"]}]},
                           "Author": {"relation": [{"id": AUTHOR_ID}]},
                           "Projects": {"relation": [{"id": row["project"]}]}, "Proof": {"url": LOOP_URL},
                           "Reply to": {"rich_text": rt("COACH-LOOP-48H-20261006 Section B · coach.yml cloud route")},
                           "Audit verdict": {"select": {"name": "N/A"}},
                           "Strategy note": {"rich_text": rt(row["note"])}}}


FAILED = []


def run(now, api, dry_run=False, log=print):
    if now >= STOP_AT:
        log("coach_pass: stop time %s reached; no rows written" % iso(STOP_AT))
        return []
    agents = {norm(p["id"]): (plain(p["properties"].get("Agent")), plain(p["properties"].get("Status")))
              for p in query_all(api, DS_AGENTS, {"page_size": 100})}
    seats = eligible_seats(SEATS, agents)
    checkins = query_all(api, DS_CHECKINS, {
        "page_size": 100, "sorts": [{"timestamp": "created_time", "direction": "descending"}],
        "filter": {"timestamp": "created_time",
                   "created_time": {"on_or_after": iso(now - dt.timedelta(minutes=WINDOW_MIN))}}})
    coach_rows = query_all(api, DS_COCEO, {"page_size": 100,
                                           "filter": {"property": "Entry", "title": {"starts_with": "COACH · "}}})
    rows, skipped = build_rows(now, seats, checkins, coach_rows)
    log("coach_pass: %d eligible seats, %d check-ins in %d min, %d COACH rows so far, writing %d, dedupe-skipped %s"
        % (len(seats), len(checkins), WINDOW_MIN, len(coach_rows), len(rows), skipped or "none"))
    written = []
    for row in rows:
        if norm(row["agent"]) in MACK_IDS:  # last guard: never dispatch to Mack
            continue
        if dry_run:
            log("DRY-RUN would write:\n" + row["note"])
            written.append(row)
            continue
        r = api("POST", "pages", page_body(row))
        if "_http_error" in r:
            log("coach_pass: WRITE FAILED %s HTTP %s %s" % (row["seat"], r["_http_error"], r.get("_body", "")))
            FAILED.append(row["seat"])
            continue
        row["id"] = norm(r.get("id"))
        log("coach_pass: wrote %s %s" % (row["id"], row["title"]))
        written.append(row)
    return written


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    now = dt.datetime.now(dt.timezone.utc)
    written = run(now, http_api, dry_run=a.dry_run)
    if not a.dry_run and now < STOP_AT:
        print("coach_pass: done, %d rows written, %d failed" % (len(written), len(FAILED)))
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
