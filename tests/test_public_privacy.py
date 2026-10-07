import re
import unittest
from datetime import datetime, timezone, timedelta

import build


class PublicPrivacyTests(unittest.TestCase):
    def test_whole_html_uses_structural_allowlist_and_keeps_sourced_owned_progress(self):
        aid = "a" * 32
        pid = "b" * 32
        did = "c" * 32
        rid = "d" * 32
        now = "2026-10-07T23:00:00Z"
        owned_source = build.owned_work_projection(
            [{"url": build.OWNED_WORK_PROJECT, "Progress %": 40, "Status": "IN PROGRESS", "_edited": now}],
            [{"url": build.OWNED_WORK_CHECKIN, "Agent": [build.OWNED_WORK_AGENT],
              "Project": [build.OWNED_WORK_PROJECT], "Logged": now, "Status": "PICKED UP"}],
            now=datetime.fromisoformat(now.replace("Z", "+00:00")))
        raw = {
            "agents": [{"url": aid, "Agent": "LEAK_AGENT_NAME", "Status": "ACTIVE", "Platform": "LEAK_DEVICE",
                        "Role": "LEAK_PRIVATE_ROLE", "Device": [did], "Projects": [pid], "email": "LEAK_EMAIL@example.invalid",
                        "lead_contact": "LEAK_LEAD_CONTACT", "phone": "LEAK_PHONE (555) 203-4444"}],
            "devices": [{"url": did, "Device": "LEAK_DEVICE", "Type": "LEAK_DEVICE_TYPE", "secret": "LEAK_DEVICE_SECRET"}],
            "projects": [{"url": pid, "Project": "LEAK_PRIVATE_PROJECT_TITLE", "Company": "LEAK_CLIENT",
                          "Status": "IN PROGRESS", "Progress %": 40, "Last %": 25,
                          "Finish condition": "LEAK_PRIVATE_FINISH", "Agents": [aid], "_edited": now,
                          "unapproved_extra": "LEAK_UNKNOWN_FIELD"}],
            "checkins": [{"url": rid, "Agent": [aid], "Logged": now, "Time": now, "Status": "BLOCKED",
                          "Doing now": "LEAK_PRIVATE_DOING", "Project": [pid], "Proof": "https://private.invalid/LEAK_PROOF",
                          "Device": [did], "Blocker question": "LEAK_PRIVATE_BLOCKER", "extra": "LEAK_CHECKIN_EXTRA"}],
            "report_coverage": {"source": "LEAK_PRIVATE_SOURCE_ID", "exhaustive": True, "receipt_cutoff": now,
                                "rows_scanned": 1, "unique_rows": 1, "collapsed_repeats": 0,
                                "per_agent": {aid: {"agent_id": aid, "included": True, "exhaustive": True,
                                    "matching_rows": 1, "invalid_receipt_rows": 0, "latest_replayed": False,
                                    "latest": {"url": rid, "Agent": [aid], "Logged": now, "Time": now,
                                               "Status": "BLOCKED", "Doing now": "LEAK_COVERAGE_DOING",
                                               "Blocker question": "LEAK_COVERAGE_BLOCKER", "Proof": "LEAK_COVERAGE_PROOF"},
                                    "latest_invalid_receipt": {"Logged": "LEAK_BAD_DATE", "Doing now": "LEAK_BAD_REPORT"}}}},
            "project_checkins": {pid: {"latest_logged": now, "rows": 1}, "LEAK_UNKNOWN_ID": {"title": "LEAK_ID_MAP"}},
            "primary_agents": [aid], "tracked_work": owned_source,
            "counts": {"agents": 1, "tasks_total": 1, "tasks_open": 1, "checkins": 1,
                       "checkins_feed_rows": 1, "aiceo": 1, "checkin_status": {"LEAK_COUNT_STATUS": 1}},
            "tasks": [{"Focus": "__YES__", "Name": "LEAK_PRIVATE_TASK_TITLE", "Owner": "LEAK_AGENT_NAME",
                       "Status": "IN PROGRESS", "Progress %": 60, "customer": "LEAK_TASK_CUSTOMER"}],
            "fleet": {"updated": now, "window": "LEAK_PRIVATE_WINDOW", "window_end": now, "status_as_of": now,
                      "hard_lines": ["LEAK_FLEET_RULE"], "lanes": [{"key": "dash", "lane": "LEAK_PRIVATE_LANE",
                        "board_agent": "LEAK_AGENT_NAME", "route": "LEAK_ROUTE", "focus": "LEAK_FOCUS",
                        "current": "LEAK_CURRENT", "queue": "LEAK_QUEUE", "thread": "LEAK_THREAD"}],
                      "projects": [{"id": "LEAK_WORK_ID", "lane": "LEAK_PRIVATE_LANE", "title": "LEAK_FLEET_TITLE",
                        "goal": "LEAK_GOAL", "done_test": "LEAK_DONE_TEST", "proof_type": "LEAK_PROOF_TYPE",
                        "subagents": ["LEAK_SUBAGENT"], "first_3_tasks": ["LEAK_FLEET_TASK"], "eta_hours": 3,
                        "protected_steps": ["LEAK_PROTECTED_DETAILS"], "status": "BLOCKED", "hours_left": 2,
                        "last_checkin": now, "latest_proof": {"url": "https://private.invalid/LEAK_FLEET_PROOF",
                                                                  "text": "LEAK_FLEET_PROOF_TEXT"}}]},
            "asks": {"updated": now, "sources": "LEAK_ASK_SOURCE", "asks": [{"n": 1, "ask": "LEAK_ASK",
                "owner": "LEAK_PERSON", "lane": "LEAK_LANE", "status": "IN PROGRESS", "proof": {"url": "LEAK_ASK_PROOF"},
                "updated": now}], "lanes": [{"lane": "LEAK_ASK_LANE", "owner": "LEAK_ASK_OWNER", "does": "LEAK_DOES",
                "status": "BLOCKED", "report": "LEAK_REPORT"}], "needs_you": [{"what": "LEAK_NEEDS_YOU",
                "where": "LEAK_WHERE", "do": "LEAK_DO", "done_when": "LEAK_DONE_WHEN"}]},
            "coceo": [{"Entry": "LEAK_COCEO_ENTRY", "Strategy note": "LEAK_COCEO_NOTE"}],
            "caio": [{"Division": "LEAK_DIVISION", "Covers": "LEAK_CAIO_COVERS", "Status": "LEAK_CAIO_STATUS"}],
            "crons": [{"Routine": "LEAK_CRON", "State": "LEAK_CRON_STATE", "Cadence": "LEAK_CADENCE",
                       "Runs on": "LEAK_RUNS_ON", "Defined in": "LEAK_DEFINED_IN"}],
            "fat20": [{"Rank": 1, "Item": "LEAK_FAT20_ITEM", "Status": "LEAK_FAT20_STATUS"}],
            "aiceo": [{"Type": "LEAK_AICEO_TYPE", "Status": "LEAK_AICEO_STATUS", "Title": "LEAK_AICEO_TITLE",
                       "Date": now, "Seat": "LEAK_AICEO_SEAT"}],
            "aiceo_coverage": {"state": "available", "exhaustive": True, "public_rows": 1},
            "aiceo_status": "LEAK_PRIVATE_DIAGNOSTIC", "unknown_top_level": "LEAK_TOP_LEVEL",
        }
        html = build.render(raw, now)
        for marker in ("LEAK_AGENT_NAME", "LEAK_DEVICE", "LEAK_PRIVATE_PROJECT_TITLE", "LEAK_CLIENT",
                       "LEAK_PRIVATE_DOING", "LEAK_PRIVATE_BLOCKER", "LEAK_PROOF", "LEAK_PRIVATE_TASK_TITLE",
                       "LEAK_EMAIL", "LEAK_LEAD_CONTACT", "LEAK_PHONE", "LEAK_CLIENT",
                       "LEAK_PRIVATE_FINISH", "LEAK_TRACKED_TITLE", "LEAK_TRACKED_SCOPE", "LEAK_ROUTE",
                       "LEAK_FOCUS", "LEAK_CURRENT", "LEAK_QUEUE", "LEAK_THREAD", "LEAK_FLEET_TITLE",
                       "LEAK_GOAL", "LEAK_DONE_TEST", "LEAK_FLEET_PROOF_TEXT", "LEAK_ASK", "LEAK_PERSON",
                       "LEAK_DOES", "LEAK_NEEDS_YOU", "LEAK_COCEO_NOTE", "LEAK_CAIO_COVERS", "LEAK_CRON",
                       "LEAK_DEFINED_IN", "LEAK_FAT20_ITEM", "LEAK_AICEO_TITLE", "LEAK_PRIVATE_DIAGNOSTIC",
                       "LEAK_UNKNOWN_FIELD", "LEAK_TOP_LEVEL", aid, pid, did, rid, "LEAK_PRIVATE_SOURCE_ID",
                       build.OWNED_WORK_AGENT, build.OWNED_WORK_PROJECT, build.OWNED_WORK_CHECKIN):
            self.assertNotIn(marker, html, marker)
        self.assertIn('"progress": 40', html)
        self.assertIn('"freshness": "FRESH"', html)
        self.assertIn("Seat 1", html)
        self.assertIn("project-001", html)
        self.assertIsNone(re.search(r"[0-9a-f]{32}", html, re.I))

    def test_missing_or_invalid_owned_progress_is_unknown_not_inferred(self):
        safe = build.public_projection({"tracked_work": {"progress": 150, "progress_state": "SOURCED",
                                                        "status": "LEAK", "status_state": "SOURCED"}})
        self.assertIsNone(safe["tracked_work"]["progress"])
        self.assertEqual(safe["tracked_work"]["progress_state"], "UNKNOWN")
        self.assertEqual(safe["tracked_work"]["status"], "UNKNOWN")

    def test_exact_relation_keeps_stale_owned_progress_but_labels_it_stale(self):
        at = datetime(2026, 10, 7, 23, 0, tzinfo=timezone.utc)
        edited = (at - timedelta(hours=30)).isoformat().replace("+00:00", "Z")
        sourced = build.owned_work_projection(
            [{"url": build.OWNED_WORK_PROJECT, "Progress %": 25, "Status": "IN PROGRESS", "_edited": edited}],
            [{"url": build.OWNED_WORK_CHECKIN, "Agent": [build.OWNED_WORK_AGENT],
              "Project": [build.OWNED_WORK_PROJECT], "Logged": edited, "Status": "PICKED UP"}],
            now=at)
        safe = build.public_projection({"tracked_work": sourced})["tracked_work"]
        self.assertEqual(safe["progress"], 25)
        self.assertEqual(safe["progress_state"], "SOURCED")
        self.assertEqual(safe["freshness"], "STALE")


if __name__ == "__main__":
    unittest.main()
