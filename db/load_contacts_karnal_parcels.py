"""Person-level verified contacts for the Karnal ripe-parcel leads (§9).

Adds the Taran §9 fields to `stakeholder` (verification status, last-verified
date, source URL, DIN) and loads the decision-maker research for the live
Karnal land-parcel leads.

Verification vocabulary (§9):
  verified   - asserted by an official register (MCA master data, HARERA filing)
  probable   - single source, or an attribution inferred from a name match
               (e.g. a company's MCA email that carries a director's name)
  unverified - no source good enough to act on

Company-level contacts are NOT promoted to a person unless the attribution is
stated here explicitly, so "whose phone is this?" never gets silently guessed.

Re-runnable: upserts on (entity_id, person_name).

Usage: python db/load_contacts_karnal_parcels.py
"""
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent / "caspar.db"
AS_OF = "2026-08-24"

# Registry mirrors of MCA master data + the HARERA filings they corroborate.
SRC_ZAUBA_RNR = "https://www.zaubacorp.com/company/RNR-TOWNSHIPS-PRIVATE-LIMITED/U70100HR2022PTC106426"
SRC_FALCON_RICH = "https://www.falconebiz.com/company/RICHMINDS-DEVELOPERS-PRIVATE-LIMITED-U68100HR2023PTC115851"
SRC_INSTA_RICH = "https://www.instafinancials.com/company/richminds-developers-private-limited-U68100HR2023PTC115851"
SRC_IF_ESMAX = "https://www.indiafilings.com/search/esmax-infradevelopers-private-limited-cin-U70109HR2021PTC092075"
SRC_RERA_ESMAX = "https://haryanarera.gov.in/ HRERA-PKL-KRL-328-2022 (32 EMPORIO) promoter filing"
SRC_RNR_SITE = "https://rnrtownship.com/"

# entity canonical_name -> company facts to fold back onto the entity row
COMPANIES = [
    dict(entity="RNR Townships Pvt Ltd", cin="U70100HR2022PTC106426", hq="Karnal",
         drop_stub="Rnr Townships Pvt Ltd",
         notes="MCA: incorporated 06-Sep-2022 (ROC Delhi), auth+paid-up Rs 1 Cr. Reg. office "
               "C/o Ram Chander, 1/264 DNC, Suburban KNL MT, Karnal 132001. Site rnrtownship.com "
               "gives office 'adjoining Signature Global City, Sector 28-A' and 17.5 ac "
               "(licence 75 OF 2026 = 16.76 ac); founders described as two brothers "
               "(diploma engineer + MBA) = Anuj + Pankaj Kumar, both directors since incorporation. "
               f"Verified {AS_OF}."),
    dict(entity="Esmax Infradevelopers Pvt Ltd", cin="U70109HR2021PTC092075", hq="Karnal",
         drop_stub=None,
         notes="MCA: incorporated 08-Jan-2021, auth+paid-up Rs 3 Cr. Reg. office Sector-32 near "
               "Noor Mahal Hotel, Karnal 132001. Prior launch 32 EMPORIO (HRERA-PKL-KRL-328-2022) "
               "on licence 121 OF 2021, Sector 32 - a DIFFERENT parcel from the Sector 33 lead "
               f"(188 OF 2025), which remains unlaunched. Verified {AS_OF}."),
    dict(entity="Richminds Developers Pvt Ltd", cin="U68100HR2023PTC115851", hq="Jind",
         drop_stub="M/S Richminds Developers Pvt. Ltd.",
         notes="MCA: incorporated 18-Oct-2023, auth+paid-up Rs 1 Cr. Reg. office Shop 4, New "
               "Jhwahar Nagar, near Eklavya Stadium, Jind 126102. First-time directors, no prior "
               f"RERA launch. Verified {AS_OF}."),
]

# (entity, person, role, din, email, email_status, phone, phone_status,
#  linkedin, source_url, source_note)
PEOPLE = [
    # --- RNR Townships Pvt Ltd -- Sector 28A, 16.76 ac (licence 75 OF 2026)
    ("RNR Townships Pvt Ltd", "Anuj", "Director (since incorporation, 06-09-2022)", "09706664",
     None, None, None, None, None, SRC_ZAUBA_RNR,
     "MCA master data via ZaubaCorp, as-on 2026-07-13. Printed '. ANUJ' - single name, no "
     "surname on the filing. No personal email/phone/LinkedIn found."),
    ("RNR Townships Pvt Ltd", "Pankaj Kumar", "Director (since incorporation, 06-09-2022)", "09706686",
     "poswalpankaj.poswal@gmail.com", "probable", None, None, None, SRC_ZAUBA_RNR,
     "Identity+DIN verified from MCA master data. Email is the COMPANY's MCA-registered address; "
     "attributed to him as probable because it carries his name (Poswal). Company also publishes "
     f"info@rnrtownship.com. No phone: RNR has never filed with HARERA. Verified {AS_OF}."),

    # --- Esmax Infradevelopers Pvt Ltd -- Sector 33, 5.03 ac (licence 188 OF 2025)
    ("Esmax Infradevelopers Pvt Ltd", "Paras Gupta", "Director (since incorporation, 08-01-2021)",
     "09023135", None, None, None, None, None, SRC_IF_ESMAX,
     "MCA master data via IndiaFilings. No personal email/phone/LinkedIn found."),
    ("Esmax Infradevelopers Pvt Ltd", "Manoj Kumar", "Director (since incorporation, 08-01-2021)",
     "03260687", "mkgupta690@gmail.com", "probable", None, None, None,
     f"{SRC_IF_ESMAX} | {SRC_RERA_ESMAX}",
     "Identity+DIN verified from MCA. Email corroborated by TWO official sources (MCA registered "
     "company email + HARERA 32 EMPORIO promoter filing); attribution to him is probable on the "
     "'mkgupta' initials. Company phones 9354915377 / 9896094990 are on the HARERA filing but are "
     f"NOT attributed to a person - do not assume either is his. Verified {AS_OF}."),

    # --- Richminds Developers Pvt Ltd -- Assandh Sector 10, 8.74 ac (licence 96 OF 2026)
    ("Richminds Developers Pvt Ltd", "Naresh Chahal", "Director (since incorporation, 18-10-2023)",
     "10360829", "chahlnaresh@gmail.com", "probable", None, None, None,
     f"{SRC_FALCON_RICH} | {SRC_INSTA_RICH}",
     "Identity+DIN verified from MCA master data. Email is the company's MCA-registered address, "
     "unmasked via InstaFinancials; attributed to him as probable on the name match. No phone: "
     f"Richminds has never filed with HARERA. Verified {AS_OF}."),
    ("Richminds Developers Pvt Ltd", "Sandeep Kumar", "Additional Director (appointed 15-03-2024)",
     "10378632", None, None, None, None, None, SRC_FALCON_RICH,
     "MCA master data via FalconEbiz. No personal email/phone/LinkedIn found."),
]


def migrate(cx):
    cols = {r[1] for r in cx.execute("PRAGMA table_info(stakeholder)")}
    for col in ("din", "verification_status", "verified_at", "source_url"):
        if col not in cols:
            cx.execute(f"ALTER TABLE stakeholder ADD COLUMN {col} TEXT")
            print(f"  + stakeholder.{col}")


def entity_id(cx, name):
    row = cx.execute("SELECT entity_id FROM entity WHERE canonical_name=?", (name,)).fetchone()
    return row[0] if row else None


def main():
    cx = sqlite3.connect(DB)
    print("schema:")
    migrate(cx)

    print("\ncompanies:")
    for c in COMPANIES:
        eid = entity_id(cx, c["entity"])
        if eid is None:
            print(f"  !! entity not found: {c['entity']}")
            continue
        cx.execute("UPDATE entity SET cin=?, hq_city=coalesce(hq_city,?), notes=? "
                   "WHERE entity_id=?", (c["cin"], c["hq"], c["notes"], eid))
        print(f"  {c['entity']} (entity {eid}) <- CIN {c['cin']}")
        # fold the auto-created tier-C stub into the curated entity
        if c["drop_stub"]:
            stub = entity_id(cx, c["drop_stub"])
            if stub and stub != eid:
                cx.execute("UPDATE entity_alias SET entity_id=? WHERE entity_id=?", (eid, stub))
                cx.execute("DELETE FROM entity WHERE entity_id=?", (stub,))
                print(f"    merged stub entity {stub} ('{c['drop_stub']}') -> {eid}")

    print("\npeople:")
    for (ent, person, role, din, email, email_st, phone, phone_st,
         li, src, note) in PEOPLE:
        eid = entity_id(cx, ent)
        if eid is None:
            print(f"  !! entity not found: {ent}")
            continue
        # identity itself is registry-verified; the weakest asserted contact
        # channel sets the row's overall status
        status = "verified" if not email and not phone else (email_st or phone_st)
        row = cx.execute("SELECT stakeholder_id FROM stakeholder WHERE entity_id=? AND person_name=?",
                         (eid, person)).fetchone()
        vals = (role, email, phone, li, "registry", note, din, status, AS_OF, src)
        if row:
            cx.execute("UPDATE stakeholder SET role=?, email=?, phone=?, linkedin=?, "
                       "confidence=?, source_note=?, din=?, verification_status=?, "
                       "verified_at=?, source_url=? WHERE stakeholder_id=?", vals + (row[0],))
            print(f"  ~ {person} ({ent}) [{status}]")
        else:
            cx.execute("INSERT INTO stakeholder (entity_id, person_name, role, email, phone, "
                       "linkedin, confidence, source_note, din, verification_status, verified_at, "
                       "source_url) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (eid, person) + vals)
            print(f"  + {person} ({ent}) [{status}]")

    cx.commit()
    n = cx.execute("SELECT count(*) FROM stakeholder WHERE verification_status IS NOT NULL").fetchone()[0]
    print(f"\n{n} stakeholder rows now carry a §9 verification status.")
    cx.close()


if __name__ == "__main__":
    main()
