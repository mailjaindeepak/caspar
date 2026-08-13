"""Export the outreach-ready outputs from caspar.db to outputs/<city>/.

Usage: python db/export_outputs.py [karnal]
"""
import csv
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "db" / "caspar.db"


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
    export(cx, "SELECT * FROM v_call_list", out / "call_list.csv")

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

    n = cx.execute("SELECT count(*) FROM parcel WHERE centroid_lat IS NOT NULL").fetchone()[0]
    print(f"(parcels geocoded: {n})")
    cx.close()


if __name__ == "__main__":
    main()
