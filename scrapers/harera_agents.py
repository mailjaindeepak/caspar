"""Scrape HARERA registered real-estate agents (gatekeeper seed list).

Usage: python harera_agents.py [DISTRICT ...]
Writes data/harera_agents_all.csv and per-district data/<district>/harera_agents.csv
"""
import csv
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

URL = "https://haryanarera.gov.in/admincontrol/registered_agents/{bench}"
ROOT = Path(__file__).resolve().parent.parent


def scrape() -> list[dict]:
    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    rows: list[dict] = []
    seen: set[str] = set()
    for bench in ("1", "2"):
        resp = session.get(URL.format(bench=bench), timeout=120)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        for table in soup.find_all("table"):
            trs = table.find_all("tr")
            if not trs:
                continue
            headers = [c.get_text(strip=True) for c in trs[0].find_all(["th", "td"])]
            if not any("Agent Name" in h for h in headers):
                continue
            for tr in trs[1:]:
                cells = tr.find_all(["th", "td"])
                if not cells:
                    continue
                values = [c.get_text(" ", strip=True) for c in cells]
                links = [a.get("href", "") for a in tr.find_all("a")]
                row = dict(zip(headers, values))
                key = row.get("Registration Certificate No.", "") + row.get("Agent Name", "")
                if key in seen:
                    continue
                seen.add(key)
                row["bench_path"] = bench
                row["cert_link"] = " | ".join(l for l in links if l and l != "#")
                rows.append(row)
    return rows


def main() -> None:
    districts = [d.upper() for d in sys.argv[1:]]
    rows = scrape()
    fieldnames = list({k: None for r in rows for k in r})

    out_all = ROOT / "data" / "harera_agents_all.csv"
    out_all.parent.mkdir(parents=True, exist_ok=True)
    with out_all.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"ALL: {len(rows)} agents -> {out_all}")

    for district in districts:
        sub = [r for r in rows if r.get("District", "").strip().upper() == district]
        out = ROOT / "data" / district.lower() / "harera_agents.csv"
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(sub)
        print(f"{district}: {len(sub)} agents -> {out}")


if __name__ == "__main__":
    main()
