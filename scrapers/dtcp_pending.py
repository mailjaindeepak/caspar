"""Scrape the DTCP statewide PENDING licence-application register.

Source: tcpharyana.gov.in/WebAdmin/License/LicensePending — the pending-side
sibling of the granted register. NOTE: this endpoint is deliberately unlinked
from the public site (license.htm points its entry at a 404 page), so it may
disappear; we log row counts and archive each fetch. Use GET only — HEAD
requests 302 to the login page.

Fields: FileNo (LC-xxxx, joins to granted register), ReceiptDate, Purpose,
Area_acre, DevPlanRaw, Sector, Developer.

Usage:
  python scrapers/dtcp_pending.py --fetch          # download fresh HTML
  python scrapers/dtcp_pending.py [CITY ...]       # parse -> data/<city>/pending_applications.csv
                                                    # + load caspar.db licence_pending_raw snapshot
"""
import csv
import sqlite3
import sys
from datetime import date
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from dtcp_licences import CITY_TOWNS, expand_table

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "licence_pending.html"
DB = ROOT / "db" / "caspar.db"
URL = "https://tcpharyana.gov.in/WebAdmin/License/LicensePending"

HEADERS = ["FileNo", "ReceiptDate", "Purpose", "Area_acre", "DevPlanRaw",
           "Sector", "Developer"]

DDL = """
CREATE TABLE IF NOT EXISTS licence_pending_raw (
    file_no       TEXT,
    receipt_date  TEXT,
    purpose       TEXT,
    area_acre     REAL,
    dev_plan      TEXT,
    sector        TEXT,
    developer_raw TEXT,
    district      TEXT,
    scraped_at    TEXT,
    PRIMARY KEY (file_no, scraped_at)
);
"""


def parse_register(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    best = max(soup.find_all("table"), key=lambda t: len(t.find_all("tr")))
    grid = expand_table(best)
    rows = []
    for r in grid:
        # Sr | FileNo | Receipt | Purpose | Area | DevPlan | Sector | Developer | Remarks
        if len(r) < 8:
            continue
        cells = [str(x or "").strip() for x in r]
        file_no = cells[1]
        if not file_no or not file_no.upper().startswith("LC"):
            continue  # header / blank-file rows
        rows.append(dict(zip(HEADERS, cells[1:8])))
    return rows


def city_of(dev_plan: str):
    up = (dev_plan or "").upper()
    for city, towns in CITY_TOWNS.items():
        if any(t in up for t in towns):
            return city
    return None


def main() -> None:
    args = [a for a in sys.argv[1:]]
    if "--fetch" in args:
        args.remove("--fetch")
        s = requests.Session()
        s.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        resp = s.get(URL, timeout=300)
        if resp.status_code != 200 or "LC" not in resp.text:
            raise SystemExit(f"register fetch failed: HTTP {resp.status_code} "
                             f"({len(resp.text)} bytes) — endpoint may have been taken down")
        CACHE.write_text(resp.text, encoding="utf-8")
        print(f"fetched pending register -> {CACHE} ({len(resp.text)} bytes)")

    rows = parse_register(CACHE.read_text(encoding="utf-8"))
    if len(rows) < 100:
        print(f"WARNING: only {len(rows)} rows parsed — sanity-check the register")
    print(f"pending register: {len(rows)} applications statewide")

    # snapshot into caspar.db (append-with-date, like other raw tables)
    cx = sqlite3.connect(DB)
    cx.executescript(DDL)
    today = date.today().isoformat()
    cx.execute("DELETE FROM licence_pending_raw WHERE scraped_at=?", (today,))
    for r in rows:
        try:
            area = float(str(r["Area_acre"]).replace(",", ""))
        except ValueError:
            area = None
        cx.execute("INSERT OR IGNORE INTO licence_pending_raw VALUES (?,?,?,?,?,?,?,?,?)",
                   (r["FileNo"], r["ReceiptDate"], r["Purpose"], area,
                    r["DevPlanRaw"], r["Sector"], r["Developer"],
                    city_of(r["DevPlanRaw"]), today))
    cx.commit()

    for city in [a.lower() for a in args] or list(CITY_TOWNS):
        sub = [r for r in rows if city_of(r["DevPlanRaw"]) == city]
        out = ROOT / "data" / city / "pending_applications.csv"
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=HEADERS)
            w.writeheader()
            w.writerows(sub)
        print(f"{city}: {len(sub)} pending applications -> {out}")
    cx.close()


if __name__ == "__main__":
    main()
