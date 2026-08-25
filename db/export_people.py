"""Export the person-level decision-maker bank per city (§9).

outputs/<city>/people.csv — one row per PERSON, not per company:
  name · designation · DIN · email · phone · linkedin · verification ·
  last verified · source · developer · tier · what they hold in this city

`promoter_contacts.csv` is the company-level sheet (all emails a developer ever
filed, pooled). This is the attributed one: who they are and how to reach them.

A person is listed under a city if their developer has a licence, a pending
application or a RERA registration there.

Usage: python db/export_people.py [city ...]
"""
import csv
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "db" / "caspar.db"
CITIES = ["karnal", "panipat", "sonipat", "rohtak", "hisar", "ambala", "kurukshetra"]

COLS = ["name", "designation", "din", "email", "phone", "linkedin",
        "verification", "last_verified", "source", "developer", "tier",
        "developer_holdings", "cin"]

# rank so the reachable, senior people sort to the top of the sheet
ORDER = """
 CASE WHEN coalesce(s.email,'')<>'' OR coalesce(s.phone,'')<>'' THEN 0 ELSE 1 END,
 CASE WHEN e.tier IN ('A','A*','A-') THEN 0 WHEN e.tier LIKE 'B%' THEN 1 ELSE 2 END,
 e.canonical_name, s.person_name
"""


def main() -> None:
    cities = [c.lower() for c in sys.argv[1:]] or CITIES
    cx = sqlite3.connect(DB)
    cx.row_factory = sqlite3.Row
    for city in cities:
        rows = cx.execute(f"""
            SELECT s.person_name, s.role, s.din, s.email, s.phone, s.linkedin,
                   coalesce(s.verification_status,'unverified') AS vs,
                   s.verified_at, coalesce(s.source_url, s.source_note) AS src,
                   e.canonical_name, coalesce(e.tier,'') AS tier, e.cin,
                   (SELECT count(*) FROM entity_alias a JOIN licence_raw l
                      ON l.licence_no = a.source_row_key
                    WHERE a.entity_id = e.entity_id AND a.source='licence'
                      AND lower(l.district) = ?) AS n_lic,
                   (SELECT count(*) FROM v_ripe_parcels rp JOIN parcel p
                      ON p.parcel_id = rp.parcel_id
                    WHERE rp.developer_group = e.canonical_name
                      AND lower(p.city) = ?) AS n_ripe
            FROM stakeholder s
            JOIN entity e ON e.entity_id = s.entity_id
            WHERE trim(coalesce(s.person_name,'')) <> ''
              AND EXISTS (SELECT 1 FROM entity_alias a JOIN licence_raw l
                            ON l.licence_no = a.source_row_key
                          WHERE a.entity_id = e.entity_id AND a.source='licence'
                            AND lower(l.district) = ?)
            ORDER BY {ORDER}""", (city, city, city)).fetchall()

        out = ROOT / "outputs" / city / "people.csv"
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=COLS)
            w.writeheader()
            for r in rows:
                holdings = f"{r['n_lic']} licence(s) in {city.title()}"
                if r["n_ripe"]:
                    holdings += f" · {r['n_ripe']} RIPE parcel(s)"
                w.writerow({
                    "name": r["person_name"], "designation": r["role"],
                    "din": r["din"] or "", "email": r["email"] or "",
                    "phone": r["phone"] or "", "linkedin": r["linkedin"] or "",
                    "verification": r["vs"].title(),
                    "last_verified": r["verified_at"] or "",
                    "source": r["src"] or "", "developer": r["canonical_name"],
                    "tier": r["tier"], "developer_holdings": holdings,
                    "cin": r["cin"] or ""})
        reach = sum(1 for r in rows if r["email"] or r["phone"])
        print(f"{city}: {len(rows)} people ({reach} reachable) -> {out}")
    cx.close()


if __name__ == "__main__":
    main()
