"""Scrape the DTCP statewide REJECTED/RETURNED/WITHDRAWN/LAPSED licence register.

Source: tcpharyana.gov.in/WebAdmin/License/LicenseRejected — linked from the
public license.htm as "List of Licence Cases: Rejected/Returned/Withdrawn/Lapsed".
This is the dead-application sibling of the granted register (dtcp_licences.py)
and the pending register (dtcp_pending.py).

Why it matters: a parcel whose licence application was rejected/withdrawn is a
parcel whose owner still holds land and still needs a route to development —
`export_outputs.py` surfaces these as a distinct outreach lane.

The cached HTML (data/licence_rejected.html) is what `db/build_city.py` parses
into `licence_application_raw`. Until 7 Sep 2026 that path pointed at a Claude
session scratchpad that no longer existed, which broke every city rebuild; the
register lives in the repo now so a rebuild is reproducible.

Columns: Sr | FileNo | Receipt | Purpose | Area | DevPlan | Sector | Developer |
Remarks(status) | Dated.

Usage:
  python scrapers/dtcp_rejected.py --fetch     # download fresh HTML, then report
  python scrapers/dtcp_rejected.py             # report from the cached copy
"""
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from dtcp_licences import CITY_TOWNS

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "licence_rejected.html"
URL = "https://tcpharyana.gov.in/WebAdmin/License/LicenseRejected"


def parse_register(html: str) -> list[list[str]]:
    """Return the register's data rows as 10-cell lists (header rows dropped)."""
    soup = BeautifulSoup(html, "lxml")
    rows = []
    for table in soup.find_all("table"):
        trs = table.find_all("tr")
        if len(trs) < 5:
            continue
        for tr in trs:
            c = [td.get_text(" ", strip=True) for td in tr.find_all(["th", "td"])]
            if len(c) < 10:
                continue
            if not c[1].upper().startswith("LC"):
                continue  # header / spacer rows
            rows.append(c)
    return rows


def city_of(dev_plan: str):
    up = (dev_plan or "").upper()
    for city, towns in CITY_TOWNS.items():
        if any(t in up for t in towns):
            return city
    return None


def fetch() -> str:
    s = requests.Session()
    s.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    resp = s.get(URL, timeout=300)
    if resp.status_code != 200 or "LC-" not in resp.text:
        raise SystemExit(f"rejected-register fetch failed: HTTP {resp.status_code} "
                         f"({len(resp.text)} bytes) — check the endpoint")
    return resp.text


def main() -> None:
    if "--fetch" in sys.argv[1:]:
        html = fetch()
        # Don't clobber a good cache with a truncated fetch — build_city.py reloads
        # licence_application_raw from whatever this file holds.
        old = len(parse_register(CACHE.read_text(encoding="utf-8"))) if CACHE.exists() else 0
        new = len(parse_register(html))
        if old and new < old * 0.8:
            raise SystemExit(f"rejected register collapsed: {new} rows vs {old} cached "
                             f"— refusing to overwrite; check the portal by hand")
        CACHE.write_text(html, encoding="utf-8")
        print(f"fetched rejected register -> {CACHE} ({len(html)} bytes)")

    rows = parse_register(CACHE.read_text(encoding="utf-8"))
    print(f"rejected register: {len(rows)} dead applications statewide")

    counts = {}
    for c in rows:
        city = city_of(c[5])
        if city:
            counts[city] = counts.get(city, 0) + 1
    for city in CITY_TOWNS:
        print(f"  {city}: {counts.get(city, 0)}")


if __name__ == "__main__":
    main()
