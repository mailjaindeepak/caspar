"""Roll up cross-register stats per developer lead into details_json.dev_stats.

Computed from caspar.db by normalized-name matching (same convention as the
entity-resolution layer's fuzzy tier):
  scale (licences, acres, RERA projects) · group-housing experience ·
  hospitality CLUs · licensed-but-unlaunched land · pending applications ·
  clean-record flags. Max ticket + financial capacity are mined from the
  research score_notes where present.

Safe to re-run (recomputes every developer lead). Run after sync_leads.py.
Usage: python app/enrich_developer_stats.py
"""
import json
import re
import sqlite3
from pathlib import Path

from sync_leads import norm_name

ROOT = Path(__file__).resolve().parent.parent
LEADS_DB = ROOT / "db" / "leads.db"
CASPAR_DB = ROOT / "db" / "caspar.db"

HOSP = ("hotel", "motel", "resort", "banquet", "farm house", "farmhouse",
        "amusement", "club", "restaurant", "dhaba", "guest", "marriage")

STOP_TOKS = {"AND", "THE", "SONS", "ESTATE", "ESTATES", "INFRASTRUCTURE",
             "DEVELOPERS", "DEVELOPER", "BUILDERS", "TOWNSHIP", "TOWNSHIPS",
             "STRATEGIC", "LANDOWNER", "PROJECTS", "REALTY", "HOMES", "INFRA"}


def toks(s):
    # strip the research-name annotations: "Aarize (Karnelya)" -> AARIZE
    s = re.sub(r"\(.*?\)", " ", s or "")
    out = set()
    for t in norm_name(s).split():
        if len(t) > 2 and t not in STOP_TOKS:
            out.add(t[:-1] if t.endswith("S") and len(t) > 3 else t)
    return out


def tmatch(t, nt):
    """Token match; single-token names must match exactly (no subset)."""
    if not t or not nt:
        return False
    if len(t) == 1 or len(nt) == 1:
        return t == nt
    return t <= nt or nt <= t


def main():
    caspar = sqlite3.connect(CASPAR_DB)
    caspar.row_factory = sqlite3.Row

    lic = [(toks(r["developer_raw"]), dict(r)) for r in caspar.execute(
        "SELECT licence_no, developer_raw, purpose, area_acre, valid_upto_raw, "
        "district FROM licence_raw")]
    rera = [(toks(r["promoter_raw"]), dict(r)) for r in caspar.execute(
        "SELECT promoter_raw, rera_reg_no FROM rera_raw")]
    # entity-resolution layer: canonical name -> alias names + linked row keys
    ent_alias_names = {}
    ent_lic_keys = {}
    ent_rera_keys = {}
    for r in caspar.execute("""SELECT e.canonical_name AS cn, ea.alias_name,
                                      ea.source, ea.source_row_key
                               FROM entity e JOIN entity_alias ea
                                 ON ea.entity_id = e.entity_id"""):
        fs = frozenset(toks(r["alias_name"]))
        if fs:
            ent_alias_names.setdefault(r["cn"], set()).add(fs)
        if r["source"] == "licence" and r["source_row_key"]:
            ent_lic_keys.setdefault(r["cn"], set()).add(r["source_row_key"])
        elif r["source"] == "rera" and r["source_row_key"]:
            ent_rera_keys.setdefault(r["cn"], set()).add(r["source_row_key"])
    clu = [(toks(r["applicant"]), dict(r)) for r in caspar.execute(
        "SELECT applicant, activity, area_acre FROM clu_raw")]
    ripe = [(toks(r["developer_group"] or r["developer_raw"]), dict(r))
            for r in caspar.execute(
        "SELECT developer_group, developer_raw, area_acre FROM v_ripe_parcels")]
    pend = [(toks(r["developer_raw"]), dict(r)) for r in caspar.execute(
        "SELECT developer_raw, area_acre, receipt_date FROM licence_pending_raw "
        "WHERE scraped_at=(SELECT max(scraped_at) FROM licence_pending_raw)")]
    entities = {r["canonical_name"]: dict(r) for r in caspar.execute(
        "SELECT canonical_name, cin, score_notes, notes FROM entity")}

    cx = sqlite3.connect(LEADS_DB)
    cx.row_factory = sqlite3.Row
    for lead in cx.execute("SELECT id, title, details_json FROM leads "
                           "WHERE kind='developer'").fetchall():
        t = toks(lead["title"])
        d = json.loads(lead["details_json"])
        ent = entities.get(lead["title"], {})
        notes = " ".join(filter(None, [d.get("score_notes"), ent.get("score_notes"),
                                       ent.get("notes")]))

        # name-sets to match on: canonical name + every alias name variant
        name_sets = [t] + [set(fs) for fs in ent_alias_names.get(lead["title"], set()) if fs]
        lic_keys = ent_lic_keys.get(lead["title"], set())
        rera_keys = ent_rera_keys.get(lead["title"], set())

        def any_match(nt):
            return any(tmatch(ns, nt) for ns in name_sets)

        my_lic = [r for tt, r in lic
                  if r["licence_no"] in lic_keys or any_match(tt)]
        my_rera = [r for tt, r in rera
                   if r["rera_reg_no"] in rera_keys or any_match(tt)]
        my_clu = [r for tt, r in clu if any_match(tt)
                  and any(h in (r["activity"] or "").lower() for h in HOSP)]
        my_ripe = [r for tt, r in ripe if any_match(tt)]
        my_pend = [r for tt, r in pend if any_match(tt)]

        acres = sum(float(r["area_acre"] or 0) for r in my_lic)
        flags = []
        for r in my_lic:
            if "cancel" in (r["valid_upto_raw"] or "").lower():
                flags.append("cancelled licence")
        for kw, label in (("CIRP", "CIRP/insolvency"), ("insolven", "CIRP/insolvency"),
                          ("blacklist", "blacklisted"), ("debt", "debt stress")):
            if kw.lower() in notes.lower():
                flags.append(label)
        ticket = re.search(r"₹\s?[\d.,]+(?:\s?[-–]\s?[\d.,]+)?\s?"
                           r"(?:Cr|cr|k/sqft|lakh|L)\b[^;.]*", notes)
        fin = []
        if "listed" in notes.lower():
            fin.append("Listed co.")
        if ent.get("cin"):
            fin.append(f"CIN {ent['cin']}")
        m = re.search(r"(₹\s?[\d,]+\+?\s?[Cc]r[^;.]{0,30}(?:invest|sold|sales|turnover)[^;.]{0,20})", notes)
        if m:
            fin.append(m.group(1).strip())

        d["dev_stats"] = {
            "n_licences": len(my_lic), "licensed_acres": round(acres, 1),
            "n_rera": len({r["rera_reg_no"] for r in my_rera}),
            "group_housing": "Yes" if any(r["purpose"] == "RGH" for r in my_lic) else "No",
            "hosp_clu": len(my_clu),
            "hosp_clu_acres": round(sum(float(r["area_acre"] or 0) for r in my_clu), 1),
            "unlaunched_n": len(my_ripe),
            "unlaunched_acres": round(sum(float(r["area_acre"] or 0) for r in my_ripe), 1),
            "pending_n": len(my_pend),
            "pending_acres": round(sum(float(r["area_acre"] or 0) for r in my_pend), 1),
            "clean_record": "; ".join(sorted(set(flags))) or "Clean",
            "max_ticket": ticket.group(0).strip() if ticket else "",
            "fin_capacity": " · ".join(fin),
        }
        cx.execute("UPDATE leads SET details_json=? WHERE id=?",
                   (json.dumps(d, ensure_ascii=False), lead["id"]))
        s = d["dev_stats"]
        print(f"  {lead['title'][:38]:<38} lic:{s['n_licences']:>2} ({s['licensed_acres']:>7} ac) "
              f"rera:{s['n_rera']:>2} rgh:{s['group_housing']:<3} clu:{s['hosp_clu']} "
              f"ripe:{s['unlaunched_n']} pend:{s['pending_n']} [{s['clean_record']}]")
    cx.commit()
    print("done")


if __name__ == "__main__":
    main()
