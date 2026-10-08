"""Publish only the operational fields already displayed by the public dashboard."""
import datetime
import html
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.request

DB = {"agents":"ceaee3c46bcb463891ea1c86e20bdf17","devices":"255af22f85d840709836a5187f407482","projects":"10edde1f306545a3bbfdb9f507d532ed","checkins":"d322e38bf5054e9a965d8696723d596e","crons":"1effc590f7824467bf114ac164d5cc0c","caio":"64223bb0677a4eb3bda557ebeb5b2579","fat20":"a0c83122aaa0410a8acc0b4a889b01f2","coceo":"96f47983f50d44e3bff55404c876e2e9","tasks":"1a757d42a2ae4cb3acdf7e2eff2e0841"}
# Notion data source behind each database id (Command Center HUB 3edcf5514fd38180b7b5e780b12bcccc).
# Tasks sit under page 3e4cf5514fd381b497f7e6aab1521c82. All ids are dash-stripped.
DATA_SOURCES = {
    "agents": "a2ee467b26574173b36edf538f6e35e3",
    "devices": "d691854b83d449e8aac13b991805c239",
    "projects": "2c75f5446d7c42eaa33f55747167624e",
    "checkins": "adb5ca487d474f4e8ca72b449c91fa41",
    "crons": "474e80b06e004a0db3738b1b6426696a",
    "caio": "8f7f298cd6a84508adae96207c4d8d4c",
    "fat20": "277b8c966cf041c7ab271917fd2044bb",
    "coceo": "c1880491d8e743218fbc5299db8dfd5f",
    "tasks": "e706e6d10f18481e998118c873469d87",
    "aiceo": "536e453290b74a5083be86567bb46f4c",
}
# The AI CEO board is read through its data source; its database id is the fallback route.
AICEO_DB = "fe2ecada96c74adfb196753abc4dfb12"
# Row titles, dollar amounts and proof links on the AI CEO board are internal (customer names, cash figures),
# so only these select/date fields are ever published from it.
AICEO_FIELDS = ("Type", "Status", "Seat", "Graded by", "date:Date:start")
PUBLIC_FIELDS = {
    "agents": ("Agent", "Status", "Platform", "Role", "Device", "Projects"),
    "devices": ("Device", "Type"),
    "projects": ("Project", "Company", "Status", "Progress %", "Last %", "Finish condition", "Agents", "Category", "Priority", "Big project"),
    "checkins": ("Agent", "Logged", "Time", "Status", "Progress %", "Doing now", "Project", "Proof", "Device", "Blocker question"),
    "crons": ("Routine", "State", "Cadence", "Runs on", "Defined in"),
    "caio": ("Division", "Status", "Covers", "Projects", "Order"),
    "fat20": ("Rank", "Item", "Status", "Progress %"),
    "coceo": ("Logged", "Author", "Entry", "Type", "Strategy note", "Audit verdict", "Audit of partner"),
    "tasks": ("Focus", "Name", "Owner", "Status", "Progress %"),
}

def q(i, body, limit=None, route="databases", version="2022-06-28"):
    out, cur, seen_cursors = [], None, set()
    while True:
        size = min(100, limit - len(out)) if limit else 100
        b = dict(body, page_size=size, **({"start_cursor": cur} if cur else {}))
        r = urllib.request.Request(
            f"https://api.notion.com/v1/{route}/{i}/query", json.dumps(b).encode(),
            {"Authorization": f"Bearer {os.environ['NOTION_TOKEN']}",
             "Notion-Version": version, "Content-Type": "application/json"})
        with urllib.request.urlopen(r, timeout=30) as response:
            d = json.load(response)
        out.extend(d["results"])
        if not d.get("has_more") or (limit and len(out) >= limit):
            return out[:limit] if limit else out
        next_cur = d.get("next_cursor")
        if not next_cur or next_cur in seen_cursors:
            raise ValueError("Notion pagination did not advance")
        seen_cursors.add(next_cur)
        cur = next_cur

def val(p):
    t = p["type"]
    v = p.get(t)
    if t in ("title", "rich_text"):
        return "".join(x["plain_text"] for x in v) or None
    if t == "select": return v and v["name"]
    if t == "relation": return [x["id"].replace("-", "") for x in v]
    if t == "date": return v and v["start"]
    if t == "checkbox": return "__YES__" if v else "__NO__"
    if t in ("number", "url", "created_time"): return v

def rows(k, body=None, limit=None):
    res = []
    for pg in q(DB[k], body or {}, limit):
        props = pg["properties"]
        r = {"url": pg["id"].replace("-", "")}
        for name in PUBLIC_FIELDS[k]:
            r[name] = val(props[name]) if name in props else None
        if k == "projects" and pg.get("last_edited_time"):
            r["_edited"] = pg["last_edited_time"]  # used only to fold projects idle for 7 days
        if k == "checkins":
            for relation in ("Agent", "Project"):
                if props.get(relation, {}).get("has_more"):
                    r[f"_{relation.lower()}_relation_complete"] = False
        if k == "checkins":
            r["Status"] = norm_status(r.get("Status"))
        res.append(r)
    return res

# Check-ins Status variants that mean the same thing. Display and counts use the canonical name; the Notion
# rows and select options are never changed here (merging the options is a separate, proposed-only step).
PICKED_UP_RE = re.compile(r"PICKED(?:[\s_-]*UP)?", re.IGNORECASE)

def norm_status(status):
    if not isinstance(status, str):
        return status
    return "PICKED UP" if PICKED_UP_RE.fullmatch(status.strip()) else status

def status_counts(reports):
    counts = {}
    for r in reports:
        key = norm_status(r.get("Status")) or "No status"
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))

# Agents-DB page ids (Agents data source a2ee467b-2657-4173-b36e-df538f6e35e3), checked 2026-10-06 by Notion fetch.
# Bennett 10/5 18:10: "Dash, Dot, and Hank run everything." Mack (Claude MB CLI) stays because it checked in
# within 24 h (2026-10-05T14:18:48Z) and its tick loop writes Check-ins. Retired seats (Grok ST, Rocky) and seats
# with no check-in in 24 h (Cursor MB, Grant, Brock) were removed; they still show under additional agents.
PRIMARY_AGENT_IDS = (
    "3edcf5514fd3812ea137d3ce41dafab3",  # Dash
    "3edcf5514fd381c18e9ad31f16369f38",  # Dot
    "3edcf5514fd3815aa780ca4aff45c771",  # Hank
    "3edcf5514fd381d7a91dd8a7bdcccb87",  # Mack (Claude MB CLI)
)

# Exact owned work tuple used for server-side joins only. IDs are never emitted.
OWNED_WORK_AGENT = "3f2cf5514fd38173bfecc443d79590d0"
OWNED_WORK_PROJECT = "3f2cf5514fd381eebbb8f8937d504b2b"
def owned_work_projection(projects, reports, now=None, max_age_minutes=5):
    """Separate current exact-related report facts from project-recorded facts."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    p = next((x for x in projects if norm_id(x.get("url")) == OWNED_WORK_PROJECT), None)
    candidates, uncertain = [], False
    for r in reports:
        agent_links = [norm_id(x) for x in (r.get("Agent") or [])]
        project_links = [norm_id(x) for x in (r.get("Project") or [])]
        possible = OWNED_WORK_AGENT in agent_links and OWNED_WORK_PROJECT in project_links
        if ((OWNED_WORK_PROJECT in project_links and r.get("_agent_relation_complete") is False)
                or (OWNED_WORK_AGENT in agent_links and r.get("_project_relation_complete") is False)):
            uncertain = True
        if possible:
            logged = timestamp(r.get("Logged"))
            if logged is None:
                uncertain = True
            else:
                candidates.append((logged, r))
    latest = None
    ambiguous = False
    future = False
    if candidates:
        newest_time = max(t for t, _ in candidates)
        newest = [r for t, r in candidates if t == newest_time]
        future = newest_time > now
        signatures = {(r.get("Progress %"), _public_status(r.get("Status"))) for r in newest}
        ambiguous = len(signatures) > 1
        if not future and not ambiguous:
            latest = newest[0]
    project_value = p.get("Progress %") if p else None
    project_value = _public_number(project_value, 0, 100)
    edited = p.get("_edited") if p else None
    edited_time = timestamp(edited)
    project_status = _public_status(p.get("Status")) if p and p.get("Status") else "UNKNOWN"
    current_value = _public_number(latest.get("Progress %"), 0, 100) if latest else None
    report_time = timestamp(latest.get("Logged")) if latest else None
    report_freshness = ("UNKNOWN" if latest is None or uncertain else
                        "STALE" if (now-report_time).total_seconds() > max_age_minutes*60 else "FRESH")
    if report_freshness == "UNKNOWN":
        current_value = None
    current_state = "SOURCED" if current_value is not None and report_freshness != "UNKNOWN" else "UNKNOWN"
    if ambiguous:
        current_state = "AMBIGUOUS"
    project_freshness = ("UNKNOWN" if edited_time is None else
                         "STALE" if edited_time > now or (now-edited_time).total_seconds() > 24*3600 else "FRESH")
    return {"label":"CEO clock-in repair", "scope":"Current report and project-recorded progress are separate source values; neither implies runtime or deployment completion.",
            "progress":current_value, "progress_state":current_state,
            "status":_public_status(latest.get("Status")) if latest and report_freshness != "UNKNOWN" else "UNKNOWN",
            "as_of":latest.get("Logged") if latest and report_freshness != "UNKNOWN" else None,
            "freshness":report_freshness,
            "checkin_status":_public_status(latest.get("Status")) if latest and report_freshness != "UNKNOWN" else "UNKNOWN",
            "checkin_logged":latest.get("Logged") if latest and report_freshness != "UNKNOWN" else None,
            "checkin_state":"AMBIGUOUS" if ambiguous else "MATCHED" if latest and report_freshness != "UNKNOWN" else "UNKNOWN",
            "project_progress":project_value, "project_progress_state":"SOURCED" if project_value is not None else "UNKNOWN",
            "project_status":project_status, "project_as_of":edited if p else None,
            "project_freshness":project_freshness,
            "mismatch":bool(current_value is not None and project_value is not None and current_value != project_value)}

def project_checkins(reports, cutoff=None):
    """Newest linked check-in per project over the complete check-in scan (not the capped feed)."""
    cutoff = cutoff or datetime.datetime.now(datetime.timezone.utc)
    out = {}
    for r in reports:
        logged = timestamp(r.get("Logged"))
        if logged is None or logged > cutoff:
            continue
        for pid in r.get("Project") or []:
            cur = out.setdefault(pid, {"latest_logged": None, "rows": 0})
            cur["rows"] += 1
            if cur["latest_logged"] is None or logged > timestamp(cur["latest_logged"]):
                cur["latest_logged"] = r["Logged"]
    return out

def timestamp(value):
    if not isinstance(value, str) or "T" not in value:
        return None
    try:
        parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo is not None else None
    except ValueError:
        return None

# Logged and created_time are minute-resolution in Notion, so a pickup and its result often share a minute.
# Within one minute an opening report (ACK, PICKED UP, CLOCK-IN) ranks below any other status, so the seat's
# latest card shows the result, not the pickup (dash-audit 2026-10-06: qwen@studio showed PICKED UP while its
# 14:40:44 FINISHED row sat in the same minute). Page id stays the last tie-break so the order is deterministic.
OPENING_STATUSES = {"ACK", "PICKED UP", "CLOCK-IN"}

def same_minute_rank(r):
    return 0 if str(norm_status(r.get("Status")) or "").strip().upper() in OPENING_STATUSES else 1

def report_coverage(reports, agents, devices, projects, cutoff=None):
    # Scan to exhaustion before limiting the activity feed. Never infer absence from a cap.
    unique = {r["url"]: r for r in reports}
    source_rows = sorted(unique.values(), key=lambda r: (timestamp(r.get("Logged")) or datetime.datetime.min.replace(tzinfo=datetime.timezone.utc), same_minute_rank(r), r["url"]), reverse=True)
    cutoff = cutoff or datetime.datetime.now(datetime.timezone.utc)
    complete = all(r.get("_agent_relation_complete", True) for r in source_rows)
    known_agents = {a["url"] for a in agents}
    known_devices = {d["url"] for d in devices}
    known_projects = {p["url"] for p in projects}
    per_agent = {}
    for agent_id in known_agents | set(PRIMARY_AGENT_IDS):
        linked = [r for r in source_rows if agent_id in (r.get("Agent") or [])]
        valid = [r for r in linked if timestamp(r.get("Logged")) is not None and timestamp(r["Logged"]) <= cutoff]
        invalid = [r for r in linked if r not in valid]
        latest = valid[0] if valid else None
        valid_older = [timestamp(r.get("Time")) for r in valid[1:]
                       if timestamp(r.get("Time")) is not None and timestamp(r.get("Logged")) is not None
                       and timestamp(r.get("Time")) <= timestamp(r.get("Logged"))]
        worker_time = timestamp(latest.get("Time")) if latest else None
        latest_replayed = bool(worker_time and valid_older and worker_time <= max(valid_older))
        per_agent[agent_id] = {"agent_id": agent_id, "included": agent_id in known_agents,
                               "exhaustive": complete, "matching_rows": len(linked),
                               "invalid_receipt_rows": len(invalid), "latest_invalid_receipt": invalid[0] if invalid else None,
                               "latest": latest, "latest_replayed": latest_replayed}
    return source_rows, {"source": DB["checkins"], "exhaustive": complete,
                         "receipt_cutoff": cutoff.isoformat().replace("+00:00", "Z"),
                         "truncated_agent_relation_rows": sum(r.get("_agent_relation_complete") is False for r in source_rows),
                         "rows_scanned": len(reports), "unique_rows": len(unique),
                         "duplicate_row_ids": len(reports)-len(unique),
                         "unlinked_rows": sum(not r.get("Agent") for r in source_rows),
                         "unknown_agent_links": sum(i not in known_agents for r in source_rows for i in (r.get("Agent") or [])),
                         "unknown_device_links": sum(i not in known_devices for r in source_rows for i in (r.get("Device") or [])),
                         "unknown_project_links": sum(i not in known_projects for r in source_rows for i in (r.get("Project") or [])),
                         "per_agent": per_agent}

def collapse_heartbeats(rows_desc):
    """Fold consecutive identical reports from one agent (same Doing now and Status) into its newest row.

    rows_desc must be newest first. Other agents' rows in between do not break a run, so a 2-minute
    heartbeat flood from one agent cannot crowd every other agent out of the capped feed."""
    out, last_by_agent = [], {}
    for r in rows_desc:
        agent = tuple(sorted(r.get("Agent") or []))
        key = (" ".join(str(r.get("Doing now") or "").split()).lower(), str(r.get("Status") or "").upper())
        prev = last_by_agent.get(agent)
        if agent and prev is not None and prev[0] == key:
            kept = prev[1]
            kept["_repeats"] = kept.get("_repeats", 1) + 1
            kept["_first_logged"] = r.get("Logged")
            continue
        kept = dict(r)
        out.append(kept)
        last_by_agent[agent] = (key, kept)
    return out

def is_done(status):
    return re.sub(r"^[^A-Za-z]+", "", str(status or "")).strip().lower() == "done"

def source_error(route, error):
    """Only bounded status metadata leaves an HTTP failure; never raw body or message."""
    record = {"route": route, "status": None, "error_code": "transport_error", "request_id": None}
    if not isinstance(error, urllib.error.HTTPError):
        return record
    record["status"] = error.code
    allowed = {"invalid_json", "invalid_request_url", "invalid_request", "validation_error",
               "missing_version", "unauthorized", "restricted_resource", "object_not_found",
               "conflict_error", "rate_limited", "internal_server_error", "bad_gateway",
               "service_unavailable", "database_connection_unavailable", "gateway_timeout"}
    record["error_code"] = "unknown_http_error"
    headers = error.headers or {}
    request_id = headers.get("x-request-id") or headers.get("X-Request-Id")
    try:
        body = json.loads(error.read(4096))
        if isinstance(body, dict):
            if body.get("code") in allowed:
                record["error_code"] = body["code"]
            request_id = request_id or body.get("request_id")
    except (ValueError, OSError, AttributeError, TypeError):
        pass
    finally:
        error.close()
    if isinstance(request_id, str) and re.fullmatch(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", request_id):
        record["request_id"] = request_id
    return record

def aiceo_rows(diagnostics=None):
    """Historical Plan/Audit/Run coverage; separate from the current command-center hub."""
    diagnostics = diagnostics if diagnostics is not None else []
    try:
        try:
            pages = q(DATA_SOURCES["aiceo"], {}, route="data_sources", version="2025-09-03")
            diagnostics.append({"route": "data_sources", "status": 200, "error_code": None, "request_id": None})
        except urllib.error.HTTPError as e:
            diagnostics.append(source_error("data_sources", e))
            if e.code not in (400, 404):
                raise
            try:
                pages = q(AICEO_DB, {})
                diagnostics.append({"route": "databases", "status": 200, "error_code": None, "request_id": None})
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError) as fallback:
                diagnostics.append(source_error("databases", fallback))
                raise
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            diagnostics.append(source_error("data_sources", e))
            raise
    except urllib.error.HTTPError as e:
        return [], f"Historical AI CEO coverage not readable with the build connection (HTTP {e.code}); not published."
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        return [], "Historical AI CEO coverage read failed; not published."
    out = []
    for pg in pages:
        props = pg.get("properties", {})
        r = {"url": pg["id"].replace("-", "")}
        for name in AICEO_FIELDS:
            if name == "date:Date:start":
                p = props.get(name) or props.get("Date")
                r["Date"] = val(p) if p else None
            else:
                r[name] = val(props[name]) if name in props else None
        out.append(r)
    return out, f"{len(out)} rows read"

# SHIP-23 Ad Reports tab, read from the 📊 Ad Reports data source (Command Center). Brand names, spend, leads
# and CPL are internal until ad_reports_public.json says publish_figures: true (Bennett's call, human gate);
# until then the public page shows only which brand-weeks have a report on file, under "Brand N" labels.
AD_REPORTS_DS = "3e13833b1cc044bbb3b26523dad05e8d"
AD_REPORTS_DB = "96e521a4224842948fd507374c48dcf2"
AD_BRANDS = ("SH", "Indy Clover", "SRP", "Loft", "Advaita", "FKI")
AD_PUBLISH_FILE = "ad_reports_public.json"

def load_ad_publish(path=AD_PUBLISH_FILE):
    """True only when the committed file says exactly publish_figures: true. Anything else keeps figures private."""
    try:
        return json.loads(Path(path).read_text()).get("publish_figures") is True
    except (OSError, ValueError, AttributeError):
        return False

def ad_report_rows():
    try:
        try:
            pages = q(AD_REPORTS_DS, {}, route="data_sources", version="2025-09-03")
        except urllib.error.HTTPError as e:
            if e.code not in (400, 404):
                raise
            pages = q(AD_REPORTS_DB, {})
    except urllib.error.HTTPError as e:
        return [], f"Ad Reports not readable with the build connection (HTTP {e.code})."
    except (urllib.error.URLError, TimeoutError, ValueError):
        return [], "Ad Reports read failed."
    out = []
    for pg in pages:
        props = pg.get("properties", {})
        r = {"url": pg["id"].replace("-", "")}
        for name in ("Brand", "Week start", "Spend", "Leads", "CPL", "Pull time"):
            r[name] = val(props[name]) if name in props else None
        out.append(r)
    return out, f"{len(out)} rows read"

def ad_weeks(at):
    """The last two full Monday-start weeks before the current one, newest first."""
    monday = at.date() - datetime.timedelta(days=at.weekday())
    return [(monday - datetime.timedelta(days=7 * n)).isoformat() for n in (1, 2)]

def ad_reports_projection(src, at, publish):
    """Every brand x last-two-weeks cell, filed or not. Figures and real brand names only when publish is True."""
    weeks = ad_weeks(at)
    rows = src.get("rows") or []
    cells, labels = [], []
    for i, brand in enumerate(AD_BRANDS, 1):
        label = brand if publish else f"Brand {i}"
        labels.append(label)
        for week in weeks:
            start = datetime.date.fromisoformat(week)
            hits = []
            for r in rows:
                try:
                    d = datetime.date.fromisoformat(str(r.get("Week start") or "")[:10])
                except ValueError:
                    continue
                if r.get("Brand") == brand and start <= d < start + datetime.timedelta(days=7):
                    hits.append(r)
            hit = max(hits, key=lambda r: str(r.get("Pull time") or "")) if hits else None
            cell = {"brand": label, "week": week, "filed": hit is not None,
                    "spend": None, "leads": None, "cpl": None, "pulled": None}
            if publish and hit:
                cell.update(spend=_public_number(hit.get("Spend"), 0), leads=_public_number(hit.get("Leads"), 0),
                            cpl=_public_number(hit.get("CPL"), 0), pulled=_public_time(hit.get("Pull time")))
            cells.append(cell)
    read = src.get("status") == f"{len(rows)} rows read"
    return {"weeks": weeks, "brands": labels, "figures": bool(publish), "state": "available" if read else "unavailable",
            "filed": sum(c["filed"] for c in cells), "cells": cells}

def snapshot():
    new = {"sorts": [{"timestamp": "created_time", "direction": "descending"}]}
    snap = {k: rows(k) for k in DB if k not in ("checkins", "tasks", "coceo")}
    all_reports = rows("checkins", new)
    reports, coverage = report_coverage(all_reports, snap["agents"], snap["devices"], snap["projects"])
    snap["tracked_work"] = owned_work_projection(snap["projects"], all_reports)
    feed = collapse_heartbeats(reports)
    coverage["collapsed_repeats"] = len(reports) - len(feed)
    snap["checkins"] = feed[:200]
    snap["report_coverage"] = coverage
    snap["primary_agents"] = list(PRIMARY_AGENT_IDS)
    snap["project_checkins"] = project_checkins(reports)
    snap["coceo"] = rows("coceo", new, 60)
    all_tasks = rows("tasks")
    snap["tasks"] = [t for t in all_tasks if not is_done(t.get("Status"))]
    aiceo_diagnostics = []
    snap["aiceo"], snap["aiceo_status"] = aiceo_rows(aiceo_diagnostics)
    print("historical_aiceo_routes:", json.dumps(aiceo_diagnostics, sort_keys=True))
    aiceo_read = snap["aiceo_status"] == f"{len(snap['aiceo'])} rows read"
    snap["aiceo_coverage"] = {"state": ("available" if snap["aiceo"] else "empty") if aiceo_read else "unavailable",
                              "exhaustive": aiceo_read, "public_rows": len(snap["aiceo"]) if aiceo_read else None}
    snap["counts"] = {"agents": len(snap["agents"]), "tasks_total": len(all_tasks), "tasks_open": len(snap["tasks"]),
                      "checkins": coverage["unique_rows"], "checkins_feed_rows": len(feed), "aiceo": len(snap["aiceo"]),
                      "checkin_status": status_counts(reports)}
    snap["asks"] = load_asks()
    ad_rows, ad_status = ad_report_rows()
    snap["ad_reports"] = {"rows": ad_rows, "status": ad_status, "publish": load_ad_publish()}
    print("ad_reports:", ad_status)
    snap["fleet"] = fleet_status(load_fleet(), reports, snap["agents"], snap["projects"])
    return snap

def load_fleet(path="agents48.json"):
    """The Agents tab: each working lane, its route and its 48-hour projects (plan by W23, committed file).
    Only these keys reach the page, and the snapshot still goes through exclude() and scrub()."""
    p = Path(path)
    if not p.exists():
        return {"lanes": [], "projects": [], "hard_lines": [], "updated": None, "window": None,
                "window_end": None, "status_as_of": None}
    raw = json.loads(p.read_text())
    lane_keys = ("key", "lane", "route", "focus", "current", "board_agent", "thread", "thread_match", "queue")
    proj_keys = ("id", "lane", "title", "goal", "done_test", "proof_type", "subagents", "first_3_tasks",
                 "eta_hours", "protected_steps", "status", "hours_left", "last_checkin", "latest_proof")
    return {"updated": raw.get("updated"), "window": raw.get("window"), "window_end": raw.get("window_end"),
            "status_as_of": raw.get("status_as_of"), "hard_lines": raw.get("hard_lines") or [],
            "lanes": [{k: l.get(k) for k in lane_keys} for l in raw.get("lanes") or []],
            "projects": [{k: q.get(k) for k in proj_keys} for q in raw.get("projects") or []]}

def fleet_status(fleet, reports, agents, projects, at=None):
    """Fill each 48-hour project's live status, hours left and latest proof at build time (W29 fix 4).
    Evidence is a check-in whose Doing now or Proof names the project id (GA1, DT2, ...) or that links the hub
    Projects row titled with that id. With no such check-in the committed values stay, so nothing is invented."""
    at = at or datetime.datetime.now(datetime.timezone.utc)
    names = {a["url"]: a.get("Agent") or "unknown agent" for a in agents}
    end = timestamp(fleet.get("window_end"))
    for q in fleet.get("projects") or []:
        pid_ = str(q.get("id") or "")
        if not pid_:
            continue
        word = re.compile(r"(?<![A-Za-z0-9])" + re.escape(pid_) + r"(?![A-Za-z0-9])")
        hub = [p for p in projects if word.match(str(p.get("Project") or "").strip())]
        hub_ids = {p["url"] for p in hub}
        hits = [r for r in reports if timestamp(r.get("Logged")) is not None and (
                word.search(" ".join(str(r.get(k) or "") for k in ("Doing now", "Proof")))
                or hub_ids & set(r.get("Project") or []))]
        hits.sort(key=lambda r: timestamp(r["Logged"]), reverse=True)
        last = hits[0] if hits else None
        if hub and hub[0].get("Status"):
            q["status"] = f"{hub[0]['Status']} (hub project row)"
        elif last:
            q["status"] = f"{str(last.get('Status') or 'Reported').capitalize()} · {len(hits)} check-in{'s' if len(hits) != 1 else ''}"
        if last:
            q["last_checkin"] = last.get("Logged")
            proof = str(last.get("Proof") or "").strip()
            who = ", ".join(names.get(i, "unlinked agent") for i in (last.get("Agent") or [])) or "unlinked agent"
            if proof.startswith("https://"):
                q["latest_proof"] = {"text": f"{who} · {last.get('Logged')}", "url": proof}
            elif proof:
                q["latest_proof"] = {"text": f"{who} · {last.get('Logged')} · {proof[:160]}"}
        if end is not None:
            q["hours_left"] = round(max(0.0, (end - at).total_seconds() / 3600), 1)
    fleet["status_as_of"] = at.isoformat().replace("+00:00", "Z")
    return fleet

def load_asks(path="asks.json"):
    """Bennett's asks, lane owners and Needs-you rows, hand-kept in a committed file. Only these keys
    reach the page; the snapshot still goes through exclude() and scrub() like every Notion row."""
    p = Path(path)
    if not p.exists():
        return {"asks": [], "lanes": [], "needs_you": [], "updated": None}
    raw = json.loads(p.read_text())
    return {k: raw.get(k) for k in ("asks", "lanes", "needs_you", "updated", "sources")}

# Public scrub. Protected terms come only from the environment (repo secret SCRUB_TERMS) or a local
# file named by SCRUB_TERMS_FILE; they are never committed. Token prefixes are written as character
# classes so this file itself carries no token-shaped text.
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
# Digits inside URLs, ids and paths (run ids, query values) are not phone numbers, so a run must not touch / = # . or -.
PHONE_RE = re.compile(r"(?<![\w/=#.-])(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}(?![\w/-])|(?<![\w/=#.+-])\+?1?\d{10}(?![\w/.-])")
TOKEN_RE = re.compile(r"(?:n[t]n_|secre[t]_|gh[po]_|s[k]-|x[o]x[a-z]-)[A-Za-z0-9_-]{8,}")
ID_RE = re.compile(r"[0-9a-f]{32}")

def scrub_terms():
    raw = os.environ.get("SCRUB_TERMS", "")
    path = os.environ.get("SCRUB_TERMS_FILE")
    if path and Path(path).is_file():
        raw += "\n" + Path(path).read_text()
    terms = sorted({t.strip() for t in re.split(r"[\n,]", raw) if len(t.strip()) >= 3}, key=len, reverse=True)
    if not terms and os.environ.get("REQUIRE_SCRUB_TERMS") == "1":
        raise SystemExit("scrub: REQUIRE_SCRUB_TERMS=1 but no terms were loaded")
    return terms

def scrub(snap, terms=None):
    """Return (clean copy, replacement count). Ids stay intact; every other string is scrubbed."""
    terms = scrub_terms() if terms is None else terms
    term_re = re.compile("|".join(re.escape(t) for t in terms), re.IGNORECASE) if terms else None
    hits = 0
    def text(s):
        nonlocal hits
        if ID_RE.fullmatch(s):
            return s
        for rx, repl in ((term_re, "[private]"), (TOKEN_RE, "[redacted token]"),
                         (EMAIL_RE, "[redacted email]"), (PHONE_RE, "[redacted phone]")):
            if rx is not None:
                s, n = rx.subn(repl, s)
                hits += n
        return s
    def walk(v):
        if isinstance(v, str):
            return text(v)
        if isinstance(v, list):
            return [walk(x) for x in v]
        if isinstance(v, dict):
            return {k: walk(x) for k, x in v.items()}
        return v
    return walk(snap), hits

# Rows kept off the public page by Notion page id: public-exclude.txt holds one id per line (dashes optional,
# '#' starts a comment). The Notion rows themselves are untouched. A missing or malformed list stops the build.
EXCLUDE_FILE = "public-exclude.txt"

def norm_id(s):
    return str(s).strip().lower().replace("-", "")

def excluded_ids(path=EXCLUDE_FILE):
    p = Path(path)
    if not p.is_file():
        raise SystemExit(f"exclude: {path} missing; refusing to publish without it")
    ids = {norm_id(line.split("#", 1)[0]) for line in p.read_text().splitlines()} - {""}
    bad = [i for i in ids if not ID_RE.fullmatch(i)]
    if bad:
        raise SystemExit(f"exclude: {len(bad)} malformed id line(s) in {path}")
    return ids

def exclude(snap, ids):
    """Return (copy without listed rows, dropped row count). A list item whose url is listed is dropped from
    every section, a listed id in a relation list is removed, a dict value pointing at a listed row becomes None,
    and any other mention of a listed id (dashed or not) is replaced, so no listed id reaches the page."""
    if not ids:
        return snap, 0
    id_re = re.compile("|".join(f"{i[:8]}-?{i[8:12]}-?{i[12:16]}-?{i[16:20]}-?{i[20:]}" for i in sorted(ids)), re.IGNORECASE)
    dropped = 0
    def listed(v):
        if isinstance(v, dict):
            return norm_id(v.get("url") or "") in ids
        return isinstance(v, str) and norm_id(v) in ids
    def walk(v):
        nonlocal dropped
        if isinstance(v, str):
            return id_re.sub("[excluded]", v)
        if isinstance(v, list):
            dropped += sum(isinstance(x, dict) and listed(x) for x in v)
            return [walk(x) for x in v if not listed(x)]
        if isinstance(v, dict):
            return {walk(k): (None if listed(x) else walk(x)) for k, x in v.items() if not listed(k)}
        return v
    return walk(snap), dropped

PUBLIC_STATUSES = {
    "ACK", "PICKED UP", "CLOCK-IN", "CLOCK IN", "CLOCKED OUT", "BLOCKED", "DONE", "COMPLETED",
    "FINISHED", "IN PROGRESS", "STARTED", "READY", "PENDING", "WAITING", "PLANNED",
    "ACTIVE", "WORKING", "ON TRACK", "PAUSED", "STUCK", "ON HOLD", "NEW", "NEEDS YOU", "NEEDS INPUT", "UNPROVED",
    "NOT STARTED", "CANCELLED", "ARCHIVED", "PARKED", "RETIRED", "INACTIVE", "OPEN",
    "CLOSED", "OK", "ERROR", "FAILED", "UNKNOWN", "NO STATUS", "REPORTED", "ALIVE",
    "NOT TESTED", "NOTHING", "OFFLINE", "CLOCK-OUT", "MOVING",
}

def _public_status(value):
    """Map exact, reviewed operational values; never normalize arbitrary emoji/free text."""
    if not isinstance(value, str):
        return "UNKNOWN"
    key = " ".join(value.strip().upper().split())
    exact = {s: s for s in PUBLIC_STATUSES}
    exact.update({"🟢 ALIVE": "ALIVE", "🟢ALIVE": "ALIVE", "🟡 WORKING": "WORKING", "🟡WORKING": "WORKING",
                  "⚪ NOT TESTED": "NOT TESTED", "⚪NOT TESTED": "NOT TESTED", "⛔ RETIRED": "RETIRED", "⛔RETIRED": "RETIRED",
                  "🟡 MOVING": "MOVING", "🟡MOVING": "MOVING",
                  "NOTHING": "NOTHING", "OFFLINE": "OFFLINE", "CLOCK-OUT": "CLOCK-OUT",
                  "CLOCK OUT": "CLOCK-OUT"})
    return exact.get(key, "UNKNOWN")

# Explicit code-owned seat registry. Names and aliases are never derived from arbitrary Notion text.
PUBLIC_SEAT_REGISTRY = {
    "3f2cf5514fd38173bfecc443d79590d0": ("agent-be434c7128d6", "ChadCodexMacBook", ("Chad", "Chad (Codex, MacBook)")),
    "3f1cf5514fd381f0a4c9cd7365e678c5": ("agent-dccd31c7f1d5", "GemmaTiffany", ("Gemma", "Gemma (Tiffany)")),
    "3edcf5514fd38131bd00e1080bf6d826": ("agent-0c2ff5563abd", "GrantGrokMacBook", ("Grok MB (Grant)",)),
    "3edcf5514fd381ecb7a7f9c2f8411b1d": ("agent-7efe68c9217a", "BrockGrokiMac", ("Grok IM (Brock)",)),
    "3edcf5514fd381d7a91dd8a7bdcccb87": ("agent-62eae1732e58", "MackClaudeMacBook", ("Claude MB CLI",)),
    "3edcf5514fd3812ea137d3ce41dafab3": ("agent-fdf92af87157", "Dash", ("Dash",)),
    "3edcf5514fd3815aa780ca4aff45c771": ("agent-2ea55c7dfbf0", "Hank", ("Hank",)),
    "3edcf5514fd381c18e9ad31f16369f38": ("agent-9e2c65b86258", "Dot", ("Dot",)),
}
_PUBLIC_SEAT_NAMES = {name.casefold(): alias for _, (alias, _, names) in PUBLIC_SEAT_REGISTRY.items() for name in names}

def _stable_alias(kind, source_id):
    import hashlib
    normalized = norm_id(str(source_id or ""))
    if kind == "agent" and normalized in PUBLIC_SEAT_REGISTRY:
        return PUBLIC_SEAT_REGISTRY[normalized][0]
    digest = hashlib.sha256(normalized.encode()).hexdigest()[:12] if normalized else "unknown000000"
    return f"{kind}-unknown-{digest}" if kind == "agent" else f"{kind}-{digest}"

def _seat_label(name):
    return _PUBLIC_SEAT_NAMES.get(str(name or "").casefold(), "Unknown seat")

def _public_time(value):
    parsed = timestamp(value)
    return parsed.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z") if parsed else None

def _public_number(value, low=None, high=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not __import__("math").isfinite(value) or (low is not None and value < low) or (high is not None and value > high):
        return None
    return value

def public_projection(snap):
    """Structural public-data allowlist. Free text and source IDs never cross serialization.

    This deliberately does not depend on SCRUB_TERMS: source titles, Doing/blocker/proof text,
    contacts, arbitrary attributes, and Notion IDs are excluded by construction. Useful status,
    aggregate coverage, freshness, and the separately verified owned-work percentage survive.
    """
    agents = snap.get("agents") or []
    projects = snap.get("projects") or []
    devices = snap.get("devices") or []
    agent_ids = {str(a.get("url")): _stable_alias("agent", a.get("url")) for a in agents if a.get("url")}
    project_ids = {str(p.get("url")): _stable_alias("project", p.get("url")) for p in projects if p.get("url")}
    device_ids = {str(d.get("url")): _stable_alias("device", d.get("url")) for d in devices if d.get("url")}

    def refs(values, mapping):
        return [mapping[str(v)] for v in values or [] if str(v) in mapping]
    out_agents = [{"url": agent_ids[str(a.get("url"))], "Agent": PUBLIC_SEAT_REGISTRY.get(norm_id(str(a.get("url"))), (None, "Unknown seat"))[1],
                   "Status": _public_status(a.get("Status")), "Projects": refs(a.get("Projects"), project_ids),
                   "Device": refs([a.get("Device")] if a.get("Device") else [], device_ids)}
                  for a in agents if str(a.get("url")) in agent_ids]
    out_projects = [{"url": project_ids[str(p.get("url"))], "Project": f"Project {project_ids[str(p.get('url'))].split('-')[-1]}",
                     "Company": "Other", "Status": _public_status(p.get("Status")),
                     "Progress %": _public_number(p.get("Progress %"), 0, 100),
                     "Last %": _public_number(p.get("Last %"), 0, 100),
                     "Agents": refs(p.get("Agents"), agent_ids),
                     "_edited": _public_time(p.get("_edited"))}
                  for p in projects if str(p.get("url")) in project_ids]
    out_devices = [{"url": device_ids[str(d.get("url"))], "Device": "Device", "Type": "Device"}
                   for d in devices if str(d.get("url")) in device_ids]
    coverage = snap.get("report_coverage") or {}
    per_agent = {}
    for raw_id, c in (coverage.get("per_agent") or {}).items():
        alias = agent_ids.get(str(raw_id))
        if alias is None:
            # Preserve primary-seat coverage when a primary registration row is absent.
            alias = _stable_alias("agent", raw_id)
        latest = c.get("latest") or {}
        latest_agent_refs = refs(latest.get("Agent"), agent_ids)
        latest_public = ({"Status": _public_status(latest.get("Status")), "Logged": _public_time(latest.get("Logged")),
                         "Time": _public_time(latest.get("Time")), "Agent": latest_agent_refs}
                        if latest else None)
        invalid = c.get("latest_invalid_receipt") or {}
        per_agent[alias] = {"agent_id": alias, "included": bool(c.get("included")),
                            "exhaustive": bool(c.get("exhaustive")),
                            "matching_rows": _public_number(c.get("matching_rows"), 0),
                            "invalid_receipt_rows": _public_number(c.get("invalid_receipt_rows"), 0),
                            "latest_invalid_receipt": ({"Logged": _public_time(invalid.get("Logged"))} if invalid else None),
                            "latest": latest_public, "latest_replayed": bool(c.get("latest_replayed"))}
    safe_status_counts = {}
    for status, n in ((snap.get("counts") or {}).get("checkin_status") or {}).items():
        safe = _public_status(status)
        safe_status_counts[safe] = safe_status_counts.get(safe, 0) + int(_public_number(n, 0) or 0)
    count_source = snap.get("counts") or {}
    counts = {key: int(_public_number(count_source.get(key), 0) or 0)
              for key in ("agents", "tasks_total", "tasks_open", "checkins", "checkins_feed_rows", "aiceo")}
    for key, source in (("coceo", "coceo"), ("caio", "caio"), ("crons", "crons"),
                        ("fat20", "fat20"), ("fleet_projects", "fleet"), ("asks", "asks")):
        rows = (snap.get("fleet") or {}).get("projects") if source == "fleet" else ((snap.get("asks") or {}).get("asks") if source == "asks" else snap.get(source))
        counts[key] = len(rows or [])
    counts["checkin_status"] = safe_status_counts
    out_checkins = []
    for i, r in enumerate(snap.get("checkins") or [], 1):
        out_checkins.append({"Agent": refs(r.get("Agent"), agent_ids), "Logged": _public_time(r.get("Logged")),
                             "Time": _public_time(r.get("Time")), "Status": _public_status(r.get("Status")),
                             "Project": refs(r.get("Project"), project_ids), "Device": refs(r.get("Device"), device_ids),
                             "_repeats": int(_public_number(r.get("_repeats", 1), 1) or 1),
                             "_first_logged": _public_time(r.get("_first_logged"))})
    project_checkins = {}
    for raw_id, v in (snap.get("project_checkins") or {}).items():
        key = project_ids.get(str(raw_id))
        if key:
            project_checkins[key] = {"latest_logged": _public_time(v.get("latest_logged")),
                                     "rows": _public_number(v.get("rows"), 0)}
    tracked = snap.get("tracked_work") or {}
    tracked_progress = _public_number(tracked.get("progress"), 0, 100)
    project_progress = _public_number(tracked.get("project_progress"), 0, 100)
    out_tracked = {"label": "CEO clock-in repair", "scope": "Current report and project-recorded progress are separate source values; neither implies runtime or public deployment completion.",
                   "progress": tracked_progress, "progress_state": tracked.get("progress_state") if tracked.get("progress_state") in {"SOURCED", "UNKNOWN", "AMBIGUOUS"} and (tracked_progress is not None or tracked.get("progress_state") == "AMBIGUOUS") else "UNKNOWN",
                   "status": _public_status(tracked.get("status")),
                   "as_of": _public_time(tracked.get("as_of")),
                   "freshness": tracked.get("freshness") if tracked.get("freshness") in {"FRESH", "STALE", "UNKNOWN"} else "UNKNOWN",
                   "checkin_status": _public_status(tracked.get("checkin_status")),
                   "checkin_logged": _public_time(tracked.get("checkin_logged")),
                   "checkin_state": tracked.get("checkin_state") if tracked.get("checkin_state") in {"MATCHED", "UNKNOWN", "AMBIGUOUS"} else "UNKNOWN",
                   "project_progress": project_progress,
                   "project_progress_state": "SOURCED" if project_progress is not None and tracked.get("project_progress_state") == "SOURCED" else "UNKNOWN",
                   "project_status": _public_status(tracked.get("project_status")),
                   "project_as_of": _public_time(tracked.get("project_as_of")),
                   "project_freshness": tracked.get("project_freshness") if tracked.get("project_freshness") in {"FRESH", "STALE", "UNKNOWN"} else "UNKNOWN",
                   "mismatch": bool(tracked.get("mismatch"))}
    out_tasks = [{"Focus": "__YES__" if t.get("Focus") == "__YES__" else "__NO__",
                  "Name": f"Open task {i}", "Owner": _seat_label(t.get("Owner")),
                  "Status": _public_status(t.get("Status")), "Progress %": _public_number(t.get("Progress %"), 0, 100)}
                  for i, t in enumerate(snap.get("tasks") or [], 1)]
    out_coceo = [{"Logged": _public_time(x.get("Logged")),
                  "Author": refs(x.get("Author"), agent_ids), "Entry": f"Entry {i}",
                  "Type": _public_status(x.get("Type")), "Strategy note": "Details withheld",
                  "Audit verdict": x.get("Audit verdict") if x.get("Audit verdict") in {"AGREE", "CHALLENGE", "WRONG"} else None,
                  "Audit of partner": x.get("Audit of partner") if x.get("Audit of partner") in {"AGREE", "CHALLENGE", "WRONG"} else None}
                 for i, x in enumerate(snap.get("coceo") or [], 1)]
    out_caio = [{"Division": f"Division {i}", "Status": _public_status(x.get("Status")),
                 "Covers": "Details withheld", "Projects": refs(x.get("Projects"), project_ids),
                 "Order": _public_number(x.get("Order"), 0)}
                for i, x in enumerate(snap.get("caio") or [], 1)]
    safe_cadences = {"MINUTELY", "HOURLY", "DAILY", "WEEKLY", "MONTHLY", "ONCE", "INTERVAL", "SCHEDULED"}
    out_crons = [{"Routine": f"Routine {i}", "State": _public_status(x.get("State")),
                  "Cadence": str(x.get("Cadence")).upper() if str(x.get("Cadence") or "").upper() in safe_cadences else "Schedule withheld",
                  "Runs on": "Device", "Defined in": None}
                 for i, x in enumerate(snap.get("crons") or [], 1)]
    out_fat20 = [{"Rank": _public_number(x.get("Rank"), 0), "Item": f"Priority item {i}",
                  "Status": _public_status(x.get("Status")), "Progress %": _public_number(x.get("Progress %"), 0, 100)}
                 for i, x in enumerate(snap.get("fat20") or [], 1)]
    # Free-text project/task/ask/agent plans are not individually approved for publication.
    # Keep only generic lanes, safe status/freshness and numeric schedule/progress fields.
    fleet = snap.get("fleet") or {}
    safe_lanes, lane_names = [], {}
    group_names = {"dash": "Dash lane", "dot": "Dot lane", "grok": "Grok lane"}
    for i, lane in enumerate(fleet.get("lanes") or [], 1):
        key = str(lane.get("key") or "").lower()
        safe_key = key if key in group_names else f"lane-{i:03d}"
        lane_names[str(lane.get("lane") or "")] = group_names.get(key, f"Lane {i}")
        safe_lanes.append({"key": safe_key, "lane": group_names.get(key, f"Lane {i}"),
                           "board_agent": _seat_label(lane.get("board_agent")),
                           "focus": None, "current": None, "queue": None, "route": None, "thread": None,
                           "thread_match": None})
    safe_fleet_projects = []
    for i, q in enumerate(fleet.get("projects") or [], 1):
        lane = lane_names.get(str(q.get("lane") or ""), "Lane 1")
        safe_fleet_projects.append({"id": f"W{i}", "lane": lane, "title": f"Work item {i}",
                                    "goal": "Details withheld", "done_test": "Details withheld", "proof_type": None,
                                    "subagents": [], "first_3_tasks": [], "eta_hours": _public_number(q.get("eta_hours"), 0),
                                    "protected_steps": ["Protected step present"] if q.get("protected_steps") else [],
                                    "status": _public_status(q.get("status")),
                                    "hours_left": _public_number(q.get("hours_left"), 0),
                                    "last_checkin": _public_time(q.get("last_checkin")), "latest_proof": None})
    fleet_time = _public_time(fleet.get("updated"))
    out_fleet = {"updated": fleet_time, "window": _public_time(fleet.get("window")),
                 "window_end": _public_time(fleet.get("window_end")), "status_as_of": _public_time(fleet.get("status_as_of")),
                 "hard_lines": [], "lanes": safe_lanes, "projects": safe_fleet_projects}
    asks = snap.get("asks") or {}
    out_asks = {"updated": _public_time(asks.get("updated")), "sources": None,
                "asks": [{"n": int(_public_number(a.get("n"), 0) or i), "ask": f"Request {i}",
                          "owner": "Unknown", "lane": f"Lane {i}",
                          "status": _public_status(a.get("status")), "proof": None,
                          "updated": _public_time(a.get("updated"))}
                         for i, a in enumerate(asks.get("asks") or [], 1)],
                "lanes": [{"lane": f"Lane {i}", "owner": "Unknown", "does": "Details withheld",
                           "status": _public_status(l.get("status")), "report": "Status only"}
                          for i, l in enumerate(asks.get("lanes") or [], 1)],
                "needs_you": [{"what": f"Request {i}", "where": "Details withheld", "do": "Details withheld",
                               "done_when": "Details withheld"}
                              for i, _ in enumerate(asks.get("needs_you") or [], 1)]}
    out_aiceo = [{"Type": str(r.get("Type")).upper() if str(r.get("Type") or "").upper() in {"PLAN", "AUDIT", "RUN"} else "OTHER",
                  "Status": _public_status(r.get("Status")), "Seat": "Seat",
                  "Graded by": None, "Date": _public_time(r.get("Date"))}
                 for r in snap.get("aiceo") or []]
    report_coverage = {"exhaustive": bool(coverage.get("exhaustive")),
                       "receipt_cutoff": _public_time(coverage.get("receipt_cutoff")),
                       "collapsed_repeats": int(_public_number(coverage.get("collapsed_repeats"), 0) or 0),
                       "rows_scanned": int(_public_number(coverage.get("rows_scanned"), 0) or 0),
                       "unique_rows": int(_public_number(coverage.get("unique_rows"), 0) or 0),
                       "duplicate_row_ids": int(_public_number(coverage.get("duplicate_row_ids"), 0) or 0),
                       "unlinked_rows": int(_public_number(coverage.get("unlinked_rows"), 0) or 0),
                       "unknown_agent_links": int(_public_number(coverage.get("unknown_agent_links"), 0) or 0),
                       "unknown_device_links": int(_public_number(coverage.get("unknown_device_links"), 0) or 0),
                       "unknown_project_links": int(_public_number(coverage.get("unknown_project_links"), 0) or 0),
                       "per_agent": per_agent}
    aiceo_cov = snap.get("aiceo_coverage") or {}
    return {"agents": out_agents, "devices": out_devices, "projects": out_projects, "checkins": out_checkins,
            "tasks": out_tasks, "primary_agents": [agent_ids.get(str(i), _stable_alias("agent", i)) for i in (snap.get("primary_agents") or [])],
            "report_coverage": report_coverage, "project_checkins": project_checkins, "tracked_work": out_tracked,
            "counts": counts, "fleet": out_fleet, "asks": out_asks, "coceo": out_coceo, "caio": out_caio, "crons": out_crons,
            "fat20": out_fat20, "aiceo": out_aiceo,
            "ad_reports": ad_reports_projection(snap.get("ad_reports") or {}, timestamp(snap.get("ad_reports_at")) or datetime.datetime.now(datetime.timezone.utc),
                                                (snap.get("ad_reports") or {}).get("publish") is True),
            "aiceo_coverage": {"state": aiceo_cov.get("state") if aiceo_cov.get("state") in {"available", "empty", "unavailable"} else "unavailable",
                               "exhaustive": bool(aiceo_cov.get("exhaustive")),
                               "public_rows": int(_public_number(aiceo_cov.get("public_rows"), 0) or 0) if aiceo_cov.get("public_rows") is not None else None},
            "aiceo_status": "Source coverage available; row details are withheld." if aiceo_cov.get("state") != "unavailable" else "Source coverage unavailable; private diagnostics are withheld."}

CONTROL_FILE = "control.json"
NOTE_MAX = 200

def load_control(path=CONTROL_FILE):
    """Small file any seat can overwrite whole (no read needed) to steer the page."""
    try:
        c = json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return {"note": ""}
    note = str(c.get("note") or "").strip()[:NOTE_MAX]
    return {"note": note}

def note_html(note):
    return f'<div class="sub" id="note"><b>Note:</b> {html.escape(note)}</div>' if note else ""

def render(snap, at, control=None, sha=""):
    control = control if control is not None else {"note": ""}
    built = html.escape(at + (f" · {sha[:7]}" if sha else ""))
    safe = public_projection(snap)
    data = json.dumps(safe, ensure_ascii=False).replace("</", "<\\/")
    return (Path("template.html").read_text().replace("__REPORT_STATUS__", Path("report_status.js").read_text() + "\n" + (Path("big.js").read_text() if Path("big.js").is_file() else ""))
            .replace("__BUILT__", built).replace("__NOTE__", note_html(control["note"]))
            .replace("__AT__", at).replace("__SNAP__", data))

def main():
    terms, ids = scrub_terms(), excluded_ids()
    snap, dropped = exclude(snapshot(), ids)
    print(f"exclude: ids={len(ids)} dropped={dropped}")
    snap, hits = scrub(snap, terms)
    print(f"scrub: terms_loaded={len(terms)} replaced={hits}")
    at = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    site = Path("site")
    site.mkdir(exist_ok=True)
    control, sha = load_control(), os.environ.get("GITHUB_SHA", "")
    (site / "index.html").write_text(render(snap, at, control, sha))
    (site / "version.json").write_text(json.dumps({"built_at": at}))
    # Fresh path per change so readers never get a stale cache: build.json carries the commit and the live note.
    (site / "build.json").write_text(json.dumps({"built_at": at, "sha": sha, "note": control["note"]}))
    print("built", {k: len(v) for k, v in snap.items() if isinstance(v, list)}, "counts", snap["counts"], "aiceo:", snap["aiceo_status"], "at", at)

if __name__ == "__main__":
    main()
