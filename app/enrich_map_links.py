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
LC_URL = "https://tcpharyana.gov.in/CS_marking/LicenceGIS/getLCResults"
T = Transformer.from_crs("EPSG:32643", "EPSG:4326", always_xy=True)


def gmaps(lat, lng):
    return f"https://maps.google.com/?q={lat:.6f},{lng:.6f}"


def wkt_rings_utm(wkt_text):
    """All coordinate rings (list of (x, y) UTM tuples) in a WKT blob."""
    rings = []
    for chunk in (wkt_text or "").split(";;"):
        for ring in re.findall(r"\(([^()]+)\)", chunk):
            pts = re.findall(r"(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)", ring)
            if len(pts) >= 3:
                rings.append([(float(x), float(y)) for x, y in pts])
    return rings


def rings_to_latlng(rings):
    out = []
    for ring in rings:
        pts = []
        for x, y in ring:
            lng, lat = T.transform(x, y)
            pts.append([round(lat, 6), round(lng, 6)])
        out.append(pts)
    return out


def centroid_of(rings):
    pts = [p for ring in rings for p in ring]
    x = sum(p[0] for p in pts) / len(pts)
    y = sum(p[1] for p in pts) / len(pts)
    lng, lat = T.transform(x, y)
    return lat, lng


def parcel_geo(caspar, licence_no):
    """(centroid, rings_latlng) for a licence's parcel from caspar.db."""
    row = caspar.execute(
        """SELECT p.centroid_lat, p.centroid_lng, p.wkt_utm43n
           FROM parcel p JOIN parcel_link pl ON pl.parcel_id = p.parcel_id
           WHERE pl.source='licence' AND pl.source_row_key=?
                 AND p.centroid_lat IS NOT NULL""", (licence_no,)).fetchone()
    if not row:
        return None, None
    rings = wkt_rings_utm(row[2]) if row[2] else []
    return (row[0], row[1]), (rings_to_latlng(rings) or None)


def lc_geo(session, file_no):
    """(centroid, rings_latlng) for a pending-application LC file from the
    licence GIS API. 'LC-1034B' -> case 'LC-1034'; often empty pre-grant."""
    m = re.match(r"(LC-\d+)", (file_no or "").upper())
    if not m:
        return None, None
    try:
        r = session.get(LC_URL, params={"LCNo": m.group(1)}, timeout=45)
        data = json.loads(r.text) if r.status_code == 200 else []
    except Exception:
        return None, None
    rings = []
    for d in data or []:
        rings.extend(wkt_rings_utm(d.get("WKT")))
    if not rings:
        return None, None
    return centroid_of(rings), rings_to_latlng(rings)


def clu_geo(session, clu_file_no):
    """(centroid, rings_latlng) from the DTCP CLU GIS API."""
    try:
        r = session.get(CLU_URL, params={"CluNo": clu_file_no}, timeout=45)
        data = json.loads(r.text) if r.status_code == 200 else []
    except Exception:
        return None, None
    rings = []
    for d in data or []:
        rings.extend(wkt_rings_utm(d.get("WKT")))
    if not rings:
        return None, None
    return centroid_of(rings), rings_to_latlng(rings)


def main():
    cx = sqlite3.connect(LEADS_DB)
    cx.row_factory = sqlite3.Row
    caspar = sqlite3.connect(CASPAR_DB)
    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

    done = miss = 0
    for lead in cx.execute("SELECT id, kind, source_key, details_json FROM leads "
                           "WHERE kind IN ('parcel','hospitality','application')").fetchall():
        details = json.loads(lead["details_json"])
        if details.get("map_link") and details.get("polygon_latlng"):
            continue
        coords = rings = None
        if lead["kind"] == "parcel":
            coords, rings = parcel_geo(caspar, lead["source_key"])
        elif lead["kind"] == "hospitality":
            coords, rings = clu_geo(session, lead["source_key"])
            time.sleep(0.5)
        elif lead["kind"] == "application":
            coords, rings = lc_geo(session, details.get("file_no"))
            time.sleep(0.5)
        if coords:
            details["map_link"] = details.get("map_link") or gmaps(*coords)
            if rings:
                details["polygon_latlng"] = rings
            cx.execute("UPDATE leads SET details_json=? WHERE id=?",
                       (json.dumps(details, ensure_ascii=False), lead["id"]))
            done += 1
        else:
            miss += 1
    cx.commit()
    print(f"geo enriched: {done}, without GIS data: {miss}")
    cx.close()
    caspar.close()


if __name__ == "__main__":
    main()
