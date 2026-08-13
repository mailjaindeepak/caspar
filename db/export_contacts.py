"""Export per-city promoter contact sheets from parsed RERA REP-I data.

Writes outputs/<city>/promoter_contacts.csv: one row per developer entity in
that city with all emails/phones from their RERA filings, plus tier and notes.

Usage: python db/export_contacts.py
"""
import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "db" / "caspar.db"
CITIES = ["karnal", "panipat", "sonipat", "rohtak", "hisar", "ambala", "kurukshetra"]


def main() -> None:
    cx = sqlite3.connect(DB)
    for city in CITIES:
        rows = cx.execute("""
            SELECT coalesce(e.canonical_name, r.promoter_raw) AS developer,
                   coalesce(e.tier,'') AS tier,
                   group_concat(DISTINCT r.promoter_raw) AS rera_names,
                   count(DISTINCT r.rera_reg_no) AS n_projects,
                   group_concat(DISTINCT r.promoter_email) AS emails,
                   group_concat(DISTINCT r.promoter_phone) AS phones,
                   group_concat(DISTINCT r.licence_no_cited) AS licences_cited,
                   coalesce(e.hq_city,'') AS hq,
                   coalesce(e.is_new,'') AS is_new
            FROM rera_raw r
            LEFT JOIN (SELECT alias_norm, min(entity_id) AS eid FROM entity_alias
                       GROUP BY alias_norm) am
              ON am.alias_norm = (SELECT alias_norm FROM entity_alias
                                  WHERE alias_name = r.promoter_raw LIMIT 1)
            LEFT JOIN entity e ON e.entity_id = am.eid
            WHERE upper(r.district) = ?
              AND r.promoter_email IS NOT NULL
            GROUP BY developer ORDER BY n_projects DESC""",
            (city.upper(),)).fetchall()
        out = ROOT / "outputs" / city / "promoter_contacts.csv"
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["developer", "tier", "rera_names", "n_projects", "emails",
                        "phones", "licences_cited", "hq", "is_new"])
            for r in rows:
                # tidy the concatenated email/phone strings
                emails = "; ".join(sorted({x.strip() for x in (r[4] or "").replace(",", ";").split(";")
                                           if x.strip() and x.strip() != "(none-found)"}))
                phones = "; ".join(sorted({x.strip() for x in (r[5] or "").replace(",", ";").split(";")
                                           if x.strip()}))
                w.writerow([r[0], r[1], r[2], r[3], emails, phones, r[6], r[7], r[8]])
        print(f"{city}: {len(rows)} developers -> {out}")
    cx.close()


if __name__ == "__main__":
    main()
