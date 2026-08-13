"""Fetch DTCP GIS polygons for every parcel (LC case) and store in caspar.db.

Usage: python scrapers/fetch_polygons.py
"""
import json
import re
import sqlite3
import time
from pathlib import Path

import requests
from pyproj import Transformer

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "db" / "caspar.db"
URL = "https://tcpharyana.gov.in/CS_marking/LicenceGIS/getLCResults"
T = Transformer.from_crs("EPSG:32643", "EPSG:4326", always_xy=True)


def main() -> None:
    cx = sqlite3.connect(DB)
    s = requests.Session()
    s.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    todo = cx.execute("SELECT parcel_id, lc_case_no FROM parcel"
                      " WHERE wkt_utm43n IS NULL").fetchall()
    ok = miss = err = 0
    for pid, lc in todo:
        try:
            r = s.get(URL, params={"LCNo": lc}, timeout=45)
            data = json.loads(r.text) if r.status_code == 200 else []
        except Exception:
            err += 1
            continue
        pts, wkts, aliases = [], [], set()
        for d in data or []:
            w = d.get("WKT") or ""
            if w:
                wkts.append(w)
                for x, y in re.findall(r"(\d+\.\d+)\s+(\d+\.\d+)", w):
                    pts.append((float(x), float(y)))
            if d.get("DeveloperName"):
                aliases.add(d["DeveloperName"].strip())
        if not pts:
            miss += 1
            time.sleep(0.4)
            continue
        cx_pt = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
        lng, lat = T.transform(*cx_pt)
        cx.execute("UPDATE parcel SET wkt_utm43n=?, centroid_lat=?, centroid_lng=?"
                   " WHERE parcel_id=?", (" ;; ".join(wkts)[:200000], lat, lng, pid))
        # GIS DeveloperName can reveal extra aliases (e.g. Grandeur Real Estate)
        for a in aliases:
            cx.execute(
                "INSERT INTO entity_alias (entity_id, alias_name, source,"
                " source_row_key, method, confidence)"
                " SELECT controlling_entity_id, ?, 'gis', ?, 'gis_field', 0.7"
                " FROM parcel WHERE parcel_id=? AND controlling_entity_id IS NOT NULL"
                " AND NOT EXISTS (SELECT 1 FROM entity_alias WHERE alias_name=?)",
                (a, lc, pid, a))
        ok += 1
        if ok % 20 == 0:
            cx.commit()
            print(f"  {ok}/{len(todo)} done")
        time.sleep(0.5)
    cx.commit()
    print(f"polygons: {ok} fetched, {miss} empty, {err} errors of {len(todo)}")
    cx.close()


if __name__ == "__main__":
    main()
