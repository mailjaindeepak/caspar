# Weekly refresh runbook

Goal: pick up new DTCP licences / CLU permissions / RERA registrations, refresh
the intel DB, and drop any new leads into the team's lead app — **for released
cities only** (check `python app/manage.py status`).

Run from repo root. Steps in order; each is safe to re-run.

## 1. Scrape fresh source data

```
python scrapers/dtcp_licences.py        # licence register (the highest-value diff)
python scrapers/dtcp_clu.py             # CLU permissions (hospitality channel)
python scrapers/harera_projects.py      # RERA registrations
python scrapers/harera_agents.py        # agent registry (monthly is fine)
```

Notes from past runs:
- jamabandi/HARIS endpoints are flaky (503s); district-portal PDFs are primary.
  Prefer early-morning IST for govt portals.
- If a scraper breaks, the portal markup likely changed — fix the parser, don't
  skip the source silently.

## 2. Rebuild DB + derived views

```
python db/build_city.py <city>          # for each city with new raw data
python scrapers/map_licences_to_rera.py
python scrapers/licence_rera_delta.py
```

## 3. Re-export outputs

```
python db/export_outputs.py <city>      # for each of the 7 cities
python db/export_contacts.py
```

## 4. Sync new leads to the team app

```
python app/sync_leads.py
```

This appends only leads not seen before (keyed by licence/CLU no.), tagged with
today's date, for **released cities only**. Team statuses/notes are never
touched. Unreleased cities' data refreshes in `outputs/` but stays invisible.

## 5. Review + commit

- `python app/manage.py status` — sanity-check new-lead counts.
- Eyeball anything surprising (a 0-new week is normal; a 50-new week means a
  register dump or a parser bug).
- `git add -A && git commit -m "weekly refresh YYYY-MM-DD" && git push`

## 6. Report

Summarize for Deepak: new licences/CLUs per city, new leads added per released
city, anything broken or worth releasing next.
