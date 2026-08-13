"""Build caspar.db and load all Karnal Phase-0 data.

Idempotent: drops and reloads Karnal rows on each run.
Usage: python db/build_karnal.py
"""
import csv
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scrapers"))
from cluster_developers import norm  # noqa: E402

DB = ROOT / "db" / "caspar.db"
DATA = ROOT / "data" / "karnal"
SCRATCH = Path(r"C:\Users\DELL\AppData\Local\Temp\claude\D--working-caspar"
               r"\09495f6a-677c-4ec7-9afc-91ece79f0690\scratchpad")
NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")
KARNAL_TOWNS = {"KARNAL", "NILOKHERI AND TARAORI", "GHARAUNDA", "ASSANDH", "INDRI"}


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def f(x):
    try:
        return float(str(x).strip())
    except (ValueError, TypeError):
        return None


def load_sources(cx: sqlite3.Connection) -> None:
    cx.execute("DELETE FROM licence_raw WHERE district='Karnal'")
    for r in read_csv(DATA / "dtcp_licences.csv"):
        lc = (re.match(r"(LC-\d+)", r.get("CaseNo", "") or "") or [None, None])[1]
        cx.execute(
            "INSERT OR REPLACE INTO licence_raw VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (r["LicenseNo"], lc, r["FileID"], r["Colony"], r["IssueDate"],
             r["Purpose"], f(r["Area_acre"]), r["DevPlan"].upper(), r["Sector"],
             r["ValidUpto"], r["Developer"], "Karnal", NOW))

    cx.execute("DELETE FROM licence_application_raw WHERE district='Karnal'")
    html = (SCRATCH / "rej.html").read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(html, "lxml")
    n_apps = 0
    for table in soup.find_all("table"):
        trs = table.find_all("tr")
        if len(trs) < 5:
            continue
        for tr in trs[1:]:
            c = [td.get_text(" ", strip=True) for td in tr.find_all(["th", "td"])]
            if len(c) < 10 or c[5].strip().upper() not in KARNAL_TOWNS:
                continue
            cx.execute(
                "INSERT INTO licence_application_raw"
                "(applicant_raw,purpose,area_acre,dev_plan,sector,status,"
                " status_date,district,detail,scraped_at)"
                " VALUES (?,?,?,?,?,?,?,?,?,?)",
                (c[7], c[3], f(c[4]), c[5], c[6], c[8], c[9], "Karnal", c[1], NOW))
            n_apps += 1

    cx.execute("DELETE FROM rera_raw WHERE district='KARNAL'")
    for r in read_csv(DATA / "harera_projects.csv"):
        blob = f"{r.get('Project Name','')} {r.get('Project Address','')}"
        am = re.search(r"AREA[^0-9]{0,15}(\d+(?:\.\d+)?)", blob, re.I) or \
             re.search(r"(\d+(?:\.\d+)?)\s*ACRES?", blob, re.I)
        sm = re.search(r"SEC(?:TOR)?[\s.\-]*(\d+[A-Z]?)", blob, re.I)
        cx.execute(
            "INSERT OR REPLACE INTO rera_raw VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (r.get("Project Registration Number", "") or r.get("Project Temp-ID", ""),
             r.get("Project Temp-ID", ""), r.get("Project Name", ""),
             r.get("Promoter Name", ""), r.get("Project Address", ""),
             r.get("Project District", ""), r.get("Registered With", ""),
             r.get("bench_path", ""), r.get("links", ""),
             f(am.group(1)) if am else None, sm.group(1).upper() if sm else None,
             None, None, None, NOW))

    cx.execute("DELETE FROM clu_raw WHERE district='Karnal'")
    for r in read_csv(DATA / "clu_permissions.csv"):
        sqm = f(re.sub(r"[^\d.]", "", r.get("Granted Area", "") or "") or None)
        cx.execute(
            "INSERT OR REPLACE INTO clu_raw VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (r.get("File No", ""), r.get("Applicant Name", ""),
             r.get("Location/ Controlled Area", ""), r.get("Purpose", ""),
             r.get("Activity", ""), sqm, (sqm / 4046.86) if sqm else None,
             r.get("District", ""), r.get("CLU Permission on", ""),
             r.get("CLU Corrigendum on", ""), int(r.get("clu_year", 0)), NOW))

    cx.execute("DELETE FROM agent_raw WHERE district='KARNAL'")
    for r in read_csv(DATA / "harera_agents.csv"):
        cx.execute(
            "INSERT OR REPLACE INTO agent_raw VALUES (?,?,?,?,?,?,?,?,?)",
            (r.get("Registration Certificate No.", ""), r.get("Agent Name", ""),
             r.get("District", ""), r.get("Category", ""),
             r.get("Certificate Issuing Date", ""),
             r.get("Certificate Expiry Date", ""), r.get("bench_path", ""),
             r.get("cert_link", ""), NOW))
    print(f"sources: {n_apps} applications + licences/rera/clu/agents loaded")


# Manual SPV → group mappings discovered in Phase 0 (method=manual, conf=1.0)
MANUAL_ALIASES = {
    "Signature Global":  ["MAA VAISHNO NET-TECH PVT. LTD.",
                          "FANTABULOUS TOWN PLANNERS PVT. LTD."],
    "Alpha Corp":        ["Grandeur Real Estate", "ALPHACORP DEVELOPMENT PVT. LTD.",
                          "Alpha Corp. Development Pvt. Ltd."],
    "Eterna Living (ex-Ansal Landmark; Dalmia Group)":
                         ["ANSAL LANDMARK(KARNAL) TOWNSHIP PVT. LTD",
                          "Ansal Properties & Infrastructure",
                          "ETERNA LIVING PVT LTD"],
    "Golf Links (Levity)": ["LEVITY ENTERPRISES PRIVATE LIMITED",
                            "Golf Link Projects", "GOLF LINK PROJECTS PVT LTD"],
}

STAKEHOLDERS = [
    ("Alpha Corp", "Ashish Sarin", "CEO & Director (DIN 00897673)",
     "sales@alphacorp.in; secretarial@alphacorp.in", "+91 11-48311111; +91 95552 80280",
     "linkedin.com/in/ashish-sarin-8678623", "official"),
    ("Alpha Corp", "Santosh Agarwal", "Exec. Director & CFO", None, None, None, "official"),
    ("Jewel Classic Hotels (strategic)", "Col. Manbeer Choudhary", "CMD",
     "mgr.accounts@noormahal.in", "+91 184 713 3333; +91 99967 87886", None, "3p"),
    ("Jewel Classic Hotels (strategic)", "Roop Partap Choudhary", "Executive Director",
     None, None, "linkedin.com/in/roop-partap-choudhary", "official"),
    ("Jewel Classic Hotels (strategic)", "Binny Choudhary", "Jt. MD", None, None, None, "official"),
    ("Eterna Living (ex-Ansal Landmark; Dalmia Group)", "Gaurav Dalmia",
     "Director / Dalmia Group control", "vkaushal@eterna-living.in",
     "+91-11-43621200; +91 93559 45508", None, "registry"),
    ("CHD Developers", "Rajesh Kumar Parakh", "Resolution Professional (CIRP)",
     "info@chddevelopers.com", "+91 8929 400 100", None, "registry"),
    ("CHD Developers", "Gaurav Mittal", "MD (promoter)", None, None, None, "3p"),
    ("Rajdarbar Builders", "Chaitanya Garg", "Board, Rajdarbar Group",
     "info@rajdarbarrealty.com", "+91 99918 88651",
     "linkedin.com/in/chaitanya-garg-a5277a17", "official"),
    ("Golf Links (Levity)", None, "Beneficial owner unknown — route via broker",
     "info@golflinkprojects.com", "011-48006514; +91 95177 70043", None, "official"),
]

LOCALITIES = [
    ("Karnal", "Sector 28", "prime", 9000, 12200, "₹/sqft",
     "Alpha Intl City rates 99acres; +178%/5yr"),
    ("Karnal", "Sector 28A", "prime", 9000, 12200, "₹/sqft", "Alpha township belt"),
    ("Karnal", "Sector 29", "prime", 9000, 12200, "₹/sqft",
     "Alpha belt; Haryana Promoters 24.9ac 770m away"),
    ("Karnal", "Sector 32", "prime", 80000, 125000, "₹/sqyd",
     "HSVP S+4 corridor (Tribune); FY26 collector hike ~70%"),
    ("Karnal", "Sector 33", "prime", 80000, 125000, "₹/sqyd", "HSVP S+4 corridor"),
    ("Karnal", "Sector 36", "secondary", None, None, None,
     "Sushant City; ₹2.5 Cr villas prove premium absorption"),
    ("Karnal", "Sector 45", "secondary", None, None, None, "CHD City belt"),
    ("Karnal", "Sector 35", "secondary", None, None, None, "Parsvnath/SG Sunrise/RAS"),
    ("Karnal", "Sector 6/7/9 + Urban Estate + Model Town", "prime", None, None, None,
     "Established HSVP kothi sectors; rates thin online — confirm w/ dealers"),
    ("Karnal", "NILOKHERI AND TARAORI", "value", None, None, None, "DDJAY belt"),
    ("Karnal", "GHARAUNDA", "value", None, None, None, "DDJAY/industrial belt"),
    ("Karnal", "ASSANDH", "value", None, None, None, "DDJAY belt"),
    ("Karnal", "INDRI", "value", None, None, None, "peripheral"),
]


def load_entities(cx: sqlite3.Connection) -> None:
    cx.execute("DELETE FROM entity_alias")
    cx.execute("DELETE FROM stakeholder")
    cx.execute("DELETE FROM entity")

    scored = read_csv(DATA / "scored_developers.csv")
    for r in scored:
        if r["developer_group"].startswith("("):     # long-tail bucket row
            continue
        cx.execute(
            "INSERT INTO entity (canonical_name, tier, score, score_notes, kind)"
            " VALUES (?,?,?,?,?)",
            (r["developer_group"], r["tier"], f(r["score"]), r["notes"],
             "hotel_group" if "Jewel" in r["developer_group"] else "developer"))
        eid = cx.execute("SELECT last_insert_rowid()").fetchone()[0]
        for alias in r["rera_entities"].split(";"):
            if alias.strip():
                cx.execute(
                    "INSERT INTO entity_alias (entity_id, alias_name, alias_norm,"
                    " source, method, confidence) VALUES (?,?,?,?,?,?)",
                    (eid, alias.strip(), norm(alias), "manual", "manual", 1.0))

    # Long-tail groups from clustering become Tier C entities
    for r in read_csv(DATA / "developers.csv"):
        names = [n.strip() for n in r["promoter_names"].split("|")]
        if cx.execute("SELECT 1 FROM entity_alias WHERE alias_norm=?",
                      (r["developer_key"],)).fetchone():
            continue
        hit = cx.execute("SELECT entity_id FROM entity_alias WHERE alias_norm LIKE ?",
                         (r["developer_key"][:12] + "%",)).fetchone()
        if hit:
            eid = hit[0]
        else:
            cx.execute("INSERT OR IGNORE INTO entity (canonical_name, tier) VALUES (?,'C')",
                       (names[0].title(),))
            row = cx.execute("SELECT entity_id FROM entity WHERE canonical_name=?",
                             (names[0].title(),)).fetchone()
            eid = row[0]
        for n in names:
            cx.execute(
                "INSERT INTO entity_alias (entity_id, alias_name, alias_norm, source,"
                " method, confidence) VALUES (?,?,?,?,?,?)",
                (eid, n, norm(n), "rera", "cluster", 0.9))

    for canonical, aliases in MANUAL_ALIASES.items():
        row = cx.execute("SELECT entity_id FROM entity WHERE canonical_name LIKE ?",
                         (canonical.split(" (")[0] + "%",)).fetchone()
        if not row:
            continue
        for a in aliases:
            cx.execute(
                "INSERT INTO entity_alias (entity_id, alias_name, alias_norm, source,"
                " method, confidence, reviewed_by) VALUES (?,?,?,?,?,?,?)",
                (row[0], a, norm(a), "manual", "manual", 1.0, "phase0-research"))

    # Alias every licence row to an entity where a normalized match exists
    for lic_no, dev in cx.execute(
            "SELECT licence_no, developer_raw FROM licence_raw").fetchall():
        k = norm(dev or "")
        hit = cx.execute(
            "SELECT entity_id FROM entity_alias WHERE alias_norm=? LIMIT 1", (k,)
        ).fetchone()
        if hit:
            cx.execute(
                "INSERT INTO entity_alias (entity_id, alias_name, alias_norm, source,"
                " source_row_key, method, confidence) VALUES (?,?,?,?,?,?,?)",
                (hit[0], dev, k, "licence", lic_no, "exact_norm", 0.95))

    for group, person, role, email, phone, li, conf in STAKEHOLDERS:
        row = cx.execute("SELECT entity_id FROM entity WHERE canonical_name LIKE ?",
                         (group.split(" (")[0] + "%",)).fetchone()
        cx.execute(
            "INSERT INTO stakeholder (entity_id, person_name, role, email, phone,"
            " linkedin, confidence) VALUES (?,?,?,?,?,?,?)",
            (row[0] if row else None, person, role, email, phone, li, conf))

    cx.execute("DELETE FROM locality_benchmark WHERE city='Karnal'")
    for city, name, tier, lo, hi, unit, ev in LOCALITIES:
        cx.execute(
            "INSERT INTO locality_benchmark (city, name, tier, rate_low, rate_high,"
            " rate_unit, evidence, as_of) VALUES (?,?,?,?,?,?,?,?)",
            (city, name, tier, lo, hi, unit, ev, "2026-08"))

    n_e = cx.execute("SELECT count(*) FROM entity").fetchone()[0]
    n_a = cx.execute("SELECT count(*) FROM entity_alias").fetchone()[0]
    print(f"entities: {n_e}, aliases: {n_a}, stakeholders: {len(STAKEHOLDERS)}, "
          f"localities: {len(LOCALITIES)}")


def load_parcels_and_links(cx: sqlite3.Connection) -> None:
    """Parcels from licences (geometry filled by fetch_polygons.py);
    links from the Phase-0 licence↔RERA mapping."""
    cx.execute("DELETE FROM parcel_link")
    cx.execute("DELETE FROM parcel")
    for lc, dev, sector, dev_plan, area in cx.execute(
            "SELECT lc_case_no, developer_raw, sector, dev_plan,"
            " sum(area_acre) FROM licence_raw WHERE lc_case_no IS NOT NULL"
            " GROUP BY lc_case_no").fetchall():
        ent = cx.execute(
            "SELECT entity_id FROM entity_alias WHERE alias_norm=? LIMIT 1",
            (norm(dev or ""),)).fetchone()
        cx.execute(
            "INSERT INTO parcel (city, dev_plan, sector, area_acre, current_stage,"
            " controlling_entity_id, lc_case_no) VALUES (?,?,?,?,?,?,?)",
            ("Karnal", dev_plan, sector, area, "licensed",
             ent[0] if ent else None, lc))

    mapping = read_csv(DATA / "licence_rera_map.csv")
    lic_to_lc = dict(cx.execute(
        "SELECT licence_no, lc_case_no FROM licence_raw").fetchall())
    conf = {"PARCEL-MATCH": 0.85, "SPV-MATCH?": 0.5, "DEV-MATCH": 0.4}
    n = 0
    for m in mapping:
        lc = lic_to_lc.get(m["LicenseNo"])
        if not lc or m["match_status"] not in conf:
            continue
        pid = cx.execute("SELECT parcel_id FROM parcel WHERE lc_case_no=?",
                         (lc,)).fetchone()
        if not pid:
            continue
        cx.execute(
            "INSERT INTO parcel_link (parcel_id, source, source_row_key, method,"
            " confidence, status) VALUES (?,?,?,?,?,?)",
            (pid[0], "rera", m["rera_reg_no"], m["match_why"],
             conf[m["match_status"]], m["match_status"]))
        if m["match_status"] == "PARCEL-MATCH":
            cx.execute("UPDATE parcel SET current_stage='rera_registered'"
                       " WHERE parcel_id=?", (pid[0],))
        n += 1
    n_p = cx.execute("SELECT count(*) FROM parcel").fetchone()[0]
    print(f"parcels: {n_p}, rera links: {n}")


def load_gatekeepers(cx: sqlite3.Connection) -> None:
    cx.execute("DELETE FROM gatekeeper WHERE city='Karnal'")
    for cert, name in cx.execute(
            "SELECT cert_no, agent_name FROM agent_raw WHERE district='KARNAL'"):
        cx.execute(
            "INSERT INTO gatekeeper (name, kind, city, rera_cert_no, relationship)"
            " VALUES (?,?,?,?,?)", (name, "broker", "Karnal", cert, "identified"))
    n = cx.execute("SELECT count(*) FROM gatekeeper").fetchone()[0]
    print(f"gatekeepers: {n}")


def main() -> None:
    DB.parent.mkdir(exist_ok=True)
    cx = sqlite3.connect(DB)
    cx.executescript((ROOT / "db" / "schema.sql").read_text(encoding="utf-8"))
    load_sources(cx)
    load_entities(cx)
    load_parcels_and_links(cx)
    load_gatekeepers(cx)
    cx.commit()

    print("\n=== v_ripe_parcels ===")
    for row in cx.execute(
            "SELECT licence_no, purpose, area_acre, sector, developer_raw,"
            " coalesce(developer_group,'?'), coalesce(tier,'-'),"
            " coalesce(locality_tier,'?') FROM v_ripe_parcels"):
        print("  " + " | ".join(str(x)[:34] for x in row))
    n_h = cx.execute("SELECT count(*) FROM v_hospitality_leads"
                     " WHERE district='Karnal'").fetchone()[0]
    print(f"\nhospitality leads: {n_h}")
    cx.close()


if __name__ == "__main__":
    main()
