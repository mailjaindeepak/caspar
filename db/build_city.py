"""Load one city's scraped CSVs into caspar.db (generic version of build_karnal).

Prereqs per city (data/<city>/): dtcp_licences.csv, harera_projects.csv,
clu_permissions.csv, harera_agents.csv, developers.csv, licence_rera_map.csv.

Usage: python db/build_city.py panipat [sonipat ...]
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
from cluster_developers import norm            # noqa: E402
from dtcp_licences import CITY_TOWNS           # noqa: E402

DB = ROOT / "db" / "caspar.db"
NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")
REJ_HTML = Path(r"C:\Users\DELL\AppData\Local\Temp\claude\D--working-caspar"
                r"\09495f6a-677c-4ec7-9afc-91ece79f0690\scratchpad\rej.html")


def read_csv(p: Path) -> list[dict]:
    with p.open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def f(x):
    try:
        return float(str(x).strip())
    except (ValueError, TypeError):
        return None


def build(cx: sqlite3.Connection, city: str) -> None:
    d = ROOT / "data" / city
    district = city.title()
    towns = [t.strip() for t in CITY_TOWNS[city]]

    cx.execute("DELETE FROM licence_raw WHERE district=?", (district,))
    for r in read_csv(d / "dtcp_licences.csv"):
        lc = (re.match(r"(LC-\d+)", r.get("CaseNo", "") or "") or [None, None])[1]
        cx.execute(
            "INSERT OR REPLACE INTO licence_raw VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (r["LicenseNo"], lc, r.get("FileID", ""), r.get("Colony", ""),
             r["IssueDate"], r["Purpose"], f(r["Area_acre"]),
             (r.get("DevPlan") or r.get("DevPlanRaw", "")).upper(),
             r.get("Sector", ""), r.get("ValidUpto", ""), r["Developer"],
             district, NOW))

    cx.execute("DELETE FROM licence_application_raw WHERE district=?", (district,))
    soup = BeautifulSoup(REJ_HTML.read_text(encoding="utf-8", errors="ignore"), "lxml")
    n_apps = 0
    for table in soup.find_all("table"):
        trs = table.find_all("tr")
        if len(trs) < 5:
            continue
        for tr in trs[1:]:
            c = [td.get_text(" ", strip=True) for td in tr.find_all(["th", "td"])]
            if len(c) < 10:
                continue
            plan = c[5].strip().upper()
            if not any(t in plan for t in towns):
                continue
            cx.execute(
                "INSERT INTO licence_application_raw"
                "(applicant_raw,purpose,area_acre,dev_plan,sector,status,"
                " status_date,district,detail,scraped_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (c[7], c[3], f(c[4]), c[5], c[6], c[8], c[9], district, c[1], NOW))
            n_apps += 1

    # preserve REP-I enrichment (citations, promoter contacts) across the
    # rebuild — the harera CSV never carries these, so a plain reload wipes them
    enrich = {row[0]: row[1:] for row in cx.execute(
        "SELECT rera_reg_no, licence_no_cited, promoter_email, promoter_phone "
        "FROM rera_raw WHERE district=?", (city.upper(),))}
    cx.execute("DELETE FROM rera_raw WHERE district=?", (city.upper(),))
    for r in read_csv(d / "harera_projects.csv"):
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
    for reg, (cited, em, ph) in enrich.items():
        cx.execute(
            "UPDATE rera_raw SET licence_no_cited=COALESCE(licence_no_cited, ?),"
            " promoter_email=COALESCE(promoter_email, ?),"
            " promoter_phone=COALESCE(promoter_phone, ?) WHERE rera_reg_no=?",
            (cited, em, ph, reg))

    cx.execute("DELETE FROM clu_raw WHERE district=?", (district,))
    for r in read_csv(d / "clu_permissions.csv"):
        sqm = f(re.sub(r"[^\d.]", "", r.get("Granted Area", "") or "") or None)
        cx.execute(
            "INSERT OR REPLACE INTO clu_raw VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (r.get("File No", ""), r.get("Applicant Name", ""),
             r.get("Location/ Controlled Area", ""), r.get("Purpose", ""),
             r.get("Activity", ""), sqm, (sqm / 4046.86) if sqm else None,
             r.get("District", ""), r.get("CLU Permission on", ""),
             r.get("CLU Corrigendum on", ""), int(r.get("clu_year", 0) or 0), NOW))

    cx.execute("DELETE FROM agent_raw WHERE district=?", (city.upper(),))
    cx.execute("DELETE FROM gatekeeper WHERE city=?", (district,))
    for r in read_csv(d / "harera_agents.csv"):
        cx.execute(
            "INSERT OR REPLACE INTO agent_raw VALUES (?,?,?,?,?,?,?,?,?)",
            (r.get("Registration Certificate No.", ""), r.get("Agent Name", ""),
             r.get("District", ""), r.get("Category", ""),
             r.get("Certificate Issuing Date", ""),
             r.get("Certificate Expiry Date", ""), r.get("bench_path", ""),
             r.get("cert_link", ""), NOW))
        cx.execute(
            "INSERT INTO gatekeeper (name, kind, city, rera_cert_no, relationship)"
            " VALUES (?,?,?,?,?)",
            (r.get("Agent Name", ""), "broker", district,
             r.get("Registration Certificate No.", ""), "identified"))

    # entities from clustering (default tier C; skip aliases already known)
    for r in read_csv(d / "developers.csv"):
        names = [n.strip() for n in r["promoter_names"].split("|") if n.strip()]
        if not names or cx.execute(
                "SELECT 1 FROM entity_alias WHERE alias_norm=?",
                (r["developer_key"],)).fetchone():
            continue
        canon = names[0].title()
        cx.execute("INSERT OR IGNORE INTO entity (canonical_name, tier) VALUES (?,'C')",
                   (canon,))
        eid = cx.execute("SELECT entity_id FROM entity WHERE canonical_name=?",
                         (canon,)).fetchone()[0]
        for n in names:
            cx.execute(
                "INSERT INTO entity_alias (entity_id, alias_name, alias_norm, source,"
                " method, confidence) VALUES (?,?,?,?,?,?)",
                (eid, n, norm(n), "rera", "cluster", 0.9))

    # alias licence rows; create entities for licence-only developers
    for lic_no, dev in cx.execute(
            "SELECT licence_no, developer_raw FROM licence_raw WHERE district=?",
            (district,)).fetchall():
        k = norm(dev or "")
        if not k:
            continue
        hit = cx.execute("SELECT entity_id FROM entity_alias WHERE alias_norm=? LIMIT 1",
                         (k,)).fetchone()
        if not hit:
            canon = (dev or "").title().strip()
            cx.execute("INSERT OR IGNORE INTO entity (canonical_name, tier) VALUES (?,'C')",
                       (canon,))
            row = cx.execute("SELECT entity_id FROM entity WHERE canonical_name=?",
                             (canon,)).fetchone()
            if not row:
                continue
            hit = row
        if not cx.execute("SELECT 1 FROM entity_alias WHERE source='licence' AND"
                          " source_row_key=? AND entity_id=?",
                          (lic_no, hit[0])).fetchone():
            cx.execute(
                "INSERT INTO entity_alias (entity_id, alias_name, alias_norm, source,"
                " source_row_key, method, confidence) VALUES (?,?,?,?,?,?,?)",
                (hit[0], dev, k, "licence", lic_no, "exact_norm", 0.95))

    # parcels + rera links
    cx.execute("DELETE FROM parcel_link WHERE parcel_id IN"
               " (SELECT parcel_id FROM parcel WHERE city=?)", (district,))
    cx.execute("DELETE FROM parcel WHERE city=?", (district,))
    for lc, dev, sector, dev_plan, area in cx.execute(
            "SELECT lc_case_no, developer_raw, sector, dev_plan, sum(area_acre)"
            " FROM licence_raw WHERE district=? AND lc_case_no IS NOT NULL"
            " GROUP BY lc_case_no", (district,)).fetchall():
        ent = cx.execute("SELECT entity_id FROM entity_alias WHERE alias_norm=? LIMIT 1",
                         (norm(dev or ""),)).fetchone()
        cx.execute(
            "INSERT INTO parcel (city, dev_plan, sector, area_acre, current_stage,"
            " controlling_entity_id, lc_case_no) VALUES (?,?,?,?,?,?,?)",
            (district, dev_plan, sector, area, "licensed",
             ent[0] if ent else None, lc))

    lic_to_lc = dict(cx.execute(
        "SELECT licence_no, lc_case_no FROM licence_raw WHERE district=?",
        (district,)).fetchall())
    conf = {"PARCEL-MATCH": 0.85, "SPV-MATCH?": 0.5, "DEV-MATCH": 0.4}
    n_links = 0
    for m in read_csv(d / "licence_rera_map.csv"):
        lc = lic_to_lc.get(m["LicenseNo"])
        if not lc or m["match_status"] not in conf:
            continue
        pid = cx.execute("SELECT parcel_id FROM parcel WHERE lc_case_no=? AND city=?",
                         (lc, district)).fetchone()
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
        n_links += 1

    n_l = cx.execute("SELECT count(*) FROM licence_raw WHERE district=?",
                     (district,)).fetchone()[0]
    n_p = cx.execute("SELECT count(*) FROM parcel WHERE city=?", (district,)).fetchone()[0]
    print(f"{city}: {n_l} licences, {n_apps} applications, {n_p} parcels, "
          f"{n_links} rera links")


def recompute_entity_flags(cx: sqlite3.Connection) -> None:
    for eid, yr in cx.execute("""
            SELECT ea.entity_id, min(CAST(substr(l.issue_date,7,4) AS INTEGER))
            FROM entity_alias ea JOIN licence_raw l ON l.developer_raw = ea.alias_name
            GROUP BY ea.entity_id""").fetchall():
        cx.execute("UPDATE entity SET first_seen_year=? WHERE entity_id=? AND"
                   " (first_seen_year IS NULL OR first_seen_year > ?)", (yr, eid, yr))
    cx.execute("UPDATE entity SET is_new = CASE WHEN first_seen_year >= 2020"
               " THEN 1 ELSE 0 END WHERE first_seen_year IS NOT NULL")


def main() -> None:
    cities = [c.lower() for c in sys.argv[1:]]
    cx = sqlite3.connect(DB)
    for city in cities:
        build(cx, city)
    recompute_entity_flags(cx)
    cx.commit()
    cx.close()


if __name__ == "__main__":
    main()
