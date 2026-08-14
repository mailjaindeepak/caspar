"""Export the outreach-ready outputs from caspar.db to outputs/<city>/.

Usage: python db/export_outputs.py [karnal]
"""
import csv
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "db" / "caspar.db"

_CORP = re.compile(r"\b(PVT|PRIVATE|LTD|LIMITED|LLP|CO|COMPANY|GROUP)\b")


def _toks(s):
    s = _CORP.sub(" ", re.sub(r"[^A-Z0-9 ]", " ", (s or "").upper()))
    return {t for t in s.split() if len(t) > 2}


def city_entity_ids(cx, district):
    """Entities that belong to a district's call list: alias-linked to its
    licence/RERA/CLU rows, HQ'd there, or name-matching its licence/RERA names."""
    ids = {r[0] for r in cx.execute("""
        SELECT DISTINCT ea.entity_id FROM entity_alias ea
        LEFT JOIN licence_raw lr ON ea.source='licence' AND lr.licence_no=ea.source_row_key
        LEFT JOIN rera_raw rr ON ea.source='rera' AND rr.rera_reg_no=ea.source_row_key
        LEFT JOIN clu_raw cr ON ea.source='clu' AND cr.clu_file_no=ea.source_row_key
        WHERE lr.district=? OR rr.district=? OR cr.district=?""",
        (district, district, district))}
    ids |= {r[0] for r in cx.execute(
        "SELECT entity_id FROM entity WHERE hq_city=?", (district,))}
    raw_names = [_toks(r[0]) for r in cx.execute(
        "SELECT developer_raw FROM licence_raw WHERE district=? UNION "
        "SELECT promoter_raw FROM rera_raw WHERE district=?", (district, district))]
    for eid, name in cx.execute("SELECT entity_id, canonical_name FROM entity"):
        t = _toks(name)
        if t and any(t <= rn or rn <= t for rn in raw_names if rn):
            ids.add(eid)
    return ids


def export(cx, sql, path, params=()):
    cur = cx.execute(sql, params)
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(rows)
    print(f"{path.name}: {len(rows)} rows")
    return rows


def main() -> None:
    city = (sys.argv[1] if len(sys.argv) > 1 else "karnal").lower()
    out = ROOT / "outputs" / city
    cx = sqlite3.connect(DB)

    export(cx, """
        SELECT v.licence_no, v.issue_date, v.purpose, v.area_acre, v.sector,
               v.dev_plan, v.developer_raw, v.developer_group, v.tier, v.score,
               v.locality_tier, v.valid_upto_raw,
               round(v.centroid_lat, 6) AS lat, round(v.centroid_lng, 6) AS lng,
               CASE WHEN v.centroid_lat IS NOT NULL THEN
                 'https://maps.google.com/?q=' || round(v.centroid_lat,6) || ',' ||
                 round(v.centroid_lng,6) END AS map_link
        FROM v_ripe_parcels v
        WHERE v.dev_plan IN (SELECT DISTINCT dev_plan FROM licence_raw
                             WHERE district = ?)""",
        out / "ripe_parcels.csv", (city.title(),))

    district = city.title()
    eids = city_entity_ids(cx, district)
    export(cx, f"""
        SELECT v.* FROM v_call_list v JOIN entity e ON e.canonical_name = v.canonical_name
        WHERE e.entity_id IN ({','.join('?' * len(eids))})""",
        out / "call_list.csv", tuple(eids))

    export(cx, "SELECT * FROM v_hospitality_leads WHERE district=?",
           out / "hospitality_leads.csv", (district,))

    export(cx, """
        SELECT applicant_raw, purpose, area_acre, dev_plan, sector, status,
               status_date, detail
        FROM licence_application_raw WHERE district=?
        ORDER BY status_date DESC""", out / "applications_intent_signals.csv",
        (district,))

    export(cx, """
        SELECT g.name, g.rera_cert_no, a.category, a.expiry_date, g.relationship
        FROM gatekeeper g LEFT JOIN agent_raw a ON a.cert_no = g.rera_cert_no
        WHERE g.city=?""", out / "gatekeepers.csv", (district,))

    export(cx, """
        SELECT * FROM v_target_parcels WHERE dev_plan IN
          (SELECT DISTINCT dev_plan FROM licence_raw WHERE district=?)""",
        out / "target_parcels_new_developers.csv", (district,))

    try:
        export(cx, """
            SELECT file_no, receipt_date, purpose, area_acre, dev_plan, sector,
                   developer_raw
            FROM licence_pending_raw
            WHERE district=? AND scraped_at=(SELECT max(scraped_at)
                                             FROM licence_pending_raw)
              AND (purpose LIKE '%RESIDENTIAL%' OR purpose LIKE '%DEEN DAYAL%'
                   OR purpose LIKE '%DDJAY%' OR purpose LIKE '%AFFORDABLE%'
                   OR purpose LIKE '%NILP%' OR purpose LIKE '%TOWNSHIP%')
            ORDER BY substr(receipt_date,7,4) DESC, substr(receipt_date,4,2) DESC""",
            out / "pending_applications.csv", (city,))
    except sqlite3.OperationalError:
        print("pending_applications: licence_pending_raw not loaded yet, skipped")

    n = cx.execute("SELECT count(*) FROM parcel WHERE centroid_lat IS NOT NULL").fetchone()[0]
    print(f"(parcels geocoded: {n})")
    cx.close()


if __name__ == "__main__":
    main()
