# Caspar Data Architecture — v1 (pre-scale design)

Design principle: **three orthogonal source tables** (each stores only what its
source publishes, verbatim, with provenance) + **one resolution layer** (entities
and parcels, where all cross-source claims live as explicit links with confidence)
+ **derived views** (scores, gaps, ripe-parcel list — always computed, never
hand-edited). Storage: SQLite (`caspar.db`), one file, versioned backups.

```
SOURCE LAYER (immutable, per-scrape snapshots)
  clu_raw          licence_raw          rera_raw          agent_raw
      \                 |                  /
       \                |                 /
RESOLUTION LAYER (the joins live here, never in source tables)
  entity  ← entity_alias (name variants, DINs, CINs)
  parcel  ← parcel_link (parcel ↔ clu/licence/rera, method + confidence)
      |
DERIVED LAYER (SQL views / scoring jobs)
  locality_benchmark → developer_score → v_ripe_parcels, v_hospitality_leads
```

---

## 1. Source tables — what each source gives us

### 1.1 `clu_raw` — one row per CLU permission

| Column | From source? | Notes |
|---|---|---|
| clu_file_no | ✅ "File No" (e.g. `CLU/KL-1226A`) | **Natural key** (unique per permission) |
| applicant | ✅ Applicant Name | Individual or company, as printed |
| village | ✅ Location/Controlled Area | Village/controlled-area name, NOT sector |
| purpose | ✅ (Industrial/Commercial/Warehouse/Institutional/Recreational/Residential) | |
| activity | ✅ (Hotel With Banquet, Rice Mill, Banquet Hall, Farm house…) | The real signal field |
| granted_area_sqm | ✅ Granted Area | Normalize "16838.9 sqm" → float; derive `area_acre = sqm/4046.86` |
| district | ✅ | |
| sanction_date | ✅ "CLU Permission on" | |
| corrigendum_date | ✅ | Usually `--` |
| map_url | ✅ "Location on Map" link | **Capture in Phase 1** — may carry lat/long for geo-tagging |
| clu_year | ✅ (page year) | |
| scraped_at | meta | |
| ~~valid_till~~ | ❌ NOT published | CLU conditions (typically 2 yrs to commence) are in the permission letter, not the register. Accept the gap; construction-commencement status comes from gatekeepers. |

### 1.2 `licence_raw` — one row per DTCP colony licence

| Column | From source? | Notes |
|---|---|---|
| licence_no | ✅ (e.g. `264 OF 2007`) | **Natural key** together with issue year |
| lc_case_no / file_id | ✅ CaseNo + FileID (LC-632A…) | LC number groups related licences of one colony |
| colony_name | ✅ | e.g. "ALPHA KAR-28-29 RPL" |
| issue_date | ✅ | |
| purpose | ✅ RPL / RGH / DDJAY-APHP / AHP / CPL / CIR-CIC / IPA / NILP | Type filter for the funnel |
| area_acre | ✅ | |
| dev_plan | ✅ | Town: Karnal / Nilokheri-Taraori / Gharaunda / Assandh / Indri — a city = a SET of dev plans |
| sector | ✅ | Sparse for peripheral towns |
| valid_upto_raw | ✅ | **Free text** — parse date AND screen for "Cancel"/"Migrated" strings (cancellations hide here) |
| developer_raw | ✅ | As printed; 5+ spelling variants per group are normal |
| land_schedule_url | ✅ link | **Capture in Phase 1** — per-licence PDF with village/khasra numbers = the true parcel definition |
| br3_date / br7_date / lc9_date | ✅ in source | Bank-guarantee/completion-certificate milestones — later lifecycle signal |
| scraped_at | meta | |

Also from the same source family: `licence_rejected_raw` (rejected/returned/withdrawn/lapsed register — negative screening) — same shape + status column.

### 1.3 `rera_raw` — one row per RERA registration

| Column | From source? | Notes |
|---|---|---|
| rera_reg_no | ✅ (e.g. `RERA-PKL-726-2019`) | **Natural key** |
| temp_id | ✅ Project Temp-ID | |
| project_name | ✅ | Often embeds acreage ("AREA 71.01 ACRES") — parse to `area_acre_derived` |
| promoter_raw | ✅ | The SPV name — rarely the group name |
| address | ✅ Project Address | Parse sector → `sector_derived` |
| district, registered_with, bench_path | ✅ | |
| certificate_url, ah_url | ✅ links | **Phase 1: download + parse.** Certificates carry promoter contact details; **A-H disclosures cite the DTCP licence number** — the deterministic join we currently approximate with fuzzy matching |
| licence_no_cited | from A-H PDF | Phase 1 field — turns licence↔RERA into an exact join |
| promoter_email / promoter_phone | from certificate PDF | Phase 1 fields |
| scraped_at | meta | |

### 1.4 `agent_raw` — RERA-registered agents (gatekeeper seed), as scraped: cert no, name, district, category, issue/expiry, cert link.

**Orthogonality rule:** no source table ever stores a foreign key into another
source table, an entity id, or any inferred field beyond mechanical parsing of
its own text (area float, sector regex). Every scrape is append-with-snapshot
(`scraped_at`), so week-over-week diffs (new licence! new CLU!) fall out of the
raw layer for free.

---

## 2. Resolution layer — how the three tie together

Two real-world objects connect everything; both live OUTSIDE the source tables:

### 2.1 `entity` + `entity_alias` — WHO

```sql
entity(entity_id PK, canonical_name, kind,          -- developer|individual|hotel_group|investor
       cin, group_parent_id, tier, notes)
entity_alias(alias_id PK, entity_id FK, alias_name, alias_norm,
             source,                                -- clu|licence|rera|mca|manual
             source_row_key,                        -- clu_file_no / licence_no / rera_reg_no
             method,                                -- exact|brand_fuzzy|area_rescue|din_overlap|manual
             confidence, reviewed_by, reviewed_at)
```

Every applicant/developer/promoter string in the raw tables maps to an
`entity_alias` row. The alias table IS the audit trail of entity resolution:
"MAA VAISHNO NET-TECH PVT LTD → Signature Global (method=manual, confidence=1.0)".
MCA director-DIN overlap and CIN links hang off `entity`.

### 2.2 `parcel` + `parcel_link` — WHERE

```sql
parcel(parcel_id PK, city, dev_plan, sector, village,
       area_acre, geom_lat, geom_lng,               -- from map_url / land schedule when available
       current_stage,                               -- clu|licensed|rera_registered|launched|delivered
       controlling_entity_id FK)
parcel_link(link_id PK, parcel_id FK,
            source,                                 -- clu|licence|rera
            source_row_key,
            method,                                 -- ah_citation|licence_no_exact|name+area|name+sector|manual
            confidence,                             -- 0..1
            status,                                 -- PARCEL-MATCH|SPV-MATCH?|DEV-MATCH|manual-confirmed|rejected
            reviewed_by, reviewed_at)
```

A parcel is created from a licence row (licences define parcels best: area +
sector + land schedule); CLU rows and RERA rows attach to parcels via
`parcel_link`. The current `licence_rera_map.csv` logic becomes the job that
writes these links. Match waterfall, strongest first:

1. **A-H licence citation** (RERA PDF cites licence no.) — deterministic, conf 1.0
2. **Brand-token fuzzy name ≥ 70 + area (±2%) or sector** — conf 0.85 (today's PARCEL-MATCH)
3. **Area exact + partial name 35–70** — conf 0.5, status SPV-MATCH?, **human review queue**
4. **Name ≥ 85 alone** — links the ENTITY, not the parcel (DEV-MATCH)
5. Below that — unlinked; appears in gap views.

Nothing below conf 0.85 is auto-accepted; review decisions are recorded on the
link row, so the machine never silently overwrites a human call.

---

## 3. Derived layer

### 3.1 `locality_benchmark` — premium vs non-premium

```sql
locality_benchmark(locality_id PK, city, name,       -- "Sector 29", "Nilokheri", "GT Road frontage"
       tier,                                         -- prime|secondary|value
       rate_low, rate_high, rate_unit,               -- ₹/sqft or ₹/sqyd
       evidence_json, as_of, confirmed_by)
```

Tier is assigned from **four independent evidence streams**, each recorded in
`evidence_json` so the call is auditable:

1. **Collector rates** (official district circle rates, revised yearly — Karnal's rose 10–20% FY25-26). The government's own price map; scrape/collect per city.
2. **Portal listing rates** per sector/locality (99acres price-trends pages, even at snippet granularity).
3. **Anchor evidence** — which projects/prices already exist there (Alpha Sec 28-29 ₹9–12.2k/sqft ⇒ prime; DDJAY clusters in Nilokheri ⇒ value).
4. **Gatekeeper confirmation** — a 30-min broker/Varun session per city to confirm/override; `confirmed_by` records it.

Rule of thumb encoded in the job: prime = top price band + premium anchors +
infra nodes (NH-44/GT Road, RRTS station zones); value = DDJAY belts. Human
confirmation is mandatory before a locality's tier feeds outreach ranking.

### 3.2 `developer_score` — the Luxury Potential Score per entity (rubric from PLAN.md §4), recomputed on refresh; inputs read from resolution + benchmark layers.

### 3.3 The output views

```sql
-- Land parcels ripe for discussion
v_ripe_parcels =
  parcels whose best licence is VALID (parsed date ≥ today, no cancel string)
  AND purpose ∈ (RPL, RGH, AHP→premium-check, NILP, CPL if mixed-use play)
  AND area_acre ≥ 4                                  -- min viable branded play; tune per brand reqs
  AND no PARCEL-MATCH link to any rera_raw row       -- entitled but unlaunched
  AND issue_date ≥ 2017                              -- pre-RERA legacy = sold out, exclude
  ORDER BY: controlling entity tier (A > B > unknown),
            locality tier (prime first),
            area desc, issue_date desc
  + reason_codes column (why it surfaced) for the outreach sheet.

-- Second lane, from CLU:
v_hospitality_leads = clu_raw where activity ~ hotel|motel|resort|banquet|farm
  joined to entity + locality; ranked by area, recency, operator-vs-individual.

-- Weekly diff alerts:
v_new_this_week = new rows in any raw table since last snapshot,
  auto-joined to entity/parcel → "New licence: 24.9 ac RPL Sec 29, Haryana Promoters (Tier B) — no RERA yet."
```

Karnal validation of the funnel: 133 licences → 28 unmatched + 13 DEV-MATCH →
after v_ripe_parcels filters ≈ **6–8 genuinely ripe residential parcels + 19
hospitality leads** — a callable list, which is the point.

---

## 4. Known gaps this design accepts (and how they're covered)

- CLU register has no validity/commencement data → gatekeeper layer.
- Residential CLUs ≈ absent in these districts (colony-licence route instead) → CLU is the hospitality/heat channel, not the residential one.
- Licence register's cancellations are free text → `valid_upto_raw` screened by string rules + rejected-register cross-check.
- Fuzzy entity matches below threshold → human review queue in `parcel_link` / `entity_alias`, never auto-merged.
- Pre-licence land assembly invisible to all three sources → gatekeeper intake (`gatekeeper`, `signal` tables — same DB, attribution for commissions).

## 4b. Geo + circle-rate sources (validated Aug 2026)

**Parcel geometry — both registers expose a JSON GIS API (no auth):**
- CLU: `tcpharyana.gov.in/CS_marking/LicenceGIS/getCLUResults?CluNo=CLU/KL-1226A` → owner, village, purpose, activity, area, permission date + **WKT polygon** of the parcel.
- Licence: `tcpharyana.gov.in/CS_marking/LicenceGIS/getLCResults?LCNo=LC-632` → colony name, all licence nos of the LC case, sector, town + **WKT polygon**; also exposes extra developer aliases (LC-632 lists "Grandeur Real Estate" alongside Alpha Corp → feed `entity_alias`).
- Coordinates are UTM zone 43N (EPSG:32643); convert with pyproj → `parcel.geom_lat/lng` + full polygon. Verified: CLU/KL-1226A lands at 29.596N 76.978E (Kurtail, Karnal). ✔ populates `parcel` geometry directly.
- Licence register rows also link BR-III certificates and **layout-plan PDFs** (`/Licences/PLANS-LOP-SP/…`) — capture hrefs in Phase 1.

**Circle (collector) rates — official locality price map:**
- District portal publishes tehsil-wise PDFs yearly: karnal.gov.in/collectorrate/ (2025-26: Karnal, Gharaunda, Nilokheri, Indri, Assandh + sub-tehsils Ballah, Nigdhu, Nissing); prior years on sibling pages. Same *.gov.in pattern per district for other cities.
- Statewide queryable interface: jamabandi.nic.in/HARIS/Collector1 (WebHARIS) and revenueharyana.gov.in (draft rates). **Reliability note (checked 13-Aug-2026): jamabandi returned timeouts then HTTP 503 from all vantage points — NIC server overload, a known pattern. Treat district-portal PDFs (s3waas CDN, fast and reliable) as the PRIMARY rate source; HARIS as opportunistic with retries/backoff, off-peak (early morning IST) scheduling.**
- PDFs are village/sector/locality-wise → parse into `locality_benchmark` (evidence stream #1). FY25-26 Karnal hikes: 10–50%, up to ~70% around Sector 32/NH-44 — itself a heat signal.

## 5. Build order when we scale

1. `caspar.db` DDL + loader that ingests the existing five CSVs per city (raw layer).
2. A-H / certificate PDF downloader + parser → exact licence citations, promoter emails/phones (upgrades join #1 and enrichment).
3. Entity-resolution job (brand-fuzzy + DIN) writing `entity_alias`; review queue as a simple CSV/sheet export-import.
4. Locality benchmarks per city (collector rates + portal + anchors), Varun confirmation pass.
5. Views + weekly-diff alert job; outreach sheet export.
