# Caspar — Branded Residences Market Intelligence

Market-intel + lead pipeline for developer ↔ hotel-brand tie-ups in tier-2
North India. See [PLAN.md](PLAN.md) for strategy and [ARCHITECTURE.md](ARCHITECTURE.md)
for the data design.

## Layout

| Path | What |
|---|---|
| `scrapers/` | Per-source scrapers (HARERA, DTCP licences/CLU, GIS polygons, agents) |
| `db/` | `caspar.db` (market intel), `schema.sql`, build/export jobs |
| `data/<city>/` | Per-city scraped + curated data (all 7 Haryana cities) |
| `outputs/<city>/` | Outreach-ready exports: target parcels, ripe parcels, hospitality leads, contacts, gatekeepers |
| `app/` | **Lead-management web app** (team-facing) |

## Lead app

```
python -m pip install flask
python app/server.py            # serves on http://<this-machine>:8765 (LAN)
```

- `python app/manage.py create-user <username> "<Full Name>" <password> [admin|member]`
- `python app/manage.py release <city>` — makes a city visible to the team and imports its leads. **Cities are hidden from members until explicitly released** (admin decides when each city goes live).
- `python app/manage.py status`

Team state lives in `db/leads.db` (users, lead statuses, notes). It is
**gitignored on purpose** — it exists only on the machine that hosts the app,
and pipeline re-runs never touch it. Leads are keyed by licence/CLU number, so
re-importing after a data refresh only appends genuinely new leads.

Access model: the team uses only the web app. Repo access = full dataset
access, so keep collaborators on the repo limited to people who should see
everything.

## Weekly refresh

See [WEEKLY_REFRESH.md](WEEKLY_REFRESH.md). Short version: re-scrape sources →
rebuild `caspar.db` → re-export `outputs/` → `python app/sync_leads.py` (appends
new leads for released cities only) → commit.
