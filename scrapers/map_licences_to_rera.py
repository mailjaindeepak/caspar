"""Map DTCP licences to HARERA registrations at parcel level.

Join keys, in order of strength:
  1. fuzzy developer name (rapidfuzz token_set_ratio on normalized names)
  2. acreage embedded in RERA project names ("AREA 71.01 ACRES") vs licence area
  3. sector extracted from RERA project name/address vs licence sector

Outputs data/<city>/licence_rera_map.csv (one row per licence, with match
status) and prints the parcel-level gap: still-valid licences with no RERA
registration.

Usage: python map_licences_to_rera.py karnal
"""
import csv
import re
import sys
from datetime import date
from pathlib import Path

from rapidfuzz import fuzz

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cluster_developers import norm

ROOT = Path(__file__).resolve().parent.parent

AREA_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:ACRE|ACERS|ACRES|SRES|AC\b)?", re.I)
SEC_RE = re.compile(r"SEC(?:TOR)?[\s.\-]*(\d+[A-Z]?)", re.I)

# Generic real-estate words that dominate token similarity and cause false
# matches ("Satwik Infrastructure" ~ "JBB Infrastructures"). Stripped before
# comparing; the distinctive brand tokens are what must match.
GENERIC = {
    "DEVELOPER", "BUILDER", "BUILDWELL", "BUILDCON", "CONSTRUCTION",
    "INFRASTRUCTURE", "INFRA", "INFRADEVELOPER", "INFRALAND", "INFRAHEIGHT",
    "ESTATE", "COLONIZER", "COLONISER", "PROMOTER", "TOWNSHIP", "REALTY",
    "REALCON", "REALTOR", "HOME", "HOUSING", "LAND", "LANDCON", "PROJECT",
    "ENTERPRISE", "GROUP", "PROPERTIE", "SPACE", "BUILDTECH", "PROPBUILD",
    "TOWN", "PLANNER", "RESIDENCY", "CORPORATION",
}


def brand(name_norm: str) -> str:
    """Distinctive tokens only; falls back to full name if nothing is left."""
    toks = [t for t in name_norm.split() if t not in GENERIC]
    return " ".join(toks) if toks else name_norm


def name_similarity(a_norm: str, b_norm: str) -> float:
    ab, bb = brand(a_norm), brand(b_norm)
    sim = fuzz.token_set_ratio(ab, bb)
    # single-token brands ("G", "KN") match too easily — require the full
    # names to broadly agree as well
    if len(ab) <= 3 or len(bb) <= 3:
        sim = min(sim, fuzz.token_set_ratio(a_norm, b_norm))
    return sim


def extract_areas(text: str) -> list[float]:
    out = []
    for m in re.finditer(r"AREA[^0-9]{0,15}(\d+(?:\.\d+)?)", text, re.I):
        out.append(float(m.group(1)))
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*(?:ACRES|ACERS|ACRE)\b", text, re.I):
        out.append(float(m.group(1)))
    return out


def extract_sectors(text: str) -> set[str]:
    return {m.group(1).upper() for m in SEC_RE.finditer(text)}


def lic_sectors(raw: str) -> set[str]:
    return {s.strip().upper() for s in re.split(r"[,&/]", raw or "") if s.strip()}


def parse_date(d: str):
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", (d or "").strip())
    if not m:
        return None
    return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))


def main() -> None:
    city = (sys.argv[1] if len(sys.argv) > 1 else "karnal").lower()
    ddir = ROOT / "data" / city
    lic = list(csv.DictReader((ddir / "dtcp_licences.csv").open(encoding="utf-8-sig")))
    rera = list(csv.DictReader((ddir / "harera_projects.csv").open(encoding="utf-8-sig")))

    for r in rera:
        blob = f"{r.get('Project Name','')} {r.get('Project Address','')}"
        r["_dev"] = norm(r.get("Promoter Name", ""))
        r["_areas"] = extract_areas(blob)
        r["_secs"] = extract_sectors(blob)

    out_rows, today = [], date.today()
    for L in lic:
        ldev = norm(L.get("Developer", ""))
        lsecs = lic_sectors(L.get("Sector", ""))
        try:
            larea = float(L.get("Area_acre", "") or 0)
        except ValueError:
            larea = 0.0

        best, best_sim, best_parcel, best_why = None, 0.0, False, ""
        for r in rera:
            name_sim = name_similarity(ldev, r["_dev"]) if ldev and r["_dev"] else 0
            area_hit = bool(larea and any(abs(a - larea) / larea < 0.02
                                          for a in r["_areas"]))
            sec_hit = bool(lsecs and r["_secs"] & lsecs)
            # Gate: strong name, OR near-exact acreage rescuing a partial name
            # (licence held by group parent, RERA under a different SPV).
            if name_sim < 70 and not (area_hit and name_sim >= 35):
                continue
            parcel = area_hit or sec_hit
            score = name_sim + (30 if area_hit else 0) + (15 if sec_hit else 0)
            cur = best_sim + (45 if best_parcel else 0)
            if score > cur:
                why = [f"name={name_sim:.0f}"] + (["area"] if area_hit else []) \
                      + (["sector"] if sec_hit else [])
                best, best_sim, best_parcel, best_why = r, name_sim, parcel, "+".join(why)

        valid_to = parse_date(L.get("ValidUpto", ""))
        if best is None:
            status = "UNMATCHED"          # developer absent from RERA entirely
        elif best_parcel and best_sim >= 70:
            status = "PARCEL-MATCH"       # same developer, same parcel
        elif best_parcel:
            status = "SPV-MATCH?"         # area/sector fits, name only partial — review
        elif best_sim >= 85:
            status = "DEV-MATCH"          # developer active in RERA; this parcel unconfirmed
        else:
            status = "WEAK"
        out_rows.append({
            "LicenseNo": L.get("LicenseNo", ""), "IssueDate": L.get("IssueDate", ""),
            "Purpose": L.get("Purpose", ""), "Area_acre": L.get("Area_acre", ""),
            "DevPlan": L.get("DevPlan") or L.get("DevPlanRaw", ""),
            "Sector": L.get("Sector", ""),
            "Developer": L.get("Developer", ""),
            "ValidUpto": L.get("ValidUpto", ""),
            "licence_active": "" if valid_to is None else str(valid_to >= today),
            "match_status": status, "match_score": f"{best_sim:.0f}",
            "match_why": best_why,
            "rera_project": best.get("Project Name", "") if best else "",
            "rera_reg_no": best.get("Project Registration Number", "") if best else "",
            "rera_promoter": best.get("Promoter Name", "") if best else "",
        })

    out = ddir / "licence_rera_map.csv"
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)

    from collections import Counter
    counts = Counter(r["match_status"] for r in out_rows)
    print(f"{city}: {len(out_rows)} licences | " +
          ", ".join(f"{k}={v}" for k, v in counts.most_common()))
    for label, statuses in [
        ("GAP A - developer absent from RERA, licence still valid", {"UNMATCHED", "WEAK"}),
        ("GAP B - developer in RERA but THIS parcel unconfirmed, licence valid", {"DEV-MATCH"}),
    ]:
        gap = [r for r in out_rows
               if r["match_status"] in statuses and r["licence_active"] == "True"]
        print(f"\n{label}: {len(gap)}")
        for r in sorted(gap, key=lambda r: r["IssueDate"][-4:]):
            print(f"  {r['IssueDate'][-4:]}  {r['Purpose']:10} {r['Area_acre']:>9} ac  "
                  f"Sec {r['Sector']:8} valid till {r['ValidUpto']:12} {r['Developer'][:42]}")


if __name__ == "__main__":
    main()
