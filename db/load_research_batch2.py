"""Load Sonipat/Hisar/Ambala/Kurukshetra research-agent findings into caspar.db."""
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent / "caspar.db"
cx = sqlite3.connect(DB)


def upsert_entity(name, cin, hq, nn, kind, tier, notes, aliases):
    row = cx.execute("SELECT entity_id FROM entity WHERE canonical_name=?", (name,)).fetchone()
    if row:
        eid = row[0]
        cx.execute("UPDATE entity SET cin=coalesce(?,cin), hq_city=coalesce(?,hq_city),"
                   " is_non_native=coalesce(?,is_non_native), kind=?, tier=?, notes=?"
                   " WHERE entity_id=?", (cin, hq, nn, kind, tier, notes, eid))
    else:
        cx.execute("INSERT INTO entity (canonical_name,cin,hq_city,is_non_native,kind,tier,notes)"
                   " VALUES (?,?,?,?,?,?,?)", (name, cin, hq, nn, kind, tier, notes))
        eid = cx.execute("SELECT last_insert_rowid()").fetchone()[0]
    for a in aliases:
        cx.execute("UPDATE entity_alias SET entity_id=? WHERE alias_name=?", (eid, a))
        if not cx.execute("SELECT 1 FROM entity_alias WHERE alias_name=? AND entity_id=?",
                          (a, eid)).fetchone():
            cx.execute("INSERT INTO entity_alias (entity_id, alias_name, source, method,"
                       " confidence, reviewed_by) VALUES (?,?,'manual','manual',1.0,"
                       "'city-research')", (eid, a))
    return eid


def add_stk(eid, person, role, email=None, phone=None, li=None, conf="registry"):
    if not cx.execute("SELECT 1 FROM stakeholder WHERE person_name=? AND entity_id=?",
                      (person, eid)).fetchone():
        cx.execute("INSERT INTO stakeholder (entity_id,person_name,role,email,phone,linkedin,"
                   "confidence) VALUES (?,?,?,?,?,?,?)", (eid, person, role, email, phone, li, conf))


def confirm_launched(dev_alias, city, reg_note):
    for (lc,) in cx.execute("SELECT DISTINCT lc_case_no FROM licence_raw WHERE developer_raw=?"
                            " AND district=?", (dev_alias, city)):
        pid = cx.execute("SELECT parcel_id FROM parcel WHERE lc_case_no=? AND city=?",
                         (lc, city)).fetchone()
        if pid and not cx.execute("SELECT 1 FROM parcel_link WHERE parcel_id=? AND"
                                  " status='manual-confirmed'", (pid[0],)).fetchone():
            cx.execute("INSERT INTO parcel_link (parcel_id,source,source_row_key,method,"
                       "confidence,status,reviewed_by) VALUES (?,?,?,?,?,?,?)",
                       (pid[0], "rera", reg_note, "manual", 1.0, "manual-confirmed",
                        "city-research"))
            cx.execute("UPDATE parcel SET current_stage='rera_registered' WHERE parcel_id=?",
                       (pid[0],))


def add_loc(city, name, tier, lo, hi, unit, ev):
    if not cx.execute("SELECT 1 FROM locality_benchmark WHERE city=? AND name=?",
                      (city, name)).fetchone():
        cx.execute("INSERT INTO locality_benchmark (city,name,tier,rate_low,rate_high,"
                   "rate_unit,evidence,as_of) VALUES (?,?,?,?,?,?,?,?)",
                   (city, name, tier, lo, hi, unit, ev, "2026-08"))


# ===== SONIPAT =====
e = upsert_entity("Eldeco Infracon Realtors (Eldeco Group)", "U70109DL2021PLC390926",
    "New Delhi", 1, "developer", "A-",
    "Eldeco Group SPV, Jasola HQ. Sonipat Sec 33 LAUNCHED: Eldeco Amaya (SNP-496-2023), "
    "Amor (SNP-527-2023, 291 plots), Amor Villa (PKL-1487-2024; villas Rs 1-1.55 Cr, "
    "~Rs 84,450/sqyd). FY25 rev Rs 112.6 Cr; Rs 1,300 cr charges. Only institutional "
    "listed-group developer selling premium villas in Sonipat - first branded-residences "
    "conversation.", ["Eldeco Infracon Realtors Limited"])
add_stk(e, "Pankaj Bajaj", "CMD Eldeco Group (ex-President CREDAI NCR)", None,
        "011-4065-5000", None, "official")
add_stk(e, "Sanjay Kumar", "RERA contact", None, "9818871148")
confirm_launched("Eldeco Infracon Realtors Limited", "Sonipat",
                 "HRERA-PKL-SNP-527-2023 + 496-2023 + PKL-1487-2024 (Amor/Amaya) - LAUNCHED")

e = upsert_entity("GPB Trading LLP (RP Group)", "LLPIN AAQ-7168", "New Delhi (Janakpuri)",
    1, "developer", "B-",
    "PP Green City 2 - 30.4 ac, 547 DDJAY plots, HRERA-PKL-SNP-526-2023, LAUNCHED 2023. "
    "Thin-capital SPV of local dealer group; rpgroup4@gmail.com.", ["GPB Trading LLP"])
add_stk(e, "Parveen", "Designated partner (DIN 03443023)", "rpgroup4@gmail.com")
add_stk(e, "Bahar Gogia", "Designated partner (DIN 07126762)")
confirm_launched("GPB Trading LLP", "Sonipat", "HRERA-PKL-SNP-526-2023 (PP Green City 2) - LAUNCHED")

e = upsert_entity("Orion Tech Park Developers LLP", "LLPIN AAW-3819", "New Delhi (CP)",
    1, "developer", "B-",
    "Orion City, Kharkhoda Sec 4 - 18.98 ac, 299 DDJAY plots, HRERA-PKL-SNP-674-2025, "
    "LAUNCHED 2025. Jain/Mehta two-family consortium (8 partners), Ansal Bhawan CP. "
    "Maruti-corridor play; likely open to structured partnerships.",
    ["Orion Tech Park Developers LLP"])
add_stk(e, "Sanjay Jain", "Designated partner")
add_stk(e, "Rohit Mehta", "Designated partner")
confirm_launched("Orion Tech Park Developers LLP", "Sonipat",
                 "HRERA-PKL-SNP-674-2025 (Orion City) - LAUNCHED")

e = upsert_entity("Jai Krishna Artec JV (Krishna Apra lineage)", None, "New Delhi", 1,
    "developer", "B",
    "Greenwood City Sec 26-27 Sonipat - 137.55 ac, RERA-PKL-647-2019. The 20.6 ac Sec 33 "
    "(2023) parcel NOT publicly linked to any RERA - potentially genuine ripe land bank.",
    ["Jai Krishna Artec JV"])
add_stk(e, "Bhupinder Singh", "RERA contact", None, "9811042112")
add_stk(e, "Ashok Wadia", "Authorized representative", None, "9811088201")

e = upsert_entity("Rishika Group (Sanjiv Sarin, Ganaur)", None, "Sonipat (Ganaur)", 0,
    "developer", "B-",
    "Local cluster: Rishika Edifice/Buildtech/Green Global/Elevation/Creator LLPs + "
    "Rissan Buildtech (holds ROHTAK 15.2 ac Sec 33A - same owner). Rishika Valley Ganaur "
    "launched (RERA-PKL-1312-2023). The 17.9 ac Sonipat (2026) likely ripe. "
    "Principal Sanjiv Sarin DIN 00346719.", ["Rishika Edifice LLP", "Rissan Buildtech LLP"])
add_stk(e, "Sanjiv Sarin", "Principal (DIN 00346719), Sector 14 Sonipat", None, "7838214128")

e = upsert_entity("Jindal Realty (OP Jindal Group)", None, "New Delhi", 1, "developer", "A-",
    "Jindal Global City Sonipat Sec 35 - 214 ac, plots from ~Rs 50L; OP Jindal group.", [])
add_stk(e, "Abhay Mishra", "President & CEO", None, "8010055333 (sales)", None, "official")

add_loc("Sonipat", "Kundli border", "prime", None, None, None,
        "~Rs3,800/sqft flats, +35.7% yoy, +73.6%/3yr; Delhi Metro Ph-IV to Kundli approved")
add_loc("Sonipat", "Sector 33-35 belt", "prime", 84000, 84450, "Rs/sqyd",
        "Eldeco Amor/Amaya; Jindal Global City; Hero Swarnpath - premium test bed")
add_loc("Sonipat", "Kharkhoda", "secondary", 35000, 85000, "Rs/sqyd",
        "Maruti Rs 18,000 cr complex; Plant 1 producing since Feb 2025")
add_loc("Sonipat", "Gohana / Gannaur", "value", None, None, None,
        "entry-level; RRTS station planned at Gannaur")
add_loc("Sonipat", "Rajiv Gandhi Education City", "secondary", None, None, None,
        "Ashoka/IIT-D ext/NLU - premium demand anchor")

# ===== HISAR =====
e = upsert_entity("Jindal Prop Infra LLP (SR Jindal Group)", "LLPIN ACE-0247", "Hisar", 0,
    "developer", "B",
    "SR Jindal Group (Jindal Polybuttons - India's largest button maker; Hisar Metal "
    "Industries listed; Liberty Shoes) - NOT the OP Jindal steel family. Neeraj Kumar "
    "Jindal (DIN 00054885) + Pankaj Jindal; Singal family added May 2025 (JV). 9.5 ac "
    "Sec 11 (2026) unlaunched + sister vehicle Avaas Roots Infra LLP (2025) - deliberate "
    "RE diversification by wealthy industrial family. Strongest Hisar target.",
    ["Jindal Prop Infra LLP"])
add_stk(e, "Neeraj Kumar Jindal", "Designated partner (DIN 00054885); MD Jindal Polybuttons",
        "via jindalbuttons.com office")
add_stk(e, "Pankaj Jindal", "Designated partner (DIN 00049921)")

e = upsert_entity("Agroha Developers", None, "Hisar (Agroha)", 0, "developer", "C+",
    "Uklana Enclave - Lic 91 of 2024, HRERA-PKL-HSR-656-2025 LAUNCHED. Marketed by Ravi "
    "Properties (Ravi Beniwal). Likely partnership firm.", ["Agroha Developers"])
add_stk(e, "Ravi Beniwal", "Marketer (Ravi Properties, Agroha Mod)",
        "ravibeniwal091999@gmail.com", "98121 91999")
confirm_launched("Agroha Developers", "Hisar", "HRERA-PKL-HSR-656-2025 (Uklana Enclave) - LAUNCHED")

upsert_entity("Deepti Gupta Trading LLP (Gupta family, Rishi Nagar)", None, "Hisar", 0,
    "developer", "C+",
    "High-probability: Gupta medical/business family, Rishi Nagar (Gupta Skin Hospital; "
    "sister LLP Nikita Gupta Trading - partners Nakul/Deepti/Shashi Gupta). 6.2 ac Sec 39 "
    "(2026) unlaunched. UNCONFIRMED - verify LLPIN via MCA.", ["Deepti Gupta Trading LLP"])
upsert_entity("Vasudha Associates", None, None, None, "developer", "C+",
    "No public footprint - likely local partnership. 20.6 ac DDJAY Hansi Sec 2 (2026); "
    "Hansi became 23rd district Dec 2025 (licensing wave). ID via DTCP file/gatekeeper.",
    ["Vasudha Associates"])

add_loc("Hisar", "Sectors 13/14", "prime", 56925, 56925, "Rs/sqyd",
        "Highest draft collector rate 2026-27; +15% residential hike")
add_loc("Hisar", "Urban Estate / Model Town / Defence Colony", "prime", None, None, None,
        "legacy premium pockets")
add_loc("Hisar", "Sector 24 / bypass belt", "secondary", None, None, None,
        "Rajdarbar Spaces 65-ac township (RERA-PKL-1534-2024)")
add_loc("Hisar", "Airport/IMC belt", "secondary", None, None, None,
        "IMC 2,988 ac Rs 4,680 cr signed Aug 2025; agri collector +25-75%; airport traffic "
        "still tiny (9,559 pax FY26) - narrative asset")
add_loc("Hisar", "Hansi", "value", None, None, None, "new district Dec 2025")
add_loc("Hisar", "Uklana", "value", None, None, None, "DDJAY belt")

# ===== AMBALA =====
e = upsert_entity("Imperial Developers (Ambala)", None, "Ambala City", 0, "developer", "B-",
    "MM Indraprasth - 10.8 ac group housing Sec 25, RERA-PKL-1592-2024, Rs 452 cr, "
    "completion 2029. The district's premium test case.", [])
add_stk(e, "Vishal Garg", "Contact, Imperial Developers", None, "+91 80598 80598", None,
        "official")
upsert_entity("Ambala Home Land Developers", None, "Ambala", 0, "developer", "C",
    "No public footprint - fresh single-purpose SPV pattern. 6 ac DDJAY Sec 28 (2026). "
    "VERDICT: Ambala not viable for branded residences (ceiling ~Rs 4 cr Vatika villas, "
    "one midscale Ramada, thin absorption) - city deprioritized.",
    ["Ambala Home Land Developers Pvt. Ltd."])
add_loc("Ambala", "Sectors 23-27 belt", "secondary", None, None, None,
        "only organized corridor: Vatika City Central 174ac, MM Indraprasth, Mahira")
add_loc("Ambala", "Ambala Cantt", "secondary", 1800, 7150, "Rs/sqft",
        "defence-encumbered supply")
add_loc("Ambala", "Naraingarh", "value", None, None, None, "hinterland; IMT land assembly")

# ===== KURUKSHETRA =====
e = upsert_entity("Green Homes platform (Sun and Sky / Green Homes Infra / Box Hive)",
    "GH Infra: U70100DL2013PTC247714", "New Delhi (Rani Bagh)", 1, "developer", "B-",
    "Platform brand, ~62 ac across 3 SPVs in Kurukshetra: Green Homes Royal (33.68 ac "
    "Sec 28-29, KRK-636-2024), Green Homes Prime (Sun and Sky Developers, 21.86 ac Sec "
    "29-30, KRK-758-2025 - LAUNCHED), Green Homes B R (Box Hive Innovation, 6.94 ac Sec 11, "
    "KRK-834-2026). Probable controllers: Vandan Jain (DIN 09084358) + Hardeep Singh "
    "(DIN 09084414) - verify. Marketing via Bhoomidarshan (info@bhoomidarshan.com).",
    ["Sun and Sky Developers Pvt. Ltd."])
add_stk(e, "Vandan Jain", "Director, Green Homes Infra (DIN 09084358) - probable controller")
add_stk(e, "Hardeep Singh", "Director, Green Homes Infra (DIN 09084414) - probable controller")
confirm_launched("Sun and Sky Developers Pvt. Ltd.", "Kurukshetra",
                 "HRERA-PKL-KRK-758-2025 (Green Homes Prime) - LAUNCHED")

e = upsert_entity("Aggarsain Land Developers", None, "Kurukshetra", 0, "developer", "C+",
    "Aggarsain Dream City, Ladwa - 10.5 ac RPL (2025), site down, no RERA found - RIPE. "
    "Possible link: Aggarsain Real Estate (Sec 13 HUDA Mkt brokerage since 1996) family "
    "graduating to development - verify.", ["Aggarsain Land Developers"])
e = upsert_entity("Shree Vardhman Group", None, "New Delhi/NCR", 1, "developer", "B-",
    "Shree Vardhman City + My Homes, Sector 30 Kurukshetra; ~10 msf across North India; "
    "longest-standing organised player there. Founder Sandeep Jain.", [])
add_stk(e, "Sandeep Jain", "Founder, Shree Vardhman Group", None, None, None, "official")

add_loc("Kurukshetra", "Thanesar HSVP core (Sec 2/3/5/7/13/17)", "prime", None, None, None,
        "Sec 3 cited Rs 6,500-8,000 (unit ambiguous); elevated rail corridor opened")
add_loc("Kurukshetra", "NH-44 belt (Sec 28-30, 41)", "secondary", None, None, None,
        "Godrej Parkland Estate Sec 41 (Rs 65L-2.57Cr, completing Sep 2026); Green Homes; "
        "Shree Vardhman; HSVP auctioning Sec 30 plots Mar 2026")
add_loc("Kurukshetra", "Brahma Sarovar / Jyotisar / Pipli", "secondary", None, None, None,
        "religious-tourism zone: Rs 250 cr Jyotisar centre, IGM 21 days/40 countries; only "
        "branded stay = Clarks Inn franchise; possible HSVP 5-star hotel site Sec 2 "
        "(single-source) - hotel/serviced-residence play, high seasonality")
add_loc("Kurukshetra", "Ladwa / Pehowa / Shahbad", "value", None, None, None,
        "tehsil towns; Ladwa getting first licensed colonies")

# ===== ROHTAK =====
e = upsert_entity("One Group Developers (Spice One / One Point Realty)",
    "Spice One: U00500DL2005PTC139217", "New Delhi (Barakhamba Rd)", 1, "developer", "B+",
    "Most active organized Rohtak developer: ONE City Sec 27A (Lic 157/2023, 15.8 ac, "
    "HRERA-PKL-ROH-511-2023), ONE City Sec 37 (ROH-525-2023), One City Homes floors. "
    "'One Height Developers' licence 15.8 ac Sec 27A 2023 = almost certainly same "
    "licence/project (co-licensee) - treated as launched.",
    ["ONE HEIGHT DEVELOPERS PVT LTD"])
add_stk(e, "Sunil Kumar Jain", "Chairman, One Group", "sales@onegroup.co.in",
        "+91 92171 28999", "linkedin.com/in/sunil-jain-68484938", "official")
add_stk(e, "Udit Jain", "Executive Director", None, "+91 88752 21116", None, "official")
confirm_launched("ONE HEIGHT DEVELOPERS PVT LTD", "Rohtak",
                 "HRERA-PKL-ROH-511-2023 (ONE City 27A) - probable same licence, LAUNCHED")

e = upsert_entity("Galaxy Magnum Group", "U45201DL2020PTC373362",
    "New Delhi (Sainik Farms)", 1, "developer", "B-",
    "Poddar family (Rajiv/Sanjiv Poddar + Vanshika Bajaj; group co Infraheights with "
    "Tarun Murarka, email sudhir@galaxymagnum.com). Commercial track record (GRIHA Gurgaon); "
    "15.6 ac Sec 27C Rohtak (2026) = first plotted/residential foray, PRE-LAUNCH - advisory "
    "window open. Paid-up Rs 10 Cr; FY25 rev Rs 6.84 Cr.",
    ["Galaxy Magnum Projects Pvt. Ltd."])
add_stk(e, "Rajiv Poddar", "Whole-Time Director", "sudhir@galaxymagnum.com (group)")
add_stk(e, "Sanjiv Poddar", "Director")

e = upsert_entity("Forteasia Realty Pvt Ltd", "U70200DL2011PTC224926",
    "Faridabad", 1, "developer", "B",
    "Fastest-scaling DDJAY specialist: FY24 rev Rs 79.2 Cr (+425%), ~5.3 msf across "
    "Haryana. Rohtak: Park View 27A, Silicon Valley 22D, 13.7 ac Sec 22A (2025) "
    "UNLAUNCHED extension + planned industrial township. Two fresh directors 2025 = "
    "scaling/capital induction.", ["Forteasia Realty Pvt. Ltd."])
add_stk(e, "Sandeep Mangla", "Director", "forteasiarealty2016@gmail.com", "+91 81201 01812")

upsert_entity("Consonance Infra LLP", None, None, None, "developer", "C+",
    "ZERO registry footprint (fresh SPV). 20.8 ac DDJAY Sec 21E (2026) - biggest ripe "
    "Rohtak parcel, PRE-LAUNCH. Possible NV City-adjacent vehicle. MCA pull needed.",
    ["Consonance Infra LLP"])

e = upsert_entity("Rishika Group (Sanjiv Sarin, Ganaur)", None, None, None, "developer", "B-",
    "See Sonipat entry. Rohtak: Rissan Buildtech 15.2 ac Sec 33A = Rishika Gardenia "
    "LAUNCHED (HRERA-PKL-ROH-493-2023, 264 plots, poss. 2028). info@rishikabuilders.com, "
    "+91 77400 00635, MG Mall Sector 14 Sonipat.", [])
confirm_launched("Rissan Buildtech LLP", "Rohtak",
                 "HRERA-PKL-ROH-493-2023 (Rishika Gardenia) - LAUNCHED")

e = upsert_entity("HL Group (HL City Rohtak)", None, "Rohtak", 0, "developer", "B-",
    "HL City Sec 30-B township, 500+ families; new 3/4/5-BHK towers HRERA-PKL-ROH-670-2025 "
    "+ 1-lakh-sqft clubhouse = Rohtak's first real luxury-apartment test and nearest "
    "premium-branded positioning. hlresidency@gmail.com, +91 89303 53525.", [])
e = upsert_entity("Suncity Projects (Rohtak)", "U45201DL1996PTC083915", "New Delhi", 1,
    "developer", "B-",
    "Legacy ~200-ac township Sec 34/35/36; plots ~Rs 60-66k/sqyd. L.N. Goel chairman.", [])

add_loc("Rohtak", "Model Town / DLF Colony / Subhash Nagar / Sec 14", "prime", None, None,
        None, "peak house listings Rs 9-12 Cr")
add_loc("Rohtak", "Sector 25-28 (Omaxe/NH-10 East belt)", "prime", 8900, 12550, "Rs/sqft",
        "+6.9% yoy; Kheri Sadh 27A belt; HTL 17-ac parcel changed hands via NCLT - watch")
add_loc("Rohtak", "Sonipat Rd (Sec 33-36)", "secondary", 7200, 9450, "Rs/sqft",
        "Suncity ~Rs 66k/sqyd plots; Rishika Gardenia")
add_loc("Rohtak", "Sector 21E/22A/22D/36A/37 (north)", "secondary", None, None, None,
        "DDJAY cluster: NV City draws, Forteasia, Consonance PRE-LAUNCH")
add_loc("Rohtak", "Sector 30-B / IMT side", "secondary", None, None, None,
        "HL City; IMT industrial base")

cx.commit()
print("entities:", cx.execute("SELECT count(*) FROM entity").fetchone()[0],
      "| stakeholders:", cx.execute("SELECT count(*) FROM stakeholder").fetchone()[0],
      "| localities:", cx.execute("SELECT count(*) FROM locality_benchmark").fetchone()[0],
      "| manual-confirmed:", cx.execute(
          "SELECT count(*) FROM parcel_link WHERE status='manual-confirmed'").fetchone()[0])
cx.close()
