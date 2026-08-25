"""Parse HARERA project_preview_open pages (FORM REP-I) for promoter contacts.

For every rera_raw row with a preview link: fetch the form, extract
company contacts (email/phone/website/CIN) + named people (MD/CEO/directors)
with their emails/mobiles. Updates rera_raw, entity.cin, and inserts
stakeholder rows linked via the promoter's entity.

Usage: python scrapers/parse_rera_preview.py [limit]
"""
import re
import sqlite3
import sys
import time
from datetime import date
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cluster_developers import norm

DB = ROOT / "db" / "caspar.db"
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE_RE = re.compile(r"(?<!\d)(?:\+91[\s-]?)?([6-9]\d{9})(?!\d)")
CIN_RE = re.compile(r"\b([ULF]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6})\b")
LIC_RE = re.compile(r"\b(\d{1,4}\s*OF\s*(?:19|20)\d{2})\b", re.I)

PERSON_LABELS = ("name of the director", "name of director", "managing director",
                 "name of partner", "name of the partner", "name:", "name of ceo")

# REP-I writes a person in three different shapes, and matching only on the
# label caught none of them (480 forms parsed -> 0 people):
#   1. empty label, value "Name : SHASHI CHAWLA"        -> director block
#   2. label "partner 1", value "Name : NARESH MALIK"   -> partnership firm
#   3. label "Name", value "VIKAS MEHLA", followed by
#      Phone(Mobile)/Email rows                         -> authorised signatory
CONTACT_WINDOW = 6        # rows after a name that may carry that person's contact
NAME_VALUE_RE = re.compile(r"^name\s*[:\-]\s*(.+)$", re.I)
ROLE_LABEL_RE = re.compile(r"^\s*(partner|director|promoter|karta|member)s?\s*\.?\s*\d*\s*$", re.I)
# a bare "name" label means a person; "name of the project/company/firm" does not
BARE_NAME_RE = re.compile(r"^\s*\d*\.?\s*name\s*$", re.I)
NOT_A_PERSON_RE = re.compile(
    r"\b(PVT|PRIVATE|LTD|LIMITED|LLP|INC|CORP|COMPANY|BUILDERS?|DEVELOPERS?|"
    r"INFRA\w*|REALTY|REALTORS?|ESTATES?|TOWNSHIPS?|PROJECTS?|ASSOCIATES?|"
    r"ENTERPRISES?|COLONISERS?|BUILDWELL|BUILDCON|BUILDTECH|GROUP|"
    r"RESIDENCY|CITY|GREENS?|BANK)\b", re.I)


HONORIFIC_RE = re.compile(
    r"^(m/s|mr|mrs|ms|miss|shri|shree|smt|sh|dr|prof|col|capt|maj|lt)\.?\s+", re.I)


def _clean_person_name(v: str) -> str | None:
    """Return a plausible personal name, else None."""
    v = re.sub(r"\s+", " ", (v or "").strip().strip(":-").strip())
    # strip honorifics, else "Mrs Divya Ansal" and "Divya Ansal" become two people
    while True:
        stripped = HONORIFIC_RE.sub("", v)
        if stripped == v:
            break
        v = stripped.strip()
    if not (3 < len(v) < 60) or "@" in v or any(ch.isdigit() for ch in v):
        return None
    if NOT_A_PERSON_RE.search(v):
        return None            # a firm, not a human
    return v.title()


def parse_form(html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    out = {"emails": set(), "phones": set(), "cin": None, "website": None,
           "licences": set(), "people": []}
    text = soup.get_text(" ", strip=True)
    out["emails"] = set(e.lower() for e in EMAIL_RE.findall(text))
    out["phones"] = set(PHONE_RE.findall(text))
    m = CIN_RE.search(text)
    if m:
        out["cin"] = m.group(1)
    out["licences"] = {x.upper().replace("  ", " ") for x in LIC_RE.findall(text)}

    # walk label/value rows; build person blocks.
    # A contact only attaches to a person within CONTACT_WINDOW rows of the
    # name row. Without that bound the PROJECT's own phone/email (which sit ~20
    # rows below the last director block) get attributed to a named individual
    # — a wrong contact is worse than a missing one.
    person = None
    person_row = -99
    for i, tr in enumerate(soup.find_all("tr")):
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
        if len(cells) < 2:
            continue
        label = " ".join(cells[:-1]).lower()
        value = cells[-1].strip()
        if not value:
            continue
        if "website" in label and value.startswith("http"):
            out["website"] = value

        # --- shapes 1 & 2: the name is inside the VALUE as "Name : X" ---
        m_nv = NAME_VALUE_RE.match(value)
        if m_nv:
            nm = _clean_person_name(m_nv.group(1))
            if nm:
                m_role = ROLE_LABEL_RE.match(label)
                role = (m_role.group(1).title() if m_role else "Director/KMP")
                person = {"name": nm, "email": None, "phone": None,
                          "role": f"{role} (RERA REP-I)"}
                person_row = i
                out["people"].append(person)
            continue

        # --- shape 3: bare "Name" label, contact rows follow ---
        if BARE_NAME_RE.match(label) or any(k in label for k in PERSON_LABELS):
            nm = _clean_person_name(value)
            if nm:
                person = {"name": nm, "email": None, "phone": None,
                          "role": "Authorised signatory (RERA REP-I)"}
                person_row = i
                out["people"].append(person)
            continue

        if person is not None and i - person_row > CONTACT_WINDOW:
            person = None          # left the person's block; stop attaching

        if person is not None:
            if "email" in label and EMAIL_RE.search(value):
                person["email"] = EMAIL_RE.search(value).group(0).lower()
            elif "mobile" in label and PHONE_RE.search(value):
                person["phone"] = PHONE_RE.search(value).group(1)
            elif "designation" in label and len(value) < 60:
                person["role"] = value

    # one human can appear twice in a form (e.g. listed as Partner and again in
    # the directors block). Merge on name, keeping any contact we found and
    # preferring the more specific role.
    merged: dict[str, dict] = {}
    for p in out["people"]:
        cur = merged.get(p["name"])
        if cur is None:
            merged[p["name"]] = p
            continue
        cur["email"] = cur["email"] or p["email"]
        cur["phone"] = cur["phone"] or p["phone"]
        if cur["role"].startswith("Director/KMP") and not p["role"].startswith("Director/KMP"):
            cur["role"] = p["role"]
    out["people"] = list(merged.values())
    return out


def main() -> None:
    # --all re-reads every form, not just the ones never parsed. Needed after a
    # parser fix: the incremental default (promoter_email IS NULL) would skip
    # the 469 forms whose contacts were already harvested.
    args = [a for a in sys.argv[1:]]
    reparse_all = "--all" in args
    if reparse_all:
        args.remove("--all")
    limit = int(args[0]) if args else 10**9
    cx = sqlite3.connect(DB)
    s = requests.Session()
    s.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    where = "" if reparse_all else " AND promoter_email IS NULL"
    rows = cx.execute(
        "SELECT rera_reg_no, promoter_raw, links FROM rera_raw"
        f" WHERE links LIKE '%project_preview_open%'{where}"
    ).fetchall()[:limit]
    print(f"to parse: {len(rows)}" + ("  (--all: re-reading every form)" if reparse_all else ""))
    ok = fail = people_added = 0
    for reg_no, promoter, links in rows:
        url = next((u.strip() for u in links.split("|")
                    if "project_preview_open" in u), None)
        if not url:
            continue
        try:
            r = s.get(url, timeout=60)
            d = parse_form(r.text)
        except Exception:
            fail += 1
            time.sleep(1)
            continue
        # On a --all re-read, never overwrite a populated field with an empty
        # one: a form that renders partially would otherwise wipe good data.
        cx.execute(
            "UPDATE rera_raw SET promoter_email=coalesce(nullif(?,''), promoter_email),"
            " promoter_phone=coalesce(nullif(?,''), promoter_phone),"
            " licence_no_cited=coalesce(nullif(?,''), licence_no_cited)"
            " WHERE rera_reg_no=?",
            ("; ".join(sorted(d["emails"])) or "(none-found)",
             "; ".join(sorted(d["phones"])),
             "; ".join(sorted(d["licences"])), reg_no))
        ent = cx.execute("SELECT entity_id FROM entity_alias WHERE alias_norm=? LIMIT 1",
                         (norm(promoter or ""),)).fetchone()
        if ent:
            if d["cin"]:
                cx.execute("UPDATE entity SET cin=coalesce(cin,?) WHERE entity_id=?",
                           (d["cin"], ent[0]))
            for p in d["people"]:
                # A named director with no contact is still §9 data (identity +
                # designation from the promoter's own filing); it is recorded
                # with an explicit verification status rather than dropped.
                if cx.execute("SELECT 1 FROM stakeholder WHERE entity_id=? AND"
                              " person_name=?", (ent[0], p["name"])).fetchone():
                    continue   # never clobber a hand-curated row
                cx.execute(
                    "INSERT INTO stakeholder (entity_id, person_name, role, email,"
                    " phone, confidence, source_note, verification_status,"
                    " verified_at, source_url) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (ent[0], p["name"], p["role"], p["email"], p["phone"],
                     "official", f"RERA REP-I {reg_no}", "verified",
                     date.today().isoformat(), url))
                people_added += 1
        ok += 1
        if ok % 25 == 0:
            cx.commit()
            print(f"  {ok}/{len(rows)} parsed, {people_added} people")
        time.sleep(0.6)
    cx.commit()
    n_mail = cx.execute("SELECT count(*) FROM rera_raw WHERE promoter_email IS NOT NULL"
                        " AND promoter_email != '(none-found)'").fetchone()[0]
    print(f"done: {ok} parsed, {fail} failed | rows with emails: {n_mail} |"
          f" stakeholders added: {people_added}")
    cx.close()


if __name__ == "__main__":
    main()
