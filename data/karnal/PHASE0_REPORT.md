# Phase 0 Report — Karnal Pilot (Aug 2026)

Goal: prove the funnel end-to-end on one city and document what each source actually yields before building Phase-1 production scrapers.

## Verdict

**The funnel works.** Karnal's full developer universe was enumerated from two public government sources with no captchas, no logins, and no paid data. The city has 93 RERA-registered projects (67 developer groups after clustering) and 133 DTCP licences (~2,009 acres) since 2005. Cross-referencing the two produced the core sales signal: 20 recent licences with no RERA registration yet — developers holding entitled land, pre-launch, pre-positioning.

## What each source yielded

### 1. HARERA project registry — WORKS, scriptable
- URL: `haryanarera.gov.in/assistancecontrol/project_search_public/{1,2}` — plain POST with `district` code; both URL variants must be queried (Karnal data sits under `/1` despite Panchkula-bench jurisdiction).
- District codes captured for all Phase-1 cities: KARNAL=67, PANIPAT=71, SONIPAT=75, ROHTAK=73, HISAR=63, AMBALA=58, KURUKSHETRA=68.
- Yield per project: name, promoter (SPV) name, registration number, address, district, bench, certificate PDF link, A-H disclosure link.
- Quirk: data cells are `<th>` not `<td>` (parser must handle both).
- **93 Karnal projects** → `harera_projects.csv`. Certificate/A-H PDFs (promoter contact details, often email/phone) not yet bulk-downloaded — Phase 1 item.

### 2. HARERA agent registry — WORKS, bonus find
- `haryanarera.gov.in/admincontrol/registered_agents/{1,2}` — the full statewide broker list in one GET: **8,759 agents, 77 in Karnal**, with certificate links and expiry dates → instant gatekeeper seed list (`harera_agents.csv`).

### 3. DTCP Haryana licence register — WORKS, the crown jewel
- Master register: `tcpharyana.gov.in/webadmin/license/licensedetails` — the ENTIRE state's licences since 2005 in one 7 MB server-rendered GET (3,125 rows). No captcha, no JS.
- Karnal district = 133 licences. Must filter Dev Plan on all five town names: Karnal, Nilokheri and Taraori, Gharaunda, Assandh, Indri.
- Also working: rejected/withdrawn register (1,184 rows statewide), CLU year-wise pages (`/WebAdmin/clu/index?id=YYYY`).
- Yield: licence no., issue date, purpose (RPL/RGH/DDJAY/CPL/IPA/AHP), acreage, sector, validity, developer, land-schedule PDF link.
- Negative screening works: CHD's Sec-45 licence cancellation (2018, later restored), Ansal 2017 rejection, Parsvnath validity expired 2019 — all visible in the registers.
- Caveat: cancellations appear as free text in the validity column; no consolidated blacklist page exists (blacklists surface via HARERA/press).

### 3b. DTCP CLU year pages — WORKS, with a corrected role
- `tcpharyana.gov.in/WebAdmin/clu/index?id=YYYY` — one server-rendered table per year, statewide, no captcha. Scraped 2017–2026: 4,918 permissions statewide, 278 Karnal (`clu_permissions.csv`; statewide in `data/clu_all_2017_2026.csv`).
- **Corrected assumption:** Karnal CLUs are almost never residential (1 of 278 — a farmhouse). Plotted/group-housing land goes straight to the colony-licence route in Haryana, so CLU is NOT a pre-licence residential indicator here.
- **Its real value:** (a) a hospitality lead channel — 19 hotel/motel/banquet/resort CLUs (`clu_hospitality_watchlist.csv`), incl. Deventure Hotels' ~5 ac hotel CLU (2024) and three new hotel CLUs in 2026 alone; these are landowners entering hospitality = direct brand-tie-up prospects. (b) a corridor-activity heat signal — Karnal CLU volume rose 11/yr (2017) → 60/yr (2025), confirming the GT Road re-rating.

### 4. Portals/news (market layer) — PARTIAL, adequate
- 99acres/MagicBricks/SquareYards block direct fetches (403) — data came via search snippets. Good enough for ticket-size banding; not for systematic price feeds. Phase-1 options: portal APIs via their sitemap/JSON endpoints, or accept snippet-level granularity.
- Full market snapshot in `market_report.md`.

### 5. Entity resolution — WORKS at 80%, needs one upgrade
- Simple normalization collapsed 93 promoters → 67 groups (caught Alpha Corp ×2 spellings, RAS ×2, Ansal ×3).
- Missed: Coloniser/Colonizer drift (K.N. Colonizers false-positived in the delta), RCNP variants. Phase 1: token-set fuzzy matching (rapidfuzz) + MCA director (DIN) overlap for SPV→group mapping. SPV opacity is real: Signature Global's Karnal projects sit under "MAA VAISHNO NET-TECH PVT LTD".

## The funnel output (Karnal)

- **Universe:** 67 developer groups (`developers.csv`), 133 licences (`dtcp_licences.csv`).
- **Scored shortlist:** `scored_developers.csv` — Tier A: Alpha Corp (87). Strategic A*: Jewel Classic Hotels (Noormahal → India's first Marriott Autograph Collection, Apr 2026 — existing Marriott relationship). A-: Eterna Living, the ex-Ansal Karnal SPV now Dalmia-controlled and outside Ansal's insolvency. Tier B: Signature Global, Rajdarbar, Golf Links. Parked: CHD (under CIRP since 2022 — counterparty is the resolution professional).
- **Stakeholders:** `stakeholders.md` — verified people/emails/phones/LinkedIn for all 6 targets, with confidence tags and honest gaps. Two stale-data traps caught: S.K. Sayal no longer leads Alpha Corp (left 2014); "Rajdarbar Builders/Green Valley" names don't match registry reality (actual entities: Rajdarbar Realty Ltd + Realty Creations).
- **Dossier:** `dossiers/alpha_corp.md` — the handoff-pack template, ready for a Varun/Taran meeting.
- **Pre-launch land signal:** two levels.
  - `licensed_not_registered.csv` — first pass, developer-level, 2020+ only: 20 licences.
  - `licence_rera_map.csv` — full parcel-level map of all 133 licences (brand-token fuzzy name + acreage + sector join): **87 parcel-matched, 14 developer-matched (parcel unconfirmed), 4 possible SPV matches (review), 28 unmatched**. Gap A (developer absent from RERA, licence valid) = 15 parcels; Gap B (developer active but this parcel unlaunched) = 13 parcels — incl. Haryana Promoters 24.9 ac RPL Sec 29 (2024) and Alpha's own unlaunched 2022 DDJAY parcels. Caveat: pre-2017 rows in Gap A (True Zone Sec 32/33) are sold-out pre-RERA colonies, not opportunities — filter by issue year for outreach.
- **Gatekeepers:** 77 RERA-registered Karnal agents (`harera_agents.csv`).

## Key market conclusions for the pitch

1. Karnal premium absorption is proven (Alpha City +178%/5yr, ₹12.5 Cr top listing, ₹2.5 Cr Ansal villas) but **zero branded/luxury group-housing supply exists** — white space.
2. Marriott itself validated Karnal by opening India's first Autograph Collection hotel there (Noormahal, Apr 2026).
3. Infra tailwinds: Delhi–Amritsar–Katra expressway, proposed RRTS extension to Karnal, collector rates +10–20%.

## Phase-1 build list (from lessons learned)

1. Generalize `harera_projects.py` to all 7 cities (district codes already mapped) + bulk-download certificate & A-H PDFs (promoter emails/phones live there).
2. DTCP scraper module: full-register GET + town-name filter per city + rejected-register + CLU year pages; weekly diff → "new licence" alerts.
3. rapidfuzz entity resolution + MCA/Zauba DIN lookup for top-50 groups.
4. SQLite schema per PLAN.md §2; CSVs are the interim format.
5. Outreach assets per PLAN.md §5.

Scripts: `scrapers/harera_projects.py`, `scrapers/harera_agents.py`, `scrapers/cluster_developers.py`, `scrapers/licence_rera_delta.py`.
