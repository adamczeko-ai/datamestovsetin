"""Křížová kontrola: rozpočtová opatření 2026 (repo, PDF) × MONITOR FIN 2-12 M 2026/08 (rozpočet po změnách − schválený).
Úroveň 1 (celkové součty) je tvrdý test (exit 1). Úroveň 2 (paragrafy, jen top 27 v MONITOR CSV) je informativní."""
import json, csv, sys
CUTOFF = "2026-08-31"
MON = {"prijmy": 1040017311 - 995899000, "vydaje": (918565308 + 547409948) - (883224000 + 397274000)}
d = json.load(open("data/rozpocet/2026/rozpoctova_opatreni_2026.json", encoding="utf-8"))
S = {"prijmy": 0.0, "vydaje": 0.0}; ro_par = {}; n = 0
for o in d["opatreni"]:
    if o["datum"] > CUTOFF: continue
    n += 1
    for r in o["radky"]:
        p = int(r["pol"])
        if 4131 <= p <= 4139 or 5341 <= p <= 5349 or r["pol"][0] == "8": continue
        if r["pol"][0] in "1234": S["prijmy"] += r["zmena"]
        elif r["pol"][0] in "56":
            S["vydaje"] += r["zmena"]; ro_par[r["odpa"]] = ro_par.get(r["odpa"], 0) + r["zmena"]
bad = 0
print(f"RO do {CUTOFF}: {n} opatření")
for k in S:
    ok = abs(S[k] - MON[k]) <= 1; bad += not ok
    print(f"{'OK ' if ok else 'ROZ'} {k}: RO {S[k]:,.0f} | MONITOR {MON[k]:,.0f}")
M = {r["paragraf"]: float(r["vydaje_po_zmenach"]) - float(r["vydaje_schvaleno"]) for r in csv.DictReader(open("data/monitor/monitor_finm_vsetin_paragrafy_2026-08_top27.csv", encoding="utf-8"), delimiter=";")}
diffs = [(p, M[p], ro_par.get(p, 0)) for p in sorted(M) if abs(M[p] - ro_par.get(p, 0)) > 1]
print(f"paragrafy (informativně): {len(M) - len(diffs)}/{len(M)} shoda")
for p, m, r in diffs: print(f"   {p}: MONITOR {m:,.0f} | RO {r:,.0f} | rozdíl {m - r:,.0f}")
sys.exit(1 if bad else 0)
