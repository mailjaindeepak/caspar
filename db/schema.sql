-- Caspar market-intelligence DB (per ARCHITECTURE.md)
-- Source layer: verbatim from scrapers, append-with-snapshot.
-- Resolution layer: entities, parcels, links (all cross-source claims).
-- Derived layer: views only.

PRAGMA journal_mode = WAL;

-- ============ SOURCE LAYER ============

CREATE TABLE IF NOT EXISTS licence_raw (
    licence_no      TEXT NOT NULL,
    lc_case_no      TEXT,
    file_id         TEXT,
    colony_name     TEXT,
    issue_date      TEXT,           -- dd/mm/yyyy as printed
    purpose         TEXT,           -- RPL/RGH/DDJAY-APHP/AHP/CPL/CIR/CIC/IPA/NILP
    area_acre       REAL,
    dev_plan        TEXT,           -- town within district
    sector          TEXT,
    valid_upto_raw  TEXT,           -- free text: dates + cancellation strings
    developer_raw   TEXT,
    district        TEXT,
    scraped_at      TEXT NOT NULL,
    PRIMARY KEY (licence_no, file_id)
);

CREATE TABLE IF NOT EXISTS licence_application_raw (   -- rejected/returned/withdrawn/lapsed
    row_id          INTEGER PRIMARY KEY,
    applicant_raw   TEXT,
    purpose         TEXT,
    area_acre       REAL,
    dev_plan        TEXT,
    sector          TEXT,
    status          TEXT,           -- Rejected|Returned|Withdrawn|Lapsed
    status_date     TEXT,
    district        TEXT,
    detail          TEXT,
    scraped_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rera_raw (
    rera_reg_no     TEXT PRIMARY KEY,
    temp_id         TEXT,
    project_name    TEXT,
    promoter_raw    TEXT,
    address         TEXT,
    district        TEXT,
    registered_with TEXT,
    bench_path      TEXT,
    links           TEXT,           -- certificate / A-H hrefs
    area_acre_derived REAL,
    sector_derived  TEXT,
    licence_no_cited TEXT,          -- Phase 1: from A-H PDF
    promoter_email  TEXT,           -- Phase 1: from certificate PDF
    promoter_phone  TEXT,
    scraped_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS clu_raw (
    clu_file_no     TEXT PRIMARY KEY,
    applicant       TEXT,
    village         TEXT,
    purpose         TEXT,
    activity        TEXT,
    granted_area_sqm REAL,
    area_acre       REAL,
    district        TEXT,
    sanction_date   TEXT,
    corrigendum_date TEXT,
    clu_year        INTEGER,
    scraped_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_raw (
    cert_no         TEXT,
    agent_name      TEXT,
    district        TEXT,
    category        TEXT,
    issue_date      TEXT,
    expiry_date     TEXT,
    bench_path      TEXT,
    cert_link       TEXT,
    scraped_at      TEXT NOT NULL,
    PRIMARY KEY (cert_no, agent_name)
);

-- ============ RESOLUTION LAYER ============

CREATE TABLE IF NOT EXISTS entity (
    entity_id       INTEGER PRIMARY KEY,
    canonical_name  TEXT NOT NULL UNIQUE,
    kind            TEXT DEFAULT 'developer',   -- developer|individual|hotel_group|investor
    cin             TEXT,
    group_parent    TEXT,
    tier            TEXT,                       -- A|A*|A-|B|B-|C+|C
    score           REAL,
    score_notes     TEXT,
    hq_city         TEXT,
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS entity_alias (
    alias_id        INTEGER PRIMARY KEY,
    entity_id       INTEGER NOT NULL REFERENCES entity(entity_id),
    alias_name      TEXT NOT NULL,
    alias_norm      TEXT,
    source          TEXT,           -- clu|licence|rera|mca|gis|manual
    source_row_key  TEXT,
    method          TEXT,           -- exact|brand_fuzzy|area_rescue|din_overlap|manual
    confidence      REAL,
    reviewed_by     TEXT,
    reviewed_at     TEXT
);

CREATE TABLE IF NOT EXISTS stakeholder (
    stakeholder_id  INTEGER PRIMARY KEY,
    entity_id       INTEGER REFERENCES entity(entity_id),
    person_name     TEXT,
    role            TEXT,
    email           TEXT,
    phone           TEXT,
    linkedin        TEXT,
    confidence      TEXT,           -- official|registry|3p
    source_note     TEXT
);

CREATE TABLE IF NOT EXISTS parcel (
    parcel_id       INTEGER PRIMARY KEY,
    city            TEXT,
    dev_plan        TEXT,
    sector          TEXT,
    village         TEXT,
    area_acre       REAL,
    wkt_utm43n      TEXT,
    centroid_lat    REAL,
    centroid_lng    REAL,
    current_stage   TEXT,           -- clu|licensed|rera_registered|launched|delivered
    controlling_entity_id INTEGER REFERENCES entity(entity_id),
    lc_case_no      TEXT
);

CREATE TABLE IF NOT EXISTS parcel_link (
    link_id         INTEGER PRIMARY KEY,
    parcel_id       INTEGER NOT NULL REFERENCES parcel(parcel_id),
    source          TEXT NOT NULL,  -- clu|licence|rera
    source_row_key  TEXT NOT NULL,
    method          TEXT,           -- ah_citation|name+area|name+sector|name_only|manual
    confidence      REAL,
    status          TEXT,           -- PARCEL-MATCH|SPV-MATCH?|DEV-MATCH|manual-confirmed|rejected
    reviewed_by     TEXT,
    reviewed_at     TEXT
);

CREATE TABLE IF NOT EXISTS gatekeeper (
    gatekeeper_id   INTEGER PRIMARY KEY,
    name            TEXT,
    kind            TEXT,           -- broker|architect|ca|other
    city            TEXT,
    firm            TEXT,
    phone           TEXT,
    email           TEXT,
    rera_cert_no    TEXT,
    relationship    TEXT,           -- identified|contacted|active|dormant
    commission_note TEXT
);

CREATE TABLE IF NOT EXISTS signal (
    signal_id       INTEGER PRIMARY KEY,
    gatekeeper_id   INTEGER REFERENCES gatekeeper(gatekeeper_id),
    city            TEXT,
    about_entity_id INTEGER REFERENCES entity(entity_id),
    about_parcel_id INTEGER REFERENCES parcel(parcel_id),
    signal_text     TEXT,
    received_at     TEXT,
    verified        INTEGER DEFAULT 0
);

-- ============ BENCHMARK LAYER ============

CREATE TABLE IF NOT EXISTS locality_benchmark (
    locality_id     INTEGER PRIMARY KEY,
    city            TEXT,
    name            TEXT,           -- "Sector 29", "Nilokheri", ...
    tier            TEXT,           -- prime|secondary|value
    rate_low        REAL,
    rate_high       REAL,
    rate_unit       TEXT,
    evidence        TEXT,           -- json-ish text: sources for the call
    as_of           TEXT,
    confirmed_by    TEXT
);

-- ============ DERIVED VIEWS ============

DROP VIEW IF EXISTS v_ripe_parcels;
CREATE VIEW v_ripe_parcels AS
SELECT
    l.licence_no, l.issue_date, l.purpose, l.area_acre, l.dev_plan, l.sector,
    l.developer_raw, l.valid_upto_raw,
    e.canonical_name AS developer_group, e.tier, e.score,
    p.centroid_lat, p.centroid_lng, p.parcel_id,
    lb.tier AS locality_tier,
    (CASE WHEN e.tier IN ('A','A*','A-') THEN 3
          WHEN e.tier LIKE 'B%' THEN 2 ELSE 1 END) AS entity_rank,
    (CASE WHEN lb.tier = 'prime' THEN 2 WHEN lb.tier = 'secondary' THEN 1 ELSE 0 END) AS locality_rank
FROM licence_raw l
LEFT JOIN entity_alias ea
       ON ea.source = 'licence' AND ea.source_row_key = l.licence_no
LEFT JOIN entity e ON e.entity_id = ea.entity_id
LEFT JOIN parcel p ON p.lc_case_no = l.lc_case_no
LEFT JOIN locality_benchmark lb
       ON lb.city = l.district AND lb.name = 'Sector ' || l.sector
WHERE l.purpose IN ('RPL', 'RGH', 'AHP', 'NILP', 'DDJAY-APHP')
  AND CAST(substr(l.issue_date, 7, 4) AS INTEGER) >= 2017
  AND l.area_acre >= 4
  AND l.valid_upto_raw NOT LIKE '%cancel%'
  AND date(substr(l.valid_upto_raw, 7, 4) || '-' || substr(l.valid_upto_raw, 4, 2)
           || '-' || substr(l.valid_upto_raw, 1, 2)) >= date('now')
  AND NOT EXISTS (
      SELECT 1 FROM parcel_link pl
      JOIN parcel pp ON pp.parcel_id = pl.parcel_id
      WHERE pp.lc_case_no = l.lc_case_no
        AND pl.source = 'rera'
        AND pl.status IN ('PARCEL-MATCH', 'manual-confirmed'))
ORDER BY entity_rank DESC, locality_rank DESC, l.area_acre DESC;

DROP VIEW IF EXISTS v_hospitality_leads;
CREATE VIEW v_hospitality_leads AS
SELECT clu_file_no, applicant, village, activity, area_acre, sanction_date, clu_year, district
FROM clu_raw
WHERE lower(activity) LIKE '%hotel%' OR lower(activity) LIKE '%motel%'
   OR lower(activity) LIKE '%resort%' OR lower(activity) LIKE '%banquet%'
   OR lower(activity) LIKE '%farm%house%' OR lower(activity) LIKE '%farmhouse%'
   OR lower(activity) LIKE '%amusement%' OR lower(activity) LIKE '%club%'
   OR lower(activity) LIKE '%restaurant%' OR lower(activity) LIKE '%dhaba%'
   OR lower(activity) LIKE '%guest%' OR lower(activity) LIKE '%boarding%'
   OR lower(activity) LIKE '%marriage%' OR lower(activity) LIKE '%wedding%'
ORDER BY clu_year DESC, area_acre DESC;

DROP VIEW IF EXISTS v_call_list;
CREATE VIEW v_call_list AS
SELECT e.canonical_name, e.tier, e.score, e.score_notes,
       group_concat(DISTINCT s.person_name || ' (' || s.role || ')') AS people,
       group_concat(DISTINCT s.email)  AS emails,
       group_concat(DISTINCT s.phone)  AS phones
FROM entity e
LEFT JOIN stakeholder s ON s.entity_id = e.entity_id
WHERE e.tier IN ('A', 'A*', 'A-', 'B', 'B-')
GROUP BY e.entity_id
ORDER BY e.score DESC;
