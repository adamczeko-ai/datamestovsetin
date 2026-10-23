"""Rekonciliace: transfery města podle FIN 2-12 M 2026/08 (data/monitor) × Územní registr dotací (data/dotace).
Exit 1, pokud zůstane nevysvětlený rozdíl."""
import csv, sys
from collections import defaultdict
F = {r["partner_ico"]: r for r in csv.DictReader(open("data/monitor/monitor_finm_vsetin_transfery_2026-08.csv", encoding="utf-8"), delimiter=";")}
R = defaultdict(float)
for r in csv.DictReader(open("data/dotace/uzemni_registr_vsetin_poskytovatel_2026.csv", encoding="utf-8")): R[r["prijemce_ico"]] += float(r["poskytnuto"])
VYLOUCENO = {"00000111": "technický kód", "72080043": "5363 sankce"}
UPRAVA = {"70891320": -200790.0}   # registr nezahrnuje pol. 5366 (finanční vypořádání)
fin = sum(float(r["vydano_bez_UZ_kz"]) for k, r in F.items() if k not in VYLOUCENO) + sum(UPRAVA.values())
reg = sum(R.values())
nevysv = [r["partner_ico"] for r in F.values() if r["rekonciliace"] == "ROZDÍL"]
print(f"FIN po úpravách {fin:,.2f} | registr {reg:,.2f} | rozdíl {fin - reg:,.2f}")
print(f"subjektů: FIN s poskytnutím {sum(1 for k,r in F.items() if float(r['vydano_bez_UZ_kz'])>0 and k not in VYLOUCENO)}, registr {len(R)}; nevysvětleno {nevysv}")
sys.exit(1 if abs(fin - reg) > 0.01 or nevysv else 0)
