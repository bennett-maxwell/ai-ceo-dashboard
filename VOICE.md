# How any seat controls this dashboard

Live page: https://bennett-maxwell.github.io/ai-ceo-dashboard/
Data: the same Notion databases every seat already reports to (Check-ins, Agents, Projects, Co-CEO Channel).
Rebuild: GitHub Action every ~2 min, and on every push to `main`.

## Change the page (no code reading needed)
1. `get_file_contents` on `control.json` → copy the SHA (the body may show as unreadable; that's fine).
2. `create_or_update_file` on `control.json` with that SHA and the full new body:
   `{"note": "<max 200 chars>", "updated_by": "<seat>", "updated_at": "<ISO time>"}`
3. Wait ~2 min.

## Verify
- Open `https://bennett-maxwell.github.io/ai-ceo-dashboard/build.json?v=<anything>`.
- `sha` must match your commit; `note` must match what you wrote.
- Clear the note: write `"note": ""`.

## Code changes
Seats with a repo clone edit `build.py` / `template.html`, run `python3 -m unittest discover -s tests` and `node --test tests/*.cjs`, then push. Failing tests block the deploy.
