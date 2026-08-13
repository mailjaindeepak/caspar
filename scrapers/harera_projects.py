"""Scrape HARERA (haryanarera.gov.in) public project search by district.

Usage: python harera_projects.py KARNAL [DISTRICT2 ...]
Writes data/<district>/harera_projects.csv
"""
import csv
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

URL = "https://haryanarera.gov.in/assistancecontrol/project_search_public/2"

DISTRICT_CODES = {
    "AMBALA": "58", "BHIWANI": "59", "FARIDABAD": "60", "FATEHABAD": "61",
    "PALWAL": "619", "GURUGRAM": "62", "HISAR": "63", "JHAJJAR": "64",
    "JIND": "65", "KAITHAL": "66", "KARNAL": "67", "KURUKSHETRA": "68",
    "MAHENDRAGARH": "69", "PANCHKULA": "70", "CHARKI DADRI": "701",
    "PANIPAT": "71", "REWARI": "72", "ROHTAK": "73", "SIRSA": "74",
    "SONIPAT": "75", "YAMUNANAGAR": "76", "NUH": "604", "ALL": "999",
}

ROOT = Path(__file__).resolve().parent.parent


URL_TMPL = "https://haryanarera.gov.in/assistancecontrol/project_search_public/{bench}"


def parse_rows(html: str, bench: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    rows = []
    for table in soup.find_all("table"):
        trs = table.find_all("tr")
        if not trs:
            continue
        # NB: the portal marks data cells as <th>, not <td> — treat the first
        # row as the header and every later row as data regardless of cell tag.
        headers = [c.get_text(strip=True) for c in trs[0].find_all(["th", "td"])]
        if not any("Promoter" in h for h in headers):
            continue
        for tr in trs[1:]:
            cells = tr.find_all(["th", "td"])
            if not cells:
                continue
            values = [c.get_text(" ", strip=True) for c in cells]
            links = [a.get("href", "") for a in tr.find_all("a")]
            row = dict(zip(headers, values))
            row["bench_path"] = bench
            row["links"] = " | ".join(l for l in links if l and l != "#")
            rows.append(row)
    return rows


def scrape_district(session: requests.Session, district: str) -> list[dict]:
    code = DISTRICT_CODES[district.upper()]
    all_rows: list[dict] = []
    seen: set[str] = set()
    # The portal exposes two registry variants (/1 and /2); a district's
    # projects may sit in either, so query both and dedupe.
    for bench in ("1", "2"):
        resp = session.post(URL_TMPL.format(bench=bench),
                            data={"district": code, "basic_search": ""}, timeout=120)
        resp.raise_for_status()
        for row in parse_rows(resp.text, bench):
            key = (row.get("Project Registration Number") or
                   row.get("Project Temp-ID") or str(row))
            if key in seen:
                continue
            seen.add(key)
            all_rows.append(row)
        time.sleep(1)
    return all_rows


def main() -> None:
    districts = sys.argv[1:] or ["KARNAL"]
    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    session.get(URL_TMPL.format(bench="1"), timeout=60)  # establish ci_session cookie
    for district in districts:
        rows = scrape_district(session, district)
        out_dir = ROOT / "data" / district.lower()
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / "harera_projects.csv"
        if rows:
            fieldnames = list({k: None for r in rows for k in r})
            with out.open("w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
        print(f"{district}: {len(rows)} projects -> {out}")
        time.sleep(2)


if __name__ == "__main__":
    main()
