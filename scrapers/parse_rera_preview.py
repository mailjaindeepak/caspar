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

    # walk label/value rows; build person blocks
    person = None
    for tr in soup.find_all("tr"):
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
        if len(cells) < 2:
            continue
        label = " ".join(cells[:-1]).lower()
        value = cells[-1].strip()
        if not value:
            continue
        if "website" in label and value.startswith("http"):
            out["website"] = value
        if any(k in label for k in PERSON_LABELS) and 3 < len(value) < 60 \
                and "@" not in value and not value.isdigit():
            person = {"name": value.title(), "email": None, "phone": None,
                      "role": "Director/KMP (RERA REP-I)"}
            out["people"].append(person)
            continue
        if person is not None:
            if "email" in label and EMAIL_RE.search(value):
                person["email"] = EMAIL_RE.search(value).group(0).lower()
            elif "mobile" in label and PHONE_RE.search(value):
                person["phone"] = PHONE_RE.search(value).group(1)
            elif "designation" in label and len(value) < 60:
                person["role"] = value
    return out


def main() -> None:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10**9
    cx = sqlite3.connect(DB)
    s = requests.Session()
    s.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    rows = cx.execute(
        "SELECT rera_reg_no, promoter_raw, links FROM rera_raw"
        " WHERE links LIKE '%project_preview_open%' AND promoter_email IS NULL"
    ).fetchall()[:limit]
    print(f"to parse: {len(rows)}")
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
        cx.execute(
            "UPDATE rera_raw SET promoter_email=?, promoter_phone=?,"
            " licence_no_cited=? WHERE rera_reg_no=?",
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
                if not (p["email"] or p["phone"]):
                    continue
                if cx.execute("SELECT 1 FROM stakeholder WHERE entity_id=? AND"
                              " person_name=?", (ent[0], p["name"])).fetchone():
                    continue
                cx.execute(
                    "INSERT INTO stakeholder (entity_id, person_name, role, email,"
                    " phone, confidence, source_note) VALUES (?,?,?,?,?,?,?)",
                    (ent[0], p["name"], p["role"], p["email"], p["phone"],
                     "registry", f"RERA REP-I {reg_no}"))
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
