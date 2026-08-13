"""Parse the DTCP Haryana statewide licence register into per-city CSVs.

The register (tcpharyana.gov.in/webadmin/license/licensedetails) is one big
server-rendered table that uses rowspans heavily (an LC case spans many licence
rows). This parser expands rowspans into a flat grid.

Usage:
  python dtcp_licences.py --fetch            # download fresh register HTML
  python dtcp_licences.py CITY [CITY ...]    # parse + write data/<city>/dtcp_licences.csv
"""
import csv
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "licence_register.html"
URL = "https://tcpharyana.gov.in/webadmin/license/licensedetails"

# Dev-plan town -> city bucket (uppercased substring match on the DevPlan cell).
# A "city" for us = its district's set of DTCP development plans.
CITY_TOWNS = {
    "karnal": ["KARNAL", "NILOKHERI", "TARAORI", "GHARAUNDA", "ASSANDH", "INDRI"],
    "panipat": ["PANIPAT", "SAMALKHA", "MADLAUDA", "BAPOLI", "ISRANA"],
    "sonipat": ["SONIPAT", "SONEPAT", "KUNDLI", "RAI ", "GANNAUR", "GOHANA",
                "KHARKHODA", "KHARKHAUDA", "BARHI", "MURTHAL"],
    "rohtak": ["ROHTAK", "MEHAM", "KALANAUR", "SAMPLA"],
    "hisar": ["HISAR", "HISSAR", "HANSI", "BARWALA(HISAR)", "NARNAUND",
              "ADAMPUR", "UKLANA"],
    "ambala": ["AMBALA", "NARAINGARH", "BARARA", "MULANA", "SHAHZADPUR"],
    "kurukshetra": ["KURUKSHETRA", "THANESAR", "PEHOWA", "SHAHBAD", "LADWA",
                    "ISMAILABAD", "BABAIN"],
}

HEADERS = ["CaseNo", "Colony", "BR3", "BR7", "LC9", "FileID", "LicenseNo",
           "IssueDate", "Purpose", "Area_acre", "DevPlanRaw", "ValidUpto",
           "Sector", "Developer", "LandSchedule1", "LandSchedule2"]


def expand_table(table) -> list[list[str]]:
    """Expand a rowspan/colspan table into a rectangular grid of cell text."""
    grid: list[list[str | None]] = []
    pending: dict[int, tuple[int, str]] = {}   # col -> (rows_left, text)
    for tr in table.find_all("tr"):
        cells = tr.find_all(["td", "th"])
        if not cells:
            continue
        row: list[str | None] = []
        col = 0
        ci = 0
        while ci < len(cells) or col in pending:
            if col in pending:
                left, text = pending[col]
                row.append(text)
                left -= 1
                if left:
                    pending[col] = (left, text)
                else:
                    del pending[col]
                col += 1
                continue
            if ci >= len(cells):
                break
            c = cells[ci]
            ci += 1
            text = c.get_text(" ", strip=True)
            rs = int(c.get("rowspan", 1) or 1)
            cs = int(c.get("colspan", 1) or 1)
            for k in range(cs):
                row.append(text)
                if rs > 1:
                    pending[col + k] = (rs - 1, text)
            col += cs
        grid.append(row)  # type: ignore[arg-type]
    return grid  # first row(s) are headers


def parse_register(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    best = max(soup.find_all("table"), key=lambda t: len(t.find_all("tr")))
    grid = expand_table(best)
    rows = []
    for r in grid:
        if len(r) < 14 or not r[6] or "OF" not in str(r[6]).upper():
            continue  # header/blank/malformed
        d = dict(zip(HEADERS, [str(x or "").strip() for x in r]))
        d["CaseNo"] = re.sub(r"\s*Map View\s*", "", d["CaseNo"]).strip()
        rows.append(d)
    return rows


def main() -> None:
    args = [a for a in sys.argv[1:]]
    if "--fetch" in args:
        args.remove("--fetch")
        s = requests.Session()
        s.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(s.get(URL, timeout=300).text, encoding="utf-8")
        print(f"fetched register -> {CACHE}")
    html = CACHE.read_text(encoding="utf-8")
    rows = parse_register(html)
    print(f"register: {len(rows)} licence rows statewide")

    for city in [a.lower() for a in args] or list(CITY_TOWNS):
        towns = CITY_TOWNS[city]
        sub = [r for r in rows
               if any(t in r["DevPlanRaw"].upper() for t in towns)]
        out = ROOT / "data" / city / "dtcp_licences.csv"
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=HEADERS)
            w.writeheader()
            w.writerows(sub)
        print(f"{city}: {len(sub)} licences -> {out}")


if __name__ == "__main__":
    main()
