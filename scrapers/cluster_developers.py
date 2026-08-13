"""Cluster HARERA project promoters into developer groups (name normalization).

Usage: python cluster_developers.py karnal
Reads data/<city>/harera_projects.csv, writes data/<city>/developers.csv
"""
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

NOISE = [
    r"\bM/S\.?\b", r"\bMS\.?\b", r"\bPRIVATE\b", r"\bPVT\.?\b", r"\bLIMITED\b",
    r"\bLTD\.?\b", r"\bLLP\b", r"\bINDIA\b", r"\bAND\b", r"\b&\b",
    r"\bCOMPANY\b", r"\bCO\.?\b",
]


def norm(name: str) -> str:
    s = name.upper()
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    for pat in NOISE:
        s = re.sub(pat, " ", s)
    s = re.sub(r"S\b", "", s)          # plural drift: DEVELOPMENTS/DEVELOPMENT
    s = re.sub(r"\s+", " ", s).strip()
    return s


def main() -> None:
    city = (sys.argv[1] if len(sys.argv) > 1 else "karnal").lower()
    src = ROOT / "data" / city / "harera_projects.csv"
    rows = list(csv.DictReader(src.open(encoding="utf-8-sig")))

    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        groups[norm(r.get("Promoter Name", ""))].append(r)

    out = ROOT / "data" / city / "developers.csv"
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["developer_key", "promoter_names", "n_projects",
                    "projects", "reg_numbers"])
        for key, prs in sorted(groups.items(), key=lambda kv: -len(kv[1])):
            names = sorted({p.get("Promoter Name", "") for p in prs})
            projects = sorted({p.get("Project Name", "") for p in prs})
            regs = sorted({p.get("Project Registration Number", "") for p in prs})
            w.writerow([key, " | ".join(names), len(prs),
                        " | ".join(projects), " | ".join(regs)])
    print(f"{city}: {len(rows)} projects -> {len(groups)} developer groups -> {out}")


if __name__ == "__main__":
    main()
