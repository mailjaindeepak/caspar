"""Scrape DTCP Haryana CLU (Change of Land Use) permissions, year-wise.

Source: https://www.tcpharyana.gov.in/WebAdmin/clu/index?id=<YYYY>
(one server-rendered HTML table per year, statewide; years go back to ~2000).

Usage:
  python scrapers/dtcp_clu.py                    # weekly: ALL districts, last year + this year
  python scrapers/dtcp_clu.py ALL 1995 2026      # backfill: every year, all districts
  python scrapers/dtcp_clu.py KARNAL 2024 2026   # one district, explicit years

Behaviour:
- Fetches the statewide table for each requested year.
- MERGES into the statewide master data/clu_all.csv — only the years that were
  fetched successfully are replaced; a failed year keeps its existing rows.
- Rewrites data/<district>/clu_permissions.csv for each requested district from
  the merged master, so each per-district file always holds the FULL history
  (db/build_city.py reloads clu_raw from that file).
- Prints per-year statewide counts and per-district new/removed CLU file numbers
  versus the previous file — use that in the weekly report.
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
MASTER = ROOT / "data" / "clu_all.csv"
LEGACY_MASTER = ROOT / "data" / "clu_all_2017_2026.csv"   # pre-merge file, seeds the master once

DISTRICTS = ["KARNAL", "PANIPAT", "SONIPAT", "ROHTAK", "HISAR", "AMBALA", "KURUKSHETRA"]
BASE_FIELDS = ["File No", "Applicant Name", "Location/ Controlled Area", "Purpose",
               "Activity", "Granted Area", "District", "CLU Permission on",
               "CLU Corrigendum on", "clu_year"]


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


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    arg_d = (sys.argv[1] if len(sys.argv) > 1 else "ALL").upper()
    districts = DISTRICTS if arg_d == "ALL" else [d.strip() for d in arg_d.split(",")]
    this_year = date.today().year
    start = int(sys.argv[2]) if len(sys.argv) > 2 else this_year - 1
    end = int(sys.argv[3]) if len(sys.argv) > 3 else this_year

    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

    fetched: dict[int, list[dict]] = {}
    for year in range(start, end + 1):
        try:
            rows = scrape_year(session, year)
        except requests.RequestException as exc:
            print(f"{year}: FAILED ({exc}) — keeping existing rows for this year")
            continue
        fetched[year] = rows
        print(f"{year}: {len(rows)} CLU permissions statewide")
        time.sleep(2)

    # ---- merge into statewide master (replace only the years we fetched) ----
    master_src = MASTER if MASTER.exists() else LEGACY_MASTER
    existing = read_csv(master_src)
    if master_src is LEGACY_MASTER and existing:
        print(f"seeding {MASTER.name} from {LEGACY_MASTER.name} ({len(existing)} rows)")
    kept = [r for r in existing if int(r.get("clu_year", 0) or 0) not in fetched]
    merged = kept + [r for rows in fetched.values() for r in rows]
    merged.sort(key=lambda r: (int(r.get("clu_year", 0) or 0), r.get("File No", "")))
    fieldnames = list(BASE_FIELDS)
    for r in merged:
        for k in r:
            if k not in fieldnames:
                fieldnames.append(k)
    write_csv(MASTER, merged, fieldnames)
    years_present = sorted({int(r.get("clu_year", 0) or 0) for r in merged})
    print(f"statewide master: {len(merged)} rows, years {years_present[0] if years_present else '-'}"
          f"..{years_present[-1] if years_present else '-'} -> {MASTER}")

    # ---- per-district files (full history) + delta vs previous file ----
    for district in districts:
        out = ROOT / "data" / district.lower() / "clu_permissions.csv"
        before = {r.get("File No", "") for r in read_csv(out)}
        sub = [r for r in merged if (r.get("District") or "").strip().upper() == district]
        after = {r.get("File No", "") for r in sub}
        write_csv(out, sub, fieldnames)
        added, removed = sorted(after - before), sorted(before - after)
        print(f"{district}: {len(sub)} rows -> {out.relative_to(ROOT)}  "
              f"(+{len(added)} new file nos, -{len(removed)} gone)")
        for fno in added[:15]:
            r = next(x for x in sub if x.get("File No", "") == fno)
            print(f"    + {fno} | {r.get('clu_year')} | {r.get('Activity','')[:40]} | "
                  f"{r.get('Applicant Name','')[:40]}")
        if len(added) > 15:
            print(f"    … {len(added) - 15} more")


if __name__ == "__main__":
    main()
