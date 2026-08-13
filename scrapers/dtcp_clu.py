"""Scrape DTCP Haryana CLU (Change of Land Use) permissions, year-wise.

Source: https://www.tcpharyana.gov.in/WebAdmin/clu/index?id=<YYYY>
(one server-rendered HTML table per year, statewide).

Usage: python dtcp_clu.py KARNAL [start_year] [end_year]
Writes data/<district>/clu_permissions.csv (all years combined, filtered)
and data/clu_all_<start>_<end>.csv (statewide, for later cities).
"""
import csv
import sys
import time
from datetime import date
from pathlib import Path

import requests
from bs4 import BeautifulSoup

URL = "https://www.tcpharyana.gov.in/WebAdmin/clu/index?id={year}"
ROOT = Path(__file__).resolve().parent.parent


def scrape_year(session: requests.Session, year: int) -> list[dict]:
    resp = session.get(URL.format(year=year), timeout=120)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")
    rows = []
    for table in soup.find_all("table"):
        trs = table.find_all("tr")
        if not trs:
            continue
        headers = [c.get_text(" ", strip=True) for c in trs[0].find_all(["th", "td"])]
        if not any("Applicant" in h for h in headers):
            continue
        for tr in trs[1:]:
            cells = tr.find_all(["th", "td"])
            if not cells:
                continue
            values = [c.get_text(" ", strip=True) for c in cells]
            row = dict(zip(headers, values))
            row["clu_year"] = year
            rows.append(row)
    return rows


def main() -> None:
    district = (sys.argv[1] if len(sys.argv) > 1 else "KARNAL").upper()
    start = int(sys.argv[2]) if len(sys.argv) > 2 else 2017
    end = int(sys.argv[3]) if len(sys.argv) > 3 else date.today().year

    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

    all_rows: list[dict] = []
    for year in range(start, end + 1):
        try:
            rows = scrape_year(session, year)
        except requests.RequestException as exc:
            print(f"{year}: FAILED ({exc})")
            continue
        all_rows.extend(rows)
        print(f"{year}: {len(rows)} CLU permissions statewide")
        time.sleep(2)

    fieldnames = list({k: None for r in all_rows for k in r})
    out_all = ROOT / "data" / f"clu_all_{start}_{end}.csv"
    out_all.parent.mkdir(parents=True, exist_ok=True)
    with out_all.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(all_rows)

    sub = [r for r in all_rows
           if r.get("District", "").strip().upper() == district]
    out = ROOT / "data" / district.lower() / "clu_permissions.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(sub)

    print(f"statewide {start}-{end}: {len(all_rows)} -> {out_all}")
    print(f"{district}: {len(sub)} -> {out}")


if __name__ == "__main__":
    main()
