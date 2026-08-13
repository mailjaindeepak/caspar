"""Build outputs/hospitality_leads_haryana_v2.xlsx — the 140 CLU hospitality leads
as a working outreach file (leads sheet + summary + legend)."""
import sqlite3
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "db" / "caspar.db"
OUT = ROOT / "outputs" / "hospitality_leads_haryana_v2.xlsx"

ARIAL = Font(name="Arial", size=10)
HDR = Font(name="Arial", size=10, bold=True, color="FFFFFF")
HDR_FILL = PatternFill("solid", fgColor="2F5D46")
WORK_FILL = PatternFill("solid", fgColor="FFF2CC")   # columns the team fills in
YELLOW = PatternFill("solid", fgColor="FFFF00")
THIN = Border(*[Side(style="thin", color="C9C9C9")] * 4)


# Contact research results (web research Aug 13, 2026). Keyed by
# (district, applicant-substring). owner, phone_email, status, note.
CONTACTS = {
    ("Karnal", "Deventure Hotels"): (
        "Rajeev Mukul — Founder & MD, Deventure Hotel and Resorts P.L. "
        "(CIN U55101DL2010PTC205366)",
        "saleshead@deventurehotel.com; gm.karnal@deventurehotel.com; "
        "+91 93178 88989; 0184-3540400",
        "Contact found",
        "Operating chain (Karnal NH-44, Shimla Hills, Delhi x2, Sarovar Portico "
        "Kapashera). Basdhara CLU = highway-resort expansion, unannounced. "
        "Src: deventurehotel.com + ZaubaCorp"),
    ("Panipat", "JAVI HOME"): (
        "Vibhor Jain — MD, Javi Home P.L. (Panipat home-textiles exporter, "
        "CIN U17120DL2010PTC210592; Neeti/Naman Jain co-directors)",
        "hello@javihome.com; WhatsApp +91 98965 44053",
        "Contact found",
        "Textile-export family diversifying into hospitality; exports to 71+ "
        "countries. Src: javihome.com + TheCompanyCheck"),
    ("Panipat", "SATBIR SINGH"): (
        "UNVERIFIED: possibly 'The Lagoon' hotel, Patti Kalyana NH-44 "
        "(opened recently, same village)",
        "+91 80595 55500 (The Lagoon front desk)",
        "Lead - verify",
        "New upscale hotel on exact village matches CLU timing; owner name "
        "not published. Verify by phone. Src: Tripadvisor/Booking"),
    ("Hisar", "GREEN VALLEY"): (
        "Green Valley (regd. partnership, GSTIN 06AAWFG6114H1Z7), GT Rd "
        "Kutabpur, Hansi — operating leisure complex",
        "greenvalliewaterpark@gmail.com; +91 98121 57357; +91 77000 12262",
        "Contact found",
        "Operating: Green Vallie Water Park (2025), Haldiram's, Levi's store, "
        "banquets on NH-9. Src: greenvalliewaterpark.com + LEI/GST"),
    ("Rohtak", "LPSIS"): (
        "Rahul & Sandhya Jain — LPSIS P.L. (CIN U74900DL2011PTC225360), "
        "Universal Precision Screws group, Rohtak",
        "rfq@lpsis.co.in; 9729870604; 7496977882",
        "Contact found",
        "Major Rohtak fastener manufacturer's family; NH-10 site. Co-licensee "
        "'Sohana Auto P.L.' unresolved in MCA — verify spelling. Src: ZaubaCorp/lpsis.co.in"),
    ("Ambala", "Ashwani"): (
        "UNVERIFIED: probable venue = Ambala Haveli, NH-44 GT Rd, village "
        "Mohra (restaurant+rooms+banquet, renovated 2020)",
        "info.ambalahaveli@gmail.com; +91 90505 66555; +91 90531 46555",
        "Lead - verify",
        "Ownership link to applicant not published — confirm by phone. "
        "Src: Booking/Facebook"),
    ("Kurukshetra", "Dayal rice"): (
        "UNVERIFIED: only rice mill in village Niwarsi = Goel Rice Mills, "
        "Pipli Rd, Ladwa (est. 2019) — plausibly same family, different firm name",
        "sales@goelricemills.com; +91 89502 23456",
        "Lead - verify",
        "Inference, not confirmation. Src: goelricemills.com"),
    ("Panipat", "GUNJAN MEHNDIRATTA"): (
        "", "", "New",
        "Ganjbar = NH-44 frontage 9 km S of Panipat — 3 hotel CLUs 2025-26 "
        "forming a new highway strip; all pre-construction. ID via DTCP file."),
    ("Karnal", "RAJESH, RAJEEV, AMIT GOYAL"): (
        "", "", "New",
        "Shamgarh GT-Road belt (comparables: The Vivaan, Comfort Inn Taraori). "
        "No footprint — gatekeeper/DTCP-file ID."),
}


def find_contact(district: str, applicant: str):
    for (d, key), v in CONTACTS.items():
        if d == district and key.lower() in (applicant or "").lower():
            return v
    return None


def category(activity: str) -> str:
    a = activity.lower()
    if "hotel" in a:
        return "Hotel"
    if "motel" in a:
        return "Motel"
    if "resort" in a:
        return "Resort"
    if "banquet" in a or "marriage" in a:
        return "Banquet"
    if "farm" in a:
        return "Farmhouse"
    if "amusement" in a:
        return "Amusement"
    if "club" in a:
        return "Club"
    return "Other"


def main() -> None:
    cx = sqlite3.connect(DB)
    rows = cx.execute(
        "SELECT district, clu_file_no, applicant, village, activity,"
        " granted_area_sqm, area_acre, sanction_date, clu_year FROM clu_raw"
        " WHERE clu_file_no IN (SELECT clu_file_no FROM v_hospitality_leads)"
        " ORDER BY district, clu_year DESC, area_acre DESC").fetchall()
    cx.close()

    wb = Workbook()

    # ---------- Leads sheet ----------
    ws = wb.active
    ws.title = "Leads"
    headers = ["City", "CLU File No", "Applicant", "Village / Location", "Activity",
               "Category", "Area (sq m)", "Area (acres)", "Sanction Date", "Year",
               "Priority Score", "Priority Band", "Map (GIS)",
               "Status", "Owner / Contact", "Phone / Email", "Next Step", "Notes"]
    work_cols = {14, 15, 16, 17, 18}
    for c, h in enumerate(headers, 1):
        cell = ws.cell(1, c, h)
        cell.font = HDR
        cell.fill = HDR_FILL if c not in work_cols else PatternFill("solid", fgColor="A87B2D")
        cell.border = THIN
        cell.alignment = Alignment(vertical="center", wrap_text=True)

    for r, (dist, fno, applicant, village, activity, sqm, acre, sdate, yr) in enumerate(rows, 2):
        cat = category(activity or "")
        gis = (f"https://tcpharyana.gov.in/CS_marking/LicenceGIS/CluIndex?CluNo={fno}"
               if fno else "")
        values = [dist, fno, applicant, village, activity, cat, sqm, acre, sdate, str(yr)]
        for c, v in enumerate(values, 1):
            cell = ws.cell(r, c, v)
            cell.font = ARIAL
            cell.border = THIN
        ws.cell(r, 7).number_format = "#,##0"
        ws.cell(r, 8).number_format = "0.00"
        # Priority score: category weight + size bonus + recency bonus (rubric in Legend)
        ws.cell(r, 11, (f'=IF($F{r}="Hotel",5,IF($F{r}="Motel",4,IF($F{r}="Resort",4,'
                        f'IF($F{r}="Amusement",4,IF($F{r}="Banquet",3,2)))))'
                        f'+IF($H{r}>=4,2,IF($H{r}>=2,1,0))'
                        f'+IF(VALUE($J{r})>=2024,2,IF(VALUE($J{r})>=2021,1,0))'))
        ws.cell(r, 12, f'=IF($K{r}>=7,"High",IF($K{r}>=5,"Medium","Low"))')
        for c in (11, 12):
            ws.cell(r, c).font = ARIAL
            ws.cell(r, c).border = THIN
        link = ws.cell(r, 13, "Map View" if gis else "")
        if gis:
            link.hyperlink = gis
            link.font = Font(name="Arial", size=10, color="2F5D46", underline="single")
        link.border = THIN
        hit = find_contact(dist, applicant or "")
        if hit:
            owner, phone_email, status, note = hit
            ws.cell(r, 14, status)
            ws.cell(r, 15, owner)
            ws.cell(r, 16, phone_email)
            ws.cell(r, 18, note)
        else:
            ws.cell(r, 14, "New")
        for c in range(14, 19):
            ws.cell(r, c).fill = WORK_FILL
            ws.cell(r, c).border = THIN
            if ws.cell(r, c).value is None:
                ws.cell(r, c).value = ""
            ws.cell(r, c).font = ARIAL
            ws.cell(r, c).alignment = Alignment(wrap_text=True, vertical="top")

    widths = [12, 15, 30, 18, 26, 11, 11, 10, 12, 7, 9, 9, 10, 10, 22, 22, 22, 30]
    for c, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(c)].width = w
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:R{len(rows) + 1}"

    # ---------- Summary sheet ----------
    n = len(rows) + 1
    s = wb.create_sheet("Summary")
    s.cell(1, 1, "Hospitality CLU Leads — Summary").font = Font(
        name="Arial", size=13, bold=True)
    s.cell(2, 1, "All figures computed live from the Leads sheet"
           " (COUNTIFS/SUMIFS).").font = Font(name="Arial", size=9, italic=True)

    cities = ["Karnal", "Panipat", "Sonipat", "Rohtak", "Hisar", "Ambala", "Kurukshetra"]
    cats = ["Hotel", "Motel", "Resort", "Banquet", "Farmhouse", "Amusement", "Club"]
    r0 = 4
    hdr = ["City", "Leads", "Acres"] + cats + ["High priority"]
    for c, h in enumerate(hdr, 1):
        cell = s.cell(r0, c, h)
        cell.font = HDR
        cell.fill = HDR_FILL
        cell.border = THIN
    for i, city in enumerate(cities):
        r = r0 + 1 + i
        s.cell(r, 1, city)
        s.cell(r, 2, f'=COUNTIF(Leads!$A$2:$A${n},$A{r})')
        s.cell(r, 3, f'=SUMIF(Leads!$A$2:$A${n},$A{r},Leads!$H$2:$H${n})')
        s.cell(r, 3).number_format = "0.0"
        for j, cat in enumerate(cats):
            s.cell(r, 4 + j,
                   f'=COUNTIFS(Leads!$A$2:$A${n},$A{r},Leads!$F$2:$F${n},"{cat}")')
        s.cell(r, 11, f'=COUNTIFS(Leads!$A$2:$A${n},$A{r},Leads!$L$2:$L${n},"High")')
        for c in range(1, 12):
            s.cell(r, c).font = ARIAL
            s.cell(r, c).border = THIN
    rt = r0 + 1 + len(cities)
    s.cell(rt, 1, "Total").font = Font(name="Arial", size=10, bold=True)
    for c in range(2, 12):
        col = get_column_letter(c)
        s.cell(rt, c, f"=SUM({col}{r0 + 1}:{col}{rt - 1})")
        s.cell(rt, c).font = Font(name="Arial", size=10, bold=True)
        s.cell(rt, c).border = THIN
    s.cell(rt, 3).number_format = "0.0"
    for c, w in enumerate([14, 8, 8, 8, 8, 8, 9, 11, 11, 7, 12], 1):
        s.column_dimensions[get_column_letter(c)].width = w

    # ---------- Legend ----------
    lr = rt + 3
    s.cell(lr, 1, "How to use this file").font = Font(name="Arial", size=11, bold=True)
    legend = [
        ("Yellow-header columns on the Leads sheet (Status, Owner/Contact, Phone/Email,"
         " Next Step, Notes) are yours to fill in; every other column is source data —"
         " do not edit."),
        ("Status values suggested: New / Researching / Contacted / Meeting / Dead."
         " Example: Status=Contacted, Owner=Deventure Hotels front office,"
         " Phone=via site visit, Next Step=Site meeting w/ Taran, Notes=open to flag talks."),
        ("Priority Score (col K) = category weight (Hotel 5, Motel/Resort/Amusement 4,"
         " Banquet 3, Farmhouse/Club 2) + size bonus (>=4 ac +2, >=2 ac +1) + recency"
         " (2024+ +2, 2021+ +1). Band: High >=7, Medium 5-6, Low <5."
         " Assumption made by Caspar analysis, not from any external source."),
        ("Map (GIS) links open the parcel's boundary on DTCP Haryana's official map"
         " (tcpharyana.gov.in)."),
        ("Source: DTCP Haryana CLU year-registers 2017-2026"
         " (tcpharyana.gov.in/WebAdmin/clu/index?id=YYYY), scraped Aug 13, 2026,"
         " filtered to hotel/motel/resort/banquet/farmhouse/amusement/club activities."),
    ]
    for i, txt in enumerate(legend):
        cell = s.cell(lr + 1 + i, 1, txt)
        cell.font = Font(name="Arial", size=9)
        cell.alignment = Alignment(wrap_text=True)
        s.merge_cells(start_row=lr + 1 + i, start_column=1,
                      end_row=lr + 1 + i, end_column=11)
        s.row_dimensions[lr + 1 + i].height = 26
    s.cell(lr, 2).fill = YELLOW

    OUT.parent.mkdir(exist_ok=True)
    wb.save(OUT)
    print(f"{len(rows)} leads -> {OUT}")


if __name__ == "__main__":
    main()
