"""Cross-reference DTCP licences vs HARERA registrations for a city.

Flags recent licences (default: issued 2020+) whose developer has no
matching RERA registration in the district — the prime outreach window
between licence grant and RERA launch.

Usage: python licence_rera_delta.py karnal [min_year]
"""
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cluster_developers import norm  # reuse the same name normalizer

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    city = (sys.argv[1] if len(sys.argv) > 1 else "karnal").lower()
    min_year = int(sys.argv[2]) if len(sys.argv) > 2 else 2020
    ddir = ROOT / "data" / city

    rera = list(csv.DictReader((ddir / "harera_projects.csv").open(encoding="utf-8-sig")))
    rera_keys = {norm(r.get("Promoter Name", "")) for r in rera}

    lic = list(csv.DictReader((ddir / "dtcp_licences.csv").open(encoding="utf-8-sig")))
    out_rows = []
    for row in lic:
        m = re.search(r"(\d{4})$", row.get("IssueDate", "").strip())
        year = int(m.group(1)) if m else 0
        if year < min_year:
            continue
        dev_key = norm(row.get("Developer", ""))
        # fuzzy containment either way, since DTCP and RERA spell names differently
        matched = any(
            dev_key and rk and (dev_key in rk or rk in dev_key)
            for rk in rera_keys
        )
        if not matched:
            out_rows.append({**row, "issue_year": year})

    out = ddir / "licensed_not_registered.csv"
    if out_rows:
        with out.open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
            w.writeheader()
            w.writerows(out_rows)
    print(f"{city}: {len(out_rows)} licences ({min_year}+) with no RERA match -> {out}")
    for r in out_rows:
        print(f"  {r['issue_year']}  {r['Purpose']:10} {r['Area_acre']:>8} ac  "
              f"{r['DevPlan']:22} Sec {r['Sector']:8} {r['Developer'][:45]}")


if __name__ == "__main__":
    main()
