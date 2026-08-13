# Caspar — Branded Residences Market Intelligence System

**Venture:** Novavia / Caspar Wealth (Varun Khanna — real estate, ex-Ireo; Taran Chhabra — hospitality brand tie-ups & contracts)
**Thesis:** Branded residences are concentrated in tier-1 metros (NCR alone = ~54% of India's ₹1 lakh crore pipeline). Tier-2 cities in Haryana / Punjab / UP are underserved. Caspar brokers developer ↔ brand tie-ups (Marriott, Taj, Leela, Clarks…), helps negotiate terms, and trains the developer's team for brand compliance.
**Problem:** Deads today come only from Varun's and Taran's personal networks — not scalable.
**Goal:** A repeatable pipeline: map every active developer in target cities → filter to luxury-capable ones → find their land parcels → find their decision-makers → reach out → hand qualified meetings to Varun & Taran.

**Phase-1 geography (Haryana, 7 cities):** Karnal, Panipat, Sonipat, Rohtak, Hisar, Ambala, Kurukshetra. All fall under the **HARERA Panchkula bench**. Later: rest of the 20 identified cities across Haryana, Punjab, UP.

---

## 1. The ecosystem — what stage tells us what

A developer's project lifecycle, and the data signal each stage emits:

| Stage | What happens | Public data trail | Value to us |
|---|---|---|---|
| 1. Land acquisition | Developer/SPV buys or JVs land | Jamabandi / registry records (hard to access at scale) | Earliest signal, but mostly reachable only via gatekeepers |
| 2. CLU + DTCP licence | Change of Land Use, colony licence from Town & Country Planning | DTCP Haryana orders, licence lists, e-licensing status | **Best early signal** — a licence means committed capital + a parcel, but design/positioning often not locked. This is the ideal moment to pitch a brand. |
| 3. RERA application & registration | Project registered with HARERA before marketing | HARERA public search: promoter, project, address, certificates, QPRs | The structured backbone — complete, official, scrapable |
| 4. Launch & sales | Marketing begins | 99acres, MagicBricks, Housing.com, SquareYards, project sites | Ticket size, positioning, sales velocity → luxury-capability scoring |
| 5. Development → OC → handover | Construction, occupation certificate | HARERA QPRs, news | Delivery track record → credibility scoring |

**Core insight:** RERA data tells us who is active *now*; DTCP licence data tells us who will launch *next*. The outreach sweet spot is the gap between stage 2 and stage 3 — before positioning is locked. The system should surface exactly those developers.

---

## 2. Data model

Entities and key fields (one SQLite/Postgres DB):

- **City / micro-market** — city, prime vs non-prime localities (from portal price maps + broker input), price benchmarks (₹/sq ft floor and ceiling).
- **Developer (group level)** — group name, aliases/SPVs, HQ, website, years active, cities active, total projects, delivery record, financial capacity (MCA filings), blacklist/cancellation flags (DTCP), *Luxury Potential Score*.
- **Project** — name, developer, city, locality, stage (licensed / RERA-registered / launched / delivered), RERA reg. no., licence no., land area, type (plotted / group housing / commercial), ticket-size band, launch & completion dates.
- **Land parcel** — location, area, licence/CLU status, whether attached to an announced project (an unattached licensed parcel = prime prospect).
- **Stakeholder** — name, role (promoter / director / CXO / sales head), company, email, phone, LinkedIn, source, confidence level.
- **Gatekeeper** — brokers (RERA-registered agents!), architects, CAs/consultants; city, firm, contacts, relationship status, commission arrangement.
- **Pipeline record** — developer × outreach status (identified → enriched → contacted → replied → meeting → handoff to Varun/Taran → deal).

Critical engineering problem: **entity resolution.** Developers register each project under a different SPV ("ABC Buildwell Pvt Ltd", "ABC Infra LLP"). MCA director overlap (shared DINs) is the reliable way to cluster SPVs into one developer group.

---

## 3. Data sources — what we can scrape vs. what needs gatekeepers

### A. Scrapable (machine + assistant-driven)

| Source | What we get | Access |
|---|---|---|
| **HARERA Panchkula** (haryanarera.gov.in) — project search | All registered projects per district: promoter name, address, reg no., certificates (PDFs often carry promoter contact details), QPRs | Server-rendered search, district dropdown includes all 7 cities. ~336 projects on the whole bench → small, fully enumerable. **Start here.** |
| **HARERA agent registry** | RERA-registered property agents per district — a ready-made, official **gatekeeper list with names & numbers** | Same portal |
| **DTCP Haryana** (tcpharyana.gov.in) | Licences granted, CLU orders, NILP-2022 policy, cancellations & blacklists (negative screening) | PDF orders + licence-status lookups; Phase 0 task: locate the district-wise LC registers / e-licensing search |
| **MCA / Zauba Corp / Tofler** | Company directors (DINs), registered email & address, charges (debt), financials | Zauba free tier + targeted paid pulls; used for SPV clustering + financial capacity |
| **Property portals** (99acres, MagicBricks, Housing.com, SquareYards) | Active projects, price/sq ft, ticket sizes, locality price maps | Scrape carefully (anti-bot) or use their published city price indices |
| **Google Maps + local news** (Tribune, HT city editions, Dainik Bhaskar/Jagran) | Developer offices, project sites, launch announcements, land deals | Search + news monitoring |
| **LinkedIn + enrichment tools** (Apollo.io, Lusha, SignalHire, ContactOut) | Stakeholder names, roles, emails, phones | Apollo free/starter tier first; verify emails (NeverBounce/ZeroBounce) before sending |
| **CoA architect registry, Justdial, IndiaMART** | Architects & consultants per city (secondary gatekeepers) | Directory scrape |

### B. Gatekeeper-only data (paid via commission)

- Off-market land parcels & who holds them; deals in negotiation
- Developer intent ("planning something premium on the NH-44 parcel")
- Warm introductions & mobile numbers of promoters
- Local prime/non-prime nuance no portal captures

The system should treat gatekeepers as a **structured input channel**, not ad-hoc gossip: a simple intake form (city, developer, parcel, signal, source) feeding the same DB, with attribution so commissions can be honoured.

---

## 4. The funnel — from master list to call list

**Level 0 — Master list (universe).** Every developer with ≥1 licence or RERA registration in the 7 cities. Expect roughly 150–400 developer groups after SPV clustering.

**Level 1 — Luxury-capable shortlist.** Score each group 0–100:

| Criterion | Weight | Source |
|---|---|---|
| Max ticket size of past/current projects (≥ ~₹1.5–2 Cr in these cities = premium) | 25 | Portals, RERA |
| Scale (total developed area, no. of projects) | 15 | RERA, DTCP |
| Group-housing / high-spec experience (not just plotted colonies) | 15 | RERA project type |
| Financial capacity (paid-up capital, charges, group turnover) | 15 | MCA |
| Land bank: licensed parcels without a launched project | 20 | DTCP − RERA delta |
| Clean record (no DTCP blacklist/cancellation, no major RERA penalties) | 10 | DTCP, HARERA orders |

Tier A (>65): direct outreach targets. Tier B (40–65): nurture. Tier C: excluded but kept in DB (market intelligence has value beyond outreach — this database *is* the moat).

**Level 2 — Parcel-qualified targets.** For each Tier A/B developer: which parcels, prime or upgradable-by-brand? This is where gatekeepers add the most value.

**Level 3 — Reachable targets.** Stakeholders enriched: promoter/MD first, then sales/marketing head. Multiple channels ranked: warm intro (via gatekeeper or Varun's network) > LinkedIn > email > phone.

---

## 5. Outreach engine

1. **Value-prop asset** — a short city-specific one-pager: "Branded residences premium in tier-2: what a Marriott/Taj flag does to your realization per sq ft" (use SKYE/360 Realtors tier-2 study + NOESIS ₹1L Cr pipeline data as third-party proof).
2. **Sequences** — personalized first-touch referencing *their specific parcel/project* (this is why the data work matters); 2 follow-ups; LinkedIn parallel touch.
3. **CRM** — start with Google Sheets/Airtable synced from the DB; graduate later. Every reply logged; meetings booked directly into Varun & Taran's calendar.
4. **Handoff pack** — before each meeting, auto-generate a developer dossier: projects, ticket sizes, parcels, financials, stakeholders, suggested brand-fit.

Compliance notes: India's DPDP Act 2023 — B2B outreach to business contacts is workable but keep provenance of every contact recorded, honour opt-outs immediately; calls to numbers on TRAI DND should be avoided; respect portal ToS / rate limits when scraping (RERA & DTCP are public records — lowest risk; LinkedIn — use enrichment tools rather than scraping directly).

---

## 6. System architecture (lean)

```
Scrapers (Python: requests/Playwright, per-source modules)
   → Raw store (JSON/PDF per source, versioned by date)
   → Parse + normalize (pdfplumber for RERA/DTCP PDFs)
   → Entity resolution (SPV clustering via MCA DINs + fuzzy name match)
   → SQLite (later Postgres)  ← gatekeeper intake form (Google Form → sheet → import)
   → Scoring job (Luxury Potential Score)
   → Outputs: Excel/Sheets master list per city · Tier-A call list · developer dossiers · refresh diffs ("new licence issued in Karnal this week")
```

- **Refresh cadence:** RERA + DTCP weekly (a *new licence* alert is the single highest-value trigger); portals monthly; MCA on-demand.
- Everything runs locally first; no cloud infra needed until Punjab/UP scale-up.

---

## 7. Phased roadmap

**Phase 0 — Validate on one city (Karnal), ~1 week.**
Manually + semi-scripted, end-to-end: enumerate Karnal from HARERA; find DTCP licence lists for Karnal district; cluster SPVs; score; enrich 5 stakeholders; produce one developer dossier. *Deliverable: proof the funnel works + honest notes on what each source actually yields (fields, formats, captchas, gaps).*

**Phase 1 — Master list, 7 Haryana cities, ~2–3 weeks.**
Production scrapers for HARERA + DTCP + portals; DB + entity resolution; master list of all developers & projects per city.

**Phase 2 — Funnel + enrichment, ~2 weeks.**
Scoring live; land-parcel delta analysis (licensed-but-unlaunched); stakeholder enrichment for all Tier A; gatekeeper intake channel live (start with RERA-registered agents in each city).

**Phase 3 — Outreach, ongoing.**
Value-prop assets; sequences; CRM; first meetings handed to Varun & Taran. KPI: qualified meetings/month.

**Phase 4 — Scale.**
Punjab (rera.punjab.gov.in — publishes a downloadable registered-projects PDF) and UP (up-rera.in — one of the better RERA portals) + remaining 13 cities. Weekly-diff alerting becomes the ongoing intelligence product.

---

## 8. Open questions for Varun / Taran

1. **Ticket-size threshold** for "luxury-capable" in these specific cities — is ₹1.5–2 Cr the right bar, or lower for plotted-development branded plays?
2. Do brands under discussion (Marriott/Taj/Leela/Clarks) have **minimum project size / positioning requirements** (keys, sq ft, city criteria)? That should feed the scoring weights.
3. **Prime localities** per city — Varun's network can shortcut the micro-market mapping; a 30-min session per city would beat weeks of scraping.
4. Gatekeeper **commission structure** — needs to be defined before we activate broker intake, since attribution must be built into the DB.
5. Is **plotted + villa branded development** in scope (very common format in these cities), or only group housing/condos?
