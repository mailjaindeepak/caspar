# Weekly refresh runbook

Goal: pick up new DTCP licences / CLU permissions / RERA registrations, refresh
the intel DB, and drop any new leads into the team's lead app — **for released
cities only** (check `python app/manage.py status`).

Run from repo root. Steps in order; each is safe to re-run.

## 1. Scrape fresh source data

```
python scrapers/dtcp_licences.py        # licence register (the highest-value diff)
python scrapers/dtcp_pending.py --fetch # PENDING applications (earliest signal)
python scrapers/dtcp_rejected.py --fetch # REJECTED/returned/withdrawn/lapsed cases —
                                        # data/licence_rejected.html, parsed by build_city.py
python scrapers/dtcp_clu.py             # CLU permissions (hospitality channel) — ALL 7 districts,
                                        # last year + this year, merged into data/clu_all.csv and
                                        # each data/<city>/clu_permissions.csv (full history kept)
python scrapers/harera_projects.py      # RERA registrations, all 7 cities by default
python scrapers/harera_agents.py        # agent registry (monthly is fine)
```

Pending-register notes: the endpoint (WebAdmin/License/LicensePending) is
deliberately unlinked from DTCP's public menus — if the fetch fails or the row
count collapses, it may have been taken down; flag it in the report. GET only
(HEAD redirects to login). A file_no that LEAVES pending and APPEARS in the
granted register that week = licence granted = the hottest possible signal;
call it out in the report.

Rejected-register notes: `build_city.py` reloads `licence_application_raw` from
`data/licence_rejected.html`. If that file is missing the rebuild now keeps the
existing rows and warns, rather than emptying the lane — but re-fetch it, or the
lane silently ages. (Until 7 Sep 2026 the path pointed at a Claude session
scratchpad; when that temp dir was cleaned, every city rebuild crashed.)

CLU notes: the register goes back to the 1990s and `caspar.db` holds the full
history (backfilled 23 Aug 2026). The weekly run re-fetches only the last two
years; a failed year keeps its existing rows. The scraper prints "+N new file
nos" per district — those are the week's genuinely new CLUs.

Notes from past runs:
- jamabandi/HARIS endpoints are flaky (503s); district-portal PDFs are primary.
  Prefer early-morning IST for govt portals.
- If a scraper breaks, the portal markup likely changed — fix the parser, don't
  skip the source silently.

## 2. Rebuild DB + derived views

```
python db/build_city.py <city>          # for each city with new raw data
python scrapers/map_licences_to_rera.py
python scrapers/apply_licence_citations.py   # MUST run after map — deterministic
                                             # citation links kill false "ripe" parcels
python scrapers/licence_rera_delta.py
```

`build_city.py` deletes and reloads each city's parcels, so anything that does
NOT come from a CSV has to be preserved explicitly. It now carries three things
across a rebuild — REP-I enrichment, DTCP GIS polygons/centroids, and
hand-confirmed `parcel_link` rows (`method='manual'`). If you add another
curated-in-DB field, teach `build_city.py` to preserve it too, or the next
refresh silently drops it.

Sanity check before exporting: if the ripe-parcel count JUMPED versus last week,
suspect missing citation links or lost manual links (either resurrects an
already-launched parcel) — do not push leads to the team until the count is
explained. Quick check:
`select count(*) from parcel_link where method='manual'` and
`select count(*) from parcel where centroid_lat is not null` should not fall.

## 3. Re-export outputs

```
python db/export_outputs.py <city>      # for each of the 7 cities
python db/export_contacts.py
```

## 4. Sync new leads to the team app

```
python app/sync_leads.py
python app/enrich_map_links.py
python app/enrich_developer_stats.py
```

The second command fills in Google-Maps links for new leads (parcel centroids
from caspar.db; hospitality CLU polygons live from the DTCP GIS API).

This appends only leads not seen before (keyed by licence/CLU no.), tagged with
today's date, for **released cities only**. Team statuses/notes are never
touched. Unreleased cities' data refreshes in `outputs/` but stays invisible.

Hospitality leads are limited to CLUs from `HOSPITALITY_MIN_YEAR` (2017, set in
`app/sync_leads.py`, env `CASPAR_HOSPITALITY_MIN_YEAR`) onward — the intel DB
holds CLUs back to the 1990s but old hotel/banquet permissions are built or
lapsed and would flood the team lane. Change it deliberately, not by accident.

## 5. Review + commit

- `python app/manage.py status` — sanity-check new-lead counts.
- Eyeball anything surprising (a 0-new week is normal; a 50-new week means a
  register dump or a parser bug).
- `git add -A && git commit -m "weekly refresh YYYY-MM-DD" && git push`

## 6. Report

Summarize for Deepak: new licences/CLUs per city, new leads added per released
city, anything broken or worth releasing next.
