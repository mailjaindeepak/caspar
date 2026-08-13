"""Import leads from outputs/<city>/ into db/leads.db for released cities.

Idempotent: leads are keyed by (city, source_key); re-running only inserts
rows not seen before, tagged with today's batch date. Existing leads (and the
team's statuses/notes on them) are never touched.

Usage:
    python app/sync_leads.py              # all released cities
    python app/sync_leads.py karnal       # one city (must exist in outputs/)
"""
import csv
import json
import re
import sqlite3
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUTS = ROOT / "outputs"
LEADS_DB = ROOT / "db" / "leads.db"
SCHEMA = ROOT / "app" / "leads_schema.sql"

# call_list.csv is currently exported without a city filter (same file in every
# city folder) — only Karnal's is genuine. Drop this once export is fixed.
CALL_LIST_CITIES = {"karnal"}

_CORP = re.compile(r"\b(PVT|PRIVATE|LTD|LIMITED|LLP|CO|COMPANY|BUILDERS?|"
                   r"DEVELOPERS?|INFRA(STRUCTURE)?|REALTY|REALTORS?|GROUP)\b")


def connect():
    cx = sqlite3.connect(LEADS_DB)
    cx.row_factory = sqlite3.Row
    cx.executescript(SCHEMA.read_text(encoding="utf-8"))
    for d in sorted(p.name for p in OUTPUTS.iterdir() if p.is_dir()):
        cx.execute("INSERT OR IGNORE INTO cities(city) VALUES (?)", (d,))
    cx.commit()
    return cx


def norm_name(s):
    s = re.sub(r"[^A-Z0-9 ]", " ", (s or "").upper())
    s = _CORP.sub(" ", s)
    return " ".join(s.split())


def read_csv(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_contacts(city_dir):
    """developer -> (emails, phones) from promoter_contacts.csv, normalized."""
    book = {}
    for row in read_csv(city_dir / "promoter_contacts.csv"):
        key = norm_name(row.get("developer"))
        if key:
            book[key] = (row.get("emails", ""), row.get("phones", ""))
    return book


def find_contacts(book, *names):
    for n in names:
        key = norm_name(n)
        if key and key in book:
            return book[key]
    # fall back to token-subset match (SPV vs group spelling variants)
    for n in names:
        toks = set(norm_name(n).split())
        if not toks:
            continue
        for key, val in book.items():
            ktoks = set(key.split())
            if toks <= ktoks or ktoks <= toks:
                return val
    return "", ""


def with_map_link(r):
    """Ensure the row dict has a map_link built from whatever coords it carries."""
    if not r.get("map_link"):
        for lat_k, lng_k in (("lat", "lng"), ("centroid_lat", "centroid_lng")):
            lat, lng = r.get(lat_k), r.get(lng_k)
            if lat and lng:
                r["map_link"] = f"https://maps.google.com/?q={float(lat):.6f},{float(lng):.6f}"
                break
    return r


def lead_rows_for_city(city):
    d = OUTPUTS / city
    book = load_contacts(d)
    rows = []

    # Target parcels (new/non-native developers) and ripe parcels overlap heavily
    # and often fully — both become one team-facing kind, 'parcel'. Targets are
    # imported first so their need_score priority wins on shared licence keys.
    for r in read_csv(d / "target_parcels_new_developers.csv"):
        dev = r.get("developer_group") or r.get("developer_raw") or "Unknown developer"
        emails, phones = find_contacts(book, r.get("developer_group"), r.get("developer_raw"))
        rows.append(dict(
            kind="parcel", source_key=r["licence_no"], title=dev,
            subtitle=f"{r.get('purpose','')} · {r.get('area_acre','?')} ac · "
                     f"Sector {r.get('sector') or '—'} · licence {r['licence_no']} "
                     f"({r.get('issue_date','')})",
            priority=float(r["need_score"]) if r.get("need_score") else None,
            emails=emails, phones=phones, details=with_map_link(r)))

    for r in read_csv(d / "ripe_parcels.csv"):
        dev = r.get("developer_group") or r.get("developer_raw") or "Unknown developer"
        emails, phones = find_contacts(book, r.get("developer_group"), r.get("developer_raw"))
        rows.append(dict(
            kind="parcel", source_key=r["licence_no"], title=dev,
            subtitle=f"{r.get('purpose','')} · {r.get('area_acre','?')} ac · "
                     f"Sector {r.get('sector') or '—'} · licence {r['licence_no']} "
                     f"({r.get('issue_date','')})",
            priority=float(r["score"]) / 10 if r.get("score") else None,
            emails=emails, phones=phones, details=with_map_link(r)))

    for r in read_csv(d / "hospitality_leads.csv"):
        rows.append(dict(
            kind="hospitality", source_key=r["clu_file_no"],
            title=r.get("applicant") or "Unknown applicant",
            subtitle=f"{r.get('activity','')} · {r.get('area_acre','?')} ac · "
                     f"{r.get('village','')} ({r.get('sanction_date','')})",
            priority=None, emails="", phones="", details=r))

    if city in CALL_LIST_CITIES:
        for r in read_csv(d / "call_list.csv"):
            name = r.get("canonical_name") or "Unknown"
            rows.append(dict(
                kind="developer", source_key=f"dev:{norm_name(name)}", title=name,
                subtitle=f"Tier {r.get('tier','?')} developer · score {r.get('score','?')}",
                priority=float(r["score"]) / 10 if r.get("score") else None,
                emails=r.get("emails", ""), phones=r.get("phones", ""), details=r))
    return rows


def sync_city(cx, city, batch_tag):
    added = 0
    for lead in lead_rows_for_city(city):
        cur = cx.execute(
            """INSERT OR IGNORE INTO leads
               (city, kind, source_key, title, subtitle, priority,
                contact_emails, contact_phones, details_json, batch_tag)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (city, lead["kind"], lead["source_key"], lead["title"],
             lead["subtitle"], lead["priority"], lead["emails"], lead["phones"],
             json.dumps(lead["details"], ensure_ascii=False), batch_tag))
        added += cur.rowcount
    cx.commit()
    return added


def main():
    cx = connect()
    if len(sys.argv) > 1:
        cities = [sys.argv[1].lower()]
    else:
        cities = [r["city"] for r in
                  cx.execute("SELECT city FROM cities WHERE released=1 ORDER BY city")]
    if not cities:
        print("No released cities. Release one first (manage.py release <city>).")
        return
    batch = date.today().isoformat()
    for city in cities:
        if not (OUTPUTS / city).is_dir():
            print(f"{city}: no outputs/ directory, skipping")
            continue
        n = sync_city(cx, city, batch)
        total = cx.execute("SELECT count(*) FROM leads WHERE city=?", (city,)).fetchone()[0]
        print(f"{city}: +{n} new leads (total {total})")
    cx.close()


if __name__ == "__main__":
    main()
