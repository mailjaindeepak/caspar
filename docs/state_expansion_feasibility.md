# State expansion feasibility — Punjab & UP (verified Aug 2026)

Goal: replicate the Haryana **"licence granted but not yet RERA-registered"** pipeline
(the pre-launch ripe-parcel signal) for Punjab and Uttar Pradesh. Per-authority
scrapers are acceptable. Findings below were verified by fetching the actual pages
on 2026-08-24, not from memory.

## Why Haryana is easy (the baseline)
One department (DTCP) publishes three **statewide** open HTML registers — CLU by year,
colony licences (granted + pending), and HARERA projects — and RERA's REP-I form
**cites the DTCP licence number**, giving a deterministic licence↔RERA join. Neither
target state has this combination. The "gold" = licensed − registered.

---

## Punjab — VIABLE (fuzzy match, ~6 authority scrapers)

The signal reproduces. Both halves are public; the join is fuzzy, not deterministic.

**Licence side (permission granted): PAPRA colony licences, per authority.**
No central register — each development authority publishes its own list, mostly as
per-district PDFs on a shared template with columns **Name of colony · Promoter ·
Area (acres) · Licence No. & Date · Status of Licence · Khasra/H.B. No. · Layout plan**.
Grant date and status (Valid upto / Completion issued / Renewal under process) are
present — so we can filter to *recent, non-completed* licences = pre-launch, from the
licence list alone.
- Patiala (PDA): https://www.pdapatiala.in/coloniesplots/licensed-colonies — clean HTML + full "Annexure A"
- GMADA (Mohali): https://www.gmada.gov.in/en/issue-of-license-for-setting-up-of-colony-under-papra → PDF (Distt-wise, dated 03-08-2026)
- Amritsar (ADA): http://adaamritsar.gov.in/en/coloniesplotslicensed-colonies/licensed-colonies → per-district PDFs
- PUDA (puda.punjab.gov.in) and Jalandhar (jda.gov.in) — refused the datacenter fetcher (ECONNREFUSED); **verify in a real browser** before scoping.
- Also expected: Bathinda (BDA).

**RERA side (launched): centralized, and richer than Haryana on contacts.**
- Live search (CAPTCHA): https://rera.punjab.gov.in/reraindex/publicview/projectinfo
- **Statewide master PDF** (the easy win, sidesteps CAPTCHA): https://rera.punjab.gov.in/pdf/registered-projects/List_of_Registered_Projects.pdf — 2,025 projects, "as on 17 Jul 2026", 9 columns incl. **promoter mobile + email**.

**The join: FUZZY.** Punjab RERA carries NO licence/LOI/PAPRA reference (confirmed by
scanning all 280 pages of the master PDF — schema is SNo · District · Promoter ·
Project · Reg No · Type · Location · Address · Contact). Match on
**promoter + colony/project name + village H.B. number + area**; block on
district + H.B. number, fuzzy-score name + area, hand-verify collisions. This is the
same secondary path the Haryana pipeline already has.

**Build:** ~6 authority scrapers (mixed HTML + PDF) + 1 RERA-PDF parser + a fuzzy
matcher. No pending-applications feed (granted-only). Bonus: RERA promoter contacts
directly feed the §9 verified-contact gap.

---

## UP — PARTIAL (NCR authorities only; different "permission" semantics)

UP has **no colony-licence regime** and no statewide land-approval register. The
"permission granted" signal must be assembled from individual development authorities,
and it means something different from Haryana: **group-housing / builder-plot
allotment + map sanction**, not a colony licence. Viable for the three NCR
authorities that matter for branded residences; weak elsewhere.

**Per-authority (best pre-launch "has permission, not launched" sources):**
- **NOIDA — best.** Open, no-auth **JSON API**: https://pims.mynoida.org.in/GroupHousing/GetGroupHousingProject?AppType=1 (AppType 1–7). Full group-housing register: ProjectName (developer), Sector, PlotNo, Area, **Sanctioned flats**, OCissued, CCIssued, DefaulterStatus, Status. Scrapability 5/5.
- **GNIDA — strong.** Migrated to **gnida.up.gov.in** (old greaternoidaauthority.in redirects, expired SSL). Clean HTML: OC/completion table https://gnida.up.gov.in/en/page/group-housing-completion-up-to-date-19-23 ; per-developer builder-project pages; defaulter lists; schemes https://gnida.up.gov.in/en/feature/schemes.
- **GDA (Ghaziabad) — workable.** Draw-result PDFs naming the developer behind each private "41D" scheme: https://gdaghaziabad.in/draw-results/ + /draw-result-archive/ ; zone-wise sanctioned-map PDFs. (403s the datacenter fetcher; works via browser UA.)
- **YEIDA — weak.** Draw results OTP-gated per applicant; allotment on external AuctionTiger portal (https://yeida.auctiontiger.net/EPROC/).
- **LDA (Lucknow) — weak.** Only individual-citizen lotteries + an unauthorized-colony blacklist; no builder-project register.

**RERA side (launched): statewide but harder plumbing.**
- https://www.up-rera.in/ → "Registered Projects" is an ASP.NET `__doPostBack` control + **CAPTCHA**. ~1,900–2,000 projects, district-tagged, data-rich (incl. QPRs). No clean paginated URL or master PDF found. Scrapability 3/5 (session-aware scraper or manual seed).

**The join: FUZZY**, on developer + project + sector/area, per authority.

**Main obstacle:** the single strongest signal — *who won an e-auction plot* — is
almost never a clean table on the authority site; it lives on external bidding portals
(SBI eAuction, AuctionTiger, procure247) and scanned PDFs. On-site map-approval data
(map.up.gov.in, GDA/YEIDA BPMS) is per-record login lookup, not bulk. Expect real
PDF-parsing effort and periodic breakage (expired certs, domain migrations).

---

---

## Southern states (Taran: brands especially interested here)

### Tamil Nadu — BEST southern candidate (deterministic, messy)
The only southern state with Haryana's key property: **RERA cites the approval number**.
- **RERA:** https://rera.tn.gov.in/registered-layout/tn and /registered-building/tn → clean static HTML tables, no login/CAPTCHA/pagination, ~956 buildings + ~10,550 layouts. The **Approval Details column cites the DTCP/CMDA layout-approval number** (e.g. "Layout No. 207/2022", "…Letter No. CBEREGN/…/TCP"). Scrapability 5/5.
- **Permission side (two buckets):** CMDA / Chennai Metro = static per-year HTML tables https://cmdachennai.gov.in/approved_layout.html (5/5, ~309 rows for 2024, links vector approval PDFs). Rest of state = https://onlineppa.tn.gov.in/approved-plan-list — ASP.NET postback form (DTCP + panchayats, 2022→, no CMDA), scrape per district×year×type (3/5).
- **Join: DETERMINISTIC** on approval number (free-text, per-authority regex needed), fuzzy fallback on village + extent + local body.
- **Main catch:** the **developer NAME is largely absent on the permission side** — CMDA PDFs give approval no + village + area + survey + date but not the promoter. You can identify *which approved parcels haven't registered*, but naming the developer needs the onlineppa approval-**letter** PDFs (unverified whether they name the applicant) or an external source, because the clean name appears only once the project reaches RERA (the set you're excluding). Two items to verify in a browser: onlineppa letter contents, and whether RERA year pages are the complete universe.

### Andhra Pradesh — favorable structure, JS/session-gated (deterministic-in-principle, fuzzy-in-practice)
- **Statewide-centralized** on one APDPMS/BPAMS instance — structurally the closest to Haryana.
- **RERA:** https://rera.ap.gov.in/RERA/Views/Reports/ApprovedProjects.aspx dumps the **entire ~7,000-project list on one no-CAPTCHA page** (32 MB, "Export to Excel" available) — current to 29/07/2026. BUT the bulk list has only 8 fields (no promoter, no permit no.); those live on per-project `Project.aspx?enc=…` which **302-redirects without a browser session**. RERA registration IDs embed the approving authority (e.g. `…-04-2021-1172-DTCP-DPMS`). Bulk 4/5, detail 2/5.
- **Permission side:** old DTCP registers are dead (404). Current public register https://apdpms.ap.gov.in/BPAMSClient/Common/OpList.aspx is a JS/SOAP TreeGrid whose data service 500s for external callers; the `:8085` host is firewalled. Needs a headless browser. 2/5.
- **RERA captures "Building Plan No" + Plan Approving Authority** on the registration form → deterministic join *on paper*, but both the permit number (session-gated RERA detail) and the permit register (JS/SOAP) are hard to bulk-extract, so it degrades to fuzzy in practice.
- **Verdict:** promising but needs a browser-driven scoping spike to confirm (i) OpList returns statewide rows anonymously and (ii) Project.aspx shows Building Plan No publicly. More engineering than TN/Punjab.

### Karnataka — RERA strong, permission side broken, no key (not buildable Haryana-style today)
- **RERA:** https://rera.karnataka.gov.in/viewDefaultProjects → public, no-CAPTCHA, server-rendered table (~3,000 rows: promoter, project, district, type, dates). Scrapability 4/5. `viewAllProjects` is JS/DataTables; detail pages are POST-only.
- **Permission side is the weakest of any state:** no statewide register, and every authority portal was down/unreachable — BDA mid-migration + SSL-mismatch, DTCP Karnataka **DNS dead**, BMRDA process-docs-only, BBMP sanction PDFs (address-level building permits, not layouts) refused the fetcher.
- **No shared key:** K-RERA does NOT cite the BDA/BBMP/DTCP approval number as a structured field (it's inside uploaded PDFs). Fuzzy-only, permission side barely accessible.

### Kerala — RERA works (deterministic key inside the record), but permission universe can't be enumerated
- **RERA:** https://rera.kerala.gov.in/projects (paged via /explore-projects?page=N) — browsable, filterable, and each record carries **Permit Number + Issuing Authority + Local Body + Extent** = a deterministic key, like Haryana. BUT the portal bot-blocks (503; confirmed live via third-party scrapes) — needs a real browser. Scrapability 4/5 with a browser.
- **Permission side:** building permits run through per-local-body Sanketham/K-SMART, **login-gated** with only a GIS "Issued Permit Map" public and 70% house-level noise; TCP layout permissions are scattered per-district PDFs.
- **Consequence:** you can read the permit off each RERA record, but you **cannot enumerate the full permission universe** to compute "permitted-but-not-registered." Viable as **RERA-anchored enrichment only**, not the Haryana-style difference.

---

## Verdict & recommendation — all seven states

| State | Permission side | RERA side | Join | Pre-launch "ripe" signal |
|---|---|---|---|---|
| **Haryana** | ✅ 1 statewide register (+ pending) | ✅ statewide | ✅ deterministic | ✅ strong (done) |
| **Tamil Nadu** | ⚠️ CMDA static + onlineppa postback; dev name missing | ✅ static HTML, cites approval no. | ✅ deterministic (messy) | ✅ strong — best new build |
| **Punjab** | ⚠️ ~6 authority lists (HTML/PDF), granted-only | ✅ statewide + master PDF w/ contacts | ❌ fuzzy | ✅ workable |
| **Andhra Pradesh** | ❌ APDPMS JS/SOAP-gated; static regs 404 | ✅ full ~7k list, but permit no. session-gated | ◑ determ. on paper, fuzzy in practice | ⚠️ needs headless-browser spike |
| **Uttar Pradesh** | ⚠️ NCR authorities only (NOIDA JSON best) | ⚠️ postback + CAPTCHA | ❌ fuzzy | ⚠️ NCR only, patchy |
| **Karnataka** | ❌ portals down/dead, no dev-name key | ✅ ~3k rows, no CAPTCHA | ❌ fuzzy, no key | ❌ not buildable now |
| **Kerala** | ❌ login-gated / fragmented, can't enumerate | ✅ paged list w/ permit no. (bot-blocked) | ✅ key exists but one-sided | ❌ RERA enrichment only |

### Re-scored for LEAD GENERATION as the product

Lead generation is the product; market intelligence (competitor DBs, benchmarks, city
intel — §11–§13) is administrative/supporting, not a reason to enter a state. So the RERA
(launched-project) layer being scrapable everywhere is **not** an expansion argument —
RERA = already launched = past the moment Caspar brokers a tie-up. The only question per
state is: **can we produce a list of NAMED developers holding land/approval who have NOT
launched, with a way to reach them?** A pre-launch parcel with no developer name is half a
lead. That reweights the ranking:

| Rank | State | Named, contactable, pre-launch leads? |
|---|---|---|
| 1 | **Punjab** | ✅ PAPRA licence lists name the promoter, are enumerable, carry grant date + status; RERA PDF adds phone/email. The recent-non-completed licence list is *itself* a named-lead list — the RERA diff just removes those who launched. |
| 2 | **UP — NCR only** | ✅ NOIDA JSON + GNIDA builder pages name the developer (Gautam Buddh Nagar / Ghaziabad). Contact enrichment needed. |
| 3 | **Tamil Nadu** | ⚠️ Cleanest data + deterministic match, BUT developer NAME missing on permission side — "hot parcels, no one to call" until onlineppa approval-letter names / land records are cracked. Verify first. |
| 4 | **Andhra Pradesh** | ⚠️ Names behind JS/SOAP/session gates — needs the browser spike. |
| — | **Karnataka, Kerala** | ❌ Off the lead-gen list — permission side inaccessible (Karnataka) / can't enumerate (Kerala). RERA-only ≠ product. |

**Implication for Haryana too:** person-level verified contacts (§9) are the highest-value
work, because a ripe parcel without a reachable decision-maker is a research task, not a lead.

**Recommended order:** Punjab → UP (NCR) → Tamil Nadu (after name-gap spike) → Andhra
(after browser spike). Drop Karnataka & Kerala for lead-gen.

**Don't promise "same as Haryana" anywhere.** Accurate framing for Varun/Taran: *Haryana is
uniquely open; Punjab reproduces it (fuzzy) and delivers named contacts; UP works for the
NCR authorities; Tamil Nadu has the best structure but needs the developer-name gap solved;
AP needs a spike; Karnataka & Kerala don't support lead-gen from public data today.*

**Caveat on method:** several state portals refused the datacenter fetcher (SSL-expired,
ECONNREFUSED, 403, WAF/503, session/postback gates). Those are almost certainly fine in a
real browser — confirm the shortlisted ones (TN onlineppa letters, AP OpList/Project.aspx,
Kerala RERA, Punjab PUDA/JDA) in the in-app browser before committing engineering effort.
