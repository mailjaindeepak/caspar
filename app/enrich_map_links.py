"""Fill in map_link for leads that lack one.

- parcel leads: centroid from caspar.db (parcel via licence parcel_link)
- hospitality leads: DTCP CLU GIS API (getCLUResults) -> WKT centroid

Safe to re-run; only touches leads without a map_link. Run after sync_leads.py
(weekly refresh step 4).

Usage: python app/enrich_map_links.py
"""
import json
import re
import sqlite3
import time
from pathlib import Path

import requests
from pyproj import Transformer

ROOT = Path(__file__).resolve().parent.parent
LEADS_DB = ROOT / "db" / "leads.db"
CASPAR_DB = ROOT / "db" / "caspar.db"
CLU_URL = "https://tcpharyana.gov.in/CS_marking/LicenceGIS/getCLUResults"
T = Transformer.from_crs("EPSG:32643", "EPSG:4326", always_xy=True)


def gmaps(lat, lng):
    return f"https://maps.google.com/?q={lat:.6f},{lng:.6f}"


def parcel_centroid(caspar, licence_no):
    row = caspar.execute(
        """SELECT p.centroid_lat, p.centroid_lng
           FROM parcel p JOIN parcel_link pl ON pl.parcel_id = p.parcel_id
           WHERE pl.source='licence' AND pl.source_row_key=?
                 AND p.centroid_lat IS NOT NULL""", (licence_no,)).fetchone()
    return (row[0], row[1]) if row else None


def clu_centroid(session, clu_file_no):
    try:
        r = session.get(CLU_URL, params={"CluNo": clu_file_no}, timeout=45)
        data = json.loads(r.text) if r.status_code == 200 else []
    except Exception:
        return None
    pts = []
    for d in data or []:
        for x, y in re.findall(r"(\d+\.\d+)\s+(\d+\.\d+)", d.get("WKT") or ""):
            pts.append((float(x), float(y)))
    if not pts:
        return None
    lng, lat = T.transform(sum(p[0] for p in pts) / len(pts),
                           sum(p[1] for p in pts) / len(pts))
    return lat, lng


def main():
    cx = sqlite3.connect(LEADS_DB)
    cx.row_factory = sqlite3.Row
    caspar = sqlite3.connect(CASPAR_DB)
    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

    done = miss = 0
    for lead in cx.execute("SELECT id, kind, source_key, details_json FROM leads "
                           "WHERE kind IN ('parcel','hospitality')").fetchall():
        details = json.loads(lead["details_json"])
        if details.get("map_link"):
            continue
        coords = None
        if lead["kind"] == "parcel":
            coords = parcel_centroid(caspar, lead["source_key"])
        elif lead["kind"] == "hospitality":
            coords = clu_centroid(session, lead["source_key"])
            time.sleep(0.5)
        if coords:
            details["map_link"] = gmaps(*coords)
            cx.execute("UPDATE leads SET details_json=? WHERE id=?",
                       (json.dumps(details, ensure_ascii=False), lead["id"]))
            done += 1
        else:
            miss += 1
    cx.commit()
    print(f"map links added: {done}, still without coordinates: {miss}")
    cx.close()
    caspar.close()


if __name__ == "__main__":
    main()
