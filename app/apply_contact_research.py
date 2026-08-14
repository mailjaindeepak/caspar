"""Apply web-research contact findings to leads.

Input: a JSON file containing an array of finding objects:
  {"lead_id": 17, "found": true, "venue_name": "...", "phones": [...],
   "emails": [...], "people": [{"name","role"}], "company_cin": "...",
   "sources": [...], "confidence": "high|medium|low", "notes": "..."}

For each found entry: fills the lead's contact fields (merging, never
overwriting existing values), stores the full finding under
details_json.contact_research (provenance for DPDP), and logs an activity
note. Skips entries with no sources — unsourced contacts are not applied.

Usage: python app/apply_contact_research.py <findings.json> [--user admin_username]
"""
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEADS_DB = ROOT / "db" / "leads.db"


def merge(existing, new_items):
    parts = [p.strip() for p in (existing or "").split(";") if p.strip()]
    for x in new_items or []:
        x = str(x).strip()
        if x and x not in parts:
            parts.append(x)
    return "; ".join(parts)


def main():
    findings = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    user = sys.argv[3] if len(sys.argv) > 3 and sys.argv[2] == "--user" else "deepak"

    cx = sqlite3.connect(LEADS_DB)
    cx.row_factory = sqlite3.Row
    uid_row = cx.execute("SELECT id FROM users WHERE username=?", (user,)).fetchone()
    uid = uid_row["id"] if uid_row else None

    applied = skipped = 0
    for f in findings:
        if not f.get("found"):
            skipped += 1
            continue
        if not f.get("sources"):
            print(f"lead {f.get('lead_id')}: found but NO SOURCES - not applied")
            skipped += 1
            continue
        lead = cx.execute("SELECT * FROM leads WHERE id=?", (f["lead_id"],)).fetchone()
        if lead is None:
            print(f"lead {f.get('lead_id')}: not in DB, skipped")
            skipped += 1
            continue
        d = json.loads(lead["details_json"])
        d["contact_research"] = {k: f.get(k) for k in
                                 ("venue_name", "people", "company_cin",
                                  "sources", "confidence", "notes")}
        cx.execute("UPDATE leads SET contact_emails=?, contact_phones=?, details_json=? "
                   "WHERE id=?",
                   (merge(lead["contact_emails"], f.get("emails")),
                    merge(lead["contact_phones"], f.get("phones")),
                    json.dumps(d, ensure_ascii=False), lead["id"]))
        if uid:
            bits = []
            if f.get("venue_name"):
                bits.append(f"venue: {f['venue_name']}")
            if f.get("people"):
                bits.append("people: " + ", ".join(
                    f"{p.get('name')} ({p.get('role', '?')})" for p in f["people"]))
            bits.append(f"confidence: {f.get('confidence', '?')}")
            bits.append("sources: " + "; ".join(f["sources"][:3]))
            cx.execute("INSERT INTO lead_notes(lead_id, user_id, note) VALUES (?,?,?)",
                       (lead["id"], uid, "Contact research — " + " · ".join(bits)))
        applied += 1
    cx.commit()
    print(f"applied {applied}, skipped {skipped}")


if __name__ == "__main__":
    main()
