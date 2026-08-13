"""Upgrade licence<->RERA links using licence numbers cited in RERA REP-I forms.

A citation is deterministic: the promoter's own filing names the DTCP licence.
Adds parcel_link rows with method='ah_citation', confidence=1.0 and flags
citation conflicts with existing fuzzy matches.

Usage: python scrapers/apply_licence_citations.py
"""
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "db" / "caspar.db"


def norm_lic(x: str) -> str:
    return re.sub(r"\s+", " ", x.upper().strip())


def main() -> None:
    cx = sqlite3.connect(DB)
    # map normalized licence no -> (lc_case_no, district)
    lic_map = {}
    for lic_no, lc, dist in cx.execute(
            "SELECT licence_no, lc_case_no, district FROM licence_raw"
            " WHERE lc_case_no IS NOT NULL"):
        lic_map[norm_lic(lic_no)] = (lc, dist)
        # register rows often cite a single number out of a range like
        # "296-301 OF 2005"; index each endpoint too
        m = re.match(r"(\d+)-(\d+) OF (\d{4})", norm_lic(lic_no))
        if m:
            a, b, yr = int(m.group(1)), int(m.group(2)), m.group(3)
            for n in range(a, min(b, a + 30) + 1):
                lic_map.setdefault(f"{n} OF {yr}", (lc, dist))

    added = confirmed = conflicts = 0
    rows = cx.execute(
        "SELECT rera_reg_no, district, licence_no_cited FROM rera_raw"
        " WHERE licence_no_cited IS NOT NULL AND licence_no_cited != ''").fetchall()
    for reg_no, district, cited in rows:
        for c in {norm_lic(x) for x in cited.split(";") if x.strip()}:
            hit = lic_map.get(c)
            if not hit:
                continue
            lc, lic_dist = hit
            if lic_dist.upper() != (district or "").upper():
                continue   # a licence from another district with same number
            pid = cx.execute("SELECT parcel_id FROM parcel WHERE lc_case_no=?"
                             " AND city=?", (lc, lic_dist)).fetchone()
            if not pid:
                continue
            existing = cx.execute(
                "SELECT link_id, status FROM parcel_link WHERE parcel_id=?"
                " AND source='rera'", (pid[0],)).fetchall()
            if any(s == "PARCEL-MATCH" or s == "manual-confirmed" for _, s in existing):
                confirmed += 1
            elif existing:
                conflicts += 1
            if not cx.execute("SELECT 1 FROM parcel_link WHERE parcel_id=? AND"
                              " source_row_key=? AND method='ah_citation'",
                              (pid[0], reg_no)).fetchone():
                cx.execute(
                    "INSERT INTO parcel_link (parcel_id, source, source_row_key,"
                    " method, confidence, status) VALUES (?,?,?,?,?,?)",
                    (pid[0], "rera", reg_no, "ah_citation", 1.0, "PARCEL-MATCH"))
                cx.execute("UPDATE parcel SET current_stage='rera_registered'"
                           " WHERE parcel_id=?", (pid[0],))
                added += 1
    cx.commit()
    print(f"citation links added: {added} | corroborated existing: {confirmed} |"
          f" fuzzy rows now superseded/flagged: {conflicts}")
    cx.close()


if __name__ == "__main__":
    main()
