"""Push person-level decision-makers from caspar.db onto the team's leads (§9).

`stakeholder` holds the person-level bank (name, designation, DIN, email, phone,
LinkedIn, verification status, source). Nothing in the lead app read it, so the
team only ever saw an undifferentiated pool of company emails. This copies the
people onto each lead's details_json.contact_research.people — the shape the
lead page's "Decision makers" table renders.

Matching, strongest first:
  parcel/application -> licence no. cited in entity_alias (deterministic)
  developer          -> lead title == entity.canonical_name (deterministic)
  any                -> normalised developer/applicant name -> alias_norm (fuzzy tier)

Hand-researched people are never overwritten: a person already on the lead wins
over the same name arriving from caspar.db, and the lead's own
contact_research fields (notes, sources, cin) are preserved when present.

Safe to re-run. Run after sync_leads.py.
Usage: python app/enrich_lead_contacts.py [--dry-run]
"""
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scrapers"))
from cluster_developers import norm  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LEADS_DB = ROOT / "db" / "leads.db"
CASPAR_DB = ROOT / "db" / "caspar.db"

# person fields carried onto the lead, in the order the table renders them
FIELDS = ("name", "role", "din", "email", "phone", "linkedin",
          "verification", "verified_at", "source", "note")


def merge_multi(existing, new_items):
    """Merge ';'-separated pools, deduping. An incoming value may itself be a
    ';'-joined list (a stakeholder row can carry several addresses), so split
    those too — otherwise the pool grows duplicates on every run."""
    parts, seen = [], set()
    for chunk in [existing or ""] + [x or "" for x in new_items]:
        for p in str(chunk).split(";"):
            p = p.strip()
            if p and p.lower() not in seen:
                seen.add(p.lower())
                parts.append(p)
    return "; ".join(parts)


def load_caspar():
    cx = sqlite3.connect(CASPAR_DB)
    cx.row_factory = sqlite3.Row
    by_licence, by_norm, by_canon = {}, {}, {}
    for r in cx.execute("SELECT entity_id, alias_norm, source, source_row_key "
                        "FROM entity_alias"):
        if r["source"] == "licence" and r["source_row_key"]:
            by_licence[r["source_row_key"].strip().upper()] = r["entity_id"]
        if r["alias_norm"]:
            by_norm.setdefault(r["alias_norm"], r["entity_id"])
    for r in cx.execute("SELECT entity_id, canonical_name, cin FROM entity"):
        by_canon[r["canonical_name"]] = (r["entity_id"], r["cin"])

    people = {}
    for r in cx.execute(
            "SELECT entity_id, person_name, role, din, email, phone, linkedin,"
            " verification_status, verified_at, source_url, source_note"
            " FROM stakeholder ORDER BY"
            # signatories carry personal contacts -> most useful first
            "  CASE WHEN coalesce(email,'')<>'' OR coalesce(phone,'')<>''"
            "       THEN 0 ELSE 1 END, person_name"):
        # some curated rows are placeholders, not people (e.g. entity 7's
        # "Beneficial owner unknown - route via broker"); they carry a contact
        # but no name and must not surface as a decision-maker
        if not (r["person_name"] or "").strip():
            continue
        people.setdefault(r["entity_id"], []).append({
            "name": r["person_name"], "role": r["role"], "din": r["din"],
            "email": r["email"], "phone": r["phone"], "linkedin": r["linkedin"],
            "verification": r["verification_status"] or "unverified",
            "verified_at": r["verified_at"],
            "source": r["source_url"] or r["source_note"],
            "note": None,
        })
    cx.close()
    return by_licence, by_norm, by_canon, people


def resolve(lead, details, by_licence, by_norm, by_canon):
    """(entity_id, cin, how) for a lead, or (None, None, None)."""
    if lead["kind"] == "developer":
        hit = by_canon.get(lead["title"])
        if hit:
            return hit[0], hit[1], "canonical"
    lic = (details.get("licence_no") or "").strip().upper()
    if lic and lic in by_licence:
        return by_licence[lic], None, "licence"
    for key in ("developer_group", "developer_raw", "applicant",
                "canonical_name"):
        v = details.get(key)
        if not v:
            continue
        hit = by_canon.get(v)
        if hit:
            return hit[0], hit[1], "canonical"
        eid = by_norm.get(norm(v))
        if eid:
            return eid, None, f"name:{key}"
    return None, None, None


def main():
    dry = "--dry-run" in sys.argv
    by_licence, by_norm, by_canon, people = load_caspar()

    cx = sqlite3.connect(LEADS_DB)
    cx.row_factory = sqlite3.Row
    uid = cx.execute("SELECT id FROM users WHERE role='admin' ORDER BY id").fetchone()
    uid = uid["id"] if uid else None

    touched = added = unmatched = 0
    by_how = {}
    for lead in cx.execute("SELECT * FROM leads ORDER BY city, kind, id").fetchall():
        details = json.loads(lead["details_json"])
        eid, cin, how = resolve(lead, details, by_licence, by_norm, by_canon)
        if eid is None:
            unmatched += 1
            continue
        incoming = people.get(eid) or []
        if not incoming:
            unmatched += 1
            continue

        research = details.get("contact_research") or {}
        current = list(research.get("people") or [])
        have = {(p.get("name") or "").strip().lower() for p in current}
        fresh = [{k: p.get(k) for k in FIELDS} for p in incoming
                 if (p["name"] or "").strip().lower() not in have]
        if not fresh:
            continue

        research["people"] = current + fresh
        if cin and not research.get("company_cin"):
            research["company_cin"] = cin
        details["contact_research"] = research

        emails = merge_multi(lead["contact_emails"], [p["email"] for p in fresh])
        phones = merge_multi(lead["contact_phones"], [p["phone"] for p in fresh])

        by_how[how] = by_how.get(how, 0) + 1
        touched += 1
        added += len(fresh)
        if dry:
            continue
        cx.execute("UPDATE leads SET contact_emails=?, contact_phones=?, "
                   "details_json=? WHERE id=?",
                   (emails, phones, json.dumps(details, ensure_ascii=False),
                    lead["id"]))
        if uid:
            names = ", ".join(p["name"] for p in fresh[:4])
            more = f" +{len(fresh) - 4} more" if len(fresh) > 4 else ""
            cx.execute(
                "INSERT INTO lead_notes(lead_id, user_id, note) VALUES (?,?,?)",
                (lead["id"], uid,
                 f"Decision makers added from RERA REP-I / registry research "
                 f"({len(fresh)}): {names}{more}"))
    if not dry:
        cx.commit()
    print(f"{'DRY RUN — ' if dry else ''}leads updated: {touched}, "
          f"people added: {added}, leads with no match: {unmatched}")
    print("  matched by:", by_how or "—")
    with_people = sum(
        1 for r in cx.execute("SELECT details_json FROM leads")
        if (json.loads(r["details_json"]).get("contact_research") or {}).get("people"))
    print(f"  leads now carrying named people: {with_people}")
    cx.close()


if __name__ == "__main__":
    main()
