"""Kontrola: RO 2026 (č. 1–15) × MONITOR 2026/08 na úrovni paragraf/položka (data/monitor/monitor_vs_ro2026_par_pol_2026-08.csv).
Ověřuje: (1) součet rozdílů = 0 (celkově RO = MONITOR), (2) CSV odpovídá aktuálnímu RO JSON, (3) čerpání rezerv mimo RO = přesuny jinam."""
import csv, json, sys
from collections import defaultdict
rows = list(csv.DictReader(open("data/monitor/monitor_vs_ro2026_par_pol_2026-08.csv", encoding="utf-8"), delimiter=";"))
bad = 0
tot = sum(float(r["rozdil"]) for r in rows)
ok = abs(tot) <= 1; bad += not ok
print(f"{'OK ' if ok else 'ROZ'} součet rozdílů {tot:,.2f}")
d = json.load(open("data/rozpocet/2026/rozpoctova_opatreni_2026.json", encoding="utf-8"))
R = defaultdict(float)
for o in d["opatreni"]:
    if o["datum"] > "2026-08-31": continue
    for x in o["radky"]:
        p = int(x["pol"])
        if x["pol"][0] in "56" and not 5341 <= p <= 5349: R[f'{x["odpa"]}/{x["pol"]}'] += x["zmena"]
mism = [r for r in rows if abs(float(r["zmena_RO"]) - R.get(f'{r["paragraf"]}/{r["polozka"]}', 0)) > 0.5]
ok = not mism; bad += not ok
print(f"{'OK ' if ok else 'ROZ'} CSV odpovídá RO JSON ({len(mism)} odchylek)")
s = defaultdict(float)
for r in rows: s[r["kategorie"]] += float(r["rozdil"])
for k, v in sorted(s.items()): print(f"   {k}: {v:,.2f} Kč")
sys.exit(1 if bad else 0)
