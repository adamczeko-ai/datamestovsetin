"""Kontrola RO 2023 proti řádkům „Celkem PŘÍJMY/VÝDAJE/FINANCOVÁNÍ“ z PDF (vytěženo 2026-10-23)."""
import collections, json, sys
d = json.load(open("data/rozpocet/2023/rozpoctova_opatreni_2023.json", encoding="utf-8"))
CEL = {1:(1112800,1112800,0),2:(2957224,5377288.87,2420064.87),3:(3571000,3571000,0),4:(269347,269347,0),5:(299575.69,40639178,40339602.31),6:(2493705.86,2425705.86,0),7:(117088,117088,0),8:(2103466,6180081,4076615),9:(2900850,2900850,0),10:(0,47799000,47799000),11:(1582201.85,1582201.85,0),12:(12105601.2,12105601.2,0),13:(2199695.03,8563743.03,6364048),14:(6129925,6129925,0),15:(2781795,2781795,0),16:(238965.1,238965.1,0),17:(0,1570314,1570314),18:(491012,491012,0),19:(0,0,0),20:(1128999.2,1128999.2,0),21:(192155,8909232,8717077),22:(-102440,-102440,0)}
bad = 0
for o in d["opatreni"]:
    s = tuple(round(sum(r["zmena"] for r in o["radky"] if r["typ"] == t), 2) for t in "PVF")
    ar = [r for r in o["radky"] if round(r["pred"] + r["zmena"], 2) != round(r["po"], 2)]
    if s != tuple(round(x, 2) for x in CEL[o["cislo"]]) or ar:
        bad += 1; print("RO", o["cislo"], s, CEL[o["cislo"]], len(ar))
rows = sum(len(o["radky"]) for o in d["opatreni"])
print("RO", len(d["opatreni"]), "rows", rows, "bad", bad)
sys.exit(1 if bad or rows != 473 else 0)
