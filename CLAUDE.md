# CLAUDE.md — Caspar Wealth market-intelligence & lead system

Standing instructions for any Claude session in this repo. Read the linked docs before non-trivial work.

## What this is
Market-intel + lead pipeline for developer ↔ hotel-brand tie-ups in tier-2 North India, built by Deepak for
Caspar Wealth / Novavia (Varun Khanna, Taran Chhabra — she/her). Strategy: [PLAN.md](PLAN.md). Data design:
[ARCHITECTURE.md](ARCHITECTURE.md). Weekly ops: [WEEKLY_REFRESH.md](WEEKLY_REFRESH.md). Layout + app CLI: [README.md](README.md).
Target feature set requested by Taran (§7–§22): [docs/taran_architecture_note.md](docs/taran_architecture_note.md).
Reference feasibility study (Autograph, Greater Noida West): [docs/autograph_gnw_feasibility_text.txt](docs/autograph_gnw_feasibility_text.txt).

## Hard rules
1. **Staged city rollout is confidential.** `caspar.db` holds all 7 Haryana cities; only Karnal is released to the
   team. Never release a city from code/automation (`python app/manage.py release <city>` is admin-only, run by
   Deepak). Nothing team-facing (app UI, exports, seed DB, Railway demo, messages drafted for Varun/Taran) may
   reveal that other cities' data already exists.
2. **`db/leads.db` is team state and gitignored.** Pipeline rebuilds must never touch it; `app/sync_leads.py`
   only appends. Don't copy it into `deploy/` — the cloud seed is `deploy/leads_seed.db`, regenerated deliberately.
3. **After any licence↔RERA mapping, run `python scrapers/apply_licence_citations.py`.** A fuzzy-only rebuild
   resurrects already-launched parcels into the ripe list. `db/build_city.py` preserves RERA enrichment — use it,
   don't hand-roll rebuilds.
4. **Build work is paused until payment is confirmed** (as of Aug 2026). Keep the weekly refresh running and fix
   correctness bugs, but don't start new features from the Taran note unless Deepak says the money/mandate is
   through. When in doubt, ask.
5. Credentials (`caspar-admin-2026`, `team-karnal-2026`) appear in docs/seed — treat as known-weak, don't spread
   them further, and don't paste them into anything shared externally.

## Key commands
```
python app/server.py                       # lead app, port 8765 (LAN); app/start_local.bat on Windows
python app/manage.py status                # users, released cities
python db/build_city.py <city>             # rebuild caspar.db for a city
python scrapers/map_licences_to_rera.py && python scrapers/apply_licence_citations.py
python db/export_outputs.py <city>         # outputs/<city>/ (ripe parcels, hospitality, call list…)
python app/sync_leads.py                   # append new leads for RELEASED cities only
```
Full sequence and ordering: WEEKLY_REFRESH.md. Scheduled task `caspar-weekly-refresh` (Mon 8 AM) follows it;
it must never release cities or regenerate `deploy/leads_seed.db`.

## Environments
- Local: `http://192.168.1.9:8765` (team). Real data in `db/leads.db`.
- Railway demo (Varun/Taran): `https://web-production-350d.up.railway.app` — no volume, reseeds from
  `deploy/leads_seed.db` on each deploy; it drifts from local and is NOT a source of truth.
- Git: private `mailjaindeepak/caspar`; `gh` at `C:\Program Files\GitHub CLI\gh.exe`. Commit only when asked.

## Conventions
- Per-city artefacts live in `data/<city>/` and `outputs/<city>/`; city slugs are lowercase (karnal, panipat,
  sonipat, rohtak, hisar, ambala, kurukshetra).
- Every curated fact (contact, launch status, dropped-parcel reason) carries a source — keep that when editing.
- Target ranking = `need_score` (non-native / first-time developers rank higher); luxury capability is the
  second lens. See PLAN.md §4 and the `v_target_parcels` view.
